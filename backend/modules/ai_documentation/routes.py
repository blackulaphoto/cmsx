import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.shared.database.workspace_store import workspace_store
from .service import documentation_ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-documentation", tags=["ai-documentation"])
DEFAULT_CASE_MANAGER_ID = "cm_001"
BRAND_UPLOADS_DIR = Path(__file__).resolve().parents[3] / "uploads" / "documentation_brand"
BRAND_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


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


def _safe_filename(filename: str) -> str:
    name = os.path.basename(filename or "upload")
    return "".join(char for char in name if char.isalnum() or char in {" ", ".", "-", "_"}) or "upload"


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


@router.get("/brand-resources")
async def list_brand_resources():
    try:
        resources = workspace_store.list_brand_resources(DEFAULT_CASE_MANAGER_ID)
        return {"success": True, "resources": resources}
    except Exception as exc:
        logger.error("Failed to list brand resources: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list brand resources") from exc


@router.post("/brand-resources/upload")
async def upload_brand_resource(
    file: UploadFile = File(...),
    category: str = Form("general"),
    description: str = Form(""),
):
    safe_name = _safe_filename(file.filename)
    extension = Path(safe_name).suffix
    stored_name = f"{uuid4().hex}{extension}"
    stored_path = BRAND_UPLOADS_DIR / stored_name

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        with open(stored_path, "wb") as buffer:
            buffer.write(content)

        extraction = documentation_ai_service.extract_brand_guidance_text(
            str(stored_path),
            file.content_type or "application/octet-stream",
        )

        resource = workspace_store.create_brand_resource(
            case_manager_id=DEFAULT_CASE_MANAGER_ID,
            resource_id=uuid4().hex,
            name=safe_name,
            category=category or "general",
            description=description or "",
            size=len(content),
            content_type=file.content_type or "application/octet-stream",
            file_path=stored_name,
            extracted_text=extraction.get("extracted_text", ""),
            extraction_status=extraction.get("extraction_status", "unsupported"),
        )
        return {"success": True, "resource": resource}
    except HTTPException:
        if stored_path.exists():
            stored_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        logger.error("Failed to upload brand resource: %s", exc)
        if stored_path.exists():
            stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Failed to upload brand resource") from exc


@router.get("/brand-resources/{resource_id}/download")
async def download_brand_resource(resource_id: str):
    resource = workspace_store.get_brand_resource(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Brand resource not found")

    file_path = (BRAND_UPLOADS_DIR / resource["file_path"]).resolve()
    uploads_root = BRAND_UPLOADS_DIR.resolve()
    try:
        file_path.relative_to(uploads_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid file path") from exc

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Uploaded file not found")

    return FileResponse(
        path=file_path,
        filename=resource.get("name") or os.path.basename(file_path),
        media_type=resource.get("type") or "application/octet-stream",
    )


@router.delete("/brand-resources/{resource_id}")
async def delete_brand_resource(resource_id: str):
    resource = workspace_store.get_brand_resource(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Brand resource not found")

    file_path = BRAND_UPLOADS_DIR / resource["file_path"]
    try:
        workspace_store.delete_brand_resource(resource_id)
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        return {"success": True, "message": "Brand resource deleted"}
    except Exception as exc:
        logger.error("Failed to delete brand resource: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to delete brand resource") from exc
