import asyncio
import logging
import os
from typing import Any, Dict, Optional

import requests
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from backend.auth.authorization import assert_client_access
from backend.auth.service import require_authenticated_user
from backend.modules.ai_documentation.service import documentation_ai_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["transcription"])

DEEPGRAM_PRERECORDED_URL = "https://api.deepgram.com/v1/listen"
MAX_AUDIO_BYTES = 10 * 1024 * 1024
SUPPORTED_AUDIO_TYPES = {
    "audio/webm",
    "audio/mp4",
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/ogg",
}


class GenerateFromTranscriptRequest(BaseModel):
    clientId: str
    noteType: str = "cm_note"
    transcript: str


def _extract_transcript_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    results = payload.get("results") or {}
    channels = results.get("channels") or []
    alternatives = channels[0].get("alternatives") if channels else []
    primary = alternatives[0] if alternatives else {}
    transcript = (primary.get("transcript") or "").strip()
    confidence = primary.get("confidence")
    return {
        "transcript": transcript,
        "confidence": confidence,
        "metadata": payload.get("metadata") or {},
    }


def _normalize_content_type(content_type: Optional[str]) -> str:
    normalized = (content_type or "").strip().lower()
    if not normalized:
        return "audio/webm"
    return normalized.split(";", 1)[0].strip()


def _validate_audio_upload(file: UploadFile, content: bytes) -> str:
    if not file:
        raise HTTPException(status_code=400, detail="Audio file is required")
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty")
    if len(content) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio file exceeds 10 MB limit")

    content_type = _normalize_content_type(file.content_type)
    if content_type not in SUPPORTED_AUDIO_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported audio format")
    return content_type


def _post_to_deepgram(api_key: str, content: bytes, content_type: str) -> Dict[str, Any]:
    response = requests.post(
        DEEPGRAM_PRERECORDED_URL,
        params={
            "model": "nova-3",
            "smart_format": "true",
            "punctuate": "true",
        },
        headers={
            "Authorization": f"Token {api_key}",
            "Content-Type": content_type,
        },
        data=content,
        timeout=60,
    )

    if response.status_code >= 400:
        logger.error("Deepgram transcription failed with status %s", response.status_code)
        raise HTTPException(status_code=502, detail="Transcription provider request failed")

    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Invalid transcription provider response") from exc

    transcript_payload = _extract_transcript_payload(payload)
    if not transcript_payload["transcript"]:
        raise HTTPException(status_code=422, detail="No transcript returned for audio")

    return transcript_payload


@router.post("/api/transcribe")
async def transcribe_audio(request: Request, audio: UploadFile = File(...)):
    require_authenticated_user(request)
    api_key = os.getenv("DEEPGRAM_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="Transcription service is not configured")

    content = await audio.read()
    content_type = _validate_audio_upload(audio, content)
    result = await asyncio.to_thread(_post_to_deepgram, api_key, content, content_type)

    return {
        "transcript": result["transcript"],
        "confidence": result["confidence"],
        "metadata": result["metadata"],
    }


@router.post("/api/notes/generate-from-transcript")
async def generate_note_from_transcript(payload: GenerateFromTranscriptRequest, request: Request):
    current_user = require_authenticated_user(request)
    assert_client_access(current_user, payload.clientId)

    transcript = (payload.transcript or "").strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript is required")

    try:
        result = await documentation_ai_service.generate_note_from_transcript(
            {
                "client_id": payload.clientId,
                "note_type": payload.noteType,
                "transcript": transcript,
                "case_manager_id": current_user.case_manager_id,
            }
        )
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to generate note from transcript: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate note from transcript") from exc
