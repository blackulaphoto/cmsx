from types import SimpleNamespace
from unittest.mock import patch

from backend.auth.service import ADMIN_ROLE, CASE_MANAGER_ROLE, FirebaseAuthService


def _service(tmp_path):
    return FirebaseAuthService(tmp_path / "auth.db")


def test_test_auth_requires_explicit_enable_and_test_environment(tmp_path):
    service = _service(tmp_path)

    with patch.dict("os.environ", {}, clear=True):
        assert service.is_test_auth_enabled() is False

    with patch.dict("os.environ", {"ENABLE_TEST_AUTH": "true"}, clear=True):
        assert service.is_test_auth_enabled() is False

    with patch.dict("os.environ", {"ENABLE_TEST_AUTH": "true", "APP_ENV": "test"}, clear=True):
        assert service.is_test_auth_enabled() is True


def test_test_auth_is_disabled_for_production_environment(tmp_path):
    service = _service(tmp_path)

    with patch.dict(
        "os.environ",
        {"ENABLE_TEST_AUTH": "true", "APP_ENV": "test", "RAILWAY_ENVIRONMENT": "production"},
        clear=True,
    ):
        assert service.is_test_auth_enabled() is False


def test_test_user_from_request_uses_safe_defaults_and_headers(tmp_path):
    service = _service(tmp_path)
    request = SimpleNamespace(
        headers={
            "X-Test-Auth-Role": CASE_MANAGER_ROLE,
            "X-Test-Auth-Email": "Worker@Example.com",
            "X-Test-Auth-Case-Manager-Id": "cm_999",
        }
    )

    user = service.test_user_from_request(request)

    assert user.role == CASE_MANAGER_ROLE
    assert user.email == "worker@example.com"
    assert user.case_manager_id == "cm_999"
    assert user.auth_provider == "test"


def test_test_user_from_request_accepts_legacy_case_manager_header(tmp_path):
    service = _service(tmp_path)
    request = SimpleNamespace(
        headers={
            "X-Test-Auth-User": "uid-legacy",
            "X-Test-Auth-Case-Manager": "cm_legacy",
        }
    )

    user = service.test_user_from_request(request)

    assert user.firebase_uid == "uid-legacy"
    assert user.case_manager_id == "cm_legacy"


def test_test_user_from_request_rejects_unknown_role_to_admin_default(tmp_path):
    service = _service(tmp_path)
    request = SimpleNamespace(headers={"X-Test-Auth-Role": "owner"})

    user = service.test_user_from_request(request)

    assert user.role == ADMIN_ROLE
