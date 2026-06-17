from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from .service import AuthenticatedUser

from backend.shared.db_path import DB_DIR
from backend.shared.tenancy import multi_tenant_enabled, resolve_org_id
CORE_CLIENTS_DB = DB_DIR / "core_clients.db"


def _connect_core_clients() -> sqlite3.Connection:
    conn = sqlite3.connect(CORE_CLIENTS_DB)
    conn.row_factory = sqlite3.Row
    return conn


def get_client_case_manager_id(client_id: str) -> Optional[str]:
    with _connect_core_clients() as conn:
        row = conn.execute(
            "SELECT case_manager_id FROM clients WHERE client_id = ?",
            (client_id,),
        ).fetchone()
    return (row["case_manager_id"] or "").strip() if row else None


def get_client_org_id(client_id: str) -> Optional[str]:
    """Return the client's org_id, or None if absent.

    Defensive against the column not yet existing (e.g. before the Phase 1
    schema migration has run): treats a missing column as "no org", which the
    caller fails closed on when multi-tenancy is enabled.
    """
    try:
        with _connect_core_clients() as conn:
            row = conn.execute(
                "SELECT org_id FROM clients WHERE client_id = ?",
                (client_id,),
            ).fetchone()
    except sqlite3.OperationalError:
        return None
    if not row:
        return None
    return (row["org_id"] or "").strip() or None


def assert_client_access(user: AuthenticatedUser, client_id: str) -> str:
    case_manager_id = get_client_case_manager_id(client_id)
    if not case_manager_id:
        raise HTTPException(status_code=404, detail="Client not found")

    # Org isolation (Phase 1). Only enforced when multi-tenancy is enabled, so
    # single-agency behavior is unchanged while MULTI_TENANT_ENABLED is false.
    # Fails closed: a missing client org or a cross-org mismatch returns 404
    # (not 403) to avoid disclosing that another org's client exists.
    if multi_tenant_enabled():
        client_org_id = get_client_org_id(client_id)
        if not client_org_id or client_org_id != resolve_org_id(user):
            raise HTTPException(status_code=404, detail="Client not found")

    if user.is_admin:
        return case_manager_id
    if case_manager_id != user.case_manager_id:
        raise HTTPException(status_code=403, detail="Access denied to this client")
    return case_manager_id


def effective_case_manager_id(user: AuthenticatedUser, requested_case_manager_id: Optional[str] = None) -> Optional[str]:
    if user.is_admin:
        return requested_case_manager_id.strip() if requested_case_manager_id else None
    return user.case_manager_id
