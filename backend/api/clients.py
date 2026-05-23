#!/usr/bin/env python3
"""
Client Management API - Core client creation and management endpoints
Fixes the missing client creation pipeline causing HTTP 405 errors
"""

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import sqlite3
import uuid
import json
from datetime import datetime
from pathlib import Path
from backend.shared.database.railway_postgres import upsert_client_to_postgres
from backend.api.client_data_integration import get_client_data_integrator

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
    email: str
    phone: str
    date_of_birth: Optional[str] = None
    case_manager_id: str
    risk_level: str = "medium"
    intake_date: Optional[str] = None
    housing_status: Optional[str] = "unknown"
    employment_status: Optional[str] = "unknown"
    benefits_needed: Optional[List[str]] = []
    legal_issues: Optional[List[str]] = []
    background_check: Optional[str] = "pending"

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

@router.post("/api/clients")
async def create_client(client_data: ClientCreateRequest):
    """
    Create client in core_clients.db and propagate to all 9 databases
    CRITICAL: This is the master client creation endpoint
    Returns: { success: True, client: {...}, integration_results: {...} }
    """
    try:
        # Generate unique client ID
        client_id = str(uuid.uuid4())
        current_time = datetime.now().isoformat()
        
        # Prepare client data for core database
        intake_date = client_data.intake_date or current_time.split('T')[0]
        
        # Step 1: Create in core_clients.db (MASTER DATABASE)
        with get_database_connection("core_clients", "ADMIN") as conn:
            ensure_core_clients_schema(conn)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO clients (
                    client_id, first_name, last_name, email, phone, 
                    date_of_birth, case_manager_id, risk_level, intake_date, created_at,
                    housing_status, employment_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                client_id, client_data.first_name, client_data.last_name,
                client_data.email, client_data.phone, client_data.date_of_birth,
                client_data.case_manager_id, client_data.risk_level,
                intake_date, current_time,
                client_data.housing_status, client_data.employment_status
            ))
            conn.commit()
        
        # Step 2: Propagate to all module databases (synchronous to avoid blocking)
        integration_results = propagate_client_to_modules(client_id, {
            "first_name": client_data.first_name,
            "last_name": client_data.last_name,
            "email": client_data.email,
            "case_manager_id": client_data.case_manager_id,
            "intake_date": intake_date,
            "risk_level": client_data.risk_level
        })

        # Step 3: Mirror write to Railway Postgres when configured
        railway_sync = upsert_client_to_postgres(
            client_data={
                "client_id": client_id,
                "first_name": client_data.first_name,
                "last_name": client_data.last_name,
                "email": client_data.email,
                "phone": client_data.phone,
                "case_manager_id": client_data.case_manager_id,
                "risk_level": client_data.risk_level,
                "intake_date": intake_date,
                "created_at": current_time,
            },
            integration_results=integration_results,
        )
        integration_results["railway_postgres"] = railway_sync
        
        # Return with success flag and proper format
        return {
            "success": True,
            "client": {
                "client_id": client_id,
                "first_name": client_data.first_name,
                "last_name": client_data.last_name,
                "email": client_data.email,
                "phone": client_data.phone,
                "case_manager_id": client_data.case_manager_id,
                "intake_date": intake_date,
                "risk_level": client_data.risk_level,
                "created_at": current_time
            },
            "integration_results": integration_results
        }
        
    except Exception as e:
        logger.error(f"Client creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Client creation failed: {str(e)}"
        )

