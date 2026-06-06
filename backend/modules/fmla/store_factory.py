from __future__ import annotations

from backend.shared.database.railway_postgres import is_postgres_configured

from .postgres_store import PostgresFMLAStore
from .store import FMLAStore


def get_fmla_store():
    if is_postgres_configured():
        return PostgresFMLAStore()
    return FMLAStore()

