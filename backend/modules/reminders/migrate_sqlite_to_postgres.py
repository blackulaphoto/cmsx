#!/usr/bin/env python3
"""
One-shot migration: SQLite reminders.db + core_clients.db → Railway Postgres.

USAGE (run manually from repo root after confirming DATABASE_URL is set):
    python -m backend.modules.reminders.migrate_sqlite_to_postgres

SAFETY RULES:
- Read-only from SQLite.  Never deletes or modifies local .db files.
- Idempotent: uses INSERT ... ON CONFLICT DO NOTHING / DO UPDATE so re-runs are safe.
- Dry-run by default.  Pass --execute to actually write to Postgres.
- Requires DATABASE_URL to point to Railway Postgres.
- Stop Railway web dyno before running to avoid write conflicts.
"""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, List

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_SQLITE_REMINDERS = "databases/reminders.db"
_SQLITE_CORE_CLIENTS = "databases/core_clients.db"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    return url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url


def _require_postgres() -> None:
    url = _database_url()
    if not (url.startswith("postgresql://") or url.startswith("postgres://")):
        sys.exit("ERROR: DATABASE_URL is not set or does not point to Postgres. Aborting.")


@contextmanager
def _pg_conn() -> Generator:
    from sqlalchemy import create_engine, text
    engine = create_engine(_database_url(), pool_pre_ping=True, future=True)
    with engine.begin() as conn:
        yield conn, text


@contextmanager
def _sqlite(path: str) -> Generator:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema setup (idempotent)
# ---------------------------------------------------------------------------

_DDL = [
    """CREATE TABLE IF NOT EXISTS railway_core_clients (
        client_id TEXT PRIMARY KEY,
        first_name TEXT, last_name TEXT, email TEXT, phone TEXT,
        case_manager_id TEXT, risk_level TEXT, case_status TEXT,
        intake_date TEXT, created_at TEXT, updated_at TEXT,
        source TEXT DEFAULT 'migrate', metadata_json TEXT DEFAULT '{}'
    )""",
    "ALTER TABLE railway_core_clients ADD COLUMN IF NOT EXISTS case_status TEXT",
    "ALTER TABLE railway_core_clients ADD COLUMN IF NOT EXISTS updated_at TEXT",
    """CREATE TABLE IF NOT EXISTS railway_intelligent_tasks (
        id TEXT PRIMARY KEY, client_id TEXT NOT NULL, case_manager_id TEXT,
        task_type TEXT, title TEXT NOT NULL, description TEXT,
        priority TEXT DEFAULT 'medium', status TEXT DEFAULT 'pending',
        estimated_minutes INTEGER DEFAULT 30,
        due_date TIMESTAMPTZ, completed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW(),
        is_demo INTEGER DEFAULT 0
    )""",
    "ALTER TABLE railway_intelligent_tasks ADD COLUMN IF NOT EXISTS case_manager_id TEXT",
    "ALTER TABLE railway_intelligent_tasks ADD COLUMN IF NOT EXISTS is_demo INTEGER DEFAULT 0",
    "ALTER TABLE railway_intelligent_tasks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()",
    """CREATE TABLE IF NOT EXISTS railway_active_reminders (
        id BIGSERIAL PRIMARY KEY,
        reminder_id TEXT UNIQUE NOT NULL,
        client_id TEXT NOT NULL, case_manager_id TEXT NOT NULL,
        reminder_type TEXT NOT NULL, message TEXT NOT NULL,
        priority TEXT DEFAULT 'Medium', due_date TIMESTAMPTZ,
        status TEXT DEFAULT 'Active', created_at TIMESTAMPTZ DEFAULT NOW()
    )""",
]


def _ensure_schema(execute: bool) -> None:
    if not execute:
        logger.info("[DRY-RUN] Would create/verify Postgres schema tables")
        return
    with _pg_conn() as (conn, text):
        for ddl in _DDL:
            try:
                conn.execute(text(ddl))
            except Exception as e:
                logger.warning(f"DDL skipped ({e}): {ddl[:60]}")
    logger.info("Schema verified / created")


