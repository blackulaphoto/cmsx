import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from openai import AsyncOpenAI

from backend.auth.service import require_authenticated_user
from backend.auth.authorization import assert_client_access
from .database import groups_db
from .models import (
    AIGroupNoteRequest,
    AITopicGenerateRequest,
    AttendanceUpsert,
    NoteCreate,
    NoteUpdate,
    PlaylistCreate,
    PlaylistUpdate,
    SessionCreate,
    SessionUpdate,
    TopicCreate,
    TopicUpdate,
    VideoCreate,
    VideoUpdate,
)
from .seed_topics import seed_topics, seed_playlists

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/groups", tags=["groups"])

# Seed on module load
try:
    seed_topics(groups_db)
    seed_playlists(groups_db)
except Exception as exc:
    logger.warning(f"[GROUPS] Seed failed at startup: {exc}")

# OpenAI client (reuses existing env var pattern)
_openai_client: Optional[AsyncOpenAI] = None


def _get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=503, detail="OpenAI API key not configured")
        _openai_client = AsyncOpenAI(api_key=api_key)
    return _openai_client


def _validate_youtube_url(url: str) -> None:
    """Reject anything that is not a recognizable YouTube URL."""
    cleaned = (url or "").strip()
    patterns = [
        r"^https?://(www\.)?youtube\.com/watch\?",
        r"^https?://youtu\.be/",
        r"^https?://(www\.)?youtube\.com/playlist\?",
        r"^https?://(www\.)?youtube\.com/embed/",
        r"^https?://m\.youtube\.com/",
    ]
    if not any(re.match(p, cleaned) for p in patterns):
        raise HTTPException(
            status_code=422,
            detail="URL must be a valid YouTube video or playlist link.",
        )


