import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.auth.authorization import get_client_org_id, get_org_for_user_id
from backend.shared.tenancy import DEFAULT_ORG_ID


ACTIVE_FMLA_STATUSES = {
    "draft",
    "pending documents",
    "submitted",
    "approved",
}


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


class FMLAStore:
    """SQLite persistence for FMLA case management."""

    def __init__(self, db_path: str = None, reminders_db_path: str = None):
        from backend.shared.db_path import DB_DIR
        self.db_path = Path(db_path) if db_path else DB_DIR / "fmla.db"
        self.reminders_db_path = Path(reminders_db_path) if reminders_db_path else DB_DIR / "reminders.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._setup()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _connect_reminders(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.reminders_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _db(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @contextmanager
    def _reminders_db(self):
        conn = self._connect_reminders()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _setup(self) -> None:
        with self._db() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS fmla_cases (
                    case_id TEXT PRIMARY KEY,
                    case_subject_type TEXT NOT NULL DEFAULT 'client',
                    client_id TEXT,
                    client_name TEXT NOT NULL,
                    staff_identifier TEXT,
                    staff_name TEXT,
                    staff_department TEXT,
                    staff_job_title TEXT,
                    date_of_birth TEXT,
                    assigned_case_manager TEXT NOT NULL,
                    treatment_status TEXT,
                    employer_name TEXT,
                    hr_contact_name TEXT,
                    hr_phone TEXT,
                    hr_email TEXT,
                    employer_fax TEXT,
                    employer_address TEXT,
                    preferred_communication_method TEXT,
                    provider_name TEXT,
                    clinic_name TEXT,
                    provider_phone TEXT,
                    provider_fax TEXT,
                    provider_email TEXT,
                    provider_address TEXT,
                    roi_status TEXT,
                    fmla_request_type TEXT NOT NULL,
                    leave_type TEXT NOT NULL DEFAULT 'continuous',
                    leave_start_date TEXT,
                    leave_end_date TEXT,
                    expected_return_date TEXT,
                    employer_response_deadline TEXT,
                    certification_expiration_date TEXT,
                    return_to_work_date TEXT,
                    paperwork_deadline TEXT,
                    paperwork_received_date TEXT,
                    paperwork_completed_date TEXT,
                    paperwork_sent_date TEXT,
                    paperwork_sent_method TEXT,
                    confirmation_received INTEGER DEFAULT 0,
                    approval_status TEXT DEFAULT 'pending',
                    status TEXT DEFAULT 'draft',
                    notes TEXT,
                    internal_comments TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS fmla_documents (
                    document_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    batch_id TEXT,
                    batch_name TEXT,
                    document_type TEXT NOT NULL,
                    document_status TEXT NOT NULL,
                    uploader_name TEXT,
                    uploader_case_manager_id TEXT,
                    file_name TEXT,
                    file_path TEXT,
                    file_size INTEGER,
                    content_type TEXT,
                    date_requested TEXT,
                    date_received TEXT,
                    date_completed TEXT,
                    date_sent TEXT,
                    sent_to TEXT,
                    sent_by TEXT,
                    confirmation_number TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (case_id) REFERENCES fmla_cases(case_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS fmla_correspondence (
                    correspondence_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    correspondence_at TEXT NOT NULL,
                    contact_type TEXT NOT NULL,
                    person_contacted TEXT,
                    organization TEXT,
                    contact_information TEXT,
                    summary TEXT NOT NULL,
                    outcome TEXT,
                    next_step_needed TEXT,
                    follow_up_date TEXT,
                    staff_member TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (case_id) REFERENCES fmla_cases(case_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS fmla_case_reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL,
                    reminder_id TEXT NOT NULL UNIQUE,
                    reminder_reason TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (case_id) REFERENCES fmla_cases(case_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS fmla_leave_usage (
                    usage_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    usage_date TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    reason_category TEXT NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (case_id) REFERENCES fmla_cases(case_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS fmla_exports (
                    export_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    export_type TEXT NOT NULL,
                    draft_title TEXT NOT NULL,
                    draft_content TEXT NOT NULL,
                    review_notes TEXT,
                    warning_text TEXT,
                    safe_filename TEXT,
                    file_path TEXT,
                    content_type TEXT,
                    created_by TEXT,
                    reviewed_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (case_id) REFERENCES fmla_cases(case_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS fmla_audit_log (
                    audit_id TEXT PRIMARY KEY,
                    case_id TEXT,
                    action TEXT NOT NULL,
                    actor_case_manager_id TEXT NOT NULL,
                    actor_name TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (case_id) REFERENCES fmla_cases(case_id) ON DELETE SET NULL
                );

                """
            )
            self._ensure_column(conn, "fmla_cases", "case_subject_type", "TEXT NOT NULL DEFAULT 'client'")
            self._ensure_column(conn, "fmla_cases", "staff_identifier", "TEXT")
            self._ensure_column(conn, "fmla_cases", "staff_name", "TEXT")
            self._ensure_column(conn, "fmla_cases", "staff_department", "TEXT")
            self._ensure_column(conn, "fmla_cases", "staff_job_title", "TEXT")
            self._ensure_column(conn, "fmla_cases", "leave_type", "TEXT NOT NULL DEFAULT 'continuous'")
            self._ensure_column(conn, "fmla_cases", "leave_end_date", "TEXT")
            self._ensure_column(conn, "fmla_cases", "employer_response_deadline", "TEXT")
            self._ensure_column(conn, "fmla_cases", "certification_expiration_date", "TEXT")
            self._ensure_column(conn, "fmla_cases", "return_to_work_date", "TEXT")
            self._ensure_column(conn, "fmla_cases", "internal_comments", "TEXT")
            self._ensure_column(conn, "fmla_documents", "batch_id", "TEXT")
            self._ensure_column(conn, "fmla_documents", "batch_name", "TEXT")
            self._ensure_column(conn, "fmla_documents", "uploader_name", "TEXT")
            self._ensure_column(conn, "fmla_documents", "uploader_case_manager_id", "TEXT")
            # Phase 3D4 multi-tenancy: additive nullable org_id on fmla_cases.
            self._ensure_column(conn, "fmla_cases", "org_id", "TEXT")
            conn.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_fmla_cases_status ON fmla_cases(status);
                CREATE INDEX IF NOT EXISTS idx_fmla_cases_client ON fmla_cases(client_id);
                CREATE INDEX IF NOT EXISTS idx_fmla_cases_deadline ON fmla_cases(paperwork_deadline);
                CREATE INDEX IF NOT EXISTS idx_fmla_cases_subject ON fmla_cases(case_subject_type);
                CREATE INDEX IF NOT EXISTS idx_fmla_cases_org ON fmla_cases(org_id);
                CREATE INDEX IF NOT EXISTS idx_fmla_documents_case ON fmla_documents(case_id);
                CREATE INDEX IF NOT EXISTS idx_fmla_correspondence_case ON fmla_correspondence(case_id);
                CREATE INDEX IF NOT EXISTS idx_fmla_leave_usage_case ON fmla_leave_usage(case_id, usage_date DESC);
                CREATE INDEX IF NOT EXISTS idx_fmla_exports_case ON fmla_exports(case_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_fmla_audit_case ON fmla_audit_log(case_id, created_at DESC);
                """
            )
            self._backfill_org_ids(conn)

    def _backfill_org_ids(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute(
            "SELECT case_id, client_id, assigned_case_manager FROM fmla_cases "
            "WHERE org_id IS NULL OR TRIM(org_id) = ''"
        ).fetchall()
        for row in rows:
            org_id = self._resolve_org_for_case(row["client_id"], row["assigned_case_manager"])
            conn.execute("UPDATE fmla_cases SET org_id = ? WHERE case_id = ?", (org_id, row["case_id"]))
        conn.execute(
            "UPDATE fmla_cases SET org_id = ? WHERE org_id IS NULL OR TRIM(org_id) = ''",
            (DEFAULT_ORG_ID,),
        )

    def _resolve_org_for_case(self, client_id: Optional[str], case_manager_id: Optional[str]) -> str:
        client_org = get_client_org_id(_normalize_text(client_id))
        if client_org:
            return client_org
        staff_org = get_org_for_user_id(_normalize_text(case_manager_id))
        if staff_org:
            return staff_org
        return DEFAULT_ORG_ID

    def _ensure_column(self, conn: sqlite3.Connection, table_name: str, column_name: str, column_sql: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
        if column_name not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")

    def _case_display_name(self, record: Dict[str, Any]) -> str:
        if _normalize_text(record.get("case_subject_type")).lower() == "staff":
            return _normalize_text(record.get("staff_name")) or _normalize_text(record.get("staff_identifier")) or "Staff case"
        return _normalize_text(record.get("client_name")) or _normalize_text(record.get("client_id")) or "Client case"

    def _safe_identifier(self, record: Dict[str, Any]) -> str:
        raw = (
            _normalize_text(record.get("staff_identifier"))
            or _normalize_text(record.get("client_id"))
            or _normalize_text(record.get("case_id"))[:8]
            or "record"
        )
        return re.sub(r"[^A-Za-z0-9_-]+", "-", raw).strip("-").lower() or "record"

    def build_safe_export_filename(self, record: Dict[str, Any], export_type: str, created_at: Optional[str] = None) -> str:
        date_part = (created_at or datetime.utcnow().date().isoformat())[:10]
        subject = _normalize_text(record.get("case_subject_type")).lower() or "case"
        identifier = self._safe_identifier(record)
        leave_type = re.sub(r"[^A-Za-z0-9_-]+", "-", _normalize_text(record.get("leave_type")).lower() or "leave").strip("-")
        export_slug = re.sub(r"[^A-Za-z0-9_-]+", "-", _normalize_text(export_type).lower() or "packet").strip("-")
        return f"{subject}-{identifier}-{leave_type}-{export_slug}-{date_part}.pdf"

    def list_cases(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        query = "SELECT * FROM fmla_cases WHERE 1=1"
        params: List[Any] = []

        search = _normalize_text(filters.get("search")).lower()
        if search:
            query += """
                AND (
                    LOWER(COALESCE(client_name, '')) LIKE ?
                    OR LOWER(COALESCE(staff_name, '')) LIKE ?
                    OR LOWER(COALESCE(staff_identifier, '')) LIKE ?
                    OR LOWER(COALESCE(employer_name, '')) LIKE ?
                    OR LOWER(COALESCE(assigned_case_manager, '')) LIKE ?
                )
            """
            like = f"%{search}%"
            params.extend([like, like, like, like, like])

        status = _normalize_text(filters.get("status"))
        if status:
            query += " AND LOWER(COALESCE(status, '')) = ?"
            params.append(status.lower())

        case_manager = _normalize_text(filters.get("case_manager"))
        if case_manager:
            query += " AND assigned_case_manager = ?"
            params.append(case_manager)

        # Phase 3D4: org filter applied only when supplied (flag on).
        org_id = filters.get("org_id")
        if org_id is not None:
            query += " AND org_id = ?"
            params.append(org_id)

        employer = _normalize_text(filters.get("employer")).lower()
        if employer:
            query += " AND LOWER(COALESCE(employer_name, '')) LIKE ?"
            params.append(f"%{employer}%")

        subject_type = _normalize_text(filters.get("case_subject_type")).lower()
        if subject_type:
            query += " AND LOWER(COALESCE(case_subject_type, 'client')) = ?"
            params.append(subject_type)

        deadline = _normalize_text(filters.get("deadline"))
        if deadline == "next_7_days":
            today = datetime.now().date().isoformat()
            next_week = (datetime.now().date() + timedelta(days=7)).isoformat()
            query += """
                AND (
                    (paperwork_deadline <> '' AND paperwork_deadline >= ? AND paperwork_deadline <= ?)
                    OR (employer_response_deadline <> '' AND employer_response_deadline >= ? AND employer_response_deadline <= ?)
                    OR (certification_expiration_date <> '' AND certification_expiration_date >= ? AND certification_expiration_date <= ?)
                    OR (return_to_work_date <> '' AND return_to_work_date >= ? AND return_to_work_date <= ?)
                )
            """
            params.extend([today, next_week, today, next_week, today, next_week, today, next_week])
        elif deadline == "overdue":
            today = datetime.now().date().isoformat()
            query += """
                AND (
                    (paperwork_deadline <> '' AND paperwork_deadline < ?)
                    OR (employer_response_deadline <> '' AND employer_response_deadline < ?)
                    OR (certification_expiration_date <> '' AND certification_expiration_date < ?)
                    OR (return_to_work_date <> '' AND return_to_work_date < ?)
                )
            """
            params.extend([today, today, today, today])

        query += " ORDER BY updated_at DESC"

        with self._db() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        with self._db() as conn:
            row = conn.execute("SELECT * FROM fmla_cases WHERE case_id = ?", (case_id,)).fetchone()
        return dict(row) if row else None

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
            "org_id": _normalize_text(payload.get("org_id")) or DEFAULT_ORG_ID,
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
        placeholders = ", ".join(["?"] * len(record))
        with self._db() as conn:
            conn.execute(f"INSERT INTO fmla_cases ({columns}) VALUES ({placeholders})", list(record.values()))
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
        assignments = ", ".join(f"{key} = ?" for key in updates.keys())
        params = list(updates.values()) + [case_id]
        with self._db() as conn:
            conn.execute(f"UPDATE fmla_cases SET {assignments} WHERE case_id = ?", params)
        return self.get_case(case_id)

    def delete_case(self, case_id: str) -> bool:
        existing = self.get_case(case_id)
        if not existing:
            return False
        with self._db() as conn:
            conn.execute("DELETE FROM fmla_cases WHERE case_id = ?", (case_id,))
        return True

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
        placeholders = ", ".join(["?"] * len(record))
        with self._db() as conn:
            conn.execute(f"INSERT INTO fmla_documents ({columns}) VALUES ({placeholders})", list(record.values()))
        return record

    def list_documents(self, case_id: str) -> List[Dict[str, Any]]:
        with self._db() as conn:
            rows = conn.execute("SELECT * FROM fmla_documents WHERE case_id = ? ORDER BY created_at DESC", (case_id,)).fetchall()
        return [dict(row) for row in rows]

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        with self._db() as conn:
            row = conn.execute("SELECT * FROM fmla_documents WHERE document_id = ?", (document_id,)).fetchone()
        return dict(row) if row else None

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
        placeholders = ", ".join(["?"] * len(record))
        with self._db() as conn:
            conn.execute(f"INSERT INTO fmla_correspondence ({columns}) VALUES ({placeholders})", list(record.values()))
        return record

    def list_correspondence(self, case_id: str) -> List[Dict[str, Any]]:
        with self._db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM fmla_correspondence
                WHERE case_id = ?
                ORDER BY correspondence_at DESC, created_at DESC
                """,
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]

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
        placeholders = ", ".join(["?"] * len(record))
        with self._db() as conn:
            conn.execute(f"INSERT INTO fmla_leave_usage ({columns}) VALUES ({placeholders})", list(record.values()))
        return record

    def list_leave_usage(self, case_id: str) -> List[Dict[str, Any]]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT * FROM fmla_leave_usage WHERE case_id = ? ORDER BY usage_date DESC, created_at DESC",
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_leave_usage_summary(self, case_id: str) -> Dict[str, Any]:
        entries = self.list_leave_usage(case_id)
        total_minutes = sum(int(entry.get("duration_minutes") or 0) for entry in entries)
        return {
            "entry_count": len(entries),
            "total_minutes": total_minutes,
            "total_hours": round(total_minutes / 60, 2),
        }

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
        placeholders = ", ".join(["?"] * len(record))
        with self._db() as conn:
            conn.execute(f"INSERT INTO fmla_exports ({columns}) VALUES ({placeholders})", list(record.values()))
        return record

    def update_export_record(self, export_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        existing = self.get_export_record(export_id)
        if not existing:
            return None
        allowed = set(existing.keys()) - {"export_id", "case_id", "created_at"}
        updates = {key: value for key, value in payload.items() if key in allowed}
        updates["updated_at"] = datetime.utcnow().isoformat()
        assignments = ", ".join(f"{key} = ?" for key in updates.keys())
        params = list(updates.values()) + [export_id]
        with self._db() as conn:
            conn.execute(f"UPDATE fmla_exports SET {assignments} WHERE export_id = ?", params)
        return self.get_export_record(export_id)

    def list_export_records(self, case_id: str) -> List[Dict[str, Any]]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT * FROM fmla_exports WHERE case_id = ? ORDER BY created_at DESC",
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_export_record(self, export_id: str) -> Optional[Dict[str, Any]]:
        with self._db() as conn:
            row = conn.execute("SELECT * FROM fmla_exports WHERE export_id = ?", (export_id,)).fetchone()
        return dict(row) if row else None

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

        with self._db() as conn:
            conn.execute(
                """
                INSERT INTO fmla_case_reminders (case_id, reminder_id, reminder_reason, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (case_id, reminder_id, reason, created_at),
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
        with self._db() as conn:
            mappings = conn.execute(
                """
                SELECT reminder_id, reminder_reason, created_at
                FROM fmla_case_reminders
                WHERE case_id = ?
                ORDER BY created_at DESC
                """,
                (case_id,),
            ).fetchall()
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
        placeholders = ", ".join(["?"] * len(record))
        with self._db() as conn:
            conn.execute(f"INSERT INTO fmla_audit_log ({columns}) VALUES ({placeholders})", list(record.values()))
        return record

    def list_audit_logs(self, case_id: str) -> List[Dict[str, Any]]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT * FROM fmla_audit_log WHERE case_id = ? ORDER BY created_at DESC",
                (case_id,),
            ).fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["metadata"] = json.loads(item.pop("metadata_json", "{}") or "{}")
            results.append(item)
        return results

    def get_summary(self, case_manager_id: Optional[str] = None, org_id: Optional[str] = None) -> Dict[str, Any]:
        filters: Dict[str, Any] = {}
        if case_manager_id:
            filters["case_manager"] = case_manager_id
        if org_id is not None:
            filters["org_id"] = org_id
        cases = self.list_cases(filters)
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
