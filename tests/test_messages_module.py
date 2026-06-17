import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth.service import ADMIN_ROLE, CASE_MANAGER_ROLE
from backend.modules.messages.database import MessagesDatabase
from backend.modules.messages.routes import get_messages_db, router
from tests.auth_helpers import make_test_user


class MessagesModuleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.temp_path = Path(self.temp_dir.name)
        self.messages_db = MessagesDatabase(self.temp_path / "messages_test.db")
        self.core_clients_db = self.temp_path / "core_clients.db"
        self._create_client_db()

        self.db_dir_patch = patch("backend.modules.messages.routes.DB_DIR", self.temp_path)
        self.client_db_patch = patch("backend.auth.authorization.CORE_CLIENTS_DB", self.core_clients_db)
        self.db_dir_patch.start()
        self.client_db_patch.start()

        app = FastAPI()

        @app.middleware("http")
        async def inject_auth_user(request, call_next):
            request.state.auth_user = make_test_user(
                firebase_uid=request.headers.get("X-Test-Auth-User", "uid-cm-001"),
                email=request.headers.get("X-Test-Auth-Email", "case.manager@example.com"),
                full_name=request.headers.get("X-Test-Auth-Name", "Case Manager"),
                role=request.headers.get("X-Test-Auth-Role", ADMIN_ROLE),
                case_manager_id=request.headers.get("X-Test-Auth-Case-Manager-Id", "cm_001"),
            )
            return await call_next(request)

        app.include_router(router, prefix="/api/messages")
        app.dependency_overrides[get_messages_db] = lambda: self.messages_db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.client_db_patch.stop()
        self.db_dir_patch.stop()
        import gc
        gc.collect()
        self.temp_dir.cleanup()

    def _create_client_db(self):
        with sqlite3.connect(self.core_clients_db) as conn:
            conn.execute(
                """
                CREATE TABLE clients (
                    client_id TEXT PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    case_manager_id TEXT
                )
                """
            )
            conn.execute(
                "INSERT INTO clients (client_id, first_name, last_name, case_manager_id) VALUES (?, ?, ?, ?)",
                ("client-john", "John", "Collins", "cm_001"),
            )
            conn.commit()

    def test_create_thread_send_message_and_reload(self):
        create_response = self.client.post(
            "/api/messages/threads",
            json={
                "thread_type": "direct_message",
                "title": "Check in",
                "participants": [{"user_id": "cm_002", "display_name": "Second Worker"}],
                "initial_message": "Can you review this?",
            },
        )
        self.assertEqual(create_response.status_code, 200)
        thread_id = create_response.json()["thread"]["id"]

        send_response = self.client.post(
            f"/api/messages/threads/{thread_id}/messages",
            json={"body": "Adding the follow-up note."},
        )
        self.assertEqual(send_response.status_code, 200)

        reload_response = self.client.get(f"/api/messages/threads/{thread_id}/messages")
        self.assertEqual(reload_response.status_code, 200)
        messages = reload_response.json()["messages"]
        self.assertEqual([message["body"] for message in messages], ["Can you review this?", "Adding the follow-up note."])

    def test_create_client_linked_thread(self):
        response = self.client.post(
            "/api/messages/threads",
            json={
                "thread_type": "client_thread",
                "client_id": "client-john",
                "purpose": "Housing plan",
                "participants": [{"user_id": "cm_002"}],
            },
        )
        self.assertEqual(response.status_code, 200)
        thread = response.json()["thread"]
        self.assertEqual(thread["client_id"], "client-john")
        self.assertEqual(thread["client_name"], "John Collins")
        self.assertEqual(thread["title"], "John Collins - Housing plan")

    def test_unread_count_endpoint_returns_valid_response(self):
        response = self.client.get("/api/messages/unread-count")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIsInstance(payload["unread_count"], int)

    def test_participant_scoping_does_not_return_unrelated_private_threads(self):
        create_response = self.client.post(
            "/api/messages/threads",
            json={
                "thread_type": "direct_message",
                "title": "Private thread",
                "participants": [{"user_id": "cm_002"}],
                "initial_message": "Only for participant two.",
            },
        )
        self.assertEqual(create_response.status_code, 200)

        other_user_headers = {
            "X-Test-Auth-Role": CASE_MANAGER_ROLE,
            "X-Test-Auth-Case-Manager-Id": "cm_003",
            "X-Test-Auth-User": "uid-cm-003",
            "X-Test-Auth-Name": "Third Worker",
        }
        list_response = self.client.get("/api/messages/threads", headers=other_user_headers)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["threads"], [])

    def test_case_manager_cannot_create_announcement(self):
        response = self.client.post(
            "/api/messages/threads",
            headers={"X-Test-Auth-Role": CASE_MANAGER_ROLE},
            json={"thread_type": "announcement", "title": "Team update"},
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
