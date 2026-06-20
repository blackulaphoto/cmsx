#!/usr/bin/env python
"""SaaS activation harness v1 — local multi-tenant isolation validator.

Proves, locally and repeatably, that with ``MULTI_TENANT_ENABLED=true`` two
organizations are walled off from each other across the major tenant-scoped
modules. It is the local mirror of the per-deploy check described in
``docs/saas_staging_runbook.md``.

How it stays safe:
  * Every SQLite database is redirected to a throwaway temp dir via the
    ``CMSX_DB_DIR`` override (see ``backend/shared/db_path.py``). No tracked
    ``databases/*.db`` file is ever opened or mutated.
  * The override and the flag are set BEFORE any backend module is imported, so
    all module-level DB paths resolve to the temp dir automatically.

Run:
    python scripts/saas_harness.py        # validate; exits 0 on PASS, 1 on any leak
    python scripts/saas_harness.py --keep  # keep the temp dir for inspection

This is intentionally standalone (not pytest). The equivalent CI assertion lives
in ``tests/test_tenancy_two_org_wall.py``.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import date, timedelta

# ── Redirect storage + enable SaaS mode BEFORE importing any backend module ──
_TMP_DB_DIR = tempfile.mkdtemp(prefix="cmsx_saas_harness_")
os.environ["CMSX_DB_DIR"] = _TMP_DB_DIR
os.environ["MULTI_TENANT_ENABLED"] = "true"
os.environ.pop("DATABASE_URL", None)  # force SQLite path, never Postgres

# Make the repo root importable when run as `python scripts/saas_harness.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.shared.db_path as db_path_mod  # noqa: E402
from backend.api import clients as clients_api  # noqa: E402
from backend.auth import authorization as authz  # noqa: E402
from backend.auth.service import AuthenticatedUser  # noqa: E402
import backend.modules.legal.routes as legal_routes  # noqa: E402
from backend.modules.reminders import repository as reminders_repo  # noqa: E402
from backend.modules.reminders import routes as reminders_routes  # noqa: E402
from backend.modules.messages.routes import get_messages_db, router as messages_router  # noqa: E402


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


def org_a_admin():
    return _user("org_a", "cm_a1", "admin")


def org_b_admin():
    return _user("org_b", "cm_b1", "admin")


class _FakeDataIntegrator:
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


def _seed():
    db_dir = db_path_mod.DB_DIR

    # core_clients (real schema) — one client per org
    with clients_api.get_database_connection("core_clients", "ADMIN") as conn:
        clients_api.ensure_core_clients_schema(conn)
        conn.executemany(
            """
            INSERT INTO clients (client_id, first_name, last_name, case_manager_id,
                                 org_id, intake_date, created_at)
            VALUES (?, ?, 'Client', ?, ?, '2026-01-01', '2026-01-01T00:00:00')
            """,
            [("client-a", "Ann", "cm_a1", "org_a"), ("client-b", "Bob", "cm_b1", "org_b")],
        )
        conn.commit()

    # auth profiles (for messages participant org resolution). The real
    # user_profiles schema already exists (created at import); insert full rows.
    now = "2026-01-01T00:00:00"
    with sqlite3.connect(db_dir / "auth.db") as conn:
        conn.executemany(
            """INSERT OR REPLACE INTO user_profiles
                 (firebase_uid, email, full_name, role, case_manager_id,
                  auth_provider, is_active, created_at, updated_at, org_id)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            [
                ("uid-cm_a1", "cm_a1@example.test", "CM A1", "admin", "cm_a1", "test", 1, now, now, "org_a"),
                ("uid-cm_a2", "cm_a2@example.test", "CM A2", "case_manager", "cm_a2", "test", 1, now, now, "org_a"),
                ("uid-cm_b1", "cm_b1@example.test", "CM B1", "admin", "cm_b1", "test", 1, now, now, "org_b"),
                ("uid-cm_b2", "cm_b2@example.test", "CM B2", "case_manager", "cm_b2", "test", 1, now, now, "org_b"),
            ],
        )
        conn.commit()

    # reminders + tasks, one per org. Drop the import-created tables and rebuild
    # with org_id (throwaway DB) so the schema is known and org-stamped.
    with sqlite3.connect(db_dir / "reminders.db") as conn:
        conn.execute("DROP TABLE IF EXISTS active_reminders")
        conn.execute("DROP TABLE IF EXISTS intelligent_tasks")
        conn.execute(
            """CREATE TABLE active_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT, reminder_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL, case_manager_id TEXT NOT NULL, reminder_type TEXT NOT NULL,
                message TEXT NOT NULL, priority TEXT DEFAULT 'Medium', due_date TEXT,
                status TEXT DEFAULT 'Active', created_at TEXT, org_id TEXT)"""
        )
        conn.execute(
            """CREATE TABLE intelligent_tasks (
                id TEXT PRIMARY KEY, client_id TEXT NOT NULL, case_manager_id TEXT, task_type TEXT,
                title TEXT, description TEXT, priority TEXT, status TEXT, estimated_minutes INTEGER,
                due_date TEXT, completed_at TEXT, created_at TEXT, is_demo INTEGER DEFAULT 0, org_id TEXT)"""
        )
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        conn.executemany(
            "INSERT INTO active_reminders (reminder_id, client_id, case_manager_id, reminder_type, message, priority, due_date, status, created_at, org_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                ("rem-a", "client-a", "cm_a1", "general", "A", "High", tomorrow, "Active", "2030-01-01T00:00:00", "org_a"),
                ("rem-b", "client-b", "cm_b1", "general", "B", "High", tomorrow, "Active", "2030-01-01T00:00:00", "org_b"),
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


def _build_client(holder):
    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(clients_api.router)
    app.include_router(reminders_routes.router, prefix="/api/reminders")
    app.include_router(messages_router, prefix="/api/messages")
    return TestClient(app)


def run() -> int:
    reminders_repo._sqlite_tenancy_ready = False
    reminders_routes.data_integrator = _FakeDataIntegrator()
    _seed()

    holder = {"user": org_a_admin()}
    client = _build_client(holder)

    # Seed one DM thread per org.
    holder["user"] = org_a_admin()
    client.post("/api/messages/threads", json={
        "thread_type": "direct_message", "title": "A-thread",
        "participants": [{"user_id": "cm_a2"}], "initial_message": "hi A"})
    holder["user"] = org_b_admin()
    client.post("/api/messages/threads", json={
        "thread_type": "direct_message", "title": "B-thread",
        "participants": [{"user_id": "cm_b2"}], "initial_message": "hi B"})

    # ── Act as Org A admin; each module must show only org_a, never org_b ──
    holder["user"] = org_a_admin()
    results = []  # (module, passed, detail)

    try:
        ids = {c["client_id"] for c in client.get("/api/clients").json()["clients"]}
        ok = "client-a" in ids and "client-b" not in ids
        results.append(("Core clients  GET /api/clients", ok, f"saw={sorted(ids)}"))
    except Exception as exc:  # noqa: BLE001
        results.append(("Core clients  GET /api/clients", False, f"error: {exc}"))

    try:
        tasks = {t["task_id"] for t in client.get("/api/reminders/tasks").json()["tasks"]}
        ok = "task-a" in tasks and "task-b" not in tasks
        results.append(("Reminders     GET /api/reminders/tasks", ok, f"saw={sorted(tasks)}"))
    except Exception as exc:  # noqa: BLE001
        results.append(("Reminders     GET /api/reminders/tasks", False, f"error: {exc}"))

    try:
        titles = {t.get("title") for t in client.get("/api/messages/threads").json()["threads"]}
        ok = "A-thread" in titles and "B-thread" not in titles
        results.append(("Messages      GET /api/messages/threads", ok, f"saw={sorted(t for t in titles if t)}"))
    except Exception as exc:  # noqa: BLE001
        results.append(("Messages      GET /api/messages/threads", False, f"error: {exc}"))

    try:
        legal_ids = set(legal_routes._get_accessible_client_ids(org_a_admin()))
        clinical_ids = set(authz.get_client_ids_for_org("org_a"))
        ok = legal_ids == {"client-a"} and clinical_ids == {"client-a"}
        results.append(("Legal/clinical scoping seam", ok, f"legal={sorted(legal_ids)} clinical={sorted(clinical_ids)}"))
    except Exception as exc:  # noqa: BLE001
        results.append(("Legal/clinical scoping seam", False, f"error: {exc}"))

    # ── Report ──
    print("\nSaaS Activation Harness v1 - 2-org wall (MULTI_TENANT_ENABLED=true)")
    print(f"Throwaway DB dir: {_TMP_DB_DIR}")
    print("-" * 72)
    all_pass = True
    for module, ok, detail in results:
        all_pass = all_pass and ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {module:<42} {detail}")
    print("-" * 72)
    print("RESULT:", "PASS - Org A and Org B are walled off." if all_pass
          else "FAIL - cross-org leak detected. Do NOT enable MT in any hosted env.")
    return 0 if all_pass else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="SaaS activation harness v1")
    parser.add_argument("--keep", action="store_true", help="keep the throwaway DB dir for inspection")
    args = parser.parse_args()
    try:
        return run()
    finally:
        if args.keep:
            print(f"(kept throwaway DB dir: {_TMP_DB_DIR})")
        else:
            shutil.rmtree(_TMP_DB_DIR, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
