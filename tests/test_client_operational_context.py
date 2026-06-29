import json
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import clients as clients_api
from backend.auth.service import FirebaseAuthService
from backend.modules.ai_documentation.service import documentation_ai_service
from backend.modules.reminders import repository as reminders_repository
from backend.modules.reminders import routes as reminders_routes
from backend.shared.database.workspace_store import workspace_store


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


def _use_temp_workspace_store(tmp_path):
    original_db_path = workspace_store.db_path
    workspace_store.db_path = tmp_path / "workspace_content.db"
    workspace_store._initialize()
    return original_db_path


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


def test_unified_view_merges_medical_referrals_into_existing_services_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client_id = _seed_core_client("client-unified-view")
    client = TestClient(_test_app(tmp_path))

    monkeypatch.setattr(clients_api, "get_client_data_integrator", lambda: _StubClientDataIntegrator())
    monkeypatch.setattr(
        clients_api,
        "get_client_benefits_summary",
        lambda _client_id: {"applications": [], "total_applications": 0, "active_applications": 0},
    )
    monkeypatch.setattr(
        clients_api,
        "get_client_legal_summary",
        lambda _client_id: {"cases": [], "active_cases": 0, "next_court_date": None},
    )
    monkeypatch.setattr(
        clients_api,
        "get_client_services_summary",
        lambda _client_id: {
            "referrals": [
                {
                    "referral_id": "service-ref-1",
                    "provider_name": "County Services Hub",
                    "service_name": "Benefits Intake",
                    "service_type": "Benefits",
                    "status": "Pending",
                    "referral_date": "2026-06-09T09:00:00",
                }
            ],
            "tasks": [],
            "total_referrals": 1,
            "active_referrals": 1,
            "open_tasks": 0,
        },
    )
    monkeypatch.setattr(
        clients_api,
        "get_client_medical_referrals_summary",
        lambda _client_id: [
            {
                "referral_id": "medical-ref-1",
                "provider_name": "Sunrise Health Clinic",
                "service_name": "Medical Access Referral",
                "service_type": "Primary Care",
                "service_category": "medical",
                "status": "Identified",
                "referral_date": "2026-06-10T11:30:00",
                "notes": "Accepts Medi-Cal.",
                "source_module": "medical_access",
            }
        ],
    )
    monkeypatch.setattr(
        workspace_store,
        "list_client_service_referrals",
        lambda _client_id: [
            {
                "ref_id": "ws-ref-1",
                "provider_name": "Community Dental Partners",
                "service_name": "Dental",
                "service_type": "Dental",
                "status": "pending",
                "referral_date": "2026-06-08",
                "notes": "Bring insurance card.",
            }
        ],
    )
    monkeypatch.setattr(workspace_store, "list_client_appointments", lambda _client_id: [])
    monkeypatch.setattr(workspace_store, "list_client_documents", lambda _client_id: [])

    response = client.get(
        f"/api/clients/{client_id}/unified-view",
        headers={
            "X-Test-Auth-Email": "case.manager@example.test",
            "X-Test-Auth-Case-Manager-Id": "cm_test",
            "X-Test-Auth-Role": "case_manager",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    referrals = payload["client_data"]["services"]["referrals"]
    assert [ref["referral_id"] for ref in referrals if ref.get("referral_id")] == ["medical-ref-1", "service-ref-1"]
    assert referrals[0]["source_module"] == "medical_access"
    assert referrals[0]["provider_name"] == "Sunrise Health Clinic"
    assert any(ref.get("provider_name") == "Community Dental Partners" for ref in referrals)
    assert payload["client_data"]["services"]["total_referrals"] == 3


def test_treatment_plan_draft_approve_and_context_readback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original_workspace_db = _use_temp_workspace_store(tmp_path)
    monkeypatch.setattr(
        documentation_ai_service,
        "generate_treatment_plan_suggestions",
        lambda payload: {
            "goal": "Client will secure sober living and complete dental follow-up.",
            "objective": "Client will complete two documented service actions within 30 days.",
            "interventions": [
                "Case manager will coordinate sober living referrals.",
                "Case manager will support dental appointment scheduling.",
            ],
            "needs_considered": payload["context"]["needs"],
        },
    )
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
    client_id = _seed_core_client("client-treatment-plan")
    client = TestClient(_test_app(tmp_path))
    headers = {
        "X-Test-Auth-Email": "case.manager@example.test",
        "X-Test-Auth-Case-Manager-Id": "cm_test",
        "X-Test-Auth-Role": "case_manager",
    }

    try:
        draft_response = client.post(
            f"/api/clients/{client_id}/treatment-plan/draft",
            headers=headers,
            json={"source": "ai_suggestion", "review_due_date": "2026-07-07"},
        )

        assert draft_response.status_code == 200
        draft_payload = draft_response.json()
        assert draft_payload["success"] is True
        plan = draft_payload["plan"]
        assert plan["status"] == "draft"
        assert plan["client_id"] == client_id
        assert plan["goals"][0]["description"] == "Client will secure sober living and complete dental follow-up."
        assert {need["need_key"] for need in plan["operational_needs"]} >= {"dental", "sober_living_aftercare"}

        approve_response = client.post(
            f"/api/clients/{client_id}/treatment-plan/{plan['plan_id']}/approve",
            headers=headers,
        )

        assert approve_response.status_code == 200
        approve_payload = approve_response.json()
        approved_plan = approve_payload["plan"]
        assert approved_plan["status"] == "active"
        assert approved_plan["approved_by"] == "cm_test"
        assert approve_payload["created_task_count"] >= 2
        task_need_keys = {task["need_key"] for task in approve_payload["created_tasks"]}
        assert {"dental", "sober_living_aftercare"}.issubset(task_need_keys)

        repeat_approve_response = client.post(
            f"/api/clients/{client_id}/treatment-plan/{plan['plan_id']}/approve",
            headers=headers,
        )

        assert repeat_approve_response.status_code == 200
        assert repeat_approve_response.json()["created_task_count"] == 0

        context_response = client.get(
            f"/api/clients/{client_id}/operational-context",
            headers=headers,
        )

        assert context_response.status_code == 200
        treatment_plan = context_response.json()["operational_context"]["treatment_plan"]
        assert treatment_plan["plan_id"] == plan["plan_id"]
        assert treatment_plan["status"] == "active"
        assert treatment_plan["review_due_date"] == "2026-07-07"
        stored_need_keys = {need["need_key"] for need in context_response.json()["operational_context"]["operational_needs"]}
        assert {"dental", "sober_living_aftercare"}.issubset(stored_need_keys)
    finally:
        workspace_store.db_path = original_workspace_db
        workspace_store._initialize()


def test_documentation_context_uses_current_treatment_plan(tmp_path):
    original_workspace_db = _use_temp_workspace_store(tmp_path)
    try:
        plan = workspace_store.create_treatment_plan_draft(
            "client-doc-plan",
            created_by="cm_test",
            plan_data={
                "source": "test",
                "goals": [{"description": "Client will maintain sober living placement."}],
                "objectives": [{"description": "Client will attend weekly recovery support."}],
                "interventions": [{"description": "CM will monitor placement and aftercare adherence."}],
                "aftercare_plan": {"summary": "Sober living plus outpatient aftercare."},
            },
        )
        approved = workspace_store.approve_treatment_plan(plan["plan_id"], approved_by="cm_test")

        context = documentation_ai_service._build_shared_intake_context(
            {
                "core": {
                    "client_id": "client-doc-plan",
                    "first_name": "Doc",
                    "last_name": "Plan",
                    "goals": "Legacy intake goal",
                },
                "treatment_plan": approved,
            },
            client_name="Doc Plan",
        )

        assert "maintain sober living placement" in context["treatment_plan_summary"]
        assert "Sober living plus outpatient aftercare" in context["aftercare_plan_summary"]
    finally:
        workspace_store.db_path = original_workspace_db
        workspace_store._initialize()


def test_smart_daily_includes_and_completes_treatment_plan_tasks(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    original_workspace_db = _use_temp_workspace_store(tmp_path)
    client_id = _seed_core_client("client-smart-daily")

    try:
        plan = workspace_store.create_treatment_plan_draft(
            client_id,
            created_by="cm_test",
            plan_data={
                "source": "test",
                "goals": [{"description": "Client will resolve dental pain and medical follow-up."}],
                "operational_needs": [
                    {
                        "need_key": "dental",
                        "domain": "medical",
                        "module": "medical",
                        "priority": "high",
                        "status": "open",
                        "reason": "Dental pain was confirmed in the approved treatment plan.",
                    }
                ],
            },
        )
        approved = workspace_store.approve_treatment_plan(plan["plan_id"], approved_by="cm_test")
        needs = workspace_store.upsert_operational_needs(
            client_id,
            approved["operational_needs"],
            source="treatment_plan",
            source_id=plan["plan_id"],
            source_plan_id=plan["plan_id"],
        )
        created_tasks = workspace_store.create_tasks_from_operational_needs(
            client_id,
            needs,
            source="treatment_plan",
            source_id=plan["plan_id"],
            assigned_to="cm_test",
        )

        result = reminders_repository.get_prioritized_tasks("cm_test")
        treatment_plan_tasks = result["buckets"]["treatment_plan"]

        assert result["counts"]["treatment_plan"] == 1
        assert treatment_plan_tasks[0]["task_id"] == created_tasks[0]["task_id"]
        assert treatment_plan_tasks[0]["source"] == "workspace_task"
        assert treatment_plan_tasks[0]["task_source"] == "treatment_plan"
        assert treatment_plan_tasks[0]["module"] == "medical"
        assert treatment_plan_tasks[0]["need_key"] == "dental"
        assert "Approved treatment plan need: dental." in treatment_plan_tasks[0]["priority_reason"]
        assert result["total_active"] >= 1

        app = FastAPI()
        app.include_router(reminders_routes.router, prefix="/api/reminders")
        complete_response = TestClient(app).post(f"/api/reminders/tasks/{created_tasks[0]['task_id']}/complete")

        assert complete_response.status_code == 200
        assert complete_response.json()["source"] == "workspace_task"
        stored_task = workspace_store.get_client_task(created_tasks[0]["task_id"])
        assert stored_task["status"] == "completed"
        assert stored_task["completed_at"]
    finally:
        workspace_store.db_path = original_workspace_db
        workspace_store._initialize()
