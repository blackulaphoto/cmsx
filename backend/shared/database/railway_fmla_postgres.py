"""
Railway Postgres bridge for FMLA persistence.
"""

from __future__ import annotations

from sqlalchemy import create_engine, text

from .railway_postgres import is_postgres_configured, _normalized_postgres_url


def _engine():
    return create_engine(_normalized_postgres_url(), pool_pre_ping=True, future=True)


def ensure_postgres_fmla_tables() -> None:
    if not is_postgres_configured():
        return

    engine = _engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_fmla_cases (
                    case_id TEXT PRIMARY KEY,
                    case_subject_type TEXT NOT NULL DEFAULT 'client',
                    client_id TEXT,
                    client_name TEXT NOT NULL,
                    staff_identifier TEXT,
                    staff_name TEXT,
                    staff_department TEXT,
                    staff_job_title TEXT,
                    date_of_birth TEXT,
                    assigned_case_manager TEXT NOT NULL,
                    treatment_status TEXT,
                    employer_name TEXT,
                    hr_contact_name TEXT,
                    hr_phone TEXT,
                    hr_email TEXT,
                    employer_fax TEXT,
                    employer_address TEXT,
                    preferred_communication_method TEXT,
                    provider_name TEXT,
                    clinic_name TEXT,
                    provider_phone TEXT,
                    provider_fax TEXT,
                    provider_email TEXT,
                    provider_address TEXT,
                    roi_status TEXT,
                    fmla_request_type TEXT NOT NULL,
                    leave_type TEXT NOT NULL DEFAULT 'continuous',
                    leave_start_date TEXT,
                    leave_end_date TEXT,
                    expected_return_date TEXT,
                    employer_response_deadline TEXT,
                    certification_expiration_date TEXT,
                    return_to_work_date TEXT,
                    paperwork_deadline TEXT,
                    paperwork_received_date TEXT,
                    paperwork_completed_date TEXT,
                    paperwork_sent_date TEXT,
                    paperwork_sent_method TEXT,
                    confirmation_received INTEGER NOT NULL DEFAULT 0,
                    approval_status TEXT DEFAULT 'pending',
                    status TEXT DEFAULT 'draft',
                    notes TEXT,
                    internal_comments TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_fmla_documents (
                    document_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES railway_fmla_cases(case_id) ON DELETE CASCADE,
                    batch_id TEXT,
                    batch_name TEXT,
                    document_type TEXT NOT NULL,
                    document_status TEXT NOT NULL,
                    uploader_name TEXT,
                    uploader_case_manager_id TEXT,
                    file_name TEXT,
                    file_path TEXT,
                    file_size BIGINT,
                    content_type TEXT,
                    date_requested TEXT,
                    date_received TEXT,
                    date_completed TEXT,
                    date_sent TEXT,
                    sent_to TEXT,
                    sent_by TEXT,
                    confirmation_number TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_fmla_correspondence (
                    correspondence_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES railway_fmla_cases(case_id) ON DELETE CASCADE,
                    correspondence_at TEXT NOT NULL,
                    contact_type TEXT NOT NULL,
                    person_contacted TEXT,
                    organization TEXT,
                    contact_information TEXT,
                    summary TEXT NOT NULL,
                    outcome TEXT,
                    next_step_needed TEXT,
                    follow_up_date TEXT,
                    staff_member TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_fmla_case_reminders (
                    reminder_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES railway_fmla_cases(case_id) ON DELETE CASCADE,
                    reminder_reason TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_fmla_leave_usage (
                    usage_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES railway_fmla_cases(case_id) ON DELETE CASCADE,
                    usage_date TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    reason_category TEXT NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_fmla_exports (
                    export_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES railway_fmla_cases(case_id) ON DELETE CASCADE,
                    export_type TEXT NOT NULL,
                    draft_title TEXT NOT NULL,
                    draft_content TEXT NOT NULL,
                    review_notes TEXT,
                    warning_text TEXT,
                    safe_filename TEXT,
                    file_path TEXT,
                    content_type TEXT,
                    created_by TEXT,
                    reviewed_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_fmla_audit_log (
                    audit_id TEXT PRIMARY KEY,
                    case_id TEXT REFERENCES railway_fmla_cases(case_id) ON DELETE SET NULL,
                    action TEXT NOT NULL,
                    actor_case_manager_id TEXT NOT NULL,
                    actor_name TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_fmla_cases_status ON railway_fmla_cases(status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_fmla_cases_client ON railway_fmla_cases(client_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_fmla_cases_deadline ON railway_fmla_cases(paperwork_deadline)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_fmla_cases_subject ON railway_fmla_cases(case_subject_type)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_fmla_cases_manager ON railway_fmla_cases(assigned_case_manager)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_fmla_documents_case ON railway_fmla_documents(case_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_fmla_correspondence_case ON railway_fmla_correspondence(case_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_fmla_leave_usage_case ON railway_fmla_leave_usage(case_id, usage_date DESC)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_fmla_exports_case ON railway_fmla_exports(case_id, created_at DESC)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_railway_fmla_audit_case ON railway_fmla_audit_log(case_id, created_at DESC)"))

