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
    AttendeeNoteSpec,
    BulkGenerateRequest,
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

def _build_individual_note_prompt(
    topic_title: str,
    topic_description: str,
    key_points: List[str],
    attendance_status: str,
    participation_level: str,
    engagement_preset: str,
    note_setting: str,
    allow_ai_quotes: bool,
    staff_quote: str,
    session_location: str,
) -> str:
    setting_label = {
        "telehealth": "Telehealth",
        "in-person": "In-Person",
        "mixed": "In-Person / Telehealth",
    }.get(note_setting, "In-Person")

    telehealth = note_setting == "telehealth"
    location_line = (
        "Location of Client: Sober Living. The client attended the group virtually via Google Meet."
        if telehealth
        else f"Location of Client: {session_location or 'In person'}."
    )

    key_pts_text = "\n".join(f"- {p}" for p in key_points) if key_points else "(no key points provided)"

    quote_instruction = ""
    if staff_quote and staff_quote.strip():
        quote_instruction = f'Staff-entered client quote (use verbatim): "{staff_quote.strip()}"'
    elif allow_ai_quotes and attendance_status not in ("absent",):
        quote_instruction = (
            "You MAY draft a realistic, clinically appropriate first-person client quote "
            "consistent with the engagement level and topic. The quote should reflect "
            "genuine insight or struggle, not a textbook answer. Introduce it with 'CT stated, \"...\"'"
        )
    else:
        quote_instruction = "Do NOT include any client quote. Do not invent statements."

    absent_instruction = ""
    if attendance_status == "absent":
        return (
            f"Write a brief group note for a client who was ABSENT from today's session.\n"
            f"Group topic: {topic_title}.\n"
            f"Format: 'CT did not attend the scheduled psychoeducational group on [topic]. "
            f"Attendance was marked absent. Staff will follow up with CT regarding missed group "
            f"participation and encourage attendance at the next scheduled group.'\n"
            f"Output only the note text. No headers. No preamble."
        )

    engagement_descriptions = {
        "active": "alert, engaged, cooperative, verbally participated throughout, maintained appropriate eye contact",
        "moderate": "attentive and cooperative, participated when prompted, appropriate demeanor",
        "minimal": "minimally engaged, quiet, limited verbal participation",
        "quiet/non-speaking": "quiet but attentive, remained seated, did not verbally participate, demonstrated nonverbal engagement (eye contact, nodding)",
        "resistant": "guarded and resistant, limited verbal participation, appeared uncomfortable at times",
        "distracted": "minimally engaged, appeared distracted at times, required redirection",
        "camera off": "remained logged in with camera off, did not verbally participate, engagement difficult to fully assess",
        "late": "arrived late, present for remainder of session, quiet but attentive after arrival",
    }
    engagement_desc = engagement_descriptions.get(engagement_preset, engagement_descriptions.get(participation_level, "attentive and cooperative"))

    prompt = f"""You are a licensed clinical social worker writing chart-ready psychoeducational group notes.

Write a professional, third-person group note for a single client using "CT" (not the client's name).

Session details:
- Group topic: {topic_title}
- Topic description: {topic_description or '(not provided)'}
- Key points covered: {key_pts_text}
- Setting: {setting_label}
- Attendance: {attendance_status}
- Client engagement: {engagement_desc}
- {quote_instruction}

Note structure to follow:
1. Start with: "{location_line}"
{"2. Note that the client attended virtually via telehealth." if telehealth else "2. Note that the client attended in person."}
3. Describe how CT presented (mood, posture, demeanor) — match the engagement level.
4. State that CT participated in a psychoeducational group on [topic].
5. Describe CT's engagement and behavior (verbally participated / remained quiet / etc.) — match engagement preset.
{"6. Include the client quote as directed above." if (staff_quote or allow_ai_quotes) else "6. Do NOT include any quote."}
7. Note that CT was receptive to (or appeared to receive) psychoeducation on the topic's key themes.
8. Briefly summarize what CT identified or engaged with (or what the facilitator reviewed if CT was non-verbal).
9. Note any encouragement given.
10. Close with whether CT remained for the full session.

Rules:
- Use "CT" throughout. Never invent a name.
- Write in past tense, third person.
- Do not include headers, bullet points, or labels — write in flowing paragraph form.
- Do not include session date, therapist name, or signature lines.
- Length: 4–7 sentences. Clinical but readable.
- Output ONLY the note text. No preamble, no explanation.
"""
    return prompt


