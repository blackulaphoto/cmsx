"""Internal plan catalog + pure pricing helpers (no Stripe).

The catalog is the single source of truth for plan display names, included
seats, per-extra-seat price, active-client limits, and AI-usage *labels*
(placeholders — no metering yet). Everything here is a pure function so the
exact same math can be mirrored on the frontend (see ``frontend/src/lib/plans.js``)
and exercised in tests without a database or any network/Stripe access.

Pricing formula:  base_price + max(0, active_users - included_users) * extra_user_price
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# ── Billing status values (internal lifecycle; not Stripe statuses) ──────────
BILLING_STATUSES = (
    "trialing",
    "active",
    "past_due",
    "cancelled",
    "comped",
    "disabled",
)

# Default state stamped onto orgs that have no billing row yet.
DEFAULT_PLAN_CODE = "free_trial"
DEFAULT_BILLING_STATUS = "trialing"
DEFAULT_TRIAL_DAYS = 14

# ── Plan catalog ─────────────────────────────────────────────────────────────
#
# price:            numeric monthly base in USD, or None for custom/contact-sales.
# included_users:   seats bundled in the base price.
# extra_user_price: per-extra-seat monthly price, or None when extra seats are
#                   not available on the plan (e.g. Individual is single-seat).
# max_active_clients: hard ceiling used for limit warnings; None = unlimited/custom.
# max_users:        hard seat ceiling for limit warnings; None = soft (extra seats
#                   are simply billable, never blocked).
# selectable:       whether the plan can be chosen via self-serve upgrade in v1.
#                   free_trial is a state, enterprise is contact-sales — both False.
PLANS: Dict[str, Dict[str, Any]] = {
    "free_trial": {
        "plan_code": "free_trial",
        "display_name": "Free Trial",
        "price": 0,
        "price_label": "Free during trial",
        "included_users": 1,
        "extra_user_price": None,
        "max_active_clients": 10,
        "max_users": 1,
        "ai_limit_label": "trial preview",
        "intended_for": "evaluating Ember before choosing a plan",
        "selectable": False,
    },
    "individual": {
        "plan_code": "individual",
        "display_name": "Solo / Individual",
        "price": 49,
        "price_label": "$49/month",
        "included_users": 1,
        "extra_user_price": None,  # extra users not available on this plan
        "max_active_clients": 25,
        "max_users": 1,
        "ai_limit_label": "fair-use starter",
        "intended_for": "solo case manager / independent provider",
        "selectable": True,
    },
    "team": {
        "plan_code": "team",
        "display_name": "Team",
        "price": 99,
        "price_label": "$99/month",
        "included_users": 3,
        "extra_user_price": 29,
        "max_active_clients": 75,
        "max_users": None,  # extra seats billable, not blocked
        "ai_limit_label": "standard team usage",
        "intended_for": "small team / sober living / small program",
        "selectable": True,
    },
    "organization": {
        "plan_code": "organization",
        "display_name": "Organization",
        "price": 199,
        "price_label": "$199/month",
        "included_users": 5,
        "extra_user_price": 25,
        "max_active_clients": 250,
        "max_users": None,
        "ai_limit_label": "expanded org usage",
        "intended_for": "larger program / treatment center / multi-staff org",
        "selectable": True,
    },
    "enterprise": {
        "plan_code": "enterprise",
        "display_name": "Enterprise",
        "price": None,  # custom
        "price_label": "Custom",
        "included_users": None,
        "extra_user_price": None,
        "max_active_clients": None,  # custom / unlimited
        "max_users": None,
        "ai_limit_label": "custom",
        "intended_for": "large treatment centers, multi-location, compliance-heavy",
        "selectable": False,  # contact sales
    },
}

PLAN_CODES = tuple(PLANS.keys())


def get_plan(plan_code: Optional[str]) -> Dict[str, Any]:
    """Return the plan dict for ``plan_code``, falling back to the default plan
    for unknown/empty codes so callers never crash on stale data."""
    code = (plan_code or "").strip().lower()
    return PLANS.get(code, PLANS[DEFAULT_PLAN_CODE])


def list_plans(*, selectable_only: bool = False) -> List[Dict[str, Any]]:
    plans = list(PLANS.values())
    if selectable_only:
        plans = [p for p in plans if p["selectable"]]
    return plans


def is_valid_plan_code(plan_code: Optional[str]) -> bool:
    return (plan_code or "").strip().lower() in PLANS


def is_valid_billing_status(status: Optional[str]) -> bool:
    return (status or "").strip().lower() in BILLING_STATUSES


def estimate_monthly_price(plan_code: Optional[str], active_users: int) -> Optional[float]:
    """Estimated monthly price for ``active_users`` on ``plan_code``.

    Returns None for custom/contact-sales plans (no numeric price). Never
    negative; extra seats below the included count cost nothing.
    """
    plan = get_plan(plan_code)
    base = plan["price"]
    if base is None:
        return None  # custom plan — no computable price
    included = plan["included_users"] or 0
    extra_price = plan["extra_user_price"]
    seats = max(0, int(active_users or 0))
    overage = max(0, seats - included)
    if overage and extra_price:
        return float(base) + overage * float(extra_price)
    return float(base)


def recommend_plan(user_count: int) -> str:
    """Recommend a plan_code from seat count.

    1 user → individual; 2–5 → team; 6–20 → organization; 21+ → enterprise.
    """
    n = max(0, int(user_count or 0))
    if n <= 1:
        return "individual"
    if n <= 5:
        return "team"
    if n <= 20:
        return "organization"
    return "enterprise"


def plan_limits(plan_code: Optional[str]) -> Dict[str, Any]:
    """Limit envelope for a plan (no usage applied)."""
    plan = get_plan(plan_code)
    return {
        "plan_code": plan["plan_code"],
        "max_active_clients": plan["max_active_clients"],
        "included_users": plan["included_users"],
        "max_users": plan["max_users"],
        "ai_limit_label": plan["ai_limit_label"],
    }


def compute_limit_status(
    plan_code: Optional[str],
    *,
    active_users: int,
    active_clients: int,
) -> Dict[str, Any]:
    """Warning-mode limit evaluation. Computes whether usage is within the
    plan's active-client and seat limits. ``over_limit`` is advisory in v1 —
    hard enforcement attaches later at the documented call sites.

    Hard-enforcement attach points (NOT enforced here in v1):
      * active clients  → client create / reactivate
      * staff/users     → team invite accept / staff activation
      * AI usage        → AI request handlers (once metering exists)
    """
    limits = plan_limits(plan_code)
    clients = max(0, int(active_clients or 0))
    users = max(0, int(active_users or 0))

    max_clients = limits["max_active_clients"]
    clients_over = max_clients is not None and clients > max_clients

    max_users = limits["max_users"]
    users_over = max_users is not None and users > max_users

    included = limits["included_users"]
    extra_billable = (
        included is not None and users > included and not users_over
    )

    return {
        "clients": {
            "used": clients,
            "limit": max_clients,
            "over_limit": bool(clients_over),
        },
        "users": {
            "used": users,
            "included": included,
            "limit": max_users,
            "over_limit": bool(users_over),
            # seats beyond the included count that would be billable (not blocked)
            "extra_billable": bool(extra_billable),
        },
        "over_limit": bool(clients_over or users_over),
    }


def build_billing_summary(
    billing: Dict[str, Any],
    *,
    active_users: int,
    active_clients: int,
    ai_usage_placeholder: int = 0,
) -> Dict[str, Any]:
    """Assemble the org-facing billing view from raw billing fields + usage.

    ``billing`` is the dict returned by the auth service's ``get_org_billing``.
    The result carries plan display info, usage counts, an estimated monthly
    price, limit warnings, and the upgrade catalog — everything the Settings
    Billing page and the Super Admin panel need, with NO Stripe identifiers
    surfaced (only an inert ``stripe_connected`` boolean placeholder).
    """
    plan_code = billing.get("plan_code") or DEFAULT_PLAN_CODE
    plan = get_plan(plan_code)
    estimated = estimate_monthly_price(plan_code, active_users)
    limit_status = compute_limit_status(
        plan_code, active_users=active_users, active_clients=active_clients
    )
    return {
        "billing_status": billing.get("billing_status") or DEFAULT_BILLING_STATUS,
        "plan_code": plan["plan_code"],
        "plan": {
            "plan_code": plan["plan_code"],
            "display_name": plan["display_name"],
            "price": plan["price"],
            "price_label": plan["price_label"],
            "included_users": plan["included_users"],
            "extra_user_price": plan["extra_user_price"],
            "max_active_clients": plan["max_active_clients"],
            "ai_limit_label": plan["ai_limit_label"],
            "intended_for": plan["intended_for"],
        },
        "trial_ends_at": billing.get("trial_ends_at"),
        "subscription_provider": billing.get("subscription_provider"),
        # Inert placeholder: never expose the raw Stripe IDs, only whether one
        # has been linked (always false today — Stripe is disabled).
        "stripe_connected": bool(
            billing.get("stripe_customer_id") or billing.get("stripe_subscription_id")
        ),
        "usage": {
            "active_users": max(0, int(active_users or 0)),
            "active_clients": max(0, int(active_clients or 0)),
            "ai_usage_placeholder": max(0, int(ai_usage_placeholder or 0)),
        },
        "estimated_monthly_price": estimated,
        "limit_status": limit_status,
        "recommended_plan": recommend_plan(active_users),
        "plans": list_plans(),
        # Stripe is intentionally disabled in this phase.
        "payments_enabled": False,
    }
