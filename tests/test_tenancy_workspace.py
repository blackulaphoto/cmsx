"""Phase 3C tests: Workspace Content org isolation.

Flag OFF: dashboard items + rolodex behave as the single-agency app. Flag ON:
dashboard notes/docs/bookmarks/resources and the rolodex are org-scoped; an
admin in org A cannot read/update/delete/download org B items (cross-org -> 404).
Client-linked tables remain protected by the existing assert_client_access.

Isolation: a fresh WorkspaceStore is pointed at a tmp DB and patched into the
dashboard + rolodex route modules; authorization's CORE_CLIENTS_DB / AUTH_DB are
monkeypatched for the client-linked defense check.
"""
import sqlite3

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import backend.modules.dashboard.routes as dash_routes
import backend.modules.rolodex.routes as rolodex_routes
from backend.modules.dashboard.routes import router as dashboard_router
from backend.modules.rolodex.routes import router as rolodex_router
from backend.shared.database.workspace_store import WorkspaceStore
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


def _fresh_store(path):
    ws = WorkspaceStore.__new__(WorkspaceStore)  # bypass real-path __init__
    ws.db_path = path
    ws._initialize()
    return ws


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    ws = _fresh_store(tmp_path / "workspace_content.db")
    monkeypatch.setattr(dash_routes, "workspace_store", ws)
    monkeypatch.setattr(rolodex_routes, "workspace_store", ws)

    holder = {"user": _user()}
    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(dashboard_router, prefix="/api")
    app.include_router(rolodex_router, prefix="/api")
    return TestClient(app), holder, ws


@pytest.fixture
def ctx_mt(ctx, monkeypatch):
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    return ctx


# ── Flag OFF: parity ────────────────────────────────────────────────────────

def test_flag_off_doc_roundtrip(ctx):
    client, holder, _ = ctx
    holder["user"] = _user(case_manager_id="cm_a1", role="case_manager")
    created = client.post("/api/dashboard/docs", json={"title": "T", "content": "C"}).json()["doc"]
    docs = client.get("/api/dashboard/docs").json()["docs"]
    assert any(d["id"] == created["id"] for d in docs)


def test_flag_off_rolodex_roundtrip(ctx):
    client, holder, _ = ctx
    holder["user"] = _user(case_manager_id="cm_a1")
    client.post("/api/rolodex", json={"name": "Clinic", "category": "Primary Care"})
    entries = client.get("/api/rolodex").json()["entries"]
    assert len(entries) == 1


# ── Flag ON: dashboard isolation ────────────────────────────────────────────

def _make_doc(client):
    return client.post("/api/dashboard/docs", json={"title": "A doc", "content": "secret"}).json()["doc"]["id"]


def test_flag_on_doc_cross_org_blocked(ctx_mt):
    client, holder, _ = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    doc_id = _make_doc(client)

    holder["user"] = _user(org_id="org_b", case_manager_id="cm_b1", role="admin")
    assert client.get(f"/api/dashboard/docs/{doc_id}/download").status_code == 404
    assert client.put(f"/api/dashboard/docs/{doc_id}", json={"title": "x", "content": "y"}).status_code == 404
    assert client.delete(f"/api/dashboard/docs/{doc_id}").status_code == 404


def test_flag_on_doc_same_org_ok(ctx_mt):
    client, holder, _ = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    doc_id = _make_doc(client)
    assert client.get(f"/api/dashboard/docs/{doc_id}/download?format=txt").status_code == 200


def test_flag_on_note_cross_org_blocked(ctx_mt):
    client, holder, _ = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    note_id = client.post("/api/dashboard/notes", json={"content": "n"}).json()["note"]["id"]
    holder["user"] = _user(org_id="org_b", case_manager_id="cm_b1", role="admin")
    assert client.put(f"/api/dashboard/notes/{note_id}", json={"content": "x"}).status_code == 404
    assert client.delete(f"/api/dashboard/notes/{note_id}").status_code == 404


def test_flag_on_bookmark_cross_org_blocked(ctx_mt):
    client, holder, _ = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    bm_id = client.post("/api/dashboard/bookmarks", json={"title": "b", "url": "https://x.com"}).json()["bookmark"]["id"]
    holder["user"] = _user(org_id="org_b", case_manager_id="cm_b1", role="admin")
    assert client.delete(f"/api/dashboard/bookmarks/{bm_id}").status_code == 404


def test_flag_on_resource_cross_org_blocked(ctx_mt):
    client, holder, ws = ctx_mt
    # Seed a resource directly under org_a.
    ws.create_dashboard_resource("cm_a1", "res-a", "file.txt", 10, "text/plain", "file.txt", org_id="org_a")
    holder["user"] = _user(org_id="org_b", case_manager_id="cm_b1", role="admin")
    assert client.get("/api/dashboard/resources/res-a/download").status_code == 404
    assert client.delete("/api/dashboard/resources/res-a").status_code == 404


# ── Flag ON: rolodex isolation (Option A) ───────────────────────────────────

def test_flag_on_rolodex_org_scoped(ctx_mt):
    client, holder, _ = ctx_mt
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1")
    entry_id = client.post("/api/rolodex", json={"name": "Org A Clinic", "category": "Primary Care"}).json()["entry"]["id"]

    # org B sees none of org A's entries
    holder["user"] = _user(org_id="org_b", case_manager_id="cm_b1")
    assert client.get("/api/rolodex").json()["entries"] == []
    assert client.put(f"/api/rolodex/{entry_id}", json={"name": "hack", "category": "Primary Care"}).status_code == 404
    assert client.delete(f"/api/rolodex/{entry_id}").status_code == 404

    # org A still sees its own
    holder["user"] = _user(org_id="org_a", case_manager_id="cm_a1")
    names = {e["name"] for e in client.get("/api/rolodex").json()["entries"]}
    assert "Org A Clinic" in names


# ── Client-linked defense (assert_client_access still enforces org) ──────────

def test_client_linked_cross_org_blocked_via_assert(tmp_path, monkeypatch):
    core = tmp_path / "core_clients.db"
    with sqlite3.connect(core) as conn:
        conn.execute(
            "CREATE TABLE clients (client_id TEXT PRIMARY KEY, case_manager_id TEXT, org_id TEXT)"
        )
        conn.execute("INSERT INTO clients VALUES ('client-b', 'cm_b1', 'org_b')")
        conn.commit()
    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", core)
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    user = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")
    with pytest.raises(HTTPException) as exc:
        authz.assert_client_access(user, "client-b")
    assert exc.value.status_code == 404
