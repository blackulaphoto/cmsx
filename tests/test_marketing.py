"""Owner Marketing + Campaign Tracker v1 tests.

Covers the marketing store (amount coercion, status/channel validation, summary
math, itemized spend log, utm correlation) and the super-admin-only owner
endpoints (``GET/POST/PATCH /api/owner/marketing/campaigns``,
``GET /api/owner/marketing/summary``). ``DB_DIR`` is repointed at a tmp dir so the
marketing + analytics SQLite files are throwaway. No Stripe env var is required
and no Stripe / external ad-platform code is exercised anywhere.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.marketing.routes as marketing_routes
import backend.marketing.store as marketing_store_mod
import backend.analytics.routes as analytics_routes
import backend.analytics.store as analytics_store_mod
import backend.shared.db_path as db_path_mod
from backend.marketing.store import (
    MarketingStore,
    normalize_channel,
    normalize_status,
    _coerce_amount,
)
from backend.analytics.store import AnalyticsStore
from backend.auth.service import (
    AuthenticatedUser,
    FirebaseAuthService,
    ORG_ADMIN_ROLE,
    ORG_MEMBER_ROLE,
)
from backend.shared.tenancy import DEFAULT_ORG_ID

SUPER_EMAIL = "blackulaphotography@gmail.com"
PHI_TOKENS = ("john doe", "123-45-6789", "1990-01-01", "jane@example.com")


def _token(uid, email, name="User"):
    return {"uid": uid, "email": email, "name": name}


def _super_admin_user():
    return AuthenticatedUser(
        firebase_uid="owner", email=SUPER_EMAIL, full_name="Owner", role="admin",
        case_manager_id="cm_owner", auth_provider="test", is_active=True,
        org_id=DEFAULT_ORG_ID, org_role=ORG_ADMIN_ROLE,
    )


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp_path)

    svc = FirebaseAuthService(db_path=tmp_path / "auth.db")

    store = MarketingStore()
    monkeypatch.setattr(marketing_store_mod, "marketing_store", store)
    monkeypatch.setattr(marketing_routes, "marketing_store", store)

    # Fresh analytics store on the same tmp DB_DIR so UTM correlation reads real
    # tracked events (seeded per-test), never fabricated numbers.
    analytics = AnalyticsStore()
    monkeypatch.setattr(analytics_store_mod, "analytics_store", analytics)
    monkeypatch.setattr(analytics_routes, "analytics_store", analytics)
    monkeypatch.setattr(marketing_routes, "analytics_store", analytics)

    # A normal org + admin to exercise the non-owner 403 path.
    svc.upsert_profile_from_token(_token("admin_a", "admin_a@a.test", "Admin A"))
    svc.create_organization("admin_a", "Org A", "case_management_agency")
    svc.upsert_profile_from_token(_token("m_a", "m_a@a.test", "Member A"))

    holder = {"user": None}
    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        if holder["user"] is not None:
            request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(marketing_routes.owner_router)
    client = TestClient(app)

    def as_user(uid):
        holder["user"] = svc.get_profile_by_uid(uid)

    def as_super():
        holder["user"] = _super_admin_user()

    return {"svc": svc, "store": store, "analytics": analytics, "client": client,
            "holder": holder, "as_user": as_user, "as_super": as_super}


# ── Store-level helpers (pure / DB) ──────────────────────────────────────────

def test_coerce_amount_clamps_and_rounds():
    assert _coerce_amount(None) is None
    assert _coerce_amount("") is None
    assert _coerce_amount("not a number") is None
    assert _coerce_amount(-50) == 0.0
    assert _coerce_amount("12.349") == 12.35
    assert _coerce_amount(10**12) == 1_000_000_000.0


def test_normalize_status_and_channel():
    assert normalize_status("ACTIVE") == "active"
    assert normalize_status("bogus") is None
    assert normalize_channel("Google_Ads") == "google_ads"
    assert normalize_channel("myspace") is None


def test_store_create_defaults_and_caps(env):
    store = env["store"]
    c = store.create_campaign(name="x" * 500, status="weird", channel="weird")
    # Invalid status/channel fall back to safe defaults; name is capped.
    assert c["status"] == "draft"
    assert c["channel"] == "manual"
    assert len(c["name"]) <= 120


def test_store_spend_entries_sum(env):
    store = env["store"]
    c = store.create_campaign(name="Launch")
    store.add_spend_entry(c["id"], amount=100, label="day 1")
    store.add_spend_entry(c["id"], amount="49.999", label="day 2")
    assert store.campaign_logged_spend(c["id"]) == 150.0


def test_store_summary_empty_state(env):
    body = env["store"].summary()
    assert body["total_campaigns"] == 0
    assert body["active_campaigns"] == 0
    assert body["total_budget"] == 0.0
    assert body["total_spend"] == 0.0
    # Breakdowns seed every known value at zero.
    assert body["by_status"]["active"] == 0
    assert body["by_channel"]["google_ads"] == 0


def test_store_summary_sums_budget_and_spend(env):
    store = env["store"]
    store.create_campaign(name="A", status="active", channel="google_ads",
                          budget_amount=1000, spend_amount=250)
    store.create_campaign(name="B", status="paused", channel="meta_ads",
                          budget_amount=500, spend_amount=100)
    body = store.summary()
    assert body["total_campaigns"] == 2
    assert body["active_campaigns"] == 1
    assert body["total_budget"] == 1500.0
    assert body["total_spend"] == 350.0
    assert body["by_status"]["active"] == 1
    assert body["by_channel"]["meta_ads"] == 1


# ── Owner endpoints: authorization ───────────────────────────────────────────

def test_list_unauthenticated_401(env):
    c = env["client"]
    env["holder"]["user"] = None
    assert c.get("/api/owner/marketing/campaigns").status_code == 401


def test_summary_unauthenticated_401(env):
    c = env["client"]
    env["holder"]["user"] = None
    assert c.get("/api/owner/marketing/summary").status_code == 401


def test_create_unauthenticated_401(env):
    c = env["client"]
    env["holder"]["user"] = None
    r = c.post("/api/owner/marketing/campaigns", json={"name": "X"})
    assert r.status_code == 401


def test_endpoints_require_super_admin(env):
    c = env["client"]
    env["as_user"]("admin_a")  # org admin, not platform owner
    assert c.get("/api/owner/marketing/campaigns").status_code == 403
    assert c.get("/api/owner/marketing/summary").status_code == 403
    assert c.post("/api/owner/marketing/campaigns", json={"name": "X"}).status_code == 403


# ── Owner endpoints: create / list / update ──────────────────────────────────

def test_owner_create_and_list_campaign(env):
    c = env["client"]
    env["as_super"]()
    r = c.post("/api/owner/marketing/campaigns", json={
        "name": "Launch Test", "status": "active", "channel": "google_ads",
        "utm_source": "google", "utm_medium": "cpc", "utm_campaign": "launch_test",
        "landing_page_url": "https://example.com/launch",
        "budget_amount": 1000, "spend_amount": 250, "notes": "Q3 paid push",
    })
    assert r.status_code == 200
    camp = r.json()["campaign"]
    assert camp["id"] >= 1
    assert camp["status"] == "active" and camp["channel"] == "google_ads"
    assert camp["budget_amount"] == 1000 and camp["spend_amount"] == 250

    body = c.get("/api/owner/marketing/campaigns").json()
    assert body["success"] is True and body["count"] == 1
    assert body["campaigns"][0]["name"] == "Launch Test"
    assert "google_ads" in body["channels"] and "active" in body["statuses"]


def test_owner_create_rejects_unknown_status(env):
    c = env["client"]
    env["as_super"]()
    r = c.post("/api/owner/marketing/campaigns", json={"name": "X", "status": "live"})
    assert r.status_code == 422
    assert "allowed_statuses" in r.json()
    assert env["store"].summary()["total_campaigns"] == 0


def test_owner_create_rejects_unknown_channel(env):
    c = env["client"]
    env["as_super"]()
    r = c.post("/api/owner/marketing/campaigns", json={"name": "X", "channel": "myspace"})
    assert r.status_code == 422
    assert "allowed_channels" in r.json()
    assert env["store"].summary()["total_campaigns"] == 0


def test_owner_create_length_caps_name(env):
    c = env["client"]
    env["as_super"]()
    # Name over the 120-char Field cap is a 422 at the model layer.
    r = c.post("/api/owner/marketing/campaigns", json={"name": "x" * 500})
    assert r.status_code == 422


def test_owner_create_rejects_negative_amount(env):
    c = env["client"]
    env["as_super"]()
    # Negative budget is rejected by the model (ge=0).
    r = c.post("/api/owner/marketing/campaigns", json={"name": "X", "budget_amount": -5})
    assert r.status_code == 422


def test_owner_create_rejects_phi_in_notes(env):
    c = env["client"]
    env["as_super"]()
    r = c.post("/api/owner/marketing/campaigns", json={
        "name": "Launch", "notes": "Targeting John Doe SSN 123-45-6789",
    })
    assert r.status_code == 422
    assert r.json()["phi_risk"]
    assert env["store"].summary()["total_campaigns"] == 0


def test_owner_create_rejects_phi_in_name(env):
    c = env["client"]
    env["as_super"]()
    r = c.post("/api/owner/marketing/campaigns", json={
        "name": "Reach jane@example.com", "channel": "email",
    })
    assert r.status_code == 422
    assert env["store"].summary()["total_campaigns"] == 0


def test_owner_update_campaign(env):
    c = env["client"]
    env["as_super"]()
    cid = c.post("/api/owner/marketing/campaigns", json={
        "name": "A", "status": "draft", "spend_amount": 0,
    }).json()["campaign"]["id"]

    r = c.patch(f"/api/owner/marketing/campaigns/{cid}", json={
        "status": "active", "spend_amount": 400, "budget_amount": 1000,
        "notes": "now live",
    })
    assert r.status_code == 200
    camp = r.json()["campaign"]
    assert camp["status"] == "active"
    assert camp["spend_amount"] == 400 and camp["budget_amount"] == 1000
    assert camp["notes"] == "now live"


def test_owner_update_rejects_unknown_status(env):
    c = env["client"]
    env["as_super"]()
    cid = c.post("/api/owner/marketing/campaigns", json={"name": "A"}).json()["campaign"]["id"]
    r = c.patch(f"/api/owner/marketing/campaigns/{cid}", json={"status": "live"})
    assert r.status_code == 422


def test_owner_update_rejects_phi(env):
    c = env["client"]
    env["as_super"]()
    cid = c.post("/api/owner/marketing/campaigns", json={"name": "A"}).json()["campaign"]["id"]
    r = c.patch(f"/api/owner/marketing/campaigns/{cid}", json={
        "notes": "client DOB 1990-01-01",
    })
    assert r.status_code == 422


def test_owner_update_missing_campaign_404(env):
    c = env["client"]
    env["as_super"]()
    r = c.patch("/api/owner/marketing/campaigns/9999", json={"status": "active"})
    assert r.status_code == 404


# ── Owner summary: math + UTM correlation + honest placeholders ──────────────

def test_owner_summary_empty_state(env):
    c = env["client"]
    env["as_super"]()
    body = c.get("/api/owner/marketing/summary").json()
    assert body["success"] is True
    assert body["total_campaigns"] == 0
    assert body["active_campaigns"] == 0
    assert body["total_budget"] == 0.0
    assert body["total_spend"] == 0.0
    # Honest performance placeholders — nothing fabricated.
    perf = body["performance"]
    assert perf["landing_page_visits"] is None
    assert perf["signups"] is None
    assert perf["conversions"] is None
    assert perf["cost_per_signup"] is None
    assert body["ad_platforms_connected"] is False
    assert body["stripe_activated"] is False


def test_owner_summary_with_budget_and_spend(env):
    c = env["client"]
    env["as_super"]()
    c.post("/api/owner/marketing/campaigns", json={
        "name": "A", "status": "active", "channel": "google_ads",
        "budget_amount": 2000, "spend_amount": 600,
    })
    c.post("/api/owner/marketing/campaigns", json={
        "name": "B", "status": "paused", "channel": "meta_ads",
        "budget_amount": 1000, "spend_amount": 150,
    })
    body = c.get("/api/owner/marketing/summary").json()
    assert body["total_campaigns"] == 2
    assert body["active_campaigns"] == 1
    assert body["total_budget"] == 3000.0
    assert body["total_spend"] == 750.0
    assert body["by_channel"]["google_ads"] == 1
    # Even with spend, cost_per_signup stays null because no real signup source exists.
    assert body["performance"]["cost_per_signup"] is None


def test_owner_summary_utm_attribution_from_analytics(env):
    c = env["client"]
    # Seed real tracked analytics events with UTM data (no fabrication).
    env["analytics"].record_event(event_type="page_view", source="google",
                                  medium="cpc", campaign="launch_test")
    env["analytics"].record_event(event_type="page_view", source="google",
                                  medium="cpc", campaign="launch_test")
    env["analytics"].record_event(event_type="page_view", source="meta",
                                  medium="paid", campaign="other_test")

    env["as_super"]()
    # A campaign whose utm_campaign matches the tracked events.
    c.post("/api/owner/marketing/campaigns", json={
        "name": "Launch", "utm_campaign": "launch_test",
    })

    body = c.get("/api/owner/marketing/summary").json()
    attribution = body["utm_attribution"]
    assert attribution["campaign"]["launch_test"] == 2
    assert attribution["source"]["google"] == 2
    # Owner campaign correlated to its tracked visits by utm_campaign.
    assert body["campaign_utm_visits"]["launch_test"] == 2
    # A campaign value with no owner campaign is NOT in the correlation map.
    assert "other_test" not in body["campaign_utm_visits"]


def test_owner_summary_stores_no_phi_and_no_stripe(env):
    """Defense-in-depth: a PHI-laden campaign is rejected, so nothing unsafe is
    ever persisted, and the summary never reports Stripe as active."""
    c = env["client"]
    env["as_super"]()
    r = c.post("/api/owner/marketing/campaigns", json={
        "name": "Bad", "notes": "John Doe 123-45-6789",
    })
    assert r.status_code == 422  # PHI rejected before any write
    # Confirm nothing landed — the store sees zero rows (no PHI persisted anywhere).
    rows = env["store"].list_campaigns()
    assert rows == []
    blob = " ".join(" ".join(str(v) for v in row.values()) for row in rows).lower()
    assert not any(tok in blob for tok in PHI_TOKENS)
    assert c.get("/api/owner/marketing/summary").json()["stripe_activated"] is False
