from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException

from .service import AuthenticatedUser

from backend.shared.db_path import DB_DIR
from backend.shared.tenancy import multi_tenant_enabled, resolve_org_id
CORE_CLIENTS_DB = DB_DIR / "core_clients.db"
AUTH_DB = DB_DIR / "auth.db"


def get_org_for_user_id(user_id: str) -> Optional[str]:
    """Resolve a participant/staff user_id to their org_id from user_profiles.

    Messages identify users by ``case_manager_id or firebase_uid`` (see the
    messages module's ``_user_id``), so both columns are checked. Returns None
    when the user cannot be resolved or the column/table is absent (callers fail
    closed on None when multi-tenancy is enabled).
    """
    uid = (user_id or "").strip()
    if not uid:
        return None
    try:
        with sqlite3.connect(AUTH_DB) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT org_id FROM user_profiles WHERE case_manager_id = ? OR firebase_uid = ? LIMIT 1",
                (uid, uid),
            ).fetchone()
    except sqlite3.OperationalError:
        return None
    if not row:
        return None
    return (row["org_id"] or "").strip() or None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 route classification (documentation + test reference).
#
# This is the explicit record of which housing/jobs/resume endpoints handle
# tenant/client data (and therefore carry the require_user + assert_client_access
# guard) versus which are global/cross-org-by-design and intentionally exempt.
# Keep this in sync with the actual route decorators; the guard-coverage test
# asserts the guarded set matches reality so the doc cannot silently drift.
# ─────────────────────────────────────────────────────────────────────────────

# Client-data endpoints guarded in Phase 2 (require_user + assert_client_access).
# Listed as "METHOD prefix+path" for readability.
TENANCY_GUARDED_ROUTES = {
    "POST /api/housing/application",
    "GET /api/housing/applications/{client_id}",
    "POST /api/jobs/save",
    "GET /api/jobs/saved/{client_id}",
    "POST /api/resume/profile",
    "GET /api/resume/profile/{client_id}",
    "GET /api/resume/resumes/{client_id}",
    "GET /api/resume/list/{client_id}",
    "POST /api/resume/create",
    "POST /api/resume/apply-job",
    "GET /api/resume/applications/{client_id}",
}

# Mixed routes: global search/reference UNLESS a client_id is supplied, in which
# case the client-specific branch is guarded with assert_client_access.
TENANCY_MIXED_ROUTES = {
    "GET /api/housing/case-manager-search",
    "POST /api/housing/case-manager-search",
    "GET /api/housing/case-manager-dashboard",
    "POST /api/resume/rewrite-profile",
    "POST /api/resume/import",
}

# Global / cross-org-exempt by design (public search, reference, health, docs).
# Documented as families rather than every path.
TENANCY_CROSS_ORG_EXEMPT = {
    "housing: search/reference/stats (/, /search, /types, /counties, /cities, "
    "/sober-living, /programs, /resource/{id}, /background-friendly, /emergency, /statistics)",
    "jobs: search/status/health (/search*, root, /search/ai, /simple_search, "
    "/health, /scrapers/health, /search/links, /cleanup)",
    "resume: root and /health",
    "services: all routes (client-data lives in the guarded case_management module)",
    "resource_library, sober_living_directory, public provider directories",
    "platform: /api/health, /docs, /openapi.json, /redoc",
}


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


def get_client_ids_for_org(org_id: str) -> List[str]:
    """Return all client_ids belonging to an org (Phase 3D shared helper).

    Used by clinical-domain list/summary endpoints to turn an admin "see all"
    into "all clients in my org" when multi-tenancy is enabled. Defensive:
    returns an empty list for a blank org_id or on any DB/query error, and on a
    missing org_id column (pre-Phase-1 schema), so callers fail closed.
    """
    org = (org_id or "").strip()
    if not org:
        return []
    try:
        with _connect_core_clients() as conn:
            rows = conn.execute(
                "SELECT client_id FROM clients WHERE org_id = ?",
                (org,),
            ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [row["client_id"] for row in rows if row["client_id"]]


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
