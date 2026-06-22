"""Support Queue storage layer (SQLite, additive, PHI-safe).

One idempotent ``support_tickets`` table tracks internal support issues — bugs,
account questions, billing questions, feature requests, usability notes, etc. The
store resolves its database path from ``backend.shared.db_path.DB_DIR`` *at call
time* (not import time) so the SaaS harness / tests can repoint ``DB_DIR`` at a
tmp dir without touching the tracked ``databases/*.db`` files.

Hard safety rules:
  * No protected client content is ever stored here. Ticket text is the user's own
    description of *their* issue, length-capped. Any structured ``extra`` metadata
    is sanitized before write — PHI-looking keys are dropped (mirroring the
    analytics store), values are coerced to safe scalars and length-capped.
  * Lifecycle fields (status / assigned_to / internal_notes) are owner-only; the
    create path never accepts them (the route model omits them and the store
    forces safe defaults).
  * The "billing" category is just a tag. No Stripe code is reachable from here.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import backend.shared.db_path as db_path_mod

logger = logging.getLogger(__name__)

DB_FILENAME = "support.db"

# ── Controlled vocabularies ──────────────────────────────────────────────────
# Fixed allowlists. The route layer rejects anything not in these sets so the
# table only ever holds known values (no free-form category/priority/status).
CATEGORIES = (
    "bug",
    "account",
    "billing",
    "feature_request",
    "usability",
    "other",
)
PRIORITIES = ("low", "normal", "high", "urgent")
STATUSES = ("open", "in_progress", "waiting", "resolved", "closed")

# Statuses that represent a finished ticket. Reaching one of these stamps
# ``resolved_at``; moving away from them clears it.
TERMINAL_STATUSES = ("resolved", "closed")

DEFAULT_CATEGORY = "other"
DEFAULT_PRIORITY = "normal"
DEFAULT_STATUS = "open"

# ── Field caps ───────────────────────────────────────────────────────────────
MAX_SUBJECT_LEN = 200
MAX_DESCRIPTION_LEN = 5000
MAX_ASSIGNED_LEN = 200
MAX_INTERNAL_NOTES_LEN = 5000
MAX_ID_FIELD_LEN = 128
MAX_EMAIL_LEN = 320
MAX_RECENT = 50

# ── PHI / protected-content guard for structured metadata ────────────────────
# Substring tokens that mark a metadata key as PHI / protected client content.
# Case-insensitive, substring-based (so ``client_name``, ``patient_dob`` are all
# caught). Aggressive on purpose — a support ticket never needs any of these.
PHI_FORBIDDEN_KEY_TOKENS = (
    "name",
    "first",
    "last",
    "ssn",
    "dob",
    "birth",
    "diagnos",
    "note",
    "message",
    "msg",
    "body",
    "content",
    "document",
    "doc_",
    "address",
    "phone",
    "mrn",
    "medical",
    "medication",
    "prescription",
    "client",
    "patient",
    "insurance",
    "memo",
)
MAX_METADATA_KEYS = 12
MAX_METADATA_VALUE_LEN = 200


def _trim(value: Optional[str], limit: int) -> Optional[str]:
    """Trim a free-text scalar to ``limit`` chars; empty / None → None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:limit]


def _key_is_phi(key: str) -> bool:
    low = str(key).lower()
    return any(token in low for token in PHI_FORBIDDEN_KEY_TOKENS)


def sanitize_extra(metadata: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[str]]:
    """Return ``(clean, dropped)`` — a PHI-free, scalar-only, size-capped copy of
    optional structured ``extra`` metadata, plus the list of dropped keys.

    Rules mirror the analytics store: non-dict → ``({}, [])``; PHI-looking keys
    dropped; only str/int/float/bool kept; strings trimmed; key count capped."""
    if not isinstance(metadata, dict):
        return {}, []
    clean: Dict[str, Any] = {}
    dropped: List[str] = []
    for raw_key, value in metadata.items():
        key = str(raw_key).strip()
        if not key:
            continue
        if _key_is_phi(key):
            dropped.append(key)
            continue
        if isinstance(value, bool) or isinstance(value, (int, float)):
            clean[key[:64]] = value
        elif isinstance(value, str):
            clean[key[:64]] = value.strip()[:MAX_METADATA_VALUE_LEN]
        else:
            dropped.append(key)
            continue
        if len(clean) >= MAX_METADATA_KEYS:
            break
    return clean, dropped


