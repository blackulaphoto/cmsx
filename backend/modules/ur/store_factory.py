from __future__ import annotations

from backend.shared.database.railway_ur_postgres import is_ur_database_configured

from .postgres_store import PostgresURStore


def get_ur_store():
    if not is_ur_database_configured():
        raise RuntimeError("UR module requires PostgreSQL DATABASE_URL configuration")
    return PostgresURStore()
