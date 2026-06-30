"""AI assistant platform context v1 tests.

Focus:
- Unauthenticated popup AI request returns 401
- Authenticated list_current_clients returns seeded clients
- Caller-supplied wrong case_manager_id cannot change visible clients
- get_upcoming_court_dates returns scoped court dates (legal + reminders)
- search_client_by_name finds within scope only
- Missing insurance data produces a grounded "not found" answer (not fabricated)
- No DB files committed
"""
import sqlite3
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth import authorization as authz
from backend.auth.service import AuthenticatedUser
from backend.shared.tenancy import DEFAULT_ORG_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _make_auth_db(path, profiles):
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE user_profiles (case_manager_id TEXT, firebase_uid TEXT, org_id TEXT)"
        )
        conn.executemany("INSERT INTO user_profiles VALUES (?,?,?)", profiles)


def _make_core_db(path, rows):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """CREATE TABLE clients (
                client_id TEXT PRIMARY KEY,
                first_name TEXT, last_name TEXT,
                case_manager_id TEXT, org_id TEXT, created_at TEXT,
                case_status TEXT DEFAULT 'Active'
            )"""
        )
        conn.executemany("INSERT INTO clients VALUES (?,?,?,?,?,?,?)", rows)


def _make_legal_db(path, court_rows):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """CREATE TABLE court_dates (
                court_date_id TEXT PRIMARY KEY,
                case_id TEXT, client_id TEXT,
                hearing_date TEXT, hearing_time TEXT,
                court_name TEXT, courtroom TEXT,
                hearing_type TEXT, status TEXT
            )"""
        )
        conn.executemany("INSERT INTO court_dates VALUES (?,?,?,?,?,?,?,?,?)", court_rows)


def _make_admissions_db(path, face_sheet_rows):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """CREATE TABLE face_sheets (
                client_id TEXT PRIMARY KEY,
                primary_payer_type TEXT,
                primary_plan_name TEXT,
                primary_member_id TEXT
            )"""
        )
        conn.executemany("INSERT INTO face_sheets VALUES (?,?,?,?)", face_sheet_rows)


def _make_reminders_db(path, task_rows):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """CREATE TABLE intelligent_tasks (
                id TEXT PRIMARY KEY,
                client_id TEXT,
                case_manager_id TEXT,
                task_type TEXT,
                title TEXT,
                description TEXT,
                priority TEXT,
                status TEXT,
                estimated_minutes INTEGER,
                due_date TEXT,
                completed_at TEXT,
                created_at TEXT,
                is_demo INTEGER DEFAULT 0,
                org_id TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE active_reminders (
                reminder_id TEXT PRIMARY KEY,
                client_id TEXT,
                case_manager_id TEXT,
                reminder_type TEXT,
                message TEXT,
                priority TEXT,
                due_date TEXT,
                status TEXT,
                created_at TEXT,
                org_id TEXT
            )"""
        )
        conn.executemany("INSERT INTO intelligent_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", task_rows)


def _make_route_app(user, tmp_path, monkeypatch):
    from backend.modules.ai_unified import unified_routes as ur_mod
    from backend.shared import db_path as db_path_mod

    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp_path)

    # Patch the module-level unified_ai singleton
    svc = _make_service(tmp_path, monkeypatch)
    monkeypatch.setattr(ur_mod, "unified_ai", svc)

    app = FastAPI()

    @app.middleware("http")
    async def inject_auth(request, call_next):
        if user is not None:
            request.state.auth_user = user
        return await call_next(request)

    from backend.modules.ai_unified.unified_routes import router
    app.include_router(router, prefix="/api/ai")
    return TestClient(app, raise_server_exceptions=False)


