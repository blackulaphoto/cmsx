"""
Reminders Repository — Postgres-first, SQLite fallback.

Single source of truth for all reminders / intelligent_tasks / active_reminders
database access.  Call use_postgres() to check which backend is active.

Usage pattern:
    from backend.modules.reminders.repository import repo
    tasks = repo.list_tasks_for_case_manager("cm_001")

The module-level `repo` singleton is created at import time and is safe
to share across requests (all operations open/close their own connections).
"""

from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from backend.shared.database.workspace_store import workspace_store

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

from backend.shared.db_path import DB_DIR as _DB_DIR
_SQLITE_REMINDERS_PATH = str(_DB_DIR / "reminders.db")
_SQLITE_CORE_CLIENTS_PATH = str(_DB_DIR / "core_clients.db")
_SQLITE_CASE_MGMT_PATH = str(_DB_DIR / "case_management.db")


# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

def _database_url() -> str:
    return os.getenv("DATABASE_URL", "").strip()


def use_postgres() -> bool:
    """Return True when DATABASE_URL points to a Postgres instance."""
    url = _database_url()
    return url.startswith("postgresql://") or url.startswith("postgres://")


def _normalized_postgres_url() -> str:
    url = _database_url()
    return url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url


# ---------------------------------------------------------------------------
# Postgres engine (lazy, module-level singleton)
# ---------------------------------------------------------------------------

_pg_engine = None


def _get_pg_engine():
    global _pg_engine
    if _pg_engine is None:
        from sqlalchemy import create_engine
        _pg_engine = create_engine(
            _normalized_postgres_url(),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            future=True,
        )
    return _pg_engine


@contextmanager
def _pg_conn() -> Generator:
    engine = _get_pg_engine()
    with engine.begin() as conn:
        yield conn


# ---------------------------------------------------------------------------
# SQLite helpers
# ---------------------------------------------------------------------------

@contextmanager
def _sqlite_conn(path: str) -> Generator:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Table DDL
# ---------------------------------------------------------------------------

_PG_INTELLIGENT_TASKS_DDL = """
CREATE TABLE IF NOT EXISTS railway_intelligent_tasks (
    id                TEXT PRIMARY KEY,
    client_id         TEXT NOT NULL,
    case_manager_id   TEXT,
    task_type         TEXT,
    title             TEXT NOT NULL,
    description       TEXT,
    priority          TEXT DEFAULT 'medium',
    status            TEXT DEFAULT 'pending',
    estimated_minutes INTEGER DEFAULT 30,
    due_date          TIMESTAMPTZ,
    completed_at      TIMESTAMPTZ,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW(),
    is_demo           INTEGER DEFAULT 0
);
"""

_PG_ACTIVE_REMINDERS_DDL = """
CREATE TABLE IF NOT EXISTS railway_active_reminders (
    id              BIGSERIAL PRIMARY KEY,
    reminder_id     TEXT UNIQUE NOT NULL,
    client_id       TEXT NOT NULL,
    case_manager_id TEXT NOT NULL,
    reminder_type   TEXT NOT NULL,
    message         TEXT NOT NULL,
    priority        TEXT DEFAULT 'Medium',
    due_date        TIMESTAMPTZ,
    status          TEXT DEFAULT 'Active',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
"""

_PG_CORE_CLIENTS_DDL = """
CREATE TABLE IF NOT EXISTS railway_core_clients (
    client_id       TEXT PRIMARY KEY,
    first_name      TEXT,
    last_name       TEXT,
    email           TEXT,
    phone           TEXT,
    case_manager_id TEXT,
    risk_level      TEXT,
    case_status     TEXT,
    intake_date     TEXT,
    created_at      TEXT,
    updated_at      TEXT,
    source          TEXT DEFAULT 'api.clients',
    metadata_json   TEXT DEFAULT '{}'
);
"""

# Backward-compatible column additions for existing Postgres tables
_PG_ALTER_STATEMENTS = [
    "ALTER TABLE railway_intelligent_tasks ADD COLUMN IF NOT EXISTS case_manager_id TEXT",
    "ALTER TABLE railway_intelligent_tasks ADD COLUMN IF NOT EXISTS is_demo INTEGER DEFAULT 0",
    "ALTER TABLE railway_intelligent_tasks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()",
    "ALTER TABLE railway_core_clients ADD COLUMN IF NOT EXISTS case_status TEXT",
    "ALTER TABLE railway_core_clients ADD COLUMN IF NOT EXISTS updated_at TEXT",
]


# ---------------------------------------------------------------------------
# Ensure tables exist
# ---------------------------------------------------------------------------

def ensure_storage_ready() -> bool:
    """
    Create Postgres tables if using Postgres, or ensure SQLite files exist.
    Returns True on success.
    """
    if use_postgres():
        try:
            from sqlalchemy import text
            with _pg_conn() as conn:
                conn.execute(text(_PG_INTELLIGENT_TASKS_DDL))
                conn.execute(text(_PG_ACTIVE_REMINDERS_DDL))
                conn.execute(text(_PG_CORE_CLIENTS_DDL))
                for stmt in _PG_ALTER_STATEMENTS:
                    try:
                        conn.execute(text(stmt))
                    except Exception:
                        pass  # column already exists — safe to ignore
            logger.info("Postgres reminders tables ready")
            return True
        except Exception as exc:
            logger.error(f"ensure_storage_ready (postgres) failed: {exc}")
            return False
    else:
        # SQLite — tables are created by ReminderDatabase.setup_database() on first use.
        # Just verify the file path is accessible.
        try:
            Path(_SQLITE_REMINDERS_PATH).parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"SQLite reminders path ready: {_SQLITE_REMINDERS_PATH}")
            return True
        except Exception as exc:
            logger.error(f"ensure_storage_ready (sqlite) failed: {exc}")
            return False


