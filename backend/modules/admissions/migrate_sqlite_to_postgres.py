#!/usr/bin/env python3
"""
One-shot migration: admissions.db (SQLite) → Railway Postgres.

USAGE (from repo root, with DATABASE_URL pointing to Railway Postgres):
    python -m backend.modules.admissions.migrate_sqlite_to_postgres
    python -m backend.modules.admissions.migrate_sqlite_to_postgres --execute

SAFETY RULES:
- Read-only from SQLite.  Never deletes or modifies local .db files.
- Idempotent: INSERT ... ON CONFLICT DO NOTHING so re-runs are safe.
- Dry-run by default.  Pass --execute to actually write to Postgres.
- Requires DATABASE_URL to point to Railway Postgres.
"""
from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import sys
from contextlib import contextmanager
from typing import Any, Dict, Generator, List

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_SQLITE_PATH = "databases/admissions.db"


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    return url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url


def _require_postgres() -> None:
    url = _database_url()
    if not (url.startswith("postgresql://") or url.startswith("postgres://")):
        sys.exit("ERROR: DATABASE_URL is not set or does not point to Postgres. Aborting.")


@contextmanager
def _pg(dry_run: bool) -> Generator:
    from sqlalchemy import create_engine, text
    engine = create_engine(_database_url(), pool_pre_ping=True, future=True)
    with engine.begin() as conn:
        yield conn, text, dry_run


@contextmanager
def _sqlite(path: str) -> Generator:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _rows(conn: sqlite3.Connection, table: str) -> List[Dict[str, Any]]:
    try:
        return [dict(r) for r in conn.execute(f"SELECT * FROM {table}").fetchall()]
    except Exception as exc:
        logger.warning(f"  Could not read {table}: {exc}")
        return []


def _migrate_table(
    pg_conn,
    text_fn,
    dry_run: bool,
    rows: List[Dict[str, Any]],
    pg_table: str,
    conflict_key: str,
) -> int:
    if not rows:
        return 0
    sample = rows[0]
    cols = list(sample.keys())
    col_list = ", ".join(cols)
    val_list = ", ".join(f":{c}" for c in cols)
    sql = (
        f"INSERT INTO {pg_table} ({col_list}) VALUES ({val_list}) "
        f"ON CONFLICT ({conflict_key}) DO NOTHING"
    )
    written = 0
    for row in rows:
        if dry_run:
            written += 1
            continue
        try:
            pg_conn.execute(text_fn(sql), row)
            written += 1
        except Exception as exc:
            logger.warning(f"  Row skipped in {pg_table}: {exc}")
    return written


def run(dry_run: bool = True) -> None:
    _require_postgres()

    if not os.path.exists(_SQLITE_PATH):
        sys.exit(f"ERROR: SQLite file not found at {_SQLITE_PATH}")

    from backend.shared.database.railway_admissions_postgres import ensure_postgres_admissions_tables

    mode = "DRY-RUN" if dry_run else "EXECUTE"
    logger.info(f"=== Admissions SQLite → Postgres migration [{mode}] ===")

    if not dry_run:
        logger.info("Ensuring Postgres schema...")
        ensure_postgres_admissions_tables()

    with _sqlite(_SQLITE_PATH) as sq:
        packets = _rows(sq, "admission_packets")
        forms = _rows(sq, "admission_packet_forms")
        responses = _rows(sq, "admission_form_responses")
        attachments = _rows(sq, "admission_form_attachments")
        tasks = _rows(sq, "admissions_created_tasks")
        fc = _rows(sq, "admissions_financial_coordination")
        suppressions = _rows(sq, "admissions_task_suppressions")
        events = _rows(sq, "admissions_financial_coordination_events")

    logger.info(
        f"SQLite counts — packets:{len(packets)}, forms:{len(forms)}, "
        f"responses:{len(responses)}, attachments:{len(attachments)}, "
        f"tasks:{len(tasks)}, fc:{len(fc)}, "
        f"suppressions:{len(suppressions)}, events:{len(events)}"
    )

    with _pg(dry_run) as (pg_conn, text_fn, _):
        tables = [
            (packets,     "railway_admission_packets",                             "id"),
            (forms,       "railway_admission_packet_forms",                        "id"),
            (responses,   "railway_admission_form_responses",                      "id"),
            (attachments, "railway_admission_form_attachments",                    "id"),
            (tasks,       "railway_admissions_created_tasks",                      "id"),
            (fc,          "railway_admissions_financial_coordination",              "id"),
            (suppressions,"railway_admissions_task_suppressions",                  "id"),
            (events,      "railway_admissions_financial_coordination_events",      "id"),
        ]
        for rows, pg_table, conflict_key in tables:
            n = _migrate_table(pg_conn, text_fn, dry_run, rows, pg_table, conflict_key)
            action = "Would insert" if dry_run else "Inserted"
            logger.info(f"  {action} {n} rows into {pg_table}")

    logger.info(
        "Done. Re-run with --execute to write to Postgres."
        if dry_run else
        "Migration complete."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate admissions SQLite data to Postgres.")
    parser.add_argument("--execute", action="store_true", help="Actually write to Postgres.")
    args = parser.parse_args()
    run(dry_run=not args.execute)


if __name__ == "__main__":
    main()