def _extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID for embed use."""
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def _extract_playlist_id(url: str) -> Optional[str]:
    """Extract YouTube playlist ID."""
    m = re.search(r"[?&]list=([A-Za-z0-9_-]+)", url)
    return m.group(1) if m else None


# ── Topics ─────────────────────────────────────────────────────────────────────

@router.get("/topics")
async def list_topics(
    request: Request,
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
):
    require_authenticated_user(request)
    topics = groups_db.list_topics(category=category, search=search, source=source)
    return {"topics": topics, "count": len(topics)}


@router.get("/topics/categories")
async def list_categories(request: Request):
    require_authenticated_user(request)
    return {"categories": groups_db.list_categories()}


@router.get("/topics/{topic_id}")
async def get_topic(request: Request, topic_id: str):
    require_authenticated_user(request)
    topic = groups_db.get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


@router.post("/topics", status_code=201)
async def create_topic(request: Request, payload: TopicCreate):
    user = require_authenticated_user(request)
    data = payload.model_dump()
    data["created_by"] = user.case_manager_id
    data["source"] = "custom"
    topic = groups_db.create_topic(data)
    return topic


@router.put("/topics/{topic_id}")
async def update_topic(request: Request, topic_id: str, payload: TopicUpdate):
    require_authenticated_user(request)
    existing = groups_db.get_topic(topic_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Topic not found")
    updated = groups_db.update_topic(topic_id, payload.model_dump(exclude_none=True))
    return updated


@router.post("/topics/ai-generate", status_code=201)
async def ai_generate_topic(request: Request, payload: AITopicGenerateRequest):
    user = require_authenticated_user(request)
    client = _get_openai()
    model = os.getenv("OPENAI_MODEL", "gpt-4o")

    system_prompt = (
        "You are a licensed clinical psychoeducation group facilitator with expertise in SUD and mental health treatment. "
        "Generate a complete, evidence-based group facilitation plan. "
        "Return ONLY valid JSON — no markdown, no explanation, no backticks."
    )

    user_prompt = (
        f"Create a full psychoeducation group session plan for the following topic.\n\n"
        f"Topic: {payload.title}\n"
        f"Group length: {payload.group_length_minutes} minutes\n"
        f"Population: {payload.population}\n"
        f"Tone/style: {payload.tone}\n"
        f"Additional context: {payload.additional_context or 'none'}\n\n"
        "Return a JSON object with these exact fields:\n"
        "{\n"
        '  "title": "string",\n'
        '  "category": "one of: Addiction Education | Relapse Prevention | Coping Skills | Mental Health | Relationships | Emotional Skills | Identity & Recovery | Practical Life Skills",\n'
        '  "description": "2-3 sentence overview of the group topic and its clinical purpose",\n'
        '  "clinical_purpose": "1-2 sentences on the clinical rationale for this group",\n'
        '  "key_points": ["string", "string", "string"],\n'
        '  "discussion_questions": ["string", "string", "string", "string"],\n'
        '  "activity": "string describing a specific in-group activity",\n'
        '  "writing_prompt": "string — a journal or writing prompt for members",\n'
        '  "facilitator_tips": "string — 2-3 practical facilitation tips"\n'
        "}"
    )

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=1200,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if model wrapped anyway
        raw = re.sub(r"^```json\s*|^```\s*|```$", "", raw, flags=re.MULTILINE).strip()
        generated: Dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(f"[GROUPS] AI generate JSON parse failed: {exc}")
        raise HTTPException(status_code=502, detail="AI returned invalid JSON. Try again.")
    except Exception as exc:
        logger.error(f"[GROUPS] AI generate failed: {exc}")
        raise HTTPException(status_code=502, detail=f"AI generation failed: {exc}")

    # Persist as ai_generated topic
    topic_data = {
        "title": generated.get("title", payload.title),
        "category": generated.get("category", "General"),
        "description": generated.get("description", ""),
        "key_points": generated.get("key_points", []),
        "discussion_questions": generated.get("discussion_questions", []),
        "activity": generated.get("activity", ""),
        "writing_prompt": generated.get("writing_prompt", ""),
        "facilitator_tips": generated.get("facilitator_tips", ""),
        "source": "ai_generated",
        "created_by": user.case_manager_id,
    }
    saved_topic = groups_db.create_topic(topic_data)
    # Include clinical_purpose in response even though it's not a stored column
    saved_topic["clinical_purpose"] = generated.get("clinical_purpose", "")
    return saved_topic


# ── Playlists ──────────────────────────────────────────────────────────────────

@router.get("/playlists")
async def list_playlists(
    request: Request,
    category: Optional[str] = Query(None),
):
    require_authenticated_user(request)
    playlists = groups_db.list_playlists(category=category)
    # Enrich each playlist with embed-ready data
    for pl in playlists:
        pl["playlist_yt_id"] = _extract_playlist_id(pl.get("youtube_playlist_url", ""))
    return {"playlists": playlists, "count": len(playlists)}


@router.post("/playlists", status_code=201)
async def create_playlist(request: Request, payload: PlaylistCreate):
    user = require_authenticated_user(request)
    _validate_youtube_url(payload.youtube_playlist_url)
    data = payload.model_dump()
    data["added_by"] = user.case_manager_id
    playlist = groups_db.create_playlist(data)
    playlist["playlist_yt_id"] = _extract_playlist_id(playlist.get("youtube_playlist_url", ""))
    return playlist


@router.put("/playlists/{playlist_id}")
async def update_playlist(request: Request, playlist_id: str, payload: PlaylistUpdate):
    require_authenticated_user(request)
    existing = groups_db.get_playlist(playlist_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Playlist not found")
    updated = groups_db.update_playlist(playlist_id, payload.model_dump(exclude_none=True))
    return updated


# ── Videos ────────────────────────────────────────────────────────────────────

@router.get("/videos")
async def list_videos(
    request: Request,
    playlist_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
):
    require_authenticated_user(request)
    videos = groups_db.list_videos(playlist_id=playlist_id, category=category)
    for v in videos:
        v["video_yt_id"] = _extract_video_id(v.get("youtube_url", ""))
    return {"videos": videos, "count": len(videos)}


@router.post("/videos", status_code=201)
async def create_video(request: Request, payload: VideoCreate):
    user = require_authenticated_user(request)
    _validate_youtube_url(payload.youtube_url)
    data = payload.model_dump()
    data["added_by"] = user.case_manager_id
    video = groups_db.create_video(data)
    video["video_yt_id"] = _extract_video_id(video.get("youtube_url", ""))
    return video


@router.put("/videos/{video_id}")
async def update_video(request: Request, video_id: str, payload: VideoUpdate):
    require_authenticated_user(request)
    existing = groups_db.get_video(video_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Video not found")
    updated = groups_db.update_video(video_id, payload.model_dump(exclude_none=True))
    return updated


# ── Sessions ───────────────────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions(
    request: Request,
    status: Optional[str] = Query(None),
    topic_id: Optional[str] = Query(None),
):
    user = require_authenticated_user(request)
    sessions = groups_db.list_sessions(
        case_manager_id=user.case_manager_id if not user.is_admin else None,
        status=status,
        topic_id=topic_id,
    )
    return {"sessions": sessions, "count": len(sessions)}


@router.post("/sessions", status_code=201)
async def create_session(request: Request, payload: SessionCreate):
    user = require_authenticated_user(request)
    data = payload.model_dump()
    data["case_manager_id"] = user.case_manager_id
    session = groups_db.create_session(data)
    return session


@router.get("/sessions/{session_id}")
async def get_session(request: Request, session_id: str):
    require_authenticated_user(request)
    session = groups_db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # Enrich videos with yt_id for embed
    for v in session.get("videos") or []:
        if v:
            v["video_yt_id"] = _extract_video_id(v.get("youtube_url", ""))
    for pl in session.get("playlists") or []:
        if pl:
            pl["playlist_yt_id"] = _extract_playlist_id(pl.get("youtube_playlist_url", ""))
    return session


@router.put("/sessions/{session_id}")
async def update_session(request: Request, session_id: str, payload: SessionUpdate):
    require_authenticated_user(request)
    existing = groups_db.get_session(session_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Session not found")
    updated = groups_db.update_session(session_id, payload.model_dump(exclude_none=True))
    return updated


# ── Attendance ─────────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/attendance")
async def list_attendance(request: Request, session_id: str):
    require_authenticated_user(request)
    if not groups_db.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    records = groups_db.list_attendance(session_id)
    return {"attendance": records, "count": len(records)}


@router.post("/sessions/{session_id}/attendance", status_code=201)
async def upsert_attendance(request: Request, session_id: str, payload: AttendanceUpsert):
    current_user = require_authenticated_user(request)
    if not groups_db.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    assert_client_access(current_user, payload.client_id)
    record = groups_db.upsert_attendance({
        "session_id": session_id,
        "client_id": payload.client_id,
        "status": payload.status,
        "participation_level": payload.participation_level,
        "added_by": current_user.case_manager_id,
    })
    return record


@router.delete("/sessions/{session_id}/attendance/{client_id}", status_code=204)
async def remove_attendance(request: Request, session_id: str, client_id: str):
    current_user = require_authenticated_user(request)
    assert_client_access(current_user, client_id)
    groups_db.delete_attendance(session_id, client_id)


# ── Group Notes ────────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/notes")
async def list_notes(request: Request, session_id: str):
    require_authenticated_user(request)
    if not groups_db.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    notes = groups_db.list_notes(session_id)
    return {"notes": notes, "count": len(notes)}


@router.post("/sessions/{session_id}/notes", status_code=201)
async def create_note(request: Request, session_id: str, payload: NoteCreate):
    current_user = require_authenticated_user(request)
    if not groups_db.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    if payload.client_id:
        assert_client_access(current_user, payload.client_id)
    note = groups_db.create_note({
        "session_id": session_id,
        "client_id": payload.client_id,
        "note_type": payload.note_type,
        "content": payload.content,
        "ai_generated": payload.ai_generated,
        "created_by": current_user.case_manager_id,
    })
    return note


@router.put("/sessions/{session_id}/notes/{note_id}")
async def update_note(request: Request, session_id: str, note_id: str, payload: NoteUpdate):
    require_authenticated_user(request)
    existing = groups_db.get_note(note_id)
    if not existing or existing.get("session_id") != session_id:
        raise HTTPException(status_code=404, detail="Note not found")
    if existing.get("client_id"):
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, existing["client_id"])
    updated = groups_db.update_note(note_id, payload.model_dump(exclude_none=True))
    return updated


@router.post("/sessions/{session_id}/notes/ai-generate", status_code=201)
async def ai_generate_group_note(request: Request, session_id: str, payload: AIGroupNoteRequest):
    import httpx
    current_user = require_authenticated_user(request)
    session = groups_db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if payload.client_id:
        assert_client_access(current_user, payload.client_id)

    # Gather context: topic name + attendance summary (no real names, client_id only)
    topic_name = (session.get("topic") or {}).get("title", "group session")
    attendance = groups_db.list_attendance(session_id)
    present_count = sum(1 for a in attendance if a.get("status") == "present")
    participation_summary = ", ".join(
        f"{a['client_id']}:{a.get('participation_level','unknown')}"
        for a in attendance
        if a.get("status") == "present"
    ) or "none recorded"

    ai_context = {
        "group_topic": topic_name,
        "attendance": f"{present_count} present",
        "participation_level": participation_summary,
        **(payload.context or {}),
    }

    # Proxy to existing AI documentation group-note endpoint
    try:
        async with httpx.AsyncClient(timeout=30.0) as client_http:
            # Build internal request – forward auth token
            auth_header = request.headers.get("Authorization", "")
            resp = await client_http.post(
                "http://localhost:8000/api/ai-documentation/group-note",
                json={
                    "client_id": payload.client_id,
                    "context": ai_context,
                    "note_kind": "group_note",
                },
                headers={"Authorization": auth_header, "Content-Type": "application/json"},
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="AI documentation service unavailable")
        ai_data = resp.json()
        draft = ai_data.get("note_text") or ai_data.get("draft") or ""
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[GROUPS] AI group note proxy failed: {exc}")
        raise HTTPException(status_code=502, detail="AI note generation failed")

    note = groups_db.create_note({
        "session_id": session_id,
        "client_id": payload.client_id,
        "note_type": payload.note_type or "group",
        "content": draft,
        "ai_generated": True,
        "created_by": current_user.case_manager_id,
    })
    return note