# ---------------------------------------------------------------------------
# Client scoping helpers
# ---------------------------------------------------------------------------

def _get_clients_for_case_manager_pg(case_manager_id: str) -> Tuple[List[str], Dict[str, str]]:
    """Return (client_id_list, {client_id: full_name}) from Postgres."""
    from sqlalchemy import text
    with _pg_conn() as conn:
        rows = conn.execute(
            text("""
                SELECT client_id,
                       COALESCE(first_name,'') || ' ' || COALESCE(last_name,'') AS full_name
                FROM railway_core_clients
                WHERE case_manager_id = :cm
            """),
            {"cm": case_manager_id},
        ).fetchall()
    ids = [r[0] for r in rows]
    names = {r[0]: r[1].strip() for r in rows}
    return ids, names


def _get_clients_for_case_manager_sqlite(case_manager_id: str) -> Tuple[List[str], Dict[str, str]]:
    """Return (client_id_list, {client_id: full_name}) from SQLite."""
    with _sqlite_conn(_SQLITE_CORE_CLIENTS_PATH) as conn:
        cur = conn.execute(
            "SELECT client_id, first_name, last_name FROM clients WHERE case_manager_id = ?",
            (case_manager_id,),
        )
        rows = cur.fetchall()
    ids = [r["client_id"] for r in rows]
    names = {r["client_id"]: f"{r['first_name']} {r['last_name']}".strip() for r in rows}
    return ids, names


def get_clients_for_case_manager(case_manager_id: str) -> Tuple[List[str], Dict[str, str]]:
    """
    Return (client_id_list, client_name_map) for the given case manager.
    Tries Postgres first when configured; falls back to SQLite on error.
    """
    if use_postgres():
        try:
            ids, names = _get_clients_for_case_manager_pg(case_manager_id)
            # If Postgres client table is empty, fall through to SQLite
            if ids:
                return ids, names
            logger.warning(
                "Postgres railway_core_clients returned 0 clients for %s — falling back to SQLite",
                case_manager_id,
            )
        except Exception as exc:
            logger.warning("Postgres client lookup failed (%s), using SQLite fallback", exc)
    return _get_clients_for_case_manager_sqlite(case_manager_id)


# ---------------------------------------------------------------------------
# Task reads
# ---------------------------------------------------------------------------

def _row_to_task_dict(row: Any, source: str = "intelligent_task") -> Dict[str, Any]:
    """Normalise a DB row (sqlite3.Row or sqlalchemy RowMapping) into a plain dict."""
    if isinstance(row, sqlite3.Row):
        d = dict(row)
    else:
        d = dict(row._mapping)

    # Normalise column names that differ between backends
    d.setdefault("task_id", d.get("id", ""))
    d.setdefault("source", source)
    d.setdefault("urgency_color", _priority_color(d.get("priority")))
    return d


def _priority_color(priority: Optional[str]) -> str:
    mapping = {
        "critical": "#CC2222",
        "high": "#FF4444",
        "medium": "#FFAA44",
        "low": "#44AA44",
    }
    return mapping.get(str(priority or "").lower(), "#888888")


def _normalise_status(status: Any) -> str:
    return str(status or "").strip().lower()


def _parse_due_date(value: Any) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def _is_treatment_plan_task(task: Dict[str, Any]) -> bool:
    task_source = str(task.get("task_source") or task.get("source") or "").lower()
    task_type = str(task.get("task_type") or "").lower()
    return task_source == "treatment_plan" or task_type == "treatment_plan_need"


def _module_urgency_bonus(module: Any, need_key: Any, title: Any) -> int:
    haystack = " ".join(
        str(part or "").lower()
        for part in (module, need_key, title)
    )
    if any(term in haystack for term in ("crisis", "court", "legal", "medical", "dental", "medication")):
        return 18
    if any(term in haystack for term in ("benefits", "disability", "housing", "sober_living")):
        return 12
    if any(term in haystack for term in ("job", "resume", "transportation")):
        return 6
    return 0


def _task_priority_score(task: Dict[str, Any], today: date) -> int:
    priority_weight = {
        "critical": 120,
        "urgent": 110,
        "high": 90,
        "medium": 60,
        "low": 30,
    }.get(str(task.get("priority") or "").lower(), 40)
    score = priority_weight

    due = _parse_due_date(task.get("due_date"))
    if due:
        days_until_due = (due - today).days
        if days_until_due < 0:
            score += 60
        elif days_until_due == 0:
            score += 45
        elif days_until_due <= 3:
            score += 30
        elif days_until_due <= 7:
            score += 15

    if _is_treatment_plan_task(task):
        score += 25
    score += _module_urgency_bonus(task.get("module"), task.get("need_key"), task.get("title"))
    return score


