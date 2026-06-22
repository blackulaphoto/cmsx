"""Support Queue endpoints.

Two routers:

* ``ticket_router`` (``/api/support``) — ``POST /tickets`` lets any authenticated
  user file a support ticket. User/org identity is derived from the token, never
  from the body. Category/priority are validated against allowlists; subject and
  description are required and length-capped. Lifecycle fields (status / assigned /
  internal notes) are NOT accepted here — the model omits them and the store forces
  safe defaults. Optional structured ``extra`` metadata is PHI-sanitized.

* ``owner_router`` (``/api/owner/support``) — platform owner / super-admin only.
  ``GET /tickets`` (full queue), ``GET /summary`` (counts + safe recent feed), and
  ``PATCH /tickets/{ticket_id}`` (triage: status / priority / assignment / internal
  notes; resolved_at is managed automatically).

No Stripe code is reachable from here. The "billing" category is just a tag.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.auth.service import require_super_admin, require_user
from backend.support.store import (
    CATEGORIES,
    PRIORITIES,
    STATUSES,
    normalize_category,
    normalize_priority,
    normalize_status,
    scan_phi_risk,
    support_store,
)

logger = logging.getLogger(__name__)

ticket_router = APIRouter(prefix="/api/support", tags=["support"])
owner_router = APIRouter(prefix="/api/owner/support", tags=["owner-support"])


# ── Payload models ───────────────────────────────────────────────────────────

class SupportTicketCreate(BaseModel):
    """Safe create payload. Deliberately omits status / assigned_to /
    internal_notes / resolved_at so a user can never set owner-only fields.
    Optional ``extra`` is sanitized server-side (PHI keys dropped)."""
    category: str = Field(min_length=1, max_length=64)
    priority: str = Field(default="normal", max_length=32)
    subject: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    extra: Optional[Dict[str, Any]] = None


class SupportTicketPatch(BaseModel):
    """Owner-only triage payload. Every field optional; resolved_at is managed by
    the store based on the resulting status (never set directly by the client)."""
    status: Optional[str] = Field(default=None, max_length=32)
    priority: Optional[str] = Field(default=None, max_length=32)
    assigned_to: Optional[str] = Field(default=None, max_length=200)
    internal_notes: Optional[str] = Field(default=None, max_length=5000)


# ── User ticket creation ─────────────────────────────────────────────────────

@ticket_router.post("/tickets")
async def create_support_ticket(payload: SupportTicketCreate, request: Request):
    """Create a support ticket for the authenticated caller.

    Does NOT require multi-tenant mode. org_id / submitted_by are taken from the
    token only. Unknown category/priority are rejected (422). The new ticket always
    starts ``open`` with no assignment/internal notes regardless of the request."""
    user = require_user(request)

    category = normalize_category(payload.category)
    if category is None:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "detail": f"Unknown category '{payload.category}'.",
                "allowed_categories": list(CATEGORIES),
            },
        )

    priority = normalize_priority(payload.priority)
    if priority is None:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "detail": f"Unknown priority '{payload.priority}'.",
                "allowed_priorities": list(PRIORITIES),
            },
        )

    subject = (payload.subject or "").strip()
    description = (payload.description or "").strip()
    if not subject or not description:
        return JSONResponse(
            status_code=422,
            content={"success": False, "detail": "Subject and description are required."},
        )

    # Conservative PHI-risk guard on free text. Tickets must describe issues in
    # general terms — protected client content is rejected outright (not scrubbed).
    risk = scan_phi_risk(subject) or scan_phi_risk(description)
    if risk:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "detail": (
                    "This ticket looks like it may contain protected client information "
                    f"({risk}). Please remove client names, PHI, MRNs, DOBs, SSNs, phone "
                    "numbers, emails, or case/progress notes and describe the issue in "
                    "general terms."
                ),
                "phi_risk": risk,
            },
        )

    result = support_store.create_ticket(
        category=category,
        priority=priority,
        subject=subject,
        description=description,
        org_id=user.org_id,
        submitted_by_user_id=user.case_manager_id,
        submitted_by_email=user.email,
        extra=payload.extra,
    )
    return {
        "success": True,
        "ticket_id": result["ticket_id"],
        "status": "open",
        "dropped_metadata_keys": result["dropped_metadata_keys"],
    }


# ── Owner queue (super-admin only) ───────────────────────────────────────────

@owner_router.get("/tickets")
async def owner_list_tickets(
    request: Request,
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """Full support queue. Platform super-admin only. Optional allowlisted filters;
    unrecognized filter values are ignored rather than erroring."""
    require_super_admin(request)
    tickets = support_store.list_tickets(
        status=status, category=category, priority=priority, limit=limit, offset=offset
    )
    return {
        "success": True,
        "tickets": tickets,
        "count": len(tickets),
        "categories": list(CATEGORIES),
        "priorities": list(PRIORITIES),
        "statuses": list(STATUSES),
    }


@owner_router.get("/tickets/{ticket_id}")
async def owner_get_ticket(ticket_id: int, request: Request):
    """Full single-ticket detail for the owner detail drawer. Platform super-admin
    only. This is the ONLY place description + internal notes are returned together —
    the summary's recent feed deliberately omits them."""
    require_super_admin(request)
    ticket = support_store.get_ticket(ticket_id)
    if ticket is None:
        return JSONResponse(
            status_code=404,
            content={"success": False, "detail": f"Ticket {ticket_id} not found."},
        )
    return {"success": True, "ticket": ticket}


