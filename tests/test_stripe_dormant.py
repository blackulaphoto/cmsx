"""Stripe DORMANT integration tests.

Verifies that with the activation flags off (the production default):
  * checkout/portal endpoints return a disabled 503 and make NO Stripe call;
  * billing status never exposes the Stripe secret key value;
  * missing price env vars are reported clearly;
  * the webhook scaffold never mutates billing.

The Stripe boundary (``stripe_integration``) is monkeypatched with a sentinel
that raises if invoked, so "does not call Stripe" is asserted structurally.
"""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.billing.routes as billing_routes
import backend.billing.stripe_config as stripe_config
import backend.billing.stripe_integration as stripe_integration
import backend.shared.db_path as db_path_mod
from backend.auth.service import AuthenticatedUser, FirebaseAuthService, ORG_ADMIN_ROLE
from backend.shared.tenancy import DEFAULT_ORG_ID

FAKE_SECRET = "sk_test_THIS_MUST_NEVER_LEAK_123456"

ALL_FLAGS = [
    stripe_config.BILLING_ENABLED_ENV,
    stripe_config.CHECKOUT_ENABLED_ENV,
    stripe_config.PORTAL_ENABLED_ENV,
    stripe_config.WEBHOOKS_ENABLED_ENV,
]


def _token(uid, email, name="User"):
    return {"uid": uid, "email": email, "name": name}


@pytest.fixture(autouse=True)
def _clear_stripe_env(monkeypatch):
    """Start every test from a clean, fully-dormant env."""
    for name in ALL_FLAGS + stripe_config.REQUIRED_PRICE_ENV_VARS + [
        stripe_config.STRIPE_SECRET_KEY_ENV,
        stripe_config.STRIPE_WEBHOOK_SECRET_ENV,
    ]:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def env(tmp_path, monkeypatch):
    svc = FirebaseAuthService(db_path=tmp_path / "auth.db")
    monkeypatch.setattr(billing_routes, "auth_service", svc)
    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp_path)

    svc.upsert_profile_from_token(_token("admin_a", "admin_a@a.test", "Admin A"))
    oa = svc.create_organization("admin_a", "Org A", "case_management_agency").org_id

    # Sentinel: any Stripe call must fail the test loudly.
    def _boom(*args, **kwargs):  # noqa: ANN001
        raise AssertionError("Stripe API was called while dormant")

    monkeypatch.setattr(stripe_integration, "create_subscription_checkout", _boom)
    monkeypatch.setattr(stripe_integration, "create_billing_portal", _boom)

    holder = {"user": None}
    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        if holder["user"] is not None:
            request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(billing_routes.router)
    client = TestClient(app)

    def as_user(uid):
        holder["user"] = svc.get_profile_by_uid(uid)

    return {"svc": svc, "client": client, "holder": holder, "as_user": as_user, "oa": oa}


# ── Config readiness ─────────────────────────────────────────────────────────

def test_default_mode_is_dormant():
    r = stripe_config.readiness()
    assert r["mode"] == "dormant"
    assert r["billing_enabled"] is False
    assert r["checkout_enabled"] is False
    assert r["portal_enabled"] is False
    assert r["webhooks_enabled"] is False
    assert stripe_config.checkout_effective_enabled() is False
    assert stripe_config.portal_effective_enabled() is False


def test_missing_price_env_vars_reported(monkeypatch):
    monkeypatch.setenv("STRIPE_PRICE_INDIVIDUAL_MONTHLY", "price_ind")
    missing = stripe_config.missing_price_env_vars()
    assert "STRIPE_PRICE_INDIVIDUAL_MONTHLY" not in missing
    assert "STRIPE_PRICE_TEAM_BASE_MONTHLY" in missing
    assert stripe_config.all_required_prices_configured() is False
    # All five present → none missing.
    for name in stripe_config.REQUIRED_PRICE_ENV_VARS:
        monkeypatch.setenv(name, "price_x")
    assert stripe_config.missing_price_env_vars() == []
    assert stripe_config.all_required_prices_configured() is True