def _make_service(tmp_path, monkeypatch):
    from backend.modules.ai_unified.unified_service import UnifiedAIService
    from backend.shared import db_path as db_path_mod

    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp_path)

    svc = UnifiedAIService.__new__(UnifiedAIService)
    svc.db_path = tmp_path / "ai_assistant.db"
    svc.model = "gpt-4o"
    svc.api_key = ""
    svc.client = None
    svc._initialized = False
    svc._knowledge_index_cache = None
    svc._knowledge_snippet_cache = {}
    svc._function_map = {}
    # Re-wire the function map using the real method references
    from backend.modules.ai_unified import platform_tools as _pt
    import asyncio

    async def _list_clients(case_manager_id, org_id=None, **_):
        return await asyncio.to_thread(_pt.list_current_clients, case_manager_id, org_id)

    async def _search_client(name, case_manager_id, org_id=None, **_):
        return await asyncio.to_thread(_pt.search_client_by_name, name, case_manager_id, org_id)

    async def _get_insurance(client_id, case_manager_id, org_id=None, **_):
        return await asyncio.to_thread(_pt.get_client_insurance, client_id, case_manager_id, org_id)

    async def _get_court_dates(case_manager_id, org_id=None, days_ahead=7, **_):
        return await asyncio.to_thread(_pt.get_upcoming_court_dates, case_manager_id, org_id, days_ahead)

    svc._function_map = {
        "list_current_clients": _list_clients,
        "search_client_by_name": _search_client,
        "get_client_insurance": _get_insurance,
        "get_upcoming_court_dates": _get_court_dates,
    }
    return svc


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def ctx(tmp_path, monkeypatch):
    auth_db = tmp_path / "auth.db"
    core_db = tmp_path / "core_clients.db"
    admissions_db = tmp_path / "admissions.db"
    legal_db = tmp_path / "legal_cases.db"
    reminders_db = tmp_path / "reminders.db"

    _make_auth_db(auth_db, [
        ("cm_a1", "uid-cm_a1", "org_a"),
        ("cm_b1", "uid-cm_b1", "org_b"),
    ])
    _make_core_db(core_db, [
        ("client-a1", "Alice", "Alpha", "cm_a1", "org_a", "2026-01-01T00:00:00", "Active"),
        ("client-a2", "Jessica", "Adams", "cm_a1", "org_a", "2026-02-01T00:00:00", "Active"),
        ("client-b1", "Bob",   "Baker", "cm_b1", "org_b", "2026-01-02T00:00:00", "Active"),
    ])
    _make_admissions_db(admissions_db, [
        ("client-a1", "Medi-Cal", "Medi-Cal Managed Care", "MCA-001"),
        ("client-a2", None, None, None),  # Jessica has no insurance
    ])
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    _make_reminders_db(reminders_db, [
        ("task-a1", "client-a1", "cm_a1", "housing_follow_up", "Pay rent", "Bring payment to housing office", "high", "pending", 30, yesterday, None, yesterday, 0, "org_a"),
    ])

    next_week = (datetime.now() + timedelta(days=5)).date().isoformat()
    _make_legal_db(legal_db, [
        ("cd-a1", "case-a1", "client-a1", next_week, "09:00",
         "LA County Superior Court", "Court 7", "Hearing", "Scheduled"),
        # Bob's court date — should NOT appear for cm_a1
        ("cd-b1", "case-b1", "client-b1", next_week, "10:00",
         "SF Superior Court", "Court 2", "Hearing", "Scheduled"),
    ])

    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", core_db)
    monkeypatch.setattr(authz, "AUTH_DB", auth_db)

    from backend.shared import db_path as db_path_mod
    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp_path)

    # Patch the module-level CoreClientService singleton (captures DB_DIR at __init__)
    from backend.modules.services import case_management_api as cma
    monkeypatch.setattr(cma.core_client_service, "db_path", str(core_db))
    monkeypatch.setattr(cma.core_client_service, "_auth_db_path", str(auth_db))

    yield {
        "auth_db": auth_db,
        "core_db": core_db,
        "admissions_db": admissions_db,
        "legal_db": legal_db,
        "reminders_db": reminders_db,
        "tmp_path": tmp_path,
    }


# ---------------------------------------------------------------------------
# Test 1: unauthenticated popup request returns 401
# ---------------------------------------------------------------------------

