from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.shared.database.railway_fmla_postgres import _engine, ensure_postgres_fmla_tables
from backend.shared.database.railway_postgres import is_postgres_configured


SQLITE_FMLA_DB = Path("databases") / "fmla.db"

TABLE_MAPPINGS = [
    ("fmla_cases", "railway_fmla_cases", "case_id"),
    ("fmla_documents", "railway_fmla_documents", "document_id"),
    ("fmla_correspondence", "railway_fmla_correspondence", "correspondence_id"),
    ("fmla_case_reminders", "railway_fmla_case_reminders", "reminder_id"),
    ("fmla_leave_usage", "railway_fmla_leave_usage", "usage_id"),
    ("fmla_exports", "railway_fmla_exports", "export_id"),
    ("fmla_audit_log", "railway_fmla_audit_log", "audit_id"),
]


def _read_sqlite_rows(db_path: Path, table_name: str):
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
    return [dict(row) for row in rows]


def _upsert_rows(engine, table_name: str, primary_key: str, rows):
    if not rows:
        return 0

    columns = list(rows[0].keys())
    insert_columns = ", ".join(columns)
    value_columns = ", ".join(f":{column}" for column in columns)
    update_columns = ", ".join(
        f"{column} = EXCLUDED.{column}" for column in columns if column != primary_key
    )
    statement = text(
        f"""
        INSERT INTO {table_name} ({insert_columns})
        VALUES ({value_columns})
        ON CONFLICT ({primary_key}) DO UPDATE SET
            {update_columns}
        """
    )
    with engine.begin() as conn:
        conn.execute(statement, rows)
    return len(rows)


def main():
    if not is_postgres_configured():
        raise SystemExit("DATABASE_URL is not configured for PostgreSQL")
    if not SQLITE_FMLA_DB.exists():
        raise SystemExit(f"SQLite FMLA database not found: {SQLITE_FMLA_DB}")

    ensure_postgres_fmla_tables()
    engine = _engine()
    summary = {}
    for sqlite_table, postgres_table, primary_key in TABLE_MAPPINGS:
        rows = _read_sqlite_rows(SQLITE_FMLA_DB, sqlite_table)
        migrated = _upsert_rows(engine, postgres_table, primary_key, rows)
        summary[sqlite_table] = {
            "postgres_table": postgres_table,
            "rows_read": len(rows),
            "rows_upserted": migrated,
        }

    print(json.dumps({"success": True, "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
