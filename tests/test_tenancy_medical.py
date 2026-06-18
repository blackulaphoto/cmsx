"""Phase 3D2 tests: Medical org isolation.

Route-level: the medical list endpoints read three DBs via module-level path
constants (core_clients, case_management appointments, medical referrals), all
isolated to a tmp dir here. Flag OFF reproduces prior behavior; flag ON scopes
admin "all" to the caller's org and excludes other-org records.
"""
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.modules.medical.routes as med
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
    case_mgmt = tmp_path / "case_management.db"
    medical = tmp_path / "medical.db"

    monkeypatch.setattr(med, "CORE_CLIENTS_DB_PATH", core)
    monkeypatch.setattr(med, "CASE_MGMT_DB_PATH", case_mgmt)
    monkeypatch.setattr(med, "MEDICAL_DB_PATH", medical)
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

    med._ensure_case_management_appointments_table()
    med._ensure_medical_tables()
    with sqlite3.connect(case_mgmt) as conn:
        conn.executemany(
            "INSERT INTO appointments (id, client_id, case_manager_id, appointment_type, appointment_date) VALUES (?,?,?,?,?)",
            [
                ("apt-a", "a1", "cm_a1", "Medical Checkup", "2026-07-01"),
                ("apt-b", "b1", "cm_b1", "Medical Checkup", "2026-07-01"),
            ],
        )
        conn.commit()
    with sqlite3.connect(medical) as conn:
        conn.executemany(
            "INSERT INTO medical_referrals (referral_id, client_id, provider_name, provider_category) VALUES (?,?,?,?)",
            [
                ("ref-a", "a1", "Clinic A", "Primary Care"),
                ("ref-b", "b1", "Clinic B", "Primary Care"),
            ],
        )
        conn.commit()

    holder = {"user": _user()}
    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(med.router, prefix="/api/medical")
    return TestClient(app), holder


@pytest.fixture
def ctx_mt(ctx, monkeypatch):
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    return ctx


def _ids(resp, key):
    return {r["client_id"] for r in resp.json()[key]}


# ── Flag OFF: parity (admin sees all orgs) ──────────────────────────────────

def test_flag_off_admin_appointments_all(ctx):
    client, holder = ctx
    holder["user"] = _user(org_id="org_a", role="admin")
    assert _ids(client.get("/api/medical/appointments"), "appointments") == {"a1", "b1"}


def test_flag_off_admin_referrals_all(ctx):
    client, holder = ctx
    holder["user"] = _user(org_id="org_a", role="admin")
    assert _ids(client.get("/api/medical/referrals"), "referrals") == {"a1", "b1"}


# ── Flag ON: org isolation ──────────────────────────────────────────────────

def test_flag_on_admin_appointments_org_only(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", role="admin")
    ids = _ids(client.get("/api/medical/appointments"), "appointments")
    assert ids == {"a1"}
    assert "b1" not in ids


def test_flag_on_admin_referrals_org_only(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", role="admin")
    ids = _ids(client.get("/api/medical/referrals"), "referrals")
    assert ids == {"a1"}
    assert "b1" not in ids


def test_flag_on_cross_org_client_id_404(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", role="admin")
    # client_id-supplied path -> assert_client_access -> cross-org 404
    assert client.get("/api/medical/appointments", params={"client_id": "b1"}).status_code == 404
    assert client.get("/api/medical/referrals", params={"client_id": "b1"}).status_code == 404


def test_flag_on_same_org_client_id_ok(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_a", role="admin")
    assert client.get("/api/medical/appointments", params={"client_id": "a1"}).status_code == 200


def test_flag_on_other_org_admin_sees_own(ctx_mt):
    client, holder = ctx_mt
    holder["user"] = _user(org_id="org_b", case_manager_id="cm_b1", role="admin")
    assert _ids(client.get("/api/medical/appointments"), "appointments") == {"b1"}
    assert _ids(client.get("/api/medical/referrals"), "referrals") == {"b1"}
