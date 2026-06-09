from __future__ import annotations

from backend.shared.database.railway_ur_postgres import is_ur_database_configured

from .postgres_store import PostgresURStore
from .store import URStore


def get_ur_store():
    if is_ur_database_configured():
        return PostgresURStore()
    return URStore()
