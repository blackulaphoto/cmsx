"""Analytics endpoints.

Two routers:

* ``event_router`` (``/api/analytics``) — ``POST /event`` accepts safe usage
  signals from any authenticated user. User/org are derived from the token, never
  from the request body. Works regardless of MULTI_TENANT_ENABLED. Event names are
  validated against an allowlist and metadata is sanitized (PHI stripped).

* ``owner_router`` (``/api/owner/analytics``) — ``GET /summary`` is platform
  owner / super-admin only. It returns counts, plan/billing breakdowns, an
  estimated MRR computed from INTERNAL plan fields (never Stripe), and module
  usage from the analytics store. No Stripe call is made anywhere here.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import backend.shared.db_path as db_path_mod
from backend.analytics.store import ALLOWED_EVENT_TYPES, analytics_store
from backend.auth.service import auth_service, require_super_admin, require_user
from backend.billing import plans as billing_plans

logger = logging.getLogger(__name__)

event_router = APIRouter(prefix="/api/analytics", tags=["analytics"])
owner_router = APIRouter(prefix="/api/owner/analytics", tags=["owner-analytics"])


class AnalyticsEvent(BaseModel):
    """Safe event payload. No client/PHI fields are accepted; metadata is
    sanitized server-side regardless of what is sent."""
    event_type: str = Field(min_length=1, max_length=64)
    route: Optional[str] = Field(default=None, max_length=512)
    module: Optional[str] = Field(default=None, max_length=128)
    source: Optional[str] = Field(default=None, max_length=128)
    medium: Optional[str] = Field(default=None, max_length=128)
    campaign: Optional[str] = Field(default=None, max_length=128)
    referrer: Optional[str] = Field(default=None, max_length=512)
    metadata: Optional[Dict[str, Any]] = None


# ── Event ingestion ──────────────────────────────────────────────────────────

@event_router.post("/event")
async def record_event(payload: AnalyticsEvent, request: Request):
    """Record one usage event for the authenticated caller.

    Does NOT require multi-tenant mode. Identity (org_id / case_manager_id) is
    taken from the token only. Unknown event names are rejected (422); metadata
    is always sanitized so PHI-like keys can never be persisted."""
    user = require_user(request)

    event_type = (payload.event_type or "").strip().lower()
    if event_type not in ALLOWED_EVENT_TYPES:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "detail": f"Unknown event_type '{event_type}'.",
                "allowed_event_types": list(ALLOWED_EVENT_TYPES),
            },
        )

    result = analytics_store.record_event(
        event_type=event_type,
        route=payload.route,
        module=payload.module,
        org_id=user.org_id,
        case_manager_id=user.case_manager_id,
        source=payload.source,
        medium=payload.medium,
        campaign=payload.campaign,
        referrer=payload.referrer,
        metadata=payload.metadata,
    )
    return {"success": True, "event_id": result["event_id"]}


# ── Owner analytics summary ──────────────────────────────────────────────────

def _total_client_count() -> int:
    """Platform-wide client COUNT only (no rows/PHI). Fails open to 0."""
    try:
        path = db_path_mod.DB_DIR / "core_clients.db"
        with sqlite3.connect(str(path)) as conn:
            row = conn.execute("SELECT COUNT(*) FROM clients").fetchone()
        return int(row[0]) if row else 0
    except Exception:  # noqa: BLE001 — counts are best-effort metadata
        return 0


def _commercial_summary() -> Dict[str, Any]:
    """Org/plan/billing rollup + estimated MRR from INTERNAL plan fields only.

    Iterates organizations, reads each org's internal billing (plan_code,
    billing_status) and active-seat count, and sums ``estimate_monthly_price``.
    Custom/contact-sales plans (price=None) contribute 0 to MRR and are surfaced
    separately so the number is honest. No Stripe call is made.
    """
    orgs = auth_service.list_organizations()
    total_orgs = len(orgs)
    active_orgs = 0
    suspended_orgs = 0
    plan_breakdown: Dict[str, int] = {}
    billing_status_breakdown: Dict[str, int] = {}
    estimated_mrr = 0.0
    custom_plan_orgs = 0

    for org in orgs:
        status = (org.get("status") or "active").lower()
        if status == "suspended":
            suspended_orgs += 1
        else:
            active_orgs += 1

        billing = auth_service.get_org_billing(org["org_id"])
        plan_code = billing.get("plan_code") or billing_plans.DEFAULT_PLAN_CODE
        billing_status = billing.get("billing_status") or billing_plans.DEFAULT_BILLING_STATUS
        plan_breakdown[plan_code] = plan_breakdown.get(plan_code, 0) + 1
        billing_status_breakdown[billing_status] = (
            billing_status_breakdown.get(billing_status, 0) + 1
        )

        active_users = int(org.get("active_user_count") or 0)
        price = billing_plans.estimate_monthly_price(plan_code, active_users)
        if price is None:
            custom_plan_orgs += 1
        else:
            estimated_mrr += float(price)

    return {
        "total_orgs": total_orgs,
        "active_orgs": active_orgs,
        "suspended_orgs": suspended_orgs,
        "plan_breakdown": plan_breakdown,
        "billing_status_breakdown": billing_status_breakdown,
        # Internal-model MRR. Stripe is never consulted.
        "estimated_mrr": round(estimated_mrr, 2),
        "estimated_mrr_source": "internal_plan_fields",
        "custom_plan_orgs": custom_plan_orgs,
    }


@owner_router.get("/summary")
async def analytics_summary(request: Request):
    """Owner HQ analytics summary. Platform super-admin only.

    Returns org/user/client counts, plan + billing breakdowns, estimated MRR
    (internal plan fields only — no Stripe), and module-usage analytics. Usage
    sections are honest empty states until tracked events exist."""
    require_super_admin(request)

    overview = auth_service.platform_overview()
    commercial = _commercial_summary()
    usage = analytics_store.usage_summary()

    return {
        "success": True,
        "total_orgs": commercial["total_orgs"],
        "active_orgs": commercial["active_orgs"],
        "suspended_orgs": commercial["suspended_orgs"],
        "total_users": overview["total_users"],
        "active_users": overview["active_users"],
        "total_clients": _total_client_count(),
        "plan_breakdown": commercial["plan_breakdown"],
        "billing_status_breakdown": commercial["billing_status_breakdown"],
        "estimated_mrr": commercial["estimated_mrr"],
        "estimated_mrr_source": commercial["estimated_mrr_source"],
        "custom_plan_orgs": commercial["custom_plan_orgs"],
        "total_events": usage["total_events"],
        "module_usage": usage["module_usage"],
        "top_modules": usage["top_modules"],
        "least_used_modules": usage["least_used_modules"],
        "marketing_source_breakdown": usage["marketing_source_breakdown"],
        "recent_activity": usage["recent_activity"],
        # Stripe stays dormant — surfaced as an inert flag only.
        "stripe_activated": False,
    }
