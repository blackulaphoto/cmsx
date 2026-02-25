"""
Railway Postgres bridge for phased migration from SQLite.
"""

from __future__ import annotations

import os
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
                    case_manager_id TEXT,
                    risk_level TEXT,
                    intake_date TEXT,
                    created_at TEXT,
                    source TEXT DEFAULT 'api.clients',
                    metadata_json TEXT DEFAULT '{}'
                )
                """
            )
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
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO railway_core_clients (
                        client_id, first_name, last_name, email, phone,
                        case_manager_id, risk_level, intake_date, created_at,
                        metadata_json
                    )
                    VALUES (
                        :client_id, :first_name, :last_name, :email, :phone,
                        :case_manager_id, :risk_level, :intake_date, :created_at,
                        :metadata_json
                    )
                    ON CONFLICT (client_id) DO UPDATE SET
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        email = EXCLUDED.email,
                        phone = EXCLUDED.phone,
                        case_manager_id = EXCLUDED.case_manager_id,
                        risk_level = EXCLUDED.risk_level,
                        intake_date = EXCLUDED.intake_date,
                        created_at = EXCLUDED.created_at,
                        metadata_json = EXCLUDED.metadata_json
                    """
                ),
                {
                    "client_id": client_data.get("client_id"),
                    "first_name": client_data.get("first_name"),
                    "last_name": client_data.get("last_name"),
                    "email": client_data.get("email"),
                    "phone": client_data.get("phone"),
                    "case_manager_id": client_data.get("case_manager_id"),
                    "risk_level": client_data.get("risk_level"),
                    "intake_date": client_data.get("intake_date"),
                    "created_at": client_data.get("created_at"),
                    "metadata_json": str(
                        {
                            "source": "api.clients",
                            "integration_results": integration_results,
                        }
                    ),
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
                    "integration_json": str(integration_results),
                },
            )
        return "success"
    except Exception as exc:
        return f"error:{exc}"
