"""Phase 3D4 tests: FMLA and UR org isolation."""
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.modules.fmla.routes as fmla_routes
import backend.modules.ur.routes as ur_routes
from backend.auth import authorization as authz
from backend.auth.service import AuthenticatedUser
from backend.modules.fmla.store import FMLAStore
from backend.modules.ur.store import URStore
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
    core_db = tmp_path / "core_clients.db"
    auth_db = tmp_path / "auth.db"
    fmla_db = tmp_path / "fmla.db"
    reminders_db = tmp_path / "reminders.db"
    ur_db = tmp_path / "ur.db"

    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", core_db)
    monkeypatch.setattr(authz, "AUTH_DB", auth_db)

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
        conn.commit()

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
        conn.commit()

    with sqlite3.connect(reminders_db) as conn:
        conn.execute(
            """
            CREATE TABLE active_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id TEXT UNIQUE NOT NULL,
                client_id TEXT,
                case_manager_id TEXT,
                reminder_type TEXT,
                message TEXT,
                priority TEXT,
                due_date TEXT,
                status TEXT,
                created_at TEXT
            )
            """
        )
        conn.commit()

    fmla_store = FMLAStore(str(fmla_db), str(reminders_db))
    ur_store = URStore(str(ur_db))

    original_fmla_store = fmla_routes.store
    original_ur_store = ur_routes.store
    fmla_routes.store = fmla_store
    ur_routes.store = ur_store

    holder = {"user": _user()}
    app = FastAPI()

    @app.middleware("http")
    async def inject_user(request, call_next):
        request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(fmla_routes.router, prefix="/api")
    app.include_router(ur_routes.router, prefix="/api")

    yield {
        "client": TestClient(app),
        "holder": holder,
        "fmla": fmla_store,
        "ur": ur_store,
        "paths": {
            "fmla": fmla_db,
            "reminders": reminders_db,
            "ur": ur_db,
        },
    }

    fmla_routes.store = original_fmla_store
    ur_routes.store = original_ur_store


@pytest.fixture
def ctx_mt(ctx, monkeypatch):
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    return ctx


def _fmla_case(store, **overrides):
    payload = {
        "client_id": "client-a",
        "client_name": "Ann A",
        "assigned_case_manager": "cm_a1",
        "employer_name": "Employer",
        "fmla_request_type": "new request",
        "leave_type": "continuous",
        "status": "pending documents",
        "approval_status": "pending",
        "org_id": "org_a",
    }
    payload.update(overrides)
    return store.create_case(payload)


def _ur_case(store, **overrides):
    payload = {
        "client_id": "client-a",
        "client_name": "Ann A",
        "assigned_case_manager": "cm_a1",
        "payer": "Health Net",
        "admit_date": "2030-01-01",
        "requested_days": 10,
        "approved_days": 5,
        "status": "approved",
        "org_id": "org_a",
    }
    payload.update(overrides)
    return store.create_case(payload)


def _case_ids(response, key="cases"):
    assert response.status_code == 200
    return {case["case_id"] for case in response.json()[key]}


def test_flag_off_parity_admin_lists_all_fmla_and_ur(ctx):
    client = ctx["client"]
    ctx["holder"]["user"] = _user(org_id="org_a", role="admin")
    fmla_a = _fmla_case(ctx["fmla"], client_name="FMLA A")
    fmla_b = _fmla_case(
        ctx["fmla"],
        client_id="client-b",
        client_name="FMLA B",
        assigned_case_manager="cm_b1",
        org_id="org_b",
    )
    ur_a = _ur_case(ctx["ur"], client_name="UR A")
    ur_b = _ur_case(
        ctx["ur"],
        client_id="client-b",
        client_name="UR B",
        assigned_case_manager="cm_b1",
        org_id="org_b",
    )

    assert _case_ids(client.get("/api/fmla")) == {fmla_a["case_id"], fmla_b["case_id"]}
    assert _case_ids(client.get("/api/ur")) == {ur_a["case_id"], ur_b["case_id"]}


def test_flag_on_fmla_list_isolation(ctx_mt):
    client = ctx_mt["client"]
    ctx_mt["holder"]["user"] = _user(org_id="org_a", role="admin")
    own = _fmla_case(ctx_mt["fmla"], client_name="FMLA A")
    other = _fmla_case(
        ctx_mt["fmla"],
        client_id="client-b",
        client_name="FMLA B",
        assigned_case_manager="cm_b1",
        org_id="org_b",
    )

    ids = _case_ids(client.get("/api/fmla"))
    assert ids == {own["case_id"]}
    assert other["case_id"] not in ids


def test_flag_on_fmla_summary_isolation(ctx_mt):
    client = ctx_mt["client"]
    ctx_mt["holder"]["user"] = _user(org_id="org_a", role="admin")
    _fmla_case(ctx_mt["fmla"], status="approved", approval_status="approved")
    _fmla_case(
        ctx_mt["fmla"],
        client_id="client-b",
        client_name="FMLA B",
        assigned_case_manager="cm_b1",
        status="denied",
        approval_status="denied",
        org_id="org_b",
    )

    payload = client.get("/api/fmla/summary").json()
    assert payload["approved_cases"] == 1
    assert payload["denied_cases"] == 0
    assert len(payload["cases"]) == 1


