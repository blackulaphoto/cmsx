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
from backend.billing import plans as billing_plans
from .service import auth_service, require_super_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/super-admin", tags=["super-admin"])


class SuspendRequest(BaseModel):
    confirm: bool = False


class BillingUpdateRequest(BaseModel):
    """Manual billing override (super-admin only, no Stripe). All fields optional;
    at least one must be present. plan_code/billing_status are validated against
    the internal catalog server-side."""
    plan_code: Optional[str] = None
    billing_status: Optional[str] = None
    trial_ends_at: Optional[str] = None


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
        client_count = client_counts.get(o["org_id"], 0)
        o["client_count"] = client_count
        # Billing visibility: plan_code, billing_status, estimated price, and
        # over-limit warning for each org. No Stripe IDs are surfaced.
        billing = auth_service.get_org_billing(o["org_id"])
        active_users = o.get("active_user_count", 0)
        plan_code = billing["plan_code"]
        o["billing_status"] = billing["billing_status"]
        o["plan_code"] = plan_code
        o["estimated_monthly_price"] = billing_plans.estimate_monthly_price(plan_code, active_users)
        o["limit_status"] = billing_plans.compute_limit_status(
            plan_code, active_users=active_users, active_clients=client_count
        )
    return {"success": True, "organizations": orgs}


@router.get("/organizations/{org_id}")
async def organization_detail(org_id: str, request: Request):
    require_super_admin(request)
    detail = auth_service.get_organization_detail(org_id)
    client_count = _client_count(org_id)
    detail["client_count"] = client_count
    # Full billing view for the detail drawer (plan, status, usage, limits,
    # estimated price). Built from the internal model only — Stripe stays inert.
    billing = auth_service.get_org_billing(org_id)
    active_users = auth_service.count_active_staff(org_id)
    detail["billing"] = billing_plans.build_billing_summary(
        billing, active_users=active_users, active_clients=client_count
    )
    detail["success"] = True
    return detail


@router.post("/organizations/{org_id}/billing")
async def update_org_billing(org_id: str, payload: BillingUpdateRequest, request: Request):
    """Manually set plan_code / billing_status / trial for an org.

    Platform super-admin only — useful for comped/internal accounts and testing.
    No Stripe call is made; only the internal billing columns are updated."""
    admin = require_super_admin(request)
    result = auth_service.set_org_billing(
        org_id,
        plan_code=payload.plan_code,
        billing_status=payload.billing_status,
        trial_ends_at=payload.trial_ends_at,
    )
    logger.info("SUPER-ADMIN %s set billing for org %s", admin.email, org_id)
    return {"success": True, "billing": result}


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
