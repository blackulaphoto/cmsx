from __future__ import annotations

import sqlite3
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from backend.shared.db_path import DB_DIR
from backend.shared.tenancy import DEFAULT_ORG_ID


logger = logging.getLogger(__name__)
THREAD_TYPES = {"direct_message", "team_channel", "client_thread", "announcement"}


def utc_now() -> str:
    return datetime.utcnow().isoformat()


class MessagesDatabase:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or DB_DIR / "messages.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Messages DB path: %s", self.db_path)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS message_threads (
                    id TEXT PRIMARY KEY,
                    thread_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    client_id TEXT,
                    client_name TEXT,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    archived_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS thread_participants (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    display_name TEXT,
                    role TEXT NOT NULL DEFAULT 'participant',
                    last_read_at TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(thread_id, user_id),
                    FOREIGN KEY(thread_id) REFERENCES message_threads(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    sender_name TEXT,
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    edited_at TEXT,
                    deleted_at TEXT,
                    FOREIGN KEY(thread_id) REFERENCES message_threads(id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_message_threads_type ON message_threads(thread_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_message_threads_client ON message_threads(client_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_thread_participants_user ON thread_participants(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_thread_created ON messages(thread_id, created_at)")

            # Phase 3A multi-tenancy: add org_id to message_threads only (the
            # access root). thread_participants and messages inherit org via
            # thread_id and are intentionally NOT altered. Idempotent + additive;
            # backfill keeps single-agency behavior while MULTI_TENANT_ENABLED is
            # false (every thread resolves to the default org).
            thread_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(message_threads)").fetchall()
            }
            if "org_id" not in thread_columns:
                conn.execute("ALTER TABLE message_threads ADD COLUMN org_id TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_message_threads_org ON message_threads(org_id)")
            conn.execute(
                "UPDATE message_threads SET org_id = ? WHERE org_id IS NULL OR TRIM(org_id) = ''",
                (DEFAULT_ORG_ID,),
            )
            conn.commit()

    def create_thread(
        self,
        *,
        thread_type: str,
        title: str,
        created_by: str,
        participants: Iterable[Dict[str, str]],
        client_id: Optional[str] = None,
        client_name: Optional[str] = None,
        initial_message: Optional[Dict[str, str]] = None,
        org_id: str = DEFAULT_ORG_ID,
    ) -> Dict[str, Any]:
        if thread_type not in THREAD_TYPES:
            raise ValueError("Unsupported thread type")
        now = utc_now()
        thread_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO message_threads (
                    id, thread_type, title, client_id, client_name, created_by,
                    created_at, updated_at, org_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (thread_id, thread_type, title, client_id, client_name, created_by, now, now, org_id),
            )
            for participant in participants:
                user_id = (participant.get("user_id") or "").strip()
                if not user_id:
                    continue
                conn.execute(
                    """
                    INSERT OR IGNORE INTO thread_participants (
                        id, thread_id, user_id, display_name, role, last_read_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        thread_id,
                        user_id,
                        participant.get("display_name") or user_id,
                        participant.get("role") or "participant",
                        now if user_id == created_by else None,
                        now,
                    ),
                )
            if initial_message and initial_message.get("body"):
                self._insert_message(
                    conn,
                    thread_id=thread_id,
                    sender_id=created_by,
                    sender_name=initial_message.get("sender_name") or created_by,
                    body=initial_message["body"],
                    created_at=now,
                )
            conn.commit()
        return self.get_thread_for_user(thread_id, created_by, include_announcements=True, org_id=org_id) or {}

    def list_threads(
        self,
        user_id: str,
        *,
        include_announcements: bool = True,
        org_id: str = DEFAULT_ORG_ID,
    ) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT t.*
                FROM message_threads t
                LEFT JOIN thread_participants p ON p.thread_id = t.id
                WHERE t.archived_at IS NULL
                  AND t.org_id = ?
                  AND (p.user_id = ? OR (? = 1 AND t.thread_type = 'announcement'))
                ORDER BY t.updated_at DESC
                """,
                (org_id, user_id, 1 if include_announcements else 0),
            ).fetchall()
            return [self._hydrate_thread(conn, row, user_id) for row in rows]

    def get_thread_for_user(
        self,
        thread_id: str,
        user_id: str,
        *,
        include_announcements: bool = True,
        org_id: str = DEFAULT_ORG_ID,
    ) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT t.*
                FROM message_threads t
                LEFT JOIN thread_participants p ON p.thread_id = t.id AND p.user_id = ?
                WHERE t.id = ?
                  AND t.archived_at IS NULL
                  AND t.org_id = ?
                  AND (p.user_id IS NOT NULL OR (? = 1 AND t.thread_type = 'announcement'))
                """,
                (user_id, thread_id, org_id, 1 if include_announcements else 0),
            ).fetchone()
            return self._hydrate_thread(conn, row, user_id) if row else None

    def list_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM messages
                WHERE thread_id = ? AND deleted_at IS NULL
                ORDER BY created_at ASC
                """,
                (thread_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def add_message(self, thread_id: str, sender_id: str, sender_name: str, body: str) -> Dict[str, Any]:
        now = utc_now()
        with self.connect() as conn:
            message = self._insert_message(
                conn,
                thread_id=thread_id,
                sender_id=sender_id,
                sender_name=sender_name,
                body=body,
                created_at=now,
            )
            conn.execute(
                "UPDATE message_threads SET updated_at = ? WHERE id = ?",
                (now, thread_id),
            )
            conn.execute(
                """
                UPDATE thread_participants
                SET last_read_at = ?
                WHERE thread_id = ? AND user_id = ?
                """,
                (now, thread_id, sender_id),
            )
            conn.commit()
            return message

    def mark_read(self, thread_id: str, user_id: str, display_name: str) -> Dict[str, Any]:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO thread_participants (
                    id, thread_id, user_id, display_name, role, last_read_at, created_at
                ) VALUES (?, ?, ?, ?, 'participant', ?, ?)
                ON CONFLICT(thread_id, user_id) DO UPDATE SET last_read_at = excluded.last_read_at
                """,
                (str(uuid.uuid4()), thread_id, user_id, display_name, now, now),
            )
            conn.commit()
        return {"thread_id": thread_id, "last_read_at": now}

    def unread_count(self, user_id: str, *, include_announcements: bool = True, org_id: str = DEFAULT_ORG_ID) -> int:
        return sum(
            thread.get("unread_count", 0)
            for thread in self.list_threads(user_id, include_announcements=include_announcements, org_id=org_id)
        )

    def _insert_message(
        self,
        conn: sqlite3.Connection,
        *,
        thread_id: str,
        sender_id: str,
        sender_name: str,
        body: str,
        created_at: str,
    ) -> Dict[str, Any]:
        message = {
            "id": str(uuid.uuid4()),
            "thread_id": thread_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "body": body,
            "created_at": created_at,
            "edited_at": None,
            "deleted_at": None,
        }
        conn.execute(
            """
            INSERT INTO messages (
                id, thread_id, sender_id, sender_name, body, created_at, edited_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message["id"],
                thread_id,
                sender_id,
                sender_name,
                body,
                created_at,
                None,
                None,
            ),
        )
        return message

    def _hydrate_thread(self, conn: sqlite3.Connection, row: sqlite3.Row, user_id: str) -> Dict[str, Any]:
        thread = dict(row)
        participants = conn.execute(
            """
            SELECT user_id, display_name, role, last_read_at, created_at
            FROM thread_participants
            WHERE thread_id = ?
            ORDER BY created_at ASC
            """,
            (thread["id"],),
        ).fetchall()
        own_participant = next((p for p in participants if p["user_id"] == user_id), None)
        last_read_at = own_participant["last_read_at"] if own_participant else None
        if last_read_at:
            unread_row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM messages
                WHERE thread_id = ? AND sender_id != ? AND created_at > ? AND deleted_at IS NULL
                """,
                (thread["id"], user_id, last_read_at),
            ).fetchone()
        else:
            unread_row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM messages
                WHERE thread_id = ? AND sender_id != ? AND deleted_at IS NULL
                """,
                (thread["id"], user_id),
            ).fetchone()
        last_message = conn.execute(
            """
            SELECT body, sender_name, created_at
            FROM messages
            WHERE thread_id = ? AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (thread["id"],),
        ).fetchone()
        thread["participants"] = [dict(participant) for participant in participants]
        thread["unread_count"] = int(unread_row["count"] if unread_row else 0)
        thread["last_message"] = dict(last_message) if last_message else None
        return thread


_messages_db: Optional[MessagesDatabase] = None


def get_messages_db() -> MessagesDatabase:
    global _messages_db
    if _messages_db is None:
        _messages_db = MessagesDatabase()
    return _messages_db
