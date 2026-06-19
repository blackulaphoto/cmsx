"""Phase 2 guard-coverage tests.

Verifies that the central guard protects client-data endpoints in
housing/jobs/resume while global search/reference routes stay open, and that
the documented classification list does not silently drift.

DB access is isolated to a tmp dir (DB_DIR is read at call-time inside
get_database_connection; authorization.CORE_CLIENTS_DB is patched to match).
Tests assert the GUARD boundary (deny -> 404/401 before any module DB work,
allow -> passes the guard), not the downstream module behavior.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.shared.db_path as db_path_mod
from backend.api import clients as clients_api
from backend.auth import authorization as authz
from backend.auth.service import AuthenticatedUser
from backend.modules.housing import routes as housing_routes
from backend.modules.jobs import routes as jobs_routes
from backend.modules.resume import routes as resume_routes
from backend.shared.tenancy import DEFAULT_ORG_ID


def _user(org_id=DEFAULT_ORG_ID, case_manager_id="cm_a", role="admin"):
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
    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp_path)
    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", tmp_path / "core_clients.db")
    holder = {"user": _user()}

    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        # Mirror the real global middleware: set auth_user when present.
        if holder["user"] is not None:
            request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(housing_routes.router, prefix="/api/housing")
    app.include_router(jobs_routes.router, prefix="/api/jobs")
    app.include_router(resume_routes.router, prefix="/api/resume")
    return TestClient(app), holder


@pytest.fixture
def ctx_mt(ctx, monkeypatch):
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    return ctx


def _seed_client(client_id, case_manager_id, org_id):
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


# ── Global / exempt routes stay open ────────────────────────────────────────

def test_global_routes_not_guarded(ctx):
    client, _ = ctx
    assert client.get("/api/housing/").status_code == 200       # housing_api_info
    assert client.get("/api/jobs/search").status_code == 200    # get_search_info
    assert client.get("/api/resume/").status_code == 200        # resume_dashboard


# ── Guarded endpoints: deny path (guard fires before module DB work) ─────────

def test_guarded_jobs_saved_allows_same_org(ctx):
    client, holder = ctx
    _seed_client("c1", "cm_a", DEFAULT_ORG_ID)
    holder["user"] = _user(role="admin", case_manager_id="cm_a")
    # Guard passes; endpoint returns gracefully (empty list) -> 200.
    assert client.get("/api/jobs/saved/c1").status_code == 200


def test_guarded_endpoint_unauthenticated_401(ctx):
    client, holder = ctx
    _seed_client("c1", "cm_a", DEFAULT_ORG_ID)
    holder["user"] = None  # no auth_user injected
    assert client.get("/api/jobs/saved/c1").status_code == 401


def test_guarded_endpoint_missing_client_404(ctx):
    client, holder = ctx
    _seed_client("c1", "cm_a", DEFAULT_ORG_ID)  # ensures the clients table exists
    holder["user"] = _user(role="admin")
    assert client.get("/api/jobs/saved/does-not-exist").status_code == 404


def test_flag_off_case_manager_scoping_preserved(ctx):
    # Existing single-agency case-manager ownership still applies (flag off).
    client, holder = ctx
    _seed_client("c1", "cm_owner", DEFAULT_ORG_ID)
    holder["user"] = _user(role="case_manager", case_manager_id="cm_other")
    assert client.get("/api/jobs/saved/c1").status_code == 403


# ── Flag on: cross-org isolation on guarded endpoints (all -> 404) ───────────

def test_flag_on_cross_org_jobs_saved(ctx_mt):
    client, holder = ctx_mt
    _seed_client("cb", "cm_b", "org_b")
    holder["user"] = _user(org_id="org_a", role="admin", case_manager_id="cm_a")
    assert client.get("/api/jobs/saved/cb").status_code == 404


def test_flag_on_cross_org_housing_applications(ctx_mt):
    client, holder = ctx_mt
    _seed_client("cb", "cm_b", "org_b")
    holder["user"] = _user(org_id="org_a", role="admin", case_manager_id="cm_a")
    assert client.get("/api/housing/applications/cb").status_code == 404


def test_flag_on_cross_org_housing_application_post(ctx_mt):
    client, holder = ctx_mt
    _seed_client("cb", "cm_b", "org_b")
    holder["user"] = _user(org_id="org_a", role="admin", case_manager_id="cm_a")
    resp = client.post(
        "/api/housing/application",
        json={"client_id": "cb", "housing_resource_id": "hr1"},
    )
    assert resp.status_code == 404


def test_flag_on_cross_org_resume_profile(ctx_mt):
    client, holder = ctx_mt
    _seed_client("cb", "cm_b", "org_b")
    holder["user"] = _user(org_id="org_a", role="admin", case_manager_id="cm_a")
    assert client.get("/api/resume/profile/cb").status_code == 404


# ── Mixed routes: global branch open, client branch guarded ──────────────────

def test_mixed_dashboard_open_without_client_id(ctx):
    client, holder = ctx
    holder["user"] = _user(role="admin")
    # No client_id -> static dashboard, no guard -> 200.
    assert client.get("/api/housing/case-manager-dashboard").status_code == 200


def test_mixed_dashboard_guarded_with_cross_org_client(ctx_mt):
    client, holder = ctx_mt
    _seed_client("cb", "cm_b", "org_b")
    holder["user"] = _user(org_id="org_a", role="admin", case_manager_id="cm_a")
    resp = client.get("/api/housing/case-manager-dashboard", params={"client_id": "cb"})
    assert resp.status_code == 404


# ── Documentation drift guard ────────────────────────────────────────────────

def test_guarded_route_doc_matches_expected():
    expected = {
        "POST /api/housing/application",
        "GET /api/housing/applications/{client_id}",
        "POST /api/jobs/save",
        "GET /api/jobs/saved/{client_id}",
        "POST /api/resume/profile",
        "GET /api/resume/profile/{client_id}",
        "GET /api/resume/resumes/{client_id}",
        "GET /api/resume/list/{client_id}",
        "POST /api/resume/create",
        "POST /api/resume/apply-job",
        "GET /api/resume/applications/{client_id}",
    }
    assert authz.TENANCY_GUARDED_ROUTES == expected


def test_services_not_in_guarded_set():
    assert not any("services" in route for route in authz.TENANCY_GUARDED_ROUTES)
