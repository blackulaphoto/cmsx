#!/usr/bin/env python3
"""
Client Management API - Core client creation and management endpoints
Fixes the missing client creation pipeline causing HTTP 405 errors
"""

from fastapi import APIRouter, HTTPException, status, Query, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import sqlite3
import uuid
import json
from datetime import datetime
from pathlib import Path
from backend.shared.database.railway_postgres import upsert_client_to_postgres
from backend.shared.database.workspace_store import workspace_store
from backend.api.client_data_integration import get_client_data_integrator
from backend.auth.authorization import assert_client_access, effective_case_manager_id
from backend.auth.service import require_authenticated_user

try:
    from backend.modules.reminders.intelligent_processor import IntelligentTaskProcessor
except ImportError:
    IntelligentTaskProcessor = None

logger = logging.getLogger(__name__)

router = APIRouter()

CORE_CLIENT_SCHEMA_COLUMNS = {
    "client_id": "TEXT PRIMARY KEY",
    "first_name": "TEXT NOT NULL",
    "last_name": "TEXT NOT NULL",
    "email": "TEXT",
    "phone": "TEXT",
    "date_of_birth": "TEXT",
    "address": "TEXT",
    "city": "TEXT",
    "state": "TEXT",
    "zip_code": "TEXT",
    "emergency_contact_name": "TEXT",
    "emergency_contact_phone": "TEXT",
    "emergency_contact_relationship": "TEXT",
    "case_manager_id": "TEXT NOT NULL",
    "risk_level": "TEXT DEFAULT 'medium'",
    "case_status": "TEXT DEFAULT 'active'",
    "intake_date": "TEXT NOT NULL",
    "created_at": "TEXT NOT NULL",
    "updated_at": "TEXT",
    "housing_status": "TEXT DEFAULT 'unknown'",
    "employment_status": "TEXT DEFAULT 'unknown'",
    "benefits_status": "TEXT DEFAULT 'not applied'",
    "legal_status": "TEXT DEFAULT 'no active cases'",
    "program_type": "TEXT",
    "referral_source": "TEXT",
    "prior_convictions": "TEXT",
    "substance_abuse_history": "TEXT",
    "mental_health_status": "TEXT",
    "transportation": "TEXT",
    "medical_conditions": "TEXT",
    "special_needs": "TEXT",
    "goals": "TEXT",
    "barriers": "TEXT",
    "notes": "TEXT",
    "progress": "INTEGER DEFAULT 0",
    "last_contact": "TEXT",
    "next_followup": "TEXT",
    "needs": "TEXT DEFAULT '[]'",
    "background": "TEXT DEFAULT '{}'",
}

def get_database_connection(db_name: str, access_type: str = "READ_ONLY"):
    """Simple database connection helper"""
    db_path = Path("databases") / f"{db_name}.db"
    if not db_path.exists():
        # Create database directory if it doesn't exist
        db_path.parent.mkdir(exist_ok=True)
        # Create empty database file
        db_path.touch()
    return sqlite3.connect(str(db_path))