# ── Free-text PHI-risk guard ─────────────────────────────────────────────────
# Conservative markers/patterns that strongly suggest protected client content
# leaked into free text (ticket subject / description / internal notes). Tuned to
# catch obvious PHI while leaving ordinary support language alone — e.g. "client
# page is broken" and "case management module won't load" do NOT match (no
# contiguous "client name" / "client is" / "case note" / "progress note").
PHI_RISK_PATTERNS = (
    (re.compile(r"\bMRN\b", re.I), "MRN reference"),
    (re.compile(r"medical record", re.I), "medical record reference"),
    (re.compile(r"\bDOB\b", re.I), "date-of-birth reference"),
    (re.compile(r"date of birth", re.I), "date-of-birth reference"),
    (re.compile(r"\bSSN\b", re.I), "SSN reference"),
    (re.compile(r"social security", re.I), "social-security reference"),
    (re.compile(r"\bclient name\b", re.I), "client name reference"),
    (re.compile(r"\bclient is\b", re.I), "client-identifying phrase"),
    (re.compile(r"\bpatient name\b", re.I), "patient name reference"),
    (re.compile(r"\bcase note", re.I), "case-note reference"),
    (re.compile(r"\bprogress note", re.I), "progress-note reference"),
    # SSN-like: 123-45-6789
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "SSN-like number"),
    # Phone-like: 555-123-4567 / 555.123.4567 / 555 123 4567
    (re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b"), "phone-like number"),
    # Phone-like: (555) 123-4567
    (re.compile(r"\(\d{3}\)\s*\d{3}[-.\s]?\d{4}"), "phone-like number"),
    # Bare 10-digit run (likely a phone number / identifier)
    (re.compile(r"\b\d{10}\b"), "10-digit number"),
    # Email address
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "email address"),
)


def scan_phi_risk(text: Optional[str]) -> Optional[str]:
    """Return a short reason string if ``text`` contains an obvious PHI-risk marker
    or pattern, else None. Conservative by design — used to *reject* unsafe free
    text at the API boundary, not to silently scrub it."""
    if not text:
        return None
    for pattern, label in PHI_RISK_PATTERNS:
        if pattern.search(text):
            return label
    return None


def normalize_category(value: Any) -> Optional[str]:
    text = str(value or "").strip().lower()
    return text if text in CATEGORIES else None


def normalize_priority(value: Any) -> Optional[str]:
    text = str(value or "").strip().lower()
    return text if text in PRIORITIES else None


def normalize_status(value: Any) -> Optional[str]:
    text = str(value or "").strip().lower()
    return text if text in STATUSES else None


