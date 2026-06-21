"""Stripe DORMANT-mode configuration (env-only; no Stripe SDK import here).

This module reads Stripe-related environment variables and reports *readiness*
without ever exposing a secret value and without making any Stripe API call. It
is the single source of truth for whether billing/checkout/portal/webhooks are
enabled. Every activation flag defaults to **false**, so production stays
dormant until the flags are explicitly flipped to a truthy value.

Reading this module has zero side effects: it imports no `stripe` package,
opens no network connection, and never returns a key. The actual Stripe API
calls live in ``stripe_integration.py`` and run only when a flag is enabled.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

# Truthy tokens, matching backend.auth.service.TRUE_VALUES.
_TRUE_VALUES = {"1", "true", "yes", "on"}

# Secret / config env var names (values are NEVER returned by this module).
STRIPE_SECRET_KEY_ENV = "STRIPE_SECRET_KEY"
STRIPE_WEBHOOK_SECRET_ENV = "STRIPE_WEBHOOK_SECRET"

# Activation flags — all default false (dormant).
BILLING_ENABLED_ENV = "STRIPE_BILLING_ENABLED"
CHECKOUT_ENABLED_ENV = "STRIPE_CHECKOUT_ENABLED"
PORTAL_ENABLED_ENV = "STRIPE_PORTAL_ENABLED"
WEBHOOKS_ENABLED_ENV = "STRIPE_WEBHOOKS_ENABLED"

# Required price env vars for the selectable subscription plans.
REQUIRED_PRICE_ENV_VARS: List[str] = [
    "STRIPE_PRICE_INDIVIDUAL_MONTHLY",
    "STRIPE_PRICE_TEAM_BASE_MONTHLY",
    "STRIPE_PRICE_TEAM_EXTRA_SEAT_MONTHLY",
    "STRIPE_PRICE_ORGANIZATION_BASE_MONTHLY",
    "STRIPE_PRICE_ORGANIZATION_EXTRA_SEAT_MONTHLY",
]

# plan_code -> {base: env var, extra: env var or None} for building line items.
PLAN_PRICE_ENV: Dict[str, Dict[str, Optional[str]]] = {
    "individual": {"base": "STRIPE_PRICE_INDIVIDUAL_MONTHLY", "extra": None},
    "team": {
        "base": "STRIPE_PRICE_TEAM_BASE_MONTHLY",
        "extra": "STRIPE_PRICE_TEAM_EXTRA_SEAT_MONTHLY",
    },
    "organization": {
        "base": "STRIPE_PRICE_ORGANIZATION_BASE_MONTHLY",
        "extra": "STRIPE_PRICE_ORGANIZATION_EXTRA_SEAT_MONTHLY",
    },
}


def _flag(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in _TRUE_VALUES


def _present(name: str) -> bool:
    return bool((os.getenv(name) or "").strip())


# ── Individual readers ───────────────────────────────────────────────────────

def stripe_secret_configured() -> bool:
    """True if a Stripe secret key is set — the boolean only, never the value."""
    return _present(STRIPE_SECRET_KEY_ENV)


def webhook_secret_configured() -> bool:
    return _present(STRIPE_WEBHOOK_SECRET_ENV)


def billing_enabled() -> bool:
    return _flag(BILLING_ENABLED_ENV)


def checkout_enabled() -> bool:
    return _flag(CHECKOUT_ENABLED_ENV)


def portal_enabled() -> bool:
    return _flag(PORTAL_ENABLED_ENV)


def webhooks_enabled() -> bool:
    return _flag(WEBHOOKS_ENABLED_ENV)


def missing_price_env_vars() -> List[str]:
    return [name for name in REQUIRED_PRICE_ENV_VARS if not _present(name)]


def all_required_prices_configured() -> bool:
    return not missing_price_env_vars()


def price_id(env_var: Optional[str]) -> Optional[str]:
    if not env_var:
        return None
    value = (os.getenv(env_var) or "").strip()
    return value or None


# ── Effective gates (used by the endpoints) ──────────────────────────────────
#
# A capability is live ONLY when master billing is enabled AND its own flag is
# enabled. With either off, the capability is dormant and no Stripe call runs.

def checkout_effective_enabled() -> bool:
    return billing_enabled() and checkout_enabled()


def portal_effective_enabled() -> bool:
    return billing_enabled() and portal_enabled()


def webhooks_effective_enabled() -> bool:
    return billing_enabled() and webhooks_enabled() and webhook_secret_configured()


def stripe_connected() -> bool:
    """Readiness for the UI: a secret key is present and every price is set.
    This does NOT mean billing is active — activation is gated by the flags."""
    return stripe_secret_configured() and all_required_prices_configured()


def mode() -> str:
    """'active' only when billing is enabled and fully configured; else 'dormant'."""
    if billing_enabled() and stripe_connected():
        return "active"
    return "dormant"


def readiness() -> Dict[str, Any]:
    """Full readiness report — safe to return to clients. Contains booleans,
    a mode string, and the list of *missing* price env var NAMES only. It never
    contains a secret key, a price id value, or any other secret material."""
    return {
        "stripe_secret_configured": stripe_secret_configured(),
        "all_required_prices_configured": all_required_prices_configured(),
        "missing_price_env_vars": missing_price_env_vars(),
        "billing_enabled": billing_enabled(),
        "checkout_enabled": checkout_enabled(),
        "portal_enabled": portal_enabled(),
        "webhooks_enabled": webhooks_enabled(),
        "webhook_secret_configured": webhook_secret_configured(),
        "stripe_connected": stripe_connected(),
        "mode": mode(),
    }
