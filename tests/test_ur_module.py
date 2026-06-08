import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DATABASE_URL", "postgresql://ur-test")

from backend.modules.ur import routes as ur_routes
from backend.modules.ur.postgres_store import PostgresURStore
from backend.shared.database.railway_ur_postgres import ensure_postgres_ur_tables
from tests.auth_helpers import add_test_auth_middleware, make_test_user


class URModuleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.sqlite_url = f"sqlite:///{self.base_path / 'ur.db'}"
        self.engine = create_engine(self.sqlite_url, future=True)
        self.engine_patches = [
            patch("backend.shared.database.railway_ur_postgres._engine", return_value=self.engine),
            patch("backend.modules.ur.postgres_store._engine", return_value=self.engine),
        ]
        for engine_patch in self.engine_patches:
            engine_patch.start()

        self.store = PostgresURStore()
        self.original_store = ur_routes.store
        ur_routes.store = self.store

        self.client = self._build_client()

    def _build_client(self, user=None):
        app = FastAPI()
        add_test_auth_middleware(app, user)
        app.include_router(ur_routes.router, prefix="/api")
        return TestClient(app)

    def tearDown(self):
        ur_routes.store = self.original_store
        self.engine.dispose()
        for engine_patch in reversed(self.engine_patches):
            engine_patch.stop()
        self.temp_dir.cleanup()

    def _create_case(self, **overrides):
        payload = {
            "client_id": "",
            "client_name": "Taylor Jones",
            "assigned_case_manager": "cm_001",
            "payer": "Health Net",
            "facility": "Main Campus",
            "program": "Residential",
            "current_level_of_care": "Detox",
            "requested_level_of_care": "Residential",
            "approved_level_of_care": "Residential",
            "admit_date": "2030-01-01",
            "requested_days": 14,
            "approved_days": 7,
            "approved_end_date": "2030-01-05",
            "next_review_date": "2030-01-03",
            "reviewer_name": "Jane Smith",
            "reviewer_company": "Health Net",
            "auth_submission_method": "Portal",
            "decision_received_method": "Fax",
            "clinical_criteria_used": "ASAM",
            "clinical_justification_summary": "Continued withdrawal management required.",
            "revenue_at_risk_amount": 4200,
            "status": "approved",
        }
        payload.update(overrides)
        return self.store.create_case(payload)

    def test_create_and_update_case(self):
        created = self._create_case()
        self.assertEqual(created["denied_days"], 7)
        self.assertEqual(created["reviewer_company"], "Health Net")

        updated = self.store.update_case(
            created["case_id"],
            {
                "client_name": "Taylor Jones Updated",
                "payer": "Aetna",
                "facility": "North Campus",
                "program": "PHP",
                "current_level_of_care": "Residential",
                "requested_level_of_care": "PHP",
                "approved_level_of_care": "PHP",
                "admit_date": "2030-01-01",
                "requested_days": 10,
                "approved_days": 6,
                "reviewer_company": "Aetna UM",
                "clinical_justification_summary": "Still unstable.",
                "status": "submitted",
            },
        )
        self.assertEqual(updated["payer"], "Aetna")
        self.assertEqual(updated["reviewer_company"], "Aetna UM")
        self.assertEqual(updated["denied_days"], 4)

    def test_route_create_detail_and_events(self):
        response = self.client.post(
            "/api/ur",
            json={
                "client_id": "",
                "client_name": "Jordan Smith",
                "payer": "Blue Shield",
                "facility": "South Campus",
                "program": "PHP",
                "current_level_of_care": "Residential",
                "requested_level_of_care": "PHP",
                "approved_level_of_care": "PHP",
                "admit_date": "2030-02-01",
                "requested_days": 7,
                "approved_days": 4,
                "reviewer_company": "Blue Shield",
                "clinical_justification_summary": "Needs continued structure.",
                "status": "submitted",
            },
        )
        self.assertEqual(response.status_code, 200)
        case_id = response.json()["case"]["case_id"]

        event_response = self.client.post(
            f"/api/ur/{case_id}/events",
            json={
                "event_type": "concurrent_review",
                "event_date": "2030-02-03T09:00:00",
                "requested_days": 7,
                "approved_days": 4,
                "reviewer_name": "Reviewer A",
                "reviewer_company": "Blue Shield",
                "notes": "Concurrent review completed",
            },
        )
        self.assertEqual(event_response.status_code, 200)

        detail_response = self.client.get(f"/api/ur/{case_id}")
        self.assertEqual(detail_response.status_code, 200)
        payload = detail_response.json()
        self.assertEqual(payload["case"]["client_name"], "Jordan Smith")
        self.assertEqual(len(payload["events"]), 1)
        self.assertEqual(payload["events"][0]["event_type"], "concurrent_review")

    def test_summary_metrics_and_filters(self):
        self._create_case(
            client_name="Taylor Jones",
            requested_days=14,
            approved_days=7,
            denied_days="",
            next_review_date="2030-01-03",
            approved_end_date="2030-01-03",
            appeal_deadline="2030-01-06",
            status="appeal_pending",
        )
        self._create_case(
            client_name="Jordan Smith",
            payer="Aetna",
            requested_days=10,
            approved_days=0,
            denied_days=10,
            next_review_date="2030-01-02",
            approved_end_date="",
            peer_review_deadline="2030-01-04",
            status="denied",
            revenue_at_risk_amount=1800,
        )

        with patch("backend.modules.ur.postgres_store.datetime") as mocked_datetime:
            from datetime import datetime as real_datetime

            mocked_datetime.utcnow.return_value = real_datetime(2030, 1, 2, 12, 0, 0)
            mocked_datetime.fromisoformat = real_datetime.fromisoformat
            summary = self.store.get_summary("cm_001")

        self.assertEqual(summary["total_authorized_days"], 7)
        self.assertEqual(summary["total_denied_days"], 17)
        self.assertAlmostEqual(summary["average_approval_rate"], 0.25)
        self.assertEqual(summary["reviews_due_today"], 1)
        self.assertEqual(summary["due_in_72_hours"], 2)
        self.assertEqual(summary["auth_expiring"], 1)
        self.assertEqual(summary["denials_needing_action"], 1)
        self.assertEqual(summary["appeals_due"], 1)
        self.assertEqual(summary["revenue_at_risk"], 6000.0)

        denied_response = self.client.get("/api/ur?due_window=denials")
        self.assertEqual(denied_response.status_code, 200)
        self.assertEqual(len(denied_response.json()["cases"]), 1)

    def test_route_update_case(self):
        created = self._create_case()
        response = self.client.put(
            f"/api/ur/{created['case_id']}",
            json={
                "client_id": "",
                "client_name": "Taylor Jones",
                "payer": "Health Net",
                "facility": "Main Campus",
                "program": "Residential",
                "current_level_of_care": "Residential",
                "requested_level_of_care": "PHP",
                "approved_level_of_care": "PHP",
                "admit_date": "2030-01-01",
                "requested_days": 14,
                "approved_days": 9,
                "denied_days": 5,
                "reviewer_company": "Health Net UM",
                "clinical_justification_summary": "Improving but still unstable.",
                "status": "approved",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["case"]
        self.assertEqual(payload["approved_days"], 9)
        self.assertEqual(payload["denied_days"], 5)
        self.assertEqual(payload["reviewer_company"], "Health Net UM")

    def test_route_validation_rejects_missing_required_fields_and_negative_days(self):
        missing_name = self.client.post(
            "/api/ur",
            json={
                "payer": "Health Net",
                "admit_date": "2030-01-01",
                "requested_days": 1,
            },
        )
        self.assertEqual(missing_name.status_code, 422)

        negative_days = self.client.post(
            "/api/ur",
            json={
                "client_name": "Taylor Jones",
                "payer": "Health Net",
                "admit_date": "2030-01-01",
                "requested_days": -1,
            },
        )
        self.assertEqual(negative_days.status_code, 422)

    def test_route_rejects_unsupported_statuses_and_event_types(self):
        bad_filter = self.client.get("/api/ur?status=not_real")
        self.assertEqual(bad_filter.status_code, 400)
        self.assertEqual(bad_filter.json()["detail"], "Unsupported UR status filter")

        bad_status = self.client.post(
            "/api/ur",
            json={
                "client_name": "Taylor Jones",
                "payer": "Health Net",
                "admit_date": "2030-01-01",
                "status": "not_real",
            },
        )
        self.assertEqual(bad_status.status_code, 400)
        self.assertEqual(bad_status.json()["detail"], "Unsupported UR status")

        created = self._create_case()
        bad_event = self.client.post(
            f"/api/ur/{created['case_id']}/events",
            json={"event_type": "not_real"},
        )
        self.assertEqual(bad_event.status_code, 400)
        self.assertEqual(bad_event.json()["detail"], "Unsupported UR event type")

    def test_missing_case_routes_return_404(self):
        detail = self.client.get("/api/ur/missing-case-id")
        self.assertEqual(detail.status_code, 404)

        update = self.client.put(
            "/api/ur/missing-case-id",
            json={
                "client_name": "Taylor Jones",
                "payer": "Health Net",
                "admit_date": "2030-01-01",
            },
        )
        self.assertEqual(update.status_code, 404)

        event_create = self.client.post(
            "/api/ur/missing-case-id/events",
            json={"event_type": "initial_auth"},
        )
        self.assertEqual(event_create.status_code, 404)

        event_list = self.client.get("/api/ur/missing-case-id/events")
        self.assertEqual(event_list.status_code, 404)

    def test_non_admin_case_manager_scope_is_enforced(self):
        non_admin_client = self._build_client(
            make_test_user(role="case_manager", case_manager_id="cm_001")
        )
        own_case = self._create_case(assigned_case_manager="cm_001", client_name="Own Case")
        other_case = self._create_case(assigned_case_manager="cm_999", client_name="Other Case")

        list_response = non_admin_client.get("/api/ur")
        self.assertEqual(list_response.status_code, 200)
        listed_ids = {case["case_id"] for case in list_response.json()["cases"]}
        self.assertIn(own_case["case_id"], listed_ids)
        self.assertNotIn(other_case["case_id"], listed_ids)

        other_detail = non_admin_client.get(f"/api/ur/{other_case['case_id']}")
        self.assertEqual(other_detail.status_code, 403)

    def test_non_admin_create_assigns_current_case_manager(self):
        non_admin_client = self._build_client(
            make_test_user(role="case_manager", case_manager_id="cm_001")
        )
        response = non_admin_client.post(
            "/api/ur",
            json={
                "client_name": "Assigned By Auth",
                "assigned_case_manager": "cm_999",
                "payer": "Health Net",
                "admit_date": "2030-01-01",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["case"]["assigned_case_manager"], "cm_001")

    def test_create_with_unknown_client_id_returns_404(self):
        response = self.client.post(
            "/api/ur",
            json={
                "client_id": "missing-client",
                "client_name": "Taylor Jones",
                "payer": "Health Net",
                "admit_date": "2030-01-01",
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Client not found")

    def test_schema_creation_is_idempotent_and_creates_expected_indexes(self):
        ensure_postgres_ur_tables(self.engine)
        ensure_postgres_ur_tables(self.engine)

        inspector = inspect(self.engine)
        tables = set(inspector.get_table_names())
        self.assertIn("railway_ur_cases", tables)
        self.assertIn("railway_ur_review_events", tables)

        case_columns = {column["name"] for column in inspector.get_columns("railway_ur_cases")}
        event_columns = {column["name"] for column in inspector.get_columns("railway_ur_review_events")}
        self.assertIn("case_id", case_columns)
        self.assertIn("client_name", case_columns)
        self.assertIn("status", case_columns)
        self.assertIn("event_id", event_columns)
        self.assertIn("case_id", event_columns)
        self.assertIn("event_type", event_columns)

        case_indexes = {index["name"] for index in inspector.get_indexes("railway_ur_cases")}
        event_indexes = {index["name"] for index in inspector.get_indexes("railway_ur_review_events")}
        self.assertIn("idx_railway_ur_cases_manager", case_indexes)
        self.assertIn("idx_railway_ur_cases_status", case_indexes)
        self.assertIn("idx_railway_ur_events_case_date", event_indexes)