# ---------------------------------------------------------------------------
# Migration: core_clients
# ---------------------------------------------------------------------------

def _migrate_clients(execute: bool) -> Dict[str, int]:
    stats = {"read": 0, "upserted": 0, "skipped": 0}

    with _sqlite(_SQLITE_CORE_CLIENTS) as sq:
        rows = sq.execute(
            """
            SELECT client_id, first_name, last_name, email, phone,
                   case_manager_id, risk_level, case_status, intake_date,
                   created_at, updated_at
            FROM clients
            """
        ).fetchall()

    stats["read"] = len(rows)
    logger.info(f"Read {len(rows)} clients from SQLite")

    if not execute:
        logger.info(f"[DRY-RUN] Would upsert {len(rows)} clients to railway_core_clients")
        return stats

    with _pg_conn() as (conn, text):
        for row in rows:
            try:
                conn.execute(
                    text(
                        """
                        INSERT INTO railway_core_clients
                            (client_id, first_name, last_name, email, phone,
                             case_manager_id, risk_level, case_status, intake_date,
                             created_at, updated_at, source)
                        VALUES
                            (:client_id, :first_name, :last_name, :email, :phone,
                             :case_manager_id, :risk_level, :case_status, :intake_date,
                             :created_at, :updated_at, 'migrate_sqlite_to_postgres')
                        ON CONFLICT (client_id) DO UPDATE SET
                            first_name = EXCLUDED.first_name,
                            last_name = EXCLUDED.last_name,
                            email = EXCLUDED.email,
                            phone = EXCLUDED.phone,
                            case_manager_id = EXCLUDED.case_manager_id,
                            risk_level = EXCLUDED.risk_level,
                            case_status = EXCLUDED.case_status,
                            updated_at = EXCLUDED.updated_at
                        """
                    ),
                    dict(row),
                )
                stats["upserted"] += 1
            except Exception as e:
                logger.warning(f"Client {row['client_id']} skipped: {e}")
                stats["skipped"] += 1

    logger.info(f"Clients: upserted={stats['upserted']} skipped={stats['skipped']}")
    return stats


# ---------------------------------------------------------------------------
# Migration: intelligent_tasks
# ---------------------------------------------------------------------------

def _migrate_tasks(execute: bool) -> Dict[str, int]:
    stats = {"read": 0, "upserted": 0, "skipped": 0}

    with _sqlite(_SQLITE_REMINDERS) as sq:
        # Only migrate tasks that have a matching client in core_clients
        rows = sq.execute(
            """
            SELECT it.id, it.client_id, it.task_type, it.title, it.description,
                   it.priority, it.status, it.estimated_minutes,
                   it.due_date, it.completed_at, it.created_at,
                   COALESCE(it.is_demo, 0) as is_demo
            FROM intelligent_tasks it
            WHERE it.status != 'completed'
            """
        ).fetchall()

    stats["read"] = len(rows)
    logger.info(f"Read {len(rows)} pending tasks from SQLite")

    if not execute:
        logger.info(f"[DRY-RUN] Would upsert {len(rows)} tasks to railway_intelligent_tasks")
        return stats

    # Load valid client IDs from Postgres to skip orphans
    valid_client_ids: set = set()
    with _pg_conn() as (conn, text):
        result = conn.execute(text("SELECT client_id FROM railway_core_clients"))
        valid_client_ids = {r[0] for r in result.fetchall()}

    orphan_count = 0
    with _pg_conn() as (conn, text):
        for row in rows:
            if row["client_id"] not in valid_client_ids:
                orphan_count += 1
                stats["skipped"] += 1
                continue
            try:
                conn.execute(
                    text(
                        """
                        INSERT INTO railway_intelligent_tasks
                            (id, client_id, task_type, title, description,
                             priority, status, estimated_minutes,
                             due_date, completed_at, created_at, is_demo)
                        VALUES
                            (:id, :client_id, :task_type, :title, :description,
                             :priority, :status, :estimated_minutes,
                             :due_date, :completed_at, :created_at, :is_demo)
                        ON CONFLICT (id) DO UPDATE SET
                            status = EXCLUDED.status,
                            completed_at = EXCLUDED.completed_at,
                            updated_at = NOW()
                        """
                    ),
                    dict(row),
                )
                stats["upserted"] += 1
            except Exception as e:
                logger.warning(f"Task {row['id']} skipped: {e}")
                stats["skipped"] += 1

    if orphan_count:
        logger.warning(f"Skipped {orphan_count} tasks with client IDs not in Postgres")
    logger.info(f"Tasks: upserted={stats['upserted']} skipped={stats['skipped']}")
    return stats


