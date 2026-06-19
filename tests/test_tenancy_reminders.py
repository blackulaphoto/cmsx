"""Reminders tenancy hardening tests."""
import sqlite3
from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth import authorization as authz
from backend.auth.service import AuthenticatedUser
from backend.modules.reminders import repository as reminders_repo
from backend.modules.reminders import routes as reminders_routes
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


class _FakeDataIntegrator:
    def get_real_tasks_data(self, case_manager_id=None, status=None, client_id=None):
        tasks = [
            {"task_id": "task-a", "client_id": "client-a", "case_manager_id": "cm_a1", "status": "pending"},
            {"task_id": "task-b", "client_id": "client-b", "case_manager_id": "cm_b1", "status": "pending"},
        ]
        if case_manager_id:
            tasks = [task for task in tasks if task["case_manager_id"] == case_manager_id]
        if client_id:
            tasks = [task for task in tasks if task["client_id"] == client_id]
        if status:
            tasks = [task for task in tasks if task["status"] == status]
        return tasks


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    core_db = tmp_path / "core_clients.db"
    auth_db = tmp_path / "auth.db"
    reminders_db = tmp_path / "reminders.db"
    case_mgmt_db = tmp_path / "case_management.db"

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", core_db)
    monkeypatch.setattr(authz, "AUTH_DB", auth_db)
    monkeypatch.setattr(reminders_repo, "_SQLITE_CORE_CLIENTS_PATH", str(core_db))
    monkeypatch.setattr(reminders_repo, "_SQLITE_REMINDERS_PATH", str(reminders_db))
    monkeypatch.setattr(reminders_repo, "_SQLITE_CASE_MGMT_PATH", str(case_mgmt_db))
    monkeypatch.setattr(reminders_repo, "_sqlite_tenancy_ready", False)

    original_integrator = reminders_routes.data_integrator
    reminders_routes.data_integrator = _FakeDataIntegrator()

    with sqlite3.connect(core_db) as conn:
        conn.execute(
            "CREATE TABLE clients (client_id TEXT PRIMARY KEY, first_name TEXT, last_name TEXT, case_manager_id TEXT, org_id TEXT)"
        )
        conn.executemany(
            "INSERT INTO clients VALUES (?,?,?,?,?)",
            [
                ("client-a", "Ann", "A", "cm_a1", "org_a"),
                ("client-b", "Bob", "B", "cm_b1", "org_b"),
            ],
        )

    with sqlite3.connect(auth_db) as conn:
        conn.execute(
            "CREATE TABLE user_profiles (firebase_uid TEXT, case_manager_id TEXT, full_name TEXT, role TEXT, is_active INTEGER, org_id TEXT)"
        )
        conn.executemany(
            "INSERT INTO user_profiles VALUES (?,?,?,?,?,?)",
            [
                ("uid-cm_a1", "cm_a1", "Admin A", "admin", 1, "org_a"),
                ("uid-cm_b1", "cm_b1", "Admin B", "admin", 1, "org_b"),
            ],
        )

    with sqlite3.connect(reminders_db) as conn:
        conn.execute(
            """
            CREATE TABLE active_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                case_manager_id TEXT NOT NULL,
                reminder_type TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT DEFAULT 'Medium',
                due_date TEXT,
                status TEXT DEFAULT 'Active',
                created_at TEXT,
                org_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE intelligent_tasks (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                case_manager_id TEXT,
                task_type TEXT,
                title TEXT,
                description TEXT,
                priority TEXT,
                status TEXT,
                estimated_minutes INTEGER,
                due_date TEXT,
                completed_at TEXT,
                created_at TEXT,
                is_demo INTEGER DEFAULT 0,
                org_id TEXT
            )
            """
        )
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        conn.executemany(
            """
            INSERT INTO active_reminders
                (reminder_id, client_id, case_manager_id, reminder_type, message, priority, due_date, status, created_at, org_id)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            [
                ("rem-a", "client-a", "cm_a1", "general", "A reminder", "High", tomorrow, "Active", "2030-01-01T00:00:00", "org_a"),
                ("rem-b", "client-b", "cm_b1", "general", "B reminder", "High", tomorrow, "Active", "2030-01-01T00:00:00", "org_b"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO intelligent_tasks
                (id, client_id, case_manager_id, task_type, title, description, priority, status, estimated_minutes, due_date, created_at, org_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            [
                ("task-a", "client-a", "cm_a1", "general", "A task", "", "high", "pending", 30, tomorrow, "2030-01-01T00:00:00", "org_a"),
                ("task-b", "client-b", "cm_b1", "general", "B task", "", "high", "pending", 30, tomorrow, "2030-01-01T00:00:00", "org_b"),
            ],
        )

    holder = {"user": _user()}
    app = FastAPI()

    @app.middleware("http")
    async def inject_user(request, call_next):
        request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(reminders_routes.router, prefix="/api/reminders")

    yield {"client": TestClient(app), "holder": holder, "paths": {"reminders": reminders_db}}

    reminders_routes.data_integrator = original_integrator


@pytest.fixture
def ctx_mt(ctx, monkeypatch):
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    return ctx


def _bucket_ids(payload):
    ids = set()
    for items in payload["buckets"].values():
        ids.update(item.get("task_id") or item.get("id") for item in items)
    return ids


def test_flag_off_parity_case_manager_lists_existing_scope(ctx):
    client = ctx["client"]
    ctx["holder"]["user"] = _user(org_id="org_a", role="admin")

    payload = client.get("/api/reminders/prioritized/cm_b1").json()

    assert "task-b" in _bucket_ids(payload)
    assert "rem-b" in _bucket_ids(payload)
    assert payload["total_active"] == 2


def test_flag_on_admin_list_isolation(ctx_mt):
    client = ctx_mt["client"]
    ctx_mt["holder"]["user"] = _user(org_id="org_a", role="admin")

    response = client.get("/api/reminders/prioritized/cm_a1")

    assert response.status_code == 200
    ids = _bucket_ids(response.json())
    assert {"task-a", "rem-a"} <= ids
    assert "task-b" not in ids
    assert "rem-b" not in ids


def test_flag_on_summary_count_isolation(ctx_mt):
    client = ctx_mt["client"]
    ctx_mt["holder"]["user"] = _user(org_id="org_a", role="admin")

    payload = client.get("/api/reminders/prioritized/cm_a1").json()

    assert payload["total_active"] == 2
    assert sum(payload["counts"].values()) == 2


def test_cross_org_direct_reminder_access_returns_404(ctx_mt):
    client = ctx_mt["client"]
    ctx_mt["holder"]["user"] = _user(org_id="org_a", role="admin")

    response = client.post("/api/reminders/rem-b/complete")

    assert response.status_code == 404
    with sqlite3.connect(ctx_mt["paths"]["reminders"]) as conn:
        status = conn.execute("SELECT status FROM active_reminders WHERE reminder_id = 'rem-b'").fetchone()[0]
    assert status == "Active"


def test_cross_org_direct_task_access_returns_404(ctx_mt):
    client = ctx_mt["client"]
    ctx_mt["holder"]["user"] = _user(org_id="org_a", role="admin")

    response = client.post("/api/reminders/tasks/task-b/complete")

    assert response.status_code == 404
    with sqlite3.connect(ctx_mt["paths"]["reminders"]) as conn:
        status = conn.execute("SELECT status FROM intelligent_tasks WHERE id = 'task-b'").fetchone()[0]
    assert status == "pending"


def test_case_manager_filter_cannot_cross_org(ctx_mt):
    client = ctx_mt["client"]
    ctx_mt["holder"]["user"] = _user(org_id="org_a", role="admin")

    assert client.get("/api/reminders/prioritized/cm_b1").status_code == 404
    assert client.get("/api/reminders/tasks?case_manager_id=cm_b1").status_code == 404


def test_tasks_admin_default_lists_only_caller_org(ctx_mt):
    client = ctx_mt["client"]
    ctx_mt["holder"]["user"] = _user(org_id="org_a", role="admin")

    payload = client.get("/api/reminders/tasks").json()

    assert payload["total_count"] == 1
    assert {task["task_id"] for task in payload["tasks"]} == {"task-a"}


def test_backfill_handles_client_staff_and_unresolved_rows(tmp_path, monkeypatch):
    core_db = tmp_path / "core_clients.db"
    auth_db = tmp_path / "auth.db"
    reminders_db = tmp_path / "reminders.db"
    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", core_db)
    monkeypatch.setattr(authz, "AUTH_DB", auth_db)
    monkeypatch.setattr(reminders_repo, "_SQLITE_CORE_CLIENTS_PATH", str(core_db))
    monkeypatch.setattr(reminders_repo, "_SQLITE_REMINDERS_PATH", str(reminders_db))
    monkeypatch.setattr(reminders_repo, "_sqlite_tenancy_ready", False)

    with sqlite3.connect(core_db) as conn:
        conn.execute("CREATE TABLE clients (client_id TEXT PRIMARY KEY, first_name TEXT, last_name TEXT, case_manager_id TEXT, org_id TEXT)")
        conn.execute("INSERT INTO clients VALUES (?,?,?,?,?)", ("client-a", "Ann", "A", "cm_a1", "org_a"))

    with sqlite3.connect(auth_db) as conn:
        conn.execute("CREATE TABLE user_profiles (firebase_uid TEXT, case_manager_id TEXT, org_id TEXT)")
        conn.execute("INSERT INTO user_profiles VALUES (?,?,?)", ("uid-cm_b1", "cm_b1", "org_b"))

    with sqlite3.connect(reminders_db) as conn:
        conn.execute(
            """
            CREATE TABLE active_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                case_manager_id TEXT NOT NULL,
                reminder_type TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT,
                due_date TEXT,
                status TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE intelligent_tasks (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                case_manager_id TEXT,
                task_type TEXT,
                title TEXT,
                description TEXT,
                priority TEXT,
                status TEXT,
                estimated_minutes INTEGER,
                due_date TEXT,
                completed_at TEXT,
                created_at TEXT,
                is_demo INTEGER DEFAULT 0
            )
            """
        )
        conn.executemany(
            "INSERT INTO active_reminders (reminder_id, client_id, case_manager_id, reminder_type, message, status) VALUES (?,?,?,?,?,?)",
            [
                ("client-linked", "client-a", "cm_b1", "general", "Client wins", "Active"),
                ("staff-scoped", "", "cm_b1", "general", "Staff wins", "Active"),
                ("unresolved", "", "", "general", "Default wins", "Active"),
            ],
        )
        conn.executemany(
            "INSERT INTO intelligent_tasks (id, client_id, case_manager_id, task_type, title, status) VALUES (?,?,?,?,?,?)",
            [
                ("task-client", "client-a", "cm_b1", "general", "Client task", "pending"),
                ("task-staff", "", "cm_b1", "general", "Staff task", "pending"),
                ("task-default", "", "", "general", "Default task", "pending"),
            ],
        )

    reminders_repo._ensure_sqlite_tenancy_schema(force=True)

    with sqlite3.connect(reminders_db) as conn:
        reminder_orgs = dict(conn.execute("SELECT reminder_id, org_id FROM active_reminders").fetchall())
        task_orgs = dict(conn.execute("SELECT id, org_id FROM intelligent_tasks").fetchall())

    assert reminder_orgs == {
        "client-linked": "org_a",
        "staff-scoped": "org_b",
        "unresolved": DEFAULT_ORG_ID,
    }
    assert task_orgs == {
        "task-client": "org_a",
        "task-staff": "org_b",
        "task-default": DEFAULT_ORG_ID,
    }