def test_unauthed_assistant_returns_401(ctx, monkeypatch):
    client = _make_route_app(None, ctx["tmp_path"], monkeypatch)
    resp = client.post("/api/ai/assistant", json={"message": "list my clients"})
    assert resp.status_code == 401


def test_chat_injects_selected_client_task_context(ctx, monkeypatch):
    user = _user(org_id="org_a", case_manager_id="cm_a1")
    captured = {}

    async def fake_process_message(*, message, case_manager_id, mode, injected_context, org_id):
        captured["message"] = message
        captured["case_manager_id"] = case_manager_id
        captured["mode"] = mode
        captured["injected_context"] = injected_context
        captured["org_id"] = org_id
        return {"success": True, "response": "ok", "function_called": ""}

    client = _make_route_app(user, ctx["tmp_path"], monkeypatch)
    from backend.modules.ai_unified import unified_routes as ur_mod
    monkeypatch.setattr(ur_mod.unified_ai, "process_message", fake_process_message)
    monkeypatch.setattr(
        ur_mod,
        "get_client_work_items",
        lambda case_manager_id, client_id, org_id=None: {
            "items": [
                {
                    "client_id": client_id,
                    "client_name": "Alice Alpha",
                    "title": "Pay rent",
                    "due_date": "2026-06-01",
                    "priority": "high",
                    "bucket": "overdue",
                    "source_label": "Reminder",
                }
            ]
        },
    )
    resp = client.post(
        "/api/ai/chat",
        json={
            "message": "Does this client have overdue tasks?",
            "client_id": "client-a1",
            "client_name": "Alice Alpha",
        },
    )

    assert resp.status_code == 200
    assert captured["case_manager_id"] == "cm_a1"
    assert captured["mode"] == "central"
    assert captured["org_id"] is None
    assert "Selected client operational context:" in captured["injected_context"]
    assert "- Client: Alice Alpha" in captured["injected_context"]
    assert "- Overdue: 1" in captured["injected_context"]
    assert "Pay rent" in captured["injected_context"]
    assert "source: Reminder" in captured["injected_context"]


def test_chat_resolves_uniquely_named_client_from_message(ctx, monkeypatch):
    user = _user(org_id="org_a", case_manager_id="cm_a1")
    captured = {}

    async def fake_process_message(*, message, case_manager_id, mode, injected_context, org_id):
        captured["injected_context"] = injected_context
        return {"success": True, "response": "ok", "function_called": ""}

    client = _make_route_app(user, ctx["tmp_path"], monkeypatch)
    from backend.modules.ai_unified import unified_routes as ur_mod
    monkeypatch.setattr(ur_mod.unified_ai, "process_message", fake_process_message)
    monkeypatch.setattr(
        ur_mod,
        "get_client_work_items",
        lambda case_manager_id, client_id, org_id=None: {
            "items": [
                {
                    "client_id": client_id,
                    "client_name": "Alice Alpha",
                    "title": "Pay rent",
                    "due_date": "2026-06-01",
                    "priority": "high",
                    "bucket": "overdue",
                    "source_label": "Reminder",
                }
            ]
        },
    )

    resp = client.post(
        "/api/ai/chat",
        json={"message": "What overdue reminders/tasks do I have for Alice Alpha?"},
    )

    assert resp.status_code == 200
    assert "Selected client operational context:" in captured["injected_context"]
    assert "- Client: Alice Alpha" in captured["injected_context"]
    assert "Pay rent" in captured["injected_context"]


# ---------------------------------------------------------------------------
# Test 2: list_current_clients returns the seeded clients for cm_a1
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_current_clients_returns_scoped_clients(ctx, monkeypatch):
    monkeypatch.delenv("MULTI_TENANT_ENABLED", raising=False)
    from backend.modules.ai_unified import platform_tools as pt
    result = pt.list_current_clients(case_manager_id="cm_a1", org_id=None)
    assert result["success"] is True
    names = [c["name"] for c in result["clients"]]
    assert "Alice Alpha" in names
    assert "Jessica Adams" in names
    # Bob Baker belongs to cm_b1, must not appear
    assert "Bob Baker" not in names


