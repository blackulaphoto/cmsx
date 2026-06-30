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
from backend.modules.services.case_management_api import get_clients_from_db
from backend.shared.tenancy import multi_tenant_enabled, resolve_org_id
from backend.modules.ai_documentation.service import documentation_ai_service
from backend.modules.reminders.repository import get_client_work_items
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
    client_id: Optional[str] = None
    client_name: Optional[str] = None
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
            injected_context=_build_chat_context(
                message,
                current_user=current_user,
                client_id=body.client_id,
                client_name=body.client_name,
            ),
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


def _resolve_client_from_request(
    message: str,
    *,
    current_user,
    client_id: Optional[str],
    client_name: Optional[str],
) -> Dict[str, Any]:
    if client_id:
        return {
            "status": "resolved",
            "client_id": client_id,
            "client_name": client_name,
        }

    org_id = resolve_org_id(current_user) if multi_tenant_enabled() else None
    scope = get_clients_from_db(case_manager_id=current_user.case_manager_id, org_id=org_id)
    clients = scope.get("clients", []) or []
    if not clients:
        return {"status": "missing"}

    def _client_display_name(client: Dict[str, Any]) -> str:
        return f"{client.get('first_name', '')} {client.get('last_name', '')}".strip()

    if client_name:
        query = client_name.strip().lower()
        matches = [
            client for client in clients
            if query and query in _client_display_name(client).lower()
        ]
    else:
        message_lc = message.lower()
        matches = [
            client for client in clients
            if _client_display_name(client) and _client_display_name(client).lower() in message_lc
        ]

    if len(matches) == 1:
        match = matches[0]
        return {
            "status": "resolved",
            "client_id": match.get("client_id"),
            "client_name": _client_display_name(match),
        }
    if len(matches) > 1:
        return {
            "status": "ambiguous",
            "matches": [
                {
                    "client_id": match.get("client_id"),
                    "client_name": _client_display_name(match),
                }
                for match in matches
            ],
        }
    return {"status": "missing"}


def _build_selected_client_task_context(current_user, client_id: Optional[str], client_name: Optional[str]) -> Optional[str]:
    if not client_id:
        return None

    org_id = resolve_org_id(current_user) if multi_tenant_enabled() else None
    work_items_payload = get_client_work_items(
        current_user.case_manager_id,
        client_id,
        org_id=org_id,
    )
    work_items = work_items_payload.get("items") or []

    resolved_name = client_name or next(
        (item.get("client_name") for item in work_items if item.get("client_name")),
        "Selected client",
    )

    counts = {
        "overdue": len([item for item in work_items if item.get("bucket") == "overdue"]),
        "today": len([item for item in work_items if item.get("bucket") == "today"]),
        "next_3_days": len([item for item in work_items if item.get("bucket") == "next_3_days"]),
        "this_week": len([item for item in work_items if item.get("bucket") == "this_week"]),
        "high_priority_no_date": len([item for item in work_items if item.get("bucket") == "high_priority_no_date"]),
        "later": len([item for item in work_items if item.get("bucket") == "later"]),
    }

    lines = [
        "Selected client operational context:",
        f"- Client: {resolved_name}",
        f"- Smart Daily aligned task count for this client: {len(work_items)}",
        f"- Overdue: {counts['overdue']}",
        f"- Due today: {counts['today']}",
        f"- Next 3 days: {counts['next_3_days']}",
        f"- This week: {counts['this_week']}",
        f"- High priority without due dates: {counts['high_priority_no_date']}",
    ]

    priority_buckets = [
        ("Overdue tasks", "overdue"),
        ("Due today", "today"),
        ("Next 3 days", "next_3_days"),
    ]
    for label, bucket_key in priority_buckets:
        bucket_tasks = [item for item in work_items if item.get("bucket") == bucket_key]
        if not bucket_tasks:
            continue
        lines.append(f"{label}:")
        for task in bucket_tasks[:5]:
            due_date = task.get("due_date") or "no due date"
            priority = task.get("priority") or "medium"
            title = task.get("title") or task.get("message") or task.get("task_type") or "Untitled task"
            source_label = task.get("source_label") or task.get("source") or "Task"
            lines.append(f"- {title} | due: {due_date} | priority: {priority} | source: {source_label}")

    if counts["overdue"] == 0:
        lines.append("If asked whether this client has overdue tasks, answer that Smart Daily currently shows none for this selected client.")
    else:
        lines.append("If asked whether this client has overdue tasks, answer from the overdue list above and do not say there are none.")

    return "\n".join(lines)


def _build_chat_context(
    message: str,
    *,
    current_user,
    client_id: Optional[str],
    client_name: Optional[str],
) -> Optional[str]:
    parts: List[str] = []
    documentation_context = _build_documentation_context(message)
    if documentation_context:
        parts.append(documentation_context)

    resolution = _resolve_client_from_request(
        message,
        current_user=current_user,
        client_id=client_id,
        client_name=client_name,
    )
    if resolution.get("status") == "ambiguous":
        matches = resolution.get("matches") or []
        matched_names = ", ".join(match.get("client_name", "Unknown Client") for match in matches[:5])
        parts.append(
            "Client resolution context:\n"
            f"- Multiple accessible clients match this request: {matched_names}\n"
            "- Ask the user to clarify which client they mean before naming tasks or reminders."
        )
    selected_client_context = _build_selected_client_task_context(
        current_user,
        resolution.get("client_id"),
        resolution.get("client_name") or client_name,
    )
    if selected_client_context:
        parts.append(selected_client_context)
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
            injected_context="\n\n".join(
                part
                for part in [
                    _build_assistant_context(
                        message,
                        current_route=body.current_route,
                        current_user=current_user,
                    ),
                    _build_chat_context(
                        message,
                        current_user=current_user,
                        client_id=body.client_id,
                        client_name=body.client_name,
                    ),
                ]
                if part
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
