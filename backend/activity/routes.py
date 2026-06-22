"""Owner Activity Center endpoint.

One router:

* ``owner_router`` (``/api/owner``) — ``GET /activity`` is platform owner /
  super-admin only. It aggregates the existing per-domain owner/admin audit
  trails into a single normalized, newest-first feed:

    - support ticket triage actions      (``owner_action_events``)
    - org suspend/restore actions        (``owner_admin_events``, target ``org``)
    - user role/status actions           (``owner_admin_events``, target ``user``)
    - marketing campaign create/update    (``marketing_owner_action_events``)
    - safe usage analytics events         (``analytics_events`` — type/module only)

Safety is structural, not incidental:

  * No new table is created and no existing audit row is rewritten.
  * Every event is re-projected through ``_normalize`` onto a fixed whitelist of
    keys. Whatever a source returns, ONLY the safe normalized fields are emitted.
  * The underlying audit trails carry only enums/ids/emails by construction —
    never PHI, client names/notes, documents, support ticket subjects or
    descriptions, internal notes, campaign names/notes, or any free text a user
    submitted.

No Stripe / billing / SaaS code is reachable from here. This endpoint is
read-only and mutates nothing.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request

from backend.auth.service import auth_service, require_super_admin

logger = logging.getLogger(__name__)

owner_router = APIRouter(prefix="/api/owner", tags=["owner-activity"])

# ── Limits / caps ─────────────────────────────────────────────────────────────
DEFAULT_LIMIT = 50
MAX_LIMIT = 200
# How many rows we pull from each source before merging. Kept generous so the
# merged + filtered window is representative; the final list is capped to ``limit``.
PER_SOURCE_FETCH = MAX_LIMIT
MAX_FILTER_LEN = 200

# The only sources this endpoint will ever emit. Used to validate the ``source``
# filter and to keep the contract closed.
SOURCES = ("support", "org", "user", "marketing", "analytics", "system")

# The exact, closed set of keys every normalized event carries. Anything not in
# this whitelist is dropped — the structural guarantee that no upstream free text
# can leak through.
_SAFE_KEYS = (
    "id",
    "source",
    "action",
    "actor_email",
    "org_id",
    "target_type",
    "target_id",
    "safe_detail",
    "created_at",
)


def _cap(value: Optional[str], limit: int = MAX_FILTER_LEN) -> Optional[str]:
    """Trim a scalar to ``limit`` chars; None/blank → None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:limit]


def _normalize(
    *,
    raw_id: Any,
    source: str,
    action: Any,
    actor_email: Any = None,
    org_id: Any = None,
    target_type: Any = None,
    target_id: Any = None,
    safe_detail: Any = None,
    created_at: Any = None,
) -> Dict[str, Any]:
    """Project one source event onto the fixed safe schema.

    Every string field is coerced + length-capped. The output dict contains
    EXACTLY ``_SAFE_KEYS`` — no source-specific extras survive."""
    event = {
        "id": str(raw_id),
        "source": source,
        "action": _cap(action, 64),
        "actor_email": _cap(actor_email, MAX_FILTER_LEN),
        "org_id": _cap(org_id, 128),
        "target_type": _cap(target_type, 32),
        "target_id": _cap(target_id, 128),
        "safe_detail": _cap(safe_detail, 64),
        "created_at": str(created_at) if created_at is not None else None,
    }
    # Defensive: emit only whitelisted keys, in a stable order.
    return {key: event[key] for key in _SAFE_KEYS}


def _support_events() -> List[Dict[str, Any]]:
    """Support ticket triage actions. ``detail`` is a safe status/priority enum;
    the ticket subject/description and internal notes are NEVER in this trail."""
    out: List[Dict[str, Any]] = []
    try:
        from backend.support.store import support_store

        for r in support_store.recent_owner_actions(limit=PER_SOURCE_FETCH):
            ticket_id = r.get("ticket_id")
            out.append(
                _normalize(
                    raw_id=f"support-{r.get('id')}",
                    source="support",
                    action=r.get("action"),
                    actor_email=r.get("actor_email"),
                    org_id=None,
                    target_type="support_ticket" if ticket_id is not None else None,
                    target_id=ticket_id,
                    safe_detail=r.get("detail"),
                    created_at=r.get("created_at"),
                )
            )
    except Exception:  # noqa: BLE001 — one bad source must not break the feed
        logger.warning("Activity Center: failed to load support events", exc_info=True)
    return out


def _admin_events() -> List[Dict[str, Any]]:
    """Org/user management actions (suspend/restore, role/status). The source is
    derived from the audited ``target_type`` (org vs user). ``detail`` is a safe
    status/role enum; no PHI is in this trail."""
    out: List[Dict[str, Any]] = []
    try:
        for r in auth_service.recent_owner_admin_actions(limit=PER_SOURCE_FETCH):
            target_type = (r.get("target_type") or "").strip().lower()
            source = target_type if target_type in ("org", "user") else "system"
            out.append(
                _normalize(
                    raw_id=f"admin-{r.get('id')}",
                    source=source,
                    action=r.get("action"),
                    actor_email=r.get("actor_email"),
                    org_id=r.get("org_id"),
                    target_type=r.get("target_type"),
                    target_id=r.get("target_id"),
                    safe_detail=r.get("detail"),
                    created_at=r.get("created_at"),
                )
            )
    except Exception:  # noqa: BLE001
        logger.warning("Activity Center: failed to load admin events", exc_info=True)
    return out


