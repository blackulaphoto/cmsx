"""Billing status endpoints (Stripe-disabled).

``GET /api/billing/status`` returns the authenticated caller's own org billing
state, plan limits, usage counts, trial info, an estimated monthly price, and
limit warnings. The org is always derived from the token (``user.org_id``) — a
client-supplied org_id is never trusted. ``GET /api/billing/plans`` exposes the
static plan catalog for the pricing UI.

No route here makes a Stripe call, requires a Stripe key, or returns PHI/secrets.
The manual billing setter lives in the super-admin router (super-admin only).
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Optional

from fastapi import APIRouter, Request

import backend.shared.db_path as db_path_mod
from backend.auth.service import auth_service, require_user
from backend.billing import plans as billing_plans

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/billing", tags=["billing"])


def active_client_count(org_id: Optional[str]) -> int:
    """Per-org active client COUNT only (no client rows/PHI). Fails open to 0.

    Mirrors the super-admin client-count helper. ``core_clients.db`` is the
    master clients table; we only ever read a COUNT, never client data.
    """
    try:
        path = db_path_mod.DB_DIR / "core_clients.db"
        with sqlite3.connect(str(path)) as conn:
            if org_id:
                row = conn.execute(
                    "SELECT COUNT(*) FROM clients WHERE org_id = ?", (org_id,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM clients").fetchone()
        return int(row[0]) if row else 0
    except Exception:  # noqa: BLE001 — counts are best-effort metadata
        return 0


@router.get("/status")
async def billing_status(request: Request):
    """Current org's billing status + plan limits + usage. Authenticated users
    read ONLY their own org (org_id comes from the token, not the request)."""
    user = require_user(request)
    org_id = user.org_id
    billing = auth_service.get_org_billing(org_id)
    active_users = auth_service.count_active_staff(org_id)
    active_clients = active_client_count(org_id)
    summary = billing_plans.build_billing_summary(
        billing,
        active_users=active_users,
        active_clients=active_clients,
    )
    return {"success": True, "org_id": org_id, **summary}


@router.get("/plans")
async def list_plans(request: Request):
    """Static plan catalog for the pricing/upgrade UI (authenticated)."""
    require_user(request)
    return {"success": True, "plans": billing_plans.list_plans()}
