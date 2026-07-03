"""Tests for the housing leads pipeline.

Covers:
- housing_applications table creation (previously missing entirely)
- POST /api/housing/leads persists a client-linked lead
- lead is retrievable via GET /api/housing/applications/{client_id}
- resource dedupe by title
- truthful failure paths (missing title, unknown client)
- no cross-client leakage
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.modules.housing.routes as housing_routes
from backend.api import clients as clients_api
from backend.auth.service import FirebaseAuthService
from backend.modules.housing.models import HousingDatabase


def _headers(case_manager_id="cm_test", email="case.manager@example.test", role="case_manager"):
    return {
        "X-Test-Auth-Email": email,
        "X-Test-Auth-Case-Manager-Id": case_manager_id,
        "X-Test-Auth-Role": role,
    }


def _seed_core_client(client_id, case_manager_id="cm_test"):
    with clients_api.get_database_connection("core_clients", "ADMIN") as conn:
        clients_api.ensure_core_clients_schema(conn)
        conn.execute(
            """INSERT INTO clients
               (client_id, first_name, last_name, case_manager_id, risk_level,
                intake_date, created_at, date_of_birth)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                client_id, "Housing", "Client", case_manager_id, "medium",
                "2026-06-01", datetime.utcnow().isoformat(), "1990-01-01",
            ),
        )
        conn.commit()
    return client_id


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path(tmp_path / "databases").mkdir(exist_ok=True)

    # Force a fresh housing DB inside the temp dir.
    monkeypatch.setattr(housing_routes, "housing_db", None)

    # Make sure the core clients schema exists so auth lookups return
    # "not found" rather than crashing on a missing table.
    with clients_api.get_database_connection("core_clients", "ADMIN") as conn:
        clients_api.ensure_core_clients_schema(conn)
        conn.commit()

    service = FirebaseAuthService(tmp_path / "auth.db")
    app = FastAPI()

    @app.middleware("http")
    async def inject_test_auth_user(request, call_next):
        request.state.auth_user = service.test_user_from_request(request)
        return await call_next(request)

    app.include_router(housing_routes.router, prefix="/api/housing")
    return TestClient(app)


def _lead_payload(client_id, title="Sunset Rooms NoHo", url="https://example.com/listing/1"):
    return {
        "client_id": client_id,
        "title": title,
        "url": url,
        "description": "2BR near transit",
        "source": "google_housing_cse",
        "location": "North Hollywood, CA",
        "price": "$1,400",
    }


def test_housing_applications_table_is_created(app_client, tmp_path):
    # Touch the DB through the routes module so create_tables runs.
    db = housing_routes.get_housing_db()
    assert db is not None
    conn = sqlite3.connect(tmp_path / "databases" / "housing_resources.db")
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "housing_applications" in tables
    assert "housing_resources" in tables


def test_save_lead_persists_and_reads_back(app_client):
    client_id = _seed_core_client("client-housing-1")

    resp = app_client.post("/api/housing/leads", json=_lead_payload(client_id), headers=_headers())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["application_id"], "application_id must not be empty"
    assert body["housing_resource_id"]

    # Read back through the client-scoped endpoint (survives "refresh").
    resp2 = app_client.get(f"/api/housing/applications/{client_id}", headers=_headers())
    assert resp2.status_code == 200, resp2.text
    apps = resp2.json()["applications"]
    assert len(apps) == 1
    assert apps[0]["facility_name"] == "Sunset Rooms NoHo"
    assert "https://example.com/listing/1" in (apps[0]["notes"] or "")
    assert apps[0]["status"] == "Submitted"


def test_save_lead_dedupes_resource_by_title(app_client):
    client_id = _seed_core_client("client-housing-2")

    r1 = app_client.post("/api/housing/leads", json=_lead_payload(client_id), headers=_headers())
    r2 = app_client.post("/api/housing/leads", json=_lead_payload(client_id), headers=_headers())
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["housing_resource_id"] == r2.json()["housing_resource_id"]
    # Distinct application records are allowed; ids must differ.
    assert r1.json()["application_id"] != r2.json()["application_id"]


def test_save_lead_requires_title(app_client):
    client_id = _seed_core_client("client-housing-3")
    payload = _lead_payload(client_id, title="   ")
    resp = app_client.post("/api/housing/leads", json=payload, headers=_headers())
    assert resp.status_code == 422


def test_save_lead_unknown_client_is_404(app_client):
    resp = app_client.post(
        "/api/housing/leads",
        json=_lead_payload("client-does-not-exist"),
        headers=_headers(),
    )
    assert resp.status_code == 404


def test_no_cross_client_leakage(app_client):
    client_a = _seed_core_client("client-housing-a", case_manager_id="cm_test")
    client_b = _seed_core_client("client-housing-b", case_manager_id="cm_test")
    client_other = _seed_core_client("client-housing-other", case_manager_id="cm_other")

    resp = app_client.post("/api/housing/leads", json=_lead_payload(client_a), headers=_headers())
    assert resp.status_code == 200

    # Same case manager, different client: no leakage.
    apps_b = app_client.get(f"/api/housing/applications/{client_b}", headers=_headers())
    assert apps_b.status_code == 200
    assert apps_b.json()["applications"] == []

    # Different case manager cannot read another CM's client at all.
    denied = app_client.get(f"/api/housing/applications/{client_a}", headers=_headers(case_manager_id="cm_other"))
    assert denied.status_code == 403

    # And cannot save a lead against it either.
    denied_save = app_client.post(
        "/api/housing/leads",
        json=_lead_payload(client_a),
        headers=_headers(case_manager_id="cm_other"),
    )
    assert denied_save.status_code == 403

    # Sanity: the other CM's own client has no phantom leads.
    apps_other = app_client.get(
        f"/api/housing/applications/{client_other}",
        headers=_headers(case_manager_id="cm_other"),
    )
    assert apps_other.status_code == 200
    assert apps_other.json()["applications"] == []
