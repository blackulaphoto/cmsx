"""
Sober Living store — Phase 1 (houses/rooms/beds/residents/stays) +
Phase 2 stubs (compliance, UA tests, incidents, rent).

Storage: Postgres when DATABASE_URL is set, SQLite fallback for local dev.
All queries written with %s placeholders; _q() converts to ? for SQLite.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

log = logging.getLogger(__name__)

SQLITE_PATH = Path("databases/sober_living_ops.db")

BED_STATUSES       = {"available", "occupied", "reserved", "maintenance", "unavailable"}
RESIDENT_STATUSES  = {"active", "on_leave", "discharged", "evicted"}
STAY_STATUSES      = {"active", "on_leave", "discharged", "evicted"}
TEST_RESULTS       = {"negative", "positive", "dilute", "refused", "not_completed"}
CHARGE_STATUSES    = {"unpaid", "partial", "paid", "waived", "void"}


def _now() -> str:
    return datetime.utcnow().isoformat()


def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def _use_postgres() -> bool:
    return bool(_database_url())


def _q(sql: str) -> str:
    """Convert %s placeholders to ? for SQLite. No-op for Postgres."""
    if _use_postgres():
        return sql
    return sql.replace("%s", "?")


@contextmanager
def _pg_conn() -> Generator:
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(_database_url(), cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def _sqlite_conn() -> Generator:
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def _db() -> Generator:
    if _use_postgres():
        with _pg_conn() as conn:
            yield conn
    else:
        with _sqlite_conn() as conn:
            yield conn


def _row(r) -> Optional[Dict]:
    if r is None:
        return None
    return dict(r)


def _rows(rs) -> List[Dict]:
    return [_row(r) for r in rs]


def _exec(conn, sql: str, args=()):
    if _use_postgres():
        cur = conn.cursor()
        cur.execute(_q(sql), args)
        return cur
    else:
        return conn.execute(_q(sql), args)


def _fetchone(conn, sql: str, args=()) -> Optional[Dict]:
    return _row(_exec(conn, sql, args).fetchone())


def _fetchall(conn, sql: str, args=()) -> List[Dict]:
    return _rows(_exec(conn, sql, args).fetchall())


# ---------------------------------------------------------------------------
# Schema DDL — order matters: referenced tables must come first
# ---------------------------------------------------------------------------

_DDL = [
    # ---- Core tables ----
    """CREATE TABLE IF NOT EXISTS sober_living_houses (
        house_id                  TEXT PRIMARY KEY,
        house_name                TEXT NOT NULL,
        house_manager_name        TEXT,
        house_manager_phone       TEXT,
        house_manager_email       TEXT,
        address                   TEXT,
        city                      TEXT,
        state                     TEXT,
        zip_code                  TEXT,
        house_type                TEXT DEFAULT 'any',
        certification_level       TEXT,
        certification_notes       TEXT,
        total_beds                INTEGER DEFAULT 0,
        monthly_rent              REAL,
        house_rules_version       TEXT,
        affiliated_clinical_program TEXT,
        notes                     TEXT,
        is_active                 INTEGER DEFAULT 1,
        payment_type              TEXT DEFAULT 'unknown',
        accepts_insurance         TEXT DEFAULT 'unknown',
        insurance_plans_accepted  TEXT,
        funding_notes             TEXT,
        requires_clinical_program INTEGER DEFAULT 0,
        billing_contact_name      TEXT,
        billing_contact_phone     TEXT,
        billing_contact_email     TEXT,
        created_at                TEXT NOT NULL,
        updated_at                TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS sober_living_rooms (
        room_id       TEXT PRIMARY KEY,
        house_id      TEXT NOT NULL REFERENCES sober_living_houses(house_id) ON DELETE CASCADE,
        room_name     TEXT NOT NULL,
        floor         TEXT,
        room_type     TEXT,
        max_occupancy INTEGER DEFAULT 1,
        notes         TEXT,
        is_active     INTEGER DEFAULT 1,
        created_at    TEXT NOT NULL,
        updated_at    TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS sober_living_beds (
        bed_id                TEXT PRIMARY KEY,
        house_id              TEXT NOT NULL REFERENCES sober_living_houses(house_id) ON DELETE CASCADE,
        room_id               TEXT NOT NULL REFERENCES sober_living_rooms(room_id) ON DELETE CASCADE,
        bed_label             TEXT NOT NULL,
        bed_status            TEXT NOT NULL DEFAULT 'available',
        current_resident_id   TEXT,
        reserved_for_client_id TEXT,
        reserved_until        TEXT,
        notes                 TEXT,
        created_at            TEXT NOT NULL,
        updated_at            TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS sober_living_residents (
        resident_id                   TEXT PRIMARY KEY,
        linked_client_id              TEXT,
        first_name                    TEXT NOT NULL,
        last_name                     TEXT NOT NULL,
        date_of_birth                 TEXT,
        phone                         TEXT,
        email                         TEXT,
        emergency_contact_name        TEXT,
        emergency_contact_phone       TEXT,
        emergency_contact_relationship TEXT,
        primary_substance             TEXT,
        sobriety_date                 TEXT,
        notes                         TEXT,
        created_at                    TEXT NOT NULL,
        updated_at                    TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS sober_living_stays (
        stay_id                TEXT PRIMARY KEY,
        resident_id            TEXT NOT NULL REFERENCES sober_living_residents(resident_id),
        house_id               TEXT NOT NULL REFERENCES sober_living_houses(house_id),
        bed_id                 TEXT REFERENCES sober_living_beds(bed_id),
        move_in_date           TEXT NOT NULL,
        expected_move_out_date TEXT,
        actual_move_out_date   TEXT,
        move_out_reason        TEXT,
        resident_status        TEXT NOT NULL DEFAULT 'active',
        clinical_program       TEXT,
        case_manager_name      TEXT,
        referral_source        TEXT,
        step_down_from_level   TEXT,
        discharge_destination  TEXT,
        created_at             TEXT NOT NULL,
        updated_at             TEXT NOT NULL
    )""",
    # ---- Phase 2: Compliance ----
    """CREATE TABLE IF NOT EXISTS sober_living_document_checklists (
        checklist_id                      TEXT PRIMARY KEY,
        resident_id                       TEXT NOT NULL REFERENCES sober_living_residents(resident_id),
        stay_id                           TEXT NOT NULL REFERENCES sober_living_stays(stay_id),
        house_rules_signed                INTEGER DEFAULT 0,
        house_rules_signed_date           TEXT,
        photo_id_on_file                  INTEGER DEFAULT 0,
        emergency_contact_on_file         INTEGER DEFAULT 0,
        intake_form_complete              INTEGER DEFAULT 0,
        consent_to_coordinate_care        INTEGER DEFAULT 0,
        medication_policy_signed          INTEGER DEFAULT 0,
        ua_policy_signed                  INTEGER DEFAULT 0,
        financial_agreement_signed        INTEGER DEFAULT 0,
        grievance_policy_acknowledged     INTEGER DEFAULT 0,
        good_neighbor_policy_acknowledged INTEGER DEFAULT 0,
        release_of_information_on_file    INTEGER DEFAULT 0,
        missing_items_summary             TEXT,
        updated_at                        TEXT NOT NULL
    )""",
    # ---- Phase 2: UA Tests ----
    """CREATE TABLE IF NOT EXISTS sober_living_ua_tests (
        test_id                   TEXT PRIMARY KEY,
        house_id                  TEXT NOT NULL REFERENCES sober_living_houses(house_id),
        resident_id               TEXT NOT NULL REFERENCES sober_living_residents(resident_id),
        stay_id                   TEXT NOT NULL REFERENCES sober_living_stays(stay_id),
        test_date                 TEXT NOT NULL,
        test_time                 TEXT,
        test_type                 TEXT,
        test_method               TEXT,
        administered_by_name      TEXT,
        result                    TEXT,
        substances_tested_json    TEXT,
        positive_substances_json  TEXT,
        specimen_validity         TEXT,
        action_taken              TEXT,
        clinical_notified         INTEGER DEFAULT 0,
        clinical_notified_at      TEXT,
        case_manager_notified     INTEGER DEFAULT 0,
        case_manager_notified_at  TEXT,
        notes                     TEXT,
        created_at                TEXT NOT NULL
    )""",
    # ---- Phase 2: Incidents ----
    """CREATE TABLE IF NOT EXISTS sober_living_incidents (
        incident_id               TEXT PRIMARY KEY,
        house_id                  TEXT NOT NULL REFERENCES sober_living_houses(house_id),
        resident_id               TEXT,
        stay_id                   TEXT,
        incident_date             TEXT NOT NULL,
        incident_time             TEXT,
        incident_type             TEXT NOT NULL,
        severity                  TEXT,
        location_in_house         TEXT,
        description               TEXT,
        immediate_safety_concern  INTEGER DEFAULT 0,
        response_taken            TEXT,
        clinical_notified         INTEGER DEFAULT 0,
        clinical_notified_at      TEXT,
        case_manager_notified     INTEGER DEFAULT 0,
        law_enforcement_involved  INTEGER DEFAULT 0,
        emergency_services_involved INTEGER DEFAULT 0,
        witness_names             TEXT,
        reported_by_name          TEXT,
        follow_up_required        INTEGER DEFAULT 0,
        follow_up_due_date        TEXT,
        incident_resolved         INTEGER DEFAULT 0,
        resolution_notes          TEXT,
        created_at                TEXT NOT NULL,
        updated_at                TEXT NOT NULL
    )""",
    # ---- Phase 2: Rent ----
    """CREATE TABLE IF NOT EXISTS sober_living_rent_charges (
        charge_id    TEXT PRIMARY KEY,
        resident_id  TEXT NOT NULL REFERENCES sober_living_residents(resident_id),
        stay_id      TEXT NOT NULL REFERENCES sober_living_stays(stay_id),
        house_id     TEXT NOT NULL REFERENCES sober_living_houses(house_id),
        charge_month TEXT NOT NULL,
        charge_type  TEXT DEFAULT 'rent',
        amount       REAL NOT NULL,
        due_date     TEXT,
        status       TEXT NOT NULL DEFAULT 'unpaid',
        notes        TEXT,
        created_at   TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS sober_living_rent_payments (
        payment_id          TEXT PRIMARY KEY,
        resident_id         TEXT NOT NULL REFERENCES sober_living_residents(resident_id),
        stay_id             TEXT NOT NULL REFERENCES sober_living_stays(stay_id),
        house_id            TEXT NOT NULL REFERENCES sober_living_houses(house_id),
        payment_date        TEXT NOT NULL,
        amount              REAL NOT NULL,
        payment_method      TEXT,
        payment_for_month   TEXT,
        applied_charge_id   TEXT,
        is_late             INTEGER DEFAULT 0,
        late_fee_charged    REAL DEFAULT 0,
        receipt_number      TEXT,
        received_by         TEXT,
        notes               TEXT,
        created_at          TEXT NOT NULL
    )""",
    # ---- Phase 3: Meetings ----
    """CREATE TABLE IF NOT EXISTS sober_living_meetings (
        meeting_id       TEXT PRIMARY KEY,
        house_id         TEXT NOT NULL REFERENCES sober_living_houses(house_id) ON DELETE CASCADE,
        scheduled_date   TEXT NOT NULL,
        scheduled_time   TEXT,
        meeting_type     TEXT NOT NULL DEFAULT 'house',
        topic            TEXT,
        facilitator_name TEXT,
        location         TEXT,
        status           TEXT NOT NULL DEFAULT 'scheduled',
        attendance_json  TEXT,
        notes            TEXT,
        created_at       TEXT NOT NULL,
        updated_at       TEXT NOT NULL
    )""",
    # ---- Phase 3: Chores ----
    """CREATE TABLE IF NOT EXISTS sober_living_chores (
        chore_id      TEXT PRIMARY KEY,
        house_id      TEXT NOT NULL REFERENCES sober_living_houses(house_id) ON DELETE CASCADE,
        resident_id   TEXT REFERENCES sober_living_residents(resident_id),
        stay_id       TEXT,
        chore_name    TEXT NOT NULL,
        location      TEXT,
        due_date      TEXT NOT NULL,
        recurrence    TEXT DEFAULT 'once',
        assigned_by   TEXT,
        completed     INTEGER DEFAULT 0,
        completed_at  TEXT,
        verified_by   TEXT,
        notes         TEXT,
        created_at    TEXT NOT NULL,
        updated_at    TEXT NOT NULL
    )""",
    # ---- Phase 3: Passes ----
    """CREATE TABLE IF NOT EXISTS sober_living_passes (
        pass_id          TEXT PRIMARY KEY,
        house_id         TEXT NOT NULL REFERENCES sober_living_houses(house_id) ON DELETE CASCADE,
        resident_id      TEXT NOT NULL REFERENCES sober_living_residents(resident_id),
        stay_id          TEXT NOT NULL,
        pass_type        TEXT NOT NULL DEFAULT 'day',
        destination      TEXT,
        leave_date       TEXT NOT NULL,
        leave_time       TEXT,
        expected_return_date TEXT NOT NULL,
        expected_return_time TEXT,
        actual_return_date   TEXT,
        actual_return_time   TEXT,
        approved_by      TEXT,
        status           TEXT NOT NULL DEFAULT 'approved',
        is_blackout      INTEGER DEFAULT 0,
        notes            TEXT,
        created_at       TEXT NOT NULL,
        updated_at       TEXT NOT NULL
    )""",
    # ---- Phase 3: Curfew checks ----
    """CREATE TABLE IF NOT EXISTS sober_living_curfew_checks (
        check_id       TEXT PRIMARY KEY,
        house_id       TEXT NOT NULL REFERENCES sober_living_houses(house_id) ON DELETE CASCADE,
        check_date     TEXT NOT NULL,
        resident_id    TEXT NOT NULL REFERENCES sober_living_residents(resident_id),
        stay_id        TEXT NOT NULL,
        status         TEXT NOT NULL DEFAULT 'pending',
        checked_at     TEXT,
        checked_by     TEXT,
        method         TEXT,
        notes          TEXT,
        created_at     TEXT NOT NULL,
        updated_at     TEXT NOT NULL
    )""",
    # ---- Indexes ----
    "CREATE INDEX IF NOT EXISTS idx_sl_rooms_house      ON sober_living_rooms(house_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_beds_house       ON sober_living_beds(house_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_beds_room        ON sober_living_beds(room_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_stays_resident   ON sober_living_stays(resident_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_stays_house      ON sober_living_stays(house_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_stays_bed        ON sober_living_stays(bed_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_ua_house         ON sober_living_ua_tests(house_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_ua_resident      ON sober_living_ua_tests(resident_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_incidents_house  ON sober_living_incidents(house_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_rcharge_stay     ON sober_living_rent_charges(stay_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_rpay_stay        ON sober_living_rent_payments(stay_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_meetings_house   ON sober_living_meetings(house_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_meetings_date    ON sober_living_meetings(scheduled_date)",
    "CREATE INDEX IF NOT EXISTS idx_sl_chores_house     ON sober_living_chores(house_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_chores_date      ON sober_living_chores(due_date)",
    "CREATE INDEX IF NOT EXISTS idx_sl_passes_house     ON sober_living_passes(house_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_passes_resident  ON sober_living_passes(resident_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_curfew_house     ON sober_living_curfew_checks(house_id)",
    "CREATE INDEX IF NOT EXISTS idx_sl_curfew_date      ON sober_living_curfew_checks(check_date)",
]


def _setup_schema() -> None:
    """
    Create all tables if they don't exist.

    Postgres: each DDL runs in its own mini-transaction via SAVEPOINT so that a
    failure on one statement (e.g. table already exists with a different constraint)
    does not abort the entire connection and block every subsequent statement.
    """
    backend = "postgres" if _use_postgres() else "sqlite"
    log.info(f"[sober_living] init_db starting — backend={backend}")

    if _use_postgres():
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(
            _database_url(),
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
        try:
            conn.autocommit = False
            cur = conn.cursor()
            for i, ddl in enumerate(_DDL):
                try:
                    cur.execute("SAVEPOINT sl_ddl")
                    cur.execute(ddl)
                    cur.execute("RELEASE SAVEPOINT sl_ddl")
                except Exception as e:
                    cur.execute("ROLLBACK TO SAVEPOINT sl_ddl")
                    # "already exists" is normal on repeat startups — log at DEBUG
                    msg = str(e).strip().splitlines()[0]
                    log.debug(f"[sober_living] DDL[{i}] skipped: {msg}")
            conn.commit()
            log.info("[sober_living] init_db complete")
        except Exception as e:
            conn.rollback()
            log.error(f"[sober_living] init_db FAILED: {e}")
            raise
        finally:
            conn.close()
    else:
        SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(SQLITE_PATH))
        conn.execute("PRAGMA foreign_keys = ON")
        for ddl in _DDL:
            try:
                conn.execute(ddl)
            except Exception as e:
                log.debug(f"[sober_living] SQLite DDL skip: {e}")
        conn.commit()
        conn.close()
        log.info("[sober_living] init_db complete (sqlite)")


def _pg_table_exists(cur, table: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM pg_catalog.pg_class c
        WHERE c.relname = %s
          AND c.relkind = 'r'
        LIMIT 1
        """,
        (table,),
    )
    return cur.fetchone() is not None


def _pg_col_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM pg_catalog.pg_attribute a
        JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
        WHERE c.relname = %s
          AND a.attname = %s
          AND a.attnum > 0
          AND NOT a.attisdropped
        LIMIT 1
        """,
        (table, column),
    )
    return cur.fetchone() is not None


def _migrate_legacy() -> None:
    """
    Bring any existing Postgres table up to the current schema.

    Three operations, each in its own SAVEPOINT so failures don't cascade:
      1. Column renames  — old_name -> new_name if old_name still exists
      2. Column additions — ADD COLUMN IF NOT EXISTS for every column the old
         schema lacked (CREATE TABLE IF NOT EXISTS is a no-op on existing tables,
         so new columns were never added to tables created by earlier deployments)
      3. Type fixes      — ALTER COLUMN ... USING ... for columns whose type
         changed (e.g. is_active was renamed from status TEXT, type must be INTEGER)

    Safe to call repeatedly — all operations are idempotent.
    Only runs on Postgres; SQLite starts fresh from DDL.
    """
    if not _use_postgres():
        return

    import psycopg2
    import psycopg2.extras

    # Step 1: renames (old_col -> new_col)
    renames = [
        ("sober_living_houses",    "name",             "house_name"),
        ("sober_living_houses",    "manager_name",     "house_manager_name"),
        ("sober_living_houses",    "phone",            "house_manager_phone"),
        ("sober_living_houses",    "email",            "house_manager_email"),
        ("sober_living_houses",    "gender_policy",    "house_type"),
        ("sober_living_houses",    "total_capacity",   "total_beds"),
        ("sober_living_houses",    "status",           "is_active"),
        ("sober_living_rooms",     "room_number",      "room_name"),
        ("sober_living_beds",      "status",           "bed_status"),
        ("sober_living_stays",     "status",           "resident_status"),
        ("sober_living_stays",     "move_out_date",    "actual_move_out_date"),
        ("sober_living_stays",     "discharge_reason", "move_out_reason"),
        ("sober_living_residents", "client_id",        "linked_client_id"),
    ]

    # Step 2: columns that must exist but may be absent on old installs
    # (table, column, column_definition)
    add_columns = [
        # sober_living_houses — columns added after initial deployment
        ("sober_living_houses", "house_manager_name",        "TEXT"),
        ("sober_living_houses", "house_manager_phone",       "TEXT"),
        ("sober_living_houses", "house_manager_email",       "TEXT"),
        ("sober_living_houses", "address",                   "TEXT"),
        ("sober_living_houses", "city",                      "TEXT"),
        ("sober_living_houses", "state",                     "TEXT"),
        ("sober_living_houses", "zip_code",                  "TEXT"),
        ("sober_living_houses", "house_type",                "TEXT DEFAULT 'any'"),
        ("sober_living_houses", "certification_level",       "TEXT"),
        ("sober_living_houses", "total_beds",                "INTEGER DEFAULT 0"),
        ("sober_living_houses", "monthly_rent",              "REAL"),
        ("sober_living_houses", "house_rules_version",       "TEXT"),
        ("sober_living_houses", "affiliated_clinical_program", "TEXT"),
        ("sober_living_houses", "notes",                     "TEXT"),
        ("sober_living_houses", "is_active",                 "INTEGER DEFAULT 1"),
        ("sober_living_houses", "certification_notes",       "TEXT"),
        ("sober_living_houses", "payment_type",              "TEXT DEFAULT 'unknown'"),
        ("sober_living_houses", "accepts_insurance",         "TEXT DEFAULT 'unknown'"),
        ("sober_living_houses", "insurance_plans_accepted",  "TEXT"),
        ("sober_living_houses", "funding_notes",             "TEXT"),
        ("sober_living_houses", "requires_clinical_program", "INTEGER DEFAULT 0"),
        ("sober_living_houses", "billing_contact_name",      "TEXT"),
        ("sober_living_houses", "billing_contact_phone",     "TEXT"),
        ("sober_living_houses", "billing_contact_email",     "TEXT"),
        # sober_living_rooms
        ("sober_living_rooms",  "floor",                     "TEXT"),
        ("sober_living_rooms",  "room_type",                 "TEXT"),
        ("sober_living_rooms",  "max_occupancy",             "INTEGER DEFAULT 1"),
        ("sober_living_rooms",  "notes",                     "TEXT"),
        ("sober_living_rooms",  "is_active",                 "INTEGER DEFAULT 1"),
        # sober_living_beds
        ("sober_living_beds",   "current_resident_id",       "TEXT"),
        ("sober_living_beds",   "reserved_for_client_id",    "TEXT"),
        ("sober_living_beds",   "reserved_until",            "TEXT"),
        ("sober_living_beds",   "notes",                     "TEXT"),
        # sober_living_stays
        ("sober_living_stays",  "expected_move_out_date",    "TEXT"),
        ("sober_living_stays",  "actual_move_out_date",      "TEXT"),
        ("sober_living_stays",  "move_out_reason",           "TEXT"),
        ("sober_living_stays",  "resident_status",           "TEXT DEFAULT 'active'"),
        ("sober_living_stays",  "clinical_program",          "TEXT"),
        ("sober_living_stays",  "case_manager_name",         "TEXT"),
        ("sober_living_stays",  "referral_source",           "TEXT"),
        ("sober_living_stays",  "step_down_from_level",      "TEXT"),
        ("sober_living_stays",  "discharge_destination",     "TEXT"),
        # sober_living_residents
        ("sober_living_residents", "linked_client_id",              "TEXT"),
        ("sober_living_residents", "emergency_contact_relationship", "TEXT"),
        ("sober_living_residents", "primary_substance",              "TEXT"),
        ("sober_living_residents", "sobriety_date",                  "TEXT"),
        # Phase 3 — new tables; ADD COLUMN on non-existent table is caught and skipped
        # These are here as a safety net; _setup_schema handles table creation
        ("sober_living_meetings",  "attendance_json",  "TEXT"),
        ("sober_living_meetings",  "location",         "TEXT"),
        ("sober_living_chores",    "verified_by",      "TEXT"),
        ("sober_living_chores",    "completed_at",     "TEXT"),
        ("sober_living_passes",    "is_blackout",      "INTEGER DEFAULT 0"),
        ("sober_living_curfew_checks", "method",       "TEXT"),
    ]

    # Step 3: type fixes — columns that exist but have wrong type
    # (table, column, new_pg_type, using_expr)
    # is_active was renamed from status TEXT — must be INTEGER for "= 1" to work
    type_fixes = [
        ("sober_living_houses", "is_active", "INTEGER",
         "CASE WHEN is_active::text IN ('1','true','active') THEN 1 ELSE 0 END"),
    ]

    conn = psycopg2.connect(
        _database_url(),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    try:
        conn.autocommit = False
        cur = conn.cursor()
        log.info(f"[sober_living] _migrate_legacy starting — catalog=pg_catalog "
                 f"renames={len(renames)} add_columns={len(add_columns)} type_fixes={len(type_fixes)}")

        # --- Step 1: renames ---
        for table, old_col, new_col in renames:
            try:
                cur.execute("SAVEPOINT sl_rename")
                if not _pg_table_exists(cur, table):
                    cur.execute("RELEASE SAVEPOINT sl_rename")
                    continue
                if _pg_col_exists(cur, table, old_col):
                    cur.execute(f"ALTER TABLE {table} RENAME COLUMN {old_col} TO {new_col}")
                    log.info(f"[sober_living] renamed {table}.{old_col} -> {new_col}")
                cur.execute("RELEASE SAVEPOINT sl_rename")
            except Exception as e:
                cur.execute("ROLLBACK TO SAVEPOINT sl_rename")
                log.warning(f"[sober_living] rename skipped {table}.{old_col}: {e}")

        # --- Step 2: add missing columns ---
        # Attempt ALTER TABLE directly; catch DuplicateColumn as a no-op.
        # This avoids any dependency on catalog queries for the add path.
        for table, col, col_def in add_columns:
            try:
                cur.execute("SAVEPOINT sl_add_col")
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
                cur.execute("RELEASE SAVEPOINT sl_add_col")
                log.info(f"[sober_living] added column {table}.{col}")
            except psycopg2.errors.DuplicateColumn:
                cur.execute("ROLLBACK TO SAVEPOINT sl_add_col")
                log.debug(f"[sober_living] column already exists (ok): {table}.{col}")
            except Exception as e:
                cur.execute("ROLLBACK TO SAVEPOINT sl_add_col")
                log.warning(f"[sober_living] add_col FAILED {table}.{col}: {e}")

        # --- Step 3: type fixes ---
        for table, col, new_type, using in type_fixes:
            try:
                cur.execute("SAVEPOINT sl_type_fix")
                if not _pg_table_exists(cur, table) or not _pg_col_exists(cur, table, col):
                    cur.execute("RELEASE SAVEPOINT sl_type_fix")
                    continue
                # Check current type via pg_catalog (avoids information_schema search_path issues)
                cur.execute(
                    """
                    SELECT t.typname
                    FROM pg_catalog.pg_attribute a
                    JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
                    JOIN pg_catalog.pg_type t ON t.oid = a.atttypid
                    WHERE c.relname = %s AND a.attname = %s
                      AND a.attnum > 0 AND NOT a.attisdropped
                    LIMIT 1
                    """,
                    (table, col),
                )
                row = cur.fetchone()
                current_type = row["typname"] if row else None
                if current_type and current_type.lower() not in ("int4", "int8", "int2", "integer"):
                    cur.execute(
                        f"ALTER TABLE {table} ALTER COLUMN {col} TYPE {new_type} USING {using}"
                    )
                    log.info(f"[sober_living] fixed type {table}.{col}: {current_type} -> {new_type}")
                cur.execute("RELEASE SAVEPOINT sl_type_fix")
            except Exception as e:
                cur.execute("ROLLBACK TO SAVEPOINT sl_type_fix")
                log.warning(f"[sober_living] type_fix skipped {table}.{col}: {e}")

        conn.commit()
        log.info("[sober_living] _migrate_legacy complete")
    except Exception as e:
        conn.rollback()
        log.error(f"[sober_living] _migrate_legacy FAILED: {e}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class SoberLivingStore:

    def __init__(self):
        try:
            _setup_schema()
        except Exception as e:
            log.error(f"[sober_living] schema setup error (continuing): {e}")
        try:
            _migrate_legacy()
        except Exception as e:
            log.error(f"[sober_living] migration error (continuing): {e}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_summary(self) -> Dict:
        try:
            with _db() as conn:
                houses_row = _fetchone(conn,
                    "SELECT COUNT(*) as c FROM sober_living_houses WHERE CAST(is_active AS TEXT) = '1'")
                houses_count = int(houses_row["c"]) if houses_row and houses_row.get("c") is not None else 0

                # configured_beds = actual bed records (not total_beds field)
                beds_row = _fetchone(conn, "SELECT COUNT(*) as c FROM sober_living_beds")
                configured_beds = int(beds_row["c"]) if beds_row else 0

                occ_row = _fetchone(conn,
                    "SELECT COUNT(*) as c FROM sober_living_beds WHERE bed_status = 'occupied'")
                occupied = int(occ_row["c"]) if occ_row else 0

                avail_row = _fetchone(conn,
                    "SELECT COUNT(*) as c FROM sober_living_beds WHERE bed_status = 'available'")
                available = int(avail_row["c"]) if avail_row else 0

                res_row = _fetchone(conn,
                    "SELECT COUNT(*) as c FROM sober_living_beds WHERE bed_status = 'reserved'")
                reserved = int(res_row["c"]) if res_row else 0

                stays_row = _fetchone(conn,
                    "SELECT COUNT(*) as c FROM sober_living_stays WHERE resident_status = 'active'")
                active_stays = int(stays_row["c"]) if stays_row else 0

                planned_row = _fetchone(conn,
                    "SELECT COALESCE(SUM(total_beds),0) as c FROM sober_living_houses WHERE CAST(is_active AS TEXT) = '1'")
                planned_capacity = int(planned_row["c"]) if planned_row else 0

            rate = round((occupied / configured_beds * 100), 1) if configured_beds else 0.0
            return {
                "total_houses":     houses_count,
                "total_beds":       configured_beds,
                "configured_beds":  configured_beds,
                "planned_capacity": planned_capacity,
                "occupied_beds":    occupied,
                "available_beds":   available,
                "reserved_beds":    reserved,
                "active_stays":     active_stays,
                "occupancy_rate":   rate,
            }
        except Exception as e:
            log.error(f"[sober_living] get_summary error: {e}")
            return {
                "total_houses": 0,
                "total_beds": 0,
                "configured_beds": 0,
                "planned_capacity": 0,
                "occupied_beds": 0,
                "available_beds": 0,
                "reserved_beds": 0,
                "active_stays": 0,
                "occupancy_rate": 0.0,
            }

    # ------------------------------------------------------------------
    # Houses
    # ------------------------------------------------------------------

    def _bed_counts(self, conn, house_id: str, planned_capacity: int = 0) -> Dict:
        rows = _fetchall(conn,
            "SELECT bed_status, COUNT(*) as cnt FROM sober_living_beds WHERE house_id = %s GROUP BY bed_status",
            (house_id,))
        counts = {r["bed_status"]: int(r["cnt"]) for r in rows}
        configured = sum(counts.values())
        occupied   = counts.get("occupied", 0)
        return {
            "total":            configured,
            "configured":       configured,
            "available":        counts.get("available", 0),
            "occupied":         occupied,
            "reserved":         counts.get("reserved", 0),
            "maintenance":      counts.get("maintenance", 0),
            "planned_capacity": planned_capacity,
            "setup_incomplete": planned_capacity > configured,
            "beds_to_configure": max(0, planned_capacity - configured),
        }

    def list_houses(self) -> List[Dict]:
        try:
            with _db() as conn:
                rows = _fetchall(conn,
                    "SELECT * FROM sober_living_houses WHERE CAST(is_active AS TEXT) = '1' ORDER BY house_name")
                for h in rows:
                    planned = int(h.get("total_beds") or 0)
                    h["bed_counts"] = self._bed_counts(conn, h["house_id"], planned)
                    h["is_active"] = bool(h.get("is_active", 1))
            return rows
        except Exception as e:
            log.error(f"[sober_living] list_houses error: {e}")
            return []

    def get_house(self, house_id: str) -> Optional[Dict]:
        with _db() as conn:
            h = _fetchone(conn,
                "SELECT * FROM sober_living_houses WHERE house_id = %s", (house_id,))
            if h:
                planned = int(h.get("total_beds") or 0)
                h["bed_counts"] = self._bed_counts(conn, house_id, planned)
                h["is_active"] = bool(h.get("is_active", 1))
        return h

    def create_house(self, data: Dict) -> Optional[Dict]:
        house_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_houses
                (house_id, house_name, house_manager_name, house_manager_phone,
                 house_manager_email, address, city, state, zip_code,
                 house_type, certification_level, certification_notes, total_beds, monthly_rent,
                 house_rules_version, affiliated_clinical_program, notes, is_active,
                 payment_type, accepts_insurance, insurance_plans_accepted, funding_notes,
                 requires_clinical_program, billing_contact_name, billing_contact_phone, billing_contact_email,
                 created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (house_id,
                 data["house_name"],
                 data.get("house_manager_name"),
                 data.get("house_manager_phone"),
                 data.get("house_manager_email"),
                 data.get("address"),
                 data.get("city"),
                 data.get("state"),
                 data.get("zip_code"),
                 data.get("house_type", "any"),
                 data.get("certification_level"),
                 data.get("certification_notes"),
                 data.get("total_beds", 0),
                 data.get("monthly_rent"),
                 data.get("house_rules_version"),
                 data.get("affiliated_clinical_program"),
                 data.get("notes"),
                 1,
                 data.get("payment_type", "unknown"),
                 data.get("accepts_insurance", "unknown"),
                 data.get("insurance_plans_accepted"),
                 data.get("funding_notes"),
                 int(data.get("requires_clinical_program") or 0),
                 data.get("billing_contact_name"),
                 data.get("billing_contact_phone"),
                 data.get("billing_contact_email"),
                 now, now))
        return self.get_house(house_id)

    def update_house(self, house_id: str, data: Dict) -> Optional[Dict]:
        updatable = [
            "house_name", "house_manager_name", "house_manager_phone",
            "house_manager_email", "address", "city", "state", "zip_code",
            "house_type", "certification_level", "certification_notes", "total_beds", "monthly_rent",
            "house_rules_version", "affiliated_clinical_program", "notes", "is_active",
            "payment_type", "accepts_insurance", "insurance_plans_accepted", "funding_notes",
            "requires_clinical_program", "billing_contact_name", "billing_contact_phone", "billing_contact_email",
        ]
        pairs = [f"{f} = %s" for f in updatable if f in data]
        vals  = [data[f]     for f in updatable if f in data]
        if not pairs:
            return self.get_house(house_id)
        with _db() as conn:
            _exec(conn,
                f"UPDATE sober_living_houses SET {', '.join(pairs)}, updated_at = %s WHERE house_id = %s",
                vals + [_now(), house_id])
        return self.get_house(house_id)

    # ------------------------------------------------------------------
    # Rooms
    # ------------------------------------------------------------------

    def list_rooms(self, house_id: str) -> List[Dict]:
        with _db() as conn:
            return _fetchall(conn,
                "SELECT * FROM sober_living_rooms WHERE house_id = %s ORDER BY room_name",
                (house_id,))

    def create_room(self, house_id: str, data: Dict) -> Dict:
        room_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_rooms
                (room_id, house_id, room_name, floor, room_type, max_occupancy, notes, is_active, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (room_id, house_id,
                 data["room_name"],
                 data.get("floor"),
                 data.get("room_type"),
                 data.get("max_occupancy", 1),
                 data.get("notes"),
                 1, now, now))
            return _fetchone(conn, "SELECT * FROM sober_living_rooms WHERE room_id = %s", (room_id,))

    def update_room(self, room_id: str, data: Dict) -> Optional[Dict]:
        updatable = ["room_name", "floor", "room_type", "max_occupancy", "notes", "is_active"]
        pairs = [f"{f} = %s" for f in updatable if f in data]
        vals  = [data[f]     for f in updatable if f in data]
        if not pairs:
            with _db() as conn:
                return _fetchone(conn, "SELECT * FROM sober_living_rooms WHERE room_id = %s", (room_id,))
        with _db() as conn:
            _exec(conn,
                f"UPDATE sober_living_rooms SET {', '.join(pairs)}, updated_at = %s WHERE room_id = %s",
                vals + [_now(), room_id])
            return _fetchone(conn, "SELECT * FROM sober_living_rooms WHERE room_id = %s", (room_id,))

    # ------------------------------------------------------------------
    # Beds
    # ------------------------------------------------------------------

    def list_beds(self, house_id: str) -> List[Dict]:
        with _db() as conn:
            return _fetchall(conn, """
                SELECT b.*,
                       r.room_name,
                       s.stay_id,
                       res.first_name, res.last_name
                FROM sober_living_beds b
                JOIN sober_living_rooms r ON b.room_id = r.room_id
                LEFT JOIN sober_living_stays s
                       ON s.bed_id = b.bed_id AND s.resident_status = 'active'
                LEFT JOIN sober_living_residents res
                       ON res.resident_id = s.resident_id
                WHERE b.house_id = %s
                ORDER BY r.room_name, b.bed_label""", (house_id,))

    def get_bed(self, bed_id: str) -> Optional[Dict]:
        with _db() as conn:
            return _fetchone(conn, "SELECT * FROM sober_living_beds WHERE bed_id = %s", (bed_id,))

    def create_bed(self, house_id: str, data: Dict) -> Dict:
        bed_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_beds
                (bed_id, house_id, room_id, bed_label, bed_status,
                 reserved_for_client_id, reserved_until, notes, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (bed_id, house_id,
                 data["room_id"],
                 data["bed_label"],
                 data.get("bed_status", "available"),
                 data.get("reserved_for_client_id"),
                 data.get("reserved_until"),
                 data.get("notes"),
                 now, now))
            return _fetchone(conn, "SELECT * FROM sober_living_beds WHERE bed_id = %s", (bed_id,))

    def update_bed(self, bed_id: str, data: Dict) -> Optional[Dict]:
        updatable = ["bed_label", "bed_status", "room_id", "reserved_for_client_id", "reserved_until", "notes"]
        pairs = [f"{f} = %s" for f in updatable if f in data]
        vals  = [data[f]     for f in updatable if f in data]
        if not pairs:
            return self.get_bed(bed_id)
        with _db() as conn:
            _exec(conn,
                f"UPDATE sober_living_beds SET {', '.join(pairs)}, updated_at = %s WHERE bed_id = %s",
                vals + [_now(), bed_id])
        return self.get_bed(bed_id)

    def bulk_create_beds(self, house_id: str, data: Dict) -> List[Dict]:
        room_id      = data["room_id"]
        quantity     = int(data.get("quantity", 1))
        label_prefix = data.get("label_prefix", "").strip()
        start_number = int(data.get("start_number", 1))
        bed_status   = data.get("bed_status", "available")

        with _db() as conn:
            # Fetch room name to use as fallback prefix
            room = _fetchone(conn,
                "SELECT room_name FROM sober_living_rooms WHERE room_id = %s", (room_id,))
            prefix = label_prefix or (room["room_name"] if room else "Bed")

            created = []
            for i in range(quantity):
                n        = start_number + i
                label    = f"{prefix} {n}" if prefix else f"Bed {n}"
                bed_id   = _uid()
                now      = _now()
                _exec(conn, """
                    INSERT INTO sober_living_beds
                        (bed_id, house_id, room_id, bed_label, bed_status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (bed_id, house_id, room_id, label, bed_status, now, now))
                created.append({
                    "bed_id":     bed_id,
                    "house_id":   house_id,
                    "room_id":    room_id,
                    "bed_label":  label,
                    "bed_status": bed_status,
                    "created_at": now,
                })
        return created

    def _set_bed_status(self, conn, bed_id: str, status: str, resident_id: Optional[str] = None) -> None:
        if resident_id is not None:
            _exec(conn,
                "UPDATE sober_living_beds SET bed_status = %s, current_resident_id = %s, updated_at = %s WHERE bed_id = %s",
                (status, resident_id, _now(), bed_id))
        else:
            _exec(conn,
                "UPDATE sober_living_beds SET bed_status = %s, current_resident_id = NULL, updated_at = %s WHERE bed_id = %s",
                (status, _now(), bed_id))

    # ------------------------------------------------------------------
    # Residents
    # ------------------------------------------------------------------

    def list_residents_for_house(self, house_id: str) -> List[Dict]:
        with _db() as conn:
            return _fetchall(conn, """
                SELECT res.*,
                       s.stay_id, s.bed_id, s.move_in_date, s.resident_status as stay_status,
                       b.bed_label, r.room_name
                FROM sober_living_stays s
                JOIN sober_living_residents res ON res.resident_id = s.resident_id
                LEFT JOIN sober_living_beds b ON b.bed_id = s.bed_id
                LEFT JOIN sober_living_rooms r ON r.room_id = b.room_id
                WHERE s.house_id = %s AND s.resident_status = 'active'
                ORDER BY res.last_name, res.first_name""", (house_id,))

    def list_all_residents(self) -> List[Dict]:
        """All residents (not filtered by house) — used to populate assign-stay dropdown."""
        with _db() as conn:
            return _fetchall(conn,
                "SELECT * FROM sober_living_residents ORDER BY last_name, first_name")

    def get_resident(self, resident_id: str) -> Optional[Dict]:
        with _db() as conn:
            return _fetchone(conn,
                "SELECT * FROM sober_living_residents WHERE resident_id = %s", (resident_id,))

    def create_resident(self, data: Dict) -> Dict:
        resident_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_residents
                (resident_id, linked_client_id, first_name, last_name, date_of_birth,
                 phone, email, emergency_contact_name, emergency_contact_phone,
                 emergency_contact_relationship, primary_substance, sobriety_date,
                 notes, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (resident_id,
                 data.get("linked_client_id"),
                 data["first_name"], data["last_name"],
                 data.get("date_of_birth"),
                 data.get("phone"), data.get("email"),
                 data.get("emergency_contact_name"),
                 data.get("emergency_contact_phone"),
                 data.get("emergency_contact_relationship"),
                 data.get("primary_substance"),
                 data.get("sobriety_date"),
                 data.get("notes"),
                 now, now))
            return _fetchone(conn,
                "SELECT * FROM sober_living_residents WHERE resident_id = %s", (resident_id,))

    def update_resident(self, resident_id: str, data: Dict) -> Optional[Dict]:
        updatable = [
            "first_name", "last_name", "date_of_birth", "phone", "email",
            "emergency_contact_name", "emergency_contact_phone",
            "emergency_contact_relationship", "primary_substance", "sobriety_date", "notes",
        ]
        pairs = [f"{f} = %s" for f in updatable if f in data]
        vals  = [data[f]     for f in updatable if f in data]
        if not pairs:
            return self.get_resident(resident_id)
        with _db() as conn:
            _exec(conn,
                f"UPDATE sober_living_residents SET {', '.join(pairs)}, updated_at = %s WHERE resident_id = %s",
                vals + [_now(), resident_id])
        return self.get_resident(resident_id)

    # ------------------------------------------------------------------
    # Stays
    # ------------------------------------------------------------------

    def _get_stay(self, stay_id: str) -> Optional[Dict]:
        with _db() as conn:
            return _fetchone(conn,
                "SELECT * FROM sober_living_stays WHERE stay_id = %s", (stay_id,))

    def create_stay(self, data: Dict) -> Dict:
        stay_id = str(uuid.uuid4())
        now = _now()
        bed_id = data.get("bed_id") or None
        with _db() as conn:
            if bed_id:
                conflict = _fetchone(conn,
                    "SELECT stay_id FROM sober_living_stays WHERE bed_id = %s AND resident_status = 'active'",
                    (bed_id,))
                if conflict:
                    raise ValueError(f"Bed is already occupied by an active stay")
            _exec(conn, """
                INSERT INTO sober_living_stays
                (stay_id, resident_id, house_id, bed_id, move_in_date,
                 expected_move_out_date, resident_status,
                 clinical_program, case_manager_name, referral_source,
                 step_down_from_level, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (stay_id,
                 data["resident_id"], data["house_id"], bed_id,
                 data.get("move_in_date", _today()),
                 data.get("expected_move_out_date"),
                 "active",
                 data.get("clinical_program"),
                 data.get("case_manager_name"),
                 data.get("referral_source"),
                 data.get("step_down_from_level"),
                 now, now))
            if bed_id:
                self._set_bed_status(conn, bed_id, "occupied", data["resident_id"])
            return _fetchone(conn, "SELECT * FROM sober_living_stays WHERE stay_id = %s", (stay_id,))

    def update_stay(self, stay_id: str, data: Dict) -> Optional[Dict]:
        updatable = [
            "move_in_date", "expected_move_out_date", "bed_id",
            "clinical_program", "case_manager_name", "referral_source",
            "step_down_from_level", "resident_status",
        ]
        pairs = [f"{f} = %s" for f in updatable if f in data]
        vals  = [data[f]     for f in updatable if f in data]
        if not pairs:
            return self._get_stay(stay_id)
        with _db() as conn:
            _exec(conn,
                f"UPDATE sober_living_stays SET {', '.join(pairs)}, updated_at = %s WHERE stay_id = %s",
                vals + [_now(), stay_id])
        return self._get_stay(stay_id)

    def discharge_stay(self, stay_id: str, data: Dict) -> Optional[Dict]:
        with _db() as conn:
            stay = _fetchone(conn, "SELECT * FROM sober_living_stays WHERE stay_id = %s", (stay_id,))
            if not stay:
                return None
            _exec(conn, """
                UPDATE sober_living_stays
                SET resident_status = 'discharged',
                    actual_move_out_date = %s,
                    move_out_reason = %s,
                    discharge_destination = %s,
                    updated_at = %s
                WHERE stay_id = %s""",
                (data.get("actual_move_out_date", _today()),
                 data.get("move_out_reason"),
                 data.get("discharge_destination"),
                 _now(), stay_id))
            if stay.get("bed_id"):
                self._set_bed_status(conn, stay["bed_id"], "available")
            return _fetchone(conn, "SELECT * FROM sober_living_stays WHERE stay_id = %s", (stay_id,))

    def transfer_bed(self, stay_id: str, new_bed_id: str) -> Optional[Dict]:
        with _db() as conn:
            stay = _fetchone(conn,
                "SELECT * FROM sober_living_stays WHERE stay_id = %s AND resident_status = 'active'",
                (stay_id,))
            if not stay:
                return None
            conflict = _fetchone(conn,
                "SELECT stay_id FROM sober_living_stays WHERE bed_id = %s AND resident_status = 'active'",
                (new_bed_id,))
            if conflict:
                raise ValueError("Target bed is already occupied")
            old_bed_id = stay.get("bed_id")
            _exec(conn,
                "UPDATE sober_living_stays SET bed_id = %s, updated_at = %s WHERE stay_id = %s",
                (new_bed_id, _now(), stay_id))
            if old_bed_id:
                self._set_bed_status(conn, old_bed_id, "available")
            self._set_bed_status(conn, new_bed_id, "occupied", stay["resident_id"])
            return _fetchone(conn, "SELECT * FROM sober_living_stays WHERE stay_id = %s", (stay_id,))

    # ------------------------------------------------------------------
    # Compliance
    # ------------------------------------------------------------------

    def get_checklist(self, stay_id: str) -> Optional[Dict]:
        with _db() as conn:
            return _fetchone(conn,
                "SELECT * FROM sober_living_document_checklists WHERE stay_id = %s",
                (stay_id,))

    def upsert_checklist(self, stay_id: str, resident_id: str, data: Dict) -> Dict:
        with _db() as conn:
            existing = _fetchone(conn,
                "SELECT checklist_id FROM sober_living_document_checklists WHERE stay_id = %s",
                (stay_id,))
            now = _now()
            bool_fields = [
                "house_rules_signed", "photo_id_on_file", "emergency_contact_on_file",
                "intake_form_complete", "consent_to_coordinate_care",
                "medication_policy_signed", "ua_policy_signed",
                "financial_agreement_signed", "grievance_policy_acknowledged",
                "good_neighbor_policy_acknowledged", "release_of_information_on_file",
            ]
            if existing:
                checklist_id = existing["checklist_id"]
                updatable = bool_fields + ["house_rules_signed_date", "missing_items_summary"]
                pairs = [f"{f} = %s" for f in updatable if f in data]
                vals  = [int(data[f]) if f in bool_fields else data[f] for f in updatable if f in data]
                if pairs:
                    _exec(conn,
                        f"UPDATE sober_living_document_checklists SET {', '.join(pairs)}, updated_at = %s WHERE checklist_id = %s",
                        vals + [now, checklist_id])
            else:
                checklist_id = str(uuid.uuid4())
                _exec(conn, """
                    INSERT INTO sober_living_document_checklists
                    (checklist_id, resident_id, stay_id,
                     house_rules_signed, house_rules_signed_date,
                     photo_id_on_file, emergency_contact_on_file, intake_form_complete,
                     consent_to_coordinate_care, medication_policy_signed,
                     ua_policy_signed, financial_agreement_signed,
                     grievance_policy_acknowledged, good_neighbor_policy_acknowledged,
                     release_of_information_on_file, missing_items_summary, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (checklist_id, resident_id, stay_id,
                     int(data.get("house_rules_signed", 0)),
                     data.get("house_rules_signed_date"),
                     int(data.get("photo_id_on_file", 0)),
                     int(data.get("emergency_contact_on_file", 0)),
                     int(data.get("intake_form_complete", 0)),
                     int(data.get("consent_to_coordinate_care", 0)),
                     int(data.get("medication_policy_signed", 0)),
                     int(data.get("ua_policy_signed", 0)),
                     int(data.get("financial_agreement_signed", 0)),
                     int(data.get("grievance_policy_acknowledged", 0)),
                     int(data.get("good_neighbor_policy_acknowledged", 0)),
                     int(data.get("release_of_information_on_file", 0)),
                     data.get("missing_items_summary"),
                     now))
            return _fetchone(conn,
                "SELECT * FROM sober_living_document_checklists WHERE checklist_id = %s",
                (checklist_id,))

    # ------------------------------------------------------------------
    # UA Tests
    # ------------------------------------------------------------------

    def list_ua_tests(self, house_id: str, resident_id: Optional[str] = None) -> List[Dict]:
        with _db() as conn:
            if resident_id:
                return _fetchall(conn,
                    "SELECT * FROM sober_living_ua_tests WHERE house_id = %s AND resident_id = %s ORDER BY test_date DESC",
                    (house_id, resident_id))
            return _fetchall(conn,
                "SELECT * FROM sober_living_ua_tests WHERE house_id = %s ORDER BY test_date DESC",
                (house_id,))

    def create_ua_test(self, data: Dict) -> Dict:
        test_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_ua_tests
                (test_id, house_id, resident_id, stay_id, test_date, test_time,
                 test_type, test_method, administered_by_name, result,
                 substances_tested_json, positive_substances_json,
                 specimen_validity, action_taken,
                 clinical_notified, clinical_notified_at,
                 case_manager_notified, case_manager_notified_at,
                 notes, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (test_id,
                 data["house_id"], data["resident_id"], data["stay_id"],
                 data["test_date"],
                 data.get("test_time"),
                 data.get("test_type"),
                 data.get("test_method"),
                 data.get("administered_by_name"),
                 data.get("result"),
                 data.get("substances_tested_json"),
                 data.get("positive_substances_json"),
                 data.get("specimen_validity"),
                 data.get("action_taken"),
                 int(data.get("clinical_notified", 0)),
                 data.get("clinical_notified_at"),
                 int(data.get("case_manager_notified", 0)),
                 data.get("case_manager_notified_at"),
                 data.get("notes"),
                 now))
            return _fetchone(conn,
                "SELECT * FROM sober_living_ua_tests WHERE test_id = %s", (test_id,))

    # ------------------------------------------------------------------
    # Incidents
    # ------------------------------------------------------------------

    def list_incidents(self, house_id: str) -> List[Dict]:
        with _db() as conn:
            return _fetchall(conn,
                "SELECT * FROM sober_living_incidents WHERE house_id = %s ORDER BY incident_date DESC, incident_time DESC",
                (house_id,))

    def create_incident(self, data: Dict) -> Dict:
        incident_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_incidents
                (incident_id, house_id, resident_id, stay_id, incident_date, incident_time,
                 incident_type, severity, location_in_house, description,
                 immediate_safety_concern, response_taken,
                 clinical_notified, clinical_notified_at,
                 case_manager_notified, law_enforcement_involved,
                 emergency_services_involved, witness_names, reported_by_name,
                 follow_up_required, follow_up_due_date,
                 incident_resolved, resolution_notes, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (incident_id,
                 data["house_id"],
                 data.get("resident_id"),
                 data.get("stay_id"),
                 data["incident_date"],
                 data.get("incident_time"),
                 data["incident_type"],
                 data.get("severity"),
                 data.get("location_in_house"),
                 data.get("description"),
                 int(data.get("immediate_safety_concern", 0)),
                 data.get("response_taken"),
                 int(data.get("clinical_notified", 0)),
                 data.get("clinical_notified_at"),
                 int(data.get("case_manager_notified", 0)),
                 int(data.get("law_enforcement_involved", 0)),
                 int(data.get("emergency_services_involved", 0)),
                 data.get("witness_names"),
                 data.get("reported_by_name"),
                 int(data.get("follow_up_required", 0)),
                 data.get("follow_up_due_date"),
                 int(data.get("incident_resolved", 0)),
                 data.get("resolution_notes"),
                 now, now))
            return _fetchone(conn,
                "SELECT * FROM sober_living_incidents WHERE incident_id = %s", (incident_id,))

    def update_incident(self, incident_id: str, data: Dict) -> Optional[Dict]:
        updatable = [
            "incident_type", "severity", "location_in_house", "description",
            "immediate_safety_concern", "response_taken", "clinical_notified",
            "clinical_notified_at", "case_manager_notified", "law_enforcement_involved",
            "emergency_services_involved", "witness_names", "reported_by_name",
            "follow_up_required", "follow_up_due_date", "incident_resolved", "resolution_notes",
        ]
        bool_fields = {
            "immediate_safety_concern", "clinical_notified", "case_manager_notified",
            "law_enforcement_involved", "emergency_services_involved",
            "follow_up_required", "incident_resolved",
        }
        pairs = [f"{f} = %s" for f in updatable if f in data]
        vals  = [int(data[f]) if f in bool_fields else data[f] for f in updatable if f in data]
        if not pairs:
            with _db() as conn:
                return _fetchone(conn,
                    "SELECT * FROM sober_living_incidents WHERE incident_id = %s", (incident_id,))
        with _db() as conn:
            _exec(conn,
                f"UPDATE sober_living_incidents SET {', '.join(pairs)}, updated_at = %s WHERE incident_id = %s",
                vals + [_now(), incident_id])
            return _fetchone(conn,
                "SELECT * FROM sober_living_incidents WHERE incident_id = %s", (incident_id,))

    # ------------------------------------------------------------------
    # Rent Charges
    # ------------------------------------------------------------------

    def list_charges(self, stay_id: str) -> List[Dict]:
        with _db() as conn:
            return _fetchall(conn,
                "SELECT * FROM sober_living_rent_charges WHERE stay_id = %s ORDER BY charge_month DESC",
                (stay_id,))

    def create_charge(self, data: Dict) -> Dict:
        charge_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_rent_charges
                (charge_id, resident_id, stay_id, house_id, charge_month,
                 charge_type, amount, due_date, status, notes, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (charge_id,
                 data["resident_id"], data["stay_id"], data["house_id"],
                 data["charge_month"],
                 data.get("charge_type", "rent"),
                 data["amount"],
                 data.get("due_date"),
                 data.get("status", "unpaid"),
                 data.get("notes"),
                 now))
            return _fetchone(conn,
                "SELECT * FROM sober_living_rent_charges WHERE charge_id = %s", (charge_id,))

    def update_charge_status(self, charge_id: str, status: str) -> Optional[Dict]:
        with _db() as conn:
            _exec(conn,
                "UPDATE sober_living_rent_charges SET status = %s WHERE charge_id = %s",
                (status, charge_id))
            return _fetchone(conn,
                "SELECT * FROM sober_living_rent_charges WHERE charge_id = %s", (charge_id,))

    # ------------------------------------------------------------------
    # Rent Payments
    # ------------------------------------------------------------------

    def list_payments(self, stay_id: str) -> List[Dict]:
        with _db() as conn:
            return _fetchall(conn,
                "SELECT * FROM sober_living_rent_payments WHERE stay_id = %s ORDER BY payment_date DESC",
                (stay_id,))

    def create_payment(self, data: Dict) -> Dict:
        payment_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_rent_payments
                (payment_id, resident_id, stay_id, house_id, payment_date, amount,
                 payment_method, payment_for_month, applied_charge_id,
                 is_late, late_fee_charged, receipt_number, received_by, notes, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (payment_id,
                 data["resident_id"], data["stay_id"], data["house_id"],
                 data.get("payment_date", _today()),
                 data["amount"],
                 data.get("payment_method"),
                 data.get("payment_for_month"),
                 data.get("applied_charge_id"),
                 int(data.get("is_late", 0)),
                 data.get("late_fee_charged", 0),
                 data.get("receipt_number"),
                 data.get("received_by"),
                 data.get("notes"),
                 now))
            return _fetchone(conn,
                "SELECT * FROM sober_living_rent_payments WHERE payment_id = %s", (payment_id,))

    def get_rent_ledger(self, stay_id: str) -> Dict:
        charges  = self.list_charges(stay_id)
        payments = self.list_payments(stay_id)
        total_charged = sum(float(c["amount"]) for c in charges if c.get("status") != "void")
        total_paid    = sum(float(p["amount"]) for p in payments)
        return {
            "stay_id":       stay_id,
            "charges":       charges,
            "payments":      payments,
            "total_charged": round(total_charged, 2),
            "total_paid":    round(total_paid, 2),
            "balance":       round(total_charged - total_paid, 2),
        }

    # ------------------------------------------------------------------
    # Meetings
    # ------------------------------------------------------------------

    def list_meetings(self, house_id: str) -> List[Dict]:
        with _db() as conn:
            return _fetchall(conn,
                "SELECT * FROM sober_living_meetings WHERE house_id = %s ORDER BY scheduled_date DESC, scheduled_time DESC",
                (house_id,))

    def create_meeting(self, data: Dict) -> Dict:
        meeting_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_meetings
                (meeting_id, house_id, scheduled_date, scheduled_time, meeting_type,
                 topic, facilitator_name, location, status, attendance_json, notes, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (meeting_id, data["house_id"],
                 data["scheduled_date"],
                 data.get("scheduled_time"),
                 data.get("meeting_type", "house"),
                 data.get("topic"),
                 data.get("facilitator_name"),
                 data.get("location"),
                 data.get("status", "scheduled"),
                 data.get("attendance_json"),
                 data.get("notes"),
                 now, now))
            return _fetchone(conn, "SELECT * FROM sober_living_meetings WHERE meeting_id = %s", (meeting_id,))

    def update_meeting(self, meeting_id: str, data: Dict) -> Optional[Dict]:
        updatable = ["scheduled_date", "scheduled_time", "meeting_type", "topic",
                     "facilitator_name", "location", "status", "attendance_json", "notes"]
        pairs = [f"{f} = %s" for f in updatable if f in data]
        vals  = [data[f] for f in updatable if f in data]
        if not pairs:
            with _db() as conn:
                return _fetchone(conn, "SELECT * FROM sober_living_meetings WHERE meeting_id = %s", (meeting_id,))
        with _db() as conn:
            _exec(conn,
                f"UPDATE sober_living_meetings SET {', '.join(pairs)}, updated_at = %s WHERE meeting_id = %s",
                vals + [_now(), meeting_id])
            return _fetchone(conn, "SELECT * FROM sober_living_meetings WHERE meeting_id = %s", (meeting_id,))

    # ------------------------------------------------------------------
    # Chores
    # ------------------------------------------------------------------

    def list_chores(self, house_id: str, due_date: Optional[str] = None) -> List[Dict]:
        with _db() as conn:
            if due_date:
                return _fetchall(conn,
                    "SELECT c.*, r.first_name, r.last_name FROM sober_living_chores c "
                    "LEFT JOIN sober_living_residents r ON r.resident_id = c.resident_id "
                    "WHERE c.house_id = %s AND c.due_date = %s ORDER BY c.completed, c.chore_name",
                    (house_id, due_date))
            return _fetchall(conn,
                "SELECT c.*, r.first_name, r.last_name FROM sober_living_chores c "
                "LEFT JOIN sober_living_residents r ON r.resident_id = c.resident_id "
                "WHERE c.house_id = %s ORDER BY c.due_date DESC, c.completed, c.chore_name",
                (house_id,))

    def create_chore(self, data: Dict) -> Dict:
        chore_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_chores
                (chore_id, house_id, resident_id, stay_id, chore_name, location,
                 due_date, recurrence, assigned_by, completed, notes, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (chore_id, data["house_id"],
                 data.get("resident_id"),
                 data.get("stay_id"),
                 data["chore_name"],
                 data.get("location"),
                 data["due_date"],
                 data.get("recurrence", "once"),
                 data.get("assigned_by"),
                 0,
                 data.get("notes"),
                 now, now))
            return _fetchone(conn, "SELECT * FROM sober_living_chores WHERE chore_id = %s", (chore_id,))

    def update_chore(self, chore_id: str, data: Dict) -> Optional[Dict]:
        updatable = ["resident_id", "stay_id", "chore_name", "location", "due_date",
                     "recurrence", "assigned_by", "completed", "completed_at", "verified_by", "notes"]
        pairs = [f"{f} = %s" for f in updatable if f in data]
        vals  = [data[f] for f in updatable if f in data]
        if not pairs:
            with _db() as conn:
                return _fetchone(conn, "SELECT * FROM sober_living_chores WHERE chore_id = %s", (chore_id,))
        with _db() as conn:
            _exec(conn,
                f"UPDATE sober_living_chores SET {', '.join(pairs)}, updated_at = %s WHERE chore_id = %s",
                vals + [_now(), chore_id])
            return _fetchone(conn, "SELECT * FROM sober_living_chores WHERE chore_id = %s", (chore_id,))

    # ------------------------------------------------------------------
    # Passes
    # ------------------------------------------------------------------

    def list_passes(self, house_id: str) -> List[Dict]:
        with _db() as conn:
            return _fetchall(conn,
                "SELECT p.*, r.first_name, r.last_name FROM sober_living_passes p "
                "JOIN sober_living_residents r ON r.resident_id = p.resident_id "
                "WHERE p.house_id = %s ORDER BY p.leave_date DESC",
                (house_id,))

    def create_pass(self, data: Dict) -> Dict:
        pass_id = str(uuid.uuid4())
        now = _now()
        with _db() as conn:
            _exec(conn, """
                INSERT INTO sober_living_passes
                (pass_id, house_id, resident_id, stay_id, pass_type, destination,
                 leave_date, leave_time, expected_return_date, expected_return_time,
                 approved_by, status, is_blackout, notes, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (pass_id, data["house_id"], data["resident_id"], data["stay_id"],
                 data.get("pass_type", "day"),
                 data.get("destination"),
                 data["leave_date"],
                 data.get("leave_time"),
                 data["expected_return_date"],
                 data.get("expected_return_time"),
                 data.get("approved_by"),
                 data.get("status", "approved"),
                 int(data.get("is_blackout", 0)),
                 data.get("notes"),
                 now, now))
            return _fetchone(conn, "SELECT * FROM sober_living_passes WHERE pass_id = %s", (pass_id,))

    def update_pass(self, pass_id: str, data: Dict) -> Optional[Dict]:
        updatable = ["pass_type", "destination", "leave_date", "leave_time",
                     "expected_return_date", "expected_return_time",
                     "actual_return_date", "actual_return_time",
                     "approved_by", "status", "is_blackout", "notes"]
        pairs = [f"{f} = %s" for f in updatable if f in data]
        vals  = [data[f] for f in updatable if f in data]
        if not pairs:
            with _db() as conn:
                return _fetchone(conn, "SELECT * FROM sober_living_passes WHERE pass_id = %s", (pass_id,))
        with _db() as conn:
            _exec(conn,
                f"UPDATE sober_living_passes SET {', '.join(pairs)}, updated_at = %s WHERE pass_id = %s",
                vals + [_now(), pass_id])
            return _fetchone(conn, "SELECT * FROM sober_living_passes WHERE pass_id = %s", (pass_id,))

    # ------------------------------------------------------------------
    # Curfew checks
    # ------------------------------------------------------------------

    def list_curfew_checks(self, house_id: str, check_date: str) -> List[Dict]:
        with _db() as conn:
            return _fetchall(conn,
                "SELECT cc.*, r.first_name, r.last_name FROM sober_living_curfew_checks cc "
                "JOIN sober_living_residents r ON r.resident_id = cc.resident_id "
                "WHERE cc.house_id = %s AND cc.check_date = %s ORDER BY r.last_name, r.first_name",
                (house_id, check_date))

    def upsert_curfew_check(self, house_id: str, check_date: str, resident_id: str,
                             stay_id: str, status: str,
                             checked_by: Optional[str] = None,
                             method: Optional[str] = None,
                             notes: Optional[str] = None) -> Dict:
        now = _now()
        with _db() as conn:
            existing = _fetchone(conn,
                "SELECT check_id FROM sober_living_curfew_checks "
                "WHERE house_id = %s AND check_date = %s AND resident_id = %s",
                (house_id, check_date, resident_id))
            if existing:
                _exec(conn,
                    "UPDATE sober_living_curfew_checks "
                    "SET status = %s, checked_at = %s, checked_by = %s, method = %s, notes = %s, updated_at = %s "
                    "WHERE check_id = %s",
                    (status, now if status != "pending" else None,
                     checked_by, method, notes, now, existing["check_id"]))
                return _fetchone(conn,
                    "SELECT * FROM sober_living_curfew_checks WHERE check_id = %s", (existing["check_id"],))
            else:
                check_id = str(uuid.uuid4())
                _exec(conn, """
                    INSERT INTO sober_living_curfew_checks
                    (check_id, house_id, check_date, resident_id, stay_id, status,
                     checked_at, checked_by, method, notes, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (check_id, house_id, check_date, resident_id, stay_id, status,
                     now if status != "pending" else None,
                     checked_by, method, notes, now, now))
                return _fetchone(conn,
                    "SELECT * FROM sober_living_curfew_checks WHERE check_id = %s", (check_id,))

    def get_dashboard(self, house_id: str) -> Dict:
        today = _today()
        with _db() as conn:
            # Tonight's curfew checks
            curfew = _fetchall(conn,
                "SELECT cc.*, r.first_name, r.last_name FROM sober_living_curfew_checks cc "
                "JOIN sober_living_residents r ON r.resident_id = cc.resident_id "
                "WHERE cc.house_id = %s AND cc.check_date = %s ORDER BY r.last_name",
                (house_id, today))

            # Active passes — on leave right now or overdue
            active_passes = _fetchall(conn,
                "SELECT p.*, r.first_name, r.last_name FROM sober_living_passes p "
                "JOIN sober_living_residents r ON r.resident_id = p.resident_id "
                "WHERE p.house_id = %s AND p.status = 'approved' "
                "AND p.actual_return_date IS NULL AND p.leave_date <= %s "
                "ORDER BY p.expected_return_date",
                (house_id, today))

            # Open incidents needing follow-up
            open_incidents = _fetchall(conn,
                "SELECT * FROM sober_living_incidents "
                "WHERE house_id = %s AND follow_up_required = 1 AND incident_resolved = 0 "
                "ORDER BY follow_up_due_date",
                (house_id,))

            # Today's chores
            todays_chores = _fetchall(conn,
                "SELECT c.*, r.first_name, r.last_name FROM sober_living_chores c "
                "LEFT JOIN sober_living_residents r ON r.resident_id = c.resident_id "
                "WHERE c.house_id = %s AND c.due_date = %s ORDER BY c.completed, c.chore_name",
                (house_id, today))

            # Upcoming meetings (next 7 days)
            upcoming_meetings = _fetchall(conn,
                "SELECT * FROM sober_living_meetings "
                "WHERE house_id = %s AND scheduled_date >= %s AND status = 'scheduled' "
                "ORDER BY scheduled_date, scheduled_time LIMIT 5",
                (house_id, today))

            # Residents currently on blackout
            on_blackout = _fetchall(conn,
                "SELECT p.*, r.first_name, r.last_name FROM sober_living_passes p "
                "JOIN sober_living_residents r ON r.resident_id = p.resident_id "
                "WHERE p.house_id = %s AND p.is_blackout = 1 "
                "AND p.actual_return_date IS NULL AND p.leave_date <= %s "
                "ORDER BY r.last_name",
                (house_id, today))

        return {
            "today":            today,
            "curfew_checks":    curfew,
            "active_passes":    active_passes,
            "open_incidents":   open_incidents,
            "todays_chores":    todays_chores,
            "upcoming_meetings":upcoming_meetings,
            "on_blackout":      on_blackout,
        }

    def get_house_rent_summary(self, house_id: str) -> Dict:
        with _db() as conn:
            residents = _fetchall(conn, """
                SELECT res.resident_id, res.first_name, res.last_name,
                       s.stay_id, s.move_in_date
                FROM sober_living_stays s
                JOIN sober_living_residents res ON res.resident_id = s.resident_id
                WHERE s.house_id = %s AND s.resident_status = 'active'
                ORDER BY res.last_name""", (house_id,))
            for r in residents:
                paid = _fetchone(conn,
                    "SELECT COALESCE(SUM(amount), 0) as total FROM sober_living_rent_payments WHERE stay_id = %s",
                    (r["stay_id"],))
                r["total_paid"] = round(float(paid["total"]), 2) if paid else 0.0
                charged = _fetchone(conn,
                    "SELECT COALESCE(SUM(amount), 0) as total FROM sober_living_rent_charges WHERE stay_id = %s AND status != 'void'",
                    (r["stay_id"],))
                r["total_charged"] = round(float(charged["total"]), 2) if charged else 0.0
        return {"house_id": house_id, "residents": residents}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_store_instance: Optional[SoberLivingStore] = None


def get_store() -> SoberLivingStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = SoberLivingStore()
    return _store_instance
