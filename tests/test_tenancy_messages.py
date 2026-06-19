"""Phase 3A tests: Messages org isolation.

Flag OFF (default): behavior matches the single-agency app (see also the
unchanged tests/test_messages_module.py). Flag ON: threads, announcements,
participants, and the staff picker are all org-scoped; cross-org thread access
returns 404.

DBs are isolated to a tmp dir: messages.db via dependency override; auth.db and
core_clients.db via monkeypatching the module-level paths the routes/authorization
use.
"""
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.modules.messages.routes as messages_routes
from backend.auth import authorization as authz
from backend.auth.service import AuthenticatedUser
from backend.modules.messages.database import MessagesDatabase
from backend.modules.messages.routes import get_messages_db, router
from backend.shared.tenancy import DEFAULT_ORG_ID


def _user(org_id=DEFAULT_ORG_ID, case_manager_id="cm_a1", role="admin", uid=None):
    return AuthenticatedUser(
        firebase_uid=uid or f"uid-{case_manager_id}",
        email=f"{case_manager_id}@example.test",
        full_name=case_manager_id.upper(),
        role=role,
        case_manager_id=case_manager_id,
        auth_provider="test",
        is_active=True,
        org_id=org_id,
        org_role="org_admin" if role == "admin" else "member",
    )


def _seed_auth_db(path):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE user_profiles (
                firebase_uid TEXT, case_manager_id TEXT, full_name TEXT,
                role TEXT, is_active INTEGER, org_id TEXT
            )
            """
        )
        rows = [
            ("uid-cm_a1", "cm_a1", "CM A1", "admin", 1, "org_a"),
            ("uid-cm_a2", "cm_a2", "CM A2", "case_manager", 1, "org_a"),
            ("uid-cm_b1", "cm_b1", "CM B1", "admin", 1, "org_b"),
        ]
        conn.executemany(
            "INSERT INTO user_profiles (firebase_uid, case_manager_id, full_name, role, is_active, org_id) VALUES (?,?,?,?,?,?)",
            rows,
        )
        conn.commit()


def _seed_core_clients(path):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE clients (
                client_id TEXT PRIMARY KEY, first_name TEXT, last_name TEXT,
                case_manager_id TEXT, org_id TEXT
            )
            """
        )
        conn.executemany(
            "INSERT INTO clients (client_id, first_name, last_name, case_manager_id, org_id) VALUES (?,?,?,?,?)",
            [
                ("client-a", "Anna", "Org-A", "cm_a1", "org_a"),
                ("client-b", "Ben", "Org-B", "cm_b1", "org_b"),
            ],
        )
        conn.commit()


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    messages_db = MessagesDatabase(tmp_path / "messages.db")
    _seed_auth_db(tmp_path / "auth.db")
    _seed_core_clients(tmp_path / "core_clients.db")

    monkeypatch.setattr(messages_routes, "DB_DIR", tmp_path)
    monkeypatch.setattr(authz, "AUTH_DB", tmp_path / "auth.db")
    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", tmp_path / "core_clients.db")

    holder = {"user": _user()}
    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(router, prefix="/api/messages")
    app.dependency_overrides[get_messages_db] = lambda: messages_db
    return TestClient(app), holder


@pytest.fixture
def ctx_mt(ctx, monkeypatch):
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    return ctx


def _make_dm(client, participant="cm_a2", body="hi"):
    return client.post(
        "/api/messages/threads",
        json={"thread_type": "direct_message", "title": "DM",
              "participants": [{"user_id": participant}], "initial_message": body},
    )


# ── Flag OFF: parity ────────────────────────────────────────────────────────

def test_flag_off_create_and_list(ctx):
    client, holder = ctx
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1")
    assert _make_dm(client).status_code == 200
    listed = client.get("/api/messages/threads").json()["threads"]
    assert len(listed) == 1


def test_flag_off_case_managers_returns_all(ctx):
    client, holder = ctx
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1")
    ids = {m["user_id"] for m in client.get("/api/messages/case-managers").json()["case_managers"]}
    # Cross-org user visible when flag off (existing behavior). cm_a1 excluded (self).
    assert {"cm_a2", "cm_b1"} <= ids


# ── Flag ON: isolation ──────────────────────────────────────────────────────

def test_flag_on_cross_org_cannot_list_or_get(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1")
    tid = _make_dm(client).json()["thread"]["id"]

    holder["user"] = _user(org_id="org_b", case_manager_id="cm_b1")
    assert client.get("/api/messages/threads").json()["threads"] == []
    assert client.get(f"/api/messages/threads/{tid}").status_code == 404


def test_flag_on_cross_org_cannot_post(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1")
    tid = _make_dm(client).json()["thread"]["id"]
    holder["user"] = _user(org_id="org_b", case_manager_id="cm_b1")
    assert client.post(f"/api/messages/threads/{tid}/messages", json={"body": "x"}).status_code == 404


def test_flag_on_cross_org_cannot_mark_read(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1")
    tid = _make_dm(client).json()["thread"]["id"]
    holder["user"] = _user(org_id="org_b", case_manager_id="cm_b1")
    assert client.patch(f"/api/messages/threads/{tid}/read").status_code == 404


def test_flag_on_cannot_add_cross_org_participant(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1")
    resp = _make_dm(client, participant="cm_b1")
    assert resp.status_code == 400
    assert "organization" in resp.json()["detail"].lower()


def test_flag_on_same_org_participant_ok(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1")
    assert _make_dm(client, participant="cm_a2").status_code == 200


def test_flag_on_announcements_are_org_scoped(ctx_mt):
    client, holder = ctx_mt
    # org A admin posts an announcement
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    assert client.post("/api/messages/threads",
                       json={"thread_type": "announcement", "title": "A-only"}).status_code == 200

    # org A member sees it
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a2", role="case_manager")
    a_titles = {t["title"] for t in client.get("/api/messages/threads").json()["threads"]}
    assert "A-only" in a_titles

    # org B admin does NOT see it
    holder["user"] = _user(org_id="org_b", case_manager_id="cm_b1", role="admin")
    b_titles = {t["title"] for t in client.get("/api/messages/threads").json()["threads"]}
    assert "A-only" not in b_titles


def test_flag_on_client_thread_requires_same_org_client(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1")
    # same-org client -> ok
    ok = client.post("/api/messages/threads",
                     json={"thread_type": "client_thread", "client_id": "client-a"})
    assert ok.status_code == 200
    # cross-org client -> 404 (assert_client_access)
    bad = client.post("/api/messages/threads",
                      json={"thread_type": "client_thread", "client_id": "client-b"})
    assert bad.status_code == 404


def test_flag_on_case_managers_same_org_only(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1")
    ids = {m["user_id"] for m in client.get("/api/messages/case-managers").json()["case_managers"]}
    assert "cm_a2" in ids
    assert "cm_b1" not in ids