def _priority_reason(task: Dict[str, Any], today: date) -> str:
    pieces: List[str] = []
    task_source = str(task.get("task_source") or task.get("source") or "").lower()

    if _is_treatment_plan_task(task):
        need_label = str(task.get("need_key") or "").replace("_", " ").strip()
        if need_label:
            pieces.append(f"Approved treatment plan need: {need_label}.")
        else:
            pieces.append("Approved treatment plan task.")
    elif task_source == "intake":
        need_label = str(task.get("need_key") or "").replace("_", " ").strip()
        if need_label:
            pieces.append(f"Intake-identified need: {need_label}.")
        else:
            pieces.append("Identified during client intake.")

    module = str(task.get("module") or "").replace("_", " ").strip()
    if module:
        pieces.append(f"Routes to {module}.")

    due = _parse_due_date(task.get("due_date"))
    if due:
        days_until_due = (due - today).days
        if days_until_due < 0:
            pieces.append(f"Overdue by {abs(days_until_due)} day{'s' if abs(days_until_due) != 1 else ''}.")
        elif days_until_due == 0:
            pieces.append("Due today.")
        elif days_until_due <= 3:
            pieces.append(f"Due in {days_until_due} day{'s' if days_until_due != 1 else ''}.")

    if not pieces:
        priority = str(task.get("priority") or "medium").lower()
        pieces.append(f"Shown because it is an open {priority}-priority task.")
    return " ".join(pieces)


def _sort_bucket(tasks: List[Dict[str, Any]], today: date) -> List[Dict[str, Any]]:
    for task in tasks:
        task["priority_score"] = _task_priority_score(task, today)
        task.setdefault("priority_reason", _priority_reason(task, today))
    return sorted(
        tasks,
        key=lambda task: (
            -int(task.get("priority_score") or 0),
            _parse_due_date(task.get("due_date")) or date.max,
            str(task.get("created_at") or ""),
        ),
    )


def _workspace_task_to_task_dict(task: Dict[str, Any], name_map: Dict[str, str], today: date) -> Dict[str, Any]:
    converted = dict(task)
    converted["task_id"] = task.get("task_id") or task.get("id") or ""
    converted["id"] = converted["task_id"]
    converted["source"] = "workspace_task"
    converted["task_source"] = task.get("source")
    converted["source_label"] = "Treatment Plan" if task.get("source") == "treatment_plan" else "Client Task"
    converted["client_name"] = name_map.get(task.get("client_id", ""), "Unknown Client")
    converted["urgency_color"] = _priority_color(task.get("priority"))
    converted["estimated_minutes"] = task.get("estimated_minutes") or 30
    converted["is_treatment_plan_task"] = _is_treatment_plan_task(converted)
    converted["priority_score"] = _task_priority_score(converted, today)
    converted["priority_reason"] = _priority_reason(converted, today)
    return converted


def list_workspace_tasks_for_case_manager(case_manager_id: str) -> List[Dict[str, Any]]:
    """Return open workspace client_tasks for this case manager's clients."""
    client_ids, name_map = get_clients_for_case_manager(case_manager_id)
    if not client_ids:
        return []

    today = date.today()
    tasks: List[Dict[str, Any]] = []
    for client_id in client_ids:
        try:
            for task in workspace_store.list_client_tasks(client_id):
                if _normalise_status(task.get("status")) in {"completed", "done", "cancelled", "canceled"}:
                    continue
                tasks.append(_workspace_task_to_task_dict(task, name_map, today))
        except Exception as exc:
            logger.warning("Workspace task lookup failed for client %s: %s", client_id, exc)
    return tasks


def list_tasks_for_client(client_id: str) -> List[Dict[str, Any]]:
    """Return all non-completed intelligent_tasks for a single client."""
    if use_postgres():
        try:
            from sqlalchemy import text
            with _pg_conn() as conn:
                rows = conn.execute(
                    text("""
                        SELECT id, client_id, case_manager_id, task_type, title,
                               description, priority, status, estimated_minutes,
                               due_date, completed_at, created_at, is_demo
                        FROM railway_intelligent_tasks
                        WHERE client_id = :cid AND status != 'completed'
                        ORDER BY
                            CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                            due_date ASC NULLS LAST
                    """),
                    {"cid": client_id},
                ).fetchall()
            return [_row_to_task_dict(r) for r in rows]
        except Exception as exc:
            logger.warning("Postgres list_tasks_for_client failed (%s), using SQLite", exc)

    with _sqlite_conn(_SQLITE_REMINDERS_PATH) as conn:
        cur = conn.execute(
            """
            SELECT id, client_id, task_type, title, description, priority,
                   status, estimated_minutes, due_date, completed_at, created_at, is_demo
            FROM intelligent_tasks
            WHERE client_id = ? AND status != 'completed'
            ORDER BY
                CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                due_date ASC
            """,
            (client_id,),
        )
        return [_row_to_task_dict(r) for r in cur.fetchall()]


