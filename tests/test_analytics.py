"""Owner Analytics + Usage Tracking foundation tests.

Covers the analytics store sanitization, the authenticated ``POST
/api/analytics/event`` endpoint, and the super-admin-only ``GET
/api/owner/analytics/summary`` endpoint. The auth service points at a tmp
auth.db and ``DB_DIR`` is repointed at the tmp dir so the analytics + clients
SQLite files are throwaway. No Stripe env var is required and no Stripe code is
exercised.
"""
import json
import sqlite3
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.analytics.routes as analytics_routes
import backend.analytics.store as analytics_store_mod
import backend.auth.super_admin_routes as sa_routes
import backend.billing.routes as billing_routes
import backend.shared.db_path as db_path_mod
from backend.analytics.store import (
    AnalyticsStore,
    normalize_window_days,
    sanitize_metadata,
)
from backend.auth.service import (
    AuthenticatedUser,
    FirebaseAuthService,
    ORG_ADMIN_ROLE,
    ORG_MEMBER_ROLE,
)
from backend.shared.tenancy import DEFAULT_ORG_ID

SUPER_EMAIL = "blackulaphotography@gmail.com"
PHI_KEYS = ("first_name", "last_name", "client_name", "ssn", "dob", "diagnosis", "note")
SECRET_KEYS = ("sk_live", "sk_test", "whsec_", "api_key", "secret_key")


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
    # Repoint every DB at the tmp dir (analytics.db, auth.db, core_clients.db).
    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp_path)

    svc = FirebaseAuthService(db_path=tmp_path / "auth.db")
    monkeypatch.setattr(sa_routes, "auth_service", svc)
    monkeypatch.setattr(billing_routes, "auth_service", svc)
    monkeypatch.setattr(analytics_routes, "auth_service", svc)

    # Fresh analytics store bound to the tmp DB_DIR (resolves path at call time).
    store = AnalyticsStore()
    monkeypatch.setattr(analytics_store_mod, "analytics_store", store)
    monkeypatch.setattr(analytics_routes, "analytics_store", store)

    # Two orgs with internal plans set (no Stripe).
    svc.upsert_profile_from_token(_token("admin_a", "admin_a@a.test", "Admin A"))
    oa = svc.create_organization("admin_a", "Org A", "case_management_agency").org_id
    svc.upsert_profile_from_token(_token("m_a", "m_a@a.test", "Member A"))
    inv = svc.create_invite(oa, "m_a@a.test", ORG_MEMBER_ROLE, invited_by="admin_a")
    svc.accept_invite("m_a", inv["token"])
    svc.set_org_billing(oa, plan_code="team", billing_status="active")  # 2 active users

    svc.upsert_profile_from_token(_token("admin_b", "admin_b@b.test", "Admin B"))
    ob = svc.create_organization("admin_b", "Org B", "sober_living").org_id
    svc.set_org_billing(ob, plan_code="individual", billing_status="trialing")  # 1 user

    # tmp core_clients.db with client COUNTS only.
    with sqlite3.connect(tmp_path / "core_clients.db") as conn:
        conn.execute("CREATE TABLE clients (client_id TEXT PRIMARY KEY, org_id TEXT)")
        conn.executemany("INSERT INTO clients VALUES (?,?)", [
            ("c1", oa), ("c2", oa), ("c3", ob),
        ])
        conn.commit()

    holder = {"user": None}
    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        if holder["user"] is not None:
            request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(analytics_routes.event_router)
    app.include_router(analytics_routes.owner_router)
    client = TestClient(app)

    def as_user(uid):
        holder["user"] = svc.get_profile_by_uid(uid)

    def as_super():
        holder["user"] = _super_admin_user()

    return {"svc": svc, "store": store, "client": client, "holder": holder,
            "as_user": as_user, "as_super": as_super, "oa": oa, "ob": ob}


# ── Store-level sanitization (pure, no DB) ───────────────────────────────────

def test_sanitize_strips_phi_keys():
    clean, dropped = sanitize_metadata({
        "first_name": "Jane",
        "client_name": "John Doe",
        "ssn": "111-22-3333",
        "diagnosis": "x",
        "note": "private",
        "tab": "overview",      # safe
        "count": 3,             # safe
    })
    assert clean == {"tab": "overview", "count": 3}
    for k in ("first_name", "client_name", "ssn", "diagnosis", "note"):
        assert k in dropped
        assert k not in clean


def test_sanitize_drops_nested_and_caps_length():
    clean, _ = sanitize_metadata({
        "nested": {"a": 1},
        "list": [1, 2],
        "long": "x" * 999,
    })
    assert "nested" not in clean and "list" not in clean
    assert len(clean["long"]) <= 200


# ── Event endpoint ───────────────────────────────────────────────────────────

def test_event_requires_auth(env):
    c = env["client"]
    env["holder"]["user"] = None
    assert c.post("/api/analytics/event", json={"event_type": "module_view"}).status_code == 401


