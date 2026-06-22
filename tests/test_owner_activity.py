"""Owner Activity Center v1 tests.

Covers the unified, read-only ``GET /api/owner/activity`` aggregation endpoint:

  * owner-only access (unauthenticated 401, non-owner 403, super-admin 200)
  * normalized events from every source (support / org / user / marketing /
    analytics)
  * the ``limit`` cap and the source / action / org_id / actor_email filters
  * the hard safety guarantee: no PHI / client content / support descriptions /
    internal notes / campaign names or notes ever appears in the response, and
    every event carries only the safe whitelisted keys.

``DB_DIR`` is repointed at a tmp dir and each domain store is isolated there, so
no tracked ``databases/*.db`` file is touched. No Stripe env var is required and
no Stripe / billing / SaaS code is exercised.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.activity.routes as activity_routes
import backend.analytics.store as analytics_store_mod
import backend.marketing.store as marketing_store_mod
import backend.support.store as support_store_mod
import backend.shared.db_path as db_path_mod
from backend.analytics.store import AnalyticsStore
from backend.marketing.store import MarketingStore
from backend.support.store import SupportStore
from backend.auth.service import (
    AuthenticatedUser,
    FirebaseAuthService,
    ORG_ADMIN_ROLE,
    ORG_MEMBER_ROLE,
)
from backend.shared.tenancy import DEFAULT_ORG_ID

SUPER_EMAIL = "blackulaphotography@gmail.com"

# Free-text strings we deliberately push into the underlying ticket/campaign rows.
# NONE of these may ever surface in the activity feed.
PHI_SUBJECT = "Client Jane Doe SSN leak"
PHI_DESCRIPTION = "Patient DOB 1990-01-01 and diagnosis details in the record"
INTERNAL_NOTE = "private internal triage note do not expose"
CAMPAIGN_NAME = "SecretCampaignNameAlpha"
CAMPAIGN_NOTES = "confidential spend rationale notes"


def _super_admin_user():
    return AuthenticatedUser(
        firebase_uid="owner", email=SUPER_EMAIL, full_name="Owner", role="admin",
        case_manager_id="cm_owner", auth_provider="test", is_active=True,
        org_id=DEFAULT_ORG_ID, org_role=ORG_ADMIN_ROLE,
    )


def _member_user():
    return AuthenticatedUser(
        firebase_uid="m_a", email="m_a@a.test", full_name="Member A", role="case_manager",
        case_manager_id="cm_1", auth_provider="test", is_active=True,
        org_id="org_a", org_role=ORG_MEMBER_ROLE,
    )


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp_path)

    # Isolated per-domain stores under the tmp DB dir.
    support = SupportStore()
    marketing = MarketingStore()
    analytics = AnalyticsStore()
    monkeypatch.setattr(support_store_mod, "support_store", support)
    monkeypatch.setattr(marketing_store_mod, "marketing_store", marketing)
    monkeypatch.setattr(analytics_store_mod, "analytics_store", analytics)

    # Isolated auth service for the org/user admin audit trail. require_super_admin
    # still uses the real global allowlist (the bootstrap super-admin email), so
    # access control is exercised genuinely; only the admin-event READ is isolated.
    svc = FirebaseAuthService(db_path=tmp_path / "auth.db")
    monkeypatch.setattr(activity_routes, "auth_service", svc)

    holder = {"user": None}
    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        if holder["user"] is not None:
            request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(activity_routes.owner_router)
    client = TestClient(app)

    def as_super():
        holder["user"] = _super_admin_user()

    def as_member():
        holder["user"] = _member_user()

    def as_anon():
        holder["user"] = None

    return {
        "client": client, "support": support, "marketing": marketing,
        "analytics": analytics, "svc": svc, "as_super": as_super,
        "as_member": as_member, "as_anon": as_anon,
    }


def _seed_all(env):
    """Seed one safe owner-action event per source plus PHI/free-text-laden source
    rows whose content must never reach the activity feed."""
    support = env["support"]
    marketing = env["marketing"]
    analytics = env["analytics"]
    svc = env["svc"]

    # Support: a real ticket carrying PHI in subject/description, then a triage
    # action (which is what the audit trail records) + an internal note write.
    ticket = support.create_ticket(
        category="bug", priority="high", subject=PHI_SUBJECT,
        description=PHI_DESCRIPTION, org_id="org_a", submitted_by_user_id="cm_1",
        submitted_by_email="reporter@a.test",
    )
    support.update_ticket(
        ticket["ticket_id"], status="resolved", internal_notes=INTERNAL_NOTE,
        internal_notes_set=True, actor_email="owner@hq.test",
    )

    # Marketing: a campaign with a private name + notes, then a safe audit event.
    campaign = marketing.create_campaign(
        name=CAMPAIGN_NAME, status="active", channel="manual", notes=CAMPAIGN_NOTES,
    )
    marketing.record_owner_action(
        "marketing_campaign_created", campaign_id=campaign["id"],
        actor_email="owner@hq.test", detail="active",
    )

    # Analytics: a safe usage event (type + module only).
    analytics.record_event(event_type="module_view", module="housing", org_id="org_a")

    # Org + user admin audit events.
    svc.record_owner_admin_action(
        "owner_org_status_changed", target_type="org", target_id="org_a",
        org_id="org_a", actor_email="owner@hq.test", detail="suspended",
    )
    svc.record_owner_admin_action(
        "owner_user_role_changed", target_type="user", target_id="uid_123",
        org_id="org_a", actor_email="owner@hq.test", detail="org_admin",
    )
    return ticket, campaign


# ── Access control ────────────────────────────────────────────────────────────

def test_activity_requires_auth(env):
    env["as_anon"]()
    res = env["client"].get("/api/owner/activity")
    assert res.status_code == 401


def test_activity_forbids_non_owner(env):
    env["as_member"]()
    res = env["client"].get("/api/owner/activity")
    assert res.status_code == 403


def test_activity_allows_super_admin(env):
    env["as_super"]()
    res = env["client"].get("/api/owner/activity")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "events" in body and isinstance(body["events"], list)
    assert body["stripe_activated"] is False


# ── Normalized aggregation ────────────────────────────────────────────────────

SAFE_KEYS = {
    "id", "source", "action", "actor_email", "org_id",
    "target_type", "target_id", "safe_detail", "created_at",
}


def test_activity_returns_normalized_events_from_all_sources(env):
    _seed_all(env)
    env["as_super"]()
    body = env["client"].get("/api/owner/activity").json()
    events = body["events"]

    sources = {e["source"] for e in events}
    assert {"support", "org", "user", "marketing", "analytics"}.issubset(sources)

    # Every event carries EXACTLY the safe whitelist of keys — nothing extra.
    for e in events:
        assert set(e.keys()) == SAFE_KEYS

    # Spot-check the normalized shape for each owner/admin action source.
    support_evt = next(
        e for e in events
        if e["source"] == "support" and e["action"] == "support_ticket_status_changed"
    )
    assert support_evt["target_type"] == "support_ticket"
    assert support_evt["safe_detail"] == "resolved"

    marketing_evt = next(e for e in events if e["source"] == "marketing")
    assert marketing_evt["action"] == "marketing_campaign_created"
    assert marketing_evt["target_type"] == "campaign"
    assert marketing_evt["safe_detail"] == "active"

    org_evt = next(e for e in events if e["source"] == "org")
    assert org_evt["org_id"] == "org_a"
    assert org_evt["safe_detail"] == "suspended"


def test_activity_limit_enforced(env):
    _seed_all(env)
    env["as_super"]()
    body = env["client"].get("/api/owner/activity?limit=2").json()
    assert len(body["events"]) <= 2
    assert body["limit"] == 2

    # Over-cap requests are clamped, never honored verbatim.
    capped = env["client"].get("/api/owner/activity?limit=99999").json()
    assert capped["limit"] == activity_routes.MAX_LIMIT


def test_activity_newest_first(env):
    _seed_all(env)
    env["as_super"]()
    events = env["client"].get("/api/owner/activity").json()["events"]
    times = [e["created_at"] for e in events if e["created_at"]]
    assert times == sorted(times, reverse=True)


# ── Filters ───────────────────────────────────────────────────────────────────

def test_activity_source_filter(env):
    _seed_all(env)
    env["as_super"]()
    body = env["client"].get("/api/owner/activity?source=marketing").json()
    assert body["events"]
    assert {e["source"] for e in body["events"]} == {"marketing"}


def test_activity_action_filter(env):
    _seed_all(env)
    env["as_super"]()
    body = env["client"].get("/api/owner/activity?action=support_ticket_status_changed").json()
    assert body["events"]
    assert {e["action"] for e in body["events"]} == {"support_ticket_status_changed"}


def test_activity_org_filter(env):
    _seed_all(env)
    env["as_super"]()
    body = env["client"].get("/api/owner/activity?org_id=org_a").json()
    assert body["events"]
    assert all(e["org_id"] == "org_a" for e in body["events"])


def test_activity_actor_filter_substring(env):
    _seed_all(env)
    env["as_super"]()
    body = env["client"].get("/api/owner/activity?actor_email=OWNER@hq").json()
    assert body["events"]
    assert all("owner@hq" in (e["actor_email"] or "").lower() for e in body["events"])


def test_activity_unknown_source_filter_ignored(env):
    _seed_all(env)
    env["as_super"]()
    body = env["client"].get("/api/owner/activity?source=__nope__").json()
    # Unknown source → filter ignored, full feed returned (not an error / empty).
    assert body["events"]


# ── Safety: no PHI / free text ever leaks ─────────────────────────────────────

def test_activity_never_returns_unsafe_text(env):
    _seed_all(env)
    env["as_super"]()
    raw = env["client"].get("/api/owner/activity?limit=200").text

    for needle in (
        PHI_SUBJECT, PHI_DESCRIPTION, INTERNAL_NOTE, CAMPAIGN_NAME, CAMPAIGN_NOTES,
        "Jane", "SSN", "DOB", "diagnosis", "1990-01-01", "record",
    ):
        assert needle not in raw, f"unsafe text leaked into activity feed: {needle!r}"


def test_activity_detail_only_safe_enums(env):
    _seed_all(env)
    env["as_super"]()
    events = env["client"].get("/api/owner/activity?limit=200").json()["events"]
    # safe_detail must be a short enum value or None — never free text.
    allowed_details = {None, "resolved", "active", "suspended", "org_admin"}
    for e in events:
        assert e["safe_detail"] in allowed_details