def list_tasks_for_case_manager(case_manager_id: str) -> List[Dict[str, Any]]:
    """Return all non-completed tasks across all clients owned by this case manager."""
    client_ids, name_map = get_clients_for_case_manager(case_manager_id)
    if not client_ids:
        return []

    tasks: List[Dict[str, Any]] = []

    if use_postgres():
        try:
            from sqlalchemy import text
            placeholders = ", ".join(f":cid{i}" for i in range(len(client_ids)))
            params = {f"cid{i}": cid for i, cid in enumerate(client_ids)}
            with _pg_conn() as conn:
                rows = conn.execute(
                    text(f"""
                        SELECT id, client_id, case_manager_id, task_type, title,
                               description, priority, status, estimated_minutes,
                               due_date, completed_at, created_at, is_demo
                        FROM railway_intelligent_tasks
                        WHERE client_id IN ({placeholders}) AND status != 'completed'
                        ORDER BY
                            CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                            due_date ASC NULLS LAST
                    """),
                    params,
                ).fetchall()
            for r in rows:
                t = _row_to_task_dict(r)
                t["client_name"] = name_map.get(t.get("client_id", ""), "Unknown Client")
                tasks.append(t)
            tasks.extend(list_workspace_tasks_for_case_manager(case_manager_id))
            return tasks
        except Exception as exc:
            logger.warning("Postgres list_tasks_for_case_manager failed (%s), using SQLite", exc)

    placeholders = ",".join("?" * len(client_ids))
    try:
        with _sqlite_conn(_SQLITE_REMINDERS_PATH) as conn:
            cur = conn.execute(
                f"""
                SELECT id, client_id, task_type, title, description, priority,
                       status, estimated_minutes, due_date, completed_at, created_at, is_demo
                FROM intelligent_tasks
                WHERE client_id IN ({placeholders}) AND status != 'completed'
                ORDER BY
                    CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                    due_date ASC
                """,
                client_ids,
            )
            for r in cur.fetchall():
                t = _row_to_task_dict(r)
                t["client_name"] = name_map.get(t.get("client_id", ""), "Unknown Client")
                tasks.append(t)
    except sqlite3.OperationalError as exc:
        logger.warning("SQLite intelligent_tasks lookup failed (%s); continuing with workspace tasks", exc)

    tasks.extend(list_workspace_tasks_for_case_manager(case_manager_id))
    return tasks


def get_today_tasks(case_manager_id: str) -> List[Dict[str, Any]]:
    """Active tasks with due_date == today, scoped to this case manager's clients."""
    client_ids, name_map = get_clients_for_case_manager(case_manager_id)
    if not client_ids:
        return []

    today_str = date.today().isoformat()

    if use_postgres():
        try:
            from sqlalchemy import text
            placeholders = ", ".join(f":cid{i}" for i in range(len(client_ids)))
            params = {f"cid{i}": cid for i, cid in enumerate(client_ids)}
            params["today"] = today_str
            with _pg_conn() as conn:
                rows = conn.execute(
                    text(f"""
                        SELECT id, client_id, task_type, title, description, priority,
                               status, estimated_minutes, due_date, completed_at, created_at
                        FROM railway_intelligent_tasks
                        WHERE client_id IN ({placeholders})
                          AND DATE(due_date) = :today
                          AND status != 'completed'
                        ORDER BY
                            CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                            due_date ASC
                    """),
                    params,
                ).fetchall()
            tasks = []
            for r in rows:
                t = _row_to_task_dict(r)
                t["client_name"] = name_map.get(t.get("client_id", ""), "Unknown Client")
                t["scheduled_for"] = today_str
                t["scheduled_time"] = _time_from_iso(t.get("due_date"))
                t["task"] = t.get("title", "")
                tasks.append(t)
            return tasks
        except Exception as exc:
            logger.warning("Postgres get_today_tasks failed (%s), using SQLite", exc)

    placeholders = ",".join("?" * len(client_ids))
    with _sqlite_conn(_SQLITE_REMINDERS_PATH) as conn:
        cur = conn.execute(
            f"""
            SELECT id, client_id, task_type, title, description, priority,
                   status, estimated_minutes, due_date, completed_at, created_at
            FROM intelligent_tasks
            WHERE client_id IN ({placeholders})
              AND DATE(due_date) = ?
              AND status != 'completed'
            ORDER BY
                CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                due_date ASC
            """,
            client_ids + [today_str],
        )
        tasks = []
        for r in cur.fetchall():
            t = _row_to_task_dict(r)
            t["client_name"] = name_map.get(t.get("client_id", ""), "Unknown Client")
            t["scheduled_for"] = today_str
            t["scheduled_time"] = _time_from_iso(t.get("due_date"))
            t["task"] = t.get("title", "")
            tasks.append(t)
        return tasks