def ensure_core_clients_schema(conn: sqlite3.Connection) -> None:
    """Ensure the shared clients table exposes the fields live modules render."""
    cursor = conn.cursor()
    create_columns_sql = ",\n                    ".join(
        f"{column} {definition}" for column, definition in CORE_CLIENT_SCHEMA_COLUMNS.items()
    )
    cursor.execute(
        f"""
            CREATE TABLE IF NOT EXISTS clients (
                {create_columns_sql}
            )
        """
    )

    cursor.execute("PRAGMA table_info(clients)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    for column, definition in CORE_CLIENT_SCHEMA_COLUMNS.items():
        if column in existing_columns:
            continue
        base_definition = definition.split(" DEFAULT ")[0]
        cursor.execute(f"ALTER TABLE clients ADD COLUMN {column} {base_definition}")

    conn.commit()


def _deserialize_json_field(value: Any, fallback: Any) -> Any:
    if value in (None, ""):
        return fallback
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _serialize_json_field(value: Any, fallback: Any) -> str:
    if value in (None, ""):
        return json.dumps(fallback)
    if isinstance(value, str):
        return value
    return json.dumps(value)


def normalize_client_record(row: sqlite3.Row) -> Dict[str, Any]:
    """Normalize shared client rows into the shape frontend modules expect."""
    first_name = row["first_name"] or ""
    last_name = row["last_name"] or ""
    risk_level = row["risk_level"] or "medium"
    case_status = row["case_status"] or "active"
    return {
        "client_id": row["client_id"],
        "first_name": first_name,
        "last_name": last_name,
        "full_name": f"{first_name} {last_name}".strip(),
        "email": row["email"] or "",
        "phone": row["phone"] or "",
        "date_of_birth": row["date_of_birth"] or "",
        "address": row["address"] or "",
        "city": row["city"] or "",
        "state": row["state"] or "",
        "zip_code": row["zip_code"] or "",
        "emergency_contact_name": row["emergency_contact_name"] or "",
        "emergency_contact_phone": row["emergency_contact_phone"] or "",
        "emergency_contact_relationship": row["emergency_contact_relationship"] or "",
        "case_manager_id": row["case_manager_id"] or "",
        "risk_level": risk_level.capitalize(),
        "case_status": case_status.capitalize(),
        "intake_date": row["intake_date"] or "",
        "created_at": row["created_at"] or "",
        "updated_at": row["updated_at"] or row["created_at"] or "",
        "housing_status": row["housing_status"] or "Unknown",
        "employment_status": row["employment_status"] or "Unknown",
        "benefits_status": row["benefits_status"] or "Not Applied",
        "legal_status": row["legal_status"] or "No Active Cases",
        "program_type": row["program_type"] or "",
        "referral_source": row["referral_source"] or "",
        "prior_convictions": row["prior_convictions"] or "",
        "substance_abuse_history": row["substance_abuse_history"] or "",
        "mental_health_status": row["mental_health_status"] or "",
        "transportation": row["transportation"] or "",
        "medical_conditions": row["medical_conditions"] or "",
        "special_needs": row["special_needs"] or "",
        "goals": row["goals"] or "",
        "barriers": row["barriers"] or "",
        "notes": row["notes"] or "",
        "progress": int(row["progress"] or 0),
        "last_contact": row["last_contact"] or "",
        "next_followup": row["next_followup"] or "",
        "needs": _deserialize_json_field(row["needs"], []),
        "background": _deserialize_json_field(row["background"], {}),
    }


def build_client_sync_payload(client: Dict[str, Any]) -> Dict[str, Any]:
    """Build the shared intake payload propagated to module databases and Postgres."""
    payload = dict(client)
    first_name = payload.get("first_name") or ""
    last_name = payload.get("last_name") or ""
    payload["full_name"] = payload.get("full_name") or f"{first_name} {last_name}".strip()
    payload["admission_date"] = payload.get("admission_date") or payload.get("intake_date")
    payload["needs"] = _serialize_json_field(payload.get("needs"), [])
    payload["background"] = _serialize_json_field(payload.get("background"), {})
    return payload


def _normalize_need_key(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _add_need(needs: List[Dict[str, Any]], seen: set, need_key: str, domain: str, reason: str, priority: str = "medium") -> None:
    normalized_key = _normalize_need_key(need_key)
    if not normalized_key or normalized_key in seen:
        return
    seen.add(normalized_key)
    needs.append({
        "need_key": normalized_key,
        "domain": domain,
        "source": "intake",
        "priority": priority,
        "status": "suggested",
        "reason": reason,
    })


def derive_operational_needs(client: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Derive normalized operational needs from current intake facts without creating tasks."""
    needs: List[Dict[str, Any]] = []
    seen: set = set()

    for raw_need in client.get("needs") or []:
        key = _normalize_need_key(raw_need)
        domain = {
            "housing": "housing",
            "sober_living": "sober_living",
            "sober_living_aftercare": "sober_living",
            "employment": "employment",
            "job_search": "employment",
            "resume": "resume",
            "benefits": "benefits",
            "medical": "medical",
            "legal": "legal",
            "transportation": "services",
        }.get(key, "services")
        _add_need(needs, seen, key, domain, "Need captured on intake form")

    housing_status = str(client.get("housing_status") or "").strip().lower()
    if housing_status in {"unknown", "unstable", "homeless", "transitional", "needs housing"}:
        _add_need(needs, seen, "housing", "housing", f"Housing status is {client.get('housing_status')}", "high")

    employment_status = str(client.get("employment_status") or "").strip().lower()
    if employment_status in {"unknown", "unemployed", "seeking", "not employed"}:
        _add_need(needs, seen, "resume", "resume", f"Employment status is {client.get('employment_status')}", "medium")
        _add_need(needs, seen, "job_search", "employment", f"Employment status is {client.get('employment_status')}", "medium")

    benefits_status = str(client.get("benefits_status") or "").strip().lower()
    if benefits_status in {"not applied", "pending", "unknown", "needs screening"}:
        _add_need(needs, seen, "benefits_screening", "benefits", f"Benefits status is {client.get('benefits_status')}", "medium")

    legal_status = str(client.get("legal_status") or "").strip().lower()
    if legal_status and legal_status not in {"no active cases", "none", "unknown"}:
        _add_need(needs, seen, "legal_follow_up", "legal", f"Legal status is {client.get('legal_status')}", "high")

    medical_text = " ".join([
        str(client.get("medical_conditions") or ""),
        str(client.get("special_needs") or ""),
        str(client.get("mental_health_status") or ""),
    ]).lower()
    if any(term in medical_text for term in ["dental", "tooth", "teeth", "dentist"]):
        _add_need(needs, seen, "dental", "medical", "Dental need found in medical/special-needs intake", "high")
    if client.get("medical_conditions"):
        _add_need(needs, seen, "primary_care", "medical", "Medical conditions documented in intake", "medium")
    if any(term in medical_text for term in ["psychiatry", "psychiatric", "medication", "mental health", "depression", "anxiety"]):
        _add_need(needs, seen, "behavioral_health", "medical", "Behavioral health context documented in intake", "medium")
    if any(term in medical_text for term in ["disabled", "disability", "ssi", "ssdi", "functional limitation"]):
        _add_need(needs, seen, "disability", "benefits", "Disability context documented in intake", "high")

    transportation = str(client.get("transportation") or "").strip().lower()
    if transportation and transportation not in {"none", "no", "n/a", "not needed"}:
        _add_need(needs, seen, "transportation", "services", f"Transportation barrier is {client.get('transportation')}", "medium")

    goals_barriers = f"{client.get('goals') or ''} {client.get('barriers') or ''}".lower()
    if any(term in goals_barriers for term in ["sober living", "aftercare", "outpatient", "step down", "step-down"]):
        _add_need(needs, seen, "sober_living_aftercare", "sober_living", "Aftercare/sober living need found in goals or barriers", "high")

    return needs


def _client_identity_context(client: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "client_id": client.get("client_id"),
        "first_name": client.get("first_name", ""),
        "last_name": client.get("last_name", ""),
        "full_name": client.get("full_name", ""),
        "date_of_birth": client.get("date_of_birth", ""),
        "phone": client.get("phone", ""),
        "email": client.get("email", ""),
        "address": client.get("address", ""),
        "city": client.get("city", ""),
        "state": client.get("state", ""),
        "zip_code": client.get("zip_code", ""),
        "case_manager_id": client.get("case_manager_id", ""),
        "risk_level": client.get("risk_level", "Medium"),
        "case_status": client.get("case_status", "Active"),
        "intake_date": client.get("intake_date", ""),
        "admission_date": client.get("admission_date") or client.get("intake_date", ""),
        "program_type": client.get("program_type", ""),
    }


def _client_intake_context(client: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "housing_status": client.get("housing_status", "Unknown"),
        "employment_status": client.get("employment_status", "Unknown"),
        "benefits_status": client.get("benefits_status", "Not Applied"),
        "legal_status": client.get("legal_status", "No Active Cases"),
        "prior_convictions": client.get("prior_convictions", ""),
        "substance_abuse_history": client.get("substance_abuse_history", ""),
        "mental_health_status": client.get("mental_health_status", ""),
        "medical_conditions": client.get("medical_conditions", ""),
        "special_needs": client.get("special_needs", ""),
        "transportation": client.get("transportation", ""),
        "referral_source": client.get("referral_source", ""),
        "goals": client.get("goals", ""),
        "barriers": client.get("barriers", ""),
        "notes": client.get("notes", ""),
        "needs": client.get("needs", []),
        "background": client.get("background", {}),
    }


def _get_active_treatment_plan_placeholder(
    client: Dict[str, Any],
    operational_needs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    try:
        current_plan = workspace_store.get_current_treatment_plan(client.get("client_id"))
    except Exception as exc:
        logger.warning("Unable to load current treatment plan for %s: %s", client.get("client_id"), exc)
        current_plan = None

    if current_plan:
        return {
            "plan_id": current_plan.get("plan_id"),
            "status": current_plan.get("status", "draft"),
            "created_at": current_plan.get("created_at"),
            "approved_at": current_plan.get("approved_at"),
            "review_due_date": current_plan.get("review_due_date"),
            "problems": current_plan.get("problems") or [],
            "goals": current_plan.get("goals") or [],
            "objectives": current_plan.get("objectives") or [],
            "interventions": current_plan.get("interventions") or [],
            "target_dates": current_plan.get("target_dates") or [],
            "aftercare_plan": current_plan.get("aftercare_plan") or {},
            "completion_criteria": current_plan.get("completion_criteria") or [],
            "operational_needs": current_plan.get("operational_needs") or operational_needs or [],
            "source": current_plan.get("source", ""),
        }

    background = client.get("background") if isinstance(client.get("background"), dict) else {}
    treatment_plan = background.get("treatment_plan") or background.get("treatment_plan_summary")
    aftercare_plan = background.get("aftercare_plan") or background.get("aftercare_plan_summary")
    intake_has_plan_seed = bool(client.get("goals") or client.get("barriers") or client.get("needs"))
    status = "draft" if treatment_plan or aftercare_plan else ("intake_seed" if intake_has_plan_seed else "missing")
    return {
        "plan_id": background.get("treatment_plan_id") or None,
        "status": status,
        "created_at": background.get("treatment_plan_created_at"),
        "approved_at": background.get("treatment_plan_approved_at"),
        "review_due_date": background.get("treatment_plan_review_due_date"),
        "problems": background.get("treatment_plan_problems") or [],
        "goals": background.get("treatment_plan_goals") or ([client.get("goals")] if client.get("goals") else []),
        "objectives": background.get("treatment_plan_objectives") or [],
        "interventions": background.get("treatment_plan_interventions") or [],
        "target_dates": background.get("treatment_plan_target_dates") or [],
        "aftercare_plan": aftercare_plan or {},
        "completion_criteria": background.get("completion_criteria") or [],
        "operational_needs": background.get("operational_needs") or operational_needs or [],
    }


def _open_task_context(overview_data: Dict[str, Any], services_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    open_tasks: List[Dict[str, Any]] = []

    for task in overview_data.get("tasks", []) or []:
        status_value = str(task.get("status") or "").strip().lower()
        if status_value in {"completed", "done", "cancelled", "canceled"}:
            continue
        open_tasks.append({
            "task_id": task.get("task_id"),
            "source": "case_management",
            "module": task.get("module") or "case_management",
            "title": task.get("title") or task.get("task_type") or "Client task",
            "description": task.get("description") or "",
            "priority": task.get("priority") or "medium",
            "due_date": task.get("due_date"),
            "status": task.get("status") or "pending",
            "need_key": task.get("need_key"),
        })

    for reminder in overview_data.get("reminders", []) or []:
        status_value = str(reminder.get("status") or "").strip().lower()
        if status_value in {"completed", "done", "cancelled", "canceled"}:
            continue
        open_tasks.append({
            "task_id": reminder.get("reminder_id"),
            "source": "reminders",
            "module": "reminders",
            "title": reminder.get("message") or reminder.get("reminder_type") or "Reminder",
            "description": reminder.get("message") or "",
            "priority": reminder.get("priority") or "medium",
            "due_date": reminder.get("due_date"),
            "status": reminder.get("status") or "active",
            "need_key": reminder.get("need_key"),
        })

    for task in services_summary.get("tasks", []) or []:
        status_value = str(task.get("status") or "").strip().lower()
        if status_value in {"completed", "done", "cancelled", "canceled"}:
            continue
        open_tasks.append({
            "task_id": task.get("task_id"),
            "source": "services",
            "module": "services",
            "title": task.get("title") or task.get("task_type") or "Service task",
            "description": task.get("description") or "",
            "priority": task.get("priority") or "medium",
            "due_date": task.get("due_date"),
            "status": task.get("status") or "pending",
            "need_key": task.get("need_key"),
        })

    return open_tasks[:25]


def build_client_operational_context(
    client: Dict[str, Any],
    overview_data: Optional[Dict[str, Any]] = None,
    benefits_summary: Optional[Dict[str, Any]] = None,
    legal_summary: Optional[Dict[str, Any]] = None,
    services_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the shared read model consumed by module dropdown workflows."""
    overview_data = overview_data or {}
    benefits_summary = benefits_summary or get_client_benefits_summary(client["client_id"])
    legal_summary = legal_summary or get_client_legal_summary(client["client_id"])
    services_summary = services_summary or get_client_services_summary(client["client_id"])
    operational_needs = derive_operational_needs(client)
    try:
        stored_needs = workspace_store.list_client_operational_needs(client["client_id"])
    except Exception as exc:
        logger.warning("Unable to load stored operational needs for %s: %s", client["client_id"], exc)
        stored_needs = []
    seen_need_keys = {need.get("need_key") for need in operational_needs}
    for stored_need in stored_needs:
        if stored_need.get("status") in {"resolved", "cancelled", "canceled"}:
            continue
        if stored_need.get("need_key") in seen_need_keys:
            continue
        operational_needs.append({
            "need_key": stored_need.get("need_key"),
            "domain": stored_need.get("domain"),
            "module": stored_need.get("module"),
            "source": stored_need.get("source"),
            "source_id": stored_need.get("source_id"),
            "source_plan_id": stored_need.get("source_plan_id"),
            "priority": stored_need.get("priority"),
            "status": stored_need.get("status"),
            "reason": stored_need.get("reason"),
        })
        seen_need_keys.add(stored_need.get("need_key"))
    open_tasks = _open_task_context(overview_data, services_summary)
    treatment_plan_context = _get_active_treatment_plan_placeholder(client, operational_needs)

    return {
        "client": _client_identity_context(client),
        "intake": _client_intake_context(client),
        "treatment_plan": treatment_plan_context,
        "module_context": {
            "legal": {
                "intake_status": client.get("legal_status", "No Active Cases"),
                "prior_convictions": client.get("prior_convictions", ""),
                "summary": legal_summary,
                "needs": [need for need in operational_needs if need["domain"] == "legal"],
                "active_needs": [need for need in operational_needs if need["domain"] == "legal"],
            },
            "medical": {
                "medical_conditions": client.get("medical_conditions", ""),
                "mental_health_status": client.get("mental_health_status", ""),
                "special_needs": client.get("special_needs", ""),
                "needs": [need for need in operational_needs if need["domain"] == "medical"],
                "active_needs": [need for need in operational_needs if need["domain"] == "medical"],
            },
            "benefits": {
                "status": client.get("benefits_status", "Not Applied"),
                "medical_conditions": client.get("medical_conditions", ""),
                "special_needs": client.get("special_needs", ""),
                "summary": benefits_summary,
                "needs": [need for need in operational_needs if need["domain"] == "benefits"],
                "active_needs": [need for need in operational_needs if need["domain"] == "benefits"],
            },
            "housing": {
                "status": client.get("housing_status", "Unknown"),
                "address": client.get("address", ""),
                "city": client.get("city", ""),
                "state": client.get("state", ""),
                "zip_code": client.get("zip_code", ""),
                "needs": [need for need in operational_needs if need["domain"] == "housing"],
                "active_needs": [need for need in operational_needs if need["domain"] == "housing"],
            },
            "sober_living": {
                "program_type": client.get("program_type", ""),
                "aftercare_plan": treatment_plan_context.get("aftercare_plan"),
                "needs": [need for need in operational_needs if need["domain"] == "sober_living"],
                "active_needs": [need for need in operational_needs if need["domain"] == "sober_living"],
            },
            "employment": {
                "status": client.get("employment_status", "Unknown"),
                "goals": client.get("goals", ""),
                "barriers": client.get("barriers", ""),
                "needs": [need for need in operational_needs if need["domain"] == "employment"],
                "active_needs": [need for need in operational_needs if need["domain"] == "employment"],
            },
            "resume": {
                "contact": _client_identity_context(client),
                "prior_convictions": client.get("prior_convictions", ""),
                "employment_status": client.get("employment_status", "Unknown"),
                "needs": [need for need in operational_needs if need["domain"] == "resume"],
                "active_needs": [need for need in operational_needs if need["domain"] == "resume"],
            },
            "documentation": {
                "admission_date": client.get("intake_date", ""),
                "program_type": client.get("program_type", ""),
                "goals": client.get("goals", ""),
                "barriers": client.get("barriers", ""),
                "treatment_plan_available": treatment_plan_context.get("status") in {"draft", "active", "review_due", "completed"},
            },
            "reminders": {
                "open_tasks": open_tasks,
                "suggested_needs": operational_needs,
            },
        },
        "operational_needs": operational_needs,
        "open_tasks": open_tasks,
        "daily_priority": {
            "risk_level": client.get("risk_level", "Medium"),
            "open_task_count": len(open_tasks),
            "suggested_need_count": len(operational_needs),
            "highest_priority_needs": [
                need for need in operational_needs if need.get("priority") in {"urgent", "high"}
            ][:5],
        },
        "data_sources": {
            "client": "core_clients.db",
            "overview": "case_management.db + reminders.db",
            "benefits": "unified_platform.db",
            "legal": "legal_cases.db",
            "services": "social_services.db",
            "treatment_plan": "background placeholder until first-class treatment plan store exists",
        },
        "metadata": {
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "read_only": True,
        },
    }


def get_client_benefits_summary(client_id: str) -> Dict[str, Any]:
    """Get benefits application summary for unified client view."""
    summary = {
        "applications": [],
        "total_applications": 0,
        "active_applications": 0,
        "latest_application": None,
    }
    try:
        with get_database_connection("unified_platform", "READ_ONLY") as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT application_id, COALESCE(benefit_type, application_type) AS benefit_type,
                       status, application_method, assistance_received, notes,
                       created_at, last_updated
                FROM benefits_applications
                WHERE client_id = ?
                ORDER BY COALESCE(last_updated, created_at) DESC, id DESC
                """,
                (client_id,),
            )
            rows = cursor.fetchall()

        applications = []
        for row in rows:
            application = {
                "application_id": row[0],
                "benefit_type": row[1],
                "status": row[2] or "Started",
                "application_method": row[3] or "Online",
                "assistance_received": bool(row[4]),
                "notes": row[5] or "",
                "created_at": row[6],
                "last_updated": row[7] or row[6],
            }
            applications.append(application)

        active_statuses = {"started", "pending", "submitted", "in progress", "under review"}
        summary["applications"] = applications
        summary["total_applications"] = len(applications)
        summary["active_applications"] = sum(
            1 for application in applications
            if str(application["status"]).strip().lower() in active_statuses
        )
        summary["latest_application"] = applications[0] if applications else None
        return summary
    except sqlite3.OperationalError:
        return summary
    except Exception as e:
        logger.error("Error getting benefits summary for %s: %s", client_id, e)
        return summary


def get_client_legal_summary(client_id: str) -> Dict[str, Any]:
    """Get legal case and court-date summary for unified client view."""
    summary = {
        "cases": [],
        "upcoming_court_dates": [],
        "total_cases": 0,
        "active_cases": 0,
        "next_court_date": None,
    }
    try:
        with get_database_connection("legal_cases", "READ_ONLY") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT case_id, case_number, case_type, case_status, court_name,
                       compliance_status, probation_end_date, created_at, last_updated
                FROM legal_cases
                WHERE client_id = ? AND is_active = 1
                ORDER BY COALESCE(last_updated, created_at) DESC
                """,
                (client_id,),
            )
            case_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT court_date_id, case_id, hearing_date, hearing_time, court_name,
                       courtroom, hearing_type, judge_name, status, reminder_sent
                FROM court_dates
                WHERE client_id = ?
                ORDER BY hearing_date ASC, hearing_time ASC
                """,
                (client_id,),
            )
            court_rows = cursor.fetchall()

        cases = []
        for row in case_rows:
            cases.append({
                "case_id": row["case_id"],
                "case_number": row["case_number"] or row["case_id"],
                "case_type": row["case_type"] or "Legal Case",
                "status": row["case_status"] or "Active",
                "court_name": row["court_name"] or "",
                "compliance_status": row["compliance_status"] or "Unknown",
                "probation_end_date": row["probation_end_date"],
                "created_at": row["created_at"],
                "last_updated": row["last_updated"] or row["created_at"],
            })

        upcoming = []
        next_court_date = None
        today = datetime.now().date().isoformat()
        for row in court_rows:
            hearing_date = row["hearing_date"]
            if hearing_date and hearing_date >= today:
                entry = {
                    "court_date_id": row["court_date_id"],
                    "case_id": row["case_id"],
                    "hearing_date": hearing_date,
                    "hearing_time": row["hearing_time"] or "",
                    "court_name": row["court_name"] or "",
                    "courtroom": row["courtroom"] or "",
                    "hearing_type": row["hearing_type"] or "",
                    "judge_name": row["judge_name"] or "",
                    "status": row["status"] or "Scheduled",
                    "reminder_sent": bool(row["reminder_sent"]),
                }
                upcoming.append(entry)
                if next_court_date is None:
                    next_court_date = entry

        summary["cases"] = cases
        summary["upcoming_court_dates"] = upcoming[:10]
        summary["total_cases"] = len(cases)
        summary["active_cases"] = sum(
            1 for case in cases
            if str(case["status"]).strip().lower() in {"active", "pending", "open"}
        )
        summary["next_court_date"] = next_court_date
        return summary
    except sqlite3.OperationalError:
        return summary
    except Exception as e:
        logger.error("Error getting legal summary for %s: %s", client_id, e)
        return summary


def get_client_services_summary(client_id: str) -> Dict[str, Any]:
    """Get services referral/task summary for unified client view."""
    summary = {
        "referrals": [],
        "tasks": [],
        "total_referrals": 0,
        "active_referrals": 0,
        "open_tasks": 0,
    }
    try:
        with get_database_connection("social_services", "READ_ONLY") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT r.referral_id, r.provider_id, r.service_id, r.referral_date,
                       r.priority_level, r.status, r.expected_start_date,
                       r.actual_start_date, r.completion_date, r.notes,
                       p.provider_name, s.service_name, s.service_category
                FROM service_referrals r
                LEFT JOIN service_providers p ON r.provider_id = p.provider_id
                LEFT JOIN social_services s ON r.service_id = s.service_id
                WHERE r.client_id = ?
                ORDER BY COALESCE(r.last_updated, r.created_at, r.referral_date) DESC
                """,
                (client_id,),
            )
            referral_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT task_id, task_type, title, description, priority, due_date,
                       status, completed_date, assigned_to
                FROM case_management_tasks
                WHERE client_id = ?
                ORDER BY COALESCE(due_date, last_updated, created_at) ASC
                """,
                (client_id,),
            )
            task_rows = cursor.fetchall()

        referrals = []
        for row in referral_rows:
            referrals.append({
                "referral_id": row["referral_id"],
                "provider_name": row["provider_name"] or "",
                "service_name": row["service_name"] or "",
                "service_category": row["service_category"] or "",
                "status": row["status"] or "Pending",
                "priority_level": row["priority_level"] or "Normal",
                "referral_date": row["referral_date"],
                "expected_start_date": row["expected_start_date"],
                "actual_start_date": row["actual_start_date"],
                "completion_date": row["completion_date"],
                "notes": row["notes"] or "",
            })

        tasks = []
        for row in task_rows:
            tasks.append({
                "task_id": row["task_id"],
                "task_type": row["task_type"] or "",
                "title": row["title"] or "",
                "description": row["description"] or "",
                "priority": row["priority"] or "Normal",
                "due_date": row["due_date"],
                "status": row["status"] or "Pending",
                "completed_date": row["completed_date"],
                "assigned_to": row["assigned_to"] or "",
            })

        summary["referrals"] = referrals[:10]
        summary["tasks"] = tasks[:10]
        summary["total_referrals"] = len(referrals)
        summary["active_referrals"] = sum(
            1 for referral in referrals
            if str(referral["status"]).strip().lower() in {"pending", "active", "in progress", "open"}
        )
        summary["open_tasks"] = sum(
            1 for task in tasks
            if str(task["status"]).strip().lower() not in {"completed", "done", "cancelled", "canceled"}
        )
        return summary
    except sqlite3.OperationalError:
        return summary
    except Exception as e:
        logger.error("Error getting services summary for %s: %s", client_id, e)
        return summary

class ClientCreateRequest(BaseModel):
    """Client creation schema - must match dependency map requirements"""
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    case_manager_id: str
    risk_level: str = "medium"
    intake_date: Optional[str] = None
    housing_status: Optional[str] = "unknown"
    employment_status: Optional[str] = "unknown"
    benefits_needed: Optional[List[str]] = Field(default_factory=list)
    legal_issues: Optional[List[str]] = Field(default_factory=list)
    background_check: Optional[str] = "pending"
    # Extended fields from the new client form
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    case_status: Optional[str] = "active"
    program_type: Optional[str] = None
    referral_source: Optional[str] = None
    prior_convictions: Optional[str] = None
    substance_abuse_history: Optional[str] = None
    mental_health_status: Optional[str] = None
    transportation: Optional[str] = None
    medical_conditions: Optional[str] = None
    special_needs: Optional[str] = None
    benefits_status: Optional[str] = None
    legal_status: Optional[str] = None
    goals: Optional[str] = None
    barriers: Optional[str] = None
    notes: Optional[str] = None
    progress: Optional[int] = None
    last_contact: Optional[str] = None
    next_followup: Optional[str] = None
    needs: Optional[List[str]] = Field(default_factory=list)
    background: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ClientResponse(BaseModel):
    """Client response schema - cannot change per dependency maps"""
    client_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    case_manager_id: str
    intake_date: str
    risk_level: str
    created_at: str
    integration_results: Dict[str, Any]


class ClientUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    case_manager_id: Optional[str] = None
    risk_level: Optional[str] = None
    case_status: Optional[str] = None
    intake_date: Optional[str] = None
    housing_status: Optional[str] = None
    employment_status: Optional[str] = None
    benefits_status: Optional[str] = None
    legal_status: Optional[str] = None
    program_type: Optional[str] = None
    referral_source: Optional[str] = None
    prior_convictions: Optional[str] = None
    substance_abuse_history: Optional[str] = None
    mental_health_status: Optional[str] = None
    transportation: Optional[str] = None
    medical_conditions: Optional[str] = None
    special_needs: Optional[str] = None
    goals: Optional[str] = None
    barriers: Optional[str] = None
    notes: Optional[str] = None
    progress: Optional[int] = None
    last_contact: Optional[str] = None
    next_followup: Optional[str] = None
    needs: Optional[List[str]] = None
    background: Optional[Dict[str, Any]] = None


class TreatmentPlanDraftRequest(BaseModel):
    source: str = "case_manager"
    context: Dict[str, Any] = Field(default_factory=dict)
    review_due_date: Optional[str] = None
    problems: Optional[List[Dict[str, Any]]] = None
    goals: Optional[List[Dict[str, Any]]] = None
    objectives: Optional[List[Dict[str, Any]]] = None
    interventions: Optional[List[Dict[str, Any]]] = None
    target_dates: Optional[List[str]] = None
    aftercare_plan: Optional[Dict[str, Any]] = None
    completion_criteria: Optional[List[str]] = None
    operational_needs: Optional[List[Dict[str, Any]]] = None


class TreatmentPlanUpdateRequest(BaseModel):
    review_due_date: Optional[str] = None
    problems: Optional[List[Dict[str, Any]]] = None
    goals: Optional[List[Dict[str, Any]]] = None
    objectives: Optional[List[Dict[str, Any]]] = None
    interventions: Optional[List[Dict[str, Any]]] = None
    target_dates: Optional[List[str]] = None
    aftercare_plan: Optional[Dict[str, Any]] = None
    completion_criteria: Optional[List[str]] = None
    operational_needs: Optional[List[Dict[str, Any]]] = None


def _get_normalized_client_or_404(client_id: str) -> Dict[str, Any]:
    with get_database_connection("core_clients", "READ_ONLY") as conn:
        ensure_core_clients_schema(conn)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
        row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")
    return normalize_client_record(row)


def _coerce_plan_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _build_treatment_plan_data(
    client: Dict[str, Any],
    payload: TreatmentPlanDraftRequest,
    suggestions: Dict[str, Any],
) -> Dict[str, Any]:
    operational_needs = payload.operational_needs or derive_operational_needs(client)
    barriers = client.get("barriers") or "Current barriers need case manager review"
    client_goal = client.get("goals") or "Improve stability and functioning"
    suggested_goal = suggestions.get("goal") or client_goal
    suggested_objective = suggestions.get("objective") or (
        "Client will complete at least one documented follow-up action each week."
    )
    suggested_interventions = suggestions.get("interventions") or []

    return {
        "source": payload.source or "case_manager",
        "review_due_date": payload.review_due_date,
        "problems": payload.problems if payload.problems is not None else [
            {
                "problem_id": f"problem_{uuid.uuid4().hex[:8]}",
                "domain": "case_management",
                "description": barriers,
                "source": "intake",
            }
        ],
        "goals": payload.goals if payload.goals is not None else [
            {
                "goal_id": f"goal_{uuid.uuid4().hex[:8]}",
                "description": suggested_goal,
                "status": "draft",
                "source": "ai_suggestion" if suggestions else "intake",
            }
        ],
        "objectives": payload.objectives if payload.objectives is not None else [
            {
                "objective_id": f"objective_{uuid.uuid4().hex[:8]}",
                "description": suggested_objective,
                "measure": "Weekly documented follow-up action and case manager review",
                "status": "draft",
                "source": "ai_suggestion" if suggestions else "intake",
            }
        ],
        "interventions": payload.interventions if payload.interventions is not None else [
            {
                "intervention_id": f"intervention_{uuid.uuid4().hex[:8]}",
                "description": intervention,
                "assigned_to": "case_manager",
                "status": "draft",
                "source": "ai_suggestion",
            }
            for intervention in _coerce_plan_list(suggested_interventions)
        ],
        "target_dates": payload.target_dates or [],
        "aftercare_plan": payload.aftercare_plan or {
            "summary": "Aftercare plan requires case manager review and client confirmation.",
            "source": "draft",
        },
        "completion_criteria": payload.completion_criteria or [
            "Client progress and service completion criteria require case manager review."
        ],
        "operational_needs": operational_needs,
        "raw_suggestions": suggestions,
    }

@router.post("/api/clients")
async def create_client(client_data: ClientCreateRequest, request: Request):
    """
    Create client in core_clients.db and propagate to all 9 databases
    CRITICAL: This is the master client creation endpoint
    Returns: { success: True, client: {...}, integration_results: {...} }
    """
    try:
        current_user = require_authenticated_user(request)
        # Generate unique client ID
        client_id = str(uuid.uuid4())
        current_time = datetime.now().isoformat()
        assigned_case_manager_id = effective_case_manager_id(current_user, client_data.case_manager_id)

        # Prepare client data for core database
        intake_date = client_data.intake_date or current_time.split('T')[0]
        
        # Step 1: Create in core_clients.db (MASTER DATABASE)
        with get_database_connection("core_clients", "ADMIN") as conn:
            ensure_core_clients_schema(conn)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO clients (
                    client_id, first_name, last_name, email, phone,
                    date_of_birth, case_manager_id, risk_level, intake_date, created_at,
                    housing_status, employment_status,
                    address, city, state, zip_code,
                    emergency_contact_name, emergency_contact_phone, emergency_contact_relationship,
                    case_status, program_type, referral_source,
                    prior_convictions, substance_abuse_history, mental_health_status,
                    transportation, medical_conditions, special_needs,
                    benefits_status, legal_status, goals, barriers, notes,
                    progress, last_contact, next_followup, needs, background,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                client_id, client_data.first_name, client_data.last_name,
                client_data.email, client_data.phone, client_data.date_of_birth,
                assigned_case_manager_id, client_data.risk_level,
                intake_date, current_time,
                client_data.housing_status, client_data.employment_status,
                client_data.address, client_data.city, client_data.state, client_data.zip_code,
                client_data.emergency_contact_name, client_data.emergency_contact_phone,
                client_data.emergency_contact_relationship,
                client_data.case_status or "active", client_data.program_type,
                client_data.referral_source, client_data.prior_convictions,
                client_data.substance_abuse_history, client_data.mental_health_status,
                client_data.transportation, client_data.medical_conditions,
                client_data.special_needs, client_data.benefits_status,
                client_data.legal_status, client_data.goals, client_data.barriers,
                client_data.notes, client_data.progress or 0, client_data.last_contact,
                client_data.next_followup,
                _serialize_json_field(client_data.needs or [], []),
                _serialize_json_field(client_data.background or {}, {}),
                current_time
            ))
            conn.commit()

            cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
            created = cursor.fetchone()

        normalized_created = normalize_client_record(created)
        client_sync_payload = build_client_sync_payload(normalized_created)
        
        # Step 2: Propagate to all module databases (synchronous to avoid blocking)
        integration_results = propagate_client_to_modules(client_id, client_sync_payload)

        # Step 3: Mirror write to Railway Postgres when configured
        railway_sync = upsert_client_to_postgres(
            client_data=client_sync_payload,
            integration_results=integration_results,
        )
        integration_results["railway_postgres"] = railway_sync
        
        # Return with success flag and proper format
        return {
            "success": True,
            "client": normalized_created,
            "integration_results": integration_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Client creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Client creation failed: {str(e)}"
        )

@router.get("/api/clients/{client_id}")
async def get_client(client_id: str, request: Request):
    """Retrieve client by ID - was returning 404"""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        with get_database_connection("core_clients", "READ_ONLY") as conn:
            ensure_core_clients_schema(conn)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))

            result = cursor.fetchone()
            if result is None:
                raise HTTPException(status_code=404, detail="Client not found")

            return normalize_client_record(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error retrieving client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/api/clients")
async def list_clients(request: Request, case_manager_id: Optional[str] = None, limit: int = Query(50, ge=1, le=1000)):
    """List clients with optional filtering
    Returns: { success: True, clients: [...], count: N }
    """
    try:
        current_user = require_authenticated_user(request)
        scoped_case_manager_id = effective_case_manager_id(current_user, case_manager_id)
        with get_database_connection("core_clients", "READ_ONLY") as conn:
            ensure_core_clients_schema(conn)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if scoped_case_manager_id:
                cursor.execute(
                    """
                    SELECT *
                    FROM clients
                    WHERE case_manager_id = ?
                    ORDER BY intake_date DESC, created_at DESC
                    LIMIT ?
                    """,
                    (scoped_case_manager_id, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT *
                    FROM clients
                    ORDER BY intake_date DESC, created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )

            results = cursor.fetchall()
            clients = [normalize_client_record(row) for row in results]

            return {
                "success": True,
                "clients": clients,
                "count": len(clients)
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error listing clients: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.put("/api/clients/{client_id}")
async def update_client(client_id: str, client_data: ClientUpdateRequest, request: Request):
    """Update a shared client record used across all module selectors."""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        updates = client_data.dict(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")

        with get_database_connection("core_clients", "ADMIN") as conn:
            ensure_core_clients_schema(conn)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
            existing = cursor.fetchone()
            if existing is None:
                raise HTTPException(status_code=404, detail="Client not found")

            normalized_updates = dict(updates)
            if "risk_level" in normalized_updates and normalized_updates["risk_level"]:
                normalized_updates["risk_level"] = str(normalized_updates["risk_level"]).strip().lower()
            if "case_status" in normalized_updates and normalized_updates["case_status"]:
                normalized_updates["case_status"] = str(normalized_updates["case_status"]).strip().lower()
            if "housing_status" in normalized_updates and normalized_updates["housing_status"]:
                normalized_updates["housing_status"] = str(normalized_updates["housing_status"]).strip()
            if "employment_status" in normalized_updates and normalized_updates["employment_status"]:
                normalized_updates["employment_status"] = str(normalized_updates["employment_status"]).strip()
            if "benefits_status" in normalized_updates and normalized_updates["benefits_status"]:
                normalized_updates["benefits_status"] = str(normalized_updates["benefits_status"]).strip()
            if "legal_status" in normalized_updates and normalized_updates["legal_status"]:
                normalized_updates["legal_status"] = str(normalized_updates["legal_status"]).strip()
            if "needs" in normalized_updates:
                normalized_updates["needs"] = _serialize_json_field(normalized_updates["needs"], [])
            if "background" in normalized_updates:
                normalized_updates["background"] = _serialize_json_field(normalized_updates["background"], {})
            if "case_manager_id" in normalized_updates:
                normalized_updates["case_manager_id"] = effective_case_manager_id(
                    current_user,
                    normalized_updates["case_manager_id"],
                )

            normalized_updates["updated_at"] = datetime.now().isoformat()
            set_clause = ", ".join(f"{column} = ?" for column in normalized_updates.keys())
            values = list(normalized_updates.values()) + [client_id]
            cursor.execute(f"UPDATE clients SET {set_clause} WHERE client_id = ?", values)
            conn.commit()

            cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
            updated = cursor.fetchone()

        normalized_updated = normalize_client_record(updated)
        client_sync_payload = build_client_sync_payload(normalized_updated)
        integration_results = propagate_client_to_modules(client_id, client_sync_payload)
        railway_sync = upsert_client_to_postgres(
            client_data=client_sync_payload,
            integration_results=integration_results,
        )
        integration_results["railway_postgres"] = railway_sync

        return {
            "success": True,
            "client": normalized_updated,
            "integration_results": integration_results,
            "message": "Client updated successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error updating client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/api/clients/{client_id}")
async def delete_client(client_id: str, request: Request):
    """Delete a shared client record and remove it from module sync tables."""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        deleted = False
        with get_database_connection("core_clients", "ADMIN") as conn:
            ensure_core_clients_schema(conn)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM clients WHERE client_id = ?", (client_id,))
            conn.commit()
            deleted = cursor.rowcount > 0

        if not deleted:
            raise HTTPException(status_code=404, detail="Client not found")

        for module in [
            "case_management", "housing", "benefits", "legal",
            "employment", "services", "reminders", "jobs"
        ]:
            try:
                with get_database_connection(module, "ADMIN") as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM clients WHERE client_id = ?", (client_id,))
                    conn.commit()
            except Exception:
                # Module databases are best-effort mirrors; do not fail core deletion.
                continue

        return {"success": True, "message": "Client deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error deleting client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/api/clients/{client_id}/unified-view")
async def get_client_unified_view(client_id: str, request: Request):
    """Get unified client view with all module data
    Returns: { success: True, client_data: { client: {...}, housing: {}, ... } }
    """
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        with get_database_connection("core_clients", "READ_ONLY") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))

            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Client not found")

        core_client = dict(result)

        overview_data = get_client_data_integrator().get_client_overview_data(client_id)
        benefits_summary = get_client_benefits_summary(client_id)
        legal_summary = get_client_legal_summary(client_id)
        services_summary = get_client_services_summary(client_id)

        return {
            "success": True,
            "client_data": {
                "client": core_client,
                "housing": {
                    "status": core_client.get("housing_status", "unknown"),
                },
                "employment": {
                    "status": core_client.get("employment_status", "unknown"),
                },
                "benefits": benefits_summary or {"status": core_client.get("benefits_status", "unknown")},
                "legal": legal_summary or {"status": core_client.get("legal_status", "No active cases")},
                "services": services_summary,
                "tasks": overview_data.get("tasks", []),
                "notes": overview_data.get("case_notes", []),
                "appointments": overview_data.get("appointments", []),
                "reminders": overview_data.get("reminders", []),
                "recent_activity": overview_data.get("recent_activity", []),
                "contact_history": overview_data.get("contact_history", []),
                "program_milestones": overview_data.get("program_milestones", []),
                "goals": overview_data.get("goals", []),
                "barriers": overview_data.get("barriers", []),
                "summary": overview_data.get("summary", {}),
            },
            "data_sources": {
                "client": "core_clients.db",
                "overview": "case_management.db + reminders.db",
                "benefits": "unified_platform.db",
                "legal": "legal_cases.db",
                "services": "social_services.db",
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting unified view for {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/clients/{client_id}/operational-context")
async def get_client_operational_context(client_id: str, request: Request):
    """Return the shared read-only client context used to prefill module workflows."""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        with get_database_connection("core_clients", "READ_ONLY") as conn:
            ensure_core_clients_schema(conn)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
            row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Client not found")

        client = normalize_client_record(row)

        try:
            overview_data = get_client_data_integrator().get_client_overview_data(client_id)
        except Exception as exc:
            logger.warning("Operational context overview unavailable for %s: %s", client_id, exc)
            overview_data = {}

        operational_context = build_client_operational_context(
            client,
            overview_data=overview_data,
            benefits_summary=get_client_benefits_summary(client_id),
            legal_summary=get_client_legal_summary(client_id),
            services_summary=get_client_services_summary(client_id),
        )

        return {
            "success": True,
            "operational_context": operational_context,
            "client": operational_context["client"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting operational context for {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/clients/{client_id}/treatment-plan")
async def get_client_treatment_plan(client_id: str, request: Request):
    """Return the current treatment plan plus plan history for a client."""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        plans = workspace_store.list_client_treatment_plans(client_id)
        current_plan = plans[0] if plans else None
        return {
            "success": True,
            "current_plan": current_plan,
            "plans": plans,
            "count": len(plans),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting treatment plan for {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/clients/{client_id}/treatment-plan/draft")
async def create_client_treatment_plan_draft(
    client_id: str,
    payload: TreatmentPlanDraftRequest,
    request: Request,
):
    """Create a structured draft treatment plan from intake and optional AI suggestions."""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        client = _get_normalized_client_or_404(client_id)

        from backend.modules.ai_documentation.service import documentation_ai_service

        suggestions = documentation_ai_service.generate_treatment_plan_suggestions(
            {
                "client_id": client_id,
                "client_name": client.get("full_name"),
                "context": {
                    **(payload.context or {}),
                    "client_goals": client.get("goals"),
                    "barriers": client.get("barriers"),
                    "needs": payload.operational_needs or derive_operational_needs(client),
                },
            }
        )
        plan_data = _build_treatment_plan_data(client, payload, suggestions)
        plan = workspace_store.create_treatment_plan_draft(
            client_id,
            created_by=current_user.case_manager_id,
            plan_data=plan_data,
        )
        return {
            "success": True,
            "plan": plan,
            "suggestions": suggestions,
            "message": "Draft treatment plan created. Approval is required before it becomes active.",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating treatment plan draft for {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/api/clients/{client_id}/treatment-plan/{plan_id}")
async def update_client_treatment_plan(
    client_id: str,
    plan_id: str,
    payload: TreatmentPlanUpdateRequest,
    request: Request,
):
    """Update a draft treatment plan. Active plans only allow review-date updates."""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        existing = workspace_store.get_treatment_plan(plan_id)
        if not existing or existing.get("client_id") != client_id:
            raise HTTPException(status_code=404, detail="Treatment plan not found")

        updated = workspace_store.update_treatment_plan(
            plan_id,
            {key: value for key, value in payload.model_dump().items() if value is not None},
        )
        return {
            "success": True,
            "plan": updated,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating treatment plan {plan_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/clients/{client_id}/treatment-plan/{plan_id}/approve")
async def approve_client_treatment_plan(client_id: str, plan_id: str, request: Request):
    """Approve a draft treatment plan and make it the active client plan."""
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        existing = workspace_store.get_treatment_plan(plan_id)
        if not existing or existing.get("client_id") != client_id:
            raise HTTPException(status_code=404, detail="Treatment plan not found")

        approved = workspace_store.approve_treatment_plan(plan_id, approved_by=current_user.case_manager_id)
        operational_needs = workspace_store.upsert_operational_needs(
            client_id,
            approved.get("operational_needs") or [],
            source="treatment_plan",
            source_id=plan_id,
            source_plan_id=plan_id,
        )
        created_tasks = workspace_store.create_tasks_from_operational_needs(
            client_id,
            operational_needs,
            source="treatment_plan",
            source_id=plan_id,
            assigned_to=current_user.full_name,
        )
        return {
            "success": True,
            "plan": approved,
            "operational_needs": operational_needs,
            "created_tasks": created_tasks,
            "created_task_count": len(created_tasks),
            "message": "Treatment plan approved and linked operational tasks generated.",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving treatment plan {plan_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/clients/{client_id}/intelligent-tasks")
async def get_intelligent_tasks(client_id: str, request: Request):
    """Get AI-generated intelligent tasks for client
    Returns: { success: True, tasks: [], recommendations: [] }
    """
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        if IntelligentTaskProcessor is None:
            return {
                "success": False,
                "error": "Intelligent task processor unavailable",
                "tasks": [],
                "recommendations": []
            }

        processor = IntelligentTaskProcessor()
        tasks = processor.get_client_tasks_from_database(client_id)
        # Never auto-generate tasks on GET — tasks are created via POST /api/reminders/start-process

        recommendations = [
            f"Complete {task['title']}" for task in tasks[:3] if task.get("title")
        ]

        return {
            "success": True,
            "tasks": tasks,
            "recommendations": recommendations,
            "count": len(tasks),
            "data_source": "reminders.db"
        }
    except Exception as e:
        logger.error(f"Error getting intelligent tasks: {e}")
        return {
            "success": False,
            "error": str(e),
            "tasks": [],
            "recommendations": []
        }

@router.get("/api/clients/{client_id}/search-recommendations")
async def get_search_recommendations(client_id: str, request: Request):
    """Get service search recommendations for client
    Returns: { success: True, recommendations: [] }
    """
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, client_id)
        with get_database_connection("core_clients", "READ_ONLY") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT first_name, last_name, housing_status, employment_status, risk_level
                FROM clients WHERE client_id = ?
            """, (client_id,))
            row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Client not found")

        _, _, housing_status, employment_status, risk_level = row

        recommendations = []
        if str(housing_status).lower() in {"unknown", "unstable", "homeless", "transitional"}:
            recommendations.append({
                "type": "housing",
                "query": "transitional housing affordable housing reentry support",
                "priority": "high",
                "reason": f"Housing status is {housing_status or 'unknown'}"
            })

        if str(employment_status).lower() in {"unknown", "unemployed", "seeking"}:
            recommendations.append({
                "type": "employment",
                "query": "background friendly jobs second chance employers",
                "priority": "high",
                "reason": f"Employment status is {employment_status or 'unknown'}"
            })

        recommendations.append({
            "type": "benefits",
            "query": "SNAP Medicaid general assistance application help",
            "priority": "medium" if str(risk_level).lower() != "high" else "high",
            "reason": f"Risk level is {risk_level or 'unknown'}"
        })

        return {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations)
        }
    except Exception as e:
        logger.error(f"Error getting search recommendations: {e}")
        return {
            "success": False,
            "error": str(e),
            "recommendations": []
        }

