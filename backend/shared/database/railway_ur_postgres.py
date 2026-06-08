"""
Railway Postgres bridge for Utilization Review persistence.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text

from backend.auth.service import auth_service
from .railway_postgres import _normalized_postgres_url, is_postgres_configured


def _test_database_url() -> str:
    if not auth_service.is_test_auth_enabled():
        return ""
    return os.getenv("UR_TEST_DATABASE_URL", "").strip()


def is_ur_database_configured() -> bool:
    return is_postgres_configured() or bool(_test_database_url())


def _database_url() -> str:
    return _test_database_url() or _normalized_postgres_url()


def _engine():
    return create_engine(_database_url(), pool_pre_ping=True, future=True)


def ensure_postgres_ur_tables(engine=None) -> None:
    if engine is None and not is_ur_database_configured():
        return

    engine = engine or _engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_ur_cases (
                    case_id TEXT PRIMARY KEY,
                    client_id TEXT,
                    client_name TEXT NOT NULL,
                    assigned_case_manager TEXT NOT NULL,
                    payer TEXT NOT NULL,
                    member_id TEXT,
                    policy_group_number TEXT,
                    facility TEXT,
                    program TEXT,
                    current_level_of_care TEXT,
                    requested_level_of_care TEXT,
                    approved_level_of_care TEXT,
                    admit_date TEXT NOT NULL,
                    diagnosis TEXT,
                    asam_level TEXT,
                    auth_required INTEGER NOT NULL DEFAULT 1,
                    auth_number TEXT,
                    requested_days INTEGER NOT NULL DEFAULT 0,
                    approved_days INTEGER NOT NULL DEFAULT 0,
                    denied_days INTEGER NOT NULL DEFAULT 0,
                    approved_start_date TEXT,
                    approved_end_date TEXT,
                    next_review_date TEXT,
                    reviewer_name TEXT,
                    reviewer_company TEXT,
                    reviewer_phone TEXT,
                    reviewer_fax TEXT,
                    reviewer_email TEXT,
                    auth_submission_method TEXT,
                    decision_received_method TEXT,
                    clinical_criteria_used TEXT DEFAULT 'ASAM',
                    clinical_justification_summary TEXT,
                    denial_reason TEXT,
                    peer_review_deadline TEXT,
                    appeal_deadline TEXT,
                    revenue_at_risk_amount REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'auth_needed',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_ur_review_events (
                    event_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES railway_ur_cases(case_id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    event_date TEXT NOT NULL,
                    status TEXT,
                    notes TEXT,
                    requested_days INTEGER NOT NULL DEFAULT 0,
                    approved_days INTEGER NOT NULL DEFAULT 0,
                    denied_days INTEGER NOT NULL DEFAULT 0,
                    approved_start_date TEXT,
                    approved_end_date TEXT,
                    reviewer_name TEXT,
                    reviewer_company TEXT,
                    reviewer_phone TEXT,
                    reviewer_fax TEXT,
                    reviewer_email TEXT,
                    auth_submission_method TEXT,
                    decision_received_method TEXT,
                    denial_reason TEXT,
                    peer_review_deadline TEXT,
                    appeal_deadline TEXT,
                    created_by TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_ur_cases_manager ON railway_ur_cases(assigned_case_manager)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_ur_cases_next_review ON railway_ur_cases(next_review_date)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_ur_cases_approved_end ON railway_ur_cases(approved_end_date)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_ur_cases_appeal_deadline ON railway_ur_cases(appeal_deadline)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_ur_cases_status ON railway_ur_cases(status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_ur_cases_payer ON railway_ur_cases(payer)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_ur_events_case_date ON railway_ur_review_events(case_id, event_date DESC)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_ur_events_type ON railway_ur_review_events(event_type)"))
