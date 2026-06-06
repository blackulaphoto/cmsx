from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from backend.shared.database.railway_fmla_postgres import _engine, ensure_postgres_fmla_tables

from .store import ACTIVE_FMLA_STATUSES, FMLAStore, _normalize_text


def _mappings(result) -> List[Dict[str, Any]]:
    return [dict(row) for row in result.mappings().all()]


class PostgresFMLAStore(FMLAStore):
    def __init__(self, reminders_db_path: str = "databases/reminders.db"):
        self.engine = _engine()
        self.reminders_db_path = Path(reminders_db_path)
        self.reminders_db_path.parent.mkdir(parents=True, exist_ok=True)
        ensure_postgres_fmla_tables()

    def _connect_reminders(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.reminders_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _reminders_db(self):
        conn = self._connect_reminders()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _fetchone(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        with self.engine.begin() as conn:
            row = conn.execute(text(query), params or {}).mappings().first()
        return dict(row) if row else None

    def _fetchall(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        with self.engine.begin() as conn:
            result = conn.execute(text(query), params or {})
            return _mappings(result)

    def _execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> None:
        with self.engine.begin() as conn:
            conn.execute(text(query), params or {})

    def list_cases(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        query = "SELECT * FROM railway_fmla_cases WHERE 1=1"
        params: Dict[str, Any] = {}

        search = _normalize_text(filters.get("search")).lower()
        if search:
            params["search"] = f"%{search}%"
            query += """
                AND (
                    LOWER(COALESCE(client_name, '')) LIKE :search
                    OR LOWER(COALESCE(staff_name, '')) LIKE :search
                    OR LOWER(COALESCE(staff_identifier, '')) LIKE :search
                    OR LOWER(COALESCE(employer_name, '')) LIKE :search
                    OR LOWER(COALESCE(assigned_case_manager, '')) LIKE :search
                )
            """

        status = _normalize_text(filters.get("status")).lower()
        if status:
            query += " AND LOWER(COALESCE(status, '')) = :status"
            params["status"] = status

        case_manager = _normalize_text(filters.get("case_manager"))
        if case_manager:
            query += " AND assigned_case_manager = :case_manager"
            params["case_manager"] = case_manager

        employer = _normalize_text(filters.get("employer")).lower()
        if employer:
            query += " AND LOWER(COALESCE(employer_name, '')) LIKE :employer"
            params["employer"] = f"%{employer}%"

        subject_type = _normalize_text(filters.get("case_subject_type")).lower()
        if subject_type:
            query += " AND LOWER(COALESCE(case_subject_type, 'client')) = :subject_type"
            params["subject_type"] = subject_type

        deadline = _normalize_text(filters.get("deadline"))
        if deadline == "next_7_days":
            today = datetime.now().date().isoformat()
            next_week = (datetime.now().date() + timedelta(days=7)).isoformat()
            params.update({
                "today": today,
                "next_week": next_week,
            })
            query += """
                AND (
                    (paperwork_deadline <> '' AND paperwork_deadline >= :today AND paperwork_deadline <= :next_week)
                    OR (employer_response_deadline <> '' AND employer_response_deadline >= :today AND employer_response_deadline <= :next_week)
                    OR (certification_expiration_date <> '' AND certification_expiration_date >= :today AND certification_expiration_date <= :next_week)
                    OR (return_to_work_date <> '' AND return_to_work_date >= :today AND return_to_work_date <= :next_week)
                )
            """
        elif deadline == "overdue":
            today = datetime.now().date().isoformat()
            params["today"] = today
            query += """
                AND (
                    (paperwork_deadline <> '' AND paperwork_deadline < :today)
                    OR (employer_response_deadline <> '' AND employer_response_deadline < :today)
                    OR (certification_expiration_date <> '' AND certification_expiration_date < :today)
                    OR (return_to_work_date <> '' AND return_to_work_date < :today)
                )
            """

        query += " ORDER BY updated_at DESC"
        return self._fetchall(query, params)

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        return self._fetchone("SELECT * FROM railway_fmla_cases WHERE case_id = :case_id", {"case_id": case_id})

    def create_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        subject_type = _normalize_text(payload.get("case_subject_type")).lower() or "client"
        record = {
            "case_id": payload.get("case_id") or str(uuid.uuid4()),
            "case_subject_type": subject_type,
            "client_id": _normalize_text(payload.get("client_id")),
            "client_name": _normalize_text(payload.get("client_name")),
            "staff_identifier": _normalize_text(payload.get("staff_identifier")),
            "staff_name": _normalize_text(payload.get("staff_name")),
            "staff_department": _normalize_text(payload.get("staff_department")),
            "staff_job_title": _normalize_text(payload.get("staff_job_title")),
            "date_of_birth": _normalize_text(payload.get("date_of_birth")),
            "assigned_case_manager": _normalize_text(payload.get("assigned_case_manager")) or "cm_001",
            "treatment_status": _normalize_text(payload.get("treatment_status")),
            "employer_name": _normalize_text(payload.get("employer_name")),
            "hr_contact_name": _normalize_text(payload.get("hr_contact_name")),
            "hr_phone": _normalize_text(payload.get("hr_phone")),
            "hr_email": _normalize_text(payload.get("hr_email")),
            "employer_fax": _normalize_text(payload.get("employer_fax")),
            "employer_address": _normalize_text(payload.get("employer_address")),
            "preferred_communication_method": _normalize_text(payload.get("preferred_communication_method")) or "phone",
            "provider_name": _normalize_text(payload.get("provider_name")),
            "clinic_name": _normalize_text(payload.get("clinic_name")),
            "provider_phone": _normalize_text(payload.get("provider_phone")),
            "provider_fax": _normalize_text(payload.get("provider_fax")),
            "provider_email": _normalize_text(payload.get("provider_email")),
            "provider_address": _normalize_text(payload.get("provider_address")),
            "roi_status": _normalize_text(payload.get("roi_status")) or "unknown",
            "fmla_request_type": _normalize_text(payload.get("fmla_request_type")) or "new request",
            "leave_type": _normalize_text(payload.get("leave_type")) or "continuous",
            "leave_start_date": _normalize_text(payload.get("leave_start_date")),
            "leave_end_date": _normalize_text(payload.get("leave_end_date")),
            "expected_return_date": _normalize_text(payload.get("expected_return_date")),
            "employer_response_deadline": _normalize_text(payload.get("employer_response_deadline")),
            "certification_expiration_date": _normalize_text(payload.get("certification_expiration_date")),
            "return_to_work_date": _normalize_text(payload.get("return_to_work_date")),
            "paperwork_deadline": _normalize_text(payload.get("paperwork_deadline")),
            "paperwork_received_date": _normalize_text(payload.get("paperwork_received_date")),
            "paperwork_completed_date": _normalize_text(payload.get("paperwork_completed_date")),
            "paperwork_sent_date": _normalize_text(payload.get("paperwork_sent_date")),
            "paperwork_sent_method": _normalize_text(payload.get("paperwork_sent_method")) or "fax",
            "confirmation_received": 1 if payload.get("confirmation_received") else 0,
            "approval_status": _normalize_text(payload.get("approval_status")) or "pending",
            "status": _normalize_text(payload.get("status")) or "draft",
            "notes": _normalize_text(payload.get("notes")),
            "internal_comments": _normalize_text(payload.get("internal_comments")),
            "created_at": now,
            "updated_at": now,
        }
        if subject_type == "staff":
            record["client_id"] = ""
            record["date_of_birth"] = ""
            record["treatment_status"] = ""
            record["roi_status"] = "not needed"
            if not record["client_name"]:
                record["client_name"] = record["staff_name"] or record["staff_identifier"] or "Staff case"

        columns = ", ".join(record.keys())
        values = ", ".join(f":{column}" for column in record.keys())
        self._execute(f"INSERT INTO railway_fmla_cases ({columns}) VALUES ({values})", record)
        return record

    def update_case(self, case_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        existing = self.get_case(case_id)
        if not existing:
            return None
        allowed = set(existing.keys()) - {"case_id", "created_at"}
        updates = {k: v for k, v in payload.items() if k in allowed}
        if "confirmation_received" in updates:
            updates["confirmation_received"] = 1 if updates["confirmation_received"] else 0
        if "case_subject_type" in updates:
            updates["case_subject_type"] = _normalize_text(updates["case_subject_type"]).lower() or "client"
        if (updates.get("case_subject_type") or existing.get("case_subject_type")) == "staff":
            updates["client_id"] = ""
            updates["date_of_birth"] = ""
            updates["treatment_status"] = ""
            if not _normalize_text(updates.get("client_name")):
                updates["client_name"] = _normalize_text(updates.get("staff_name")) or _normalize_text(existing.get("staff_name")) or "Staff case"
            updates.setdefault("roi_status", "not needed")
        updates["updated_at"] = datetime.utcnow().isoformat()
        assignments = ", ".join(f"{key} = :{key}" for key in updates.keys())
        params = {**updates, "case_id": case_id}
        self._execute(f"UPDATE railway_fmla_cases SET {assignments} WHERE case_id = :case_id", params)
        return self.get_case(case_id)

    def create_document(self, case_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        record = {
            "document_id": str(uuid.uuid4()),
            "case_id": case_id,
            "batch_id": _normalize_text(payload.get("batch_id")),
            "batch_name": _normalize_text(payload.get("batch_name")),
            "document_type": _normalize_text(payload.get("document_type")) or "other",
            "document_status": _normalize_text(payload.get("document_status")) or "needed",
            "uploader_name": _normalize_text(payload.get("uploader_name")),
            "uploader_case_manager_id": _normalize_text(payload.get("uploader_case_manager_id")),
            "file_name": _normalize_text(payload.get("file_name")),
            "file_path": _normalize_text(payload.get("file_path")),
            "file_size": int(payload.get("file_size") or 0),
            "content_type": _normalize_text(payload.get("content_type")),
            "date_requested": _normalize_text(payload.get("date_requested")),
            "date_received": _normalize_text(payload.get("date_received")),
            "date_completed": _normalize_text(payload.get("date_completed")),
            "date_sent": _normalize_text(payload.get("date_sent")),
            "sent_to": _normalize_text(payload.get("sent_to")),
            "sent_by": _normalize_text(payload.get("sent_by")),
            "confirmation_number": _normalize_text(payload.get("confirmation_number")),
            "notes": _normalize_text(payload.get("notes")),
            "created_at": now,
            "updated_at": now,
        }
        columns = ", ".join(record.keys())
        values = ", ".join(f":{column}" for column in record.keys())
        self._execute(f"INSERT INTO railway_fmla_documents ({columns}) VALUES ({values})", record)
        return record

    def list_documents(self, case_id: str) -> List[Dict[str, Any]]:
        return self._fetchall(
            "SELECT * FROM railway_fmla_documents WHERE case_id = :case_id ORDER BY created_at DESC",
            {"case_id": case_id},
        )

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        return self._fetchone(
            "SELECT * FROM railway_fmla_documents WHERE document_id = :document_id",
            {"document_id": document_id},
        )

    def create_correspondence(self, case_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        record = {
            "correspondence_id": str(uuid.uuid4()),
            "case_id": case_id,
            "correspondence_at": _normalize_text(payload.get("correspondence_at")) or now,
            "contact_type": _normalize_text(payload.get("contact_type")) or "phone",
            "person_contacted": _normalize_text(payload.get("person_contacted")),
            "organization": _normalize_text(payload.get("organization")),
            "contact_information": _normalize_text(payload.get("contact_information")),
            "summary": _normalize_text(payload.get("summary")),
            "outcome": _normalize_text(payload.get("outcome")),
            "next_step_needed": _normalize_text(payload.get("next_step_needed")),
            "follow_up_date": _normalize_text(payload.get("follow_up_date")),
            "staff_member": _normalize_text(payload.get("staff_member")) or "cm_001",
            "created_at": now,
        }
        columns = ", ".join(record.keys())
        values = ", ".join(f":{column}" for column in record.keys())
        self._execute(f"INSERT INTO railway_fmla_correspondence ({columns}) VALUES ({values})", record)
        return record

    def list_correspondence(self, case_id: str) -> List[Dict[str, Any]]:
        return self._fetchall(
            """
            SELECT * FROM railway_fmla_correspondence
            WHERE case_id = :case_id
            ORDER BY correspondence_at DESC, created_at DESC
            """,
            {"case_id": case_id},
        )

    def create_leave_usage(self, case_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        record = {
            "usage_id": str(uuid.uuid4()),
            "case_id": case_id,
            "usage_date": _normalize_text(payload.get("usage_date")) or datetime.utcnow().date().isoformat(),
            "duration_minutes": int(payload.get("duration_minutes") or 0),
            "reason_category": _normalize_text(payload.get("reason_category")) or "other",
            "notes": _normalize_text(payload.get("notes")),
            "created_at": now,
            "updated_at": now,
        }
        columns = ", ".join(record.keys())
        values = ", ".join(f":{column}" for column in record.keys())
        self._execute(f"INSERT INTO railway_fmla_leave_usage ({columns}) VALUES ({values})", record)
        return record

    def list_leave_usage(self, case_id: str) -> List[Dict[str, Any]]:
        return self._fetchall(
            "SELECT * FROM railway_fmla_leave_usage WHERE case_id = :case_id ORDER BY usage_date DESC, created_at DESC",
            {"case_id": case_id},
        )

    def create_export_record(self, case_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        record = {
            "export_id": str(uuid.uuid4()),
            "case_id": case_id,
            "export_type": _normalize_text(payload.get("export_type")) or "employer packet",
            "draft_title": _normalize_text(payload.get("draft_title")) or "FMLA Employer Packet",
            "draft_content": str(payload.get("draft_content") or "").strip(),
            "review_notes": _normalize_text(payload.get("review_notes")),
            "warning_text": str(payload.get("warning_text") or "").strip(),
            "safe_filename": _normalize_text(payload.get("safe_filename")),
            "file_path": _normalize_text(payload.get("file_path")),
            "content_type": _normalize_text(payload.get("content_type")) or "application/pdf",
            "created_by": _normalize_text(payload.get("created_by")),
            "reviewed_at": _normalize_text(payload.get("reviewed_at")),
            "created_at": now,
            "updated_at": now,
        }
        columns = ", ".join(record.keys())
        values = ", ".join(f":{column}" for column in record.keys())
        self._execute(f"INSERT INTO railway_fmla_exports ({columns}) VALUES ({values})", record)
        return record

    def update_export_record(self, export_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        existing = self.get_export_record(export_id)
        if not existing:
            return None
        allowed = set(existing.keys()) - {"export_id", "case_id", "created_at"}
        updates = {key: value for key, value in payload.items() if key in allowed}
        updates["updated_at"] = datetime.utcnow().isoformat()
        assignments = ", ".join(f"{key} = :{key}" for key in updates.keys())
        params = {**updates, "export_id": export_id}
        self._execute(f"UPDATE railway_fmla_exports SET {assignments} WHERE export_id = :export_id", params)
        return self.get_export_record(export_id)

    def list_export_records(self, case_id: str) -> List[Dict[str, Any]]:
        return self._fetchall(
            "SELECT * FROM railway_fmla_exports WHERE case_id = :case_id ORDER BY created_at DESC",
            {"case_id": case_id},
        )

    def get_export_record(self, export_id: str) -> Optional[Dict[str, Any]]:
        return self._fetchone(
            "SELECT * FROM railway_fmla_exports WHERE export_id = :export_id",
            {"export_id": export_id},
        )

    def create_reminder(self, case_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        case_record = self.get_case(case_id)
        if not case_record:
            raise ValueError("FMLA case not found")

        reminder_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        reminder_text = _normalize_text(payload.get("reminder_text"))
        reason = _normalize_text(payload.get("reason")) or reminder_text
        subject_name = self._case_display_name(case_record)
        message = f"FMLA [{case_record['status']}] {subject_name}: {reminder_text} (Case {case_id[:8]})"

        with self._reminders_db() as conn:
            conn.execute(
                """
                INSERT INTO active_reminders (
                    reminder_id,
                    client_id,
                    case_manager_id,
                    reminder_type,
                    message,
                    priority,
                    due_date,
                    status,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reminder_id,
                    case_record.get("client_id") or "",
                    _normalize_text(payload.get("case_manager_id")) or case_record.get("assigned_case_manager") or "cm_001",
                    "fmla",
                    message,
                    _normalize_text(payload.get("priority")) or "Medium",
                    _normalize_text(payload.get("due_date")),
                    "Active",
                    created_at,
                ),
            )

        self._execute(
            """
            INSERT INTO railway_fmla_case_reminders (case_id, reminder_id, reminder_reason, created_at)
            VALUES (:case_id, :reminder_id, :reminder_reason, :created_at)
            """,
            {
                "case_id": case_id,
                "reminder_id": reminder_id,
                "reminder_reason": reason,
                "created_at": created_at,
            },
        )

        return {
            "reminder_id": reminder_id,
            "case_id": case_id,
            "subject_name": subject_name,
            "status": case_record["status"],
            "message": message,
            "priority": _normalize_text(payload.get("priority")) or "Medium",
            "due_date": _normalize_text(payload.get("due_date")),
            "created_at": created_at,
        }

    def list_case_reminders(self, case_id: str) -> List[Dict[str, Any]]:
        mappings = self._fetchall(
            """
            SELECT reminder_id, reminder_reason, created_at
            FROM railway_fmla_case_reminders
            WHERE case_id = :case_id
            ORDER BY created_at DESC
            """,
            {"case_id": case_id},
        )
        if not mappings:
            return []

        reminder_ids = [row["reminder_id"] for row in mappings]
        placeholders = ",".join(["?"] * len(reminder_ids))
        with self._reminders_db() as conn:
            rows = conn.execute(
                f"""
                SELECT reminder_id, client_id, case_manager_id, reminder_type, message, priority, due_date, status, created_at
                FROM active_reminders
                WHERE reminder_id IN ({placeholders})
                ORDER BY created_at DESC
                """,
                reminder_ids,
            ).fetchall()
        reminder_map = {row["reminder_id"]: dict(row) for row in rows}
        results: List[Dict[str, Any]] = []
        for mapping in mappings:
            reminder = reminder_map.get(mapping["reminder_id"])
            if reminder:
                reminder["reminder_reason"] = mapping["reminder_reason"]
                results.append(reminder)
        return results

    def log_audit(self, action: str, actor_case_manager_id: str, actor_name: str, case_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        safe_metadata = metadata or {}
        record = {
            "audit_id": str(uuid.uuid4()),
            "case_id": case_id,
            "action": action,
            "actor_case_manager_id": _normalize_text(actor_case_manager_id) or "unknown",
            "actor_name": _normalize_text(actor_name),
            "metadata_json": json.dumps(safe_metadata, sort_keys=True),
            "created_at": now,
        }
        columns = ", ".join(record.keys())
        values = ", ".join(f":{column}" for column in record.keys())
        self._execute(f"INSERT INTO railway_fmla_audit_log ({columns}) VALUES ({values})", record)
        return record

    def list_audit_logs(self, case_id: str) -> List[Dict[str, Any]]:
        rows = self._fetchall(
            "SELECT * FROM railway_fmla_audit_log WHERE case_id = :case_id ORDER BY created_at DESC",
            {"case_id": case_id},
        )
        results: List[Dict[str, Any]] = []
        for item in rows:
            item["metadata"] = json.loads(item.pop("metadata_json", "{}") or "{}")
            results.append(item)
        return results

    def get_summary(self, case_manager_id: Optional[str] = None) -> Dict[str, Any]:
        cases = self.list_cases({"case_manager": case_manager_id} if case_manager_id else {})
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        deadlines_next_7 = 0
        missing_paperwork = 0
        needing_follow_up = 0
        approved = 0
        denied = 0
        for case in cases:
            deadline_fields = [
                case.get("paperwork_deadline"),
                case.get("employer_response_deadline"),
                case.get("certification_expiration_date"),
                case.get("return_to_work_date"),
            ]
            for deadline in deadline_fields:
                if not deadline:
                    continue
                try:
                    parsed = datetime.fromisoformat(deadline).date()
                except ValueError:
                    continue
                if today <= parsed <= next_week:
                    deadlines_next_7 += 1
                    break

            if not case.get("paperwork_received_date") or not case.get("paperwork_sent_date"):
                missing_paperwork += 1

            if _normalize_text(case.get("status")).lower() in {"pending documents", "submitted"}:
                needing_follow_up += 1

            if _normalize_text(case.get("approval_status")).lower() == "approved" or _normalize_text(case.get("status")).lower() == "approved":
                approved += 1
            if _normalize_text(case.get("approval_status")).lower() == "denied" or _normalize_text(case.get("status")).lower() == "denied":
                denied += 1

        return {
            "total_active_cases": sum(1 for case in cases if _normalize_text(case.get("status")).lower() in ACTIVE_FMLA_STATUSES),
            "deadlines_next_7_days": deadlines_next_7,
            "missing_paperwork": missing_paperwork,
            "needing_follow_up": needing_follow_up,
            "approved_cases": approved,
            "denied_cases": denied,
            "cases": cases,
        }

