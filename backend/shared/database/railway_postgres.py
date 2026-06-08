"""
Railway Postgres bridge for phased migration from SQLite.
"""

from __future__ import annotations

import os
import json
from typing import Any, Dict, Tuple

from sqlalchemy import create_engine, text


def _database_url() -> str:
    return os.getenv("DATABASE_URL", "").strip()


def is_postgres_configured() -> bool:
    url = _database_url()
    return url.startswith("postgresql://") or url.startswith("postgres://")


def _normalized_postgres_url() -> str:
    url = _database_url()
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def _engine():
    return create_engine(_normalized_postgres_url(), pool_pre_ping=True, future=True)


def check_postgres_health() -> Tuple[bool, str]:
    if not is_postgres_configured():
        return False, "DATABASE_URL is not PostgreSQL"
    try:
        engine = _engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "connected"
    except Exception as exc:
        return False, str(exc)


def ensure_postgres_client_tables() -> None:
    if not is_postgres_configured():
        return
    engine = _engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_core_clients (
                    client_id TEXT PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    email TEXT,
                    phone TEXT,
                    date_of_birth TEXT,
                    address TEXT,
                    city TEXT,
                    state TEXT,
                    zip_code TEXT,
                    emergency_contact_name TEXT,
                    emergency_contact_phone TEXT,
                    emergency_contact_relationship TEXT,
                    case_manager_id TEXT,
                    risk_level TEXT,
                    case_status TEXT,
                    intake_date TEXT,
                    admission_date TEXT,
                    housing_status TEXT,
                    employment_status TEXT,
                    benefits_status TEXT,
                    legal_status TEXT,
                    program_type TEXT,
                    referral_source TEXT,
                    prior_convictions TEXT,
                    substance_abuse_history TEXT,
                    mental_health_status TEXT,
                    transportation TEXT,
                    medical_conditions TEXT,
                    special_needs TEXT,
                    goals TEXT,
                    barriers TEXT,
                    notes TEXT,
                    progress INTEGER,
                    last_contact TEXT,
                    next_followup TEXT,
                    needs_json TEXT,
                    background_json TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    source TEXT DEFAULT 'api.clients',
                    metadata_json TEXT DEFAULT '{}'
                )
                """
            )
        )
        # Backward-compatible column adds for existing tables.
        conn.execute(
            text("ALTER TABLE railway_core_clients ADD COLUMN IF NOT EXISTS case_status TEXT")
        )
        conn.execute(
            text("ALTER TABLE railway_core_clients ADD COLUMN IF NOT EXISTS updated_at TEXT")
        )
        for column_sql in [
            "date_of_birth TEXT",
            "address TEXT",
            "city TEXT",
            "state TEXT",
            "zip_code TEXT",
            "emergency_contact_name TEXT",
            "emergency_contact_phone TEXT",
            "emergency_contact_relationship TEXT",
            "admission_date TEXT",
            "housing_status TEXT",
            "employment_status TEXT",
            "benefits_status TEXT",
            "legal_status TEXT",
            "program_type TEXT",
            "referral_source TEXT",
            "prior_convictions TEXT",
            "substance_abuse_history TEXT",
            "mental_health_status TEXT",
            "transportation TEXT",
            "medical_conditions TEXT",
            "special_needs TEXT",
            "goals TEXT",
            "barriers TEXT",
            "notes TEXT",
            "progress INTEGER",
            "last_contact TEXT",
            "next_followup TEXT",
            "needs_json TEXT",
            "background_json TEXT",
        ]:
            conn.execute(
                text(f"ALTER TABLE railway_core_clients ADD COLUMN IF NOT EXISTS {column_sql}")
            )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS railway_client_sync_events (
                    event_id BIGSERIAL PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    sync_status TEXT NOT NULL,
                    integration_json TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )


def upsert_client_to_postgres(
    client_data: Dict[str, Any],
    integration_results: Dict[str, Any],
) -> str:
    """
    Mirror core client writes to Railway Postgres during migration.
    Returns one of: success, skipped, error:<reason>
    """
    if not is_postgres_configured():
        return "skipped"

    try:
        ensure_postgres_client_tables()
        engine = _engine()
        needs_value = client_data.get("needs")
        background_value = client_data.get("background")
        if isinstance(needs_value, str):
            needs_json = needs_value
        else:
            needs_json = json.dumps(needs_value or [])
        if isinstance(background_value, str):
            background_json = background_value
        else:
            background_json = json.dumps(background_value or {})
        metadata_json = json.dumps(
            {
                "source": "api.clients",
                "integration_results": integration_results,
                "intake_context": client_data,
            },
            default=str,
        )
        integration_json = json.dumps(integration_results, default=str)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO railway_core_clients (
                        client_id, first_name, last_name, email, phone,
                        date_of_birth, address, city, state, zip_code,
                        emergency_contact_name, emergency_contact_phone, emergency_contact_relationship,
                        case_manager_id, risk_level, case_status, intake_date, admission_date,
                        housing_status, employment_status, benefits_status, legal_status,
                        program_type, referral_source, prior_convictions, substance_abuse_history,
                        mental_health_status, transportation, medical_conditions, special_needs,
                        goals, barriers, notes, progress, last_contact, next_followup,
                        needs_json, background_json, created_at, updated_at,
                        metadata_json
                    )
                    VALUES (
                        :client_id, :first_name, :last_name, :email, :phone,
                        :date_of_birth, :address, :city, :state, :zip_code,
                        :emergency_contact_name, :emergency_contact_phone, :emergency_contact_relationship,
                        :case_manager_id, :risk_level, :case_status, :intake_date, :admission_date,
                        :housing_status, :employment_status, :benefits_status, :legal_status,
                        :program_type, :referral_source, :prior_convictions, :substance_abuse_history,
                        :mental_health_status, :transportation, :medical_conditions, :special_needs,
                        :goals, :barriers, :notes, :progress, :last_contact, :next_followup,
                        :needs_json, :background_json, :created_at, :updated_at,
                        :metadata_json
                    )
                    ON CONFLICT (client_id) DO UPDATE SET
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        email = EXCLUDED.email,
                        phone = EXCLUDED.phone,
                        date_of_birth = EXCLUDED.date_of_birth,
                        address = EXCLUDED.address,
                        city = EXCLUDED.city,
                        state = EXCLUDED.state,
                        zip_code = EXCLUDED.zip_code,
                        emergency_contact_name = EXCLUDED.emergency_contact_name,
                        emergency_contact_phone = EXCLUDED.emergency_contact_phone,
                        emergency_contact_relationship = EXCLUDED.emergency_contact_relationship,
                        case_manager_id = EXCLUDED.case_manager_id,
                        risk_level = EXCLUDED.risk_level,
                        case_status = EXCLUDED.case_status,
                        intake_date = EXCLUDED.intake_date,
                        admission_date = EXCLUDED.admission_date,
                        housing_status = EXCLUDED.housing_status,
                        employment_status = EXCLUDED.employment_status,
                        benefits_status = EXCLUDED.benefits_status,
                        legal_status = EXCLUDED.legal_status,
                        program_type = EXCLUDED.program_type,
                        referral_source = EXCLUDED.referral_source,
                        prior_convictions = EXCLUDED.prior_convictions,
                        substance_abuse_history = EXCLUDED.substance_abuse_history,
                        mental_health_status = EXCLUDED.mental_health_status,
                        transportation = EXCLUDED.transportation,
                        medical_conditions = EXCLUDED.medical_conditions,
                        special_needs = EXCLUDED.special_needs,
                        goals = EXCLUDED.goals,
                        barriers = EXCLUDED.barriers,
                        notes = EXCLUDED.notes,
                        progress = EXCLUDED.progress,
                        last_contact = EXCLUDED.last_contact,
                        next_followup = EXCLUDED.next_followup,
                        needs_json = EXCLUDED.needs_json,
                        background_json = EXCLUDED.background_json,
                        created_at = EXCLUDED.created_at,
                        updated_at = EXCLUDED.updated_at,
                        metadata_json = EXCLUDED.metadata_json
                    """
                ),
                {
                    "client_id": client_data.get("client_id"),
                    "first_name": client_data.get("first_name"),
                    "last_name": client_data.get("last_name"),
                    "email": client_data.get("email"),
                    "phone": client_data.get("phone"),
                    "date_of_birth": client_data.get("date_of_birth"),
                    "address": client_data.get("address"),
                    "city": client_data.get("city"),
                    "state": client_data.get("state"),
                    "zip_code": client_data.get("zip_code"),
                    "emergency_contact_name": client_data.get("emergency_contact_name"),
                    "emergency_contact_phone": client_data.get("emergency_contact_phone"),
                    "emergency_contact_relationship": client_data.get("emergency_contact_relationship"),
                    "case_manager_id": client_data.get("case_manager_id"),
                    "risk_level": client_data.get("risk_level"),
                    "case_status": client_data.get("case_status"),
                    "intake_date": client_data.get("intake_date"),
                    "admission_date": client_data.get("admission_date") or client_data.get("intake_date"),
                    "housing_status": client_data.get("housing_status"),
                    "employment_status": client_data.get("employment_status"),
                    "benefits_status": client_data.get("benefits_status"),
                    "legal_status": client_data.get("legal_status"),
                    "program_type": client_data.get("program_type"),
                    "referral_source": client_data.get("referral_source"),
                    "prior_convictions": client_data.get("prior_convictions"),
                    "substance_abuse_history": client_data.get("substance_abuse_history"),
                    "mental_health_status": client_data.get("mental_health_status"),
                    "transportation": client_data.get("transportation"),
                    "medical_conditions": client_data.get("medical_conditions"),
                    "special_needs": client_data.get("special_needs"),
                    "goals": client_data.get("goals"),
                    "barriers": client_data.get("barriers"),
                    "notes": client_data.get("notes"),
                    "progress": client_data.get("progress"),
                    "last_contact": client_data.get("last_contact"),
                    "next_followup": client_data.get("next_followup"),
                    "needs_json": needs_json,
                    "background_json": background_json,
                    "created_at": client_data.get("created_at"),
                    "updated_at": client_data.get("updated_at"),
                    "metadata_json": metadata_json,
                },
            )
            conn.execute(
                text(
                    """
                    INSERT INTO railway_client_sync_events (
                        client_id, sync_status, integration_json
                    )
                    VALUES (:client_id, :sync_status, :integration_json)
                    """
                ),
                {
                    "client_id": client_data.get("client_id"),
                    "sync_status": "success",
                    "integration_json": integration_json,
                },
            )
        return "success"
    except Exception as exc:
        return f"error:{exc}"