@router.get("/api/clients/{client_id}")
async def get_client(client_id: str):
    """Retrieve client by ID - was returning 404"""
    try:
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
async def list_clients(case_manager_id: Optional[str] = None, limit: int = Query(50, ge=1, le=1000)):
    """List clients with optional filtering
    Returns: { success: True, clients: [...], count: N }
    """
    try:
        with get_database_connection("core_clients", "READ_ONLY") as conn:
            ensure_core_clients_schema(conn)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if case_manager_id:
                cursor.execute(
                    """
                    SELECT *
                    FROM clients
                    WHERE case_manager_id = ?
                    ORDER BY intake_date DESC, created_at DESC
                    LIMIT ?
                    """,
                    (case_manager_id, limit),
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
    except Exception as e:
        logger.error(f"Database error listing clients: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.put("/api/clients/{client_id}")
async def update_client(client_id: str, client_data: ClientUpdateRequest):
    """Update a shared client record used across all module selectors."""
    try:
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

            normalized_updates["updated_at"] = datetime.now().isoformat()
            set_clause = ", ".join(f"{column} = ?" for column in normalized_updates.keys())
            values = list(normalized_updates.values()) + [client_id]
            cursor.execute(f"UPDATE clients SET {set_clause} WHERE client_id = ?", values)
            conn.commit()

            cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
            updated = cursor.fetchone()

        return {
            "success": True,
            "client": normalize_client_record(updated),
            "message": "Client updated successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error updating client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/api/clients/{client_id}")
async def delete_client(client_id: str):
    """Delete a shared client record and remove it from module sync tables."""
    try:
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
async def get_client_unified_view(client_id: str):
    """Get unified client view with all module data
    Returns: { success: True, client_data: { client: {...}, housing: {}, ... } }
    """
    try:
        with get_database_connection("core_clients", "READ_ONLY") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT client_id, first_name, last_name, email, phone, 
                       case_manager_id, intake_date, risk_level, created_at,
                       housing_status, employment_status
                FROM clients WHERE client_id = ?
            """, (client_id,))
            
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Client not found")

        core_client = {
            "client_id": result[0],
            "first_name": result[1],
            "last_name": result[2],
            "email": result[3],
            "phone": result[4],
            "case_manager_id": result[5],
            "intake_date": result[6],
            "risk_level": result[7],
            "created_at": result[8],
            "housing_status": result[9],
            "employment_status": result[10]
        }

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
                "benefits": benefits_summary,
                "legal": legal_summary,
                "services": services_summary,
                "tasks": overview_data.get("tasks", []),
                "notes": overview_data.get("case_notes", []),
                "appointments": overview_data.get("appointments", []),
                "reminders": overview_data.get("reminders", []),
                "recent_activity": overview_data.get("recent_activity", []),
                "contact_history": overview_data.get("contact_history", []),
                "program_milestones": overview_data.get("program_milestones", []),
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

@router.get("/api/clients/{client_id}/intelligent-tasks")
async def get_intelligent_tasks(client_id: str):
    """Get AI-generated intelligent tasks for client
    Returns: { success: True, tasks: [], recommendations: [] }
    """
    try:
        if IntelligentTaskProcessor is None:
            return {
                "success": False,
                "error": "Intelligent task processor unavailable",
                "tasks": [],
                "recommendations": []
            }

        processor = IntelligentTaskProcessor()
        tasks = processor.get_client_tasks_from_database(client_id)
        if not tasks:
            tasks = processor.generate_and_persist_process_tasks(client_id)

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
async def get_search_recommendations(client_id: str):
    """Get service search recommendations for client
    Returns: { success: True, recommendations: [] }
    """
    try:
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
                        first_name TEXT,
                        last_name TEXT,
                        email TEXT,
                        case_manager_id TEXT,
                        intake_date TEXT,
                        risk_level TEXT,
                        synced_at TEXT
                    )
                """)

                # Ensure legacy tables can accept sync metadata and core fields.
                cursor.execute("PRAGMA table_info(clients)")
                existing_columns = {row[1] for row in cursor.fetchall()}
                expected_columns = {
                    "first_name": "TEXT",
                    "last_name": "TEXT",
                    "email": "TEXT",
                    "case_manager_id": "TEXT",
                    "intake_date": "TEXT",
                    "risk_level": "TEXT",
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
                    "first_name": client_data.get("first_name"),
                    "last_name": client_data.get("last_name"),
                    "email": client_data.get("email"),
                    "case_manager_id": client_data.get("case_manager_id"),
                    "intake_date": client_data.get("intake_date"),
                    "risk_level": client_data.get("risk_level"),
                    "synced_at": datetime.now().isoformat(),
                }

                insert_columns = [c for c in values_by_column if c in existing_columns]
                if not insert_columns:
                    raise ValueError("No compatible clients columns for propagation")

                placeholders = ", ".join("?" for _ in insert_columns)
                columns_sql = ", ".join(insert_columns)
                values = [values_by_column[c] for c in insert_columns]
                
                # Insert client data
                cursor.execute(
                    f"""
                    INSERT OR REPLACE INTO clients ({columns_sql})
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