def test_secret_configured_is_boolean_only(monkeypatch):
    assert stripe_config.stripe_secret_configured() is False
    monkeypatch.setenv("STRIPE_SECRET_KEY", FAKE_SECRET)
    assert stripe_config.stripe_secret_configured() is True
    # The readiness report carries the boolean, never the value.
    assert FAKE_SECRET not in json.dumps(stripe_config.readiness())


def test_connected_requires_secret_and_all_prices(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", FAKE_SECRET)
    for name in stripe_config.REQUIRED_PRICE_ENV_VARS:
        monkeypatch.setenv(name, "price_x")
    assert stripe_config.stripe_connected() is True
    # Still dormant until billing is enabled.
    assert stripe_config.mode() == "dormant"
    monkeypatch.setenv("STRIPE_BILLING_ENABLED", "true")
    assert stripe_config.mode() == "active"


# ── Endpoint behavior in dormant mode ────────────────────────────────────────

def test_checkout_disabled_returns_503_and_no_stripe_call(env):
    env["as_user"]("admin_a")
    resp = env["client"].post("/api/billing/checkout-session", json={"plan_code": "team"})
    assert resp.status_code == 503
    body = resp.json()
    assert body["enabled"] is False
    assert body["detail"] == "Stripe checkout is not enabled."
    # The sentinel would have raised AssertionError if Stripe were called.


def test_portal_disabled_returns_503_and_no_stripe_call(env):
    env["as_user"]("admin_a")
    resp = env["client"].post("/api/billing/portal-session", json={})
    assert resp.status_code == 503
    assert resp.json()["enabled"] is False
    assert resp.json()["detail"] == "Stripe billing portal is not enabled."


def test_checkout_requires_auth(env):
    env["holder"]["user"] = None
    assert env["client"].post("/api/billing/checkout-session", json={"plan_code": "team"}).status_code == 401


def test_portal_requires_auth(env):
    env["holder"]["user"] = None
    assert env["client"].post("/api/billing/portal-session", json={}).status_code == 401


def test_checkout_still_disabled_when_only_one_flag_set(env, monkeypatch):
    """BILLING on but CHECKOUT off → still disabled (both required)."""
    monkeypatch.setenv("STRIPE_BILLING_ENABLED", "true")
    env["as_user"]("admin_a")
    resp = env["client"].post("/api/billing/checkout-session", json={"plan_code": "team"})
    assert resp.status_code == 503
    assert resp.json()["enabled"] is False


def test_webhook_dormant_does_not_process(env):
    resp = env["client"].post("/api/billing/webhook", json={"type": "invoice.paid"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["received"] is True
    assert body["processed"] is False


def test_billing_status_includes_stripe_readiness_without_secret(env, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", FAKE_SECRET)
    env["as_user"]("admin_a")
    body = env["client"].get("/api/billing/status").json()
    assert body["stripe"]["mode"] == "dormant"
    assert body["stripe"]["stripe_secret_configured"] is True
    assert "missing_price_env_vars" in body["stripe"]
    # The secret value must never appear anywhere in the response.
    assert FAKE_SECRET not in json.dumps(body)


def test_build_line_items_quantities():
    """Line-item math (pure, no Stripe): base seat + extra seats over included."""
    import os
    os.environ["STRIPE_PRICE_TEAM_BASE_MONTHLY"] = "price_team_base"
    os.environ["STRIPE_PRICE_TEAM_EXTRA_SEAT_MONTHLY"] = "price_team_extra"
    try:
        items = stripe_integration.build_line_items("team", 6)  # 3 included, 3 extra
        assert items[0] == {"price": "price_team_base", "quantity": 1}
        assert items[1] == {"price": "price_team_extra", "quantity": 3}
        # At/under included seats → only the base line.
        assert stripe_integration.build_line_items("team", 3) == [
            {"price": "price_team_base", "quantity": 1}
        ]
    finally:
        os.environ.pop("STRIPE_PRICE_TEAM_BASE_MONTHLY", None)
        os.environ.pop("STRIPE_PRICE_TEAM_EXTRA_SEAT_MONTHLY", None)


def test_enterprise_not_checkoutable():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as e:
        stripe_integration.build_line_items("enterprise", 5)
    assert e.value.status_code == 400
