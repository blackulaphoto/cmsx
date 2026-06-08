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

logger = logging.getLogger(__name__)


class WorkspaceStore:
    """Persist lightweight notes, tasks, and dashboard content in SQLite."""

    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parents[3]
        self.db_path = project_root / "databases" / "workspace_content.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
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

    def list_dashboard_items(self, table: str, case_manager_id: str) -> List[Dict[str, Any]]:
        order_by = {
            "dashboard_notes": "pinned DESC, created_at DESC",
            "dashboard_docs": "created_at DESC",
            "dashboard_bookmarks": "created_at DESC",
            "dashboard_resources": "uploaded_at DESC",
            "case_manager_rolodex": "category ASC, name ASC, updated_at DESC",
        }[table]
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE case_manager_id = ? ORDER BY {order_by}",
                (case_manager_id,),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def create_dashboard_note(self, case_manager_id: str, content: str, pinned: bool) -> Dict[str, Any]:
        item = {
            "id": uuid4().hex,
            "case_manager_id": case_manager_id,
            "content": content,
            "pinned": 1 if pinned else 0,
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dashboard_notes (id, case_manager_id, content, pinned, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (item["id"], item["case_manager_id"], item["content"], item["pinned"], item["created_at"], item["updated_at"]),
            )
            conn.commit()
        item["pinned"] = bool(item["pinned"])
        return item

    def update_dashboard_note(self, note_id: str, content: str, pinned: bool) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE dashboard_notes
                SET content = ?, pinned = ?, updated_at = ?
                WHERE id = ?
                """,
                (content, 1 if pinned else 0, self._now(), note_id),
            )
            if cursor.rowcount == 0:
                return None
            conn.commit()
            row = conn.execute("SELECT * FROM dashboard_notes WHERE id = ?", (note_id,)).fetchone()
        item = self._row_to_dict(row) if row else None
        if item:
            item["pinned"] = bool(item["pinned"])
        return item

    def create_dashboard_doc(self, case_manager_id: str, title: str, content: str, url: Optional[str]) -> Dict[str, Any]:
        item = {
            "id": uuid4().hex,
            "case_manager_id": case_manager_id,
            "title": title,
            "content": content,
            "url": url,
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dashboard_docs (id, case_manager_id, title, content, url, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (item["id"], item["case_manager_id"], item["title"], item["content"], item["url"], item["created_at"], item["updated_at"]),
            )
            conn.commit()
        return item

    def update_dashboard_doc(self, doc_id: str, title: str, content: str, url: Optional[str]) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE dashboard_docs
                SET title = ?, content = ?, url = ?, updated_at = ?
                WHERE id = ?
                """,
                (title, content, url, self._now(), doc_id),
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

    def create_dashboard_bookmark(self, case_manager_id: str, title: str, url: str, description: Optional[str], favicon: Optional[str]) -> Dict[str, Any]:
        item = {
            "id": uuid4().hex,
            "case_manager_id": case_manager_id,
            "title": title,
            "url": url,
            "description": description,
            "favicon": favicon,
            "created_at": self._now(),
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dashboard_bookmarks (id, case_manager_id, title, url, description, favicon, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (item["id"], item["case_manager_id"], item["title"], item["url"], item["description"], item["favicon"], item["created_at"]),
            )
            conn.commit()
        return item

    def create_dashboard_resource(self, case_manager_id: str, resource_id: str, name: str, size: int, content_type: str, file_path: str) -> Dict[str, Any]:
        item = {
            "id": resource_id,
            "case_manager_id": case_manager_id,
            "name": name,
            "size": size,
            "type": content_type,
            "uploaded_at": self._now(),
            "file_path": file_path,
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dashboard_resources (id, case_manager_id, name, size, type, uploaded_at, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (item["id"], item["case_manager_id"], item["name"], item["size"], item["type"], item["uploaded_at"], item["file_path"]),
            )
            conn.commit()
        return item

    def delete_dashboard_item(self, table: str, item_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
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

    def list_rolodex_entries(self, case_manager_id: str) -> List[Dict[str, Any]]:
        return self.list_dashboard_items("case_manager_rolodex", case_manager_id)

    def create_rolodex_entry(self, case_manager_id: str, entry_data: Dict[str, Any]) -> Dict[str, Any]:
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
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO case_manager_rolodex (
                    id, case_manager_id, name, category, custom_category, organization, role_title,
                    phone, email, website, address, city, trusted_status, availability_notes,
                    referral_notes, general_notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )
            conn.commit()
        return item

    def update_rolodex_entry(self, entry_id: str, entry_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
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

    def delete_rolodex_entry(self, entry_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM case_manager_rolodex WHERE id = ?", (entry_id,))
            conn.commit()
            return cursor.rowcount > 0


workspace_store = WorkspaceStore()
