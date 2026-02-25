"""
Unified AI Routes
FastAPI router for GPT-4o + SQLite memory.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .unified_service import UnifiedAIService

logger = logging.getLogger(__name__)
router = APIRouter()

unified_ai = UnifiedAIService()

def _cleanup_tool_messages(case_manager_id: str) -> None:
    """Remove stale tool-role rows that break OpenAI message validation."""
    db_path = Path(__file__).resolve().parents[3] / "databases" / "ai_assistant.db"
    if not db_path.exists():
        return
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(conversations)")
        columns = {row[1] for row in cursor.fetchall()}
        if "role" not in columns:
            conn.close()
            return
        cursor.execute(
            "DELETE FROM conversations WHERE case_manager_id = ? AND role = ?",
            (case_manager_id, "tool"),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning(f"Unified AI cleanup skipped: {exc}")


class ChatRequest(BaseModel):
    message: str
    case_manager_id: Optional[str] = None


@router.post("/chat")
async def chat(request: ChatRequest) -> Dict[str, Any]:
    try:
        case_manager_id = (request.case_manager_id or "default_cm").strip() or "default_cm"
        message = request.message
        _cleanup_tool_messages(case_manager_id)
        return await unified_ai.process_message(
            message=message,
            case_manager_id=case_manager_id,
            mode="central",
        )
    except Exception as exc:
        logger.error(f"Unified AI chat error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/assistant")
async def assistant_chat(request: ChatRequest) -> Dict[str, Any]:
    """Read-only + search assistant endpoint for popup UI."""
    try:
        case_manager_id = (request.case_manager_id or "default_cm").strip() or "default_cm"
        message = request.message
        _cleanup_tool_messages(case_manager_id)
        return await unified_ai.process_message(
            message=message,
            case_manager_id=case_manager_id,
            mode="assistant",
        )
    except Exception as exc:
        logger.error(f"Unified AI assistant error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/conversation/{case_manager_id}")
async def get_conversation(case_manager_id: str) -> List[Dict[str, Any]]:
    try:
        return await unified_ai.get_conversation_history(case_manager_id)
    except Exception as exc:
        logger.error(f"Unified AI conversation error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
