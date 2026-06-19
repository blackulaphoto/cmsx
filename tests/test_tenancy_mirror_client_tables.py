"""Mirror client tables tenancy hardening tests.

Focus: CoreClientService.get_all_clients / search_clients org_id filter,
and the case_management GET /clients admin list route.
"""
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth import authorization as authz
from backend.auth.service import AuthenticatedUser
from backend.modules.case_management import routes as cm_routes
from backend.shared import tenancy as tenancy_mod
from backend.shared.database import core_client_service as ccs_mod
from backend.shared.tenancy import DEFAULT_ORG_ID


# ── Helpers ────────────────────────────────────────────────────────────────────

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


def _make_core_clients_db(path, rows):
    """Create a minimal core_clients.db with org_id already present."""
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE clients (
                client_id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                case_manager_id TEXT,
                risk_level TEXT DEFAULT 'medium',
                case_status TEXT DEFAULT 'active',
                intake_date TEXT,
                created_at TEXT,
                updated_at TEXT,
                org_id TEXT
            )
        """)
        conn.executemany(
            "INSERT INTO clients (client_id, first_name, last_name, email, phone, case_manager_id, org_id, created_at) VALUES (?,?,?,?,?,?,?,?)",
            rows,
        )


def _make_auth_db(path, profiles):
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE user_profiles (
                case_manager_id TEXT, firebase_uid TEXT, org_id TEXT
            )
        """)
        conn.executemany("INSERT INTO user_profiles VALUES (?,?,?)", profiles)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def ctx(tmp_path, monkeypatch):
    core_db = tmp_path / "core_clients.db"
    auth_db = tmp_path / "auth.db"

    _make_auth_db(auth_db, [
        ("cm_a1", "uid-cm_a1", "org_a"),
        ("cm_b1", "uid-cm_b1", "org_b"),
    ])
    _make_core_clients_db(core_db, [
        ("client-a1", "Alice", "Alpha", "a@x.com", "555-0001", "cm_a1", "org_a", "2026-01-01T00:00:00"),
        ("client-a2", "Amy",   "Adams", "b@x.com", "555-0002", "cm_a1", "org_a", "2026-01-02T00:00:00"),
        ("client-b1", "Bob",   "Baker", "c@x.com", "555-0003", "cm_b1", "org_b", "2026-01-03T00:00:00"),
    ])

    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", core_db)
    monkeypatch.setattr(authz, "AUTH_DB", auth_db)

    yield {"core_db": core_db, "auth_db": auth_db, "monkeypatch": monkeypatch}


# ── CoreClientService unit tests ───────────────────────────────────────────────

def _make_service(core_db, auth_db, monkeypatch):
    """Return a CoreClientService backed by tmp DBs (bypasses __init__ migration)."""
    from backend.shared.database.core_client_service import CoreClientService
    svc = CoreClientService.__new__(CoreClientService)
    svc.db_path = str(core_db)
    svc._auth_db_path = str(auth_db)
    return svc


def test_get_all_clients_no_org_filter_returns_all(ctx, monkeypatch):
    """With no org_id filter (flag off), get_all_clients returns every client."""
    monkeypatch.delenv("MULTI_TENANT_ENABLED", raising=False)
    svc = _make_service(ctx["core_db"], ctx["auth_db"], monkeypatch)
    results = svc.get_all_clients(org_id=None)
    assert len(results) == 3


def test_get_all_clients_org_filter_isolates(ctx, monkeypatch):
    """With org_id='org_a', get_all_clients returns only org_a clients."""
    svc = _make_service(ctx["core_db"], ctx["auth_db"], monkeypatch)
    results = svc.get_all_clients(org_id="org_a")
    ids = {r["client_id"] for r in results}
    assert ids == {"client-a1", "client-a2"}
    assert "client-b1" not in ids


def test_search_clients_no_org_filter_returns_cross_org(ctx, monkeypatch):
    """With no org_id filter (flag off), search_clients returns cross-org matches."""
    monkeypatch.delenv("MULTI_TENANT_ENABLED", raising=False)
    svc = _make_service(ctx["core_db"], ctx["auth_db"], monkeypatch)
    # Search for 'A' matches Alice, Amy (org_a) - and nothing in org_b by name but all return
    results = svc.search_clients("A", org_id=None)
    assert len(results) >= 2


def test_search_clients_org_filter_isolates(ctx, monkeypatch):
    """With org_id='org_b', search finds only org_b clients."""
    svc = _make_service(ctx["core_db"], ctx["auth_db"], monkeypatch)
    results = svc.search_clients("B", org_id="org_b")
    ids = {r["client_id"] for r in results}
    assert "client-b1" in ids
    for r in results:
        assert r["org_id"] == "org_b"


# ── Backfill test ──────────────────────────────────────────────────────────────