def _marketing_events() -> List[Dict[str, Any]]:
    """Marketing campaign create/update actions. ``detail`` is a safe status enum
    (or None); the campaign name/notes/URL are NEVER in this trail."""
    out: List[Dict[str, Any]] = []
    try:
        from backend.marketing.store import marketing_store

        for r in marketing_store.recent_owner_actions(limit=PER_SOURCE_FETCH):
            campaign_id = r.get("campaign_id")
            out.append(
                _normalize(
                    raw_id=f"marketing-{r.get('id')}",
                    source="marketing",
                    action=r.get("action"),
                    actor_email=r.get("actor_email"),
                    org_id=None,
                    target_type="campaign" if campaign_id is not None else None,
                    target_id=campaign_id,
                    safe_detail=r.get("detail"),
                    created_at=r.get("created_at"),
                )
            )
    except Exception:  # noqa: BLE001
        logger.warning("Activity Center: failed to load marketing events", exc_info=True)
    return out


def _analytics_events() -> List[Dict[str, Any]]:
    """Safe usage analytics tail. ``recent_events`` already exposes only event
    type, module, and timestamp — no route, ids, or metadata. Surfaced here as
    inert ``analytics`` rows (no actor) so the feed is genuinely unified; the UI
    badges them distinctly from owner/admin actions."""
    out: List[Dict[str, Any]] = []
    try:
        from backend.analytics.store import analytics_store

        rows = analytics_store.recent_events(limit=PER_SOURCE_FETCH)
        for idx, r in enumerate(rows):
            module = r.get("module")
            out.append(
                _normalize(
                    raw_id=f"analytics-{idx}-{r.get('created_at')}",
                    source="analytics",
                    action=r.get("event_type"),
                    actor_email=None,
                    org_id=None,
                    target_type="module" if module else None,
                    target_id=module,
                    safe_detail=None,
                    created_at=r.get("created_at"),
                )
            )
    except Exception:  # noqa: BLE001
        logger.warning("Activity Center: failed to load analytics events", exc_info=True)
    return out


@owner_router.get("/activity")
async def owner_activity(
    request: Request,
    source: Optional[str] = None,
    action: Optional[str] = None,
    org_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
):
    """Unified owner/admin activity feed. Platform super-admin only.

    Aggregates the existing per-domain audit trails into one normalized,
    newest-first list of SAFE events. Optional filters (all length-capped):

      * ``source``       — one of support / org / user / marketing / analytics / system
      * ``action``       — exact action enum match (e.g. ``support_status_changed``)
      * ``org_id``       — exact org id match
      * ``actor_email``  — case-insensitive substring match
      * ``limit``        — capped to ``MAX_LIMIT`` (default ``DEFAULT_LIMIT``)

    Returns only enum/id/email/timestamp metadata. It never returns PHI, client
    names/notes, documents, support descriptions, internal notes, campaign notes,
    or any other free text — the underlying trails do not store it, and every row
    is re-projected onto a fixed safe whitelist before it leaves this endpoint."""
    require_super_admin(request)

    # Normalize + cap filters.
    source_f = (_cap(source, 32) or "").lower() or None
    if source_f is not None and source_f not in SOURCES:
        source_f = None  # unknown source → no filter, rather than erroring
    action_f = (_cap(action, 64) or "").lower() or None
    org_f = _cap(org_id, 128)
    actor_f = (_cap(actor_email, MAX_FILTER_LEN) or "").lower() or None
    try:
        limit_n = max(1, min(int(limit), MAX_LIMIT))
    except (TypeError, ValueError):
        limit_n = DEFAULT_LIMIT

    events: List[Dict[str, Any]] = []
    events.extend(_support_events())
    events.extend(_admin_events())
    events.extend(_marketing_events())
    events.extend(_analytics_events())

    # Apply filters.
    if source_f:
        events = [e for e in events if e["source"] == source_f]
    if action_f:
        events = [e for e in events if (e.get("action") or "").lower() == action_f]
    if org_f:
        events = [e for e in events if (e.get("org_id") or "") == org_f]
    if actor_f:
        events = [e for e in events if actor_f in (e.get("actor_email") or "").lower()]

    # Newest-first. ISO-8601 timestamps sort correctly as strings; missing
    # timestamps sort last.
    events.sort(key=lambda e: e.get("created_at") or "", reverse=True)
    events = events[:limit_n]

    return {
        "success": True,
        "events": events,
        "count": len(events),
        "limit": limit_n,
        "sources": list(SOURCES),
        # Inert posture flags — this endpoint never touches Stripe / billing / SaaS.
        "stripe_activated": False,
    }
