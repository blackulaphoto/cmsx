"""Super Admin Panel tests.

Service points at a tmp auth.db (monkeypatched into super_admin_routes); a tmp
core_clients.db provides client counts. Identity is injected via middleware. The
super-admin check is an email allowlist enforced server-side.
"""
import json
import sqlite3
import types

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import backend.auth.super_admin_routes as sa_routes
import backend.shared.db_path as db_path_mod
from backend.auth.service import AuthenticatedUser, FirebaseAuthService, ORG_ADMIN_ROLE, ORG_MEMBER_ROLE
from backend.shared.tenancy import DEFAULT_ORG_ID

SUPER_EMAIL = "blackulaphotography@gmail.com"
PHI_KEYS = ("first_name", "last_name", "date_of_birth", "dob", "ssn", "diagnosis", "client_name")


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
    svc = FirebaseAuthService(db_path=tmp_path / "auth.db")
    monkeypatch.setattr(sa_routes, "auth_service", svc)
    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp_path)

    # Two orgs with staff.
    svc.upsert_profile_from_token(_token("admin_a", "admin_a@a.test", "Admin A"))
    oa = svc.create_organization("admin_a", "Org A", "case_management_agency").org_id
    svc.upsert_profile_from_token(_token("m_a", "m_a@a.test", "Member A"))
    inv = svc.create_invite(oa, "m_a@a.test", ORG_MEMBER_ROLE, invited_by="admin_a")
    svc.accept_invite("m_a", inv["token"])
    svc.upsert_profile_from_token(_token("admin_b", "admin_b@b.test", "Admin B"))
    ob = svc.create_organization("admin_b", "Org B", "sober_living").org_id

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

    app.include_router(sa_routes.router)
    client = TestClient(app)

    def as_user(uid):
        holder["user"] = svc.get_profile_by_uid(uid)

    def as_super():
        holder["user"] = _super_admin_user()

    return {"svc": svc, "client": client, "holder": holder, "as_user": as_user,
            "as_super": as_super, "oa": oa, "ob": ob}


# ── Access control ──────────────────────────────────────────────────────────

def test_unauthenticated_returns_401(env):
    c = env["client"]
    env["holder"]["user"] = None
    assert c.get("/api/super-admin/overview").status_code == 401
    assert c.get("/api/super-admin/organizations").status_code == 401


def test_org_admin_is_not_super_admin_403(env):
    c = env["client"]
    env["as_user"]("admin_a")  # an org admin (org_admin + app admin) — but not platform owner
    assert c.get("/api/super-admin/organizations").status_code == 403
    assert c.post(f"/api/super-admin/organizations/{env['ob']}/suspend", json={}).status_code == 403


def test_role_org_claims_do_not_elevate(env):
    """admin_a has role=admin + org_role=org_admin yet is still rejected — only the
    email allowlist grants super-admin, so role/org claims cannot elevate."""
    c = env["client"]
    env["as_user"]("admin_a")
    assert c.get("/api/super-admin/users").status_code == 403


# ── Reads ───────────────────────────────────────────────────────────────────

def test_super_admin_lists_orgs_with_counts(env):
    c = env["client"]
    env["as_super"]()
    body = c.get("/api/super-admin/organizations").json()
    assert body["success"] is True
    orgs = {o["org_id"]: o for o in body["organizations"]}
    assert env["oa"] in orgs and env["ob"] in orgs
    assert orgs[env["oa"]]["user_count"] == 2          # admin_a + m_a
    assert orgs[env["oa"]]["client_count"] == 2
    assert orgs[env["ob"]]["client_count"] == 1
    # No PHI anywhere in the listing.
    blob = json.dumps(body).lower()
    assert not any(k in blob for k in PHI_KEYS)


def test_super_admin_overview(env):
    c = env["client"]
    env["as_super"]()
    body = c.get("/api/super-admin/overview").json()
    assert body["total_clients"] == 3
    assert body["total_orgs"] >= 2
    assert "multi_tenant_enabled" in body


def test_super_admin_org_detail(env):
    c = env["client"]
    env["as_super"]()
    body = c.get(f"/api/super-admin/organizations/{env['oa']}").json()
    assert body["client_count"] == 2
    assert {s["firebase_uid"] for s in body["staff"]} == {"admin_a", "m_a"}
    assert body["pending_invites"] == 0
    assert not any(k in json.dumps(body).lower() for k in PHI_KEYS)


def test_super_admin_user_search(env):
    c = env["client"]
    env["as_super"]()
    users = c.get("/api/super-admin/users", params={"q": "admin_a"}).json()["users"]
    assert any(u["email"] == "admin_a@a.test" for u in users)


# ── Suspend / restore ───────────────────────────────────────────────────────

def test_suspend_and_restore_org(env):
    c = env["client"]
    env["as_super"]()
    assert c.post(f"/api/super-admin/organizations/{env['ob']}/suspend", json={}).json()["status"] == "suspended"
    assert c.get(f"/api/super-admin/organizations/{env['ob']}").json()["organization"]["status"] == "suspended"
    assert c.post(f"/api/super-admin/organizations/{env['ob']}/restore").json()["status"] == "active"


def test_default_org_suspend_requires_confirm(env):
    c = env["client"]
    env["as_super"]()
    assert c.post(f"/api/super-admin/organizations/{DEFAULT_ORG_ID}/suspend", json={}).status_code == 400
    assert c.post(f"/api/super-admin/organizations/{DEFAULT_ORG_ID}/suspend", json={"confirm": True}).status_code == 200
    c.post(f"/api/super-admin/organizations/{DEFAULT_ORG_ID}/restore")  # cleanup


def test_suspended_org_blocks_guarded_access(env):
    """A user in a suspended org fails resolve_request_user (403)."""
    svc = env["svc"]
    svc.set_org_status(env["ob"], "suspended")
    user_b = svc.get_profile_by_uid("admin_b")
    request = types.SimpleNamespace(state=types.SimpleNamespace(auth_user=user_b))
    with pytest.raises(HTTPException) as e:
        svc.resolve_request_user(request)
    assert e.value.status_code == 403
    # The default org is never treated as suspended (lockout guard).
    assert svc.is_org_suspended(DEFAULT_ORG_ID) is False
