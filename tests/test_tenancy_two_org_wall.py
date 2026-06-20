"""Consolidated "2-org wall" test (SaaS activation harness v1).

A single readable integration check that, with ``MULTI_TENANT_ENABLED=true``,
an Org A admin sees ONLY Org A data and NEVER Org B data across the major
tenant-scoped modules — driven from one seeded two-org dataset.

This intentionally does NOT re-prove every per-module edge case (those live in
the per-module ``tests/test_tenancy_*.py`` suites). It is the single cross-module
"wall holds" smoke that mirrors what the staging harness asserts against a real
deployment (see ``scripts/saas_harness.py``).

Modules covered:
  - Core clients   — ``GET /api/clients``                 (real HTTP, admin list)
  - Reminders      — ``GET /api/reminders/tasks``         (real HTTP, admin list)
  - Messages       — ``GET /api/messages/threads``        (real HTTP, thread list)
  - Legal/clinical — ``_get_accessible_client_ids`` +     (shared scoping seam used
                     ``get_client_ids_for_org``            by legal/benefits/medical/
                                                           fmla/ur list endpoints)
"""
import sqlite3
from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.shared.db_path as db_path_mod
from backend.api import clients as clients_api
from backend.auth import authorization as authz
from backend.auth.service import AuthenticatedUser
import backend.modules.legal.routes as legal_routes
from backend.modules.reminders import repository as reminders_repo
from backend.modules.reminders import routes as reminders_routes
import backend.modules.messages.routes as messages_routes
from backend.modules.messages.database import MessagesDatabase
from backend.modules.messages.routes import get_messages_db, router as messages_router


def _user(org_id, case_manager_id, role="admin"):
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


ORG_A_ADMIN = lambda: _user("org_a", "cm_a1", "admin")
ORG_B_ADMIN = lambda: _user("org_b", "cm_b1", "admin")


class _FakeDataIntegrator:
    """Mirrors the reminders per-module test: hardcoded tasks filtered by caller."""

    def get_real_tasks_data(self, case_manager_id=None, status=None, client_id=None):
        tasks = [
            {"task_id": "task-a", "client_id": "client-a", "case_manager_id": "cm_a1", "status": "pending"},
            {"task_id": "task-b", "client_id": "client-b", "case_manager_id": "cm_b1", "status": "pending"},
        ]
        if case_manager_id:
            tasks = [t for t in tasks if t["case_manager_id"] == case_manager_id]
        if client_id:
            tasks = [t for t in tasks if t["client_id"] == client_id]
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        return tasks


def _seed_core_clients():
    """Real core-clients schema + two orgs (one client each)."""
    with clients_api.get_database_connection("core_clients", "ADMIN") as conn:
        clients_api.ensure_core_clients_schema(conn)
        conn.executemany(
            """
            INSERT INTO clients (client_id, first_name, last_name, case_manager_id,
                                 org_id, intake_date, created_at)
            VALUES (?, ?, 'Client', ?, ?, '2026-01-01', '2026-01-01T00:00:00')
            """,
            [
                ("client-a", "Ann", "cm_a1", "org_a"),
                ("client-b", "Bob", "cm_b1", "org_b"),
            ],
        )
        conn.commit()


def _seed_auth(path):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE user_profiles (
                firebase_uid TEXT, case_manager_id TEXT, full_name TEXT,
                role TEXT, is_active INTEGER, org_id TEXT
            )
            """
        )
        conn.executemany(
            "INSERT INTO user_profiles (firebase_uid, case_manager_id, full_name, role, is_active, org_id) VALUES (?,?,?,?,?,?)",
            [
                ("uid-cm_a1", "cm_a1", "CM A1", "admin", 1, "org_a"),
                ("uid-cm_a2", "cm_a2", "CM A2", "case_manager", 1, "org_a"),
                ("uid-cm_b1", "cm_b1", "CM B1", "admin", 1, "org_b"),
                ("uid-cm_b2", "cm_b2", "CM B2", "case_manager", 1, "org_b"),
            ],
        )
        conn.commit()


def _seed_reminders(path):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE active_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id TEXT UNIQUE NOT NULL, client_id TEXT NOT NULL,
                case_manager_id TEXT NOT NULL, reminder_type TEXT NOT NULL,
                message TEXT NOT NULL, priority TEXT DEFAULT 'Medium',
                due_date TEXT, status TEXT DEFAULT 'Active', created_at TEXT, org_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE intelligent_tasks (
                id TEXT PRIMARY KEY, client_id TEXT NOT NULL, case_manager_id TEXT,
                task_type TEXT, title TEXT, description TEXT, priority TEXT, status TEXT,
                estimated_minutes INTEGER, due_date TEXT, completed_at TEXT,
                created_at TEXT, is_demo INTEGER DEFAULT 0, org_id TEXT
            )
            """
        )
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        conn.executemany(
            "INSERT INTO active_reminders (reminder_id, client_id, case_manager_id, reminder_type, message, priority, due_date, status, created_at, org_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                ("rem-a", "client-a", "cm_a1", "general", "A reminder", "High", tomorrow, "Active", "2030-01-01T00:00:00", "org_a"),
                ("rem-b", "client-b", "cm_b1", "general", "B reminder", "High", tomorrow, "Active", "2030-01-01T00:00:00", "org_b"),
            ],
        )
        conn.executemany(
            "INSERT INTO intelligent_tasks (id, client_id, case_manager_id, task_type, title, description, priority, status, estimated_minutes, due_date, created_at, org_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                ("task-a", "client-a", "cm_a1", "general", "A task", "", "high", "pending", 30, tomorrow, "2030-01-01T00:00:00", "org_a"),
                ("task-b", "client-b", "cm_b1", "general", "B task", "", "high", "pending", 30, tomorrow, "2030-01-01T00:00:00", "org_b"),
            ],
        )
        conn.commit()


