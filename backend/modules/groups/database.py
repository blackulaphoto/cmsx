import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parents[3] / "databases" / "groups.db"


class GroupsDatabase:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # WAL improves concurrent read performance in production.
        # On Windows test environments the WAL file is held open;
        # the try/except lets tests pass without it.
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
        return conn

    def _init_tables(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS group_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'General',
                    description TEXT DEFAULT '',
                    key_points_json TEXT DEFAULT '[]',
                    discussion_questions_json TEXT DEFAULT '[]',
                    activity TEXT DEFAULT '',
                    writing_prompt TEXT DEFAULT '',
                    facilitator_tips TEXT DEFAULT '',
                    source TEXT NOT NULL DEFAULT 'custom',
                    created_by TEXT NOT NULL DEFAULT 'system',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS group_video_playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    youtube_playlist_url TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    category TEXT NOT NULL DEFAULT 'General',
                    tags_json TEXT DEFAULT '[]',
                    added_by TEXT NOT NULL DEFAULT 'system',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS group_videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT UNIQUE NOT NULL,
                    playlist_id TEXT,
                    title TEXT NOT NULL,
                    youtube_url TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    category TEXT NOT NULL DEFAULT 'General',
                    tags_json TEXT DEFAULT '[]',
                    added_by TEXT NOT NULL DEFAULT 'system',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS group_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    topic_id TEXT,
                    scheduled_date TEXT,
                    scheduled_time TEXT,
                    location TEXT DEFAULT '',
                    group_type TEXT NOT NULL DEFAULT 'psychoeducation',
                    status TEXT NOT NULL DEFAULT 'planned',
                    playlist_ids_json TEXT DEFAULT '[]',
                    video_ids_json TEXT DEFAULT '[]',
                    facilitator_notes TEXT DEFAULT '',
                    case_manager_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS group_attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attendance_id TEXT UNIQUE NOT NULL,
                    session_id TEXT NOT NULL,
                    client_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'present',
                    participation_level TEXT NOT NULL DEFAULT 'moderate',
                    added_by TEXT NOT NULL DEFAULT 'system',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(session_id, client_id)
                );

                CREATE TABLE IF NOT EXISTS group_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id TEXT UNIQUE NOT NULL,
                    session_id TEXT NOT NULL,
                    client_id TEXT,
                    note_type TEXT NOT NULL DEFAULT 'group',
                    content TEXT NOT NULL DEFAULT '',
                    ai_generated INTEGER NOT NULL DEFAULT 0,
                    quote_generated INTEGER NOT NULL DEFAULT 0,
                    reviewed INTEGER NOT NULL DEFAULT 0,
                    finalized INTEGER NOT NULL DEFAULT 0,
                    engagement_preset TEXT DEFAULT '',
                    note_setting TEXT NOT NULL DEFAULT 'in-person',
                    staff_quote TEXT DEFAULT '',
                    created_by TEXT NOT NULL DEFAULT 'system',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS group_schedules (
                    schedule_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    group_type TEXT NOT NULL DEFAULT 'psychoeducation',
                    topic_id TEXT,
                    curriculum_pack_id TEXT,
                    day_of_week INTEGER NOT NULL DEFAULT 0,
                    start_time TEXT NOT NULL DEFAULT '10:00',
                    duration_minutes INTEGER NOT NULL DEFAULT 60,
                    location TEXT NOT NULL DEFAULT '',
                    facilitator TEXT NOT NULL DEFAULT '',
                    recurrence TEXT NOT NULL DEFAULT 'weekly',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_by TEXT NOT NULL DEFAULT 'system',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS group_curriculum_packs (
                    pack_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    target_population TEXT NOT NULL DEFAULT '',
                    level_of_care TEXT NOT NULL DEFAULT '',
                    topic_ids_json TEXT NOT NULL DEFAULT '[]',
                    total_sessions INTEGER NOT NULL DEFAULT 0,
                    created_by TEXT NOT NULL DEFAULT 'system',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS group_schedule_instances (
                    instance_id TEXT PRIMARY KEY,
                    schedule_id TEXT NOT NULL,
                    session_id TEXT,
                    scheduled_date TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'planned',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
        # Safe migration for existing DBs that predate new columns
        self._migrate_notes_table()

    def _migrate_notes_table(self) -> None:
        new_cols = [
            ("quote_generated", "INTEGER NOT NULL DEFAULT 0"),
            ("reviewed", "INTEGER NOT NULL DEFAULT 0"),
            ("finalized", "INTEGER NOT NULL DEFAULT 0"),
            ("engagement_preset", "TEXT DEFAULT ''"),
            ("note_setting", "TEXT NOT NULL DEFAULT 'in-person'"),
            ("staff_quote", "TEXT DEFAULT ''"),
        ]
        with self._connect() as conn:
            existing = {row[1] for row in conn.execute("PRAGMA table_info(group_notes)").fetchall()}
            for col_name, col_def in new_cols:
                if col_name not in existing:
                    try:
                        conn.execute(f"ALTER TABLE group_notes ADD COLUMN {col_name} {col_def}")
                    except Exception:
                        pass
            conn.commit()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        for key in ("key_points_json", "discussion_questions_json", "tags_json",
                    "playlist_ids_json", "video_ids_json"):
            if key in d and d[key]:
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    d[key] = []
        return d

    # ── Topics ───────────────────────────────────────────────────────────────

    def is_seeded(self) -> bool:
        with self._connect() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM group_topics WHERE source = 'seeded'"
            ).fetchone()[0]
            return count > 0

    def create_topic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        topic_id = data.get("topic_id") or f"topic_{uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO group_topics
                   (topic_id, title, category, description,
                    key_points_json, discussion_questions_json,
                    activity, writing_prompt, facilitator_tips,
                    source, created_by, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    topic_id,
                    data["title"],
                    data.get("category", "General"),
                    data.get("description", ""),
                    json.dumps(data.get("key_points", [])),
                    json.dumps(data.get("discussion_questions", [])),
                    data.get("activity", ""),
                    data.get("writing_prompt", ""),
                    data.get("facilitator_tips", ""),
                    data.get("source", "custom"),
                    data.get("created_by", "system"),
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_topic(topic_id)

    def get_topic(self, topic_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM group_topics WHERE topic_id = ?", (topic_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_topics(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM group_topics WHERE 1=1"
        params: List[Any] = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if source:
            query += " AND source = ?"
            params.append(source)
        if search:
            query += " AND (title LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY source ASC, title ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def update_topic(self, topic_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        fields = []
        params: List[Any] = []
        mapping = {
            "title": "title",
            "category": "category",
            "description": "description",
            "activity": "activity",
            "writing_prompt": "writing_prompt",
            "facilitator_tips": "facilitator_tips",
        }
        for model_key, col in mapping.items():
            if model_key in data and data[model_key] is not None:
                fields.append(f"{col} = ?")
                params.append(data[model_key])
        if "key_points" in data and data["key_points"] is not None:
            fields.append("key_points_json = ?")
            params.append(json.dumps(data["key_points"]))
        if "discussion_questions" in data and data["discussion_questions"] is not None:
            fields.append("discussion_questions_json = ?")
            params.append(json.dumps(data["discussion_questions"]))
        if not fields:
            return self.get_topic(topic_id)
        fields.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(topic_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE group_topics SET {', '.join(fields)} WHERE topic_id = ?",
                params,
            )
            conn.commit()
        return self.get_topic(topic_id)

    def list_categories(self) -> List[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT category FROM group_topics ORDER BY category ASC"
            ).fetchall()
        return [r[0] for r in rows]

    # ── Playlists ─────────────────────────────────────────────────────────────

    def create_playlist(self, data: Dict[str, Any]) -> Dict[str, Any]:
        playlist_id = f"pl_{uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO group_video_playlists
                   (playlist_id, title, youtube_playlist_url, description,
                    category, tags_json, added_by, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    playlist_id,
                    data["title"],
                    data["youtube_playlist_url"],
                    data.get("description", ""),
                    data.get("category", "General"),
                    json.dumps(data.get("tags", [])),
                    data.get("added_by", "system"),
                    now,
                ),
            )
            conn.commit()
        return self.get_playlist(playlist_id)

    def get_playlist(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM group_video_playlists WHERE playlist_id = ?", (playlist_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_playlists(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM group_video_playlists WHERE 1=1"
        params: List[Any] = []
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def update_playlist(self, playlist_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        fields = []
        params: List[Any] = []
        for col in ("title", "description", "category"):
            if col in data and data[col] is not None:
                fields.append(f"{col} = ?")
                params.append(data[col])
        if "tags" in data and data["tags"] is not None:
            fields.append("tags_json = ?")
            params.append(json.dumps(data["tags"]))
        if not fields:
            return self.get_playlist(playlist_id)
        params.append(playlist_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE group_video_playlists SET {', '.join(fields)} WHERE playlist_id = ?",
                params,
            )
            conn.commit()
        return self.get_playlist(playlist_id)

    # ── Videos ───────────────────────────────────────────────────────────────

    def create_video(self, data: Dict[str, Any]) -> Dict[str, Any]:
        video_id = f"vid_{uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO group_videos
                   (video_id, playlist_id, title, youtube_url, description,
                    category, tags_json, added_by, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    video_id,
                    data.get("playlist_id"),
                    data["title"],
                    data["youtube_url"],
                    data.get("description", ""),
                    data.get("category", "General"),
                    json.dumps(data.get("tags", [])),
                    data.get("added_by", "system"),
                    now,
                ),
            )
            conn.commit()
        return self.get_video(video_id)

    def get_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM group_videos WHERE video_id = ?", (video_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_videos(
        self, playlist_id: Optional[str] = None, category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM group_videos WHERE 1=1"
        params: List[Any] = []
        if playlist_id:
            query += " AND playlist_id = ?"
            params.append(playlist_id)
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def update_video(self, video_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        fields = []
        params: List[Any] = []
        for col in ("title", "description", "category"):
            if col in data and data[col] is not None:
                fields.append(f"{col} = ?")
                params.append(data[col])
        if "tags" in data and data["tags"] is not None:
            fields.append("tags_json = ?")
            params.append(json.dumps(data["tags"]))
        if not fields:
            return self.get_video(video_id)
        params.append(video_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE group_videos SET {', '.join(fields)} WHERE video_id = ?",
                params,
            )
            conn.commit()
        return self.get_video(video_id)

    # ── Sessions ─────────────────────────────────────────────────────────────

    def create_session(self, data: Dict[str, Any]) -> Dict[str, Any]:
        session_id = f"sess_{uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO group_sessions
                   (session_id, title, topic_id, scheduled_date, scheduled_time,
                    location, group_type, status, playlist_ids_json, video_ids_json,
                    facilitator_notes, case_manager_id, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    session_id,
                    data["title"],
                    data.get("topic_id"),
                    data.get("scheduled_date"),
                    data.get("scheduled_time"),
                    data.get("location", ""),
                    data.get("group_type", "psychoeducation"),
                    data.get("status", "planned"),
                    json.dumps(data.get("playlist_ids", [])),
                    json.dumps(data.get("video_ids", [])),
                    data.get("facilitator_notes", ""),
                    data["case_manager_id"],
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM group_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        if not row:
            return None
        session = self._row_to_dict(row)
        # Enrich with topic if linked
        if session.get("topic_id"):
            session["topic"] = self.get_topic(session["topic_id"])
        else:
            session["topic"] = None
        # Enrich with linked playlists and videos
        pl_ids = session.get("playlist_ids_json") or []
        session["playlists"] = [self.get_playlist(pid) for pid in pl_ids if pid]
        vid_ids = session.get("video_ids_json") or []
        session["videos"] = [self.get_video(vid) for vid in vid_ids if vid]
        return session

    def list_sessions(
        self,
        case_manager_id: Optional[str] = None,
        status: Optional[str] = None,
        topic_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM group_sessions WHERE 1=1"
        params: List[Any] = []
        if case_manager_id:
            query += " AND case_manager_id = ?"
            params.append(case_manager_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        if topic_id:
            query += " AND topic_id = ?"
            params.append(topic_id)
        query += " ORDER BY scheduled_date DESC, created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def update_session(self, session_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        fields = []
        params: List[Any] = []
        scalar_cols = (
            "title", "topic_id", "scheduled_date", "scheduled_time",
            "location", "group_type", "status", "facilitator_notes",
        )
        for col in scalar_cols:
            if col in data and data[col] is not None:
                fields.append(f"{col} = ?")
                params.append(data[col])
        if "playlist_ids" in data and data["playlist_ids"] is not None:
            fields.append("playlist_ids_json = ?")
            params.append(json.dumps(data["playlist_ids"]))
        if "video_ids" in data and data["video_ids"] is not None:
            fields.append("video_ids_json = ?")
            params.append(json.dumps(data["video_ids"]))
        if not fields:
            return self.get_session(session_id)
        fields.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(session_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE group_sessions SET {', '.join(fields)} WHERE session_id = ?",
                params,
            )
            conn.commit()
        return self.get_session(session_id)

    # ── Attendance ────────────────────────────────────────────────────────────

    def upsert_attendance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        session_id = data["session_id"]
        client_id = data["client_id"]
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT attendance_id FROM group_attendance WHERE session_id=? AND client_id=?",
                (session_id, client_id),
            ).fetchone()
            if existing:
                attendance_id = existing["attendance_id"]
                conn.execute(
                    """UPDATE group_attendance
                       SET status=?, participation_level=?, updated_at=?
                       WHERE attendance_id=?""",
                    (
                        data.get("status", "present"),
                        data.get("participation_level", "moderate"),
                        now,
                        attendance_id,
                    ),
                )
            else:
                attendance_id = f"att_{uuid4().hex[:12]}"
                conn.execute(
                    """INSERT INTO group_attendance
                       (attendance_id, session_id, client_id, status, participation_level, added_by, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        attendance_id,
                        session_id,
                        client_id,
                        data.get("status", "present"),
                        data.get("participation_level", "moderate"),
                        data.get("added_by", "system"),
                        now,
                        now,
                    ),
                )
            conn.commit()
        return self.get_attendance_record(attendance_id)

    def get_attendance_record(self, attendance_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM group_attendance WHERE attendance_id=?", (attendance_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_attendance(self, session_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM group_attendance WHERE session_id=? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_attendance(self, session_id: str, client_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM group_attendance WHERE session_id=? AND client_id=?",
                (session_id, client_id),
            )
            conn.commit()
        return cur.rowcount > 0

    # ── Group Notes ───────────────────────────────────────────────────────────

    def create_note(self, data: Dict[str, Any]) -> Dict[str, Any]:
        note_id = f"note_{uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO group_notes
                   (note_id, session_id, client_id, note_type, content,
                    ai_generated, quote_generated, reviewed, finalized,
                    engagement_preset, note_setting, staff_quote,
                    created_by, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    note_id,
                    data["session_id"],
                    data.get("client_id"),
                    data.get("note_type", "group"),
                    data.get("content", ""),
                    1 if data.get("ai_generated") else 0,
                    1 if data.get("quote_generated") else 0,
                    1 if data.get("reviewed") else 0,
                    1 if data.get("finalized") else 0,
                    data.get("engagement_preset", ""),
                    data.get("note_setting", "in-person"),
                    data.get("staff_quote", ""),
                    data.get("created_by", "system"),
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_note(note_id)

    def get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM group_notes WHERE note_id=?", (note_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_notes(self, session_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM group_notes WHERE session_id=? ORDER BY note_type ASC, created_at ASC",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def update_note(self, note_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        fields = []
        params: List[Any] = []
        for col in ("content", "note_type", "engagement_preset", "note_setting", "staff_quote"):
            if col in data and data[col] is not None:
                fields.append(f"{col} = ?")
                params.append(data[col])
        for bool_col in ("reviewed", "finalized", "ai_generated", "quote_generated"):
            if bool_col in data and data[bool_col] is not None:
                fields.append(f"{bool_col} = ?")
                params.append(1 if data[bool_col] else 0)
        if not fields:
            return self.get_note(note_id)
        fields.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(note_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE group_notes SET {', '.join(fields)} WHERE note_id=?", params
            )
            conn.commit()
        return self.get_note(note_id)

    def get_note_by_session_client(self, session_id: str, client_id: Optional[str], note_type: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            if client_id:
                row = conn.execute(
                    "SELECT * FROM group_notes WHERE session_id=? AND client_id=? AND note_type=? ORDER BY created_at DESC LIMIT 1",
                    (session_id, client_id, note_type),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM group_notes WHERE session_id=? AND client_id IS NULL AND note_type=? ORDER BY created_at DESC LIMIT 1",
                    (session_id, note_type),
                ).fetchone()
        return dict(row) if row else None

    # ── Schedules ──────────────────────────────────────────────────────────────

    def list_schedules(self) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM group_schedules ORDER BY day_of_week, start_time").fetchall()
            return [dict(r) for r in rows]

    def create_schedule(self, data: dict) -> dict:
        schedule_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO group_schedules
                (schedule_id, title, group_type, topic_id, curriculum_pack_id,
                 day_of_week, start_time, duration_minutes, location, facilitator,
                 recurrence, is_active, created_by, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (schedule_id, data["title"], data.get("group_type", "psychoeducation"),
                  data.get("topic_id"), data.get("curriculum_pack_id"),
                  data.get("day_of_week", 0), data.get("start_time", "10:00"),
                  data.get("duration_minutes", 60), data.get("location", ""),
                  data.get("facilitator", ""), data.get("recurrence", "weekly"),
                  1 if data.get("is_active", True) else 0,
                  data.get("created_by", "system"), now, now))
            conn.commit()
        return self.get_schedule(schedule_id)

    def get_schedule(self, schedule_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM group_schedules WHERE schedule_id=?", (schedule_id,)).fetchone()
            return dict(row) if row else None

    def update_schedule(self, schedule_id: str, data: dict) -> Optional[dict]:
        now = datetime.utcnow().isoformat()
        allowed = {"title", "group_type", "topic_id", "curriculum_pack_id", "day_of_week",
                   "start_time", "duration_minutes", "location", "facilitator", "recurrence", "is_active"}
        sets, vals = [], []
        for k, v in data.items():
            if k in allowed:
                sets.append(f"{k}=?")
                vals.append(1 if (k == "is_active" and isinstance(v, bool) and v) else
                            0 if (k == "is_active" and isinstance(v, bool) and not v) else v)
        if not sets:
            return self.get_schedule(schedule_id)
        sets.append("updated_at=?")
        vals.append(now)
        vals.append(schedule_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE group_schedules SET {', '.join(sets)} WHERE schedule_id=?", vals)
            conn.commit()
        return self.get_schedule(schedule_id)

    def list_instances(self, schedule_id: str) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM group_schedule_instances WHERE schedule_id=? ORDER BY scheduled_date",
                (schedule_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def create_instance(self, data: dict) -> dict:
        instance_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO group_schedule_instances (instance_id, schedule_id, session_id, scheduled_date, status, created_at)
                VALUES (?,?,?,?,?,?)
            """, (instance_id, data["schedule_id"], data.get("session_id"),
                  data["scheduled_date"], data.get("status", "planned"), now))
            conn.commit()
            row = conn.execute("SELECT * FROM group_schedule_instances WHERE instance_id=?", (instance_id,)).fetchone()
            return dict(row)

    def update_instance(self, instance_id: str, data: dict) -> Optional[dict]:
        allowed = {"session_id", "status"}
        sets, vals = [], []
        for k, v in data.items():
            if k in allowed:
                sets.append(f"{k}=?")
                vals.append(v)
        if not sets:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM group_schedule_instances WHERE instance_id=?", (instance_id,)).fetchone()
                return dict(row) if row else None
        vals.append(instance_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE group_schedule_instances SET {', '.join(sets)} WHERE instance_id=?", vals)
            conn.commit()
            row = conn.execute("SELECT * FROM group_schedule_instances WHERE instance_id=?", (instance_id,)).fetchone()
            return dict(row) if row else None

    # ── Curriculum Packs ───────────────────────────────────────────────────────

    def list_packs(self) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM group_curriculum_packs ORDER BY name").fetchall()
            result = []
            for r in rows:
                d = dict(r)
                try:
                    d["topic_ids"] = json.loads(d.get("topic_ids_json", "[]"))
                except Exception:
                    d["topic_ids"] = []
                result.append(d)
            return result

    def create_pack(self, data: dict) -> dict:
        pack_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        topic_ids = data.get("topic_ids", [])
        topic_ids_json = json.dumps(topic_ids)
        total = len(topic_ids)
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO group_curriculum_packs
                (pack_id, name, description, target_population, level_of_care,
                 topic_ids_json, total_sessions, created_by, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (pack_id, data["name"], data.get("description", ""),
                  data.get("target_population", ""), data.get("level_of_care", ""),
                  topic_ids_json, total, data.get("created_by", "system"), now, now))
            conn.commit()
        return self.get_pack(pack_id)

    def get_pack(self, pack_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM group_curriculum_packs WHERE pack_id=?", (pack_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["topic_ids"] = json.loads(d.get("topic_ids_json", "[]"))
            except Exception:
                d["topic_ids"] = []
            return d

    def update_pack(self, pack_id: str, data: dict) -> Optional[dict]:
        now = datetime.utcnow().isoformat()
        allowed = {"name", "description", "target_population", "level_of_care", "topic_ids"}
        sets, vals = [], []
        for k, v in data.items():
            if k == "topic_ids":
                sets.append("topic_ids_json=?")
                vals.append(json.dumps(v if isinstance(v, list) else []))
                sets.append("total_sessions=?")
                vals.append(len(v) if isinstance(v, list) else 0)
            elif k in allowed:
                sets.append(f"{k}=?")
                vals.append(v)
        if not sets:
            return self.get_pack(pack_id)
        sets.append("updated_at=?")
        vals.append(now)
        vals.append(pack_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE group_curriculum_packs SET {', '.join(sets)} WHERE pack_id=?", vals)
            conn.commit()
        return self.get_pack(pack_id)

    # ── Reports ────────────────────────────────────────────────────────────────

    def report_attendance(self, start_date: str, end_date: str, facilitator: str = "", topic_id: str = "") -> List[dict]:
        with self._connect() as conn:
            # Join schedule instances so we can filter by facilitator stored on the schedule
            query = """
                SELECT s.session_id, s.title, s.scheduled_date,
                       COALESCE(sch.facilitator, '') as facilitator,
                       COUNT(a.attendance_id) as total_attendees,
                       SUM(CASE WHEN a.status='present' THEN 1 ELSE 0 END) as present_count,
                       SUM(CASE WHEN a.status='absent' THEN 1 ELSE 0 END) as absent_count,
                       SUM(CASE WHEN a.status='late' THEN 1 ELSE 0 END) as late_count,
                       SUM(CASE WHEN a.status='excused' THEN 1 ELSE 0 END) as excused_count
                FROM group_sessions s
                LEFT JOIN group_attendance a ON a.session_id = s.session_id
                LEFT JOIN group_schedule_instances gsi ON gsi.session_id = s.session_id
                LEFT JOIN group_schedules sch ON sch.schedule_id = gsi.schedule_id
                WHERE s.scheduled_date >= ? AND s.scheduled_date <= ?
            """
            params = [start_date, end_date]
            if topic_id:
                query += " AND s.topic_id = ?"
                params.append(topic_id)
            if facilitator:
                query += " AND LOWER(COALESCE(sch.facilitator,'')) LIKE ?"
                params.append(f"%{facilitator.lower()}%")
            query += " GROUP BY s.session_id ORDER BY s.scheduled_date"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def report_topics(self, start_date: str, end_date: str) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT t.topic_id, t.title, t.category,
                       COUNT(s.session_id) as session_count
                FROM group_topics t
                JOIN group_sessions s ON s.topic_id = t.topic_id
                WHERE s.scheduled_date >= ? AND s.scheduled_date <= ?
                GROUP BY t.topic_id
                ORDER BY session_count DESC
            """, (start_date, end_date)).fetchall()
            return [dict(r) for r in rows]

    def report_notes(self, start_date: str, end_date: str) -> dict:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT n.note_id, n.reviewed, n.finalized, n.ai_generated,
                       s.scheduled_date
                FROM group_notes n
                JOIN group_sessions s ON s.session_id = n.session_id
                WHERE s.scheduled_date >= ? AND s.scheduled_date <= ?
            """, (start_date, end_date)).fetchall()
            total = len(rows)
            reviewed = sum(1 for r in rows if r["reviewed"])
            finalized = sum(1 for r in rows if r["finalized"])
            ai_drafted = sum(1 for r in rows if r["ai_generated"])
            return {
                "total": total,
                "drafted": total - reviewed - finalized,
                "reviewed": reviewed,
                "finalized": finalized,
                "ai_drafted": ai_drafted,
            }


# Module-level singleton
groups_db = GroupsDatabase()
