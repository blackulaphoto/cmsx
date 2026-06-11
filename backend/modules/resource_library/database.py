"""
Resource Library Database - SQLite operations for the master resource library.
All programs/resources exist once here; modules filter via category, pathways, and tags.
"""
import sqlite3
import json
import logging
from datetime import datetime
from typing import Any, Optional
from backend.shared.db_path import DB_DIR

logger = logging.getLogger(__name__)

DB_PATH = DB_DIR / "resource_library.db"

# Fields stored as JSON text in SQLite
JSON_FIELDS = [
    "secondary_categories", "pathways", "tags", "services_offered",
    "people_served", "eligibility", "documents_required", "languages",
    "locations", "coverage_area",
]

VALID_VERIFICATION_STATUSES = {
    "needs_review", "verified", "needs_update", "inactive", "duplicate_review"
}

VALID_REFERRAL_STATUSES = {
    "not_started", "called", "left_message", "emailed", "application_started",
    "documents_needed", "submitted", "waiting", "accepted", "denied", "closed"
}

_CREATE_RESOURCE_TABLE = """
CREATE TABLE IF NOT EXISTS resource_library (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_name        TEXT NOT NULL,
    service_name         TEXT,
    display_name         TEXT,
    primary_category     TEXT,
    secondary_categories TEXT DEFAULT '[]',
    pathways             TEXT DEFAULT '[]',
    tags                 TEXT DEFAULT '[]',
    description          TEXT,
    services_offered     TEXT DEFAULT '[]',
    people_served        TEXT DEFAULT '[]',
    eligibility          TEXT DEFAULT '[]',
    documents_required   TEXT DEFAULT '[]',
    cost                 TEXT,
    languages            TEXT DEFAULT '[]',
    phone                TEXT,
    email                TEXT,
    website              TEXT,
    locations            TEXT DEFAULT '[]',
    coverage_area        TEXT DEFAULT '[]',
    cmsx_notes           TEXT,
    verification_status  TEXT DEFAULT 'needs_review',
    source               TEXT,
    source_url           TEXT,
    active               INTEGER DEFAULT 1,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);
"""

_CREATE_REFERRALS_TABLE = """
CREATE TABLE IF NOT EXISTS client_resource_referrals (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id           TEXT NOT NULL,
    resource_id         INTEGER NOT NULL,
    status              TEXT DEFAULT 'not_started',
    priority            TEXT DEFAULT 'medium',
    referral_reason     TEXT,
    assigned_to         TEXT,
    follow_up_date      TEXT,
    notes               TEXT,
    documents_needed    TEXT DEFAULT '[]',
    documents_submitted TEXT DEFAULT '[]',
    outcome             TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    FOREIGN KEY (resource_id) REFERENCES resource_library (id)
);
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_rl_primary_category ON resource_library (primary_category);",
    "CREATE INDEX IF NOT EXISTS idx_rl_active ON resource_library (active);",
    "CREATE INDEX IF NOT EXISTS idx_rl_verification_status ON resource_library (verification_status);",
    "CREATE INDEX IF NOT EXISTS idx_rl_provider_name ON resource_library (provider_name);",
]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db() -> None:
    with get_connection() as conn:
        conn.execute(_CREATE_RESOURCE_TABLE)
        conn.execute(_CREATE_REFERRALS_TABLE)
        for idx in _CREATE_INDEXES:
            conn.execute(idx)
        conn.commit()
    logger.info(f"Resource library DB initialized at {DB_PATH}")


def _serialize(record: dict) -> dict:
    """Convert list/dict fields to JSON strings for storage."""
    out = dict(record)
    for field in JSON_FIELDS:
        if field in out and not isinstance(out[field], str):
            out[field] = json.dumps(out[field] or [])
    return out


def _deserialize(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a dict, parsing JSON fields."""
    d = dict(row)
    for field in JSON_FIELDS:
        if field in d and isinstance(d[field], str):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                d[field] = []
    d["active"] = bool(d.get("active", 1))
    return d


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def insert_resource(data: dict) -> int:
    now = datetime.utcnow().isoformat()
    row = _serialize(data)
    row.setdefault("verification_status", "needs_review")
    row["created_at"] = now
    row["updated_at"] = now

    cols = ", ".join(row.keys())
    placeholders = ", ".join("?" for _ in row)
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO resource_library ({cols}) VALUES ({placeholders})",
            list(row.values()),
        )
        conn.commit()
        return cur.lastrowid


def get_resource_by_id(resource_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM resource_library WHERE id = ?", (resource_id,)
        ).fetchone()
    return _deserialize(row) if row else None


def update_resource(resource_id: int, data: dict) -> Optional[dict]:
    data["updated_at"] = datetime.utcnow().isoformat()
    row = _serialize(data)
    set_clause = ", ".join(f"{k} = ?" for k in row)
    with get_connection() as conn:
        conn.execute(
            f"UPDATE resource_library SET {set_clause} WHERE id = ?",
            list(row.values()) + [resource_id],
        )
        conn.commit()
    return get_resource_by_id(resource_id)


def search_resources(
    *,
    category: Optional[str] = None,
    pathway: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    city: Optional[str] = None,
    county: Optional[str] = None,
    verification_status: Optional[str] = None,
    active: Optional[bool] = True,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    conditions = []
    params: list[Any] = []

    if active is not None:
        conditions.append("active = ?")
        params.append(1 if active else 0)

    if category:
        conditions.append(
            "(primary_category = ? OR secondary_categories LIKE ? OR pathways LIKE ?)"
        )
        params += [category, f'%"{category}"%', f'%"{category}"%']

    if pathway:
        conditions.append("pathways LIKE ?")
        params.append(f'%"{pathway}"%')

    if tag:
        conditions.append("tags LIKE ?")
        params.append(f"%{tag}%")

    if search:
        like = f"%{search}%"
        conditions.append(
            "(provider_name LIKE ? OR service_name LIKE ? OR display_name LIKE ?"
            " OR description LIKE ? OR tags LIKE ? OR services_offered LIKE ?)"
        )
        params += [like, like, like, like, like, like]

    if city:
        conditions.append("locations LIKE ?")
        params.append(f"%{city}%")

    if county:
        conditions.append(
            "(coverage_area LIKE ? OR locations LIKE ?)"
        )
        params += [f"%{county}%", f"%{county}%"]

    if verification_status:
        conditions.append("verification_status = ?")
        params.append(verification_status)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * per_page

    with get_connection() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM resource_library {where}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"SELECT * FROM resource_library {where}"
            " ORDER BY provider_name ASC"
            " LIMIT ? OFFSET ?",
            params + [per_page, offset],
        ).fetchall()

    results = [_deserialize(r) for r in rows]
    total_pages = max(1, (total + per_page - 1) // per_page)

    return {
        "success": True,
        "results": results,
        "total_count": total,
        "source": "resource_library",
        "pagination": {
            "current_page": page,
            "per_page": per_page,
            "total_results": total,
            "total_pages": total_pages,
            "has_next_page": page < total_pages,
            "has_prev_page": page > 1,
            "start_index": offset + 1 if total > 0 else 0,
            "end_index": min(offset + per_page, total),
        },
    }


def resource_exists(provider_name: str, service_name: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM resource_library WHERE provider_name = ? AND service_name = ?",
            (provider_name, service_name),
        ).fetchone()
    return row is not None


def get_resource_count() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM resource_library").fetchone()[0]
