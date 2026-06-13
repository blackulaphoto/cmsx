import json
import logging
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
from backend.shared.db_path import DB_DIR as _DB_DIR
DB_PATH = _DB_DIR / "admissions.db"
MANIFEST_PATH = _PROJECT_ROOT / "data" / "form_templates" / "admissions" / "manifest.json"

if not MANIFEST_PATH.exists():
    MANIFEST_PATH = Path("data") / "form_templates" / "admissions" / "manifest.json"

# Resolve attachment storage root once at startup.
# Priority: Railway volume > ADMISSIONS_UPLOAD_DIR env var > local default.
_RAILWAY_VOLUME_ROOT = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "")
_UPLOAD_DIR_ENV = os.environ.get("ADMISSIONS_UPLOAD_DIR", "")
if _RAILWAY_VOLUME_ROOT:
    _UPLOADS_BASE = Path(_RAILWAY_VOLUME_ROOT) / "admissions"
elif _UPLOAD_DIR_ENV:
    _UPLOADS_BASE = Path(_UPLOAD_DIR_ENV)
else:
    _UPLOADS_BASE = _PROJECT_ROOT / "uploads" / "admissions"


def _resolve_attachment_path(storage_path: str) -> Path:
    """Resolve a stored attachment path to an absolute filesystem Path.

    Handles two storage_path formats:
    - New (relative):  '{packet_id}/{form_key}/{name}'  → _UPLOADS_BASE / path
    - Legacy (prefixed): 'uploads/admissions/{...}'    → _UPLOADS_BASE / stripped
    """
    sp = storage_path
    if sp.startswith("uploads/admissions/"):
        return _UPLOADS_BASE / sp[len("uploads/admissions/"):]
    if sp.startswith("uploads/"):
        # Generic uploads/ prefix from before Railway Volume support
        return _PROJECT_ROOT / sp
    return _UPLOADS_BASE / sp

# Column migrations: run at startup, silently skip if column already exists
_COLUMN_MIGRATIONS = [
    "ALTER TABLE admission_packet_forms ADD COLUMN review_status TEXT NOT NULL DEFAULT 'Not Reviewed'",
    "ALTER TABLE admission_packet_forms ADD COLUMN review_notes TEXT",
    "ALTER TABLE admission_packet_forms ADD COLUMN reviewed_by TEXT",
    "ALTER TABLE admission_packet_forms ADD COLUMN started_at TEXT",
    "ALTER TABLE admissions_financial_coordination ADD COLUMN last_updated_by TEXT",
    "ALTER TABLE admission_packets ADD COLUMN shared_profile_json TEXT NOT NULL DEFAULT '{}'",
]


def _load_manifest() -> List[Dict[str, Any]]:
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("forms", [])
    except Exception as exc:
        logger.error(f"[ADMISSIONS] Failed to load form manifest: {exc}")
        return []


def _now() -> str:
    return datetime.utcnow().isoformat()


def _calc_progress(forms: List[Dict[str, Any]]) -> int:
    required = [f for f in forms if f.get("required")]
    if not required:
        return 0
    completed = [f for f in required if f.get("status") == "Completed"]
    return round(len(completed) / len(required) * 100)


_FC_ALLOWED_COLUMNS = {
    "billing_explained_status", "billing_explained_date", "billing_notes",
    "insurance_verification_status", "primary_payer_type", "primary_plan_name",
    "primary_member_id", "verification_date", "verification_rep_name",
    "verification_reference_number", "deductible", "copay", "coinsurance",
    "out_of_pocket_max", "auth_required",
    "cob_status", "cob_issue_identified", "cob_notes", "cob_followup_needed",
    "payment_plan_status", "payment_arrangement_type", "payment_amount",
    "payment_due_date", "payment_notes",
    "std_needed", "std_status", "std_notes",
    "fmla_needed", "linked_fmla_case_id",
    "discharge_planning_started", "discharge_destination", "sober_living_needed",
    "pcp_dental_psych_needed", "legal_probation_followup_needed",
    "benefits_followup_needed", "employment_resume_needed",
    "transportation_plan", "discharge_notes",
    "case_manager_id", "last_updated_by",
}

_FC_BOOL_COLUMNS = {
    "cob_issue_identified", "cob_followup_needed", "discharge_planning_started",
    "sober_living_needed", "pcp_dental_psych_needed", "legal_probation_followup_needed",
    "benefits_followup_needed", "employment_resume_needed",
}


class AdmissionsStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._setup()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
        except Exception:
            pass
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
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS admission_packets (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    client_name TEXT NOT NULL,
                    case_manager_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'In Progress',
                    progress_percent INTEGER NOT NULL DEFAULT 0,
                    shared_profile_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_packets_client_id
                    ON admission_packets(client_id);

                CREATE TABLE IF NOT EXISTS admission_packet_forms (
                    id TEXT PRIMARY KEY,
                    packet_id TEXT NOT NULL REFERENCES admission_packets(id) ON DELETE CASCADE,
                    form_key TEXT NOT NULL,
                    form_name TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Not Started',
                    required INTEGER NOT NULL DEFAULT 1,
                    timing_group TEXT NOT NULL DEFAULT 'admission',
                    timing_label TEXT NOT NULL DEFAULT 'Required at Admission',
                    requires_signature INTEGER NOT NULL DEFAULT 0,
                    signatures_required TEXT NOT NULL DEFAULT '[]',
                    allow_attachments INTEGER NOT NULL DEFAULT 0,
                    allow_revocation INTEGER NOT NULL DEFAULT 0,
                    expires_in_days INTEGER,
                    expires_at TEXT,
                    notes TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    signed_at TEXT,
                    review_status TEXT NOT NULL DEFAULT 'Not Reviewed',
                    review_notes TEXT,
                    reviewed_by TEXT,
                    reviewed_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(packet_id, form_key)
                );

                CREATE TABLE IF NOT EXISTS admission_form_responses (
                    id TEXT PRIMARY KEY,
                    packet_id TEXT NOT NULL REFERENCES admission_packets(id) ON DELETE CASCADE,
                    form_key TEXT NOT NULL,
                    response_data TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(packet_id, form_key)
                );

                CREATE TABLE IF NOT EXISTS admission_form_attachments (
                    id TEXT PRIMARY KEY,
                    packet_id TEXT NOT NULL REFERENCES admission_packets(id) ON DELETE CASCADE,
                    form_key TEXT NOT NULL,
                    client_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_type TEXT NOT NULL DEFAULT '',
                    file_size INTEGER NOT NULL DEFAULT 0,
                    storage_path TEXT NOT NULL,
                    uploaded_by TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS admissions_created_tasks (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    task_key TEXT NOT NULL,
                    reminder_id TEXT,
                    case_manager_id TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(client_id, task_key)
                );

                CREATE TABLE IF NOT EXISTS admissions_financial_coordination (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    packet_id TEXT NOT NULL DEFAULT '',
                    case_manager_id TEXT NOT NULL DEFAULT '',
                    billing_explained_status TEXT NOT NULL DEFAULT 'Not Started',
                    billing_explained_date TEXT,
                    billing_notes TEXT,
                    insurance_verification_status TEXT NOT NULL DEFAULT 'Not Started',
                    primary_payer_type TEXT,
                    primary_plan_name TEXT,
                    primary_member_id TEXT,
                    verification_date TEXT,
                    verification_rep_name TEXT,
                    verification_reference_number TEXT,
                    deductible TEXT,
                    copay TEXT,
                    coinsurance TEXT,
                    out_of_pocket_max TEXT,
                    auth_required TEXT NOT NULL DEFAULT 'Unknown',
                    cob_status TEXT NOT NULL DEFAULT 'Not Needed',
                    cob_issue_identified INTEGER NOT NULL DEFAULT 0,
                    cob_notes TEXT,
                    cob_followup_needed INTEGER NOT NULL DEFAULT 0,
                    payment_plan_status TEXT NOT NULL DEFAULT 'Not Needed',
                    payment_arrangement_type TEXT,
                    payment_amount TEXT,
                    payment_due_date TEXT,
                    payment_notes TEXT,
                    std_needed TEXT NOT NULL DEFAULT 'Unknown',
                    std_status TEXT NOT NULL DEFAULT 'Not Started',
                    std_notes TEXT,
                    fmla_needed TEXT NOT NULL DEFAULT 'Unknown',
                    linked_fmla_case_id TEXT,
                    discharge_planning_started INTEGER NOT NULL DEFAULT 0,
                    discharge_destination TEXT,
                    sober_living_needed INTEGER NOT NULL DEFAULT 0,
                    pcp_dental_psych_needed INTEGER NOT NULL DEFAULT 0,
                    legal_probation_followup_needed INTEGER NOT NULL DEFAULT 0,
                    benefits_followup_needed INTEGER NOT NULL DEFAULT 0,
                    employment_resume_needed INTEGER NOT NULL DEFAULT 0,
                    transportation_plan TEXT,
                    discharge_notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(client_id)
                );

                CREATE TABLE IF NOT EXISTS admissions_task_suppressions (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    task_key TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'dismissed',
                    reason TEXT,
                    dismissed_by TEXT,
                    dismissed_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(client_id, task_key)
                );

                CREATE TABLE IF NOT EXISTS admissions_financial_coordination_events (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    packet_id TEXT NOT NULL DEFAULT '',
                    event_type TEXT NOT NULL DEFAULT 'update',
                    changed_by TEXT NOT NULL DEFAULT '',
                    changed_fields_json TEXT NOT NULL DEFAULT '[]',
                    previous_values_json TEXT,
                    new_values_json TEXT,
                    created_at TEXT NOT NULL
                );
            """)
            # Migrate existing tables that pre-date Phase 5 columns
            for stmt in _COLUMN_MIGRATIONS:
                try:
                    conn.execute(stmt)
                except Exception:
                    pass  # column already exists

    # ── Packet operations ──────────────────────────────────────────────

    def get_or_create_packet(
        self,
        client_id: str,
        client_name: str,
        case_manager_id: str,
        shared_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM admission_packets WHERE client_id = ?", (client_id,)
            ).fetchone()

            if row:
                packet = self._packet_row_to_dict(row)
                packet["forms"] = self._get_forms(conn, packet["id"])
                packet["progress_percent"] = _calc_progress(packet["forms"])
                conn.execute(
                    "UPDATE admission_packets SET progress_percent = ?, updated_at = ? WHERE id = ?",
                    (packet["progress_percent"], _now(), packet["id"]),
                )
                if shared_profile:
                    packet = self.update_packet_profile(packet["id"], shared_profile, conn=conn)
                return packet

            packet_id = str(uuid.uuid4())
            now = _now()
            conn.execute(
                """INSERT INTO admission_packets
                   (id, client_id, client_name, case_manager_id, status, progress_percent, shared_profile_json, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    packet_id,
                    client_id,
                    client_name,
                    case_manager_id,
                    "In Progress",
                    0,
                    json.dumps(shared_profile or {}),
                    now,
                    now,
                ),
            )
            self._seed_forms(conn, packet_id, now)
            forms = self._get_forms(conn, packet_id)
            return {
                "id": packet_id,
                "client_id": client_id,
                "client_name": client_name,
                "case_manager_id": case_manager_id,
                "status": "In Progress",
                "progress_percent": 0,
                "shared_profile": shared_profile or {},
                "created_at": now,
                "updated_at": now,
                "forms": forms,
            }

    def get_packet_by_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM admission_packets WHERE client_id = ?", (client_id,)
            ).fetchone()
            if not row:
                return None
            packet = self._packet_row_to_dict(row)
            packet["forms"] = self._get_forms(conn, packet["id"])
            packet["progress_percent"] = _calc_progress(packet["forms"])
            conn.execute(
                "UPDATE admission_packets SET progress_percent = ?, updated_at = ? WHERE id = ?",
                (packet["progress_percent"], _now(), packet["id"]),
            )
            return packet

    def update_form_status(
        self, packet_id: str, form_key: str, status: str, notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        now = _now()
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM admission_packet_forms WHERE packet_id = ? AND form_key = ?",
                (packet_id, form_key),
            ).fetchone()
            if not row:
                return None

            completed_at = row["completed_at"]
            if status == "Completed" and not completed_at:
                completed_at = now
            elif status != "Completed":
                completed_at = None

            # Set started_at the first time the form moves out of Not Started
            started_at = row["started_at"]
            if not started_at and status != "Not Started":
                started_at = now

            conn.execute(
                """UPDATE admission_packet_forms
                   SET status=?, notes=?, started_at=?, completed_at=?, updated_at=?
                   WHERE packet_id=? AND form_key=?""",
                (status, notes or row["notes"], started_at, completed_at, now, packet_id, form_key),
            )

            forms = self._get_forms(conn, packet_id)
            progress = _calc_progress(forms)

            packet_status = "Completed" if progress == 100 else "In Progress"
            conn.execute(
                "UPDATE admission_packets SET progress_percent=?, status=?, updated_at=? WHERE id=?",
                (progress, packet_status, now, packet_id),
            )

            updated = conn.execute(
                "SELECT * FROM admission_packet_forms WHERE packet_id=? AND form_key=?",
                (packet_id, form_key),
            ).fetchone()
            return self._form_row_to_dict(updated)

    def get_packet_by_id(self, packet_id: str) -> Optional[Dict[str, Any]]:
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM admission_packets WHERE id = ?", (packet_id,)
            ).fetchone()
            if not row:
                return None
            packet = self._packet_row_to_dict(row)
            packet["forms"] = self._get_forms(conn, packet["id"])
            packet["progress_percent"] = _calc_progress(packet["forms"])
            conn.execute(
                "UPDATE admission_packets SET progress_percent = ?, updated_at = ? WHERE id = ?",
                (packet["progress_percent"], _now(), packet["id"]),
            )
            return packet

    def update_packet_profile(
        self,
        packet_id: str,
        shared_profile: Dict[str, Any],
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[Dict[str, Any]]:
        now = _now()
        if conn is not None:
            return self._update_packet_profile(conn, packet_id, shared_profile, now)
        with self._db() as managed_conn:
            return self._update_packet_profile(managed_conn, packet_id, shared_profile, now)

    def _update_packet_profile(
        self,
        conn: sqlite3.Connection,
        packet_id: str,
        shared_profile: Dict[str, Any],
        now: str,
    ) -> Optional[Dict[str, Any]]:
        client_name = (shared_profile or {}).get("full_name") or None
        if client_name:
            conn.execute(
                """
                UPDATE admission_packets
                SET shared_profile_json = ?, client_name = ?, updated_at = ?
                WHERE id = ?
                """,
                (json.dumps(shared_profile or {}), client_name, now, packet_id),
            )
        else:
            conn.execute(
                """
                UPDATE admission_packets
                SET shared_profile_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (json.dumps(shared_profile or {}), now, packet_id),
            )
        row = conn.execute("SELECT * FROM admission_packets WHERE id = ?", (packet_id,)).fetchone()
        if not row:
            return None
        packet = self._packet_row_to_dict(row)
        packet["forms"] = self._get_forms(conn, packet_id)
        return packet

    # ── Form response operations ───────────────────────────────────────

    def get_form_response(self, packet_id: str, form_key: str) -> Optional[Dict[str, Any]]:
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM admission_form_responses WHERE packet_id = ? AND form_key = ?",
                (packet_id, form_key),
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["response_data"] = json.loads(d.get("response_data") or "{}")
            except (ValueError, TypeError):
                d["response_data"] = {}
            return d

    def save_form_response(
        self, packet_id: str, form_key: str, response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        now = _now()
        serialized = json.dumps(response_data)
        with self._db() as conn:
            existing = conn.execute(
                "SELECT id FROM admission_form_responses WHERE packet_id = ? AND form_key = ?",
                (packet_id, form_key),
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE admission_form_responses
                       SET response_data = ?, updated_at = ?
                       WHERE packet_id = ? AND form_key = ?""",
                    (serialized, now, packet_id, form_key),
                )
                row_id = existing["id"]
            else:
                row_id = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO admission_form_responses
                       (id, packet_id, form_key, response_data, created_at, updated_at)
                       VALUES (?,?,?,?,?,?)""",
                    (row_id, packet_id, form_key, serialized, now, now),
                )
        return {
            "id": row_id,
            "packet_id": packet_id,
            "form_key": form_key,
            "response_data": response_data,
            "updated_at": now,
        }

    # ── Attachment operations ──────────────────────────────────────────

    def get_attachments(self, packet_id: str, form_key: str) -> List[Dict[str, Any]]:
        with self._db() as conn:
            rows = conn.execute(
                """SELECT * FROM admission_form_attachments
                   WHERE packet_id = ? AND form_key = ?
                   ORDER BY created_at ASC""",
                (packet_id, form_key),
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["file_exists"] = _resolve_attachment_path(d["storage_path"]).exists()
                result.append(d)
            return result

    def add_attachment(
        self,
        packet_id: str,
        form_key: str,
        client_id: str,
        file_name: str,
        file_type: str,
        file_size: int,
        storage_path: str,
        uploaded_by: str = "",
    ) -> Dict[str, Any]:
        now = _now()
        att_id = str(uuid.uuid4())
        with self._db() as conn:
            conn.execute(
                """INSERT INTO admission_form_attachments
                   (id, packet_id, form_key, client_id, file_name, file_type, file_size,
                    storage_path, uploaded_by, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (att_id, packet_id, form_key, client_id, file_name, file_type, file_size,
                 storage_path, uploaded_by, now),
            )
        return {
            "id": att_id,
            "packet_id": packet_id,
            "form_key": form_key,
            "client_id": client_id,
            "file_name": file_name,
            "file_type": file_type,
            "file_size": file_size,
            "storage_path": storage_path,
            "uploaded_by": uploaded_by,
            "created_at": now,
        }

    def delete_attachment(self, attachment_id: str) -> bool:
        with self._db() as conn:
            cur = conn.execute(
                "DELETE FROM admission_form_attachments WHERE id = ?", (attachment_id,)
            )
            return cur.rowcount > 0

    def get_attachment_by_id(self, attachment_id: str) -> Optional[Dict[str, Any]]:
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM admission_form_attachments WHERE id = ?", (attachment_id,)
            ).fetchone()
            return dict(row) if row else None

    # ── Staff review ───────────────────────────────────────────────────

    def update_form_review(
        self,
        packet_id: str,
        form_key: str,
        review_status: str,
        review_notes: Optional[str] = None,
        reviewed_by: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        now = _now()
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM admission_packet_forms WHERE packet_id = ? AND form_key = ?",
                (packet_id, form_key),
            ).fetchone()
            if not row:
                return None

            reviewed_at = row["reviewed_at"]
            if review_status in ("Approved", "Needs Correction"):
                reviewed_at = now

            conn.execute(
                """UPDATE admission_packet_forms
                   SET review_status=?, review_notes=?, reviewed_by=?, reviewed_at=?, updated_at=?
                   WHERE packet_id=? AND form_key=?""",
                (
                    review_status,
                    review_notes if review_notes is not None else row["review_notes"],
                    reviewed_by if reviewed_by is not None else row["reviewed_by"],
                    reviewed_at,
                    now,
                    packet_id,
                    form_key,
                ),
            )
            updated = conn.execute(
                "SELECT * FROM admission_packet_forms WHERE packet_id=? AND form_key=?",
                (packet_id, form_key),
            ).fetchone()
            return self._form_row_to_dict(updated)

    # ── Task suppression tracking ──────────────────────────────────────

    def suppress_task(
        self,
        client_id: str,
        task_key: str,
        status: str,
        reason: Optional[str] = None,
        dismissed_by: Optional[str] = None,
    ) -> None:
        now = _now()
        with self._db() as conn:
            conn.execute(
                """INSERT INTO admissions_task_suppressions
                   (id, client_id, task_key, status, reason, dismissed_by, dismissed_at, created_at)
                   VALUES (?,?,?,?,?,?,?,?)
                   ON CONFLICT(client_id, task_key) DO UPDATE SET
                       status=excluded.status,
                       reason=excluded.reason,
                       dismissed_by=excluded.dismissed_by,
                       dismissed_at=excluded.dismissed_at""",
                (str(uuid.uuid4()), client_id, task_key, status, reason, dismissed_by, now, now),
            )

    def get_task_suppressions(self, client_id: str) -> Dict[str, str]:
        """Return {task_key: status} for all suppressions for this client."""
        with self._db() as conn:
            rows = conn.execute(
                "SELECT task_key, status FROM admissions_task_suppressions WHERE client_id = ?",
                (client_id,),
            ).fetchall()
            return {r["task_key"]: r["status"] for r in rows}

    # ── Task dedup tracking ────────────────────────────────────────────

    def record_task_key(
        self,
        client_id: str,
        task_key: str,
        reminder_id: Optional[str] = None,
        case_manager_id: Optional[str] = None,
    ) -> None:
        now = _now()
        with self._db() as conn:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO admissions_created_tasks
                       (id, client_id, task_key, reminder_id, case_manager_id, created_at)
                       VALUES (?,?,?,?,?,?)""",
                    (str(uuid.uuid4()), client_id, task_key, reminder_id, case_manager_id, now),
                )
            except Exception:
                pass  # UNIQUE conflict — already recorded

    def get_created_task_keys(self, client_id: str) -> List[str]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT task_key FROM admissions_created_tasks WHERE client_id = ?",
                (client_id,),
            ).fetchall()
            return [r["task_key"] for r in rows]

    # ── Financial coordination ─────────────────────────────────────────

    def get_financial_coordination_readonly(self, client_id: str) -> Dict[str, Any]:
        """Read FC record without creating one. Returns exists=False dict if missing."""
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM admissions_financial_coordination WHERE client_id = ?",
                (client_id,),
            ).fetchone()
            if row:
                return self._fc_row_to_dict(row)
            return {
                "exists": False,
                "billing_explained_status": "Not Started",
                "insurance_verification_status": "Not Started",
                "cob_status": "Not Needed",
                "payment_plan_status": "Not Needed",
                "std_needed": "Unknown",
                "std_status": "Not Started",
                "fmla_needed": "Unknown",
                "discharge_planning_started": False,
            }

    def get_recent_fc_events(self, client_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        with self._db() as conn:
            rows = conn.execute(
                """SELECT * FROM admissions_financial_coordination_events
                   WHERE client_id = ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (client_id, limit),
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                try:
                    d["changed_fields"] = json.loads(d.get("changed_fields_json") or "[]")
                except (ValueError, TypeError):
                    d["changed_fields"] = []
                result.append(d)
            return result

    def get_financial_coordination(self, client_id: str) -> Dict[str, Any]:
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM admissions_financial_coordination WHERE client_id = ?",
                (client_id,),
            ).fetchone()
            if row:
                return self._fc_row_to_dict(row)
            packet_row = conn.execute(
                "SELECT id, case_manager_id FROM admission_packets WHERE client_id = ?",
                (client_id,),
            ).fetchone()
            now = _now()
            fc_id = str(uuid.uuid4())
            packet_id = packet_row["id"] if packet_row else ""
            case_mgr = packet_row["case_manager_id"] if packet_row else ""
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO admissions_financial_coordination
                       (id, client_id, packet_id, case_manager_id, created_at, updated_at)
                       VALUES (?,?,?,?,?,?)""",
                    (fc_id, client_id, packet_id, case_mgr, now, now),
                )
            except Exception:
                pass
            row = conn.execute(
                "SELECT * FROM admissions_financial_coordination WHERE client_id = ?",
                (client_id,),
            ).fetchone()
            if not row:
                return {
                    "billing_explained_status": "Not Started",
                    "insurance_verification_status": "Not Started",
                    "cob_status": "Not Needed",
                    "payment_plan_status": "Not Needed",
                    "std_needed": "Unknown",
                    "std_status": "Not Started",
                    "fmla_needed": "Unknown",
                    "discharge_planning_started": False,
                }
            return self._fc_row_to_dict(row)

    def upsert_financial_coordination(
        self,
        client_id: str,
        packet_id: str,
        fields: Dict[str, Any],
        changed_by: str = "",
    ) -> Dict[str, Any]:
        now = _now()
        safe = {k: v for k, v in fields.items() if k in _FC_ALLOWED_COLUMNS}
        if changed_by:
            safe["last_updated_by"] = changed_by
        with self._db() as conn:
            existing = conn.execute(
                "SELECT * FROM admissions_financial_coordination WHERE client_id = ?",
                (client_id,),
            ).fetchone()
            _AUDIT_META = {"updated_at", "last_updated_by"}
            if existing:
                prev = dict(existing)
                if safe:
                    safe["updated_at"] = now
                    set_clause = ", ".join(f"{k} = ?" for k in safe)
                    conn.execute(
                        f"UPDATE admissions_financial_coordination SET {set_clause} WHERE client_id = ?",
                        list(safe.values()) + [client_id],
                    )
                # Record audit event
                changed_field_names = [k for k in safe if k not in _AUDIT_META]
                if changed_field_names:
                    prev_vals = {k: prev.get(k) for k in changed_field_names}
                    new_vals = {k: safe[k] for k in changed_field_names}
                    conn.execute(
                        """INSERT INTO admissions_financial_coordination_events
                           (id, client_id, packet_id, event_type, changed_by,
                            changed_fields_json, previous_values_json, new_values_json, created_at)
                           VALUES (?,?,?,?,?,?,?,?,?)""",
                        (
                            str(uuid.uuid4()), client_id,
                            existing["packet_id"] or packet_id, "update", changed_by,
                            json.dumps(changed_field_names),
                            json.dumps(prev_vals),
                            json.dumps(new_vals),
                            now,
                        ),
                    )
            else:
                fc_id = str(uuid.uuid4())
                insert_data: Dict[str, Any] = {
                    "id": fc_id,
                    "client_id": client_id,
                    "packet_id": packet_id,
                    "created_at": now,
                    "updated_at": now,
                    **safe,
                }
                cols = list(insert_data.keys())
                vals = list(insert_data.values())
                conn.execute(
                    f"INSERT INTO admissions_financial_coordination "
                    f"({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                    vals,
                )
                _create_fields = [k for k in safe if k not in _AUDIT_META]
                conn.execute(
                    """INSERT INTO admissions_financial_coordination_events
                       (id, client_id, packet_id, event_type, changed_by,
                        changed_fields_json, created_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (
                        str(uuid.uuid4()), client_id, packet_id, "create", changed_by,
                        json.dumps(_create_fields), now,
                    ),
                )
            row = conn.execute(
                "SELECT * FROM admissions_financial_coordination WHERE client_id = ?",
                (client_id,),
            ).fetchone()
            return self._fc_row_to_dict(row) if row else self.get_financial_coordination(client_id)

    # ── Templates endpoint ─────────────────────────────────────────────

    def get_templates(self) -> List[Dict[str, Any]]:
        return _load_manifest()

    # ── Internal helpers ───────────────────────────────────────────────

    def _seed_forms(self, conn: sqlite3.Connection, packet_id: str, now: str) -> None:
        forms = _load_manifest()
        for form in forms:
            expires_at = None
            if form.get("expires_in_days"):
                expires_at = (
                    datetime.utcnow() + timedelta(days=form["expires_in_days"])
                ).isoformat()
            conn.execute(
                """INSERT OR IGNORE INTO admission_packet_forms
                   (id, packet_id, form_key, form_name, category, status, required,
                    timing_group, timing_label, requires_signature, signatures_required,
                    allow_attachments, allow_revocation, expires_in_days, expires_at,
                    review_status, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()),
                    packet_id,
                    form["form_key"],
                    form["form_name"],
                    form.get("category", ""),
                    "Not Started",
                    1 if form.get("required") else 0,
                    form.get("timing_group", "admission"),
                    form.get("timing_label", "Required at Admission"),
                    1 if form.get("requires_signature") else 0,
                    json.dumps(form.get("signatures_required", [])),
                    1 if form.get("allow_attachments") else 0,
                    1 if form.get("allow_revocation") else 0,
                    form.get("expires_in_days"),
                    expires_at,
                    "Not Reviewed",
                    now,
                    now,
                ),
            )

    def _get_forms(self, conn: sqlite3.Connection, packet_id: str) -> List[Dict[str, Any]]:
        rows = conn.execute(
            """SELECT f.*,
                   (SELECT COUNT(*) FROM admission_form_attachments a
                    WHERE a.packet_id = f.packet_id AND a.form_key = f.form_key) AS attachment_count
               FROM admission_packet_forms f
               WHERE f.packet_id = ?
               ORDER BY CASE f.timing_group
                   WHEN 'admission' THEN 1
                   WHEN '72_hours'  THEN 2
                   WHEN '7_days'    THEN 3
                   ELSE 4 END,
               f.form_key""",
            (packet_id,),
        ).fetchall()
        return [self._form_row_to_dict(r) for r in rows]

    @staticmethod
    def _form_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        try:
            d["signatures_required"] = json.loads(d.get("signatures_required") or "[]")
        except (ValueError, TypeError):
            d["signatures_required"] = []
        d["required"] = bool(d.get("required"))
        d["requires_signature"] = bool(d.get("requires_signature"))
        d["allow_attachments"] = bool(d.get("allow_attachments"))
        d["allow_revocation"] = bool(d.get("allow_revocation"))
        # Ensure Phase 5 columns have safe defaults for pre-migration rows
        if not d.get("review_status"):
            d["review_status"] = "Not Reviewed"
        return d

    @staticmethod
    def _packet_row_to_dict(row: sqlite3.Row | Dict[str, Any]) -> Dict[str, Any]:
        d = dict(row)
        raw_profile = d.pop("shared_profile_json", "{}")
        try:
            d["shared_profile"] = json.loads(raw_profile or "{}")
        except (TypeError, ValueError):
            d["shared_profile"] = {}
        return d

    @staticmethod
    def _fc_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        for col in _FC_BOOL_COLUMNS:
            if col in d:
                d[col] = bool(d[col])
        d["exists"] = True
        return d


# Singleton is created in store_factory.py (SQLite dev / Postgres production).