@owner_router.get("/audit")
async def owner_support_audit(request: Request, limit: int = 50):
    """Recent owner-action audit events (status/priority/internal-note changes).
    Platform super-admin only. Safe by construction — carries no ticket text, note
    content, client names, or other free text; only action type, ticket id, acting
    owner email, and a safe enum detail."""
    require_super_admin(request)
    events = support_store.recent_owner_actions(limit=limit)
    return {"success": True, "events": events, "count": len(events)}


@owner_router.get("/summary")
async def owner_support_summary(request: Request):
    """Support queue summary. Platform super-admin only.

    Counts (total / open / high+urgent), category/status/priority breakdowns, and a
    safe recent-tickets feed. Honest empty state until tickets exist."""
    require_super_admin(request)
    data = support_store.summary()
    return {
        "success": True,
        **data,
        # Stripe stays dormant — surfaced as an inert flag only.
        "stripe_activated": False,
    }


@owner_router.patch("/tickets/{ticket_id}")
async def owner_update_ticket(ticket_id: int, payload: SupportTicketPatch, request: Request):
    """Triage a ticket. Platform super-admin only. Validates status/priority against
    the allowlists; assignment / internal notes are length-capped in the store;
    resolved_at is managed automatically from the resulting status."""
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
    if payload.priority is not None and normalize_priority(payload.priority) is None:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "detail": f"Unknown priority '{payload.priority}'.",
                "allowed_priorities": list(PRIORITIES),
            },
        )

    # Same PHI-risk guard applies to owner-authored internal notes.
    if payload.internal_notes:
        note_risk = scan_phi_risk(payload.internal_notes)
        if note_risk:
            return JSONResponse(
                status_code=422,
                content={
                    "success": False,
                    "detail": (
                        "Internal note looks like it may contain protected client "
                        f"information ({note_risk}). Keep notes free of client names, "
                        "PHI, MRNs, DOBs, SSNs, phone numbers, emails, or case notes."
                    ),
                    "phi_risk": note_risk,
                },
            )

    fields_set = getattr(payload, "model_fields_set", None) or getattr(payload, "__fields_set__", set())
    updated = support_store.update_ticket(
        ticket_id,
        status=payload.status,
        priority=payload.priority,
        assigned_to=payload.assigned_to,
        internal_notes=payload.internal_notes,
        assigned_to_set="assigned_to" in fields_set,
        internal_notes_set="internal_notes" in fields_set,
        actor_email=getattr(actor, "email", None),
    )
    if updated is None:
        return JSONResponse(
            status_code=404,
            content={"success": False, "detail": f"Ticket {ticket_id} not found."},
        )
    return {"success": True, "ticket": updated}
