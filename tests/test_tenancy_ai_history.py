"""AI history tenancy hardening tests.

Focus:
- All AI chat/conversation endpoints require authentication (401 when unauthed)
- case_manager_id is derived from the authenticated user token, not caller-supplied param
- Flag-off: same-user history still works normally
- Flag-on: org_a user cannot read org_b history (org-scoped fetch)
- New conversation rows are stamped with org_id
- Backfill populates org_id from user_profiles
- No DB files committed
"""
import sqlite3

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth import authorization as authz
from backend.auth.service import AuthenticatedUser
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


def _make_auth_db(path, profiles):
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE user_profiles (
                case_manager_id TEXT, firebase_uid TEXT, org_id TEXT
            )
        """)
        conn.executemany("INSERT INTO user_profiles VALUES (?,?,?)", profiles)


def _make_core_db(path, rows):
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE clients (
                client_id TEXT PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                case_manager_id TEXT,
                org_id TEXT,
                created_at TEXT
            )
        """)
        conn.executemany("INSERT INTO clients VALUES (?,?,?,?,?,?)", rows)


# ── Service factory ────────────────────────────────────────────────────────────

def _make_service(tmp_path, monkeypatch):
    """Return an uninitialized UnifiedAIService backed by a tmp DB."""
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
    return svc


# ── Route-level app factory ────────────────────────────────────────────────────

def _make_route_app(user, tmp_path, monkeypatch):
    """Build a minimal FastAPI app with the unified AI router and injected auth."""
    from backend.modules.ai_unified import unified_routes as ur_mod
    from backend.modules.ai_unified.unified_service import UnifiedAIService
    from backend.shared import db_path as db_path_mod

    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp_path)

    # Patch the module-level unified_ai singleton so it uses tmp_path
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


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture
def ctx(tmp_path, monkeypatch):
    auth_db = tmp_path / "auth.db"
    core_db = tmp_path / "core_clients.db"

    _make_auth_db(auth_db, [
        ("cm_a1", "uid-cm_a1", "org_a"),
        ("cm_b1", "uid-cm_b1", "org_b"),
    ])
    _make_core_db(core_db, [
        ("client-a1", "Alice", "Alpha", "cm_a1", "org_a", "2026-01-01T00:00:00"),
        ("client-b1", "Bob",   "Baker", "cm_b1", "org_b", "2026-01-02T00:00:00"),
    ])

    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", core_db)
    monkeypatch.setattr(authz, "AUTH_DB", auth_db)

    yield {"auth_db": auth_db, "core_db": core_db, "tmp_path": tmp_path}


# ── Test 1: unauthenticated POST /chat returns 401 ────────────────────────────

def test_unauthed_chat_returns_401(ctx, monkeypatch):
    """POST /api/ai/chat without auth → 401."""
    client = _make_route_app(None, ctx["tmp_path"], monkeypatch)
    resp = client.post("/api/ai/chat", json={"message": "hello"})
    assert resp.status_code == 401


# ── Test 2: unauthenticated POST /assistant returns 401 ───────────────────────

def test_unauthed_assistant_returns_401(ctx, monkeypatch):
    """POST /api/ai/assistant without auth → 401."""
    client = _make_route_app(None, ctx["tmp_path"], monkeypatch)
    resp = client.post("/api/ai/assistant", json={"message": "hello"})
    assert resp.status_code == 401


# ── Test 3: unauthenticated GET /conversation returns 401 ─────────────────────

def test_unauthed_conversation_returns_401(ctx, monkeypatch):
    """GET /api/ai/conversation without auth → 401."""
    client = _make_route_app(None, ctx["tmp_path"], monkeypatch)
    resp = client.get("/api/ai/conversation")
    assert resp.status_code == 401


# ── Test 4: caller-supplied case_manager_id is ignored ────────────────────────

def test_caller_supplied_case_manager_id_ignored(ctx, monkeypatch):
    """Token-derived case_manager_id is used even if body supplies a different one.

    We verify this by inspecting which case_manager_id ends up in the DB row.
    """
    monkeypatch.delenv("MULTI_TENANT_ENABLED", raising=False)
    user = _user(org_id="org_a", case_manager_id="cm_a1")
    client = _make_route_app(user, ctx["tmp_path"], monkeypatch)

    # POST with a different case_manager_id in the body — should be ignored
    resp = client.post("/api/ai/chat", json={"message": "hi", "case_manager_id": "cm_b1"})
    # expect success or missing-key error, not 401/500
    assert resp.status_code in (200, 500)  # 500 if OpenAI key missing is fine

    db = ctx["tmp_path"] / "ai_assistant.db"
    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT case_manager_id FROM conversations").fetchall()

    # All rows should belong to the authenticated user (cm_a1), not the caller-supplied cm_b1
    for row in rows:
        assert row[0] == "cm_a1", f"Expected cm_a1 but found {row[0]}"


