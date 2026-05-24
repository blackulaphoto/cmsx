import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class FMLAStore:
    """SQLite persistence for FMLA case management."""

    def __init__(self, db_path: str = "databases/fmla.db", reminders_db_path: str = "databases/reminders.db"):
        self.db_path = Path(db_path)
        self.reminders_db_path = Path(reminders_db_path)
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
                    client_id TEXT,
                    client_name TEXT NOT NULL,
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
                    leave_start_date TEXT,
                    expected_return_date TEXT,
                    paperwork_deadline TEXT,
                    paperwork_received_date TEXT,
                    paperwork_completed_date TEXT,
                    paperwork_sent_date TEXT,
                    paperwork_sent_method TEXT,
                    confirmation_received INTEGER DEFAULT 0,
                    approval_status TEXT DEFAULT 'pending',
                    status TEXT DEFAULT 'Draft',
                    notes TEXT,
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

                CREATE INDEX IF NOT EXISTS idx_fmla_cases_status ON fmla_cases(status);
                CREATE INDEX IF NOT EXISTS idx_fmla_cases_client ON fmla_cases(client_id);
                CREATE INDEX IF NOT EXISTS idx_fmla_cases_deadline ON fmla_cases(paperwork_deadline);
                CREATE INDEX IF NOT EXISTS idx_fmla_documents_case ON fmla_documents(case_id);
                CREATE INDEX IF NOT EXISTS idx_fmla_correspondence_case ON fmla_correspondence(case_id);
                """
            )
            self._ensure_column(conn, "fmla_documents", "batch_id", "TEXT")
            self._ensure_column(conn, "fmla_documents", "batch_name", "TEXT")

    def _ensure_column(self, conn: sqlite3.Connection, table_name: str, column_name: str, column_sql: str) -> None:
        columns = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")

    def list_cases(
        self,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        filters = filters or {}
        query = "SELECT * FROM fmla_cases WHERE 1=1"
        params: List[Any] = []

        search = (filters.get("search") or "").strip().lower()
        if search:
            query += """
                AND (
                    LOWER(COALESCE(client_name, '')) LIKE ?
                    OR LOWER(COALESCE(employer_name, '')) LIKE ?
                    OR LOWER(COALESCE(assigned_case_manager, '')) LIKE ?
                )
            """
            like = f"%{search}%"
            params.extend([like, like, like])

        status = (filters.get("status") or "").strip()
        if status:
            query += " AND status = ?"
            params.append(status)

        case_manager = (filters.get("case_manager") or "").strip()
        if case_manager:
            query += " AND assigned_case_manager = ?"
            params.append(case_manager)

        employer = (filters.get("employer") or "").strip().lower()
        if employer:
            query += " AND LOWER(COALESCE(employer_name, '')) LIKE ?"
            params.append(f"%{employer}%")

        deadline = (filters.get("deadline") or "").strip()
        if deadline == "next_7_days":
            today = datetime.now().date().isoformat()
            next_week = (datetime.now().date() + timedelta(days=7)).isoformat()
            query += " AND paperwork_deadline >= ? AND paperwork_deadline <= ?"
            params.extend([today, next_week])
        elif deadline == "overdue":
            today = datetime.now().date().isoformat()
            query += " AND paperwork_deadline <> '' AND paperwork_deadline < ?"
            params.append(today)

        query += " ORDER BY CASE WHEN paperwork_deadline IS NULL OR paperwork_deadline = '' THEN 1 ELSE 0 END, paperwork_deadline ASC, updated_at DESC"

        with self._db() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        with self._db() as conn:
            row = conn.execute("SELECT * FROM fmla_cases WHERE case_id = ?", (case_id,)).fetchone()
        return dict(row) if row else None

    def create_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        case_id = payload.get("case_id") or str(uuid.uuid4())
        record = {
            "case_id": case_id,
            "client_id": payload.get("client_id", ""),
            "client_name": payload.get("client_name", ""),
            "date_of_birth": payload.get("date_of_birth", ""),
            "assigned_case_manager": payload.get("assigned_case_manager", "cm_001"),
            "treatment_status": payload.get("treatment_status", ""),
            "employer_name": payload.get("employer_name", ""),
            "hr_contact_name": payload.get("hr_contact_name", ""),
            "hr_phone": payload.get("hr_phone", ""),
            "hr_email": payload.get("hr_email", ""),
            "employer_fax": payload.get("employer_fax", ""),
            "employer_address": payload.get("employer_address", ""),
            "preferred_communication_method": payload.get("preferred_communication_method", ""),
            "provider_name": payload.get("provider_name", ""),
            "clinic_name": payload.get("clinic_name", ""),
            "provider_phone": payload.get("provider_phone", ""),
            "provider_fax": payload.get("provider_fax", ""),
            "provider_email": payload.get("provider_email", ""),
            "provider_address": payload.get("provider_address", ""),
            "roi_status": payload.get("roi_status", ""),
            "fmla_request_type": payload.get("fmla_request_type", "new request"),
            "leave_start_date": payload.get("leave_start_date", ""),
            "expected_return_date": payload.get("expected_return_date", ""),
            "paperwork_deadline": payload.get("paperwork_deadline", ""),
            "paperwork_received_date": payload.get("paperwork_received_date", ""),
            "paperwork_completed_date": payload.get("paperwork_completed_date", ""),
            "paperwork_sent_date": payload.get("paperwork_sent_date", ""),
            "paperwork_sent_method": payload.get("paperwork_sent_method", ""),
            "confirmation_received": 1 if payload.get("confirmation_received") else 0,
            "approval_status": payload.get("approval_status", "pending"),
            "status": payload.get("status", "Draft"),
            "notes": payload.get("notes", ""),
            "created_at": now,
            "updated_at": now,
        }
        columns = ", ".join(record.keys())
        placeholders = ", ".join(["?"] * len(record))
        with self._db() as conn:
            conn.execute(
                f"INSERT INTO fmla_cases ({columns}) VALUES ({placeholders})",
                list(record.values()),
            )
        return record

    def update_case(self, case_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        existing = self.get_case(case_id)
        if not existing:
            return None
        allowed = set(existing.keys()) - {"case_id", "created_at"}
        updates = {k: v for k, v in payload.items() if k in allowed}
        if "confirmation_received" in updates:
            updates["confirmation_received"] = 1 if updates["confirmation_received"] else 0
        updates["updated_at"] = datetime.utcnow().isoformat()
        assignments = ", ".join(f"{key} = ?" for key in updates.keys())
        params = list(updates.values()) + [case_id]
        with self._db() as conn:
            conn.execute(f"UPDATE fmla_cases SET {assignments} WHERE case_id = ?", params)
        return self.get_case(case_id)

    def create_document(self, case_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        record = {
            "document_id": str(uuid.uuid4()),
            "case_id": case_id,
            "batch_id": payload.get("batch_id", ""),
            "batch_name": payload.get("batch_name", ""),
            "document_type": payload.get("document_type", "other"),
            "document_status": payload.get("document_status", "needed"),
            "file_name": payload.get("file_name", ""),
            "file_path": payload.get("file_path", ""),
            "file_size": payload.get("file_size", 0),
            "content_type": payload.get("content_type", ""),
            "date_requested": payload.get("date_requested", ""),
            "date_received": payload.get("date_received", ""),
            "date_completed": payload.get("date_completed", ""),
            "date_sent": payload.get("date_sent", ""),
            "sent_to": payload.get("sent_to", ""),
            "sent_by": payload.get("sent_by", ""),
            "confirmation_number": payload.get("confirmation_number", ""),
            "notes": payload.get("notes", ""),
            "created_at": now,
            "updated_at": now,
        }
        columns = ", ".join(record.keys())
        placeholders = ", ".join(["?"] * len(record))
        with self._db() as conn:
            conn.execute(
                f"INSERT INTO fmla_documents ({columns}) VALUES ({placeholders})",
                list(record.values()),
            )
        return record

    def list_documents(self, case_id: str) -> List[Dict[str, Any]]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT * FROM fmla_documents WHERE case_id = ? ORDER BY created_at DESC",
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM fmla_documents WHERE document_id = ?",
                (document_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_correspondence(self, case_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        record = {
            "correspondence_id": str(uuid.uuid4()),
            "case_id": case_id,
            "correspondence_at": payload.get("correspondence_at") or now,
            "contact_type": payload.get("contact_type", "phone"),
            "person_contacted": payload.get("person_contacted", ""),
            "organization": payload.get("organization", ""),
            "contact_information": payload.get("contact_information", ""),
            "summary": payload.get("summary", ""),
            "outcome": payload.get("outcome", ""),
            "next_step_needed": payload.get("next_step_needed", ""),
            "follow_up_date": payload.get("follow_up_date", ""),
            "staff_member": payload.get("staff_member", "cm_001"),
            "created_at": now,
        }
        columns = ", ".join(record.keys())
        placeholders = ", ".join(["?"] * len(record))
        with self._db() as conn:
            conn.execute(
                f"INSERT INTO fmla_correspondence ({columns}) VALUES ({placeholders})",
                list(record.values()),
            )
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

    def create_reminder(self, case_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        case_record = self.get_case(case_id)
        if not case_record:
            raise ValueError("FMLA case not found")

        reminder_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        reminder_text = payload.get("reminder_text", "").strip()
        reason = payload.get("reason", "").strip() or reminder_text
        message = (
            f"FMLA [{case_record['status']}] {case_record['client_name']}: "
            f"{reminder_text} (Case {case_id[:8]})"
        )

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
                    payload.get("case_manager_id") or case_record.get("assigned_case_manager") or "cm_001",
                    "fmla",
                    message,
                    payload.get("priority", "Medium"),
                    payload.get("due_date", ""),
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
            "client_name": case_record["client_name"],
            "status": case_record["status"],
            "message": message,
            "priority": payload.get("priority", "Medium"),
            "due_date": payload.get("due_date", ""),
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

    def get_summary(self, case_manager_id: Optional[str] = None) -> Dict[str, Any]:
        cases = self.list_cases({"case_manager": case_manager_id} if case_manager_id else {})
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        active_statuses = {
            "Draft", "Waiting on client", "Waiting on employer", "Waiting on provider",
            "Paperwork received", "Paperwork sent", "Confirmation pending", "Extension needed"
        }
        deadlines_next_7 = 0
        missing_paperwork = 0
        needing_follow_up = 0
        approved = 0
        denied = 0
        for case in cases:
            deadline = case.get("paperwork_deadline") or ""
            if deadline:
                try:
                    parsed = datetime.fromisoformat(deadline).date()
                    if today <= parsed <= next_week:
                        deadlines_next_7 += 1
                except ValueError:
                    pass
            if not case.get("paperwork_received_date") or not case.get("paperwork_sent_date"):
                missing_paperwork += 1
            if case.get("status") in {"Waiting on client", "Waiting on employer", "Waiting on provider", "Confirmation pending", "Extension needed"}:
                needing_follow_up += 1
            if (case.get("approval_status") or "").lower() == "approved" or case.get("status") == "Approved":
                approved += 1
            if (case.get("approval_status") or "").lower() == "denied" or case.get("status") == "Denied":
                denied += 1

        return {
            "total_active_cases": sum(1 for case in cases if case.get("status") in active_statuses),
            "deadlines_next_7_days": deadlines_next_7,
            "missing_paperwork": missing_paperwork,
            "needing_follow_up": needing_follow_up,
            "approved_cases": approved,
            "denied_cases": denied,
            "cases": cases,
        }