def _build_group_summary_prompt(
    topic_title: str,
    topic_description: str,
    key_points: List[str],
    discussion_questions: List[str],
    activity: str,
    present_count: int,
    note_setting: str,
) -> str:
    key_pts_text = "\n".join(f"- {p}" for p in key_points) if key_points else "(not provided)"
    dq_text = "\n".join(f"- {q}" for q in discussion_questions) if discussion_questions else "(not provided)"

    return f"""You are a licensed clinical social worker writing a chart-ready group summary note.

Write a professional group summary note documenting a psychoeducational group session.

Session details:
- Group topic: {topic_title}
- Topic description: {topic_description or '(not provided)'}
- Key points covered:
{key_pts_text}
- Discussion questions used:
{dq_text}
- In-group activity: {activity or '(not provided)'}
- Attendance: approximately {present_count} participants
- Setting: {note_setting}

Note structure:
1. Start with "Group Topic: {topic_title}" on its own line, then a blank line.
2. Write 1–2 paragraphs describing:
   - What the facilitator covered (education provided, key concepts)
   - What participants were prompted to discuss or reflect on
   - What coping strategies, skills, or tools were highlighted
   - What participants were encouraged to practice or identify
3. Do not reference specific clients by name or ID.
4. Write in past tense, third person.
5. Do not include headers beyond the topic line, bullet points, or signature lines.
6. Length: 100–180 words total.
7. Output ONLY the note text. No preamble.
"""


async def _call_openai_for_note(prompt: str) -> str:
    client = _get_openai()
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You write clinical psychoeducational group notes. Return only the note text."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=600,
    )
    return response.choices[0].message.content.strip()


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
        "quote_generated": payload.quote_generated,
        "reviewed": payload.reviewed,
        "finalized": payload.finalized,
        "engagement_preset": payload.engagement_preset or "",
        "note_setting": payload.note_setting,
        "staff_quote": payload.staff_quote or "",
        "created_by": current_user.case_manager_id,
    })
    return note


@router.put("/sessions/{session_id}/notes/{note_id}")
async def update_session_note(request: Request, session_id: str, note_id: str, payload: NoteUpdate):
    current_user = require_authenticated_user(request)
    existing = groups_db.get_note(note_id)
    if not existing or existing.get("session_id") != session_id:
        raise HTTPException(status_code=404, detail="Note not found")
    if existing.get("client_id"):
        assert_client_access(current_user, existing["client_id"])
    updated = groups_db.update_note(note_id, payload.model_dump(exclude_none=True))
    return updated


