"""First-login onboarding / org creation tests.

Covers the service seam (no Firebase needed — upsert takes a decoded-token dict)
and the HTTP endpoints (verify_bearer_token monkeypatched to a fixed identity),
including the security property that the client cannot supply role/org authority.
"""
import sqlite3
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import backend.auth.router as auth_router
from backend.auth.service import (
    ADMIN_ROLE,
    CASE_MANAGER_ROLE,
    ORG_ADMIN_ROLE,
    ORG_MEMBER_ROLE,
    FirebaseAuthService,
)
from backend.shared.tenancy import DEFAULT_ORG_ID


def _token(uid="u_new", email="new.user@example.test", name="New User"):
    return {"uid": uid, "email": email, "name": name}


@pytest.fixture
def svc(tmp_path):
    return FirebaseAuthService(db_path=tmp_path / "auth.db")


# ── New users need onboarding; existing users do not ────────────────────────

def test_new_user_needs_onboarding(svc):
    user = svc.upsert_profile_from_token(_token())
    assert user.onboarding_completed is False
    assert user.org_id == DEFAULT_ORG_ID  # stamped default until they choose


def test_existing_users_backfilled_to_complete(tmp_path):
    """A profile present before the migration must be marked complete (1) so
    existing/production users are never sent back through onboarding."""
    db = tmp_path / "auth.db"
    with sqlite3.connect(db) as conn:
        # Old-style schema: no onboarding_completed column yet.
        conn.execute(
            """
            CREATE TABLE user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                firebase_uid TEXT NOT NULL UNIQUE, email TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'case_manager',
                case_manager_id TEXT NOT NULL UNIQUE, auth_provider TEXT NOT NULL DEFAULT 'password',
                photo_url TEXT, is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_login_at TEXT,
                metadata TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO user_profiles (firebase_uid, email, full_name, case_manager_id, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            ("legacy_uid", "legacy@example.test", "Legacy User", "cm_legacy", now, now),
        )
        conn.commit()

    service = FirebaseAuthService(db_path=db)  # runs migration + backfill
    user = service.get_profile_by_uid("legacy_uid")
    assert user is not None
    assert user.onboarding_completed is True  # not trapped in onboarding


# ── Individual workspace ────────────────────────────────────────────────────

def test_individual_workspace_creates_org_and_assigns_owner(svc):
    svc.upsert_profile_from_token(_token())
    user = svc.create_individual_workspace("u_new")
    assert user.onboarding_completed is True
    assert user.org_id != DEFAULT_ORG_ID
    assert user.org_role == ORG_ADMIN_ROLE
    assert user.role == ADMIN_ROLE
    with sqlite3.connect(svc.db_path) as conn:
        conn.row_factory = sqlite3.Row
        org = conn.execute("SELECT * FROM organizations WHERE org_id = ?", (user.org_id,)).fetchone()
    assert org["org_type"] == "individual"
    assert org["created_by"] == "u_new"


# ── Create organization ─────────────────────────────────────────────────────

def test_create_organization_assigns_owner_admin(svc):
    svc.upsert_profile_from_token(_token())
    user = svc.create_organization("u_new", "Acme Recovery", "treatment_center")
    assert user.onboarding_completed is True
    assert user.org_id != DEFAULT_ORG_ID
    assert user.org_role == ORG_ADMIN_ROLE
    assert user.role == ADMIN_ROLE
    with sqlite3.connect(svc.db_path) as conn:
        conn.row_factory = sqlite3.Row
        org = conn.execute("SELECT * FROM organizations WHERE org_id = ?", (user.org_id,)).fetchone()
    assert org["name"] == "Acme Recovery"
    assert org["org_type"] == "treatment_center"


def test_create_organization_rejects_bad_input(svc):
    svc.upsert_profile_from_token(_token())
    with pytest.raises(HTTPException) as e1:
        svc.create_organization("u_new", "   ", "treatment_center")
    assert e1.value.status_code == 400
    with pytest.raises(HTTPException) as e2:
        svc.create_organization("u_new", "Acme", "not_a_real_type")
    assert e2.value.status_code == 400


# ── Join by invite ──────────────────────────────────────────────────────────

def _seed_invite(db_path, token, org_id="org_partner", org_role=ORG_MEMBER_ROLE,
                 status="pending", expires_in_days=7):
    expires = (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO invites (invite_id, org_id, email, org_role, token, status, expires_at, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (f"inv_{token}", org_id, "invitee@example.test", org_role, token, status, expires, datetime.utcnow().isoformat()),
        )
        # ensure the org exists
        conn.execute(
            "INSERT OR IGNORE INTO organizations (org_id, name, status, created_at, updated_at) VALUES (?,?, 'active', ?, ?)",
            (org_id, "Partner Org", datetime.utcnow().isoformat(), datetime.utcnow().isoformat()),
        )
        conn.commit()


def test_accept_valid_invite_assigns_org_and_role(svc):
    svc.upsert_profile_from_token(_token())
    _seed_invite(svc.db_path, "good-token", org_id="org_partner", org_role=ORG_MEMBER_ROLE)
    user = svc.accept_invite("u_new", "good-token")
    assert user.org_id == "org_partner"
    assert user.org_role == ORG_MEMBER_ROLE
    assert user.role == CASE_MANAGER_ROLE  # member invite -> case_manager
    assert user.onboarding_completed is True
    with sqlite3.connect(svc.db_path) as conn:
        status = conn.execute("SELECT status FROM invites WHERE token = 'good-token'").fetchone()[0]
    assert status == "accepted"


def test_accept_invalid_invite_rejected(svc):
    svc.upsert_profile_from_token(_token())
    with pytest.raises(HTTPException) as e:
        svc.accept_invite("u_new", "does-not-exist")
    assert e.value.status_code == 400


def test_accept_expired_invite_rejected(svc):
    svc.upsert_profile_from_token(_token())
    _seed_invite(svc.db_path, "old-token", expires_in_days=-1)
    with pytest.raises(HTTPException) as e:
        svc.accept_invite("u_new", "old-token")
    assert e.value.status_code == 400


# ── HTTP endpoints + "no client-supplied role authority" ────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    service = FirebaseAuthService(db_path=tmp_path / "auth.db")
    # Fixed identity; no real Firebase. The router derives identity from this.
    service.verify_bearer_token = lambda header: _token()
    monkeypatch.setattr(auth_router, "auth_service", service)
    app = FastAPI()
    app.include_router(auth_router.router)
    return TestClient(app), service


def test_me_reports_needs_onboarding_for_new_user(client):
    c, _ = client
    resp = c.get("/api/auth/me", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_onboarding"] is True
    assert body["user"]["onboarding_completed"] is False


def test_create_org_endpoint_ignores_client_supplied_role(client):
    c, _ = client
    # Client tries to assert authority by sending role/org_role in the body.
    # The server must ignore them and assign owner/admin on its own.
    resp = c.post(
        "/api/auth/onboarding/organization",
        headers={"Authorization": "Bearer x"},
        json={"name": "Sneaky Org", "org_type": "sober_living",
              "role": "case_manager", "org_role": "member"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_onboarding"] is False
    assert body["user"]["role"] == ADMIN_ROLE          # server-assigned, not body's case_manager
    assert body["user"]["org_role"] == ORG_ADMIN_ROLE  # server-assigned, not body's member
    assert body["user"]["org_id"] != DEFAULT_ORG_ID


def test_join_endpoint_invalid_token_returns_400(client):
    c, service = client
    c.get("/api/auth/me", headers={"Authorization": "Bearer x"})  # ensure profile exists
    resp = c.post(
        "/api/auth/onboarding/join",
        headers={"Authorization": "Bearer x"},
        json={"token": "nope"},
    )
    assert resp.status_code == 400
