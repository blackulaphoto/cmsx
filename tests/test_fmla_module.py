import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
        app.include_router(fmla_routes.router, prefix="/api")
        self.client = TestClient(app)

    def tearDown(self):
        fmla_routes.store = self.original_store
        fmla_routes.FMLA_UPLOADS_DIR = self.original_upload_dir
        self.temp_dir.cleanup()

    def _create_case(self):
        return self.store.create_case(
            {
                "client_id": "client_1",
                "client_name": "Taylor Jones",
                "assigned_case_manager": "cm_001",
                "employer_name": "ACME Logistics",
                "fmla_request_type": "new request",
                "paperwork_deadline": "2030-01-15",
                "status": "Waiting on provider",
                "approval_status": "pending",
            }
        )

    def test_create_and_update_case_persists_after_reload(self):
        created = self._create_case()
        self.assertEqual(created["client_name"], "Taylor Jones")

        updated = self.store.update_case(created["case_id"], {"status": "Paperwork sent", "confirmation_received": True})
        self.assertIsNotNone(updated)
        self.assertEqual(updated["status"], "Paperwork sent")
        self.assertEqual(updated["confirmation_received"], 1)

        reloaded_store = FMLAStore(str(self.fmla_db), str(self.reminders_db))
        reloaded = reloaded_store.get_case(created["case_id"])
        self.assertEqual(reloaded["status"], "Paperwork sent")
        self.assertEqual(reloaded["confirmation_received"], 1)

    def test_add_document_and_correspondence(self):
        created = self._create_case()
        document = self.store.create_document(
            created["case_id"],
            {
                "document_type": "medical certification",
                "document_status": "received",
                "date_received": "2030-01-10",
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
        self.assertEqual(len(payload["documents"]), 2)
        first_document = payload["documents"][0]
        second_document = payload["documents"][1]
        self.assertEqual(first_document["batch_name"], "Initial employer packet")
        self.assertTrue(first_document["batch_id"])
        self.assertEqual(first_document["batch_id"], second_document["batch_id"])
        self.assertEqual(first_document["file_name"], "release.pdf")
        self.assertEqual(second_document["file_name"], "employer-letter.jpg")

        stored_first = self.store.get_document(first_document["document_id"])
        stored_second = self.store.get_document(second_document["document_id"])
        self.assertIsNotNone(stored_first)
        self.assertIsNotNone(stored_second)
        self.assertTrue((fmla_routes.FMLA_UPLOADS_DIR / stored_first["file_path"]).exists())
        self.assertTrue((fmla_routes.FMLA_UPLOADS_DIR / stored_second["file_path"]).exists())

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

    def test_filters_and_summary(self):
        first = self._create_case()
        self.store.update_case(first["case_id"], {"status": "Approved", "approval_status": "approved"})
        second = self.store.create_case(
            {
                "client_id": "client_2",
                "client_name": "Jordan Smith",
                "assigned_case_manager": "cm_001",
                "employer_name": "Northwind Health",
                "fmla_request_type": "extension",
                "paperwork_deadline": "2000-01-01",
                "status": "Denied",
                "approval_status": "denied",
            }
        )
        denied_cases = self.store.list_cases({"status": "Denied"})
        self.assertEqual(len(denied_cases), 1)
        self.assertEqual(denied_cases[0]["case_id"], second["case_id"])

        summary = self.store.get_summary("cm_001")
        self.assertEqual(summary["approved_cases"], 1)
        self.assertEqual(summary["denied_cases"], 1)
        self.assertGreaterEqual(summary["missing_paperwork"], 2)


if __name__ == "__main__":
    unittest.main()
