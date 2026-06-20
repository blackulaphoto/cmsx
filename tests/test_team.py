"""Team management (invites + staff) tests.

Service is pointed at a tmp auth.db; team_routes.auth_service is monkeypatched to
it. Auth identity is injected via middleware (the same pattern as the tenancy
tests), so require_org_admin / resolve_request_user run for real.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.auth.team_routes as team_routes
from backend.auth.service import (
    ADMIN_ROLE, CASE_MANAGER_ROLE, ORG_ADMIN_ROLE, ORG_MEMBER_ROLE,
    FirebaseAuthService,
)


def _token(uid, email, name="User"):
    return {"uid": uid, "email": email, "name": name}


@pytest.fixture
def env(tmp_path, monkeypatch):
    svc = FirebaseAuthService(db_path=tmp_path / "auth.db")
    monkeypatch.setattr(team_routes, "auth_service", svc)

    # Org A: owner admin_a; second admin a2; member m_a. Org B: owner admin_b.
    svc.upsert_profile_from_token(_token("admin_a", "admin_a@a.test", "Admin A"))
    oa = svc.create_organization("admin_a", "Org A", "case_management_agency").org_id

    svc.upsert_profile_from_token(_token("a2", "a2@a.test", "Admin A2"))
    svc.upsert_profile_from_token(_token("m_a", "m_a@a.test", "Member A"))
    inv_admin = svc.create_invite(oa, "a2@a.test", ORG_ADMIN_ROLE, invited_by="admin_a")
    svc.accept_invite("a2", inv_admin["token"])
    inv_member = svc.create_invite(oa, "m_a@a.test", ORG_MEMBER_ROLE, invited_by="admin_a")
    svc.accept_invite("m_a", inv_member["token"])

    svc.upsert_profile_from_token(_token("admin_b", "admin_b@b.test", "Admin B"))
    ob = svc.create_organization("admin_b", "Org B", "sober_living").org_id

    holder = {"user": None}
    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        if holder["user"] is not None:
            request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(team_routes.router)
    client = TestClient(app)

    def as_user(uid):
        holder["user"] = svc.get_profile_by_uid(uid)

    return {"svc": svc, "client": client, "holder": holder, "as_user": as_user, "oa": oa, "ob": ob}


# ── Auth / authorization ────────────────────────────────────────────────────

def test_unauthenticated_endpoints_return_401(env):
    c = env["client"]
    env["holder"]["user"] = None
    assert c.get("/api/team/invites").status_code == 401
    assert c.get("/api/team/staff").status_code == 401
    assert c.post("/api/team/invites", json={"email": "x@y.test", "role": "member"}).status_code == 401


def test_non_admin_cannot_manage(env):
    c = env["client"]
    env["as_user"]("m_a")  # plain member
    assert c.get("/api/team/invites").status_code == 403
    assert c.get("/api/team/staff").status_code == 403
    assert c.post("/api/team/invites", json={"email": "x@y.test", "role": "member"}).status_code == 403


# ── Invite creation + org scoping ───────────────────────────────────────────

def test_admin_creates_invite_for_own_org(env):
    c = env["client"]
    env["as_user"]("admin_a")
    r = c.post("/api/team/invites", json={"email": "new@a.test", "role": "member", "name": "New"})
    assert r.status_code == 200
    inv = r.json()["invite"]
    assert inv["org_id"] == env["oa"]
    assert inv["org_role"] == ORG_MEMBER_ROLE
    assert inv["status"] == "pending"
    assert len(inv["token"]) >= 20  # unguessable


def test_caller_supplied_org_id_is_ignored(env):
    c = env["client"]
    env["as_user"]("admin_a")
    # Try to smuggle another org's id in the body; it must be ignored.
    r = c.post("/api/team/invites", json={"email": "x@a.test", "role": "member", "org_id": env["ob"]})
    assert r.status_code == 200
    assert r.json()["invite"]["org_id"] == env["oa"]  # caller's org, not ob


def test_admin_lists_only_their_org_invites(env):
    c = env["client"]
    env["as_user"]("admin_a")
    c.post("/api/team/invites", json={"email": "p1@a.test", "role": "member"})
    env["as_user"]("admin_b")
    c.post("/api/team/invites", json={"email": "p2@b.test", "role": "member"})

    env["as_user"]("admin_a")
    emails_a = {i["email"] for i in c.get("/api/team/invites").json()["invites"]}
    assert "p1@a.test" in emails_a
    assert "p2@b.test" not in emails_a
    assert all(i["org_id"] == env["oa"] for i in c.get("/api/team/invites").json()["invites"])


# ── Resend / cancel / accept lifecycle ──────────────────────────────────────

def test_resend_regenerates_token(env):
    c = env["client"]
    env["as_user"]("admin_a")
    inv = c.post("/api/team/invites", json={"email": "r@a.test", "role": "member"}).json()["invite"]
    resent = c.post(f"/api/team/invites/{inv['invite_id']}/resend").json()["invite"]
    assert resent["token"] != inv["token"]
    assert resent["status"] == "pending"


def test_cancelled_invite_cannot_be_accepted(env):
    c, svc = env["client"], env["svc"]
    env["as_user"]("admin_a")
    inv = c.post("/api/team/invites", json={"email": "c@a.test", "role": "member"}).json()["invite"]
    assert c.post(f"/api/team/invites/{inv['invite_id']}/cancel").status_code == 200
    svc.upsert_profile_from_token(_token("joiner", "joiner@a.test"))
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as e:
        svc.accept_invite("joiner", inv["token"])
    assert e.value.status_code == 400


def test_cross_org_invite_action_404(env):
    c = env["client"]
    env["as_user"]("admin_a")
    inv = c.post("/api/team/invites", json={"email": "z@a.test", "role": "member"}).json()["invite"]
    # Admin B must not be able to cancel Org A's invite.
    env["as_user"]("admin_b")
    assert c.post(f"/api/team/invites/{inv['invite_id']}/cancel").status_code == 404


# ── Staff listing + role + removal ──────────────────────────────────────────

def test_admin_lists_only_their_org_staff(env):
    c = env["client"]
    env["as_user"]("admin_a")
    uids = {s["firebase_uid"] for s in c.get("/api/team/staff").json()["staff"]}
    assert {"admin_a", "a2", "m_a"} <= uids
    assert "admin_b" not in uids


def test_cannot_remove_last_org_admin(env):
    c = env["client"]
    env["as_user"]("admin_a")
    # Two admins (admin_a, a2): removing a2 is allowed.
    assert c.post("/api/team/staff/a2/remove").status_code == 200
    # Now admin_a is the last active admin: removing them is blocked.
    assert c.post("/api/team/staff/admin_a/remove").status_code == 400


def test_disabled_staff_loses_access(env):
    c = env["client"]
    env["as_user"]("admin_a")
    assert c.post("/api/team/staff/a2/remove").status_code == 200  # disable a2 (still 1 admin left)
    assert env["svc"].get_profile_by_uid("a2").is_active is False
    # a2 is org_admin but now inactive -> every guarded endpoint 403s.
    env["as_user"]("a2")
    assert c.get("/api/team/staff").status_code == 403


def test_cannot_demote_last_org_admin(env):
    c = env["client"]
    env["as_user"]("admin_a")
    c.post("/api/team/staff/a2/remove")  # a2 disabled -> admin_a is last active admin
    r = c.post("/api/team/staff/admin_a/role", json={"role": "member"})
    assert r.status_code == 400


def test_admin_can_change_member_role(env):
    c = env["client"]
    env["as_user"]("admin_a")
    r = c.post("/api/team/staff/m_a/role", json={"role": "org_admin"})
    assert r.status_code == 200
    assert r.json()["staff"]["org_role"] == ORG_ADMIN_ROLE
    assert r.json()["staff"]["role"] == ADMIN_ROLE
