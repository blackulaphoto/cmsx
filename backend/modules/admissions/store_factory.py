from __future__ import annotations

from backend.shared.database.railway_postgres import is_postgres_configured

from .database import AdmissionsStore


def get_admissions_store():
    if is_postgres_configured():
        from .postgres_store import PostgresAdmissionsStore
        return PostgresAdmissionsStore()
    return AdmissionsStore()


admissions_store = get_admissions_store()
