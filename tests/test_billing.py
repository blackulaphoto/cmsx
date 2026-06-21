"""Billing + plan-limits foundation tests (Stripe-disabled).

Covers the pure pricing helpers, the org-scoped ``GET /api/billing/status``
endpoint (token-derived org, never client-supplied), and the super-admin-only
manual billing setter. The auth service points at a tmp auth.db; a tmp
core_clients.db supplies active-client counts. No Stripe env var is required.
"""
import json
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.billing.routes as billing_routes
import backend.auth.super_admin_routes as sa_routes
import backend.shared.db_path as db_path_mod
from backend.billing import plans as billing_plans
from backend.auth.service import (
    AuthenticatedUser,
    FirebaseAuthService,
    ORG_ADMIN_ROLE,
    ORG_MEMBER_ROLE,
)
from backend.shared.tenancy import DEFAULT_ORG_ID

SUPER_EMAIL = "blackulaphotography@gmail.com"
PHI_KEYS = ("first_name", "last_name", "date_of_birth", "dob", "ssn", "diagnosis", "client_name")
SECRET_KEYS = ("sk_live", "sk_test", "stripe_secret", "api_key", "secret_key", "whsec_")


def _token(uid, email, name="User"):
    return {"uid": uid, "email": email, "name": name}


def _super_admin_user():
    return AuthenticatedUser(
        firebase_uid="owner", email=SUPER_EMAIL, full_name="Owner", role="admin",
        case_manager_id="cm_owner", auth_provider="test", is_active=True,
        org_id=DEFAULT_ORG_ID, org_role=ORG_ADMIN_ROLE,
    )


# ── Pure pricing helpers (no DB, no network, no Stripe) ──────────────────────

@pytest.mark.parametrize("plan_code,users,expected", [
    ("team", 6, 186.0),          # 99 + (6-3)*29
    ("team", 16, 476.0),         # 99 + (16-3)*29
    ("organization", 6, 224.0),  # 199 + (6-5)*25
    ("organization", 16, 474.0), # 199 + (16-5)*25
    ("team", 3, 99.0),           # exactly included
    ("team", 1, 99.0),           # below included — no negative overage
    ("individual", 5, 49.0),     # extra users not allowed → flat base
    ("individual", 1, 49.0),
])
def test_estimate_monthly_price(plan_code, users, expected):
    assert billing_plans.estimate_monthly_price(plan_code, users) == expected


def test_estimate_custom_plan_is_none():
    assert billing_plans.estimate_monthly_price("enterprise", 50) is None


@pytest.mark.parametrize("users,expected", [
    (1, "individual"), (2, "team"), (5, "team"),
    (6, "organization"), (20, "organization"), (21, "enterprise"), (100, "enterprise"),
])
def test_recommend_plan(users, expected):
    assert billing_plans.recommend_plan(users) == expected


def test_compute_limit_status_clients_and_users():
    # individual: 25 client cap, single seat. 30 clients + 2 users → both over.
    over = billing_plans.compute_limit_status("individual", active_users=2, active_clients=30)
    assert over["clients"]["over_limit"] is True
    assert over["users"]["over_limit"] is True
    assert over["over_limit"] is True

    # team: extra seats are billable, not blocked → users never "over_limit".
    team = billing_plans.compute_limit_status("team", active_users=10, active_clients=10)
    assert team["users"]["over_limit"] is False
    assert team["users"]["extra_billable"] is True
    assert team["clients"]["over_limit"] is False

    # within limits everywhere
    ok = billing_plans.compute_limit_status("organization", active_users=5, active_clients=10)
    assert ok["over_limit"] is False


def test_enterprise_has_no_hard_limits():
    ls = billing_plans.compute_limit_status("enterprise", active_users=500, active_clients=10000)
    assert ls["over_limit"] is False


# ── HTTP harness ─────────────────────────────────────────────────────────────

@pytest.fixture
def env(tmp_path, monkeypatch):
    svc = FirebaseAuthService(db_path=tmp_path / "auth.db")
    monkeypatch.setattr(billing_routes, "auth_service", svc)
    monkeypatch.setattr(sa_routes, "auth_service", svc)
    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp_path)

    # Org A: admin + member (2 users). Org B: admin only (1 user).
    svc.upsert_profile_from_token(_token("admin_a", "admin_a@a.test", "Admin A"))
    oa = svc.create_organization("admin_a", "Org A", "case_management_agency").org_id
    svc.upsert_profile_from_token(_token("m_a", "m_a@a.test", "Member A"))
    inv = svc.create_invite(oa, "m_a@a.test", ORG_MEMBER_ROLE, invited_by="admin_a")
    svc.accept_invite("m_a", inv["token"])
    svc.upsert_profile_from_token(_token("admin_b", "admin_b@b.test", "Admin B"))
    ob = svc.create_organization("admin_b", "Org B", "sober_living").org_id

    # tmp core_clients.db: 30 clients for Org A (over the 25 individual cap), 1 for B.
    with sqlite3.connect(tmp_path / "core_clients.db") as conn:
        conn.execute("CREATE TABLE clients (client_id TEXT PRIMARY KEY, org_id TEXT)")
        conn.executemany(
            "INSERT INTO clients VALUES (?,?)",
            [(f"a{i}", oa) for i in range(30)] + [("b1", ob)],
        )
        conn.commit()

    holder = {"user": None}
    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        if holder["user"] is not None:
            request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(billing_routes.router)
    app.include_router(sa_routes.router)
    client = TestClient(app)

    def as_user(uid):
        holder["user"] = svc.get_profile_by_uid(uid)

    def as_super():
        holder["user"] = _super_admin_user()

    return {"svc": svc, "client": client, "holder": holder, "as_user": as_user,
            "as_super": as_super, "oa": oa, "ob": ob}


