from __future__ import annotations

from backend.shared.database.railway_postgres import is_postgres_configured

from .postgres_store import PostgresURStore


def get_ur_store():
    if not is_postgres_configured():
        raise RuntimeError("UR module requires PostgreSQL DATABASE_URL configuration")
    return PostgresURStore()
