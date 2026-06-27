"""
Shared SQLite-backed storage for lightweight workspace content.
"""

from __future__ import annotations

import logging
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from backend.shared.db_path import DB_DIR
from backend.shared.tenancy import DEFAULT_ORG_ID

logger = logging.getLogger(__name__)

# Phase 3C multi-tenancy: tables that carry an org_id.
# Case-manager-scoped tables are the active enforcement targets (dashboard items
# + rolodex). Client-linked tables get org_id for defense-in-depth only; their
# route enforcement continues to rely on assert_client_access (Phase 1).
_ORG_ENFORCED_TABLES = (
    "dashboard_notes",
    "dashboard_docs",
    "dashboard_bookmarks",
    "dashboard_resources",
    "case_manager_rolodex",
)
_ORG_DEFENSE_TABLES = (
    "client_notes",
    "client_tasks",
    "client_treatment_plans",
    "client_operational_needs",
    "client_appointments",
    "client_service_referrals",
    "client_documents",
    "roi_records",
)


class WorkspaceStore:
    """Persist lightweight notes, tasks, and dashboard content in SQLite."""

    def __init__(self) -> None:
        # Resolve from the central DB_DIR so production persists on the Railway
        # volume (RAILWAY_VOLUME_MOUNT_PATH -> /mnt/data/databases) and the SaaS
        # harness/tests honor CMSX_DB_DIR — exactly like every other store.
        #
        # Previously this hardcoded a repo-relative path (project_root/databases).
        # That path is both ephemeral on Railway AND a git-tracked file, so every
        # deploy/restart overwrote runtime data (client ROI records, notes, tasks,
        # documents, etc.) with the stale committed snapshot — the cause of newly
        # created ROI records disappearing on refresh.
        self.db_path = DB_DIR / "workspace_content.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        # Ensure the parent dir exists for whatever db_path is currently set
        # (volume path in prod, tmp dir under tests), mirroring the other stores.
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS client_notes (
                    note_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    title TEXT,
                    note_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_by TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS client_tasks (
                    task_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    task_type TEXT,
                    due_date TEXT,
                    assigned_to TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    source TEXT,
                    source_id TEXT,
                    need_key TEXT,
                    module TEXT,
                    ai_generated INTEGER NOT NULL DEFAULT 0,
                    requires_case_manager_approval INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS dashboard_notes (
                    id TEXT PRIMARY KEY,
                    case_manager_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    pinned INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dashboard_docs (
                    id TEXT PRIMARY KEY,
                    case_manager_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    url TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dashboard_bookmarks (
                    id TEXT PRIMARY KEY,
                    case_manager_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    description TEXT,
                    favicon TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dashboard_resources (
                    id TEXT PRIMARY KEY,
                    case_manager_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    uploaded_at TEXT NOT NULL,
                    file_path TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS documentation_brand_resources (
                    id TEXT PRIMARY KEY,
                    case_manager_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    size INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    extracted_text TEXT,
                    extraction_status TEXT NOT NULL,
                    uploaded_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS case_manager_rolodex (
                    id TEXT PRIMARY KEY,
                    case_manager_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    custom_category TEXT,
                    organization TEXT,
                    role_title TEXT,
                    phone TEXT,
                    email TEXT,
                    website TEXT,
                    address TEXT,
                    city TEXT,
                    trusted_status TEXT,
                    availability_notes TEXT,
                    referral_notes TEXT,
                    general_notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS client_treatment_plans (
                    plan_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_by TEXT,
                    approved_by TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    approved_at TEXT,
                    review_due_date TEXT,
                    problems_json TEXT NOT NULL DEFAULT '[]',
                    goals_json TEXT NOT NULL DEFAULT '[]',
                    objectives_json TEXT NOT NULL DEFAULT '[]',
                    interventions_json TEXT NOT NULL DEFAULT '[]',
                    target_dates_json TEXT NOT NULL DEFAULT '[]',
                    aftercare_plan_json TEXT NOT NULL DEFAULT '{}',
                    completion_criteria_json TEXT NOT NULL DEFAULT '[]',
                    operational_needs_json TEXT NOT NULL DEFAULT '[]',
                    raw_suggestions_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_client_treatment_plans_client
                ON client_treatment_plans (client_id, status, updated_at);

                CREATE TABLE IF NOT EXISTS client_operational_needs (
                    need_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    need_key TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    module TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_id TEXT,
                    source_plan_id TEXT,
                    reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    resolved_at TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_client_operational_needs_client
                ON client_operational_needs (client_id, status, priority);

                CREATE INDEX IF NOT EXISTS idx_client_operational_needs_dedupe
                ON client_operational_needs (client_id, need_key, source, source_id);

                CREATE TABLE IF NOT EXISTS client_appointments (
                    apt_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    appointment_date TEXT NOT NULL,
                    appointment_time TEXT,
                    location TEXT,
                    doctor_name TEXT,
                    service_type TEXT,
                    status TEXT NOT NULL DEFAULT 'scheduled',
                    notes TEXT,
                    items_to_bring TEXT,
                    reminder_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_client_appointments_client
                ON client_appointments (client_id, appointment_date);

                CREATE TABLE IF NOT EXISTS client_service_referrals (
                    ref_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    service_type TEXT,
                    provider_name TEXT,
                    phone TEXT,
                    address TEXT,
                    url TEXT,
                    appointment_time TEXT,
                    doctor_name TEXT,
                    items_to_bring TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    notes TEXT,
                    referral_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_client_service_referrals_client
                ON client_service_referrals (client_id, referral_date);

                CREATE TABLE IF NOT EXISTS client_documents (
                    doc_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    doc_type TEXT NOT NULL DEFAULT 'other',
                    file_name TEXT,
                    file_size INTEGER,
                    file_mime TEXT,
                    file_path TEXT,
                    url TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_client_documents_client
                ON client_documents (client_id, created_at);

                CREATE TABLE IF NOT EXISTS roi_records (
                    roi_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    authorized_party TEXT NOT NULL,
                    relationship_type TEXT,
                    party_address TEXT,
                    party_contact TEXT,
                    purpose TEXT,
                    info_to_release TEXT NOT NULL DEFAULT '[]',
                    release_method TEXT,
                    effective_date TEXT,
                    expiration_date TEXT,
                    revocable INTEGER NOT NULL DEFAULT 1,
                    revoked INTEGER NOT NULL DEFAULT 0,
                    revoked_at TEXT,
                    status TEXT NOT NULL DEFAULT 'draft',
                    linked_document_id TEXT,
                    source TEXT NOT NULL DEFAULT 'created_in_ember',
                    created_by TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_roi_records_client
                ON roi_records (client_id, created_at);

                CREATE INDEX IF NOT EXISTS idx_roi_records_client_status
                ON roi_records (client_id, status);
                """
            )
            note_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(client_notes)").fetchall()
            }
            if "title" not in note_columns:
                conn.execute("ALTER TABLE client_notes ADD COLUMN title TEXT")

            task_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(client_tasks)").fetchall()
            }
            task_column_definitions = {
                "source": "TEXT",
                "source_id": "TEXT",
                "need_key": "TEXT",
                "module": "TEXT",
                "ai_generated": "INTEGER NOT NULL DEFAULT 0",
                "requires_case_manager_approval": "INTEGER NOT NULL DEFAULT 0",
            }
            for column, definition in task_column_definitions.items():
                if column not in task_columns:
                    conn.execute(f"ALTER TABLE client_tasks ADD COLUMN {column} {definition}")

            # Phase 3C: additive, idempotent org_id on workspace tables. Backfill
            # NULL/blank -> DEFAULT_ORG_ID so single-agency behavior is unchanged
            # while MULTI_TENANT_ENABLED is false. Indexes only on the enforced
            # (case-manager-scoped) tables.
            for table in _ORG_ENFORCED_TABLES + _ORG_DEFENSE_TABLES:
                existing = {
                    row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
                }
                if "org_id" not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN org_id TEXT")
                conn.execute(
                    f"UPDATE {table} SET org_id = ? WHERE org_id IS NULL OR TRIM(org_id) = ''",
                    (DEFAULT_ORG_ID,),
                )
            for table in _ORG_ENFORCED_TABLES:
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{table}_org ON {table}(org_id)"
                )
            conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return dict(row)

    @staticmethod
    def _json_dumps(value: Any, fallback: Any) -> str:
        if value in (None, ""):
            return json.dumps(fallback)
        if isinstance(value, str):
            try:
                json.loads(value)
                return value
            except Exception:
                return json.dumps(value)
        return json.dumps(value)

    @staticmethod
    def _json_loads(value: Any, fallback: Any) -> Any:
        if value in (None, ""):
            return fallback
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return fallback

    def _plan_row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        plan = self._row_to_dict(row)
        plan["problems"] = self._json_loads(plan.pop("problems_json", None), [])
        plan["goals"] = self._json_loads(plan.pop("goals_json", None), [])
        plan["objectives"] = self._json_loads(plan.pop("objectives_json", None), [])
        plan["interventions"] = self._json_loads(plan.pop("interventions_json", None), [])
        plan["target_dates"] = self._json_loads(plan.pop("target_dates_json", None), [])
        plan["aftercare_plan"] = self._json_loads(plan.pop("aftercare_plan_json", None), {})
        plan["completion_criteria"] = self._json_loads(plan.pop("completion_criteria_json", None), [])
        plan["operational_needs"] = self._json_loads(plan.pop("operational_needs_json", None), [])
        plan["raw_suggestions"] = self._json_loads(plan.pop("raw_suggestions_json", None), {})
        return plan

    def list_client_treatment_plans(self, client_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM client_treatment_plans
                WHERE client_id = ?
                ORDER BY
                    CASE status
                        WHEN 'active' THEN 0
                        WHEN 'review_due' THEN 1
                        WHEN 'draft' THEN 2
                        ELSE 3
                    END,
                    COALESCE(approved_at, updated_at, created_at) DESC
                """,
                (client_id,),
            ).fetchall()
        return [self._plan_row_to_dict(row) for row in rows]

    def get_current_treatment_plan(self, client_id: str) -> Optional[Dict[str, Any]]:
        plans = self.list_client_treatment_plans(client_id)
        return plans[0] if plans else None

    def get_treatment_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM client_treatment_plans WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()
        return self._plan_row_to_dict(row) if row else None

    def create_treatment_plan_draft(
        self,
        client_id: str,
        created_by: str,
        plan_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        now = self._now()
        plan = {
            "plan_id": plan_data.get("plan_id") or f"txp_{uuid4().hex[:12]}",
            "client_id": client_id,
            "status": "draft",
            "source": plan_data.get("source") or "case_manager",
            "created_by": created_by or "",
            "approved_by": None,
            "created_at": now,
            "updated_at": now,
            "approved_at": None,
            "review_due_date": plan_data.get("review_due_date"),
            "problems": plan_data.get("problems") or [],
            "goals": plan_data.get("goals") or [],
            "objectives": plan_data.get("objectives") or [],
            "interventions": plan_data.get("interventions") or [],
            "target_dates": plan_data.get("target_dates") or [],
            "aftercare_plan": plan_data.get("aftercare_plan") or {},
            "completion_criteria": plan_data.get("completion_criteria") or [],
            "operational_needs": plan_data.get("operational_needs") or [],
            "raw_suggestions": plan_data.get("raw_suggestions") or {},
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO client_treatment_plans (
                    plan_id, client_id, status, source, created_by, approved_by,
                    created_at, updated_at, approved_at, review_due_date,
                    problems_json, goals_json, objectives_json, interventions_json,
                    target_dates_json, aftercare_plan_json, completion_criteria_json,
                    operational_needs_json, raw_suggestions_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan["plan_id"],
                    plan["client_id"],
                    plan["status"],
                    plan["source"],
                    plan["created_by"],
                    plan["approved_by"],
                    plan["created_at"],
                    plan["updated_at"],
                    plan["approved_at"],
                    plan["review_due_date"],
                    self._json_dumps(plan["problems"], []),
                    self._json_dumps(plan["goals"], []),
                    self._json_dumps(plan["objectives"], []),
                    self._json_dumps(plan["interventions"], []),
                    self._json_dumps(plan["target_dates"], []),
                    self._json_dumps(plan["aftercare_plan"], {}),
                    self._json_dumps(plan["completion_criteria"], []),
                    self._json_dumps(plan["operational_needs"], []),
                    self._json_dumps(plan["raw_suggestions"], {}),
                ),
            )
            conn.commit()
        return plan

    def update_treatment_plan(self, plan_id: str, plan_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        existing = self.get_treatment_plan(plan_id)
        if not existing:
            return None
        if existing["status"] == "active":
            plan_data = {key: value for key, value in plan_data.items() if key in {"review_due_date"}}

        updated = {**existing, **{key: value for key, value in plan_data.items() if value is not None}}
        updated["updated_at"] = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE client_treatment_plans
                SET updated_at = ?, review_due_date = ?, problems_json = ?, goals_json = ?,
                    objectives_json = ?, interventions_json = ?, target_dates_json = ?,
                    aftercare_plan_json = ?, completion_criteria_json = ?, operational_needs_json = ?,
                    raw_suggestions_json = ?
                WHERE plan_id = ?
                """,
                (
                    updated["updated_at"],
                    updated.get("review_due_date"),
                    self._json_dumps(updated.get("problems"), []),
                    self._json_dumps(updated.get("goals"), []),
                    self._json_dumps(updated.get("objectives"), []),
                    self._json_dumps(updated.get("interventions"), []),
                    self._json_dumps(updated.get("target_dates"), []),
                    self._json_dumps(updated.get("aftercare_plan"), {}),
                    self._json_dumps(updated.get("completion_criteria"), []),
                    self._json_dumps(updated.get("operational_needs"), []),
                    self._json_dumps(updated.get("raw_suggestions"), {}),
                    plan_id,
                ),
            )
            conn.commit()
        return self.get_treatment_plan(plan_id)

    def approve_treatment_plan(self, plan_id: str, approved_by: str) -> Optional[Dict[str, Any]]:
        existing = self.get_treatment_plan(plan_id)
        if not existing:
            return None
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE client_treatment_plans
                SET status = 'superseded', updated_at = ?
                WHERE client_id = ? AND plan_id != ? AND status IN ('active', 'review_due')
                """,
                (now, existing["client_id"], plan_id),
            )
            conn.execute(
                """
                UPDATE client_treatment_plans
                SET status = 'active', approved_by = ?, approved_at = ?, updated_at = ?
                WHERE plan_id = ?
                """,
                (approved_by or "", now, now, plan_id),
            )
            conn.commit()
        return self.get_treatment_plan(plan_id)

    @staticmethod
    def _module_for_need(domain: str, need_key: str) -> str:
        if domain == "resume":
            return "resume"
        if domain == "employment":
            return "jobs"
        if domain == "sober_living":
            return "sober_living"
        if domain in {"housing", "medical", "benefits", "legal", "services"}:
            return domain
        if need_key in {"transportation"}:
            return "services"
        return "case_management"

    def _need_row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        need = self._row_to_dict(row)
        need["metadata"] = self._json_loads(need.pop("metadata_json", None), {})
        return need

    def list_client_operational_needs(self, client_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM client_operational_needs
                WHERE client_id = ?
                ORDER BY
                    CASE priority
                        WHEN 'urgent' THEN 0
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        ELSE 3
                    END,
                    updated_at DESC
                """,
                (client_id,),
            ).fetchall()
        return [self._need_row_to_dict(row) for row in rows]

    def upsert_operational_need(
        self,
        client_id: str,
        need: Dict[str, Any],
        source: str,
        source_id: Optional[str] = None,
        source_plan_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        need_key = str(need.get("need_key") or "").strip().lower()
        domain = str(need.get("domain") or "case_management").strip().lower()
        source_id = source_id or source_plan_id or need.get("source_id") or ""
        now = self._now()
        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT *
                FROM client_operational_needs
                WHERE client_id = ? AND need_key = ? AND source = ? AND COALESCE(source_id, '') = ?
                """,
                (client_id, need_key, source, source_id),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE client_operational_needs
                    SET domain = ?, module = ?, priority = ?, status = ?, source_plan_id = ?,
                        reason = ?, updated_at = ?, metadata_json = ?
                    WHERE need_id = ?
                    """,
                    (
                        domain,
                        need.get("module") or self._module_for_need(domain, need_key),
                        need.get("priority") or "medium",
                        need.get("status") or "active",
                        source_plan_id,
                        need.get("reason") or "",
                        now,
                        self._json_dumps(need.get("metadata") or {}, {}),
                        existing["need_id"],
                    ),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM client_operational_needs WHERE need_id = ?",
                    (existing["need_id"],),
                ).fetchone()
                return self._need_row_to_dict(row)

            need_id = f"need_{uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO client_operational_needs (
                    need_id, client_id, need_key, domain, module, priority, status,
                    source, source_id, source_plan_id, reason, created_at, updated_at,
                    resolved_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    need_id,
                    client_id,
                    need_key,
                    domain,
                    need.get("module") or self._module_for_need(domain, need_key),
                    need.get("priority") or "medium",
                    need.get("status") or "active",
                    source,
                    source_id,
                    source_plan_id,
                    need.get("reason") or "",
                    now,
                    now,
                    None,
                    self._json_dumps(need.get("metadata") or {}, {}),
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM client_operational_needs WHERE need_id = ?", (need_id,)).fetchone()
            return self._need_row_to_dict(row)

    def upsert_operational_needs(
        self,
        client_id: str,
        needs: List[Dict[str, Any]],
        source: str,
        source_id: Optional[str] = None,
        source_plan_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return [
            self.upsert_operational_need(client_id, need, source, source_id, source_plan_id)
            for need in needs
            if need.get("need_key")
        ]

    @staticmethod
    def _task_title_for_need(need: Dict[str, Any]) -> str:
        labels = {
            "dental": "Book dental appointment",
            "primary_care": "Schedule primary care follow-up",
            "behavioral_health": "Coordinate behavioral health follow-up",
            "disability": "Start disability benefits screening",
            "benefits_screening": "Complete benefits eligibility screening",
            "legal_follow_up": "Review legal follow-up needs",
            "housing": "Review housing placement options",
            "sober_living_aftercare": "Review sober living aftercare options",
            "resume": "Create or update client resume",
            "job_search": "Start background-friendly job search",
            "transportation": "Arrange transportation support",
        }
        return labels.get(need.get("need_key"), f"Follow up on {str(need.get('need_key')).replace('_', ' ')}")

    def create_tasks_from_operational_needs(
        self,
        client_id: str,
        needs: List[Dict[str, Any]],
        source: str,
        source_id: str,
        assigned_to: str,
    ) -> List[Dict[str, Any]]:
        created_tasks: List[Dict[str, Any]] = []
        with self._connect() as conn:
            for need in needs:
                need_key = need.get("need_key")
                if not need_key:
                    continue
                existing = conn.execute(
                    """
                    SELECT task_id
                    FROM client_tasks
                    WHERE client_id = ?
                      AND need_key = ?
                      AND COALESCE(source_id, '') = ?
                      AND COALESCE(source, '') = ?
                      AND LOWER(COALESCE(status, 'pending')) NOT IN ('completed', 'done', 'cancelled', 'canceled')
                    LIMIT 1
                    """,
                    (client_id, need_key, source_id or "", source),
                ).fetchone()
                if existing:
                    continue
                task = self.create_client_task(
                    client_id,
                    {
                        "title": self._task_title_for_need(need),
                        "description": need.get("reason") or "Generated from approved treatment-plan need.",
                        "priority": need.get("priority") or "medium",
                        "status": "pending",
                        "task_type": "treatment_plan_need",
                        "assigned_to": assigned_to or "Case Manager",
                        "source": source,
                        "source_id": source_id,
                        "need_key": need_key,
                        "module": need.get("module") or self._module_for_need(need.get("domain", ""), need_key),
                        "ai_generated": 1 if need.get("source") == "ai_suggestion" else 0,
                        "requires_case_manager_approval": 0,
                    },
                )
                created_tasks.append(task)
        return created_tasks

    def update_need_status_by_key(
        self,
        client_id: str,
        need_key: str,
        status: str,
        priority: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> int:
        """Update status (and optionally priority/reason) for all needs matching need_key for a client.
        Returns the number of rows updated."""
        now = self._now()
        resolved_at = now if status in {"completed", "cancelled", "canceled"} else None
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE client_operational_needs
                SET status = ?,
                    priority = COALESCE(?, priority),
                    reason = COALESCE(?, reason),
                    resolved_at = CASE WHEN ? = 1 THEN ? ELSE resolved_at END,
                    updated_at = ?
                WHERE client_id = ? AND need_key = ?
                """,
                (
                    status,
                    priority,
                    reason,
                    1 if resolved_at else 0,
                    resolved_at,
                    now,
                    client_id,
                    need_key,
                ),
            )
            conn.commit()
            return cursor.rowcount

    def list_client_notes(self, client_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT note_id, client_id, title, note_type, content, created_by, created_at, updated_at
                FROM client_notes
                WHERE client_id = ?
                ORDER BY created_at DESC
                """,
                (client_id,),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def create_client_note(
        self,
        client_id: str,
        note_type: str,
        content: str,
        created_by: str,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        note = {
            "note_id": f"note_{uuid4().hex[:12]}",
            "client_id": client_id,
            "title": title or "",
            "note_type": note_type or "General",
            "content": content,
            "created_by": created_by or "Case Manager",
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO client_notes (note_id, client_id, title, note_type, content, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    note["note_id"],
                    note["client_id"],
                    note["title"],
                    note["note_type"],
                    note["content"],
                    note["created_by"],
                    note["created_at"],
                    note["updated_at"],
                ),
            )
            conn.commit()
        return note

    def update_client_note(
        self,
        note_id: str,
        note_type: str,
        content: str,
        created_by: Optional[str],
        title: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM client_notes WHERE note_id = ?",
                (note_id,),
            ).fetchone()
            if not existing:
                return None
            updated_at = self._now()
            conn.execute(
                """
                UPDATE client_notes
                SET title = ?, note_type = ?, content = ?, created_by = ?, updated_at = ?
                WHERE note_id = ?
                """,
                (
                    title if title is not None else existing["title"],
                    note_type or existing["note_type"],
                    content,
                    created_by or existing["created_by"],
                    updated_at,
                    note_id,
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM client_notes WHERE note_id = ?", (note_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def get_client_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM client_notes WHERE note_id = ?", (note_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def delete_client_note(self, note_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM client_notes WHERE note_id = ?", (note_id,))
            conn.commit()
            return cursor.rowcount > 0

    def list_client_tasks(self, client_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT task_id, client_id, title, description, priority, status, task_type,
                       due_date, assigned_to, created_at, updated_at, completed_at,
                       source, source_id, need_key, module, ai_generated, requires_case_manager_approval
                FROM client_tasks
                WHERE client_id = ?
                ORDER BY COALESCE(due_date, '9999-12-31'), created_at DESC
                """,
                (client_id,),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def create_client_task(self, client_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        task = {
            "task_id": f"task_{uuid4().hex[:12]}",
            "client_id": client_id,
            "title": task_data.get("title", ""),
            "description": task_data.get("description", ""),
            "priority": task_data.get("priority", "medium"),
            "status": task_data.get("status", "pending"),
            "task_type": task_data.get("task_type", "general"),
            "due_date": task_data.get("due_date"),
            "assigned_to": task_data.get("assigned_to", "Case Manager"),
            "created_at": self._now(),
            "updated_at": self._now(),
            "completed_at": task_data.get("completed_at"),
            "source": task_data.get("source"),
            "source_id": task_data.get("source_id"),
            "need_key": task_data.get("need_key"),
            "module": task_data.get("module"),
            "ai_generated": int(bool(task_data.get("ai_generated"))),
            "requires_case_manager_approval": int(bool(task_data.get("requires_case_manager_approval"))),
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO client_tasks (
                    task_id, client_id, title, description, priority, status, task_type,
                    due_date, assigned_to, created_at, updated_at, completed_at,
                    source, source_id, need_key, module, ai_generated, requires_case_manager_approval
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task["task_id"],
                    task["client_id"],
                    task["title"],
                    task["description"],
                    task["priority"],
                    task["status"],
                    task["task_type"],
                    task["due_date"],
                    task["assigned_to"],
                    task["created_at"],
                    task["updated_at"],
                    task["completed_at"],
                    task["source"],
                    task["source_id"],
                    task["need_key"],
                    task["module"],
                    task["ai_generated"],
                    task["requires_case_manager_approval"],
                ),
            )
            conn.commit()
        return task

    def update_client_task(self, task_id: str, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM client_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if not existing:
                return None

            status = task_data.get("status", existing["status"])
            completed_at = existing["completed_at"]
            if status == "completed" and not completed_at:
                completed_at = self._now()

            conn.execute(
                """
                UPDATE client_tasks
                SET title = ?, description = ?, priority = ?, status = ?, task_type = ?,
                    due_date = ?, assigned_to = ?, updated_at = ?, completed_at = ?
                WHERE task_id = ?
                """,
                (
                    task_data.get("title", existing["title"]),
                    task_data.get("description", existing["description"]),
                    task_data.get("priority", existing["priority"]),
                    status,
                    task_data.get("task_type", existing["task_type"]),
                    task_data.get("due_date", existing["due_date"]),
                    task_data.get("assigned_to", existing["assigned_to"]),
                    self._now(),
                    completed_at,
                    task_id,
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM client_tasks WHERE task_id = ?", (task_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def get_client_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM client_tasks WHERE task_id = ?", (task_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def delete_client_task(self, task_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM client_tasks WHERE task_id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    def list_dashboard_items(self, table: str, case_manager_id: str, org_id: Optional[str] = None) -> List[Dict[str, Any]]:
        order_by = {
            "dashboard_notes": "pinned DESC, created_at DESC",
            "dashboard_docs": "created_at DESC",
            "dashboard_bookmarks": "created_at DESC",
            "dashboard_resources": "uploaded_at DESC",
            "case_manager_rolodex": "category ASC, name ASC, updated_at DESC",
        }[table]
        # Phase 3C: org_id filter applied only when supplied (callers pass it
        # while MULTI_TENANT_ENABLED is true). None preserves prior behavior.
        clause = "WHERE case_manager_id = ?"
        params: List[Any] = [case_manager_id]
        if org_id is not None:
            clause += " AND org_id = ?"
            params.append(org_id)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM {table} {clause} ORDER BY {order_by}",
                tuple(params),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def create_dashboard_note(self, case_manager_id: str, content: str, pinned: bool, org_id: str = DEFAULT_ORG_ID) -> Dict[str, Any]:
        item = {
            "id": uuid4().hex,
            "case_manager_id": case_manager_id,
            "content": content,
            "pinned": 1 if pinned else 0,
            "created_at": self._now(),
            "updated_at": self._now(),
            "org_id": org_id,
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dashboard_notes (id, case_manager_id, content, pinned, created_at, updated_at, org_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (item["id"], item["case_manager_id"], item["content"], item["pinned"], item["created_at"], item["updated_at"], item["org_id"]),
            )
            conn.commit()
        item["pinned"] = bool(item["pinned"])
        return item

    def update_dashboard_note(self, note_id: str, content: str, pinned: bool, org_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        # Phase 3C: when org_id is supplied (flag on), scope the update so a
        # cross-org item is not modified (rowcount 0 -> caller returns 404).
        where = "WHERE id = ?"
        params: List[Any] = [content, 1 if pinned else 0, self._now(), note_id]
        if org_id is not None:
            where += " AND org_id = ?"
            params.append(org_id)
        with self._connect() as conn:
            cursor = conn.execute(
                f"""
                UPDATE dashboard_notes
                SET content = ?, pinned = ?, updated_at = ?
                {where}
                """,
                tuple(params),
            )
            if cursor.rowcount == 0:
                return None
            conn.commit()
            row = conn.execute("SELECT * FROM dashboard_notes WHERE id = ?", (note_id,)).fetchone()
        item = self._row_to_dict(row) if row else None
        if item:
            item["pinned"] = bool(item["pinned"])
        return item

    def create_dashboard_doc(self, case_manager_id: str, title: str, content: str, url: Optional[str], org_id: str = DEFAULT_ORG_ID) -> Dict[str, Any]:
        item = {
            "id": uuid4().hex,
            "case_manager_id": case_manager_id,
            "title": title,
            "content": content,
            "url": url,
            "created_at": self._now(),
            "updated_at": self._now(),
            "org_id": org_id,
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dashboard_docs (id, case_manager_id, title, content, url, created_at, updated_at, org_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (item["id"], item["case_manager_id"], item["title"], item["content"], item["url"], item["created_at"], item["updated_at"], item["org_id"]),
            )
            conn.commit()
        return item

    def update_dashboard_doc(self, doc_id: str, title: str, content: str, url: Optional[str], org_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        # Phase 3C: org-scope the update when org_id is supplied (flag on).
        where = "WHERE id = ?"
        params: List[Any] = [title, content, url, self._now(), doc_id]
        if org_id is not None:
            where += " AND org_id = ?"
            params.append(org_id)
        with self._connect() as conn:
            cursor = conn.execute(
                f"""
                UPDATE dashboard_docs
                SET title = ?, content = ?, url = ?, updated_at = ?
                {where}
                """,
                tuple(params),
            )
            if cursor.rowcount == 0:
                return None
            conn.commit()
            row = conn.execute("SELECT * FROM dashboard_docs WHERE id = ?", (doc_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def get_dashboard_doc(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM dashboard_docs WHERE id = ?", (doc_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def create_dashboard_bookmark(self, case_manager_id: str, title: str, url: str, description: Optional[str], favicon: Optional[str], org_id: str = DEFAULT_ORG_ID) -> Dict[str, Any]:
        item = {
            "id": uuid4().hex,
            "case_manager_id": case_manager_id,
            "title": title,
            "url": url,
            "description": description,
            "favicon": favicon,
            "created_at": self._now(),
            "org_id": org_id,
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dashboard_bookmarks (id, case_manager_id, title, url, description, favicon, created_at, org_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (item["id"], item["case_manager_id"], item["title"], item["url"], item["description"], item["favicon"], item["created_at"], item["org_id"]),
            )
            conn.commit()
        return item

    def create_dashboard_resource(self, case_manager_id: str, resource_id: str, name: str, size: int, content_type: str, file_path: str, org_id: str = DEFAULT_ORG_ID) -> Dict[str, Any]:
        item = {
            "id": resource_id,
            "case_manager_id": case_manager_id,
            "name": name,
            "size": size,
            "type": content_type,
            "uploaded_at": self._now(),
            "file_path": file_path,
            "org_id": org_id,
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dashboard_resources (id, case_manager_id, name, size, type, uploaded_at, file_path, org_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (item["id"], item["case_manager_id"], item["name"], item["size"], item["type"], item["uploaded_at"], item["file_path"], item["org_id"]),
            )
            conn.commit()
        return item

    def delete_dashboard_item(self, table: str, item_id: str, org_id: Optional[str] = None) -> bool:
        # Phase 3C: when org_id is supplied (flag on), a cross-org delete matches
        # no row (returns False -> caller returns 404). None = prior behavior.
        where = "WHERE id = ?"
        params: List[Any] = [item_id]
        if org_id is not None:
            where += " AND org_id = ?"
            params.append(org_id)
        with self._connect() as conn:
            cursor = conn.execute(f"DELETE FROM {table} {where}", tuple(params))
            conn.commit()
            return cursor.rowcount > 0

    def get_dashboard_resource(self, resource_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM dashboard_resources WHERE id = ?",
                (resource_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_brand_resources(self, case_manager_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM documentation_brand_resources
                WHERE case_manager_id = ?
                ORDER BY uploaded_at DESC
                """,
                (case_manager_id,),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def create_brand_resource(
        self,
        case_manager_id: str,
        resource_id: str,
        name: str,
        category: str,
        description: Optional[str],
        size: int,
        content_type: str,
        file_path: str,
        extracted_text: Optional[str],
        extraction_status: str,
    ) -> Dict[str, Any]:
        item = {
            "id": resource_id,
            "case_manager_id": case_manager_id,
            "name": name,
            "category": category,
            "description": description,
            "size": size,
            "type": content_type,
            "file_path": file_path,
            "extracted_text": extracted_text or "",
            "extraction_status": extraction_status,
            "uploaded_at": self._now(),
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documentation_brand_resources (
                    id, case_manager_id, name, category, description, size, type,
                    file_path, extracted_text, extraction_status, uploaded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["id"],
                    item["case_manager_id"],
                    item["name"],
                    item["category"],
                    item["description"],
                    item["size"],
                    item["type"],
                    item["file_path"],
                    item["extracted_text"],
                    item["extraction_status"],
                    item["uploaded_at"],
                ),
            )
            conn.commit()
        return item

    def get_brand_resource(self, resource_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM documentation_brand_resources WHERE id = ?",
                (resource_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def delete_brand_resource(self, resource_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM documentation_brand_resources WHERE id = ?",
                (resource_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def list_rolodex_entries(self, case_manager_id: str, org_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.list_dashboard_items("case_manager_rolodex", case_manager_id, org_id=org_id)

    def create_rolodex_entry(self, case_manager_id: str, entry_data: Dict[str, Any], org_id: str = DEFAULT_ORG_ID) -> Dict[str, Any]:
        item = {
            "id": uuid4().hex,
            "case_manager_id": case_manager_id,
            "name": entry_data.get("name", "").strip(),
            "category": entry_data.get("category", "").strip(),
            "custom_category": (entry_data.get("custom_category") or "").strip(),
            "organization": (entry_data.get("organization") or "").strip(),
            "role_title": (entry_data.get("role_title") or "").strip(),
            "phone": (entry_data.get("phone") or "").strip(),
            "email": (entry_data.get("email") or "").strip(),
            "website": (entry_data.get("website") or "").strip(),
            "address": (entry_data.get("address") or "").strip(),
            "city": (entry_data.get("city") or "").strip(),
            "trusted_status": (entry_data.get("trusted_status") or "Trusted").strip(),
            "availability_notes": (entry_data.get("availability_notes") or "").strip(),
            "referral_notes": (entry_data.get("referral_notes") or "").strip(),
            "general_notes": (entry_data.get("general_notes") or "").strip(),
            "created_at": self._now(),
            "updated_at": self._now(),
            "org_id": org_id,
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO case_manager_rolodex (
                    id, case_manager_id, name, category, custom_category, organization, role_title,
                    phone, email, website, address, city, trusted_status, availability_notes,
                    referral_notes, general_notes, created_at, updated_at, org_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["id"],
                    item["case_manager_id"],
                    item["name"],
                    item["category"],
                    item["custom_category"],
                    item["organization"],
                    item["role_title"],
                    item["phone"],
                    item["email"],
                    item["website"],
                    item["address"],
                    item["city"],
                    item["trusted_status"],
                    item["availability_notes"],
                    item["referral_notes"],
                    item["general_notes"],
                    item["created_at"],
                    item["updated_at"],
                    item["org_id"],
                ),
            )
            conn.commit()
        return item

    def update_rolodex_entry(self, entry_id: str, entry_data: Dict[str, Any], org_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            # Phase 3C: when org_id is supplied (flag on), a cross-org entry is
            # not found here -> returns None -> caller returns 404.
            if org_id is not None:
                existing = conn.execute(
                    "SELECT * FROM case_manager_rolodex WHERE id = ? AND org_id = ?",
                    (entry_id, org_id),
                ).fetchone()
            else:
                existing = conn.execute(
                    "SELECT * FROM case_manager_rolodex WHERE id = ?",
                    (entry_id,),
                ).fetchone()
            if not existing:
                return None

            updated = {
                "name": entry_data.get("name", existing["name"]).strip(),
                "category": entry_data.get("category", existing["category"]).strip(),
                "custom_category": (entry_data.get("custom_category", existing["custom_category"]) or "").strip(),
                "organization": (entry_data.get("organization", existing["organization"]) or "").strip(),
                "role_title": (entry_data.get("role_title", existing["role_title"]) or "").strip(),
                "phone": (entry_data.get("phone", existing["phone"]) or "").strip(),
                "email": (entry_data.get("email", existing["email"]) or "").strip(),
                "website": (entry_data.get("website", existing["website"]) or "").strip(),
                "address": (entry_data.get("address", existing["address"]) or "").strip(),
                "city": (entry_data.get("city", existing["city"]) or "").strip(),
                "trusted_status": (entry_data.get("trusted_status", existing["trusted_status"]) or "Trusted").strip(),
                "availability_notes": (entry_data.get("availability_notes", existing["availability_notes"]) or "").strip(),
                "referral_notes": (entry_data.get("referral_notes", existing["referral_notes"]) or "").strip(),
                "general_notes": (entry_data.get("general_notes", existing["general_notes"]) or "").strip(),
                "updated_at": self._now(),
            }

            conn.execute(
                """
                UPDATE case_manager_rolodex
                SET name = ?, category = ?, custom_category = ?, organization = ?, role_title = ?,
                    phone = ?, email = ?, website = ?, address = ?, city = ?, trusted_status = ?,
                    availability_notes = ?, referral_notes = ?, general_notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    updated["name"],
                    updated["category"],
                    updated["custom_category"],
                    updated["organization"],
                    updated["role_title"],
                    updated["phone"],
                    updated["email"],
                    updated["website"],
                    updated["address"],
                    updated["city"],
                    updated["trusted_status"],
                    updated["availability_notes"],
                    updated["referral_notes"],
                    updated["general_notes"],
                    updated["updated_at"],
                    entry_id,
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM case_manager_rolodex WHERE id = ?", (entry_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def delete_rolodex_entry(self, entry_id: str, org_id: Optional[str] = None) -> bool:
        # Phase 3C: org-scope the delete when org_id is supplied (flag on).
        where = "WHERE id = ?"
        params: List[Any] = [entry_id]
        if org_id is not None:
            where += " AND org_id = ?"
            params.append(org_id)
        with self._connect() as conn:
            cursor = conn.execute(f"DELETE FROM case_manager_rolodex {where}", tuple(params))
            conn.commit()
            return cursor.rowcount > 0

    # ── Client Appointments ──────────────────────────────────────────────────

    def list_client_appointments(self, client_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM client_appointments WHERE client_id = ? ORDER BY appointment_date ASC, appointment_time ASC",
                (client_id,),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def create_client_appointment(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now()
        item = {
            "apt_id": uuid4().hex,
            "client_id": client_id,
            "title": data.get("title", "Appointment"),
            "appointment_date": data.get("appointment_date", ""),
            "appointment_time": data.get("appointment_time"),
            "location": data.get("location"),
            "doctor_name": data.get("doctor_name"),
            "service_type": data.get("service_type"),
            "status": data.get("status", "scheduled"),
            "notes": data.get("notes"),
            "items_to_bring": data.get("items_to_bring"),
            "reminder_id": data.get("reminder_id"),
            "created_at": now,
            "updated_at": now,
        }
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO client_appointments
                   (apt_id, client_id, title, appointment_date, appointment_time,
                    location, doctor_name, service_type, status, notes, items_to_bring,
                    reminder_id, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    item["apt_id"], item["client_id"], item["title"],
                    item["appointment_date"], item["appointment_time"],
                    item["location"], item["doctor_name"], item["service_type"],
                    item["status"], item["notes"], item["items_to_bring"],
                    item["reminder_id"], item["created_at"], item["updated_at"],
                ),
            )
            conn.commit()
        return item

    def update_client_appointment(self, apt_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        now = self._now()
        with self._connect() as conn:
            cursor = conn.execute(
                """UPDATE client_appointments
                   SET title=COALESCE(?,title), appointment_date=COALESCE(?,appointment_date),
                       appointment_time=?, location=?, doctor_name=?, service_type=?,
                       status=COALESCE(?,status), notes=?, items_to_bring=?, updated_at=?
                   WHERE apt_id=?""",
                (
                    data.get("title"), data.get("appointment_date"),
                    data.get("appointment_time"), data.get("location"),
                    data.get("doctor_name"), data.get("service_type"),
                    data.get("status"), data.get("notes"),
                    data.get("items_to_bring"), now, apt_id,
                ),
            )
            conn.commit()
            if cursor.rowcount == 0:
                return None
            row = conn.execute("SELECT * FROM client_appointments WHERE apt_id=?", (apt_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def delete_client_appointment(self, apt_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM client_appointments WHERE apt_id=?", (apt_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ── Client Service Referrals ─────────────────────────────────────────────

    def list_client_service_referrals(self, client_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM client_service_referrals WHERE client_id=? ORDER BY referral_date DESC",
                (client_id,),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def create_client_service_referral(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        from datetime import date
        now = self._now()
        item = {
            "ref_id": uuid4().hex,
            "client_id": client_id,
            "service_name": data.get("service_name", "Service"),
            "service_type": data.get("service_type"),
            "provider_name": data.get("provider_name"),
            "phone": data.get("phone"),
            "address": data.get("address"),
            "url": data.get("url"),
            "appointment_time": data.get("appointment_time"),
            "doctor_name": data.get("doctor_name"),
            "items_to_bring": data.get("items_to_bring"),
            "status": data.get("status", "pending"),
            "notes": data.get("notes"),
            "referral_date": data.get("referral_date", str(date.today())),
            "created_at": now,
            "updated_at": now,
        }
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO client_service_referrals
                   (ref_id, client_id, service_name, service_type, provider_name, phone,
                    address, url, appointment_time, doctor_name, items_to_bring, status,
                    notes, referral_date, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    item["ref_id"], item["client_id"], item["service_name"],
                    item["service_type"], item["provider_name"], item["phone"],
                    item["address"], item["url"], item["appointment_time"],
                    item["doctor_name"], item["items_to_bring"], item["status"],
                    item["notes"], item["referral_date"], item["created_at"], item["updated_at"],
                ),
            )
            conn.commit()
        return item

    def update_client_service_referral(self, ref_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        now = self._now()
        with self._connect() as conn:
            cursor = conn.execute(
                """UPDATE client_service_referrals
                   SET service_name=COALESCE(?,service_name), service_type=?,
                       provider_name=?, phone=?, address=?, url=?,
                       appointment_time=?, doctor_name=?, items_to_bring=?,
                       status=COALESCE(?,status), notes=?, updated_at=?
                   WHERE ref_id=?""",
                (
                    data.get("service_name"), data.get("service_type"),
                    data.get("provider_name"), data.get("phone"),
                    data.get("address"), data.get("url"),
                    data.get("appointment_time"), data.get("doctor_name"),
                    data.get("items_to_bring"), data.get("status"),
                    data.get("notes"), now, ref_id,
                ),
            )
            conn.commit()
            if cursor.rowcount == 0:
                return None
            row = conn.execute("SELECT * FROM client_service_referrals WHERE ref_id=?", (ref_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def delete_client_service_referral(self, ref_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM client_service_referrals WHERE ref_id=?", (ref_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ── Client Documents ─────────────────────────────────────────────────────

    def list_client_documents(self, client_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM client_documents WHERE client_id=? ORDER BY created_at DESC",
                (client_id,),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def create_client_document(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now()
        item = {
            "doc_id": uuid4().hex,
            "client_id": client_id,
            "title": data.get("title", "Document"),
            "doc_type": data.get("doc_type", "other"),
            "file_name": data.get("file_name"),
            "file_size": data.get("file_size"),
            "file_mime": data.get("file_mime"),
            "file_path": data.get("file_path"),
            "url": data.get("url"),
            "created_at": now,
            "updated_at": now,
        }
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO client_documents
                   (doc_id, client_id, title, doc_type, file_name, file_size,
                    file_mime, file_path, url, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    item["doc_id"], item["client_id"], item["title"],
                    item["doc_type"], item["file_name"], item["file_size"],
                    item["file_mime"], item["file_path"], item["url"],
                    item["created_at"], item["updated_at"],
                ),
            )
            conn.commit()
        return item

    def get_client_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM client_documents WHERE doc_id=?", (doc_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def delete_client_document(self, doc_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM client_documents WHERE doc_id=?", (doc_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ── Client ROI Records (Phase 1) ──────────────────────────────────────────
    #
    # Structured, multiple-per-client release-of-information records. This is the
    # ongoing client-level ROI system and is intentionally separate from:
    #   * Admissions packet ROI (a single intake-packet artifact), and
    #   * Uploaded Signed ROIs (scanned/external files stored as client_documents).
    #
    # Status is derived defensively on read so the displayed state can never claim
    # more than the data supports. Revoked records are preserved as history.

    ALLOWED_ROI_STATUSES = ("draft", "needs_signature", "active", "expired", "revoked")
    ALLOWED_ROI_SOURCES = (
        "created_in_ember",
        "uploaded_signed_file",
        "admissions_packet_seed",
    )

    @staticmethod
    def _is_past_date(value: Any) -> bool:
        """True when value parses to a date strictly before today."""
        if not value:
            return False
        text = str(value).strip()
        if not text:
            return False
        # Accept a plain YYYY-MM-DD as well as a full ISO datetime.
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return parsed.date() < datetime.now().date()
        except Exception:
            pass
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d")
            return parsed.date() < datetime.now().date()
        except Exception:
            return False

    @classmethod
    def _roi_has_min_data(cls, record: Dict[str, Any]) -> bool:
        has_party = bool(str(record.get("authorized_party") or "").strip())
        info = record.get("info_to_release")
        has_scope = bool(info) if isinstance(info, list) else bool(str(info or "").strip())
        return has_party and has_scope

    @classmethod
    def _derive_roi_status(cls, record: Dict[str, Any]) -> str:
        """Defensive, read-time status. Never claims more than the data supports."""
        if cls._truthy(record.get("revoked")):
            return "revoked"
        if cls._is_past_date(record.get("expiration_date")):
            return "expired"
        requested = record.get("status") or "draft"
        if requested not in cls.ALLOWED_ROI_STATUSES:
            requested = "draft"
        # 'revoked'/'expired' are derived-only; if stored without the underlying
        # condition (e.g. an un-revoke), fall back to a safe non-terminal state.
        if requested in ("revoked", "expired"):
            requested = "needs_signature" if record.get("linked_document_id") else "draft"
        if requested == "active":
            if not cls._roi_has_min_data(record):
                return "draft"
            if not record.get("linked_document_id"):
                return "needs_signature"
        return requested

    @staticmethod
    def _truthy(value: Any) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "y", "t")
        return bool(value)

    def _roi_row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        record = self._row_to_dict(row)
        record["info_to_release"] = self._json_loads(record.get("info_to_release"), [])
        record["revocable"] = self._truthy(record.get("revocable"))
        record["revoked"] = self._truthy(record.get("revoked"))
        # Defensive read-time status overrides the stored value for display.
        record["stored_status"] = record.get("status")
        record["status"] = self._derive_roi_status(record)
        return record

    def list_client_roi_records(self, client_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM roi_records WHERE client_id=? ORDER BY created_at DESC",
                (client_id,),
            ).fetchall()
        return [self._roi_row_to_dict(r) for r in rows]

    def get_client_roi_record(self, roi_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM roi_records WHERE roi_id=?", (roi_id,)
            ).fetchone()
        return self._roi_row_to_dict(row) if row else None

    def create_client_roi_record(
        self, client_id: str, data: Dict[str, Any], created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        now = self._now()
        source = data.get("source") or "created_in_ember"
        if source not in self.ALLOWED_ROI_SOURCES:
            source = "created_in_ember"
        requested_status = data.get("status") or "draft"
        if requested_status not in self.ALLOWED_ROI_STATUSES:
            requested_status = "draft"
        revocable = 1 if self._truthy(data.get("revocable", True)) else 0
        info_to_release = self._json_dumps(data.get("info_to_release"), [])
        with self._connect() as conn:
            roi_id = uuid4().hex
            conn.execute(
                """INSERT INTO roi_records
                   (roi_id, client_id, authorized_party, relationship_type,
                    party_address, party_contact, purpose, info_to_release,
                    release_method, effective_date, expiration_date, revocable,
                    revoked, revoked_at, status, linked_document_id, source,
                    created_by, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    roi_id, client_id,
                    str(data.get("authorized_party") or "").strip(),
                    data.get("relationship_type"),
                    data.get("party_address"),
                    data.get("party_contact"),
                    data.get("purpose"),
                    info_to_release,
                    data.get("release_method"),
                    data.get("effective_date"),
                    data.get("expiration_date"),
                    revocable,
                    0,
                    None,
                    requested_status,
                    data.get("linked_document_id"),
                    source,
                    created_by,
                    now,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM roi_records WHERE roi_id=?", (roi_id,)
            ).fetchone()
        return self._roi_row_to_dict(row)

    def update_client_roi_record(
        self, roi_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if not updates:
            return self.get_client_roi_record(roi_id)
        column_map = {
            "authorized_party": lambda v: str(v or "").strip(),
            "relationship_type": lambda v: v,
            "party_address": lambda v: v,
            "party_contact": lambda v: v,
            "purpose": lambda v: v,
            "info_to_release": lambda v: self._json_dumps(v, []),
            "release_method": lambda v: v,
            "effective_date": lambda v: v,
            "expiration_date": lambda v: v,
            "revocable": lambda v: 1 if self._truthy(v) else 0,
            "linked_document_id": lambda v: v,
        }
        set_parts: List[str] = []
        values: List[Any] = []
        for column, transform in column_map.items():
            if column in updates:
                set_parts.append(f"{column} = ?")
                values.append(transform(updates[column]))

        if "status" in updates and updates["status"] is not None:
            requested_status = updates["status"]
            if requested_status in self.ALLOWED_ROI_STATUSES:
                set_parts.append("status = ?")
                values.append(requested_status)

        # Revocation is sticky and preserves history: set revoked + timestamp,
        # never delete. Allow explicit un-revoke only if the caller clears it.
        if "revoked" in updates:
            revoked = self._truthy(updates["revoked"])
            set_parts.append("revoked = ?")
            values.append(1 if revoked else 0)
            if revoked:
                set_parts.append("revoked_at = ?")
                values.append(updates.get("revoked_at") or self._now())
                set_parts.append("status = ?")
                values.append("revoked")
            else:
                set_parts.append("revoked_at = ?")
                values.append(None)

        if not set_parts:
            return self.get_client_roi_record(roi_id)

        set_parts.append("updated_at = ?")
        values.append(self._now())
        values.append(roi_id)
        with self._connect() as conn:
            cursor = conn.execute(
                f"UPDATE roi_records SET {', '.join(set_parts)} WHERE roi_id = ?",
                values,
            )
            conn.commit()
            if cursor.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM roi_records WHERE roi_id=?", (roi_id,)
            ).fetchone()
        return self._roi_row_to_dict(row) if row else None


workspace_store = WorkspaceStore()