def test_flag_on_ur_list_isolation(ctx_mt):
    client = ctx_mt["client"]
    ctx_mt["holder"]["user"] = _user(org_id="org_a", role="admin")
    own = _ur_case(ctx_mt["ur"], client_name="UR A")
    other = _ur_case(
        ctx_mt["ur"],
        client_id="client-b",
        client_name="UR B",
        assigned_case_manager="cm_b1",
        org_id="org_b",
    )

    ids = _case_ids(client.get("/api/ur"))
    assert ids == {own["case_id"]}
    assert other["case_id"] not in ids


def test_flag_on_ur_summary_isolation(ctx_mt):
    client = ctx_mt["client"]
    ctx_mt["holder"]["user"] = _user(org_id="org_a", role="admin")
    _ur_case(ctx_mt["ur"], requested_days=10, approved_days=5, revenue_at_risk_amount=100)
    _ur_case(
        ctx_mt["ur"],
        client_id="client-b",
        client_name="UR B",
        assigned_case_manager="cm_b1",
        requested_days=20,
        approved_days=0,
        revenue_at_risk_amount=999,
        org_id="org_b",
    )

    payload = client.get("/api/ur/summary").json()
    assert payload["total_cases"] == 1
    assert payload["total_authorized_days"] == 5
    assert payload["revenue_at_risk"] == 100


def test_staff_scoped_fmla_cross_org_by_id_404(ctx_mt):
    client = ctx_mt["client"]
    ctx_mt["holder"]["user"] = _user(org_id="org_a", role="admin")
    staff_case = _fmla_case(
        ctx_mt["fmla"],
        case_subject_type="staff",
        client_id="",
        client_name="Staff B",
        staff_identifier="staff-b",
        staff_name="Staff B",
        assigned_case_manager="cm_b1",
        org_id="org_b",
    )

    assert client.get(f"/api/fmla/{staff_case['case_id']}").status_code == 404


def test_staff_scoped_ur_cross_org_by_id_404(ctx_mt):
    client = ctx_mt["client"]
    ctx_mt["holder"]["user"] = _user(org_id="org_a", role="admin")
    staff_case = _ur_case(
        ctx_mt["ur"],
        client_id="",
        client_name="Staff UR B",
        assigned_case_manager="cm_b1",
        org_id="org_b",
    )

    assert client.get(f"/api/ur/{staff_case['case_id']}").status_code == 404


def test_case_manager_filter_cannot_cross_org(ctx_mt):
    client = ctx_mt["client"]
    ctx_mt["holder"]["user"] = _user(org_id="org_a", role="admin")
    _fmla_case(ctx_mt["fmla"], client_name="FMLA A", assigned_case_manager="cm_a1")
    _fmla_case(
        ctx_mt["fmla"],
        client_id="client-b",
        client_name="FMLA B",
        assigned_case_manager="cm_b1",
        org_id="org_b",
    )
    _ur_case(ctx_mt["ur"], client_name="UR A", assigned_case_manager="cm_a1")
    _ur_case(
        ctx_mt["ur"],
        client_id="client-b",
        client_name="UR B",
        assigned_case_manager="cm_b1",
        org_id="org_b",
    )

    assert _case_ids(client.get("/api/fmla", params={"case_manager": "cm_b1"})) == set()
    assert _case_ids(client.get("/api/ur", params={"case_manager": "cm_b1"})) == set()


def test_backfill_handles_client_staff_and_unresolved_rows(ctx):
    fmla = ctx["fmla"]
    ur = ctx["ur"]

    fmla_client = _fmla_case(fmla, client_id="client-a", assigned_case_manager="cm_b1", org_id="")
    fmla_staff = _fmla_case(
        fmla,
        case_subject_type="staff",
        client_id="",
        staff_identifier="staff-b",
        staff_name="Staff B",
        assigned_case_manager="cm_b1",
        org_id="",
    )
    fmla_unresolved = _fmla_case(fmla, client_id="", assigned_case_manager="missing", org_id="")
    ur_client = _ur_case(ur, client_id="client-a", assigned_case_manager="cm_b1", org_id="")
    ur_staff = _ur_case(ur, client_id="", assigned_case_manager="cm_b1", org_id="")
    ur_unresolved = _ur_case(ur, client_id="", assigned_case_manager="missing", org_id="")

    with sqlite3.connect(ctx["paths"]["fmla"]) as conn:
        conn.execute("UPDATE fmla_cases SET org_id = NULL WHERE case_id IN (?, ?, ?)", (fmla_client["case_id"], fmla_staff["case_id"], fmla_unresolved["case_id"]))
        conn.commit()
    with sqlite3.connect(ctx["paths"]["ur"]) as conn:
        conn.execute("UPDATE railway_ur_cases SET org_id = NULL WHERE case_id IN (?, ?, ?)", (ur_client["case_id"], ur_staff["case_id"], ur_unresolved["case_id"]))
        conn.commit()

    fmla_reloaded = FMLAStore(str(ctx["paths"]["fmla"]), str(ctx["paths"]["reminders"]))
    ur_reloaded = URStore(str(ctx["paths"]["ur"]))

    assert fmla_reloaded.get_case(fmla_client["case_id"])["org_id"] == "org_a"
    assert fmla_reloaded.get_case(fmla_staff["case_id"])["org_id"] == "org_b"
    assert fmla_reloaded.get_case(fmla_unresolved["case_id"])["org_id"] == DEFAULT_ORG_ID
    assert ur_reloaded.get_case(ur_client["case_id"])["org_id"] == "org_a"
    assert ur_reloaded.get_case(ur_staff["case_id"])["org_id"] == "org_b"
    assert ur_reloaded.get_case(ur_unresolved["case_id"])["org_id"] == DEFAULT_ORG_ID
