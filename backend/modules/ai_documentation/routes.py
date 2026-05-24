import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .service import documentation_ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-documentation", tags=["ai-documentation"])


class NoteDraftRequest(BaseModel):
    module: str = "case_management"
    note_kind: str = "progress_note"
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    user_prompt: Optional[str] = ""
    current_text: Optional[str] = ""
    context: Dict[str, Any] = Field(default_factory=dict)


class ComplianceReviewRequest(BaseModel):
    note_kind: str = "progress_note"
    content: str
    context: Dict[str, Any] = Field(default_factory=dict)


class TreatmentPlanSuggestionRequest(BaseModel):
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class GroupNoteRequest(BaseModel):
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    user_prompt: Optional[str] = ""
    current_text: Optional[str] = ""
    context: Dict[str, Any] = Field(default_factory=dict)


class FollowUpTaskRequest(BaseModel):
    client_id: str
    title: str
    description: Optional[str] = ""
    priority: str = "medium"
    due_date: Optional[str] = None
    task_type: str = "documentation_follow_up"
    assigned_to: Optional[str] = "Case Manager"


@router.post("/note-draft")
async def generate_note_draft(payload: NoteDraftRequest):
    try:
        result = await documentation_ai_service.generate_note_draft(payload.model_dump())
        return {"success": True, **result}
    except Exception as exc:
        logger.error("Failed to generate documentation draft: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate documentation draft") from exc


@router.post("/compliance-review")
async def compliance_review(payload: ComplianceReviewRequest):
    try:
        result = documentation_ai_service.compliance_review(payload.model_dump())
        return {"success": True, **result}
    except Exception as exc:
        logger.error("Failed to review documentation compliance: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to review documentation compliance") from exc


@router.post("/treatment-plan-suggestions")
async def treatment_plan_suggestions(payload: TreatmentPlanSuggestionRequest):
    try:
        result = documentation_ai_service.generate_treatment_plan_suggestions(payload.model_dump())
        return {"success": True, **result}
    except Exception as exc:
        logger.error("Failed to generate treatment plan suggestions: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate treatment plan suggestions") from exc


@router.post("/group-note")
async def generate_group_note(payload: GroupNoteRequest):
    try:
        result = await documentation_ai_service.generate_group_note(payload.model_dump())
        return {"success": True, **result}
    except Exception as exc:
        logger.error("Failed to generate group note: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate group note") from exc


@router.post("/follow-up-task")
async def create_follow_up_task(payload: FollowUpTaskRequest):
    try:
        task = documentation_ai_service.create_follow_up_task(payload.client_id, payload.model_dump())
        return {"success": True, "task": task}
    except Exception as exc:
        logger.error("Failed to create documentation follow-up task: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create documentation follow-up task") from exc