class SupportStore:
    """Thin SQLite wrapper for the support-ticket queue."""

    def _db_path(self):
        # Resolve dynamically so a monkeypatched/redirected DB_DIR is honored.
        return db_path_mod.DB_DIR / DB_FILENAME

    def _connect(self) -> sqlite3.Connection:
        path = self._db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        self._ensure_schema(conn)
        return conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id TEXT,
                submitted_by_user_id TEXT,
                submitted_by_email TEXT,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                assigned_to TEXT,
                internal_notes TEXT,
                extra_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_support_status ON support_tickets(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_support_category ON support_tickets(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_support_priority ON support_tickets(priority)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_support_created_at ON support_tickets(created_at)")

    # ── Writes ───────────────────────────────────────────────────────────────

    def create_ticket(
        self,
        *,
        category: str,
        priority: str,
        subject: str,
        description: str,
        org_id: Optional[str] = None,
        submitted_by_user_id: Optional[str] = None,
        submitted_by_email: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Insert one ticket. Category/priority are assumed already validated by the
        caller (the endpoint enforces the allowlists). Status/assigned/internal_notes
        are always forced to safe defaults here — the create path can never set them.
        Optional ``extra`` metadata is sanitized (PHI stripped)."""
        clean_extra, dropped = sanitize_extra(extra)
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO support_tickets (
                    org_id, submitted_by_user_id, submitted_by_email,
                    category, priority, status, subject, description,
                    assigned_to, internal_notes, extra_json,
                    created_at, updated_at, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, NULL)
                """,
                (
                    _trim(org_id, MAX_ID_FIELD_LEN),
                    _trim(submitted_by_user_id, MAX_ID_FIELD_LEN),
                    _trim(submitted_by_email, MAX_EMAIL_LEN),
                    str(category).strip().lower()[:32],
                    str(priority).strip().lower()[:32],
                    DEFAULT_STATUS,
                    _trim(subject, MAX_SUBJECT_LEN) or "(no subject)",
                    _trim(description, MAX_DESCRIPTION_LEN) or "(no description)",
                    json.dumps(clean_extra) if clean_extra else None,
                    now,
                    now,
                ),
            )
            conn.commit()
            ticket_id = cur.lastrowid
        if dropped:
            logger.info(
                "support: dropped %d unsafe metadata key(s) from new ticket", len(dropped)
            )
        return {"ticket_id": ticket_id, "dropped_metadata_keys": dropped}

    def update_ticket(
        self,
        ticket_id: int,
        *,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[str] = None,
        internal_notes: Optional[str] = None,
        assigned_to_set: bool = False,
        internal_notes_set: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Owner-only update. Only status/priority/assigned_to/internal_notes can
        change. ``resolved_at`` is managed automatically: stamped when status enters
        a terminal state (resolved/closed), cleared when it leaves one. Returns the
        updated row dict, or None if the ticket does not exist.

        ``assigned_to_set`` / ``internal_notes_set`` let the caller distinguish
        "field omitted" from "field explicitly cleared to null"."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM support_tickets WHERE id = ?", (int(ticket_id),)
            ).fetchone()
            if row is None:
                return None

            sets: List[str] = []
            params: List[Any] = []

            new_status = normalize_status(status) if status is not None else None
            if new_status:
                sets.append("status = ?")
                params.append(new_status)
                # Manage resolved_at based on the resulting status.
                if new_status in TERMINAL_STATUSES:
                    existing_resolved = row["resolved_at"]
                    if not existing_resolved:
                        sets.append("resolved_at = ?")
                        params.append(datetime.utcnow().isoformat())
                else:
                    sets.append("resolved_at = NULL")

            new_priority = normalize_priority(priority) if priority is not None else None
            if new_priority:
                sets.append("priority = ?")
                params.append(new_priority)

            if assigned_to_set:
                sets.append("assigned_to = ?")
                params.append(_trim(assigned_to, MAX_ASSIGNED_LEN))

            if internal_notes_set:
                sets.append("internal_notes = ?")
                params.append(_trim(internal_notes, MAX_INTERNAL_NOTES_LEN))

            if not sets:
                # Nothing valid to change — return the current row unchanged.
                return self._row_to_dict(row)

            sets.append("updated_at = ?")
            params.append(datetime.utcnow().isoformat())
            params.append(int(ticket_id))
            conn.execute(
                f"UPDATE support_tickets SET {', '.join(sets)} WHERE id = ?", params
            )
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM support_tickets WHERE id = ?", (int(ticket_id),)
            ).fetchone()
        return self._row_to_dict(updated) if updated else None

    # ── Reads ────────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        extra = None
        if row["extra_json"]:
            try:
                extra = json.loads(row["extra_json"])
            except Exception:  # noqa: BLE001
                extra = None
        return {
            "id": row["id"],
            "org_id": row["org_id"],
            "submitted_by_user_id": row["submitted_by_user_id"],
            "submitted_by_email": row["submitted_by_email"],
            "category": row["category"],
            "priority": row["priority"],
            "status": row["status"],
            "subject": row["subject"],
            "description": row["description"],
            "assigned_to": row["assigned_to"],
            "internal_notes": row["internal_notes"],
            "extra": extra,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "resolved_at": row["resolved_at"],
        }

    def get_ticket(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM support_tickets WHERE id = ?", (int(ticket_id),)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_tickets(
        self,
        *,
        status: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Full ticket rows for the owner queue, newest first. Optional allowlisted
        filters; unrecognized filter values are ignored (the list still renders)."""
        conds: List[str] = []
        params: List[Any] = []
        s = normalize_status(status)
        if s:
            conds.append("status = ?")
            params.append(s)
        c = normalize_category(category)
        if c:
            conds.append("category = ?")
            params.append(c)
        p = normalize_priority(priority)
        if p:
            conds.append("priority = ?")
            params.append(p)
        where = (" WHERE " + " AND ".join(conds)) if conds else ""
        sql = (
            "SELECT * FROM support_tickets" + where +
            " ORDER BY id DESC LIMIT ? OFFSET ?"
        )
        params.append(max(1, min(int(limit), 500)))
        params.append(max(0, int(offset)))
        out: List[Dict[str, Any]] = []
        try:
            with self._connect() as conn:
                rows = conn.execute(sql, params).fetchall()
            out = [self._row_to_dict(r) for r in rows]
        except Exception:  # noqa: BLE001
            pass
        return out

    def _count_where(self, conn: sqlite3.Connection, where: str, params: list) -> int:
        sql = "SELECT COUNT(*) FROM support_tickets"
        if where:
            sql += f" WHERE {where}"
        row = conn.execute(sql, params).fetchone()
        return int(row[0]) if row else 0

    def _group_counts(self, conn: sqlite3.Connection, column: str, allowed: tuple) -> Dict[str, int]:
        """Count by an allowlisted column, seeding every known value at 0 so the UI
        always sees the full set (not just whatever has rows)."""
        counts: Dict[str, int] = {v: 0 for v in allowed}
        rows = conn.execute(
            f"SELECT {column} v, COUNT(*) c FROM support_tickets GROUP BY {column}"
        ).fetchall()
        for r in rows:
            key = r["v"]
            if key in counts:
                counts[key] = int(r["c"])
            elif key:
                counts[key] = int(r["c"])
        return counts

    def summary(self, *, recent_limit: int = 10) -> Dict[str, Any]:
        """Owner summary counts + a safe recent-tickets feed."""
        empty = {
            "total_tickets": 0,
            "open_tickets": 0,
            "high_priority_tickets": 0,
            "by_category": {c: 0 for c in CATEGORIES},
            "by_status": {s: 0 for s in STATUSES},
            "by_priority": {p: 0 for p in PRIORITIES},
            "recent_tickets": [],
        }
        try:
            with self._connect() as conn:
                total = self._count_where(conn, "", [])
                open_count = self._count_where(
                    conn, "status NOT IN (?, ?)", list(TERMINAL_STATUSES)
                )
                high = self._count_where(
                    conn, "priority IN (?, ?)", ["high", "urgent"]
                )
                by_category = self._group_counts(conn, "category", CATEGORIES)
                by_status = self._group_counts(conn, "status", STATUSES)
                by_priority = self._group_counts(conn, "priority", PRIORITIES)
                recent_rows = conn.execute(
                    "SELECT id, category, priority, status, subject, assigned_to,"
                    " created_at, updated_at FROM support_tickets"
                    " ORDER BY id DESC LIMIT ?",
                    (max(1, min(int(recent_limit), MAX_RECENT)),),
                ).fetchall()
            recent = [
                {
                    "id": r["id"],
                    "category": r["category"],
                    "priority": r["priority"],
                    "status": r["status"],
                    "subject": r["subject"],
                    "assigned_to": r["assigned_to"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                }
                for r in recent_rows
            ]
            return {
                "total_tickets": total,
                "open_tickets": open_count,
                "high_priority_tickets": high,
                "by_category": by_category,
                "by_status": by_status,
                "by_priority": by_priority,
                "recent_tickets": recent,
            }
        except Exception:  # noqa: BLE001 — summary is best-effort
            return empty


# Module-level singleton, mirroring analytics_store / billing usage.
support_store = SupportStore()