def test_event_creation_persists_and_derives_identity(env):
    c = env["client"]
    env["as_user"]("admin_a")
    r = c.post("/api/analytics/event", json={
        "event_type": "module_view", "module": "dashboard", "route": "/",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True and body["event_id"] >= 1

    # Identity derived from token, not the body.
    with sqlite3.connect(env["store"]._db_path()) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM analytics_events").fetchone()
    assert row["module"] == "dashboard"
    assert row["org_id"] == env["oa"]
    assert row["case_manager_id"] == env["svc"].get_profile_by_uid("admin_a").case_manager_id


def test_event_rejects_unknown_event_name(env):
    c = env["client"]
    env["as_user"]("admin_a")
    r = c.post("/api/analytics/event", json={"event_type": "definitely_not_real"})
    assert r.status_code == 422
    assert env["store"].total_events() == 0


def test_event_strips_phi_metadata(env):
    c = env["client"]
    env["as_user"]("admin_a")
    r = c.post("/api/analytics/event", json={
        "event_type": "feature_use",
        "module": "case_management",
        "metadata": {
            "client_name": "John Doe",
            "ssn": "111-22-3333",
            "note_text": "confidential",
            "tab": "timeline",   # safe survivor
        },
    })
    assert r.status_code == 200
    with sqlite3.connect(env["store"]._db_path()) as conn:
        row = conn.execute("SELECT metadata_json FROM analytics_events").fetchone()
    blob = (row[0] or "").lower()
    assert "john doe" not in blob and "111-22-3333" not in blob
    assert not any(k in blob for k in PHI_KEYS)
    assert "timeline" in blob  # the safe key survived


def test_event_captures_marketing_attribution(env):
    c = env["client"]
    env["as_user"]("admin_a")
    c.post("/api/analytics/event", json={
        "event_type": "page_view", "module": "owner",
        "source": "google", "medium": "cpc", "campaign": "launch",
    })
    assert env["store"].marketing_source_breakdown() == {"google": 1}


# ── Owner summary authorization ──────────────────────────────────────────────

def test_summary_unauthenticated_401(env):
    c = env["client"]
    env["holder"]["user"] = None
    assert c.get("/api/owner/analytics/summary").status_code == 401


def test_summary_requires_super_admin(env):
    c = env["client"]
    env["as_user"]("admin_a")  # org admin, not platform owner
    assert c.get("/api/owner/analytics/summary").status_code == 403


# ── Owner summary content ────────────────────────────────────────────────────

def test_summary_empty_state_is_stable(env):
    c = env["client"]
    env["as_super"]()
    body = c.get("/api/owner/analytics/summary").json()
    assert body["success"] is True
    # Org A + Org B + the auto-created default org.
    assert body["total_orgs"] == 3
    assert body["total_clients"] == 3
    assert body["total_events"] == 0
    assert body["top_modules"] == []                 # honest empty state
    assert body["marketing_source_breakdown"] == {}  # honest empty state
    # least_used still lists known modules (all at zero) so coverage is visible.
    assert len(body["least_used_modules"]) > 0
    assert all(m["count"] == 0 for m in body["least_used_modules"])


def test_summary_estimated_mrr_uses_internal_plan_fields(env):
    c = env["client"]
    env["as_super"]()
    body = c.get("/api/owner/analytics/summary").json()
    # Org A: team plan, 2 active users → base 99 (within 3 included) = 99.
    # Org B: individual plan, 1 user → 49.
    # Default org: free_trial → $0.  Total = 148. No Stripe consulted.
    assert body["estimated_mrr"] == 148.0
    assert body["estimated_mrr_source"] == "internal_plan_fields"
    assert body["plan_breakdown"] == {"team": 1, "individual": 1, "free_trial": 1}
    # Org A active; Org B + the default org default to trialing.
    assert body["billing_status_breakdown"] == {"active": 1, "trialing": 2}
    assert body["stripe_activated"] is False
    # No Stripe secret value anywhere in the response.
    blob = json.dumps(body).lower()
    assert not any(k in blob for k in SECRET_KEYS)


def test_summary_top_modules_after_events(env):
    c = env["client"]
    env["as_user"]("admin_a")
    for _ in range(3):
        c.post("/api/analytics/event", json={"event_type": "module_view", "module": "dashboard"})
    c.post("/api/analytics/event", json={"event_type": "module_view", "module": "housing"})

    env["as_super"]()
    body = c.get("/api/owner/analytics/summary").json()
    assert body["total_events"] == 4
    assert body["top_modules"][0] == {"module": "dashboard", "count": 3}
    assert body["module_usage"]["housing"] == 1
    # A never-visited known module remains in least_used at zero.
    assert any(m["module"] == "fmla" and m["count"] == 0 for m in body["least_used_modules"])


# ── Polish: window filtering, attribution, recent feed, ad readiness ─────────

def test_normalize_window_days_accepts_known_and_falls_back():
    assert normalize_window_days("7") == 7
    assert normalize_window_days("7d") == 7
    assert normalize_window_days(30) == 30
    assert normalize_window_days("30d") == 30
    # Anything unrecognized → all-time (None), never an error.
    assert normalize_window_days("all") is None
    assert normalize_window_days("") is None
    assert normalize_window_days(None) is None
    assert normalize_window_days("90") is None
    assert normalize_window_days("garbage") is None


def test_window_filters_out_old_events(env):
    """Events older than the window are excluded; recent ones are kept."""
    store = env["store"]
    # One old event (40 days ago) and one fresh event (today).
    store.record_event(event_type="module_view", module="housing")
    with sqlite3.connect(store._db_path()) as conn:
        old = (datetime.utcnow() - timedelta(days=40)).isoformat()
        conn.execute(
            "INSERT INTO analytics_events (event_type, module, created_at) VALUES (?,?,?)",
            ("module_view", "fmla", old),
        )
        conn.commit()

    assert store.total_events() == 2                       # all-time
    assert store.total_events(since_days=30) == 1          # 30d window drops the old one
    assert store.total_events(since_days=7) == 1
    assert store.module_usage(since_days=30)["fmla"] == 0  # old fmla event excluded
    assert store.module_usage()["fmla"] == 1               # but present all-time


def test_summary_window_param_is_echoed_and_applied(env):
    c = env["client"]
    env["as_user"]("admin_a")
    c.post("/api/analytics/event", json={"event_type": "module_view", "module": "owner"})
    # Backdate it beyond the 7-day window directly in the store.
    with sqlite3.connect(env["store"]._db_path()) as conn:
        conn.execute(
            "UPDATE analytics_events SET created_at = ?",
            ((datetime.utcnow() - timedelta(days=10)).isoformat(),),
        )
        conn.commit()

    env["as_super"]()
    all_body = c.get("/api/owner/analytics/summary?window=all").json()
    win_body = c.get("/api/owner/analytics/summary?window=7").json()
    assert all_body["window"] == "all" and all_body["total_events"] == 1
    assert win_body["window"] == "7d" and win_body["total_events"] == 0
    # A bogus window value falls back to all-time rather than erroring.
    bogus = c.get("/api/owner/analytics/summary?window=nonsense")
    assert bogus.status_code == 200 and bogus.json()["window"] == "all"


def test_summary_marketing_attribution_breakdowns(env):
    c = env["client"]
    env["as_user"]("admin_a")
    c.post("/api/analytics/event", json={
        "event_type": "page_view", "module": "owner",
        "source": "google", "medium": "cpc", "campaign": "launch",
    })
    c.post("/api/analytics/event", json={
        "event_type": "page_view", "module": "owner",
        "source": "google", "medium": "email", "campaign": "launch",
    })
    env["as_super"]()
    body = c.get("/api/owner/analytics/summary").json()
    attribution = body["marketing_attribution"]
    assert attribution["source"] == {"google": 2}
    assert attribution["medium"] == {"cpc": 1, "email": 1}
    assert attribution["campaign"] == {"launch": 2}
    # Back-compat: the source-only key still mirrors the source breakdown.
    assert body["marketing_source_breakdown"] == {"google": 2}


def test_summary_recent_events_feed_is_safe(env):
    """The latest-events feed exposes only event_type/module/timestamp — never
    route, ids, referrer, or metadata."""
    c = env["client"]
    env["as_user"]("admin_a")
    c.post("/api/analytics/event", json={
        "event_type": "module_view", "module": "housing", "route": "/client/secret-123",
        "metadata": {"tab": "overview"},
    })
    env["as_super"]()
    body = c.get("/api/owner/analytics/summary").json()
    feed = body["recent_events"]
    assert len(feed) == 1
    event = feed[0]
    assert set(event.keys()) == {"event_type", "module", "created_at"}
    blob = json.dumps(feed).lower()
    assert "secret-123" not in blob and "route" not in blob and "overview" not in blob


def test_summary_active_event_identity_counts(env):
    c = env["client"]
    env["as_user"]("admin_a")
    c.post("/api/analytics/event", json={"event_type": "module_view", "module": "owner"})
    env["as_user"]("m_a")
    c.post("/api/analytics/event", json={"event_type": "module_view", "module": "owner"})
    env["as_super"]()
    body = c.get("/api/owner/analytics/summary").json()
    # admin_a and m_a share Org A → 1 active org, 2 distinct active users.
    assert body["active_event_orgs"] == 1
    assert body["active_event_users"] == 2


def test_summary_ad_readiness_is_placeholder(env):
    c = env["client"]
    env["as_super"]()
    body = c.get("/api/owner/analytics/summary").json()
    ad = body["ad_readiness"]
    assert ad["source"] == "not_connected"
    # No fabricated numbers — every metric is explicitly null until wired up.
    for key in ("landing_page_visits", "campaign_conversions", "cost_per_signup", "ad_spend"):
        assert ad[key] is None
