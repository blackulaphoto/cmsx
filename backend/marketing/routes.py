"""Owner Marketing + Campaign Tracker endpoints.

One router:

* ``owner_router`` (``/api/owner/marketing``) — platform owner / super-admin only.
  - ``GET /campaigns`` — full campaign list (optional allowlisted status/channel
    filters).
  - ``POST /campaigns`` — create a campaign. Status/channel validated against
    allowlists; text fields length-capped; free text PHI-risk scanned (rejected,
    not scrubbed).
  - ``PATCH /campaigns/{campaign_id}`` — partial update (status/spend/budget/notes
    and the rest). Same validation + PHI guard.
  - ``GET /summary`` — counts by status/channel, total planned budget, total
    manual spend, UTM attribution correlated from ``analytics_events``, and honest
    performance placeholders (null until a real data source exists).

No external ad-platform call (Google Ads, Meta, TikTok, LinkedIn) and no Stripe
code is reachable from here. Nothing here activates billing or SaaS mode.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.analytics.store import analytics_store
from backend.auth.service import require_super_admin
from backend.marketing.store import (
    CHANNELS,
    OWNER_ACTION_CAMPAIGN_CREATED,
    OWNER_ACTION_CAMPAIGN_SPEND_UPDATED,
    OWNER_ACTION_CAMPAIGN_STATUS_CHANGED,
    STATUSES,
    marketing_store,
    normalize_channel,
    normalize_status,
)
from backend.support.store import scan_phi_risk

logger = logging.getLogger(__name__)

owner_router = APIRouter(prefix="/api/owner/marketing", tags=["owner-marketing"])


# ── Payload models ───────────────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    """Create payload. Status/channel default to safe values and are validated in
    the route; text fields are length-capped here and again in the store."""
    name: str = Field(min_length=1, max_length=120)
    status: str = Field(default="draft", max_length=32)
    channel: str = Field(default="manual", max_length=32)
    utm_source: Optional[str] = Field(default=None, max_length=128)
    utm_medium: Optional[str] = Field(default=None, max_length=128)
    utm_campaign: Optional[str] = Field(default=None, max_length=128)
    landing_page_url: Optional[str] = Field(default=None, max_length=500)
    budget_amount: Optional[float] = Field(default=None, ge=0)
    spend_amount: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)


class CampaignPatch(BaseModel):
    """Partial-update payload. Every field optional; ``model_fields_set`` lets the
    store tell "omitted" from "explicitly cleared to null"."""
    name: Optional[str] = Field(default=None, max_length=120)
    status: Optional[str] = Field(default=None, max_length=32)
    channel: Optional[str] = Field(default=None, max_length=32)
    utm_source: Optional[str] = Field(default=None, max_length=128)
    utm_medium: Optional[str] = Field(default=None, max_length=128)
    utm_campaign: Optional[str] = Field(default=None, max_length=128)
    landing_page_url: Optional[str] = Field(default=None, max_length=500)
    budget_amount: Optional[float] = Field(default=None, ge=0)
    spend_amount: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _phi_risk_in_text(*values: Optional[str]) -> Optional[str]:
    """Return the first PHI-risk reason found across the given free-text fields,
    else None. Marketing copy never needs client PHI — unsafe text is rejected."""
    for value in values:
        if value:
            risk = scan_phi_risk(value)
            if risk:
                return risk
    return None


def _fields_set(payload: BaseModel) -> set:
    return getattr(payload, "model_fields_set", None) or getattr(payload, "__fields_set__", set())


# ── Owner campaign endpoints (super-admin only) ──────────────────────────────

@owner_router.get("/campaigns")
async def owner_list_campaigns(
    request: Request,
    status: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
):
    """Full campaign list. Platform super-admin only. Optional allowlisted filters;
    unrecognized filter values are ignored rather than erroring."""
    require_super_admin(request)
    campaigns = marketing_store.list_campaigns(
        status=status, channel=channel, limit=limit, offset=offset
    )
    return {
        "success": True,
        "campaigns": campaigns,
        "count": len(campaigns),
        "statuses": list(STATUSES),
        "channels": list(CHANNELS),
    }


@owner_router.post("/campaigns")
async def owner_create_campaign(payload: CampaignCreate, request: Request):
    """Create a campaign. Platform super-admin only. Status/channel are validated
    against the allowlists; free-text fields are PHI-risk scanned and rejected if
    they look like protected client content."""
    actor = require_super_admin(request)

    if normalize_status(payload.status) is None:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "detail": f"Unknown status '{payload.status}'.",
                "allowed_statuses": list(STATUSES),
            },
        )
    if normalize_channel(payload.channel) is None:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "detail": f"Unknown channel '{payload.channel}'.",
                "allowed_channels": list(CHANNELS),
            },
        )

    risk = _phi_risk_in_text(payload.name, payload.notes, payload.landing_page_url)
    if risk:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "detail": (
                    "This campaign looks like it may contain protected client "
                    f"information ({risk}). Keep campaign names, notes, and URLs free "
                    "of client names, PHI, MRNs, DOBs, SSNs, phone numbers, and emails."
                ),
                "phi_risk": risk,
            },
        )

    campaign = marketing_store.create_campaign(
        name=payload.name,
        status=payload.status,
        channel=payload.channel,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        landing_page_url=payload.landing_page_url,
        budget_amount=payload.budget_amount,
        spend_amount=payload.spend_amount,
        notes=payload.notes,
    )
    # Safe audit trail: action enum + campaign id + the new (allowlisted) status
    # only. Never the campaign name, notes, or URL. Best-effort — never blocks.
    marketing_store.record_owner_action(
        OWNER_ACTION_CAMPAIGN_CREATED,
        campaign_id=campaign.get("id"),
        actor_email=getattr(actor, "email", None),
        detail=campaign.get("status"),
    )
    return {"success": True, "campaign": campaign}


@owner_router.patch("/campaigns/{campaign_id}")
async def owner_update_campaign(campaign_id: int, payload: CampaignPatch, request: Request):
    """Partial-update a campaign. Platform super-admin only. Validates status/channel
    against the allowlists and PHI-risk scans any supplied free text."""
    actor = require_super_admin(request)

    if payload.status is not None and normalize_status(payload.status) is None:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "detail": f"Unknown status '{payload.status}'.",
                "allowed_statuses": list(STATUSES),
            },
        )
    if payload.channel is not None and normalize_channel(payload.channel) is None:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "detail": f"Unknown channel '{payload.channel}'.",
                "allowed_channels": list(CHANNELS),
            },
        )

    risk = _phi_risk_in_text(payload.name, payload.notes, payload.landing_page_url)
    if risk:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "detail": (
                    "This update looks like it may contain protected client "
                    f"information ({risk}). Keep campaign names, notes, and URLs free "
                    "of client names, PHI, MRNs, DOBs, SSNs, phone numbers, and emails."
                ),
                "phi_risk": risk,
            },
        )

    fields_set = _fields_set(payload)
    updated = marketing_store.update_campaign(
        campaign_id,
        name=payload.name,
        status=payload.status,
        channel=payload.channel,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        landing_page_url=payload.landing_page_url,
        budget_amount=payload.budget_amount,
        spend_amount=payload.spend_amount,
        notes=payload.notes,
        name_set="name" in fields_set,
        status_set="status" in fields_set,
        channel_set="channel" in fields_set,
        utm_source_set="utm_source" in fields_set,
        utm_medium_set="utm_medium" in fields_set,
        utm_campaign_set="utm_campaign" in fields_set,
        landing_page_url_set="landing_page_url" in fields_set,
        budget_amount_set="budget_amount" in fields_set,
        spend_amount_set="spend_amount" in fields_set,
        notes_set="notes" in fields_set,
    )
    if updated is None:
        return JSONResponse(
            status_code=404,
            content={"success": False, "detail": f"Campaign {campaign_id} not found."},
        )
    # Safe audit trail for the two meaningful owner edits. Only the action enum,
    # the campaign id, and (for status) the new allowlisted status value are
    # logged — never the campaign name, notes, URL, or the spend figure as text.
    actor_email = getattr(actor, "email", None)
    if "status" in fields_set:
        marketing_store.record_owner_action(
            OWNER_ACTION_CAMPAIGN_STATUS_CHANGED,
            campaign_id=campaign_id,
            actor_email=actor_email,
            detail=updated.get("status"),
        )
    if "spend_amount" in fields_set:
        marketing_store.record_owner_action(
            OWNER_ACTION_CAMPAIGN_SPEND_UPDATED,
            campaign_id=campaign_id,
            actor_email=actor_email,
            detail=None,
        )
    return {"success": True, "campaign": updated}


@owner_router.get("/summary")
async def owner_marketing_summary(request: Request):
    """Campaign-tracker summary. Platform super-admin only.

    Counts by status/channel, total planned budget, total manual spend, UTM
    attribution from ``analytics_events`` (with per-campaign correlation by
    ``utm_campaign`` where data exists), and honest performance placeholders. No
    numbers are fabricated — performance fields stay null until a real source
    exists. No Stripe / external ad-platform call is made."""
    require_super_admin(request)

    data = marketing_store.summary()

    # UTM attribution from real tracked analytics events (never fabricated).
    attribution = analytics_store.marketing_attribution()
    campaign_visits = attribution.get("campaign", {}) or {}

    # Correlate owner-defined campaigns to tracked visits by utm_campaign value.
    correlated = {}
    for utm_value in marketing_store.utm_campaign_values():
        if utm_value in campaign_visits:
            correlated[utm_value] = int(campaign_visits[utm_value])

    total_spend = data.get("total_spend") or 0.0

    return {
        "success": True,
        **data,
        "utm_attribution": attribution,
        # Tracked visits matched to an owner-defined campaign's utm_campaign value.
        "campaign_utm_visits": correlated,
        # Honest performance placeholders. landing_page_visits / signups /
        # conversions stay null until a real source is wired up; cost_per_signup is
        # computed only when both spend and a real signup count exist (not in v1).
        "performance": {
            "landing_page_visits": None,
            "signups": None,
            "conversions": None,
            "cost_per_signup": None,
            "source": "not_connected",
        },
        # Marketing data sources are not connected to any external ad platform.
        "ad_platforms_connected": False,
        # Stripe stays dormant — surfaced as an inert flag only.
        "stripe_activated": False,
    }
