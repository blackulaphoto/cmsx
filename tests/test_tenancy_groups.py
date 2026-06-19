"""Groups tenancy hardening tests (Phase 3E)."""
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth import authorization as authz
from backend.auth.service import AuthenticatedUser
from backend.modules.groups import database as groups_db_module
from backend.modules.groups import routes as groups_routes
from backend.modules.groups.database import GroupsDatabase
from backend.shared.tenancy import DEFAULT_ORG_ID


def _user(org_id="org_a", case_manager_id="cm_a1", role="admin"):
    return AuthenticatedUser(
        firebase_uid=f"uid-{case_manager_id}",
        email=f"{case_manager_id}@example.test",
        full_name=case_manager_id.upper(),
        role=role,
        case_manager_id=case_manager_id,
        auth_provider="test",
        is_active=True,
        org_id=org_id,
        org_role="org_admin" if role == "admin" else "member",
    )


def _make_app(user: AuthenticatedUser, groups_db_instance: GroupsDatabase, monkeypatch) -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def inject_auth(request, call_next):
        request.state.auth_user = user
        return await call_next(request)

    monkeypatch.setattr(groups_routes, "groups_db", groups_db_instance)
    app.include_router(groups_routes.router)
    return TestClient(app, raise_server_exceptions=True)


def _seed_session(db: GroupsDatabase, case_manager_id: str, org_id: str, title: str = "Test Session") -> dict:
    return db.create_session({
        "title": title,
        "topic_id": None,
        "scheduled_date": "2026-01-15",
        "scheduled_time": "10:00",
        "location": "Room 1",
        "group_type": "psychoeducation",
        "facilitator_notes": "",
        "case_manager_id": case_manager_id,
        "org_id": org_id,
    })


def _seed_schedule(db: GroupsDatabase, created_by: str, org_id: str, title: str = "Test Schedule") -> dict:
    return db.create_schedule({
        "title": title,
        "group_type": "psychoeducation",
        "day_of_week": 1,
        "start_time": "10:00",
        "location": "Room 1",
        "recurrence": "weekly",
        "created_by": created_by,
        "org_id": org_id,
    })


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    auth_db = tmp_path / "auth.db"
    core_db = tmp_path / "core_clients.db"

    monkeypatch.setattr(authz, "AUTH_DB", auth_db)
    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", core_db)

    # Seed auth DB with two orgs
    with sqlite3.connect(auth_db) as conn:
        conn.execute("""
            CREATE TABLE user_profiles (
                case_manager_id TEXT, firebase_uid TEXT, org_id TEXT
            )
        """)
        conn.executemany(
            "INSERT INTO user_profiles VALUES (?,?,?)",
            [
                ("cm_a1", "uid-cm_a1", "org_a"),
                ("cm_a2", "uid-cm_a2", "org_a"),
                ("cm_b1", "uid-cm_b1", "org_b"),
            ],
        )

    # Create a shared in-memory-like isolated groups DB for each test
    db_a = GroupsDatabase(tmp_path / "groups.db")

    yield {
        "db": db_a,
        "monkeypatch": monkeypatch,
    }


# ── Test 1: flag off — list sessions returns all without org filter ─────────────

def test_flag_off_parity_list_sessions(ctx, monkeypatch):
    db: GroupsDatabase = ctx["db"]
    _seed_session(db, "cm_a1", "org_a", "Session A")
    _seed_session(db, "cm_b1", "org_b", "Session B")

    monkeypatch.delenv("MULTI_TENANT_ENABLED", raising=False)

    user = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    client = _make_app(user, db, monkeypatch)

    resp = client.get("/groups/sessions")
    assert resp.status_code == 200
    titles = {s["title"] for s in resp.json()["sessions"]}
    # When flag is off, admin sees all sessions regardless of org
    assert "Session A" in titles
    assert "Session B" in titles