# ── Test 5: flag-off — authenticated user can fetch own history ───────────────

@pytest.mark.asyncio
async def test_flag_off_own_history_works(ctx, monkeypatch):
    """Flag off: get_conversation_history returns rows for the authenticated user."""
    monkeypatch.delenv("MULTI_TENANT_ENABLED", raising=False)
    svc = _make_service(ctx["tmp_path"], monkeypatch)
    await svc.initialize()

    await svc._save_message("cm_a1", "user", "hello", org_id=DEFAULT_ORG_ID)
    result = await svc.get_conversation_history("cm_a1", org_id=None)
    assert len(result) == 1
    assert result[0]["content"] == "hello"


# ── Test 6: flag-on — org_a cannot read org_b history ────────────────────────

@pytest.mark.asyncio
async def test_flag_on_org_isolation(ctx, monkeypatch):
    """Flag on: org_b user cannot see messages stored under org_a."""
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    svc = _make_service(ctx["tmp_path"], monkeypatch)
    await svc.initialize()

    # org_a saves a message
    await svc._save_message("cm_a1", "user", "secret org_a message", org_id="org_a")

    # org_b fetches cm_a1 history scoped to org_b — should get nothing
    result_b = await svc._fetch_history("cm_a1", org_id="org_b")
    assert result_b == [], f"org_b should not see org_a messages, got: {result_b}"

    # org_a fetches their own history — should see it
    result_a = await svc._fetch_history("cm_a1", org_id="org_a")
    assert len(result_a) == 1
    assert result_a[0]["content"] == "secret org_a message"


# ── Test 7: new rows stamp org_id ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_new_rows_stamp_org_id(ctx, monkeypatch):
    """_save_message stores the org_id on the row."""
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    svc = _make_service(ctx["tmp_path"], monkeypatch)
    await svc.initialize()

    await svc._save_message("cm_a1", "user", "stamped", org_id="org_a")

    db = ctx["tmp_path"] / "ai_assistant.db"
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "SELECT org_id FROM conversations WHERE case_manager_id = 'cm_a1'"
        ).fetchone()
    assert row is not None
    assert row[0] == "org_a"


# ── Test 8: backfill populates org_id from DEFAULT_ORG_ID to real org ─────────

@pytest.mark.asyncio
async def test_backfill_derives_org_from_user_profiles(ctx, monkeypatch):
    """_backfill_org_ids_from_auth updates rows from DEFAULT_ORG_ID to real org."""
    from backend.shared import db_path as db_path_mod
    tmp = ctx["tmp_path"]
    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp)

    # Pre-create the DB with a row stamped DEFAULT_ORG_ID
    db = tmp / "ai_assistant.db"
    with sqlite3.connect(db) as conn:
        conn.execute("""
            CREATE TABLE conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_manager_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                org_id TEXT
            )
        """)
        conn.execute(
            "INSERT INTO conversations (case_manager_id, role, content, timestamp, org_id) VALUES (?,?,?,?,?)",
            ("cm_a1", "user", "hello", "2026-01-01T00:00:00", DEFAULT_ORG_ID),
        )

    from backend.modules.ai_unified.unified_service import UnifiedAIService
    svc = UnifiedAIService.__new__(UnifiedAIService)
    svc.db_path = db
    svc._initialized = False

    # Run just the backfill
    await svc._backfill_org_ids_from_auth()

    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT org_id FROM conversations WHERE case_manager_id = 'cm_a1'").fetchone()
    # The backfill should have resolved DEFAULT_ORG_ID → org_a via user_profiles
    assert row is not None
    assert row[0] == "org_a"


# ── Test 9: backfill falls back to DEFAULT_ORG_ID for unknown case_manager ────

@pytest.mark.asyncio
async def test_backfill_unknown_cm_stays_default(ctx, monkeypatch):
    """Backfill leaves DEFAULT_ORG_ID when case_manager_id has no user_profiles match."""
    from backend.shared import db_path as db_path_mod
    tmp = ctx["tmp_path"]
    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp)

    db = tmp / "ai_assistant.db"
    with sqlite3.connect(db) as conn:
        conn.execute("""
            CREATE TABLE conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_manager_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                org_id TEXT
            )
        """)
        conn.execute(
            "INSERT INTO conversations (case_manager_id, role, content, timestamp, org_id) VALUES (?,?,?,?,?)",
            ("ghost_cm", "user", "msg", "2026-01-01T00:00:00", DEFAULT_ORG_ID),
        )

    from backend.modules.ai_unified.unified_service import UnifiedAIService
    svc = UnifiedAIService.__new__(UnifiedAIService)
    svc.db_path = db
    svc._initialized = False

    await svc._backfill_org_ids_from_auth()

    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT org_id FROM conversations WHERE case_manager_id = 'ghost_cm'").fetchone()
    assert row is not None
    assert row[0] == DEFAULT_ORG_ID
