import json
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import clients as clients_api
from backend.auth.service import FirebaseAuthService


class _StubClientDataIntegrator:
    def get_client_overview_data(self, client_id):
        return {
            "tasks": [
                {
                    "task_id": "task-intake-1",
                    "module": "case_management",
                    "title": "Schedule dentist appointment",
                    "priority": "high",
                    "status": "pending",
                    "due_date": "2026-06-10",
                    "need_key": "dental",
                }
            ],
            "reminders": [],
        }


def _test_app(tmp_path):
    service = FirebaseAuthService(tmp_path / "auth.db")
    app = FastAPI()

    @app.middleware("http")
    async def inject_test_auth_user(request, call_next):
        request.state.auth_user = service.test_user_from_request(request)
        return await call_next(request)

    app.include_router(clients_api.router)
    return app


def _seed_core_client(client_id="client-operational-1"):
    with clients_api.get_database_connection("core_clients", "ADMIN") as conn:
        clients_api.ensure_core_clients_schema(conn)
        client = {
            "client_id": client_id,
            "first_name": "Operational",
            "last_name": "Client",
            "email": "operational.client@example.test",
            "phone": "555-0100",
            "date_of_birth": "1987-04-03",
            "address": "123 Intake Street",
            "city": "Los Angeles",
            "state": "CA",
            "zip_code": "90012",
            "case_manager_id": "cm_test",
            "risk_level": "high",
            "case_status": "active",
            "intake_date": "2026-06-07",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "housing_status": "Transitional",
            "employment_status": "Unemployed",
            "benefits_status": "Not Applied",
            "legal_status": "Probation active",
            "program_type": "Reentry Program",
            "referral_source": "County referral",
            "prior_convictions": "Non-violent felony history",
            "substance_abuse_history": "In recovery",
            "mental_health_status": "Anxiety, medication support needed",
            "transportation": "Needs bus passes",
            "medical_conditions": "Dental pain and diabetes; disability screening requested",
            "special_needs": "SSI paperwork support",
            "goals": "Secure sober living aftercare and stable work",
            "barriers": "Needs dental appointment and court compliance support",
            "notes": "Initial intake completed.",
            "needs": json.dumps(["housing"]),
            "background": json.dumps({}),
        }
        columns = list(client.keys())
        placeholders = ", ".join("?" for _ in columns)
        conn.execute(
            f"INSERT INTO clients ({', '.join(columns)}) VALUES ({placeholders})",
            tuple(client[column] for column in columns),
        )
        conn.commit()
    return client_id


def test_operational_context_routes_intake_to_module_needs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(clients_api, "get_client_data_integrator", lambda: _StubClientDataIntegrator())
    monkeypatch.setattr(
        clients_api,
        "get_client_benefits_summary",
        lambda client_id: {"applications": [], "total_applications": 0, "active_applications": 0},
    )
    monkeypatch.setattr(
        clients_api,
        "get_client_legal_summary",
        lambda client_id: {"cases": [], "active_cases": 0, "next_court_date": None},
    )
    monkeypatch.setattr(
        clients_api,
        "get_client_services_summary",
        lambda client_id: {"referrals": [], "tasks": [], "open_tasks": 0},
    )
    client_id = _seed_core_client()
    client = TestClient(_test_app(tmp_path))

    response = client.get(
        f"/api/clients/{client_id}/operational-context",
        headers={
            "X-Test-Auth-Email": "case.manager@example.test",
            "X-Test-Auth-Case-Manager-Id": "cm_test",
            "X-Test-Auth-Role": "case_manager",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    context = payload["operational_context"]

    assert context["client"]["full_name"] == "Operational Client"
    assert context["client"]["phone"] == "555-0100"
    assert context["intake"]["medical_conditions"].startswith("Dental pain")
    assert context["treatment_plan"]["status"] == "intake_seed"
    assert context["metadata"]["read_only"] is True

    need_keys = {need["need_key"] for need in context["operational_needs"]}
    assert {
        "housing",
        "resume",
        "job_search",
        "benefits_screening",
        "legal_follow_up",
        "dental",
        "primary_care",
        "behavioral_health",
        "disability",
        "transportation",
        "sober_living_aftercare",
    }.issubset(need_keys)

    assert context["module_context"]["resume"]["contact"]["email"] == "operational.client@example.test"
    assert {need["need_key"] for need in context["module_context"]["medical"]["active_needs"]} >= {
        "dental",
        "primary_care",
    }
    assert context["open_tasks"][0]["need_key"] == "dental"


def test_operational_context_enforces_case_manager_access(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client_id = _seed_core_client("client-access-denied")
    client = TestClient(_test_app(tmp_path))

    response = client.get(
        f"/api/clients/{client_id}/operational-context",
        headers={
            "X-Test-Auth-Email": "other.case.manager@example.test",
            "X-Test-Auth-Case-Manager-Id": "cm_other",
            "X-Test-Auth-Role": "case_manager",
        },
    )

    assert response.status_code == 403
