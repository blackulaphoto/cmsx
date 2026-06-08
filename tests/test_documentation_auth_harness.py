from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth.service import FirebaseAuthService
from backend.modules.ai_documentation.routes import router as ai_documentation_router
from backend.modules.ai_documentation.service import documentation_ai_service


def _test_app(tmp_path):
    service = FirebaseAuthService(tmp_path / "auth.db")
    app = FastAPI()

    @app.middleware("http")
    async def inject_test_auth_user(request, call_next):
        request.state.auth_user = service.test_user_from_request(request)
        return await call_next(request)

    app.include_router(ai_documentation_router, prefix="/api")
    return app


def test_documentation_templates_endpoint_works_with_test_auth_headers(tmp_path):
    client = TestClient(_test_app(tmp_path))

    response = client.get(
        "/api/ai-documentation/templates",
        headers={
            "X-Test-Auth-Email": "e2e.case.manager@example.com",
            "X-Test-Auth-Case-Manager-Id": "cm_e2e",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert isinstance(payload["templates"], list)


def test_documentation_draft_endpoint_works_with_test_auth_and_no_bearer_token(tmp_path, monkeypatch):
    monkeypatch.setattr(documentation_ai_service, "client", None)
    client = TestClient(_test_app(tmp_path))

    response = client.post(
        "/api/ai-documentation/note-draft",
        headers={
            "X-Test-Auth-Email": "e2e.case.manager@example.com",
            "X-Test-Auth-Case-Manager-Id": "cm_e2e",
        },
        json={
            "module": "documentation_center_e2e",
            "note_kind": "progress_note",
            "client_name": "E2E Test Client",
            "user_prompt": "Client discussed housing barriers and probation follow-up.",
            "current_text": "GOAL:\nINTERVENTION:\nRESPONSE:\nPLAN:",
            "context": {
                "template_label": "Weekly CM Note",
                "direct_quotes": ["I need housing this week."],
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["draft"]
    assert "GOAL:" in payload["draft"]
    assert "INTERVENTION:" in payload["draft"]
    assert "RESPONSE:" in payload["draft"]
    assert "PLAN:" in payload["draft"]