def propagate_client_to_modules(client_id: str, client_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Propagate client to all module databases (SYNCHRONOUS - no blocking)
    Must complete within 1 second
    """
    integration_results = {}
    
    # Module databases to sync to
    modules = [
        "case_management", "housing", "benefits", "legal", 
        "employment", "services", "reminders", "jobs"
    ]
    
    for module in modules:
        try:
            with get_database_connection(module, "ADMIN") as conn:
                cursor = conn.cursor()
                
                # Check if clients table exists, create if needed
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS clients (
                        client_id TEXT PRIMARY KEY,
                        full_name TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        phone TEXT,
                        email TEXT,
                        date_of_birth TEXT,
                        address TEXT,
                        city TEXT,
                        state TEXT,
                        zip_code TEXT,
                        emergency_contact_name TEXT,
                        emergency_contact_phone TEXT,
                        emergency_contact_relationship TEXT,
                        case_manager_id TEXT,
                        case_status TEXT,
                        intake_date TEXT,
                        admission_date TEXT,
                        risk_level TEXT,
                        housing_status TEXT,
                        employment_status TEXT,
                        benefits_status TEXT,
                        legal_status TEXT,
                        program_type TEXT,
                        referral_source TEXT,
                        prior_convictions TEXT,
                        substance_abuse_history TEXT,
                        mental_health_status TEXT,
                        transportation TEXT,
                        medical_conditions TEXT,
                        special_needs TEXT,
                        goals TEXT,
                        barriers TEXT,
                        notes TEXT,
                        progress INTEGER,
                        last_contact TEXT,
                        next_followup TEXT,
                        needs TEXT,
                        background TEXT,
                        created_at TEXT,
                        updated_at TEXT,
                        synced_at TEXT
                    )
                """)

                # Ensure legacy tables can accept sync metadata and core fields.
                cursor.execute("PRAGMA table_info(clients)")
                existing_columns = {row[1] for row in cursor.fetchall()}
                expected_columns = {
                    "full_name": "TEXT",
                    "first_name": "TEXT",
                    "last_name": "TEXT",
                    "phone": "TEXT",
                    "email": "TEXT",
                    "date_of_birth": "TEXT",
                    "address": "TEXT",
                    "city": "TEXT",
                    "state": "TEXT",
                    "zip_code": "TEXT",
                    "emergency_contact_name": "TEXT",
                    "emergency_contact_phone": "TEXT",
                    "emergency_contact_relationship": "TEXT",
                    "case_manager_id": "TEXT",
                    "case_status": "TEXT",
                    "intake_date": "TEXT",
                    "admission_date": "TEXT",
                    "risk_level": "TEXT",
                    "housing_status": "TEXT",
                    "employment_status": "TEXT",
                    "benefits_status": "TEXT",
                    "legal_status": "TEXT",
                    "program_type": "TEXT",
                    "referral_source": "TEXT",
                    "prior_convictions": "TEXT",
                    "substance_abuse_history": "TEXT",
                    "mental_health_status": "TEXT",
                    "transportation": "TEXT",
                    "medical_conditions": "TEXT",
                    "special_needs": "TEXT",
                    "goals": "TEXT",
                    "barriers": "TEXT",
                    "notes": "TEXT",
                    "progress": "INTEGER",
                    "last_contact": "TEXT",
                    "next_followup": "TEXT",
                    "needs": "TEXT",
                    "background": "TEXT",
                    "created_at": "TEXT",
                    "updated_at": "TEXT",
                    "synced_at": "TEXT",
                }
                for col_name, col_type in expected_columns.items():
                    if col_name not in existing_columns:
                        try:
                            cursor.execute(
                                f"ALTER TABLE clients ADD COLUMN {col_name} {col_type}"
                            )
                        except Exception:
                            # Some legacy tables may block alteration; continue with available cols.
                            pass

                cursor.execute("PRAGMA table_info(clients)")
                existing_columns = [row[1] for row in cursor.fetchall()]

                values_by_column = {
                    "client_id": client_id,
                    "full_name": client_data.get("full_name"),
                    "first_name": client_data.get("first_name"),
                    "last_name": client_data.get("last_name"),
                    "phone": client_data.get("phone"),
                    "email": client_data.get("email"),
                    "date_of_birth": client_data.get("date_of_birth"),
                    "address": client_data.get("address"),
                    "city": client_data.get("city"),
                    "state": client_data.get("state"),
                    "zip_code": client_data.get("zip_code"),
                    "emergency_contact_name": client_data.get("emergency_contact_name"),
                    "emergency_contact_phone": client_data.get("emergency_contact_phone"),
                    "emergency_contact_relationship": client_data.get("emergency_contact_relationship"),
                    "case_manager_id": client_data.get("case_manager_id"),
                    "case_status": client_data.get("case_status"),
                    "intake_date": client_data.get("intake_date"),
                    "admission_date": client_data.get("admission_date") or client_data.get("intake_date"),
                    "risk_level": client_data.get("risk_level"),
                    "housing_status": client_data.get("housing_status"),
                    "employment_status": client_data.get("employment_status"),
                    "benefits_status": client_data.get("benefits_status"),
                    "legal_status": client_data.get("legal_status"),
                    "program_type": client_data.get("program_type"),
                    "referral_source": client_data.get("referral_source"),
                    "prior_convictions": client_data.get("prior_convictions"),
                    "substance_abuse_history": client_data.get("substance_abuse_history"),
                    "mental_health_status": client_data.get("mental_health_status"),
                    "transportation": client_data.get("transportation"),
                    "medical_conditions": client_data.get("medical_conditions"),
                    "special_needs": client_data.get("special_needs"),
                    "goals": client_data.get("goals"),
                    "barriers": client_data.get("barriers"),
                    "notes": client_data.get("notes"),
                    "progress": client_data.get("progress"),
                    "last_contact": client_data.get("last_contact"),
                    "next_followup": client_data.get("next_followup"),
                    "needs": _serialize_json_field(client_data.get("needs"), []),
                    "background": _serialize_json_field(client_data.get("background"), {}),
                    "created_at": client_data.get("created_at"),
                    "updated_at": client_data.get("updated_at"),
                    "synced_at": datetime.now().isoformat(),
                }

                insert_columns = [c for c in values_by_column if c in existing_columns]
                if not insert_columns:
                    raise ValueError("No compatible clients columns for propagation")

                placeholders = ", ".join("?" for _ in insert_columns)
                columns_sql = ", ".join(insert_columns)
                values = [values_by_column[c] for c in insert_columns]
                
                # Upsert shared intake fields without deleting module-owned columns.
                update_columns = [c for c in insert_columns if c != "client_id"]
                if update_columns:
                    update_sql = ", ".join(f"{c} = excluded.{c}" for c in update_columns)
                    cursor.execute(
                        f"""
                        INSERT INTO clients ({columns_sql})
                        VALUES ({placeholders})
                        ON CONFLICT(client_id) DO UPDATE SET {update_sql}
                        """,
                        values,
                    )
                else:
                    cursor.execute(
                        f"""
                        INSERT OR IGNORE INTO clients ({columns_sql})
                        VALUES ({placeholders})
                        """,
                        values,
                    )
                
                conn.commit()
                integration_results[module] = "success"
                
        except Exception as e:
            logger.error(f"Failed to sync client {client_id} to {module}: {e}")
            integration_results[module] = f"error: {str(e)}"
    
    return integration_results