# ── Test 2: flag on — admin list isolation ──────────────────────────────────────

def test_flag_on_admin_session_list_isolation(ctx, monkeypatch):
    db: GroupsDatabase = ctx["db"]
    _seed_session(db, "cm_a1", "org_a", "Session A")
    _seed_session(db, "cm_b1", "org_b", "Session B")

    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")

    user = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    client = _make_app(user, db, monkeypatch)

    resp = client.get("/groups/sessions")
    assert resp.status_code == 200
    titles = {s["title"] for s in resp.json()["sessions"]}
    assert "Session A" in titles
    assert "Session B" not in titles


# ── Test 3: flag on — cross-org GET session returns 404 ────────────────────────

def test_cross_org_session_get_returns_404(ctx, monkeypatch):
    db: GroupsDatabase = ctx["db"]
    session_b = _seed_session(db, "cm_b1", "org_b", "Session B")

    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")

    user = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    client = _make_app(user, db, monkeypatch)

    resp = client.get(f"/groups/sessions/{session_b['session_id']}")
    assert resp.status_code == 404


# ── Test 4: flag on — cross-org PUT session returns 404 ────────────────────────

def test_cross_org_session_put_returns_404(ctx, monkeypatch):
    db: GroupsDatabase = ctx["db"]
    session_b = _seed_session(db, "cm_b1", "org_b", "Session B")

    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")

    user = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    client = _make_app(user, db, monkeypatch)

    resp = client.put(f"/groups/sessions/{session_b['session_id']}", json={"title": "Hacked"})
    assert resp.status_code == 404


# ── Test 5: flag on — cross-org GET schedule returns 404 ───────────────────────

def test_cross_org_schedule_get_instances_returns_404(ctx, monkeypatch):
    db: GroupsDatabase = ctx["db"]
    sched_b = _seed_schedule(db, "cm_b1", "org_b", "Schedule B")

    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")

    user = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    client = _make_app(user, db, monkeypatch)

    resp = client.get(f"/groups/schedules/{sched_b['schedule_id']}/instances")
    assert resp.status_code == 404


# ── Test 6: flag on — cross-org PUT schedule returns 404 ───────────────────────

def test_cross_org_schedule_put_returns_404(ctx, monkeypatch):
    db: GroupsDatabase = ctx["db"]
    sched_b = _seed_schedule(db, "cm_b1", "org_b", "Schedule B")

    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")

    user = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    client = _make_app(user, db, monkeypatch)

    resp = client.put(f"/groups/schedules/{sched_b['schedule_id']}", json={"title": "Hacked"})
    assert resp.status_code == 404


# ── Test 7: flag on — admin schedule list isolation ────────────────────────────

def test_flag_on_admin_schedule_list_isolation(ctx, monkeypatch):
    db: GroupsDatabase = ctx["db"]
    _seed_schedule(db, "cm_a1", "org_a", "Schedule A")
    _seed_schedule(db, "cm_b1", "org_b", "Schedule B")

    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")

    user = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    client = _make_app(user, db, monkeypatch)

    resp = client.get("/groups/schedules")
    assert resp.status_code == 200
    titles = {s["title"] for s in resp.json()["schedules"]}
    assert "Schedule A" in titles
    assert "Schedule B" not in titles


# ── Test 8: backfill derives org from case_manager_id ──────────────────────────

def test_backfill_sessions_derives_org_from_case_manager(ctx, monkeypatch):
    db: GroupsDatabase = ctx["db"]

    # Write a session without org_id (simulating pre-migration row)
    with sqlite3.connect(db.db_path) as conn:
        session_id = "sess-backfill-test"
        conn.execute(
            "INSERT INTO group_sessions (session_id, title, status, case_manager_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
            (session_id, "Backfill Session", "planned", "cm_a1"),
        )

    # Trigger backfill
    db._backfill_tenancy()

    org = db.get_session_org(session_id)
    assert org == "org_a"