@router.put("/notes/{note_id}")
async def update_note_direct(request: Request, note_id: str, payload: NoteUpdate):
    """Top-level note update — client PHI check enforced if note has client_id."""
    current_user = require_authenticated_user(request)
    existing = groups_db.get_note(note_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")
    if existing.get("client_id"):
        assert_client_access(current_user, existing["client_id"])
    return groups_db.update_note(note_id, payload.model_dump(exclude_none=True))


@router.post("/sessions/{session_id}/notes/ai-generate", status_code=201)
async def ai_generate_note(request: Request, session_id: str, payload: AIGroupNoteRequest):
    current_user = require_authenticated_user(request)
    session = groups_db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if payload.client_id:
        assert_client_access(current_user, payload.client_id)

    topic = session.get("topic") or {}
    topic_title = topic.get("title", "group session")
    topic_desc = topic.get("description", "")
    key_points = topic.get("key_points_json") or []
    discussion_questions = topic.get("discussion_questions_json") or []
    activity = topic.get("activity", "")
    session_location = session.get("location", "In person")

    try:
        if payload.note_type == "group":
            attendance = groups_db.list_attendance(session_id)
            present_count = sum(1 for a in attendance if a.get("status") in ("present", "late"))
            prompt = _build_group_summary_prompt(
                topic_title, topic_desc, key_points, discussion_questions,
                activity, present_count, payload.note_setting,
            )
        else:
            prompt = _build_individual_note_prompt(
                topic_title=topic_title,
                topic_description=topic_desc,
                key_points=key_points,
                attendance_status=payload.attendance_status or "present",
                participation_level=payload.participation_level or "moderate",
                engagement_preset=payload.engagement_preset or "moderate",
                note_setting=payload.note_setting,
                allow_ai_quotes=payload.allow_ai_quotes,
                staff_quote=payload.staff_quote or "",
                session_location=session_location,
            )

        draft = await _call_openai_for_note(prompt)
    except Exception as exc:
        logger.error(f"[GROUPS] Note AI generation failed: {exc}")
        raise HTTPException(status_code=502, detail=f"AI note generation failed: {exc}")

    note = groups_db.create_note({
        "session_id": session_id,
        "client_id": payload.client_id,
        "note_type": payload.note_type,
        "content": draft,
        "ai_generated": True,
        "quote_generated": bool(payload.allow_ai_quotes and not payload.staff_quote),
        "engagement_preset": payload.engagement_preset or "",
        "note_setting": payload.note_setting,
        "staff_quote": payload.staff_quote or "",
        "created_by": current_user.case_manager_id,
    })
    return note


@router.post("/sessions/{session_id}/notes/bulk-generate")
async def bulk_generate_notes(request: Request, session_id: str, payload: BulkGenerateRequest):
    """Generate individual notes for up to 50 attendees in one request."""
    current_user = require_authenticated_user(request)
    session = groups_db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if len(payload.attendees) > 50:
        raise HTTPException(status_code=422, detail="Maximum 50 attendees per bulk request")

    topic = session.get("topic") or {}
    topic_title = topic.get("title", "group session")
    topic_desc = topic.get("description", "")
    key_points = topic.get("key_points_json") or []
    session_location = session.get("location", "In person")

    results: List[Dict[str, Any]] = []
    succeeded = 0
    failed = 0

    import asyncio
    semaphore = asyncio.Semaphore(5)

    async def _gen_one(spec: AttendeeNoteSpec) -> Dict[str, Any]:
        nonlocal succeeded, failed
        try:
            assert_client_access(current_user, spec.client_id)
        except Exception:
            failed += 1
            return {"client_id": spec.client_id, "error": "access denied", "note": None}

        async with semaphore:
            try:
                prompt = _build_individual_note_prompt(
                    topic_title=topic_title,
                    topic_description=topic_desc,
                    key_points=key_points,
                    attendance_status=spec.attendance_status,
                    participation_level=spec.participation_level,
                    engagement_preset=spec.engagement_preset,
                    note_setting=payload.note_setting,
                    allow_ai_quotes=payload.allow_ai_quotes,
                    staff_quote=spec.staff_quote or "",
                    session_location=session_location,
                )
                draft = await _call_openai_for_note(prompt)
                note = groups_db.create_note({
                    "session_id": session_id,
                    "client_id": spec.client_id,
                    "note_type": "individual",
                    "content": draft,
                    "ai_generated": True,
                    "quote_generated": bool(payload.allow_ai_quotes and not spec.staff_quote),
                    "engagement_preset": spec.engagement_preset,
                    "note_setting": payload.note_setting,
                    "staff_quote": spec.staff_quote or "",
                    "created_by": current_user.case_manager_id,
                })
                succeeded += 1
                return {"client_id": spec.client_id, "error": None, "note": note}
            except Exception as exc:
                logger.error(f"[GROUPS] Bulk note failed for {spec.client_id}: {exc}")
                failed += 1
                return {"client_id": spec.client_id, "error": str(exc), "note": None}

    tasks = [_gen_one(spec) for spec in payload.attendees]
    results = await asyncio.gather(*tasks)

    return {
        "succeeded": succeeded,
        "failed": failed,
        "total": len(payload.attendees),
        "results": results,
    }
