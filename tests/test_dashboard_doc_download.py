from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth.service import FirebaseAuthService
from backend.modules.dashboard.routes import router as dashboard_router
from backend.shared.database.workspace_store import workspace_store


def _test_app(tmp_path):
    service = FirebaseAuthService(tmp_path / "auth.db")
    app = FastAPI()

    @app.middleware("http")
    async def inject_test_auth_user(request, call_next):
        request.state.auth_user = service.test_user_from_request(request)
        return await call_next(request)

    app.include_router(dashboard_router, prefix="/api")
    return app


def _headers(case_manager_id="cm_e2e"):
    return {
        "X-Test-Auth-Email": "e2e.case.manager@example.com",
        "X-Test-Auth-Name": "E2E Case Manager",
        "X-Test-Auth-Role": "case_manager",
        "X-Test-Auth-Case-Manager-Id": case_manager_id,
    }


def test_dashboard_doc_download_returns_pdf_and_text(tmp_path):
    client = TestClient(_test_app(tmp_path))
    doc = workspace_store.create_dashboard_doc(
        "cm_e2e",
        "E2E Export Document",
        "PROOF OF RESIDENCY\n\nThis exported document should include saved content.",
        None,
    )

    try:
        pdf_response = client.get(
            f"/api/dashboard/docs/{doc['id']}/download?format=pdf",
            headers=_headers(),
        )
        assert pdf_response.status_code == 200
        assert pdf_response.headers["content-type"] == "application/pdf"
        assert pdf_response.content.startswith(b"%PDF-1.4")
        assert b"PROOF OF RESIDENCY" in pdf_response.content

        text_response = client.get(
            f"/api/dashboard/docs/{doc['id']}/download?format=txt",
            headers=_headers(),
        )
        assert text_response.status_code == 200
        assert "text/plain" in text_response.headers["content-type"]
        assert "E2E Export Document" in text_response.text
        assert "PROOF OF RESIDENCY" in text_response.text
    finally:
        workspace_store.delete_dashboard_item("dashboard_docs", doc["id"])


def test_dashboard_doc_download_enforces_case_manager_scope(tmp_path):
    client = TestClient(_test_app(tmp_path))
    doc = workspace_store.create_dashboard_doc(
        "cm_owner",
        "Private Export Document",
        "This should not download for another case manager.",
        None,
    )

    try:
        response = client.get(
            f"/api/dashboard/docs/{doc['id']}/download?format=pdf",
            headers=_headers(case_manager_id="cm_other"),
        )
        assert response.status_code == 403
    finally:
        workspace_store.delete_dashboard_item("dashboard_docs", doc["id"])
