import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.auth.service import AuthenticatedUser
from backend.modules.fmla import routes as fmla_routes
from backend.modules.fmla.store import FMLAStore


class FMLAStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.fmla_db = self.base_path / "fmla.db"
        self.reminders_db = self.base_path / "reminders.db"
        conn = sqlite3.connect(self.reminders_db)
        conn.execute(
            """
            CREATE TABLE active_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id TEXT UNIQUE NOT NULL,
                client_id TEXT,
                case_manager_id TEXT,
                reminder_type TEXT,
                message TEXT,
                priority TEXT,
                due_date TEXT,
                status TEXT,
                created_at TEXT
            )
            """
        )
        conn.commit()
        conn.close()
        self.store = FMLAStore(str(self.fmla_db), str(self.reminders_db))
        self.original_store = fmla_routes.store
        self.original_upload_dir = fmla_routes.FMLA_UPLOADS_DIR
        fmla_routes.store = self.store
        fmla_routes.FMLA_UPLOADS_DIR = self.base_path / "uploads"
        fmla_routes.FMLA_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

        app = FastAPI()

        @app.middleware("http")
        async def inject_auth_user(request: Request, call_next):
            request.state.auth_user = AuthenticatedUser(
                firebase_uid="uid-1",
                email="case.manager@example.com",
                full_name="Case Manager",
                role="admin",
                case_manager_id="cm_001",
                auth_provider="password",
                is_active=True,
            )
            return await call_next(request)

        app.include_router(fmla_routes.router, prefix="/api")
        self.client = TestClient(app)

    def tearDown(self):
        fmla_routes.store = self.original_store
        fmla_routes.FMLA_UPLOADS_DIR = self.original_upload_dir
        self.temp_dir.cleanup()

    def _create_case(self, **overrides):
        payload = {
            "client_id": "",
            "client_name": "Taylor Jones",
            "assigned_case_manager": "cm_001",
            "employer_name": "ACME Logistics",
            "fmla_request_type": "new request",
            "leave_type": "continuous",
            "paperwork_deadline": "2030-01-15",
            "status": "pending documents",
            "approval_status": "pending",
        }
        payload.update(overrides)
        return self.store.create_case(payload)

    def test_create_and_update_case_persists_after_reload(self):
        created = self._create_case()
        self.assertEqual(created["client_name"], "Taylor Jones")

        updated = self.store.update_case(created["case_id"], {"status": "submitted", "confirmation_received": True})
        self.assertIsNotNone(updated)
        self.assertEqual(updated["status"], "submitted")
        self.assertEqual(updated["confirmation_received"], 1)

        reloaded_store = FMLAStore(str(self.fmla_db), str(self.reminders_db))
        reloaded = reloaded_store.get_case(created["case_id"])
        self.assertEqual(reloaded["status"], "submitted")
        self.assertEqual(reloaded["confirmation_received"], 1)

    def test_add_document_and_correspondence(self):
        created = self._create_case()
        document = self.store.create_document(
            created["case_id"],
            {
                "document_type": "medical certification",
                "document_status": "received",
                "date_received": "2030-01-10",
                "uploader_name": "Case Manager",
            },
        )
        correspondence = self.store.create_correspondence(
            created["case_id"],
            {
                "contact_type": "email",
                "summary": "Requested provider completion timeline",
                "organization": "Provider Clinic",
            },
        )

        documents = self.store.list_documents(created["case_id"])
        correspondence_rows = self.store.list_correspondence(created["case_id"])
        self.assertEqual(document["document_type"], "medical certification")
        self.assertEqual(documents[0]["uploader_name"], "Case Manager")
        self.assertEqual(len(documents), 1)
        self.assertEqual(correspondence["contact_type"], "email")
        self.assertEqual(len(correspondence_rows), 1)

    def test_upload_and_download_document_packet(self):
        created = self._create_case()
        upload_response = self.client.post(
            f"/api/fmla/{created['case_id']}/documents/upload",
            data={
                "batch_name": "Initial employer packet",
                "document_type": "ROI",
                "document_status": "received",
                "date_received": "2030-01-11",
                "sent_to": "Provider Clinic",
            },
            files=[
                ("files", ("release.pdf", b"fake-pdf-content", "application/pdf")),
                ("files", ("employer-letter.jpg", b"fake-image-content", "image/jpeg")),
            ],
        )

        self.assertEqual(upload_response.status_code, 200)
        payload = upload_response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["document_count"], 2)
        first_document = payload["documents"][0]
        stored_first = self.store.get_document(first_document["document_id"])
        self.assertEqual(stored_first["uploader_case_manager_id"], "cm_001")
        self.assertTrue((fmla_routes.FMLA_UPLOADS_DIR / stored_first["file_path"]).exists())

        download_response = self.client.get(f"/api/fmla/documents/{first_document['document_id']}/download")
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(download_response.content, b"fake-pdf-content")
        self.assertEqual(download_response.headers["content-type"], "application/pdf")

    def test_create_reminder_writes_to_main_reminders_table(self):
        created = self._create_case()
        reminder = self.store.create_reminder(
            created["case_id"],
            {
                "reminder_text": "Follow up with HR on receipt confirmation",
                "due_date": "2030-01-12",
                "priority": "High",
                "case_manager_id": "cm_001",
                "reason": "confirm fax receipt",
            },
        )

        self.assertEqual(reminder["priority"], "High")
        linked = self.store.list_case_reminders(created["case_id"])
        self.assertEqual(len(linked), 1)
        self.assertIn("Taylor Jones", linked[0]["message"])

        conn = sqlite3.connect(self.reminders_db)
        row = conn.execute("SELECT reminder_type, priority, due_date FROM active_reminders").fetchone()
        conn.close()
        self.assertEqual(row[0], "fmla")
        self.assertEqual(row[1], "High")
        self.assertEqual(row[2], "2030-01-12")

    def test_leave_usage_and_exports_persist(self):
        created = self._create_case(leave_type="intermittent", certification_expiration_date="2030-02-01")

        usage_response = self.client.post(
            f"/api/fmla/{created['case_id']}/leave-usage",
            json={
                "usage_date": "2030-01-05",
                "duration_minutes": 90,
                "reason_category": "medical appointment",
                "notes": "Follow-up visit",
            },
        )
        self.assertEqual(usage_response.status_code, 200)
        usage_payload = usage_response.json()
        self.assertEqual(usage_payload["summary"]["total_minutes"], 90)

        draft_response = self.client.post(
            f"/api/fmla/{created['case_id']}/exports/draft",
            json={
                "export_type": "employer packet",
                "custom_instructions": "Avoid diagnosis details",
            },
        )
        self.assertEqual(draft_response.status_code, 200)
        draft_payload = draft_response.json()
        self.assertIn("Generated draft only", draft_payload["export"]["warning_text"])

        export_id = draft_payload["export"]["export_id"]
        pdf_response = self.client.post(
            f"/api/fmla/{created['case_id']}/exports/{export_id}/pdf",
            json={
                "draft_title": "Employer Safe Packet",
                "draft_content": draft_payload["export"]["draft_content"],
                "review_notes": "Reviewed by supervisor",
            },
        )
        self.assertEqual(pdf_response.status_code, 200)
        export_payload = pdf_response.json()
        self.assertTrue(export_payload["export"]["safe_filename"].endswith(".pdf"))

        download_response = self.client.get(f"/api/fmla/exports/{export_id}/download")
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(download_response.headers["content-type"], "application/pdf")

    def test_filters_and_summary(self):
        first = self._create_case(status="approved", approval_status="approved")
        self.store.create_case(
            {
                "client_id": "",
                "client_name": "Jordan Smith",
                "assigned_case_manager": "cm_001",
                "employer_name": "Northwind Health",
                "fmla_request_type": "extension",
                "leave_type": "continuous",
                "paperwork_deadline": "2000-01-01",
                "status": "denied",
                "approval_status": "denied",
            }
        )
        self.store.create_case(
            {
                "case_subject_type": "staff",
                "client_name": "Staff leave case",
                "staff_identifier": "emp-22",
                "staff_name": "Alex Worker",
                "assigned_case_manager": "cm_001",
                "employer_name": "Northwind Health",
                "fmla_request_type": "new request",
                "leave_type": "reduced schedule",
                "status": "submitted",
                "approval_status": "pending",
            }
        )
        denied_cases = self.store.list_cases({"status": "denied"})
        self.assertEqual(len(denied_cases), 1)

        summary = self.store.get_summary("cm_001")
        self.assertEqual(summary["approved_cases"], 1)
        self.assertEqual(summary["denied_cases"], 1)
        self.assertGreaterEqual(summary["missing_paperwork"], 3)
        self.assertGreaterEqual(summary["total_active_cases"], 2)


if __name__ == "__main__":
    unittest.main()