def get_prioritized_tasks(case_manager_id: str, client_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Return tasks bucketed into overdue / today / next_3_days / this_week /
    treatment_plan / high_priority_no_date / later, plus an AI summary string.
    Pass client_date (YYYY-MM-DD) to use the client's local date for bucketing
    instead of the server's UTC date.today().
    """
    all_tasks = list_tasks_for_case_manager(case_manager_id)

    if client_date:
        try:
            today = datetime.strptime(client_date, "%Y-%m-%d").date()
        except ValueError:
            today = date.today()
    else:
        today = date.today()
    in_3_days = today + timedelta(days=3)
    in_7_days = today + timedelta(days=7)

    buckets: Dict[str, List[Dict]] = {
        "overdue": [],
        "today": [],
        "next_3_days": [],
        "this_week": [],
        "treatment_plan": [],
        "high_priority_no_date": [],
        "later": [],
    }

    for task in all_tasks:
        due = _parse_due_date(task.get("due_date"))
        task["priority_score"] = _task_priority_score(task, today)
        task.setdefault("priority_reason", _priority_reason(task, today))

        if due is None:
            if _is_treatment_plan_task(task):
                buckets["treatment_plan"].append(task)
            elif str(task.get("priority", "")).lower() in {"high", "critical"}:
                buckets["high_priority_no_date"].append(task)
        elif due < today:
            buckets["overdue"].append(task)
        elif due == today:
            buckets["today"].append(task)
        elif due <= in_3_days:
            buckets["next_3_days"].append(task)
        elif due <= in_7_days:
            buckets["this_week"].append(task)
        else:
            buckets["later"].append(task)

    # Also pull active_reminders into buckets
    active_reminders = get_active_reminders_for_case_manager(case_manager_id)
    _, name_map = get_clients_for_case_manager(case_manager_id)
    for r in active_reminders:
        due = _parse_due_date(r.get("due_date"))
        r.setdefault("client_name", name_map.get(r.get("client_id", ""), "Unknown"))
        r.setdefault("source", "active_reminder")
        r.setdefault("title", r.get("message", ""))
        # Map reminder_id → task_id so the frontend completion handler can target the right row
        r.setdefault("task_id", r.get("reminder_id", ""))
        # Map reminder_type → task_type so the category filter works
        r.setdefault("task_type", r.get("reminder_type", ""))
        r["priority_score"] = _task_priority_score(r, today)
        r.setdefault("priority_reason", _priority_reason(r, today))

        if due is None:
            if str(r.get("priority", "")).lower() in {"high", "critical"}:
                buckets["high_priority_no_date"].append(r)
        elif due < today:
            buckets["overdue"].append(r)
        elif due == today:
            buckets["today"].append(r)
        elif due <= in_3_days:
            buckets["next_3_days"].append(r)
        elif due <= in_7_days:
            buckets["this_week"].append(r)
        else:
            buckets["later"].append(r)

    for bucket_key, bucket_tasks in buckets.items():
        buckets[bucket_key] = _sort_bucket(bucket_tasks, today)

    overdue_n = len(buckets["overdue"])
    today_n = len(buckets["today"])
    next3_n = len(buckets["next_3_days"])
    treatment_plan_n = len(buckets["treatment_plan"])
    total_active = sum(len(v) for k, v in buckets.items() if k != "later")

    ai_summary: Optional[str] = None
    if overdue_n or today_n or next3_n:
        parts = []
        if overdue_n:
            first = buckets["overdue"][0].get("title", "")
            parts.append(
                f"{overdue_n} overdue task{'s' if overdue_n > 1 else ''}"
                + (f' — start with "{first}"' if first else "")
            )
        if today_n:
            parts.append(f"{today_n} due today")
        if next3_n:
            parts.append(f"{next3_n} coming up in the next 3 days")
        if treatment_plan_n:
            parts.append(f"{treatment_plan_n} treatment-plan item{'s' if treatment_plan_n > 1 else ''} need scheduling")
        ai_summary = "You have " + ", ".join(parts) + "."
    elif treatment_plan_n:
        ai_summary = (
            f"You have {treatment_plan_n} treatment-plan item{'s' if treatment_plan_n > 1 else ''} "
            "without due dates. Start by scheduling the highest-risk need."
        )
    elif buckets["high_priority_no_date"]:
        n = len(buckets["high_priority_no_date"])
        ai_summary = f"You have {n} high-priority item{'s' if n > 1 else ''} without due dates. Consider scheduling them."
    elif buckets["later"]:
        first = buckets["later"][0].get("title", "")
        ai_summary = f'Nothing urgent right now. Next up: "{first}"' if first else "Nothing urgent right now."

    return {
        "buckets": buckets,
        "ai_summary": ai_summary,
        "total_active": total_active,
        "counts": {
            "overdue": overdue_n,
            "today": today_n,
            "next_3_days": next3_n,
            "this_week": len(buckets["this_week"]),
            "treatment_plan": treatment_plan_n,
            "high_priority_no_date": len(buckets["high_priority_no_date"]),
            "later": len(buckets["later"]),
        },
    }


# ---------------------------------------------------------------------------
# Active reminders reads
# ---------------------------------------------------------------------------

def get_active_reminders_for_case_manager(case_manager_id: str) -> List[Dict[str, Any]]:
    """Return Active reminders for the given case manager."""
    if use_postgres():
        try:
            from sqlalchemy import text
            with _pg_conn() as conn:
                rows = conn.execute(
                    text("""
                        SELECT reminder_id, client_id, case_manager_id, reminder_type,
                               message, priority, due_date, status, created_at
                        FROM railway_active_reminders
                        WHERE case_manager_id = :cm AND status = 'Active'
                        ORDER BY
                            CASE priority
                                WHEN 'Critical' THEN 1 WHEN 'High' THEN 2
                                WHEN 'Medium' THEN 3 ELSE 4
                            END,
                            due_date ASC NULLS LAST
                    """),
                    {"cm": case_manager_id},
                ).fetchall()
            return [dict(r._mapping) for r in rows]
        except Exception as exc:
            logger.warning("Postgres get_active_reminders failed (%s), using SQLite", exc)

    try:
        with _sqlite_conn(_SQLITE_REMINDERS_PATH) as conn:
            cur = conn.execute(
                """
                SELECT reminder_id, client_id, case_manager_id, reminder_type,
                       message, priority, due_date, status, created_at
                FROM active_reminders
                WHERE case_manager_id = ? AND status = 'Active'
                ORDER BY
                    CASE priority
                        WHEN 'Critical' THEN 1 WHEN 'High' THEN 2
                        WHEN 'Medium' THEN 3 ELSE 4
                    END,
                    due_date ASC
                """,
                (case_manager_id,),
            )
            return [dict(r) for r in cur.fetchall()]
    except sqlite3.OperationalError as exc:
        logger.warning("SQLite active_reminders lookup failed (%s); returning none", exc)
        return []


# ---------------------------------------------------------------------------
# Task writes
# ---------------------------------------------------------------------------

def create_intelligent_tasks(
    client_id: str,
    tasks: List[Dict[str, Any]],
    case_manager_id: str = "",
    is_demo: bool = False,
    clear_process_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Persist a batch of generated tasks.

    If clear_process_types is given, existing tasks of those process types
    for this client are deleted first (prevents duplicates without wiping
    unrelated tasks).
    """
    demo_flag = 1 if is_demo else 0
    inserted = 0
    errors = 0

    if use_postgres():
        try:
            from sqlalchemy import text
            with _pg_conn() as conn:
                # Clear stale tasks for the specified process types
                if clear_process_types:
                    placeholders = ", ".join(f":pt{i}" for i in range(len(clear_process_types)))
                    params = {f"pt{i}": pt for i, pt in enumerate(clear_process_types)}
                    params["cid"] = client_id
                    conn.execute(
                        text(f"""
                            DELETE FROM railway_intelligent_tasks
                            WHERE client_id = :cid AND task_type IN ({placeholders})
                        """),
                        params,
                    )
                else:
                    conn.execute(
                        text("DELETE FROM railway_intelligent_tasks WHERE client_id = :cid"),
                        {"cid": client_id},
                    )

                for task in tasks:
                    try:
                        conn.execute(
                            text("""
                                INSERT INTO railway_intelligent_tasks (
                                    id, client_id, case_manager_id, task_type, title,
                                    description, priority, status, estimated_minutes,
                                    due_date, completed_at, created_at, is_demo
                                ) VALUES (
                                    :id, :client_id, :case_manager_id, :task_type, :title,
                                    :description, :priority, :status, :estimated_minutes,
                                    :due_date, NULL, :created_at, :is_demo
                                )
                                ON CONFLICT (id) DO UPDATE SET
                                    title = EXCLUDED.title,
                                    description = EXCLUDED.description,
                                    priority = EXCLUDED.priority,
                                    status = EXCLUDED.status,
                                    due_date = EXCLUDED.due_date,
                                    updated_at = NOW()
                            """),
                            {
                                "id": task.get("task_id", str(uuid.uuid4())),
                                "client_id": client_id,
                                "case_manager_id": case_manager_id or task.get("case_manager_id", ""),
                                "task_type": task.get("process_type", task.get("task_type", "unknown")),
                                "title": task.get("title", "Untitled"),
                                "description": task.get("description", ""),
                                "priority": str(task.get("priority", "medium")).lower(),
                                "status": str(task.get("status", "pending")).lower(),
                                "estimated_minutes": task.get("estimated_minutes", 30),
                                "due_date": task.get("scheduled_date") or task.get("due_date"),
                                "created_at": task.get("created_at", datetime.now().isoformat()),
                                "is_demo": demo_flag,
                            },
                        )
                        inserted += 1
                    except Exception as exc:
                        logger.warning("Failed to insert task '%s': %s", task.get("title"), exc)
                        errors += 1

            logger.info("Postgres: inserted %d/%d tasks for client %s", inserted, len(tasks), client_id)
            return {"success": True, "inserted": inserted, "errors": errors, "backend": "postgres"}
        except Exception as exc:
            logger.error("Postgres create_intelligent_tasks failed (%s), falling back to SQLite", exc)

    # SQLite fallback
    with _sqlite_conn(_SQLITE_REMINDERS_PATH) as conn:
        if clear_process_types:
            placeholders = ",".join("?" * len(clear_process_types))
            conn.execute(
                f"DELETE FROM intelligent_tasks WHERE client_id = ? AND task_type IN ({placeholders})",
                [client_id] + clear_process_types,
            )
        else:
            conn.execute("DELETE FROM intelligent_tasks WHERE client_id = ?", (client_id,))

        for task in tasks:
            try:
                conn.execute(
                    """
                    INSERT INTO intelligent_tasks (
                        id, client_id, task_type, title, description,
                        priority, estimated_minutes, status, created_at, due_date, is_demo
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.get("task_id", str(uuid.uuid4())),
                        client_id,
                        task.get("process_type", task.get("task_type", "unknown")),
                        task.get("title", "Untitled"),
                        task.get("description", ""),
                        str(task.get("priority", "medium")).lower(),
                        task.get("estimated_minutes", 30),
                        str(task.get("status", "pending")).lower(),
                        task.get("created_at", datetime.now().isoformat()),
                        task.get("scheduled_date") or task.get("due_date"),
                        demo_flag,
                    ),
                )
                inserted += 1
            except Exception as exc:
                logger.warning("SQLite: failed to insert task '%s': %s", task.get("title"), exc)
                errors += 1

    return {"success": True, "inserted": inserted, "errors": errors, "backend": "sqlite"}


def update_task_status(
    task_id: str,
    status: str,
    completed_at: Optional[str] = None,
) -> bool:
    """Mark a task completed (or any other status). Returns True on success."""
    completed_ts = completed_at or (datetime.now().isoformat() if status == "completed" else None)

    if use_postgres():
        try:
            from sqlalchemy import text
            with _pg_conn() as conn:
                result = conn.execute(
                    text("""
                        UPDATE railway_intelligent_tasks
                        SET status = :status,
                            completed_at = :completed_at,
                            updated_at = NOW()
                        WHERE id = :task_id
                    """),
                    {"status": status, "completed_at": completed_ts, "task_id": task_id},
                )
                if result.rowcount == 0:
                    logger.warning("update_task_status: task %s not found in Postgres", task_id)
                    return False
            return True
        except Exception as exc:
            logger.warning("Postgres update_task_status failed (%s), using SQLite", exc)

    try:
        with _sqlite_conn(_SQLITE_REMINDERS_PATH) as conn:
            cur = conn.execute(
                "UPDATE intelligent_tasks SET status = ?, completed_at = ? WHERE id = ?",
                (status, completed_ts, task_id),
            )
            return cur.rowcount > 0
    except sqlite3.OperationalError as exc:
        logger.warning("SQLite intelligent_tasks update failed (%s); task may be workspace-backed", exc)
        return False


# ---------------------------------------------------------------------------
# Active reminder writes
# ---------------------------------------------------------------------------

def create_active_reminder(
    client_id: str,
    case_manager_id: str,
    reminder_type: str,
    message: str,
    priority: str = "Medium",
    due_date: Optional[str] = None,
) -> str:
    """Persist a new active reminder. Returns the reminder_id."""
    reminder_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()

    if use_postgres():
        try:
            from sqlalchemy import text
            with _pg_conn() as conn:
                conn.execute(
                    text("""
                        INSERT INTO railway_active_reminders (
                            reminder_id, client_id, case_manager_id, reminder_type,
                            message, priority, due_date, status, created_at
                        ) VALUES (
                            :reminder_id, :client_id, :case_manager_id, :reminder_type,
                            :message, :priority, :due_date, 'Active', :created_at
                        )
                    """),
                    {
                        "reminder_id": reminder_id,
                        "client_id": client_id,
                        "case_manager_id": case_manager_id,
                        "reminder_type": reminder_type,
                        "message": message,
                        "priority": priority,
                        "due_date": due_date,
                        "created_at": created_at,
                    },
                )
            return reminder_id
        except Exception as exc:
            logger.warning("Postgres create_active_reminder failed (%s), using SQLite", exc)

    with _sqlite_conn(_SQLITE_REMINDERS_PATH) as conn:
        conn.execute(
            """
            INSERT INTO active_reminders (
                reminder_id, client_id, case_manager_id, reminder_type,
                message, priority, due_date, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Active', ?)
            """,
            (reminder_id, client_id, case_manager_id, reminder_type,
             message, priority, due_date, created_at),
        )
    return reminder_id


def update_active_reminder(
    reminder_id: str,
    message: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    reminder_type: Optional[str] = None,
) -> bool:
    """Update editable fields on an active reminder. Returns True if a row was changed."""
    updates: Dict[str, Any] = {}
    if message is not None:
        updates["message"] = message
    if due_date is not None:
        updates["due_date"] = due_date
    if priority is not None:
        updates["priority"] = priority
    if reminder_type is not None:
        updates["reminder_type"] = reminder_type
    if not updates:
        return True

    if use_postgres():
        try:
            from sqlalchemy import text
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            updates["reminder_id"] = reminder_id
            with _pg_conn() as conn:
                result = conn.execute(
                    text(f"UPDATE railway_active_reminders SET {set_clause} WHERE reminder_id = :reminder_id"),
                    updates,
                )
                if result.rowcount > 0:
                    return True
        except Exception as exc:
            logger.warning("Postgres update_active_reminder failed (%s), using SQLite", exc)

    try:
        set_clause = ", ".join(f"{k} = ?" for k in updates if k != "reminder_id_placeholder")
        # Re-build without the pg key
        fields = {k: v for k, v in updates.items() if k != "reminder_id"}
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [reminder_id]
        with _sqlite_conn(_SQLITE_REMINDERS_PATH) as conn:
            cur = conn.execute(
                f"UPDATE active_reminders SET {set_clause} WHERE reminder_id = ?",
                values,
            )
            return cur.rowcount > 0
    except Exception as exc:
        logger.warning("SQLite update_active_reminder failed: %s", exc)
        return False


def delete_active_reminder(reminder_id: str) -> bool:
    """Permanently delete an active reminder. Returns True if a row was removed."""
    if use_postgres():
        try:
            from sqlalchemy import text
            with _pg_conn() as conn:
                result = conn.execute(
                    text("DELETE FROM railway_active_reminders WHERE reminder_id = :rid"),
                    {"rid": reminder_id},
                )
                if result.rowcount > 0:
                    return True
        except Exception as exc:
            logger.warning("Postgres delete_active_reminder failed (%s), using SQLite", exc)

    try:
        with _sqlite_conn(_SQLITE_REMINDERS_PATH) as conn:
            cur = conn.execute(
                "DELETE FROM active_reminders WHERE reminder_id = ?",
                (reminder_id,),
            )
            return cur.rowcount > 0
    except Exception as exc:
        logger.warning("SQLite delete_active_reminder failed: %s", exc)
        return False


def reopen_active_reminder(reminder_id: str) -> bool:
    """Set a completed active reminder back to Active."""
    if use_postgres():
        try:
            from sqlalchemy import text
            with _pg_conn() as conn:
                result = conn.execute(
                    text("UPDATE railway_active_reminders SET status = 'Active' WHERE reminder_id = :rid"),
                    {"rid": reminder_id},
                )
                if result.rowcount > 0:
                    return True
        except Exception as exc:
            logger.warning("Postgres reopen_active_reminder failed (%s), using SQLite", exc)

    try:
        with _sqlite_conn(_SQLITE_REMINDERS_PATH) as conn:
            cur = conn.execute(
                "UPDATE active_reminders SET status = 'Active' WHERE reminder_id = ?",
                (reminder_id,),
            )
            return cur.rowcount > 0
    except Exception as exc:
        logger.warning("SQLite reopen_active_reminder failed: %s", exc)
        return False


def complete_active_reminder(reminder_id: str) -> bool:
    """Mark an active reminder as Completed. Returns True if a row was updated."""
    if use_postgres():
        try:
            from sqlalchemy import text
            with _pg_conn() as conn:
                result = conn.execute(
                    text("""
                        UPDATE railway_active_reminders
                        SET status = 'Completed'
                        WHERE reminder_id = :reminder_id
                    """),
                    {"reminder_id": reminder_id},
                )
                if result.rowcount > 0:
                    return True
        except Exception as exc:
            logger.warning("Postgres complete_active_reminder failed (%s), using SQLite", exc)

    try:
        with _sqlite_conn(_SQLITE_REMINDERS_PATH) as conn:
            cur = conn.execute(
                "UPDATE active_reminders SET status = 'Completed' WHERE reminder_id = ?",
                (reminder_id,),
            )
            return cur.rowcount > 0
    except Exception as exc:
        logger.warning("SQLite complete_active_reminder failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def cleanup_orphan_tasks() -> Dict[str, int]:
    """
    Delete intelligent_tasks whose client_id has no matching client record.
    SAFE: only removes truly orphaned rows.  Call manually — never auto-runs.
    """
    # Get all real client IDs from SQLite (or Postgres when available)
    real_ids: set = set()
    if use_postgres():
        try:
            from sqlalchemy import text
            with _pg_conn() as conn:
                rows = conn.execute(text("SELECT client_id FROM railway_core_clients")).fetchall()
            real_ids = {r[0] for r in rows}
        except Exception as exc:
            logger.warning("Postgres client fetch failed in cleanup (%s), using SQLite", exc)
    if not real_ids:
        with _sqlite_conn(_SQLITE_CORE_CLIENTS_PATH) as conn:
            cur = conn.execute("SELECT client_id FROM clients")
            real_ids = {r["client_id"] for r in cur.fetchall()}

    removed = 0
    if use_postgres():
        try:
            from sqlalchemy import text
            with _pg_conn() as conn:
                rows = conn.execute(
                    text("SELECT DISTINCT client_id FROM railway_intelligent_tasks")
                ).fetchall()
                orphan_ids = [r[0] for r in rows if r[0] not in real_ids]
                for oid in orphan_ids:
                    result = conn.execute(
                        text("DELETE FROM railway_intelligent_tasks WHERE client_id = :cid"),
                        {"cid": oid},
                    )
                    removed += result.rowcount
        except Exception as exc:
            logger.error("Postgres cleanup_orphan_tasks failed: %s", exc)
    else:
        with _sqlite_conn(_SQLITE_REMINDERS_PATH) as conn:
            cur = conn.execute("SELECT DISTINCT client_id FROM intelligent_tasks")
            orphan_ids = [r["client_id"] for r in cur.fetchall() if r["client_id"] not in real_ids]
            for oid in orphan_ids:
                r = conn.execute(
                    "DELETE FROM intelligent_tasks WHERE client_id = ?", (oid,)
                )
                removed += r.rowcount

    return {"orphan_client_ids_found": len(orphan_ids), "tasks_removed": removed}


def storage_status() -> Dict[str, Any]:
    """Return diagnostic info about the current storage backend."""
    pg = use_postgres()
    pg_ok = False
    pg_msg = "not configured"
    if pg:
        try:
            from sqlalchemy import text
            with _pg_conn() as conn:
                conn.execute(text("SELECT 1"))
            pg_ok = True
            pg_msg = "connected"
        except Exception as exc:
            pg_msg = str(exc)

    return {
        "storage_backend": "postgres" if (pg and pg_ok) else "sqlite",
        "database_url_configured": pg,
        "postgres_available": pg_ok,
        "postgres_detail": pg_msg,
        "sqlite_fallback_path": _SQLITE_REMINDERS_PATH,
        "sqlite_clients_path": _SQLITE_CORE_CLIENTS_PATH,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _time_from_iso(value: Optional[str]) -> str:
    if not value:
        return "09:00"
    try:
        return datetime.fromisoformat(str(value)).strftime("%H:%M")
    except ValueError:
        return "09:00"


# ---------------------------------------------------------------------------
# Module-level singleton (convenient import)
# ---------------------------------------------------------------------------

class _Repo:
    """Thin namespace so callers can do `from repository import repo; repo.list_tasks_for_case_manager(...)` ."""

    use_postgres = staticmethod(use_postgres)
    ensure_storage_ready = staticmethod(ensure_storage_ready)
    get_clients_for_case_manager = staticmethod(get_clients_for_case_manager)
    list_tasks_for_client = staticmethod(list_tasks_for_client)
    list_tasks_for_case_manager = staticmethod(list_tasks_for_case_manager)
    get_today_tasks = staticmethod(get_today_tasks)
    get_prioritized_tasks = staticmethod(get_prioritized_tasks)
    get_active_reminders_for_case_manager = staticmethod(get_active_reminders_for_case_manager)
    create_intelligent_tasks = staticmethod(create_intelligent_tasks)
    update_task_status = staticmethod(update_task_status)
    create_active_reminder = staticmethod(create_active_reminder)
    cleanup_orphan_tasks = staticmethod(cleanup_orphan_tasks)
    storage_status = staticmethod(storage_status)


repo = _Repo()