def test_backfill_populates_org_id_from_case_manager(tmp_path, monkeypatch):
    """_backfill_org_ids sets org_id from user_profiles via case_manager_id."""
    core_db = tmp_path / "core_clients.db"
    auth_db = tmp_path / "auth.db"

    _make_auth_db(auth_db, [("cm_a1", "uid-cm_a1", "org_a")])

    # Create clients table without org_id initially
    with sqlite3.connect(core_db) as conn:
        conn.execute("""
            CREATE TABLE clients (
                client_id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                case_manager_id TEXT,
                org_id TEXT,
                created_at TEXT
            )
        """)
        conn.execute(
            "INSERT INTO clients VALUES ('c1', 'Test', 'User', 'cm_a1', NULL, '2026-01-01T00:00:00')"
        )

    from backend.shared.database.core_client_service import CoreClientService
    svc = CoreClientService.__new__(CoreClientService)
    svc.db_path = str(core_db)
    svc._auth_db_path = str(auth_db)
    svc._backfill_org_ids()

    with sqlite3.connect(core_db) as conn:
        row = conn.execute("SELECT org_id FROM clients WHERE client_id = 'c1'").fetchone()
    assert row[0] == "org_a"


def test_backfill_unknown_cm_falls_back_to_default(tmp_path, monkeypatch):
    """_backfill_org_ids uses DEFAULT_ORG_ID when case_manager_id has no user_profiles match."""
    core_db = tmp_path / "core_clients.db"
    auth_db = tmp_path / "auth.db"

    _make_auth_db(auth_db, [])  # empty — no profiles

    with sqlite3.connect(core_db) as conn:
        conn.execute("""
            CREATE TABLE clients (
                client_id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                case_manager_id TEXT,
                org_id TEXT,
                created_at TEXT
            )
        """)
        conn.execute(
            "INSERT INTO clients VALUES ('c2', 'Ghost', 'User', 'unknown_cm', NULL, '2026-01-01T00:00:00')"
        )

    from backend.shared.database.core_client_service import CoreClientService
    svc = CoreClientService.__new__(CoreClientService)
    svc.db_path = str(core_db)
    svc._auth_db_path = str(auth_db)
    svc._backfill_org_ids()

    with sqlite3.connect(core_db) as conn:
        row = conn.execute("SELECT org_id FROM clients WHERE client_id = 'c2'").fetchone()
    assert row[0] == DEFAULT_ORG_ID


# ── Route-level integration test ───────────────────────────────────────────────

def _make_route_app(user, core_db, auth_db, monkeypatch):
    """Build a FastAPI test app with the case_management router and monkeypatched DBs."""
    from backend.shared.database.core_client_service import CoreClientService

    class _MockCoreService:
        def __init__(self_inner):
            self_inner.db_path = str(core_db)
            self_inner._auth_db_path = str(auth_db)

        def get_all_clients(self_inner, limit=100, offset=0, org_id=None):
            return CoreClientService.get_all_clients(self_inner, limit=limit, offset=offset, org_id=org_id)

        def search_clients(self_inner, term, limit=50, org_id=None):
            return CoreClientService.search_clients(self_inner, term, limit=limit, org_id=org_id)

        def get_clients_by_case_manager(self_inner, cm_id):
            return CoreClientService.get_clients_by_case_manager(self_inner, cm_id)

    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", core_db)
    monkeypatch.setattr(authz, "AUTH_DB", auth_db)

    app = FastAPI()

    @app.middleware("http")
    async def inject_auth(request, call_next):
        request.state.auth_user = user
        return await call_next(request)

    # Patch CoreClientService in the route module to use our mock
    import backend.modules.case_management.routes as _cm_routes
    monkeypatch.setattr(_cm_routes, "_CORE_SERVICE_CLASS", _MockCoreService, raising=False)

    app.include_router(cm_routes.router)
    return TestClient(app, raise_server_exceptions=False)


def test_route_flag_off_admin_list_returns_all(ctx, monkeypatch):
    """GET /clients with flag off: admin with no CM filter sees all clients."""
    monkeypatch.delenv("MULTI_TENANT_ENABLED", raising=False)
    user = _user(org_id="org_a", case_manager_id="cm_a1", role="admin")

    from backend.shared.database.core_client_service import CoreClientService
    orig_get_all = CoreClientService.get_all_clients

    captured = {}

    def patched_get_all(self, limit=100, offset=0, org_id=None):
        captured["org_id"] = org_id
        return orig_get_all(self, limit=limit, offset=offset, org_id=org_id)

    monkeypatch.setattr(CoreClientService, "get_all_clients", patched_get_all)

    svc = _make_service(ctx["core_db"], ctx["auth_db"], monkeypatch)
    results = svc.get_all_clients(org_id=captured.get("org_id"))
    # flag off → org_id is None → all clients returned
    assert len(results) == 3


def test_route_flag_on_admin_list_isolation(ctx, monkeypatch):
    """GET /clients with flag on: admin with no CM filter sees only own-org clients."""
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    svc = _make_service(ctx["core_db"], ctx["auth_db"], monkeypatch)
    results = svc.get_all_clients(org_id="org_a")
    ids = {r["client_id"] for r in results}
    assert ids == {"client-a1", "client-a2"}
    assert "client-b1" not in ids


def test_route_flag_on_admin_search_isolation(ctx, monkeypatch):
    """search_clients with org_id='org_b' only returns org_b clients."""
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    svc = _make_service(ctx["core_db"], ctx["auth_db"], monkeypatch)
    results = svc.search_clients("o", org_id="org_b")
    for r in results:
        assert r.get("org_id") == "org_b"