# ── Billing status (org-scoped reads) ────────────────────────────────────────

def test_unauthenticated_billing_status_401(env):
    env["holder"]["user"] = None
    assert env["client"].get("/api/billing/status").status_code == 401
    assert env["client"].get("/api/billing/plans").status_code == 401


def test_user_sees_own_org_billing(env):
    env["as_user"]("admin_a")
    body = env["client"].get("/api/billing/status").json()
    assert body["success"] is True
    assert body["org_id"] == env["oa"]
    assert body["plan_code"] == "free_trial"          # new org default
    assert body["billing_status"] == "trialing"
    assert body["usage"]["active_users"] == 2          # admin_a + m_a
    assert body["usage"]["active_clients"] == 30
    assert "ai_usage_placeholder" in body["usage"]
    assert body["payments_enabled"] is False
    assert body["stripe_connected"] is False


def test_billing_status_org_scoped_from_token(env):
    """The endpoint takes NO org_id param; each caller sees only their own org,
    so a caller can never read another org's billing by supplying an id."""
    env["as_user"]("admin_a")
    a = env["client"].get("/api/billing/status").json()
    env["as_user"]("admin_b")
    b = env["client"].get("/api/billing/status").json()
    assert a["org_id"] == env["oa"] and b["org_id"] == env["ob"]
    assert a["usage"]["active_clients"] == 30 and b["usage"]["active_clients"] == 1
    # A client-supplied org_id query param is ignored (org comes from the token).
    spoof = env["client"].get(f"/api/billing/status?org_id={env['oa']}").json()
    assert spoof["org_id"] == env["ob"]


def test_limit_status_reflects_plan(env):
    """On the individual plan, Org A's 30 clients exceed the 25 cap → warning."""
    env["svc"].set_org_billing(env["oa"], plan_code="individual", billing_status="active")
    env["as_user"]("admin_a")
    body = env["client"].get("/api/billing/status").json()
    assert body["plan_code"] == "individual"
    assert body["limit_status"]["clients"]["limit"] == 25
    assert body["limit_status"]["clients"]["over_limit"] is True
    assert body["limit_status"]["over_limit"] is True
    assert body["estimated_monthly_price"] == 49.0


def test_billing_status_no_phi_or_secrets(env):
    env["as_user"]("admin_a")
    blob = json.dumps(env["client"].get("/api/billing/status").json()).lower()
    assert not any(k in blob for k in PHI_KEYS)
    assert not any(k in blob for k in SECRET_KEYS)


def test_plans_catalog(env):
    env["as_user"]("admin_a")
    plans = {p["plan_code"]: p for p in env["client"].get("/api/billing/plans").json()["plans"]}
    assert {"free_trial", "individual", "team", "organization", "enterprise"} <= set(plans)
    assert plans["team"]["price"] == 99
    assert plans["enterprise"]["selectable"] is False


# ── Super-admin manual billing setter ────────────────────────────────────────

def test_super_admin_sets_plan_and_status(env):
    env["as_super"]()
    resp = env["client"].post(
        f"/api/super-admin/organizations/{env['ob']}/billing",
        json={"plan_code": "organization", "billing_status": "comped"},
    )
    assert resp.status_code == 200
    billing = resp.json()["billing"]
    assert billing["plan_code"] == "organization"
    assert billing["billing_status"] == "comped"
    # Persisted + visible in the detail drawer.
    detail = env["client"].get(f"/api/super-admin/organizations/{env['ob']}").json()
    assert detail["billing"]["plan_code"] == "organization"
    assert detail["billing"]["billing_status"] == "comped"


def test_super_admin_rejects_invalid_billing_values(env):
    env["as_super"]()
    assert env["client"].post(
        f"/api/super-admin/organizations/{env['ob']}/billing",
        json={"plan_code": "platinum"},
    ).status_code == 400
    assert env["client"].post(
        f"/api/super-admin/organizations/{env['ob']}/billing",
        json={"billing_status": "bankrupt"},
    ).status_code == 400


def test_normal_org_admin_cannot_set_billing(env):
    """admin_a is an org admin (role=admin, org_role=org_admin) but not the
    platform owner — the billing setter is super-admin-only → 403."""
    env["as_user"]("admin_a")
    resp = env["client"].post(
        f"/api/super-admin/organizations/{env['oa']}/billing",
        json={"plan_code": "team"},
    )
    assert resp.status_code == 403


def test_super_admin_org_list_shows_billing(env):
    env["as_super"]()
    body = env["client"].get("/api/super-admin/organizations").json()
    orgs = {o["org_id"]: o for o in body["organizations"]}
    assert orgs[env["oa"]]["plan_code"] == "free_trial"
    assert orgs[env["oa"]]["billing_status"] == "trialing"
    assert "estimated_monthly_price" in orgs[env["oa"]]
    assert "limit_status" in orgs[env["oa"]]
    # No Stripe IDs leak into the super-admin listing.
    blob = json.dumps(body).lower()
    assert not any(k in blob for k in SECRET_KEYS)
