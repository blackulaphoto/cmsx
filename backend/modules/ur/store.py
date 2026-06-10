from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .postgres_store import (
    ALLOWED_UR_EVENT_TYPES,
    ALLOWED_UR_STATUSES,
    _normalize_text,
    _to_int,
    _to_float,
    _parse_date,
    _sort_key,
)


class URStore:
    """SQLite persistence for Utilization Review case management."""

    def __init__(self, db_path: str = None):
        from backend.shared.db_path import DB_DIR
        db_path = db_path or str(DB_DIR / "ur.db")
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._setup()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
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

    def _setup(self) -> None:
        with self._db() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS railway_ur_cases (
                    case_id TEXT PRIMARY KEY,
                    client_id TEXT,
                    client_name TEXT NOT NULL,
                    assigned_case_manager TEXT NOT NULL,
                    payer TEXT NOT NULL,
                    member_id TEXT,
                    policy_group_number TEXT,
                    facility TEXT,
                    program TEXT,
                    current_level_of_care TEXT,
                    requested_level_of_care TEXT,
                    approved_level_of_care TEXT,
                    admit_date TEXT NOT NULL,
                    diagnosis TEXT,
                    asam_level TEXT,
                    auth_required INTEGER NOT NULL DEFAULT 1,
                    auth_number TEXT,
                    requested_days INTEGER NOT NULL DEFAULT 0,
                    approved_days INTEGER NOT NULL DEFAULT 0,
                    denied_days INTEGER NOT NULL DEFAULT 0,
                    approved_start_date TEXT,
                    approved_end_date TEXT,
                    next_review_date TEXT,
                    reviewer_name TEXT,
                    reviewer_company TEXT,
                    reviewer_phone TEXT,
                    reviewer_fax TEXT,
                    reviewer_email TEXT,
                    auth_submission_method TEXT,
                    decision_received_method TEXT,
                    clinical_criteria_used TEXT DEFAULT 'ASAM',
                    clinical_justification_summary TEXT,
                    denial_reason TEXT,
                    peer_review_deadline TEXT,
                    appeal_deadline TEXT,
                    revenue_at_risk_amount REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'auth_needed',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS railway_ur_review_events (
                    event_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES railway_ur_cases(case_id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    event_date TEXT NOT NULL,
                    status TEXT,
                    notes TEXT,
                    requested_days INTEGER NOT NULL DEFAULT 0,
                    approved_days INTEGER NOT NULL DEFAULT 0,
                    denied_days INTEGER NOT NULL DEFAULT 0,
                    approved_start_date TEXT,
                    approved_end_date TEXT,
                    reviewer_name TEXT,
                    reviewer_company TEXT,
                    reviewer_phone TEXT,
                    reviewer_fax TEXT,
                    reviewer_email TEXT,
                    auth_submission_method TEXT,
                    decision_received_method TEXT,
                    denial_reason TEXT,
                    peer_review_deadline TEXT,
                    appeal_deadline TEXT,
                    created_by TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_ur_cases_manager ON railway_ur_cases(assigned_case_manager);
                CREATE INDEX IF NOT EXISTS idx_ur_cases_next_review ON railway_ur_cases(next_review_date);
                CREATE INDEX IF NOT EXISTS idx_ur_cases_status ON railway_ur_cases(status);
                CREATE INDEX IF NOT EXISTS idx_ur_events_case ON railway_ur_review_events(case_id);
                """
            )

    def _normalize_case_payload(self, payload: Dict[str, Any], existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        requested_days = _to_int(payload.get("requested_days"), _to_int((existing or {}).get("requested_days"), 0))
        approved_days = _to_int(payload.get("approved_days"), _to_int((existing or {}).get("approved_days"), 0))
        denied_input = payload.get("denied_days")
        denied_days = _to_int(denied_input, _to_int((existing or {}).get("denied_days"), 0))
        if denied_input in (None, ""):
            denied_days = max(requested_days - approved_days, 0)
        status = _normalize_text(payload.get("status") or (existing or {}).get("status") or "auth_needed").lower()
        if status not in ALLOWED_UR_STATUSES:
            status = "auth_needed"
        return {
            "client_id": _normalize_text(payload.get("client_id") or (existing or {}).get("client_id")),
            "client_name": _normalize_text(payload.get("client_name") or (existing or {}).get("client_name")),
            "assigned_case_manager": _normalize_text(payload.get("assigned_case_manager") or (existing or {}).get("assigned_case_manager")),
            "payer": _normalize_text(payload.get("payer") or (existing or {}).get("payer")),
            "member_id": _normalize_text(payload.get("member_id") or (existing or {}).get("member_id")),
            "policy_group_number": _normalize_text(payload.get("policy_group_number") or (existing or {}).get("policy_group_number")),
            "facility": _normalize_text(payload.get("facility") or (existing or {}).get("facility")),
            "program": _normalize_text(payload.get("program") or (existing or {}).get("program")),
            "current_level_of_care": _normalize_text(payload.get("current_level_of_care") or (existing or {}).get("current_level_of_care")),
            "requested_level_of_care": _normalize_text(payload.get("requested_level_of_care") or (existing or {}).get("requested_level_of_care")),
            "approved_level_of_care": _normalize_text(payload.get("approved_level_of_care") or (existing or {}).get("approved_level_of_care")),
            "admit_date": _normalize_text(payload.get("admit_date") or (existing or {}).get("admit_date")),
            "diagnosis": _normalize_text(payload.get("diagnosis") or (existing or {}).get("diagnosis")),
            "asam_level": _normalize_text(payload.get("asam_level") or (existing or {}).get("asam_level")),
            "auth_required": 1 if payload.get("auth_required", (existing or {}).get("auth_required", True)) else 0,
            "auth_number": _normalize_text(payload.get("auth_number") or (existing or {}).get("auth_number")),
            "requested_days": requested_days,
            "approved_days": approved_days,
            "denied_days": denied_days,
            "approved_start_date": _normalize_text(payload.get("approved_start_date") or (existing or {}).get("approved_start_date")),
            "approved_end_date": _normalize_text(payload.get("approved_end_date") or (existing or {}).get("approved_end_date")),
            "next_review_date": _normalize_text(payload.get("next_review_date") or (existing or {}).get("next_review_date")),
            "reviewer_name": _normalize_text(payload.get("reviewer_name") or (existing or {}).get("reviewer_name")),
            "reviewer_company": _normalize_text(payload.get("reviewer_company") or (existing or {}).get("reviewer_company")),
            "reviewer_phone": _normalize_text(payload.get("reviewer_phone") or (existing or {}).get("reviewer_phone")),
            "reviewer_fax": _normalize_text(payload.get("reviewer_fax") or (existing or {}).get("reviewer_fax")),
            "reviewer_email": _normalize_text(payload.get("reviewer_email") or (existing or {}).get("reviewer_email")),
            "auth_submission_method": _normalize_text(payload.get("auth_submission_method") or (existing or {}).get("auth_submission_method")),
            "decision_received_method": _normalize_text(payload.get("decision_received_method") or (existing or {}).get("decision_received_method")),
            "clinical_criteria_used": _normalize_text(payload.get("clinical_criteria_used") or (existing or {}).get("clinical_criteria_used") or "ASAM"),
            "clinical_justification_summary": _normalize_text(payload.get("clinical_justification_summary") or (existing or {}).get("clinical_justification_summary")),
            "denial_reason": _normalize_text(payload.get("denial_reason") or (existing or {}).get("denial_reason")),
            "peer_review_deadline": _normalize_text(payload.get("peer_review_deadline") or (existing or {}).get("peer_review_deadline")),
            "appeal_deadline": _normalize_text(payload.get("appeal_deadline") or (existing or {}).get("appeal_deadline")),
            "revenue_at_risk_amount": _to_float(payload.get("revenue_at_risk_amount"), _to_float((existing or {}).get("revenue_at_risk_amount"), 0)),
            "status": status,
        }

    def _normalize_event_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        requested_days = _to_int(payload.get("requested_days"), 0)
        approved_days = _to_int(payload.get("approved_days"), 0)
        denied_input = payload.get("denied_days")
        denied_days = _to_int(denied_input, 0)
        if denied_input in (None, ""):
            denied_days = max(requested_days - approved_days, 0)
        event_type = _normalize_text(payload.get("event_type")).lower()
        if event_type not in ALLOWED_UR_EVENT_TYPES:
            raise ValueError("Unsupported UR event type")
        return {
            "event_type": event_type,
            "event_date": _normalize_text(payload.get("event_date")) or datetime.utcnow().isoformat(),
            "status": _normalize_text(payload.get("status")),
            "notes": _normalize_text(payload.get("notes")),
            "requested_days": requested_days,
            "approved_days": approved_days,
            "denied_days": denied_days,
            "approved_start_date": _normalize_text(payload.get("approved_start_date")),
            "approved_end_date": _normalize_text(payload.get("approved_end_date")),
            "reviewer_name": _normalize_text(payload.get("reviewer_name")),
            "reviewer_company": _normalize_text(payload.get("reviewer_company")),
            "reviewer_phone": _normalize_text(payload.get("reviewer_phone")),
            "reviewer_fax": _normalize_text(payload.get("reviewer_fax")),
            "reviewer_email": _normalize_text(payload.get("reviewer_email")),
            "auth_submission_method": _normalize_text(payload.get("auth_submission_method")),
            "decision_received_method": _normalize_text(payload.get("decision_received_method")),
            "denial_reason": _normalize_text(payload.get("denial_reason")),
            "peer_review_deadline": _normalize_text(payload.get("peer_review_deadline")),
            "appeal_deadline": _normalize_text(payload.get("appeal_deadline")),
        }

    def list_cases(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        query = "SELECT * FROM railway_ur_cases WHERE 1=1"
        params: List[Any] = []

        search = _normalize_text(filters.get("search")).lower()
        if search:
            query += """
                AND (
                    LOWER(COALESCE(client_name, '')) LIKE ?
                    OR LOWER(COALESCE(client_id, '')) LIKE ?
                    OR LOWER(COALESCE(payer, '')) LIKE ?
                    OR LOWER(COALESCE(program, '')) LIKE ?
                )
            """
            params.extend([f"%{search}%"] * 4)
        payer = _normalize_text(filters.get("payer")).lower()
        if payer:
            query += " AND LOWER(COALESCE(payer, '')) LIKE ?"
            params.append(f"%{payer}%")
        status = _normalize_text(filters.get("status")).lower()
        if status:
            query += " AND LOWER(COALESCE(status, '')) = ?"
            params.append(status)
        case_manager = _normalize_text(filters.get("case_manager"))
        if case_manager:
            query += " AND assigned_case_manager = ?"
            params.append(case_manager)

        query += " ORDER BY updated_at DESC"
        with self._db() as conn:
            rows = conn.execute(query, params).fetchall()
        cases = [dict(row) for row in rows]

        due_window = _normalize_text(filters.get("due_window")).lower()
        if due_window:
            today = datetime.utcnow().date()
            within_72 = today + timedelta(days=3)

            def matches(record: Dict[str, Any]) -> bool:
                next_review = _parse_date(record.get("next_review_date"))
                approved_end = _parse_date(record.get("approved_end_date"))
                appeal_deadline = _parse_date(record.get("appeal_deadline"))
                peer_review_deadline = _parse_date(record.get("peer_review_deadline"))
                record_status = _normalize_text(record.get("status")).lower()
                if due_window == "today":
                    return next_review == today
                if due_window == "72_hours":
                    return bool(next_review and today <= next_review <= within_72)
                if due_window == "auth_expiring":
                    return bool(approved_end and today <= approved_end <= within_72)
                if due_window == "denials":
                    return record_status == "denied" and (
                        (peer_review_deadline and peer_review_deadline >= today)
                        or (appeal_deadline and appeal_deadline >= today)
                    )
                if due_window == "appeals":
                    return record_status in {"denied", "appeal_pending"} and bool(appeal_deadline and appeal_deadline >= today)
                return True

            cases = [record for record in cases if matches(record)]
        return cases

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        with self._db() as conn:
            row = conn.execute("SELECT * FROM railway_ur_cases WHERE case_id = ?", (case_id,)).fetchone()
        return dict(row) if row else None

    def create_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        record = self._normalize_case_payload(payload)
        record.update(
            {
                "case_id": payload.get("case_id") or str(uuid.uuid4()),
                "created_at": now,
                "updated_at": now,
            }
        )
        columns = ", ".join(record.keys())
        placeholders = ", ".join("?" for _ in record)
        with self._db() as conn:
            conn.execute(f"INSERT INTO railway_ur_cases ({columns}) VALUES ({placeholders})", list(record.values()))
        return record

    def update_case(self, case_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        existing = self.get_case(case_id)
        if not existing:
            return None
        updates = self._normalize_case_payload(payload, existing)
        updates["updated_at"] = datetime.utcnow().isoformat()
        assignments = ", ".join(f"{key} = ?" for key in updates.keys())
        params = list(updates.values()) + [case_id]
        with self._db() as conn:
            conn.execute(f"UPDATE railway_ur_cases SET {assignments} WHERE case_id = ?", params)
        return self.get_case(case_id)

    def create_event(self, case_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        event = self._normalize_event_payload(payload)
        record = {
            "event_id": str(uuid.uuid4()),
            "case_id": case_id,
            "created_by": _normalize_text(payload.get("created_by")),
            "created_at": now,
            **event,
        }
        columns = ", ".join(record.keys())
        placeholders = ", ".join("?" for _ in record)
        with self._db() as conn:
            conn.execute(f"INSERT INTO railway_ur_review_events ({columns}) VALUES ({placeholders})", list(record.values()))
        return record

    def list_events(self, case_id: str) -> List[Dict[str, Any]]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT * FROM railway_ur_review_events WHERE case_id = ? ORDER BY event_date DESC, created_at DESC",
                (case_id,),
            ).fetchall()
        events = [dict(row) for row in rows]
        return sorted(events, key=_sort_key, reverse=True)

    def get_case_detail(self, case_id: str) -> Optional[Dict[str, Any]]:
        record = self.get_case(case_id)
        if not record:
            return None
        return {
            "case": record,
            "events": self.list_events(case_id),
        }

    def get_summary(self, case_manager_id: Optional[str] = None) -> Dict[str, Any]:
        cases = self.list_cases({"case_manager": case_manager_id} if case_manager_id else {})
        today = datetime.utcnow().date()
        within_72 = today + timedelta(days=3)

        reviews_due_today = 0
        due_in_72_hours = 0
        auth_expiring = 0
        denials_needing_action = 0
        appeals_due = 0
        revenue_at_risk = 0.0
        total_authorized_days = 0
        total_denied_days = 0
        approval_rates: List[float] = []

        for case in cases:
            requested_days = _to_int(case.get("requested_days"), 0)
            approved_days = _to_int(case.get("approved_days"), 0)
            denied_days = _to_int(case.get("denied_days"), max(requested_days - approved_days, 0))
            status = _normalize_text(case.get("status")).lower()
            next_review = _parse_date(case.get("next_review_date"))
            approved_end = _parse_date(case.get("approved_end_date"))
            peer_review_deadline = _parse_date(case.get("peer_review_deadline"))
            appeal_deadline = _parse_date(case.get("appeal_deadline"))

            total_authorized_days += approved_days
            total_denied_days += denied_days
            if requested_days > 0:
                approval_rates.append(approved_days / requested_days)
            if status != "closed":
                revenue_at_risk += _to_float(case.get("revenue_at_risk_amount"), 0)
            if next_review == today:
                reviews_due_today += 1
            if next_review and today <= next_review <= within_72:
                due_in_72_hours += 1
            if approved_end and today <= approved_end <= within_72:
                auth_expiring += 1
            if status == "denied" and (
                (peer_review_deadline and peer_review_deadline >= today)
                or (appeal_deadline and appeal_deadline >= today)
            ):
                denials_needing_action += 1
            if status in {"denied", "appeal_pending"} and appeal_deadline and appeal_deadline >= today:
                appeals_due += 1

        average_approval_rate = 0.0
        if approval_rates:
            average_approval_rate = sum(approval_rates) / len(approval_rates)

        return {
            "total_cases": len(cases),
            "total_authorized_days": total_authorized_days,
            "total_denied_days": total_denied_days,
            "average_approval_rate": average_approval_rate,
            "reviews_due_today": reviews_due_today,
            "due_in_72_hours": due_in_72_hours,
            "auth_expiring": auth_expiring,
            "denials_needing_action": denials_needing_action,
            "appeals_due": appeals_due,
            "revenue_at_risk": round(revenue_at_risk, 2),
            "cases": cases,
        }
