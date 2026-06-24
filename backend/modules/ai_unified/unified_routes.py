"""
Unified AI Routes
FastAPI router for GPT-4o + SQLite memory.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.auth.service import auth_service, require_authenticated_user
from backend.shared.tenancy import multi_tenant_enabled, resolve_org_id
from backend.modules.ai_documentation.service import documentation_ai_service
from .platform_guide import build_platform_guide_context
from .unified_service import UnifiedAIService

logger = logging.getLogger(__name__)
router = APIRouter()

unified_ai = UnifiedAIService()


def _build_documentation_context(message: str) -> Optional[str]:
    return documentation_ai_service.get_template_reference_context(message)

def _cleanup_tool_messages(case_manager_id: str) -> None:
    """Remove stale tool-role rows that break OpenAI message validation."""
    from backend.shared.db_path import DB_DIR as _DB_DIR
    db_path = _DB_DIR / "ai_assistant.db"
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
    # case_manager_id is accepted for backward compatibility but ignored;
    # the authenticated user's case_manager_id is always used instead.
    case_manager_id: Optional[str] = None
    current_route: Optional[str] = None


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> Dict[str, Any]:
    current_user = require_authenticated_user(request)
    case_manager_id = current_user.case_manager_id
    org_id = resolve_org_id(current_user) if multi_tenant_enabled() else None
    try:
        message = body.message
        _cleanup_tool_messages(case_manager_id)
        return await unified_ai.process_message(
            message=message,
            case_manager_id=case_manager_id,
            mode="central",
            injected_context=_build_documentation_context(message),
            org_id=org_id,
        )
    except Exception as exc:
        logger.error(f"Unified AI chat error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


def _build_assistant_context(message: str, *, current_route: Optional[str], current_user) -> Optional[str]:
    parts: List[str] = []
    documentation_context = _build_documentation_context(message)
    if documentation_context:
        parts.append(documentation_context)

    parts.append(
        build_platform_guide_context(
            message,
            current_route=current_route,
            user_role=getattr(current_user, "role", None),
            is_super_admin=auth_service.is_platform_super_admin(current_user),
        )
    )
    return "\n\n".join(part for part in parts if part)


@router.post("/assistant")
async def assistant_chat(request: Request, body: ChatRequest) -> Dict[str, Any]:
    """Read-only + search assistant endpoint for popup UI."""
    current_user = require_authenticated_user(request)
    case_manager_id = current_user.case_manager_id
    org_id = resolve_org_id(current_user) if multi_tenant_enabled() else None
    try:
        message = body.message
        _cleanup_tool_messages(case_manager_id)
        return await unified_ai.process_message(
            message=message,
            case_manager_id=case_manager_id,
            mode="assistant",
            injected_context=_build_assistant_context(
                message,
                current_route=body.current_route,
                current_user=current_user,
            ),
            org_id=org_id,
        )
    except Exception as exc:
        logger.error(f"Unified AI assistant error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/conversation")
async def get_conversation(request: Request) -> List[Dict[str, Any]]:
    current_user = require_authenticated_user(request)
    case_manager_id = current_user.case_manager_id
    org_id = resolve_org_id(current_user) if multi_tenant_enabled() else None
    try:
        return await unified_ai.get_conversation_history(case_manager_id, org_id=org_id)
    except Exception as exc:
        logger.error(f"Unified AI conversation error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