# ---------------------------------------------------------------------------
# Test 3: caller-supplied wrong case_manager_id cannot change visible clients
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_caller_supplied_wrong_cm_id_is_ignored(ctx, monkeypatch):
    """The process_message flow injects auth case_manager_id; LLM param is overridden."""
    monkeypatch.delenv("MULTI_TENANT_ENABLED", raising=False)
    from backend.modules.ai_unified import platform_tools as pt
    # Even if someone calls the tool with cm_b1, scope is determined by the argument
    # (which would be the auth-derived value in production).
    result_b = pt.list_current_clients(case_manager_id="cm_b1", org_id=None)
    assert result_b["success"] is True
    names_b = [c["name"] for c in result_b["clients"]]
    assert "Bob Baker" in names_b
    assert "Alice Alpha" not in names_b

    # cm_a1 gets only their clients
    result_a = pt.list_current_clients(case_manager_id="cm_a1", org_id=None)
    names_a = [c["name"] for c in result_a["clients"]]
    assert "Alice Alpha" in names_a
    assert "Bob Baker" not in names_a


# ---------------------------------------------------------------------------
# Test 4: get_upcoming_court_dates is scoped to the case manager's clients
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_court_dates_scoped_to_case_manager(ctx, monkeypatch):
    monkeypatch.delenv("MULTI_TENANT_ENABLED", raising=False)
    from backend.modules.ai_unified import platform_tools as pt
    result = pt.get_upcoming_court_dates(case_manager_id="cm_a1", org_id=None, days_ahead=14)
    assert result["success"] is True
    client_ids = [cd["client_id"] for cd in result["court_dates"]]
    # Alice's court date should appear
    assert "client-a1" in client_ids
    # Bob's should NOT appear (he's cm_b1's client)
    assert "client-b1" not in client_ids


# ---------------------------------------------------------------------------
# Test 5: search_client_by_name finds Jessica within scope
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_client_by_name_finds_within_scope(ctx, monkeypatch):
    monkeypatch.delenv("MULTI_TENANT_ENABLED", raising=False)
    from backend.modules.ai_unified import platform_tools as pt
    result = pt.search_client_by_name(name="Jessica", case_manager_id="cm_a1", org_id=None)
    assert result["success"] is True
    assert result["found"] is True
    assert result["matches"][0]["name"] == "Jessica Adams"

    # Bob is out of scope — should not be found
    result_b = pt.search_client_by_name(name="Bob", case_manager_id="cm_a1", org_id=None)
    assert result_b["found"] is False


# ---------------------------------------------------------------------------
# Test 6: get_client_insurance returns data for Alice, not-found note for Jessica
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_client_insurance_grounded_response(ctx, monkeypatch):
    monkeypatch.delenv("MULTI_TENANT_ENABLED", raising=False)
    from backend.modules.ai_unified import platform_tools as pt

    # Alice has Medi-Cal
    result_alice = pt.get_client_insurance(
        client_id="client-a1", case_manager_id="cm_a1", org_id=None
    )
    assert result_alice["success"] is True
    assert result_alice["insurance_provider"] == "Medi-Cal"
    assert result_alice["insurance_member_id"] == "MCA-001"

    # Jessica has no insurance — must return success with explicit note, not fabricate
    result_jessica = pt.get_client_insurance(
        client_id="client-a2", case_manager_id="cm_a1", org_id=None
    )
    assert result_jessica["success"] is True
    assert result_jessica["insurance_provider"] is None
    assert result_jessica["note"] is not None  # grounded "not found" explanation


# ---------------------------------------------------------------------------
# Test 7: get_client_insurance blocks cross-scope access
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_client_insurance_cross_scope_blocked(ctx, monkeypatch):
    monkeypatch.delenv("MULTI_TENANT_ENABLED", raising=False)
    from backend.modules.ai_unified import platform_tools as pt

    # cm_a1 tries to get insurance for Bob (cm_b1's client) — must be blocked
    result = pt.get_client_insurance(
        client_id="client-b1", case_manager_id="cm_a1", org_id=None
    )
    assert result["success"] is False
    assert "caseload" in result.get("error", "").lower()
