"""Phase 3D3 tests: Benefits org isolation.

Route-level: GET /applications reads benefits_applications (unified_platform.db)
and client names + accessible-client-ids (core_clients.db), all via the module's
_DB_DIR which is isolated to a tmp dir here. Flag OFF reproduces prior behavior;
flag ON scopes admin "all" to the caller's org.
"""
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.modules.benefits.routes as ben
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


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    core = tmp_path / "core_clients.db"
    monkeypatch.setattr(ben, "_DB_DIR", tmp_path)
    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", core)

    with sqlite3.connect(core) as conn:
        conn.execute(
            "CREATE TABLE clients (client_id TEXT PRIMARY KEY, first_name TEXT, last_name TEXT, case_manager_id TEXT, org_id TEXT)"
        )
        conn.executemany(
            "INSERT INTO clients VALUES (?,?,?,?,?)",
            [
                ("a1", "Ann", "A", "cm_a1", "org_a"),
                ("b1", "Bob", "B", "cm_b1", "org_b"),
            ],
        )
        conn.commit()

    ben.ensure_benefits_applications_schema()
    with sqlite3.connect(tmp_path / "unified_platform.db") as conn:
        conn.executemany(
            "INSERT INTO benefits_applications (client_id, application_id, benefit_type, status) VALUES (?,?,?,?)",
            [
                ("a1", "app-a", "SNAP", "Pending"),
                ("b1", "app-b", "SNAP", "Pending"),
            ],
        )
        conn.commit()

    holder = {"user": _user()}
    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(ben.router, prefix="/api/benefits")
    return TestClient(app), holder


@pytest.fixture
def ctx_mt(ctx, monkeypatch):
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    return ctx


def _ids(resp):
    return {a["client_id"] for a in resp.json()["applications"]}


# ── Flag OFF: parity ────────────────────────────────────────────────────────

def test_flag_off_admin_sees_all(ctx):
    client, holder = ctx
    holder["user"] = _user(org_id="org_a", role="admin")
    assert _ids(client.get("/api/benefits/applications")) == {"a1", "b1"}


# ── Flag ON: org isolation ──────────────────────────────────────────────────

def test_flag_on_admin_org_only(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", role="admin")
    ids = _ids(client.get("/api/benefits/applications"))
    assert ids == {"a1"}
    assert "b1" not in ids


def test_flag_on_other_org_admin_sees_own(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_b", case_manager_id="cm_b1", role="admin")
    assert _ids(client.get("/api/benefits/applications")) == {"b1"}


def test_flag_on_cross_org_client_id_404(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", role="admin")
    assert client.get("/api/benefits/applications", params={"client_id": "b1"}).status_code == 404


def test_flag_on_same_org_client_id_ok(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", role="admin")
    resp = client.get("/api/benefits/applications", params={"client_id": "a1"})
    assert resp.status_code == 200
    assert _ids(resp) == {"a1"}


def test_flag_on_nonadmin_own_org_only(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1", role="case_manager")
    ids = _ids(client.get("/api/benefits/applications"))
    assert ids == {"a1"}
    assert "b1" not in ids