# ---------------------------------------------------------------------------
# Migration: active_reminders
# ---------------------------------------------------------------------------

def _migrate_reminders(execute: bool) -> Dict[str, int]:
    stats = {"read": 0, "upserted": 0, "skipped": 0}

    with _sqlite(_SQLITE_REMINDERS) as sq:
        rows = sq.execute(
            """
            SELECT reminder_id, client_id, case_manager_id, reminder_type,
                   message, priority, due_date, status, created_at
            FROM active_reminders
            WHERE status = 'Active'
            """
        ).fetchall()

    stats["read"] = len(rows)
    logger.info(f"Read {len(rows)} active reminders from SQLite")

    if not execute:
        logger.info(f"[DRY-RUN] Would upsert {len(rows)} reminders to railway_active_reminders")
        return stats

    with _pg_conn() as (conn, text):
        for row in rows:
            try:
                conn.execute(
                    text(
                        """
                        INSERT INTO railway_active_reminders
                            (reminder_id, client_id, case_manager_id, reminder_type,
                             message, priority, due_date, status, created_at)
                        VALUES
                            (:reminder_id, :client_id, :case_manager_id, :reminder_type,
                             :message, :priority, :due_date, :status, :created_at)
                        ON CONFLICT (reminder_id) DO NOTHING
                        """
                    ),
                    dict(row),
                )
                stats["upserted"] += 1
            except Exception as e:
                logger.warning(f"Reminder {row['reminder_id']} skipped: {e}")
                stats["skipped"] += 1

    logger.info(f"Reminders: upserted={stats['upserted']} skipped={stats['skipped']}")
    return stats


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate reminders SQLite → Railway Postgres")
    parser.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Actually write to Postgres (default is dry-run)",
    )
    args = parser.parse_args()

    _require_postgres()

    mode = "EXECUTE" if args.execute else "DRY-RUN"
    logger.info(f"=== Migration starting [{mode}] at {datetime.now().isoformat()} ===")
    logger.info(f"Target: {_database_url()[:40]}...")

    _ensure_schema(args.execute)

    client_stats = _migrate_clients(args.execute)
    task_stats = _migrate_tasks(args.execute)
    reminder_stats = _migrate_reminders(args.execute)

    logger.info("=== Summary ===")
    logger.info(f"  Clients   : read={client_stats['read']}  upserted={client_stats['upserted']}  skipped={client_stats['skipped']}")
    logger.info(f"  Tasks     : read={task_stats['read']}  upserted={task_stats['upserted']}  skipped={task_stats['skipped']}")
    logger.info(f"  Reminders : read={reminder_stats['read']}  upserted={reminder_stats['upserted']}  skipped={reminder_stats['skipped']}")

    if not args.execute:
        logger.info("")
        logger.info("This was a DRY-RUN.  Re-run with --execute to apply changes.")
    else:
        logger.info("Migration complete.  Verify data in Railway Postgres before restarting the web dyno.")


if __name__ == "__main__":
    main()
