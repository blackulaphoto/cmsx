"""Billing status + DORMANT Stripe endpoints.

``GET /api/billing/status`` returns the authenticated caller's own org billing
state, plan limits, usage counts, trial info, an estimated monthly price, limit
warnings, and a Stripe *readiness* block (booleans only, no secrets). The org is
always derived from the token (``user.org_id``) — a client-supplied org_id is
never trusted. ``GET /api/billing/plans`` exposes the static plan catalog.

Stripe is wired in DORMANT mode: ``POST /checkout-session`` and
``POST /portal-session`` short-circuit to a 503 disabled response (and make NO
Stripe call) unless their activation flags are true; the webhook scaffold never
mutates billing unless webhooks are enabled with a valid secret. Every flag
defaults false, so production stays dormant. No route returns a secret.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import backend.shared.db_path as db_path_mod
from backend.auth.service import auth_service, require_user
from backend.billing import plans as billing_plans
from backend.billing import stripe_config
from backend.billing import stripe_integration

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan_code: str = Field(min_length=1, max_length=40)


class PortalRequest(BaseModel):
    # No fields needed today; present for forward compatibility.
    pass


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
    # Stripe readiness (booleans + mode only — never a secret value).
    return {
        "success": True,
        "org_id": org_id,
        "stripe": stripe_config.readiness(),
        **summary,
    }


@router.get("/plans")
async def list_plans(request: Request):
    """Static plan catalog for the pricing/upgrade UI (authenticated)."""
    require_user(request)
    return {"success": True, "plans": billing_plans.list_plans()}


# ── Stripe checkout (DORMANT) ────────────────────────────────────────────────

@router.post("/checkout-session")
async def create_checkout_session(payload: CheckoutRequest, request: Request):
    """Create a subscription Checkout Session — DISABLED in dormant mode.

    Returns 503 and makes NO Stripe call unless BOTH STRIPE_BILLING_ENABLED and
    STRIPE_CHECKOUT_ENABLED are true. The flag check happens before any Stripe
    code is reached, so production (flags false) never contacts Stripe."""
    user = require_user(request)
    if not stripe_config.checkout_effective_enabled():
        return JSONResponse(
            status_code=503,
            content={"success": False, "enabled": False,
                     "detail": "Stripe checkout is not enabled."},
        )

    # ── Enabled path (not reachable in dormant production) ──────────────────
    org_id = user.org_id
    active_users = auth_service.count_active_staff(org_id)
    base = str(request.base_url).rstrip("/")
    result = stripe_integration.create_subscription_checkout(
        plan_code=payload.plan_code,
        active_users=active_users,
        customer_email=user.email,
        success_url=f"{base}/billing?checkout=success",
        cancel_url=f"{base}/billing?checkout=cancel",
        client_reference_id=org_id,
    )
    logger.info("Stripe checkout session created for org %s", org_id)
    return {"success": True, "enabled": True, "checkout_url": result["url"], "session_id": result["id"]}


# ── Stripe customer portal (DORMANT) ─────────────────────────────────────────

@router.post("/portal-session")
async def create_portal_session(payload: PortalRequest, request: Request):
    """Create a Customer Portal session — DISABLED in dormant mode.

    Returns 503 and makes NO Stripe call unless BOTH STRIPE_BILLING_ENABLED and
    STRIPE_PORTAL_ENABLED are true."""
    user = require_user(request)
    if not stripe_config.portal_effective_enabled():
        return JSONResponse(
            status_code=503,
            content={"success": False, "enabled": False,
                     "detail": "Stripe billing portal is not enabled."},
        )

    # ── Enabled path (not reachable in dormant production) ──────────────────
    org_id = user.org_id
    billing = auth_service.get_org_billing(org_id)
    customer_id = billing.get("stripe_customer_id") or ""
    base = str(request.base_url).rstrip("/")
    result = stripe_integration.create_billing_portal(
        customer_id=customer_id,
        return_url=f"{base}/billing",
    )
    logger.info("Stripe portal session created for org %s", org_id)
    return {"success": True, "enabled": True, "portal_url": result["url"]}


# ── Stripe webhook scaffold (DORMANT — never mutates billing) ─────────────────

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Webhook scaffold. In dormant mode this acknowledges the request WITHOUT
    parsing, verifying, or mutating any billing state. It only processes events
    when STRIPE_WEBHOOKS_ENABLED is true AND a valid STRIPE_WEBHOOK_SECRET is
    configured. No webhook is registered with Stripe yet."""
    if not stripe_config.webhooks_effective_enabled():
        # Do not read the body, verify a signature, or change any state.
        return JSONResponse(
            status_code=200,
            content={"received": True, "processed": False,
                     "detail": "Stripe webhooks are not enabled."},
        )

    # ── Enabled path (not reachable in dormant production) ──────────────────
    # Signature verification + event handling would attach here. Intentionally
    # left unimplemented so no billing mutation can occur until activation.
    logger.info("Stripe webhook received while enabled; no handler wired yet")
    return {"received": True, "processed": False, "detail": "No webhook handler configured."}
