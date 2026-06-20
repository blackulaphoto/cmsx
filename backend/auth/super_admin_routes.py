"""Super Admin Panel endpoints — platform owner command center.

Read-mostly view over organizations and users, plus suspend/restore. Every route
is gated by ``require_super_admin`` (email allowlist, server-enforced). Responses
contain only counts/metadata — never PHI/client records, secrets, DB paths, or tokens.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

import backend.shared.db_path as db_path_mod
from backend.shared.tenancy import multi_tenant_enabled
from .service import auth_service, require_super_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/super-admin", tags=["super-admin"])


class SuspendRequest(BaseModel):
    confirm: bool = False


def _client_counts_by_org() -> dict:
    """Per-org client COUNTS only (no client rows/PHI). Fails open to {}."""
    try:
        path = db_path_mod.DB_DIR / "core_clients.db"
        with sqlite3.connect(str(path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT org_id, COUNT(*) c FROM clients GROUP BY org_id"
            ).fetchall()
        return {r["org_id"]: r["c"] for r in rows}
    except Exception:  # noqa: BLE001 — counts are best-effort metadata
        return {}


def _client_count(org_id: Optional[str] = None) -> int:
    try:
        path = db_path_mod.DB_DIR / "core_clients.db"
        with sqlite3.connect(str(path)) as conn:
            if org_id:
                row = conn.execute("SELECT COUNT(*) FROM clients WHERE org_id = ?", (org_id,)).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM clients").fetchone()
        return int(row[0]) if row else 0
    except Exception:  # noqa: BLE001
        return 0


@router.get("/overview")
async def overview(request: Request):
    require_super_admin(request)
    stats = auth_service.platform_overview()
    return {
        "success": True,
        "multi_tenant_enabled": multi_tenant_enabled(),
        "total_orgs": stats["total_orgs"],
        "total_users": stats["total_users"],
        "active_users": stats["active_users"],
        "total_clients": _client_count(),
    }


@router.get("/organizations")
async def list_organizations(request: Request):
    require_super_admin(request)
    orgs = auth_service.list_organizations()
    client_counts = _client_counts_by_org()
    for o in orgs:
        o["client_count"] = client_counts.get(o["org_id"], 0)
    return {"success": True, "organizations": orgs}


@router.get("/organizations/{org_id}")
async def organization_detail(org_id: str, request: Request):
    require_super_admin(request)
    detail = auth_service.get_organization_detail(org_id)
    detail["client_count"] = _client_count(org_id)
    detail["success"] = True
    return detail


@router.get("/users")
async def search_users(request: Request, q: str = ""):
    require_super_admin(request)
    return {"success": True, "users": auth_service.search_users(q)}


@router.post("/organizations/{org_id}/suspend")
async def suspend_org(org_id: str, payload: SuspendRequest, request: Request):
    admin = require_super_admin(request)
    result = auth_service.set_org_status(org_id, "suspended", confirm=payload.confirm)
    logger.info("SUPER-ADMIN %s suspended org %s", admin.email, org_id)
    return {"success": True, **result}


@router.post("/organizations/{org_id}/restore")
async def restore_org(org_id: str, request: Request):
    admin = require_super_admin(request)
    result = auth_service.set_org_status(org_id, "active")
    logger.info("SUPER-ADMIN %s restored org %s", admin.email, org_id)
    return {"success": True, **result}
