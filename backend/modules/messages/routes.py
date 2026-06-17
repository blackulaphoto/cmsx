from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.auth.authorization import assert_client_access
from backend.auth.service import AuthenticatedUser, require_authenticated_user
from backend.modules.messages.database import THREAD_TYPES, MessagesDatabase, get_messages_db
from backend.shared.db_path import DB_DIR

router = APIRouter()


class ParticipantInput(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    role: str = "participant"


class ThreadCreateRequest(BaseModel):
    thread_type: str
    title: Optional[str] = None
    client_id: Optional[str] = None
    purpose: Optional[str] = None
    participants: List[ParticipantInput] = Field(default_factory=list)
    initial_message: Optional[str] = None


class MessageCreateRequest(BaseModel):
    body: str


def _user_id(user: AuthenticatedUser) -> str:
    return user.case_manager_id or user.firebase_uid


def _display_name(user: AuthenticatedUser) -> str:
    return user.full_name or user.email or _user_id(user)


def _participant_from_user(user: AuthenticatedUser, role: str = "participant") -> Dict[str, str]:
    return {"user_id": _user_id(user), "display_name": _display_name(user), "role": role}


def _get_client_summary(client_id: str) -> Optional[Dict[str, str]]:
    db_path = DB_DIR / "core_clients.db"
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT client_id, first_name, last_name, case_manager_id
            FROM clients
            WHERE client_id = ?
            """,
            (client_id,),
        ).fetchone()
    if not row:
        return None
    full_name = f"{row['first_name'] or ''} {row['last_name'] or ''}".strip() or row["client_id"]
    return {
        "client_id": row["client_id"],
        "client_name": full_name,
        "case_manager_id": row["case_manager_id"] or "",
    }


def _normalize_participants(user: AuthenticatedUser, payload: ThreadCreateRequest) -> List[Dict[str, str]]:
    participants: Dict[str, Dict[str, str]] = {}
    creator = _participant_from_user(user, "owner")
    participants[creator["user_id"]] = creator

    for participant in payload.participants:
        participant_id = participant.user_id.strip()
        if not participant_id:
            continue
        participants[participant_id] = {
            "user_id": participant_id,
            "display_name": (participant.display_name or participant_id).strip(),
            "role": participant.role or "participant",
        }

    return list(participants.values())


def _default_title(payload: ThreadCreateRequest, client_name: Optional[str]) -> str:
    supplied = (payload.title or "").strip()
    if supplied:
        return supplied
    if payload.thread_type == "client_thread" and client_name:
        purpose = (payload.purpose or "").strip()
        return f"{client_name} - {purpose}" if purpose else f"{client_name} - Client thread"
    if payload.thread_type == "direct_message":
        return "Direct message"
    if payload.thread_type == "team_channel":
        return "Team channel"
    if payload.thread_type == "announcement":
        return "Announcement"
    return "Message thread"


def _assert_can_access_thread(
    db: MessagesDatabase,
    thread_id: str,
    user: AuthenticatedUser,
) -> Dict[str, Any]:
    thread = db.get_thread_for_user(thread_id, _user_id(user), include_announcements=True)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@router.get("/threads")
async def list_threads(
    request: Request,
    db: MessagesDatabase = Depends(get_messages_db),
) -> Dict[str, Any]:
    user = require_authenticated_user(request)
    return {"success": True, "threads": db.list_threads(_user_id(user), include_announcements=True)}


@router.post("/threads")
async def create_thread(
    payload: ThreadCreateRequest,
    request: Request,
    db: MessagesDatabase = Depends(get_messages_db),
) -> Dict[str, Any]:
    user = require_authenticated_user(request)
    thread_type = payload.thread_type.strip()
    if thread_type not in THREAD_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported thread type")
    if thread_type == "announcement" and not user.is_admin:
        raise HTTPException(status_code=403, detail="Only supervisors/admins can create announcements")
    if thread_type == "direct_message" and not payload.participants:
        raise HTTPException(status_code=400, detail="Direct messages require a recipient")

    client_name = None
    if thread_type == "client_thread":
        if not payload.client_id:
            raise HTTPException(status_code=400, detail="Client thread requires client_id")
        assert_client_access(user, payload.client_id)
        client = _get_client_summary(payload.client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        client_name = client["client_name"]

    participants = _normalize_participants(user, payload)
    thread = db.create_thread(
        thread_type=thread_type,
        title=_default_title(payload, client_name),
        client_id=payload.client_id if thread_type == "client_thread" else None,
        client_name=client_name,
        created_by=_user_id(user),
        participants=participants,
        initial_message={
            "body": payload.initial_message.strip(),
            "sender_name": _display_name(user),
        } if payload.initial_message and payload.initial_message.strip() else None,
    )
    return {"success": True, "thread": thread}


@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    request: Request,
    db: MessagesDatabase = Depends(get_messages_db),
) -> Dict[str, Any]:
    user = require_authenticated_user(request)
    return {"success": True, "thread": _assert_can_access_thread(db, thread_id, user)}


@router.get("/threads/{thread_id}/messages")
async def list_messages(
    thread_id: str,
    request: Request,
    db: MessagesDatabase = Depends(get_messages_db),
) -> Dict[str, Any]:
    user = require_authenticated_user(request)
    _assert_can_access_thread(db, thread_id, user)
    return {"success": True, "messages": db.list_messages(thread_id)}


@router.post("/threads/{thread_id}/messages")
async def send_message(
    thread_id: str,
    payload: MessageCreateRequest,
    request: Request,
    db: MessagesDatabase = Depends(get_messages_db),
) -> Dict[str, Any]:
    user = require_authenticated_user(request)
    thread = _assert_can_access_thread(db, thread_id, user)
    if thread["thread_type"] == "announcement" and not user.is_admin:
        raise HTTPException(status_code=403, detail="Only supervisors/admins can post announcement messages")
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="Message body is required")
    message = db.add_message(thread_id, _user_id(user), _display_name(user), body)
    return {"success": True, "message": message}


@router.patch("/threads/{thread_id}/read")
async def mark_thread_read(
    thread_id: str,
    request: Request,
    db: MessagesDatabase = Depends(get_messages_db),
) -> Dict[str, Any]:
    user = require_authenticated_user(request)
    _assert_can_access_thread(db, thread_id, user)
    return {"success": True, "read": db.mark_read(thread_id, _user_id(user), _display_name(user))}


@router.get("/unread-count")
async def unread_count(
    request: Request,
    db: MessagesDatabase = Depends(get_messages_db),
) -> Dict[str, Any]:
    user = require_authenticated_user(request)
    return {"success": True, "unread_count": db.unread_count(_user_id(user), include_announcements=True)}

