"""Phase 1 multi-tenancy tests: org_id on the clients root.

Two regimes are exercised:
  - Flag OFF (default): behavior is identical to the single-agency app.
  - Flag ON: org isolation is enforced (create stamps org; cross-org access
    is denied with 404; admin lists are org-scoped).

DB access is isolated to a tmp dir by pointing DB_DIR (read at call-time inside
get_database_connection) and authorization.CORE_CLIENTS_DB at tmp_path. The
heavy cross-module propagation is stubbed so tests focus on the core insert.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.shared.db_path as db_path_mod
from backend.api import clients as clients_api
from backend.auth import authorization as authz
from backend.auth.service import AuthenticatedUser
from backend.shared.tenancy import DEFAULT_ORG_ID


def _user(org_id=DEFAULT_ORG_ID, case_manager_id="cm_a", role="case_manager"):
    return AuthenticatedUser(
        firebase_uid=f"uid-{case_manager_id}",
        email=f"{case_manager_id}@example.test",
        full_name="Test User",
        role=role,
        case_manager_id=case_manager_id,
        auth_provider="test",
        is_active=True,
        org_id=org_id,
        org_role="org_admin" if role == "admin" else "member",
    )


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    # Isolate every SQLite DB to the tmp dir.
    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp_path)
    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", tmp_path / "core_clients.db")
    # Keep create_client focused on the core insert.
    monkeypatch.setattr(clients_api, "propagate_client_to_modules", lambda *a, **k: {})
    monkeypatch.setattr(clients_api, "upsert_client_to_postgres", lambda *a, **k: {})

    holder = {"user": _user()}
    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(clients_api.router)
    return TestClient(app), holder


def _create_payload(first="Pat", cm="cm_a"):
    return {"first_name": first, "last_name": "Client", "case_manager_id": cm}


def _seed_client(client_id, case_manager_id, org_id):
    """Insert a client row directly with an explicit org_id."""
    with clients_api.get_database_connection("core_clients", "ADMIN") as conn:
        clients_api.ensure_core_clients_schema(conn)
        conn.execute(
            """
            INSERT INTO clients (client_id, first_name, last_name, case_manager_id,
                                 org_id, intake_date, created_at)
            VALUES (?, 'Seed', 'Client', ?, ?, '2026-01-01', '2026-01-01T00:00:00')
            """,
            (client_id, case_manager_id, org_id),
        )
        conn.commit()


# ── Flag OFF: parity ────────────────────────────────────────────────────────

def test_flag_off_create_and_get_roundtrip(ctx):
    client, holder = ctx
    holder["user"] = _user(role="admin", case_manager_id="cm_a")
    resp = client.post("/api/clients", json=_create_payload())
    assert resp.status_code == 200
    created = resp.json()["client"]
    cid = created["client_id"]

    got = client.get(f"/api/clients/{cid}")
    assert got.status_code == 200
    assert got.json()["client_id"] == cid


def test_flag_off_create_stamps_default_org(ctx):
    client, holder = ctx
    holder["user"] = _user(role="admin")
    cid = client.post("/api/clients", json=_create_payload()).json()["client"]["client_id"]
    assert authz.get_client_org_id(cid) == DEFAULT_ORG_ID


def test_flag_off_admin_lists_all_clients(ctx):
    client, holder = ctx
    # Two clients under different orgs in the data, but flag OFF => no org filter.
    _seed_client("c-default", "cm_a", DEFAULT_ORG_ID)
    _seed_client("c-other", "cm_b", "org_other")
    holder["user"] = _user(role="admin")
    listed = client.get("/api/clients").json()
    ids = {c["client_id"] for c in listed["clients"]}
    assert {"c-default", "c-other"} <= ids


def test_flag_off_case_manager_cannot_access_other_cm_client(ctx):
    # Existing case_manager_id scoping must still work unchanged.
    client, holder = ctx
    _seed_client("c1", "cm_owner", DEFAULT_ORG_ID)
    holder["user"] = _user(role="case_manager", case_manager_id="cm_other")
    assert client.get("/api/clients/c1").status_code == 403


# ── Flag ON: isolation ──────────────────────────────────────────────────────

@pytest.fixture
def ctx_mt(ctx, monkeypatch):
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    return ctx


def test_flag_on_create_stamps_user_org(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", role="admin", case_manager_id="cm_a")
    cid = client.post("/api/clients", json=_create_payload()).json()["client"]["client_id"]
    assert authz.get_client_org_id(cid) == "org_a"


def test_flag_on_case_manager_blocked_from_other_org_client(ctx_mt):
    client, holder = ctx_mt
    _seed_client("cb", "cm_b", "org_b")
    holder["user"] = _user(org_id="org_a", role="case_manager", case_manager_id="cm_b")
    # Same case_manager_id, but different org -> 404 (existence not disclosed).
    assert client.get("/api/clients/cb").status_code == 404


def test_flag_on_admin_blocked_from_other_org_client(ctx_mt):
    client, holder = ctx_mt
    _seed_client("cb", "cm_b", "org_b")
    holder["user"] = _user(org_id="org_a", role="admin", case_manager_id="cm_a")
    assert client.get("/api/clients/cb").status_code == 404


def test_flag_on_admin_accesses_own_org_client(ctx_mt):
    client, holder = ctx_mt
    _seed_client("ca", "cm_a", "org_a")
    holder["user"] = _user(org_id="org_a", role="admin", case_manager_id="cm_a")
    assert client.get("/api/clients/ca").status_code == 200


def test_flag_on_admin_list_is_org_scoped(ctx_mt):
    client, holder = ctx_mt
    _seed_client("ca", "cm_a", "org_a")
    _seed_client("cb", "cm_b", "org_b")
    holder["user"] = _user(org_id="org_a", role="admin", case_manager_id="cm_a")
    ids = {c["client_id"] for c in client.get("/api/clients").json()["clients"]}
    assert "ca" in ids
    assert "cb" not in ids


def test_flag_on_cross_org_update_and_delete_blocked(ctx_mt):
    client, holder = ctx_mt
    _seed_client("cb", "cm_b", "org_b")
    holder["user"] = _user(org_id="org_a", role="admin", case_manager_id="cm_a")
    assert client.put("/api/clients/cb", json={"first_name": "Hacked"}).status_code == 404
    assert client.delete("/api/clients/cb").status_code == 404


def test_flag_on_fails_closed_on_null_org(ctx_mt):
    # A row whose org_id is NULL must not be reachable when multi-tenant is on.
    client, holder = ctx_mt
    with clients_api.get_database_connection("core_clients", "ADMIN") as conn:
        clients_api.ensure_core_clients_schema(conn)
        # Bypass the backfill by writing NULL after schema-ensure.
        conn.execute(
            "INSERT INTO clients (client_id, first_name, last_name, case_manager_id, org_id, intake_date, created_at) "
            "VALUES ('cnull', 'No', 'Org', 'cm_a', NULL, '2026-01-01', '2026-01-01T00:00:00')",
        )
        conn.commit()
    holder["user"] = _user(org_id="org_a", role="admin", case_manager_id="cm_a")
    assert client.get("/api/clients/cnull").status_code == 404


# ── Backfill ────────────────────────────────────────────────────────────────

def test_schema_init_backfills_null_org_to_default(ctx):
    client, _ = ctx
    with clients_api.get_database_connection("core_clients", "ADMIN") as conn:
        clients_api.ensure_core_clients_schema(conn)
        conn.execute(
            "INSERT INTO clients (client_id, first_name, last_name, case_manager_id, org_id, intake_date, created_at) "
            "VALUES ('legacy', 'Legacy', 'Row', 'cm_a', NULL, '2026-01-01', '2026-01-01T00:00:00')",
        )
        conn.commit()
    # Re-run schema-ensure -> backfill.
    with clients_api.get_database_connection("core_clients", "ADMIN") as conn:
        clients_api.ensure_core_clients_schema(conn)
        row = conn.execute("SELECT org_id FROM clients WHERE client_id='legacy'").fetchone()
    assert row[0] == DEFAULT_ORG_ID
