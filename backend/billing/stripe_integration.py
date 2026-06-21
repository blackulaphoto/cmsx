"""Stripe API calls — invoked ONLY when the relevant flag is enabled.

Everything here lazy-imports the ``stripe`` SDK inside the function body, so:
  * importing this module has no side effects and needs no Stripe dependency;
  * in dormant mode (the production default) these functions are never called,
    because the routes short-circuit on the activation flags first.

The line-item math mirrors the internal plan model: base seat price + extra
seat price * (active_users - included_users). These functions raise
HTTPException(503) if the SDK is missing or Stripe is not configured, so a
misconfiguration can never silently fall through to an unguarded call.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import HTTPException

from backend.billing import plans as billing_plans
from backend.billing import stripe_config

logger = logging.getLogger(__name__)


def _load_stripe():
    """Lazy-import + configure the Stripe SDK. Raises 503 if unavailable.

    Never called in dormant mode. Reads the secret key only here, at call time,
    and never returns or logs it."""
    import os

    try:
        import stripe  # noqa: PLC0415 — intentional lazy import
    except Exception as exc:  # noqa: BLE001
        logger.error("Stripe SDK not installed but a Stripe call was attempted")
        raise HTTPException(status_code=503, detail="Stripe is not available") from exc

    secret = (os.getenv(stripe_config.STRIPE_SECRET_KEY_ENV) or "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    stripe.api_key = secret
    return stripe


def build_line_items(plan_code: str, active_users: int) -> List[Dict[str, Any]]:
    """Subscription line items for a plan + seat count, using configured price
    IDs. Validates the plan is self-serve and all needed prices are present."""
    plan = billing_plans.get_plan(plan_code)
    code = plan["plan_code"]
    if not plan["selectable"]:
        # free_trial / enterprise are not self-serve checkout plans.
        raise HTTPException(status_code=400, detail="Plan is not available for checkout")

    mapping = stripe_config.PLAN_PRICE_ENV.get(code)
    if not mapping:
        raise HTTPException(status_code=400, detail="Plan is not available for checkout")

    base_price = stripe_config.price_id(mapping["base"])
    if not base_price:
        raise HTTPException(status_code=503, detail="Stripe price is not configured")

    items: List[Dict[str, Any]] = [{"price": base_price, "quantity": 1}]

    included = plan["included_users"] or 0
    seats = max(0, int(active_users or 0))
    extra_seats = max(0, seats - included)
    if extra_seats and mapping["extra"]:
        extra_price = stripe_config.price_id(mapping["extra"])
        if not extra_price:
            raise HTTPException(status_code=503, detail="Stripe price is not configured")
        items.append({"price": extra_price, "quantity": extra_seats})

    return items


def create_subscription_checkout(
    *,
    plan_code: str,
    active_users: int,
    customer_email: str,
    success_url: str,
    cancel_url: str,
    client_reference_id: str,
) -> Dict[str, Any]:
    """Create a subscription-mode Checkout Session. Caller MUST have verified
    ``stripe_config.checkout_effective_enabled()`` first — this never checks the
    flags itself, so it is the explicit Stripe boundary."""
    stripe = _load_stripe()
    line_items = build_line_items(plan_code, active_users)
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=line_items,
        customer_email=customer_email or None,
        client_reference_id=client_reference_id,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return {"id": session["id"], "url": session["url"]}


def create_billing_portal(*, customer_id: str, return_url: str) -> Dict[str, Any]:
    """Create a Customer Portal session. Caller MUST have verified
    ``stripe_config.portal_effective_enabled()`` first."""
    if not customer_id:
        raise HTTPException(status_code=409, detail="No Stripe customer on file")
    stripe = _load_stripe()
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return {"url": session["url"]}
