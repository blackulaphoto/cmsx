#!/usr/bin/env python3
"""
Backfill core clients from SQLite into Railway Postgres mirror table.
Safe to rerun (upsert-based).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.shared.database.railway_postgres import (
    is_postgres_configured,
    upsert_client_to_postgres,
)


CORE_DB = ROOT / "databases" / "core_clients.db"


def main() -> int:
    if not CORE_DB.exists():
        print(f"Core database not found: {CORE_DB}")
        return 1

    if not is_postgres_configured():
        print("DATABASE_URL is not configured for PostgreSQL; aborting backfill.")
        return 1

    with sqlite3.connect(CORE_DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM clients")
        rows = cur.fetchall()
        cur.execute("PRAGMA table_info(clients)")
        columns = [c[1] for c in cur.fetchall()]

    success = 0
    failed = 0
    for row in rows:
        payload = dict(zip(columns, row))
        status = upsert_client_to_postgres(
            client_data=payload,
            integration_results={"source": "backfill_core_clients_to_postgres"},
        )
        if status == "success":
            success += 1
        else:
            failed += 1
            print(f"Failed for client_id={payload.get('client_id')}: {status}")

    print(f"Backfill complete. total={len(rows)} success={success} failed={failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