@pytest.fixture
def wall(tmp_path, monkeypatch):
    """One tmp dir, every DB isolated, two orgs seeded, MULTI_TENANT_ENABLED=true."""
    core_db = tmp_path / "core_clients.db"
    auth_db = tmp_path / "auth.db"
    reminders_db = tmp_path / "reminders.db"
    case_mgmt_db = tmp_path / "case_management.db"

    # Point every storage seam at the tmp dir.
    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp_path)
    monkeypatch.setattr(legal_routes, "_DB_DIR", tmp_path)
    monkeypatch.setattr(messages_routes, "DB_DIR", tmp_path)
    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", core_db)
    monkeypatch.setattr(authz, "AUTH_DB", auth_db)
    monkeypatch.setattr(reminders_repo, "_SQLITE_CORE_CLIENTS_PATH", str(core_db))
    monkeypatch.setattr(reminders_repo, "_SQLITE_REMINDERS_PATH", str(reminders_db))
    monkeypatch.setattr(reminders_repo, "_SQLITE_CASE_MGMT_PATH", str(case_mgmt_db))
    monkeypatch.setattr(reminders_repo, "_sqlite_tenancy_ready", False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Keep client creation focused (unused here, but matches the per-module pattern).
    monkeypatch.setattr(clients_api, "propagate_client_to_modules", lambda *a, **k: {})
    monkeypatch.setattr(clients_api, "upsert_client_to_postgres", lambda *a, **k: {})

    _seed_core_clients()
    _seed_auth(auth_db)
    _seed_reminders(reminders_db)

    original_integrator = reminders_routes.data_integrator
    reminders_routes.data_integrator = _FakeDataIntegrator()

    messages_db = MessagesDatabase(tmp_path / "messages.db")

    holder = {"user": ORG_A_ADMIN()}
    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(clients_api.router)
    app.include_router(reminders_routes.router, prefix="/api/reminders")
    app.include_router(messages_router, prefix="/api/messages")
    app.dependency_overrides[get_messages_db] = lambda: messages_db

    # The flag is the whole point — turn SaaS mode ON.
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")

    client = TestClient(app)

    # Seed one DM thread per org (each between two same-org users).
    holder["user"] = ORG_A_ADMIN()
    client.post("/api/messages/threads", json={
        "thread_type": "direct_message", "title": "A-thread",
        "participants": [{"user_id": "cm_a2"}], "initial_message": "hi A"})
    holder["user"] = ORG_B_ADMIN()
    client.post("/api/messages/threads", json={
        "thread_type": "direct_message", "title": "B-thread",
        "participants": [{"user_id": "cm_b2"}], "initial_message": "hi B"})

    yield {"client": client, "holder": holder}

    reminders_routes.data_integrator = original_integrator


def test_two_org_wall_holds_across_modules(wall):
    """Org A admin sees only org_a and never org_b, across every module."""
    client = wall["client"]
    wall["holder"]["user"] = ORG_A_ADMIN()

    # 1) Core clients list (real HTTP).
    clients_resp = client.get("/api/clients")
    assert clients_resp.status_code == 200
    client_ids = {c["client_id"] for c in clients_resp.json()["clients"]}
    assert "client-a" in client_ids
    assert "client-b" not in client_ids

    # 2) Reminders / tasks list (real HTTP, admin default = caller's org).
    tasks_resp = client.get("/api/reminders/tasks")
    assert tasks_resp.status_code == 200
    task_ids = {t["task_id"] for t in tasks_resp.json()["tasks"]}
    assert "task-a" in task_ids
    assert "task-b" not in task_ids

    # 3) Messages thread list (real HTTP, org-scoped).
    threads_resp = client.get("/api/messages/threads")
    assert threads_resp.status_code == 200
    titles = {t.get("title") for t in threads_resp.json()["threads"]}
    assert "A-thread" in titles
    assert "B-thread" not in titles

    # 4) Legal + clinical (benefits/medical/fmla/ur) shared scoping seam.
    legal_ids = set(legal_routes._get_accessible_client_ids(ORG_A_ADMIN()))
    assert legal_ids == {"client-a"}
    org_a_ids = set(authz.get_client_ids_for_org("org_a"))
    assert org_a_ids == {"client-a"}
    assert "client-b" not in org_a_ids


def test_two_org_wall_symmetric_for_org_b(wall):
    """The wall is symmetric: org_b admin sees only org_b."""
    client = wall["client"]
    wall["holder"]["user"] = ORG_B_ADMIN()

    client_ids = {c["client_id"] for c in client.get("/api/clients").json()["clients"]}
    assert client_ids == {"client-b"}

    titles = {t.get("title") for t in client.get("/api/messages/threads").json()["threads"]}
    assert "B-thread" in titles
    assert "A-thread" not in titles

    assert set(authz.get_client_ids_for_org("org_b")) == {"client-b"}
