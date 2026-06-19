"""Phase 3B tests: Dashboard aggregate org isolation.

Flag OFF: dashboard aggregates behave as the single-agency app. Flag ON: admin
stats, the supervisor team overview, /clients, and /case are scoped to the
caller's org; cross-org case_manager_id params and cross-org case ids do not leak.

DB isolation: the CoreClientService singleton's db_path is repointed at a tmp
core_clients.db; dashboard routes' _DB_DIR and authorization's CORE_CLIENTS_DB /
AUTH_DB are monkeypatched to the tmp dir.
"""
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.modules.dashboard.routes as dash_routes
from backend.modules.dashboard.routes import router as clickup_router
from backend.modules.dashboard.sqlite_routes import router as sqlite_router
from backend.modules.services import case_management_api as cma
from backend.auth import authorization as authz
from backend.auth.service import AuthenticatedUser
from backend.shared.tenancy import DEFAULT_ORG_ID


def _user(org_id=DEFAULT_ORG_ID, case_manager_id="cm_a1", role="admin"):
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


def _seed_core_clients(path):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE clients (
                client_id TEXT PRIMARY KEY, first_name TEXT, last_name TEXT,
                case_manager_id TEXT, org_id TEXT, risk_level TEXT, case_status TEXT,
                intake_date TEXT, created_at TEXT, barriers TEXT
            )
            """
        )
        rows = [
            ("a1", "A", "One", "cm_a1", "org_a", "high", "active", "2026-06-10", "2026-06-10T00:00:00", ""),
            ("a2", "A", "Two", "cm_a1", "org_a", "low", "active", "2026-06-10", "2026-06-10T00:00:00", ""),
            ("b1", "B", "One", "cm_b1", "org_b", "high", "active", "2026-06-10", "2026-06-10T00:00:00", ""),
        ]
        conn.executemany(
            "INSERT INTO clients (client_id, first_name, last_name, case_manager_id, org_id, risk_level, case_status, intake_date, created_at, barriers) VALUES (?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
        conn.commit()


def _seed_auth(path):
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE user_profiles (firebase_uid TEXT, case_manager_id TEXT, full_name TEXT, role TEXT, is_active INTEGER, org_id TEXT)"
        )
        conn.executemany(
            "INSERT INTO user_profiles (firebase_uid, case_manager_id, full_name, role, is_active, org_id) VALUES (?,?,?,?,?,?)",
            [
                ("uid-cm_a1", "cm_a1", "CM A1", "admin", 1, "org_a"),
                ("uid-cm_a2", "cm_a2", "CM A2", "case_manager", 1, "org_a"),
                ("uid-cm_b1", "cm_b1", "CM B1", "admin", 1, "org_b"),
            ],
        )
        conn.commit()


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    core = tmp_path / "core_clients.db"
    auth = tmp_path / "auth.db"
    _seed_core_clients(core)
    _seed_auth(auth)

    monkeypatch.setattr(cma.core_client_service, "db_path", str(core))
    monkeypatch.setattr(dash_routes, "_DB_DIR", tmp_path)
    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", core)
    monkeypatch.setattr(authz, "AUTH_DB", auth)

    holder = {"user": _user()}
    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(sqlite_router, prefix="/api/dashboard")
    app.include_router(clickup_router, prefix="/api")
    return TestClient(app), holder


@pytest.fixture
def ctx_mt(ctx, monkeypatch):
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    return ctx


# ── Flag OFF: parity ────────────────────────────────────────────────────────

def test_flag_off_admin_stats_sees_all_orgs(ctx):
    client, holder = ctx
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    stats = client.get("/api/dashboard/stats", params={"case_manager_id": "cm_a1"}).json()
    assert stats["stats"]["total_clients"] == 3  # both orgs (unchanged behavior)


def test_flag_off_supervisor_includes_all_orgs(ctx):
    client, holder = ctx
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    ov = client.get("/api/dashboard/supervisor/overview").json()["overview"]
    cm_ids = {c["case_manager_id"] for c in ov["case_managers"]}
    assert {"cm_a1", "cm_b1"} <= cm_ids  # cross-org visible when flag off


# ── Flag ON: isolation ──────────────────────────────────────────────────────

def test_flag_on_admin_stats_excludes_other_org(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    stats = client.get("/api/dashboard/stats", params={"case_manager_id": "cm_a1"}).json()
    assert stats["stats"]["total_clients"] == 2  # org_a only (a1, a2)


def test_flag_on_supervisor_excludes_other_org(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    ov = client.get("/api/dashboard/supervisor/overview").json()["overview"]
    cm_ids = {c["case_manager_id"] for c in ov["case_managers"]}
    assert "cm_a1" in cm_ids
    assert "cm_b1" not in cm_ids
    assert ov["team_summary"]["total_clients"] == 2


def test_flag_on_name_map_same_org_only(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    ov = client.get("/api/dashboard/supervisor/overview").json()["overview"]
    names = {c["case_manager_name"] for c in ov["case_managers"]}
    assert "CM B1" not in names


def test_flag_on_admin_cannot_pull_cross_org_case_manager(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    resp = client.get("/api/dashboard/clients", params={"case_manager_id": "cm_b1"}).json()
    assert resp["total_count"] == 0
    assert resp["clients"] == []


def test_flag_on_case_manager_cannot_query_other_org(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1", role="case_manager")
    # Non-admin requesting org B's CM resolves to their own (org_a) clients only.
    resp = client.get("/api/dashboard/clients", params={"case_manager_id": "cm_b1"}).json()
    returned_ids = {c["client_id"] for c in resp["clients"]}
    assert "b1" not in returned_ids


def test_flag_on_case_cross_org_returns_404(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    assert client.get("/api/dashboard/case/b1").status_code == 404


def test_flag_on_case_same_org_ok(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    resp = client.get("/api/dashboard/case/a1")
    assert resp.status_code == 200
    assert resp.json()["case"]["client_id"] == "a1"
