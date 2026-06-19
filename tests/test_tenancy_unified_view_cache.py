"""Unified view cache tenancy hardening tests.

Focus:
- Memory cache key is org-scoped when MT enabled (prevents cross-org hits)
- Cache writes stamp org_id on the DB row
- DB schema migration adds org_id idempotently and backfills DEFAULT_ORG_ID
- Route-level assert_client_access blocks cross-org reads (returns 404)
- Flag-off parity: cache key does NOT include org, all clients share one entry
"""
import sqlite3
import time

import pytest
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


def _make_core_db(path, rows):
    """Minimal core_clients.db with org_id and case_manager_id."""
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
        conn.executemany(
            "INSERT INTO clients VALUES (?,?,?,?,?,?)",
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
    _make_core_db(core_db, [
        ("client-a1", "Alice", "Alpha", "cm_a1", "org_a", "2026-01-01T00:00:00"),
        ("client-b1", "Bob",   "Baker", "cm_b1", "org_b", "2026-01-02T00:00:00"),
    ])

    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", core_db)
    monkeypatch.setattr(authz, "AUTH_DB", auth_db)

    yield {"core_db": core_db, "auth_db": auth_db, "tmp_path": tmp_path}


# ── Engine unit tests ──────────────────────────────────────────────────────────

def _make_engine(tmp_path, monkeypatch):
    """Return a UnifiedClientViewEngine with its db_dir pointed at tmp_path."""
    from backend.shared import phase_4a_unified_client_view as mod

    monkeypatch.setattr(mod, "DB_DIR", tmp_path)

    engine = mod.UnifiedClientViewEngine.__new__(mod.UnifiedClientViewEngine)
    engine.db_dir = tmp_path
    engine.cache_storage = {}
    engine.cache_timestamps = {}
    engine.cache_ttl = 300
    engine.lock = __import__("threading").Lock()
    engine.modules = {}

    # Create the DB table so migration tests have something to work with
    db = tmp_path / "unified_client_view.db"
    with sqlite3.connect(db) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS unified_view_cache (
                client_id TEXT PRIMARY KEY,
                cached_data TEXT NOT NULL,
                cache_timestamp TEXT NOT NULL,
                expiry_timestamp TEXT NOT NULL,
                data_hash TEXT NOT NULL,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                org_id TEXT
            )
        """)

    return engine


# ── Test 1: flag-off cache key has no org prefix ───────────────────────────────

def test_flag_off_cache_key_is_unscoped(ctx, monkeypatch):
    """Flag off → cache key is plain unified_view_{client_id}."""
    monkeypatch.delenv("MULTI_TENANT_ENABLED", raising=False)
    engine = _make_engine(ctx["tmp_path"], monkeypatch)
    key = engine._generate_cache_key("client-a1", org_id="org_a")
    assert key == "unified_view_client-a1"


# ── Test 2: flag-on cache key includes org prefix ─────────────────────────────

def test_flag_on_cache_key_is_org_scoped(ctx, monkeypatch):
    """Flag on → cache key is unified_view_{org_id}_{client_id}."""
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    engine = _make_engine(ctx["tmp_path"], monkeypatch)
    key = engine._generate_cache_key("client-a1", org_id="org_a")
    assert key == "unified_view_org_a_client-a1"


# ── Test 3: flag-on different orgs get different cache keys ───────────────────

def test_flag_on_different_orgs_get_different_keys(ctx, monkeypatch):
    """org_a and org_b must not share a memory cache slot for the same client_id."""
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    engine = _make_engine(ctx["tmp_path"], monkeypatch)
    key_a = engine._generate_cache_key("client-x", org_id="org_a")
    key_b = engine._generate_cache_key("client-x", org_id="org_b")
    assert key_a != key_b


# ── Test 4: cache write stamps org_id on DB row ───────────────────────────────

def test_cache_write_stamps_org_id(ctx, monkeypatch):
    """_cache_view stamps org_id on the unified_view_cache DB row."""
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    from backend.shared.phase_4a_unified_client_view import UnifiedClientView, NavigationContext
    engine = _make_engine(ctx["tmp_path"], monkeypatch)

    nav = NavigationContext(
        client_id="client-a1",
        current_module="core_clients",
        previous_module=None,
        breadcrumbs=[],
        session_id="sess-1",
        timestamp="2026-01-01T00:00:00",
    )
    view = UnifiedClientView(
        client_id="client-a1",
        core_profile={},
        modules={},
        navigation_context=nav,
        cache_info={},
        data_freshness_summary={},
        last_aggregated="2026-01-01T00:00:00",
        total_records=0,
    )

    engine._cache_view("client-a1", view, org_id="org_a")

    db = ctx["tmp_path"] / "unified_client_view.db"
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "SELECT org_id FROM unified_view_cache WHERE client_id = 'client-a1'"
        ).fetchone()
    assert row is not None
    assert row[0] == "org_a"


# ── Test 5: DB schema migration adds org_id and backfills DEFAULT_ORG_ID ──────

def test_migration_adds_org_id_and_backfills(ctx, monkeypatch):
    """init_unified_view_database adds org_id column and backfills existing rows."""
    engine = _make_engine(ctx["tmp_path"], monkeypatch)

    # Insert a row without org_id (simulating a pre-migration row)
    db = ctx["tmp_path"] / "unified_client_view.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO unified_view_cache "
            "(client_id, cached_data, cache_timestamp, expiry_timestamp, data_hash) "
            "VALUES ('c-old', '{}', '2026-01-01', '2027-01-01', 'abc')"
        )

    # Run the migration
    engine.init_unified_view_database()

    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "SELECT org_id FROM unified_view_cache WHERE client_id = 'c-old'"
        ).fetchone()
    assert row is not None
    assert row[0] == DEFAULT_ORG_ID


# ── Test 6: migration is idempotent ───────────────────────────────────────────

def test_migration_is_idempotent(ctx, monkeypatch):
    """Calling init_unified_view_database twice does not raise."""
    engine = _make_engine(ctx["tmp_path"], monkeypatch)
    engine.init_unified_view_database()
    engine.init_unified_view_database()  # should not raise


# ── Test 7: cross-org access blocked by assert_client_access ──────────────────

def test_cross_org_assert_client_access_raises(ctx, monkeypatch):
    """assert_client_access raises 404 when org_a user requests org_b client."""
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")

    from backend.auth.authorization import assert_client_access
    from fastapi import HTTPException

    user_a = _user(org_id="org_a", case_manager_id="cm_a1")

    with pytest.raises(HTTPException) as exc_info:
        assert_client_access(user_a, "client-b1")
    assert exc_info.value.status_code == 404


# ── Test 8: flag-off cross-org access is NOT blocked ──────────────────────────

def test_flag_off_cross_org_access_allowed(ctx, monkeypatch):
    """When flag is off, assert_client_access does not raise for cross-org client."""
    monkeypatch.delenv("MULTI_TENANT_ENABLED", raising=False)

    from backend.auth.authorization import assert_client_access

    user_a = _user(org_id="org_a", case_manager_id="cm_a1")
    # Should not raise when MT is disabled
    assert_client_access(user_a, "client-b1")


# ── Test 9: flag-on memory cache isolates orgs ────────────────────────────────

def test_flag_on_memory_cache_org_isolation(ctx, monkeypatch):
    """org_b user cannot hit a cache entry written by org_a for the same client_id."""
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    from backend.shared.phase_4a_unified_client_view import UnifiedClientView, NavigationContext

    engine = _make_engine(ctx["tmp_path"], monkeypatch)

    nav = NavigationContext(
        client_id="client-x",
        current_module="core_clients",
        previous_module=None,
        breadcrumbs=[],
        session_id="sess-1",
        timestamp="2026-01-01T00:00:00",
    )
    view = UnifiedClientView(
        client_id="client-x",
        core_profile={},
        modules={},
        navigation_context=nav,
        cache_info={},
        data_freshness_summary={},
        last_aggregated="2026-01-01T00:00:00",
        total_records=0,
    )

    # org_a writes to cache
    engine._cache_view("client-x", view, org_id="org_a")

    # org_b should NOT get a cache hit for the same client_id
    result = engine._get_cached_view("client-x", org_id="org_b")
    assert result is None

    # org_a SHOULD get a cache hit
    result_a = engine._get_cached_view("client-x", org_id="org_a")
    assert result_a is not None
