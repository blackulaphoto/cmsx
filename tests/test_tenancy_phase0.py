"""Phase 0 multi-tenancy foundation tests.

These verify that the tenancy scaffolding exists and that the app keeps its
current single-agency behavior while MULTI_TENANT_ENABLED is false.
"""
from types import SimpleNamespace
from unittest.mock import patch

from backend.auth.service import (
    ADMIN_ROLE,
    ORG_ADMIN_ROLE,
    ORG_MEMBER_ROLE,
    AuthenticatedUser,
    FirebaseAuthService,
)
from backend.shared.tenancy import (
    DEFAULT_ORG_ID,
    multi_tenant_enabled,
    resolve_org_id,
)


def _service(tmp_path):
    return FirebaseAuthService(tmp_path / "auth.db")


def _table_exists(service, name: str) -> bool:
    with service._connect() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (name,),
        ).fetchone()
    return row is not None


def _columns(service, table: str):
    with service._connect() as conn:
        return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


# ── Flag + resolver ─────────────────────────────────────────────────────────

def test_multi_tenant_disabled_by_default():
    with patch.dict("os.environ", {}, clear=True):
        assert multi_tenant_enabled() is False


def test_resolve_org_id_returns_default_when_flag_false():
    user = SimpleNamespace(org_id="org_other")
    with patch.dict("os.environ", {}, clear=True):
        # Even if the user carries another org, one-org mode wins.
        assert resolve_org_id(user) == DEFAULT_ORG_ID


def test_resolve_org_id_uses_user_org_when_flag_true():
    user = SimpleNamespace(org_id="org_other")
    with patch.dict("os.environ", {"MULTI_TENANT_ENABLED": "true"}, clear=True):
        assert resolve_org_id(user) == "org_other"


def test_resolve_org_id_falls_back_to_default_when_user_has_no_org():
    user = SimpleNamespace()
    with patch.dict("os.environ", {"MULTI_TENANT_ENABLED": "true"}, clear=True):
        assert resolve_org_id(user) == DEFAULT_ORG_ID


# ── Schema / seed / backfill ────────────────────────────────────────────────

def test_init_creates_organizations_table(tmp_path):
    service = _service(tmp_path)
    assert _table_exists(service, "organizations")


def test_init_creates_invites_table(tmp_path):
    service = _service(tmp_path)
    assert _table_exists(service, "invites")


def test_default_org_exists(tmp_path):
    service = _service(tmp_path)
    with service._connect() as conn:
        row = conn.execute(
            "SELECT org_id, name, status FROM organizations WHERE org_id = ?",
            (DEFAULT_ORG_ID,),
        ).fetchone()
    assert row is not None
    assert row["name"] == "Default Organization"
    assert row["status"] == "active"


def test_user_profiles_has_org_columns(tmp_path):
    service = _service(tmp_path)
    cols = _columns(service, "user_profiles")
    assert "org_id" in cols
    assert "org_role" in cols


def test_existing_users_are_backfilled_into_default_org(tmp_path):
    service = _service(tmp_path)
    # Simulate a legacy row created before org columns were populated.
    with service._connect() as conn:
        conn.execute(
            """
            INSERT INTO user_profiles (
                firebase_uid, email, full_name, role, case_manager_id, auth_provider,
                is_active, created_at, updated_at, org_id, org_role
            ) VALUES ('legacy-uid', 'legacy@example.com', 'Legacy', 'case_manager',
                      'cm_legacy', 'password', 1, '2026-01-01', '2026-01-01', NULL, 'member')
            """
        )
        conn.commit()

    # Re-run init (idempotent) — this performs the backfill.
    service._initialize_profile_store()

    with service._connect() as conn:
        row = conn.execute(
            "SELECT org_id FROM user_profiles WHERE firebase_uid = 'legacy-uid'"
        ).fetchone()
    assert row["org_id"] == DEFAULT_ORG_ID


def test_allowlist_admin_backfilled_as_org_admin(tmp_path):
    service = _service(tmp_path)
    with service._connect() as conn:
        conn.execute(
            """
            INSERT INTO user_profiles (
                firebase_uid, email, full_name, role, case_manager_id, auth_provider,
                is_active, created_at, updated_at, org_id, org_role
            ) VALUES ('admin-uid', 'blackulaphotography@gmail.com', 'Owner', 'admin',
                      'admin-uid', 'password', 1, '2026-01-01', '2026-01-01', NULL, 'member')
            """
        )
        conn.commit()

    service._initialize_profile_store()

    with service._connect() as conn:
        row = conn.execute(
            "SELECT org_role FROM user_profiles WHERE firebase_uid = 'admin-uid'"
        ).fetchone()
    assert row["org_role"] == ORG_ADMIN_ROLE


# ── Dataclass + test-auth ───────────────────────────────────────────────────

def test_authenticated_user_exposes_org_fields_with_safe_defaults():
    user = AuthenticatedUser(
        firebase_uid="u",
        email="a@b.com",
        full_name="A",
        role="case_manager",
        case_manager_id="cm_1",
        auth_provider="password",
        is_active=True,
    )
    assert user.org_id == DEFAULT_ORG_ID
    assert user.org_role == ORG_MEMBER_ROLE


def test_test_auth_user_gets_default_org_and_org_admin(tmp_path):
    service = _service(tmp_path)
    request = SimpleNamespace(headers={})
    user = service.test_user_from_request(request)
    assert user.org_id == DEFAULT_ORG_ID
    assert user.org_role == ORG_ADMIN_ROLE
    # Existing behavior preserved: unknown/empty role defaults to admin.
    assert user.role == ADMIN_ROLE
