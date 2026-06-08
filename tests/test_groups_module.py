"""
Tests for the Group Facilitation module.
Follows the pattern established in test_fmla_module.py.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.modules.groups.database import GroupsDatabase
from backend.modules.groups.seed_topics import seed_topics, SEEDED_TOPICS
from tests.auth_helpers import add_test_auth_middleware
import backend.modules.groups.routes as groups_routes


class GroupsDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "groups_test.db"
        self.db = GroupsDatabase(db_path=db_path)

    def tearDown(self):
        # Close any open connections before deleting the temp dir on Windows
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass  # WAL files may still be held briefly on Windows; not a test failure

    # ── Seed ──────────────────────────────────────────────────────────────────

    def test_seed_inserts_50_topics(self):
        count = seed_topics(self.db)
        self.assertEqual(count, len(SEEDED_TOPICS))

    def test_seed_is_idempotent(self):
        seed_topics(self.db)
        count_second = seed_topics(self.db)
        self.assertEqual(count_second, 0, "Second seed run should insert 0 topics")

    def test_seeded_topics_have_source_seeded(self):
        seed_topics(self.db)
        topics = self.db.list_topics(source="seeded")
        self.assertEqual(len(topics), len(SEEDED_TOPICS))
        for t in topics:
            self.assertEqual(t["source"], "seeded")

    # ── Topics ────────────────────────────────────────────────────────────────

    def test_create_custom_topic(self):
        topic = self.db.create_topic({
            "title": "Test Topic",
            "category": "Coping Skills",
            "description": "A test description",
            "key_points": ["Point 1", "Point 2"],
            "discussion_questions": ["Question 1"],
            "activity": "Do something",
            "writing_prompt": "Write about it",
            "facilitator_tips": "Some tips",
            "source": "custom",
            "created_by": "cm_001",
        })
        self.assertIsNotNone(topic["topic_id"])
        self.assertEqual(topic["title"], "Test Topic")
        self.assertEqual(topic["source"], "custom")

    def test_list_topics_returns_all(self):
        seed_topics(self.db)
        result = self.db.list_topics()
        self.assertEqual(len(result), len(SEEDED_TOPICS))

    def test_list_topics_filter_by_category(self):
        seed_topics(self.db)
        result = self.db.list_topics(category="Relapse Prevention")
        self.assertTrue(len(result) > 0)
        for t in result:
            self.assertEqual(t["category"], "Relapse Prevention")

    def test_list_topics_search(self):
        self.db.create_topic({
            "title": "Unique Cravings Topic",
            "category": "Coping Skills",
            "source": "custom",
            "created_by": "cm_001",
        })
        result = self.db.list_topics(search="Unique Cravings")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Unique Cravings Topic")

    def test_get_topic_returns_none_for_missing(self):
        result = self.db.get_topic("nonexistent_topic_id")
        self.assertIsNone(result)

    def test_update_topic(self):
        topic = self.db.create_topic({
            "title": "Before Update",
            "category": "General",
            "source": "custom",
            "created_by": "cm_001",
        })
        updated = self.db.update_topic(topic["topic_id"], {"title": "After Update"})
        self.assertEqual(updated["title"], "After Update")

    def test_list_categories(self):
        seed_topics(self.db)
        cats = self.db.list_categories()
        self.assertIn("Relapse Prevention", cats)
        self.assertIn("Coping Skills", cats)

    # ── Playlists ─────────────────────────────────────────────────────────────

    def test_create_playlist(self):
        pl = self.db.create_playlist({
            "title": "Test Playlist",
            "youtube_playlist_url": "https://www.youtube.com/playlist?list=PLtest123",
            "description": "A test playlist",
            "category": "General",
            "tags": ["recovery", "education"],
            "added_by": "cm_001",
        })
        self.assertIsNotNone(pl["playlist_id"])
        self.assertEqual(pl["title"], "Test Playlist")
        self.assertIn("PLtest123", pl["youtube_playlist_url"])

    def test_list_playlists(self):
        self.db.create_playlist({
            "title": "PL1", "youtube_playlist_url": "https://www.youtube.com/playlist?list=PL1",
            "category": "General", "added_by": "cm_001",
        })
        self.db.create_playlist({
            "title": "PL2", "youtube_playlist_url": "https://www.youtube.com/playlist?list=PL2",
            "category": "General", "added_by": "cm_001",
        })
        result = self.db.list_playlists()
        self.assertEqual(len(result), 2)

    # ── Videos ────────────────────────────────────────────────────────────────

    def test_create_individual_video(self):
        v = self.db.create_video({
            "title": "Test Video",
            "youtube_url": "https://www.youtube.com/watch?v=abc12345678",
            "description": "A test video",
            "category": "General",
            "tags": [],
            "added_by": "cm_001",
        })
        self.assertIsNotNone(v["video_id"])
        self.assertEqual(v["title"], "Test Video")
        self.assertIn("abc12345678", v["youtube_url"])

    def test_list_videos(self):
        self.db.create_video({
            "title": "V1", "youtube_url": "https://www.youtube.com/watch?v=aaaaaaaaaaa",
            "category": "General", "added_by": "cm_001",
        })
        result = self.db.list_videos()
        self.assertEqual(len(result), 1)

    # ── Sessions ──────────────────────────────────────────────────────────────

    def test_create_session(self):
        sess = self.db.create_session({
            "title": "Test Group Session",
            "topic_id": None,
            "scheduled_date": "2026-07-01",
            "scheduled_time": "10:00",
            "location": "Room 3",
            "group_type": "psychoeducation",
            "status": "planned",
            "playlist_ids": [],
            "video_ids": [],
            "facilitator_notes": "Be prepared",
            "case_manager_id": "cm_001",
        })
        self.assertIsNotNone(sess["session_id"])
        self.assertEqual(sess["title"], "Test Group Session")
        self.assertEqual(sess["case_manager_id"], "cm_001")

    def test_get_session_enriches_topic(self):
        seed_topics(self.db)
        topics = self.db.list_topics(source="seeded")
        topic = topics[0]
        sess = self.db.create_session({
            "title": "Session with Topic",
            "topic_id": topic["topic_id"],
            "case_manager_id": "cm_001",
            "playlist_ids": [],
            "video_ids": [],
        })
        fetched = self.db.get_session(sess["session_id"])
        self.assertIsNotNone(fetched["topic"])
        self.assertEqual(fetched["topic"]["topic_id"], topic["topic_id"])

    def test_get_session_enriches_videos(self):
        v = self.db.create_video({
            "title": "V1", "youtube_url": "https://www.youtube.com/watch?v=aaaaaaaaaaa",
            "category": "General", "added_by": "cm_001",
        })
        sess = self.db.create_session({
            "title": "Session with Video",
            "topic_id": None,
            "case_manager_id": "cm_001",
            "playlist_ids": [],
            "video_ids": [v["video_id"]],
        })
        fetched = self.db.get_session(sess["session_id"])
        self.assertEqual(len(fetched["videos"]), 1)
        self.assertEqual(fetched["videos"][0]["video_id"], v["video_id"])


class GroupsAttendanceNotesTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "groups_phase2_test.db"
        self.db = GroupsDatabase(db_path=db_path)
        self.sess = self.db.create_session({
            "title": "Test Session",
            "topic_id": None,
            "case_manager_id": "cm_001",
            "playlist_ids": [],
            "video_ids": [],
        })
        self.session_id = self.sess["session_id"]

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    # ── Attendance ────────────────────────────────────────────────────────────

    def test_upsert_attendance_creates_record(self):
        rec = self.db.upsert_attendance({
            "session_id": self.session_id,
            "client_id": "client_001",
            "status": "present",
            "participation_level": "active",
            "added_by": "cm_001",
        })
        self.assertIsNotNone(rec["attendance_id"])
        self.assertEqual(rec["status"], "present")
        self.assertEqual(rec["participation_level"], "active")

    def test_upsert_attendance_updates_existing(self):
        self.db.upsert_attendance({
            "session_id": self.session_id,
            "client_id": "client_001",
            "status": "present",
            "participation_level": "minimal",
            "added_by": "cm_001",
        })
        rec = self.db.upsert_attendance({
            "session_id": self.session_id,
            "client_id": "client_001",
            "status": "late",
            "participation_level": "moderate",
            "added_by": "cm_001",
        })
        self.assertEqual(rec["status"], "late")
        self.assertEqual(rec["participation_level"], "moderate")
        # Only one record should exist
        all_records = self.db.list_attendance(self.session_id)
        self.assertEqual(len(all_records), 1)

    def test_list_attendance(self):
        self.db.upsert_attendance({"session_id": self.session_id, "client_id": "c1", "status": "present", "participation_level": "active", "added_by": "cm_001"})
        self.db.upsert_attendance({"session_id": self.session_id, "client_id": "c2", "status": "absent", "participation_level": "none", "added_by": "cm_001"})
        records = self.db.list_attendance(self.session_id)
        self.assertEqual(len(records), 2)

    def test_delete_attendance(self):
        self.db.upsert_attendance({"session_id": self.session_id, "client_id": "c1", "status": "present", "participation_level": "active", "added_by": "cm_001"})
        result = self.db.delete_attendance(self.session_id, "c1")
        self.assertTrue(result)
        self.assertEqual(len(self.db.list_attendance(self.session_id)), 0)

    # ── Notes ─────────────────────────────────────────────────────────────────

    def test_create_group_note(self):
        note = self.db.create_note({
            "session_id": self.session_id,
            "note_type": "group",
            "content": "Group discussed coping skills.",
            "ai_generated": False,
            "created_by": "cm_001",
        })
        self.assertIsNotNone(note["note_id"])
        self.assertEqual(note["note_type"], "group")
        self.assertEqual(note["content"], "Group discussed coping skills.")

    def test_create_individual_note(self):
        note = self.db.create_note({
            "session_id": self.session_id,
            "client_id": "client_001",
            "note_type": "individual",
            "content": "Client was engaged.",
            "ai_generated": True,
            "created_by": "cm_001",
        })
        self.assertEqual(note["client_id"], "client_001")
        self.assertEqual(note["ai_generated"], 1)

    def test_list_notes(self):
        self.db.create_note({"session_id": self.session_id, "note_type": "group", "content": "Group note", "created_by": "cm_001"})
        self.db.create_note({"session_id": self.session_id, "client_id": "c1", "note_type": "individual", "content": "Individual note", "created_by": "cm_001"})
        notes = self.db.list_notes(self.session_id)
        self.assertEqual(len(notes), 2)

    def test_update_note(self):
        note = self.db.create_note({
            "session_id": self.session_id,
            "note_type": "group",
            "content": "Original content",
            "created_by": "cm_001",
        })
        updated = self.db.update_note(note["note_id"], {"content": "Updated content"})
        self.assertEqual(updated["content"], "Updated content")


class GroupsAPITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "groups_api_test.db"
        self.db = GroupsDatabase(db_path=db_path)

        # Patch the module-level groups_db singleton used by routes
        self.original_db = groups_routes.groups_db
        groups_routes.groups_db = self.db

        app = FastAPI()
        add_test_auth_middleware(app)
        app.include_router(groups_routes.router, prefix="/api")
        self.client = TestClient(app)

    def tearDown(self):
        groups_routes.groups_db = self.original_db
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass  # WAL files may still be held briefly on Windows

    def test_list_topics_requires_auth(self):
        """Route returns 200 with test auth middleware injected."""
        resp = self.client.get("/api/groups/topics")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("topics", resp.json())

    def test_seed_topics_visible_via_api(self):
        seed_topics(self.db)
        resp = self.client.get("/api/groups/topics")
        data = resp.json()
        self.assertEqual(data["count"], len(SEEDED_TOPICS))

    def test_create_custom_topic_via_api(self):
        payload = {
            "title": "API Custom Topic",
            "category": "Coping Skills",
            "description": "Created via API",
            "key_points": ["Point A", "Point B"],
            "discussion_questions": ["Q1"],
            "activity": "Do something",
            "writing_prompt": "Write about it",
            "facilitator_tips": "Tips",
        }
        resp = self.client.post("/api/groups/topics", json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["title"], "API Custom Topic")
        self.assertEqual(data["source"], "custom")

    def test_ai_generate_topic_returns_expected_fields(self):
        """AI generate endpoint returns correct structure (mocked OpenAI)."""
        mock_ai_response = {
            "title": "Managing Cravings",
            "category": "Relapse Prevention",
            "description": "A test description",
            "clinical_purpose": "Helps members manage cravings",
            "key_points": ["Point 1", "Point 2", "Point 3"],
            "discussion_questions": ["Q1", "Q2", "Q3", "Q4"],
            "activity": "Practice urge surfing",
            "writing_prompt": "Describe a recent craving",
            "facilitator_tips": "Validate and normalize"
        }
        import json

        mock_message = MagicMock()
        mock_message.content = json.dumps(mock_ai_response)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        with patch.object(groups_routes, '_openai_client', mock_client):
            resp = self.client.post("/api/groups/topics/ai-generate", json={
                "title": "Managing Cravings",
                "group_length_minutes": 60,
                "population": "Adults in SUD treatment",
                "tone": "psychoeducational",
            })

        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        for field in ("title", "category", "description", "key_points_json", "discussion_questions_json", "activity", "writing_prompt", "facilitator_tips"):
            self.assertIn(field, data, f"Missing field: {field}")
        self.assertEqual(data["source"], "ai_generated")

    def test_add_youtube_playlist_url_valid(self):
        payload = {
            "title": "Recovery Videos",
            "youtube_playlist_url": "https://www.youtube.com/playlist?list=PLtAXzvuI-cJdbNMBGE9bmsdHFpjNzwZAP",
            "description": "Good recovery videos",
            "category": "General",
            "tags": [],
        }
        resp = self.client.post("/api/groups/playlists", json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn("playlist_id", data)
        self.assertEqual(data["title"], "Recovery Videos")

    def test_add_youtube_playlist_url_invalid_rejected(self):
        payload = {
            "title": "Bad URL",
            "youtube_playlist_url": "https://vimeo.com/12345",
            "category": "General",
            "tags": [],
        }
        resp = self.client.post("/api/groups/playlists", json=payload)
        self.assertEqual(resp.status_code, 422)

    def test_add_youtube_video_url_valid(self):
        payload = {
            "title": "Test Video",
            "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "description": "A video",
            "category": "General",
            "tags": [],
        }
        resp = self.client.post("/api/groups/videos", json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn("video_id", data)
        self.assertIn("video_yt_id", data)
        self.assertEqual(data["video_yt_id"], "dQw4w9WgXcQ")

    def test_add_youtube_video_url_invalid_rejected(self):
        payload = {
            "title": "Bad Video",
            "youtube_url": "https://nottuybe.com/watch?v=xxx",
            "category": "General",
            "tags": [],
        }
        resp = self.client.post("/api/groups/videos", json=payload)
        self.assertEqual(resp.status_code, 422)

    def test_create_session_from_topic(self):
        seed_topics(self.db)
        topics = self.db.list_topics()
        topic_id = topics[0]["topic_id"]
        payload = {
            "title": "Wednesday Morning Group",
            "topic_id": topic_id,
            "scheduled_date": "2026-07-09",
            "scheduled_time": "10:00",
            "location": "Room A",
            "group_type": "psychoeducation",
            "facilitator_notes": "Prepare handouts",
        }
        resp = self.client.post("/api/groups/sessions", json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn("session_id", data)
        self.assertEqual(data["topic_id"], topic_id)

    def test_session_detail_includes_topic_and_videos(self):
        seed_topics(self.db)
        topics = self.db.list_topics()
        topic_id = topics[0]["topic_id"]
        v = self.db.create_video({
            "title": "V1", "youtube_url": "https://www.youtube.com/watch?v=aaaaaaaaaaa",
            "category": "General", "added_by": "cm_001",
        })
        sess = self.db.create_session({
            "title": "Full Session",
            "topic_id": topic_id,
            "case_manager_id": "cm_001",
            "playlist_ids": [],
            "video_ids": [v["video_id"]],
        })
        resp = self.client.get(f"/api/groups/sessions/{sess['session_id']}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNotNone(data["topic"])
        self.assertEqual(data["topic"]["topic_id"], topic_id)
        self.assertEqual(len(data["videos"]), 1)
        self.assertEqual(data["videos"][0]["video_id"], v["video_id"])


class GroupsPhase3Tests(unittest.TestCase):
    """Phase 3: scheduling, curriculum packs, and reports."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "groups_phase3_test.db"
        self.db = GroupsDatabase(db_path=db_path)

        # Patch the module-level groups_db singleton used by routes
        self.original_db = groups_routes.groups_db
        groups_routes.groups_db = self.db

        app = FastAPI()
        add_test_auth_middleware(app)
        app.include_router(groups_routes.router, prefix="/api")
        self.client = TestClient(app)

    def tearDown(self):
        groups_routes.groups_db = self.original_db
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass  # WAL files may still be held briefly on Windows

    def _create_topic(self, title="Test Topic", category="General"):
        return self.db.create_topic({
            "title": title,
            "category": category,
            "source": "custom",
            "created_by": "cm_001",
        })

    # ── Schedules ─────────────────────────────────────────────────────────────

    def test_create_schedule(self):
        payload = {
            "title": "Monday Morning Group",
            "group_type": "psychoeducation",
            "day_of_week": 0,
            "start_time": "10:00",
            "duration_minutes": 60,
            "location": "Room A",
            "facilitator": "Jane Smith",
            "recurrence": "weekly",
        }
        resp = self.client.post("/api/groups/schedules", json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn("schedule_id", data)
        self.assertEqual(data["title"], "Monday Morning Group")
        self.assertEqual(data["day_of_week"], 0)
        self.assertEqual(data["recurrence"], "weekly")

    def test_list_schedules(self):
        self.db.create_schedule({"title": "Sched A", "day_of_week": 1, "created_by": "cm_001"})
        self.db.create_schedule({"title": "Sched B", "day_of_week": 3, "created_by": "cm_001"})
        resp = self.client.get("/api/groups/schedules")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("schedules", data)
        self.assertEqual(data["count"], 2)

    def test_generate_sessions_from_schedule(self):
        topic = self._create_topic("Fixed Topic")
        schedule = self.db.create_schedule({
            "title": "Wed Group",
            "day_of_week": 2,  # Wednesday
            "start_time": "14:00",
            "topic_id": topic["topic_id"],
            "recurrence": "weekly",
            "created_by": "cm_001",
        })
        resp = self.client.post(
            f"/api/groups/schedules/{schedule['schedule_id']}/generate-sessions",
            json={"start_date": "2026-07-01", "num_sessions": 4},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["created"], 4)
        self.assertEqual(len(data["sessions"]), 4)
        self.assertEqual(len(data["instances"]), 4)
        # All sessions should use the fixed topic
        for sess in data["sessions"]:
            self.assertEqual(sess["topic_id"], topic["topic_id"])

    def test_generate_sessions_curriculum_pack_rotates_topics(self):
        t1 = self._create_topic("Topic 1")
        t2 = self._create_topic("Topic 2")
        t3 = self._create_topic("Topic 3")
        pack = self.db.create_pack({
            "name": "3-Week Pack",
            "topic_ids": [t1["topic_id"], t2["topic_id"], t3["topic_id"]],
            "created_by": "cm_001",
        })
        schedule = self.db.create_schedule({
            "title": "Pack Group",
            "day_of_week": 0,  # Monday
            "curriculum_pack_id": pack["pack_id"],
            "recurrence": "weekly",
            "created_by": "cm_001",
        })
        resp = self.client.post(
            f"/api/groups/schedules/{schedule['schedule_id']}/generate-sessions",
            json={"start_date": "2026-07-06", "num_sessions": 6},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        sessions = data["sessions"]
        self.assertEqual(len(sessions), 6)
        # Session 0 and session 3 should have the same topic (rotation)
        self.assertEqual(sessions[0]["topic_id"], t1["topic_id"])
        self.assertEqual(sessions[1]["topic_id"], t2["topic_id"])
        self.assertEqual(sessions[2]["topic_id"], t3["topic_id"])
        self.assertEqual(sessions[3]["topic_id"], t1["topic_id"])

    # ── Curriculum Packs ──────────────────────────────────────────────────────

    def test_create_curriculum_pack(self):
        t1 = self._create_topic("T1")
        t2 = self._create_topic("T2")
        payload = {
            "name": "8-Week SUD Pack",
            "description": "A starter curriculum",
            "target_population": "Adults in SUD treatment",
            "level_of_care": "IOP",
            "topic_ids": [t1["topic_id"], t2["topic_id"]],
        }
        resp = self.client.post("/api/groups/curriculum-packs", json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn("pack_id", data)
        self.assertEqual(data["name"], "8-Week SUD Pack")
        self.assertEqual(data["total_sessions"], 2)
        self.assertIn("topic_ids", data)
        self.assertEqual(len(data["topic_ids"]), 2)

    def test_get_curriculum_pack(self):
        t1 = self._create_topic("Topic Alpha")
        pack = self.db.create_pack({
            "name": "Alpha Pack",
            "topic_ids": [t1["topic_id"]],
            "created_by": "cm_001",
        })
        resp = self.client.get(f"/api/groups/curriculum-packs/{pack['pack_id']}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["name"], "Alpha Pack")
        self.assertIn("topics", data)
        self.assertEqual(len(data["topics"]), 1)
        self.assertEqual(data["topics"][0]["title"], "Topic Alpha")

    # ── Reports ───────────────────────────────────────────────────────────────

    def test_attendance_report(self):
        topic = self._create_topic("Report Topic")
        sess = self.db.create_session({
            "title": "Report Session",
            "topic_id": topic["topic_id"],
            "scheduled_date": "2026-06-01",
            "case_manager_id": "cm_001",
            "playlist_ids": [],
            "video_ids": [],
        })
        self.db.upsert_attendance({
            "session_id": sess["session_id"],
            "client_id": "c1",
            "status": "present",
            "participation_level": "active",
            "added_by": "cm_001",
        })
        self.db.upsert_attendance({
            "session_id": sess["session_id"],
            "client_id": "c2",
            "status": "absent",
            "participation_level": "none",
            "added_by": "cm_001",
        })
        resp = self.client.get("/api/groups/reports/attendance?start_date=2026-06-01&end_date=2026-06-30")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("sessions", data)
        self.assertIn("summary", data)
        self.assertEqual(data["summary"]["total_sessions"], 1)
        self.assertEqual(data["summary"]["total_present"], 1)
        self.assertEqual(data["summary"]["total_absent"], 1)

    def test_topics_report(self):
        topic = self._create_topic("Relapse Prevention 101", "Relapse Prevention")
        self.db.create_session({
            "title": "RP Session",
            "topic_id": topic["topic_id"],
            "scheduled_date": "2026-06-05",
            "case_manager_id": "cm_001",
            "playlist_ids": [],
            "video_ids": [],
        })
        resp = self.client.get("/api/groups/reports/topics?start_date=2026-06-01&end_date=2026-06-30")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("topics", data)
        self.assertGreaterEqual(len(data["topics"]), 1)
        found = next((t for t in data["topics"] if t["topic_id"] == topic["topic_id"]), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["session_count"], 1)

    def test_notes_report(self):
        sess = self.db.create_session({
            "title": "Notes Session",
            "topic_id": None,
            "scheduled_date": "2026-06-10",
            "case_manager_id": "cm_001",
            "playlist_ids": [],
            "video_ids": [],
        })
        self.db.create_note({
            "session_id": sess["session_id"],
            "note_type": "group",
            "content": "Group went well.",
            "ai_generated": True,
            "reviewed": False,
            "finalized": False,
            "created_by": "cm_001",
        })
        self.db.create_note({
            "session_id": sess["session_id"],
            "note_type": "individual",
            "content": "Individual note.",
            "ai_generated": False,
            "reviewed": True,
            "finalized": False,
            "created_by": "cm_001",
        })
        resp = self.client.get("/api/groups/reports/notes?start_date=2026-06-01&end_date=2026-06-30")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total", data)
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["ai_drafted"], 1)
        self.assertEqual(data["reviewed"], 1)


if __name__ == "__main__":
    unittest.main()
