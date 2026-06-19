"""Phase 3D1 tests: Legal org isolation.

The three legal list endpoints (/cases, /court-dates, /documents) derive their
org scoping entirely from two helpers plus assert_client_access:
  - _get_accessible_client_ids(user)  -> the client_id IN (...) row filter
  - _get_client_name_map(org_id)      -> the client-name labels
  - assert_client_access(user, client_id) -> by-id / client_id-supplied access
So these tests exercise that enforcement seam directly (deterministic and not
coupled to the legal DB schema). Flag OFF must reproduce prior behavior.
"""
import sqlite3

import pytest
from fastapi import HTTPException

import backend.modules.legal.routes as legal_routes
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
def core(tmp_path, monkeypatch):
    path = tmp_path / "core_clients.db"
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE clients (client_id TEXT PRIMARY KEY, first_name TEXT, last_name TEXT, case_manager_id TEXT, org_id TEXT)"
        )
        conn.executemany(
            "INSERT INTO clients VALUES (?,?,?,?,?)",
            [
                ("a1", "Ann", "A", "cm_a1", "org_a"),
                ("a2", "Al", "A", "cm_a2", "org_a"),
                ("b1", "Bob", "B", "cm_b1", "org_b"),
            ],
        )
        conn.commit()
    # Both the legal module (direct _DB_DIR reads) and authorization (helper +
    # assert_client_access) must point at the same tmp core_clients.db.
    monkeypatch.setattr(legal_routes, "_DB_DIR", tmp_path)
    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", path)
    return path


# ── Shared helper: get_client_ids_for_org ───────────────────────────────────

def test_get_client_ids_for_org(core):
    assert set(authz.get_client_ids_for_org("org_a")) == {"a1", "a2"}
    assert set(authz.get_client_ids_for_org("org_b")) == {"b1"}
    assert authz.get_client_ids_for_org("") == []
    assert authz.get_client_ids_for_org("org_unknown") == []


# ── _get_accessible_client_ids ──────────────────────────────────────────────

def test_accessible_flag_off_admin_is_none(core, monkeypatch):
    monkeypatch.delenv("MULTI_TENANT_ENABLED", raising=False)
    assert legal_routes._get_accessible_client_ids(_user(role="admin")) is None


def test_accessible_flag_on_admin_org_scoped(core, monkeypatch):
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    ids = set(legal_routes._get_accessible_client_ids(_user(org_id="org_a", role="admin")))
    assert ids == {"a1", "a2"}
    assert "b1" not in ids


def test_accessible_flag_on_nonadmin_own_org_only(core, monkeypatch):
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    ids = set(legal_routes._get_accessible_client_ids(
        _user(org_id="org_a", case_manager_id="cm_a1", role="case_manager")
    ))
    assert ids == {"a1"}  # cm_a1's own client in org_a; not a2 (cm_a2), not b1


def test_accessible_flag_off_nonadmin_unchanged(core, monkeypatch):
    monkeypatch.delenv("MULTI_TENANT_ENABLED", raising=False)
    ids = set(legal_routes._get_accessible_client_ids(
        _user(case_manager_id="cm_a1", role="case_manager")
    ))
    assert ids == {"a1"}


# ── _get_client_name_map ────────────────────────────────────────────────────

def test_name_map_flag_on_same_org_only(core):
    names = legal_routes._get_client_name_map("org_a")
    assert set(names.keys()) == {"a1", "a2"}
    assert "b1" not in names


def test_name_map_flag_off_all(core):
    names = legal_routes._get_client_name_map(None)
    assert {"a1", "a2", "b1"} <= set(names.keys())


# ── assert_client_access: cross-org by-id -> 404 ────────────────────────────

def test_assert_client_access_cross_org_404(core, monkeypatch):
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    with pytest.raises(HTTPException) as exc:
        authz.assert_client_access(_user(org_id="org_a", role="admin"), "b1")
    assert exc.value.status_code == 404


def test_assert_client_access_same_org_ok(core, monkeypatch):
    monkeypatch.setenv("MULTI_TENANT_ENABLED", "true")
    # org_a admin reaching an org_a client succeeds (returns the case_manager_id).
    assert authz.assert_client_access(_user(org_id="org_a", role="admin"), "a1") == "cm_a1"
