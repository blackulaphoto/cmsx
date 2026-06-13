"""
Railway Postgres bridge for Admissions persistence.
"""
from __future__ import annotations

from sqlalchemy import create_engine, text

from .railway_postgres import _normalized_postgres_url, is_postgres_configured


def _engine():
    return create_engine(_normalized_postgres_url(), pool_pre_ping=True, future=True)


def ensure_postgres_admissions_tables() -> None:
    if not is_postgres_configured():
        return

    engine = _engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_admission_packets (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    client_name TEXT NOT NULL,
                    case_manager_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'In Progress',
                    progress_percent INTEGER NOT NULL DEFAULT 0,
                    shared_profile_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_rw_adm_packets_client "
                "ON railway_admission_packets(client_id)"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE railway_admission_packets "
                "ADD COLUMN IF NOT EXISTS shared_profile_json TEXT NOT NULL DEFAULT '{}'"
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_admission_packet_forms (
                    id TEXT PRIMARY KEY,
                    packet_id TEXT NOT NULL
                        REFERENCES railway_admission_packets(id) ON DELETE CASCADE,
                    form_key TEXT NOT NULL,
                    form_name TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Not Started',
                    required INTEGER NOT NULL DEFAULT 1,
                    timing_group TEXT NOT NULL DEFAULT 'admission',
                    timing_label TEXT NOT NULL DEFAULT 'Required at Admission',
                    requires_signature INTEGER NOT NULL DEFAULT 0,
                    signatures_required TEXT NOT NULL DEFAULT '[]',
                    allow_attachments INTEGER NOT NULL DEFAULT 0,
                    allow_revocation INTEGER NOT NULL DEFAULT 0,
                    expires_in_days INTEGER,
                    expires_at TEXT,
                    notes TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    signed_at TEXT,
                    review_status TEXT NOT NULL DEFAULT 'Not Reviewed',
                    review_notes TEXT,
                    reviewed_by TEXT,
                    reviewed_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(packet_id, form_key)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_admission_form_responses (
                    id TEXT PRIMARY KEY,
                    packet_id TEXT NOT NULL
                        REFERENCES railway_admission_packets(id) ON DELETE CASCADE,
                    form_key TEXT NOT NULL,
                    response_data TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(packet_id, form_key)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_admission_form_attachments (
                    id TEXT PRIMARY KEY,
                    packet_id TEXT NOT NULL
                        REFERENCES railway_admission_packets(id) ON DELETE CASCADE,
                    form_key TEXT NOT NULL,
                    client_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_type TEXT NOT NULL DEFAULT '',
                    file_size INTEGER NOT NULL DEFAULT 0,
                    storage_path TEXT NOT NULL,
                    uploaded_by TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_admissions_created_tasks (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    task_key TEXT NOT NULL,
                    reminder_id TEXT,
                    case_manager_id TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(client_id, task_key)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_admissions_financial_coordination (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    packet_id TEXT NOT NULL DEFAULT '',
                    case_manager_id TEXT NOT NULL DEFAULT '',
                    billing_explained_status TEXT NOT NULL DEFAULT 'Not Started',
                    billing_explained_date TEXT,
                    billing_notes TEXT,
                    insurance_verification_status TEXT NOT NULL DEFAULT 'Not Started',
                    primary_payer_type TEXT,
                    primary_plan_name TEXT,
                    primary_member_id TEXT,
                    verification_date TEXT,
                    verification_rep_name TEXT,
                    verification_reference_number TEXT,
                    deductible TEXT,
                    copay TEXT,
                    coinsurance TEXT,
                    out_of_pocket_max TEXT,
                    auth_required TEXT NOT NULL DEFAULT 'Unknown',
                    cob_status TEXT NOT NULL DEFAULT 'Not Needed',
                    cob_issue_identified INTEGER NOT NULL DEFAULT 0,
                    cob_notes TEXT,
                    cob_followup_needed INTEGER NOT NULL DEFAULT 0,
                    payment_plan_status TEXT NOT NULL DEFAULT 'Not Needed',
                    payment_arrangement_type TEXT,
                    payment_amount TEXT,
                    payment_due_date TEXT,
                    payment_notes TEXT,
                    std_needed TEXT NOT NULL DEFAULT 'Unknown',
                    std_status TEXT NOT NULL DEFAULT 'Not Started',
                    std_notes TEXT,
                    fmla_needed TEXT NOT NULL DEFAULT 'Unknown',
                    linked_fmla_case_id TEXT,
                    discharge_planning_started INTEGER NOT NULL DEFAULT 0,
                    discharge_destination TEXT,
                    sober_living_needed INTEGER NOT NULL DEFAULT 0,
                    pcp_dental_psych_needed INTEGER NOT NULL DEFAULT 0,
                    legal_probation_followup_needed INTEGER NOT NULL DEFAULT 0,
                    benefits_followup_needed INTEGER NOT NULL DEFAULT 0,
                    employment_resume_needed INTEGER NOT NULL DEFAULT 0,
                    transportation_plan TEXT,
                    discharge_notes TEXT,
                    last_updated_by TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(client_id)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_admissions_task_suppressions (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    task_key TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'dismissed',
                    reason TEXT,
                    dismissed_by TEXT,
                    dismissed_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(client_id, task_key)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_admissions_financial_coordination_events (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    packet_id TEXT NOT NULL DEFAULT '',
                    event_type TEXT NOT NULL DEFAULT 'update',
                    changed_by TEXT NOT NULL DEFAULT '',
                    changed_fields_json TEXT NOT NULL DEFAULT '[]',
                    previous_values_json TEXT,
                    new_values_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
        )
        # Indexes
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_rw_adm_forms_packet "
                "ON railway_admission_packet_forms(packet_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_rw_adm_responses_packet "
                "ON railway_admission_form_responses(packet_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_rw_adm_attachments_packet "
                "ON railway_admission_form_attachments(packet_id, form_key)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_rw_adm_tasks_client "
                "ON railway_admissions_created_tasks(client_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_rw_adm_suppressions_client "
                "ON railway_admissions_task_suppressions(client_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_rw_adm_fc_client "
                "ON railway_admissions_financial_coordination(client_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_rw_adm_events_client "
                "ON railway_admissions_financial_coordination_events(client_id, created_at DESC)"
            )
        )
