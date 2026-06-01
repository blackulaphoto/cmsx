import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.shared.database.workspace_store import workspace_store
from backend.auth.authorization import assert_client_access
from backend.auth.service import require_authenticated_user
from .service import documentation_ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-documentation", tags=["ai-documentation"])
DEFAULT_CASE_MANAGER_ID = "cm_001"
BRAND_UPLOADS_DIR = Path(__file__).resolve().parents[3] / "uploads" / "documentation_brand"
BRAND_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "templates"
DOCUMENT_TEMPLATES_DIR = PROJECT_TEMPLATES_DIR / "document-templates"
REFERENCE_LIBRARY_DIR = PROJECT_TEMPLATES_DIR / "reference-library"
AI_INSTRUCTIONS_DIR = PROJECT_TEMPLATES_DIR / "ai-instructions"


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


def _slugify(value: str) -> str:
    lowered = (value or "").strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "template"


def _guess_template_metadata(file_name: str, body: str) -> Dict[str, str]:
    normalized_name = file_name.lower()
    normalized_body = body.lower()

    if "fmla" in normalized_name or "fmla" in normalized_body:
        return {
            "mode": "document",
            "category": "fmla",
            "noteType": "FMLA",
            "noteKind": "fmla_correspondence",
            "bestFor": "Employer, provider, HR, and paperwork communication tied to leave management.",
        }

    if "group" in normalized_name or "group note" in normalized_body:
        return {
            "mode": "note",
            "category": "clinical",
            "noteType": "Group",
            "noteKind": "group_note",
            "bestFor": "Attendance, participation, interventions, and client response in groups.",
        }

    if "treatment plan" in normalized_name or "treatment plan" in normalized_body:
        return {
            "mode": "document",
            "category": "planning",
            "noteType": "Treatment Plan",
            "noteKind": "treatment_plan",
            "bestFor": "Goal reviews, objective updates, and intervention planning.",
        }

    if "discharge" in normalized_name or "discharge summary" in normalized_body:
        return {
            "mode": "document",
            "category": "planning",
            "noteType": "Discharge",
            "noteKind": "discharge_summary",
            "bestFor": "Transition planning, aftercare coordination, and discharge readiness.",
        }

    if "progress report" in normalized_name or "progress report" in normalized_body:
        return {
            "mode": "document",
            "category": "letters",
            "noteType": "Court",
            "noteKind": "referral_summary",
            "bestFor": "Formal treatment progress updates for court, probation, employer, or benefits requests.",
        }

    if "proof of residence" in normalized_name or "proof of residency" in normalized_body:
        return {
            "mode": "document",
            "category": "letters",
            "noteType": "Housing",
            "noteKind": "referral_summary",
            "bestFor": "Residency verification for sober living, benefits, DMV, court, or probation needs.",
        }

    if "presence" in normalized_name or "presence in treatment" in normalized_body:
        return {
            "mode": "document",
            "category": "letters",
            "noteType": "Court",
            "noteKind": "referral_summary",
            "bestFor": "Treatment presence verification for court, probation, or administrative requests.",
        }

    if "completion" in normalized_name or "successfully completed treatment" in normalized_body:
        return {
            "mode": "document",
            "category": "letters",
            "noteType": "Discharge",
            "noteKind": "discharge_summary",
            "bestFor": "Completion verification for court, probation, employer, housing, or aftercare coordination.",
        }

    if "initial cm note" in normalized_name or "cm-init-01" in normalized_body:
        return {
            "mode": "note",
            "category": "clinical",
            "noteType": "Progress",
            "noteKind": "initial_note",
            "bestFor": "Week 1 intake, treatment orientation, and early case management documentation.",
        }

    if "weekly cm note" in normalized_name or "ongoing weekly cm note" in normalized_body:
        return {
            "mode": "note",
            "category": "clinical",
            "noteType": "Progress",
            "noteKind": "progress_note",
            "bestFor": "Ongoing weekly case management notes and progress tracking.",
        }

    return {
        "mode": "document",
        "category": "planning",
        "noteType": "General",
        "noteKind": "progress_note",
        "bestFor": "General documentation template.",
    }


def _load_document_templates() -> List[Dict[str, Any]]:
    templates: List[Dict[str, Any]] = []
    if not DOCUMENT_TEMPLATES_DIR.exists():
        return templates

    for template_path in sorted(DOCUMENT_TEMPLATES_DIR.glob("*")):
        if not template_path.is_file() or template_path.suffix.lower() not in {".md", ".txt"}:
            continue

        body = template_path.read_text(encoding="utf-8", errors="ignore").strip()
        label = template_path.stem
        metadata = _guess_template_metadata(template_path.name, body)
        templates.append(
            {
                "id": f"file-{_slugify(label)}",
                "label": label,
                "source": "file",
                "fileName": template_path.name,
                "relativePath": str(template_path.relative_to(PROJECT_TEMPLATES_DIR)).replace("\\", "/"),
                "body": body,
                **metadata,
            }
        )

    return templates


def _load_reference_files(directory: Path, source: str) -> List[Dict[str, Any]]:
    resources: List[Dict[str, Any]] = []
    if not directory.exists():
        return resources

    for resource_path in sorted(directory.glob("*")):
        if not resource_path.is_file():
            continue
        text = resource_path.read_text(encoding="utf-8", errors="ignore").strip()
        resources.append(
            {
                "name": resource_path.stem,
                "fileName": resource_path.name,
                "relativePath": str(resource_path.relative_to(PROJECT_TEMPLATES_DIR)).replace("\\", "/"),
                "source": source,
                "excerpt": text[:1200],
            }
        )

    return resources


@router.post("/note-draft")
async def generate_note_draft(payload: NoteDraftRequest, request: Request):
    try:
        current_user = require_authenticated_user(request)
        if payload.client_id:
            assert_client_access(current_user, payload.client_id)
        result = await documentation_ai_service.generate_note_draft(payload.model_dump())
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to generate documentation draft: %s", exc, exc_info=True)
        try:
            fallback_draft = documentation_ai_service._build_fallback_draft(  # noqa: SLF001 - scoped route fallback
                payload.model_dump(),
                documentation_ai_service._get_recent_note_context(payload.client_id),  # noqa: SLF001
            )
            review = documentation_ai_service.compliance_review({
                "draft": fallback_draft,
                "note_kind": payload.note_kind,
                "context": payload.context,
            })
            return {
                "success": True,
                "draft": fallback_draft,
                "source": "route_fallback",
                "template_excerpt": (payload.current_text or "").strip(),
                "compliance_preview": review,
                "suggested_tasks": documentation_ai_service._build_suggested_tasks(  # noqa: SLF001
                    payload.model_dump(),
                    fallback_draft,
                    review,
                ),
            }
        except Exception as fallback_exc:
            logger.error("Documentation draft fallback also failed: %s", fallback_exc, exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to generate documentation draft") from exc


@router.post("/compliance-review")
async def compliance_review(payload: ComplianceReviewRequest, request: Request):
    try:
        require_authenticated_user(request)
        result = documentation_ai_service.compliance_review(payload.model_dump())
        return {"success": True, **result}
    except Exception as exc:
        logger.error("Failed to review documentation compliance: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to review documentation compliance") from exc


@router.post("/treatment-plan-suggestions")
async def treatment_plan_suggestions(payload: TreatmentPlanSuggestionRequest, request: Request):
    try:
        current_user = require_authenticated_user(request)
        if payload.client_id:
            assert_client_access(current_user, payload.client_id)
        result = documentation_ai_service.generate_treatment_plan_suggestions(payload.model_dump())
        return {"success": True, **result}
    except Exception as exc:
        logger.error("Failed to generate treatment plan suggestions: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate treatment plan suggestions") from exc


@router.post("/group-note")
async def generate_group_note(payload: GroupNoteRequest, request: Request):
    try:
        current_user = require_authenticated_user(request)
        if payload.client_id:
            assert_client_access(current_user, payload.client_id)
        result = await documentation_ai_service.generate_group_note(payload.model_dump())
        return {"success": True, **result}
    except Exception as exc:
        logger.error("Failed to generate group note: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate group note") from exc


@router.post("/follow-up-task")
async def create_follow_up_task(payload: FollowUpTaskRequest, request: Request):
    try:
        current_user = require_authenticated_user(request)
        assert_client_access(current_user, payload.client_id)
        task = documentation_ai_service.create_follow_up_task(payload.client_id, payload.model_dump())
        return {"success": True, "task": task}
    except Exception as exc:
        logger.error("Failed to create documentation follow-up task: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create documentation follow-up task") from exc


@router.get("/templates")
async def list_documentation_templates(request: Request):
    try:
        require_authenticated_user(request)
        templates = _load_document_templates()
        references = _load_reference_files(REFERENCE_LIBRARY_DIR, "reference")
        instructions = _load_reference_files(AI_INSTRUCTIONS_DIR, "instruction")
        return {
            "success": True,
            "templates": templates,
            "reference_library": references,
            "ai_instructions": instructions,
        }
    except Exception as exc:
        logger.error("Failed to load documentation templates: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load documentation templates") from exc


@router.get("/brand-resources")
async def list_brand_resources(request: Request):
    try:
        current_user = require_authenticated_user(request)
        resources = workspace_store.list_brand_resources(current_user.case_manager_id)
        return {"success": True, "resources": resources}
    except Exception as exc:
        logger.error("Failed to list brand resources: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list brand resources") from exc


@router.post("/brand-resources/upload")
async def upload_brand_resource(
    request: Request,
    file: UploadFile = File(...),
    category: str = Form("general"),
    description: str = Form(""),
):
    current_user = require_authenticated_user(request)
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
            case_manager_id=current_user.case_manager_id,
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
async def download_brand_resource(resource_id: str, request: Request):
    current_user = require_authenticated_user(request)
    resource = workspace_store.get_brand_resource(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Brand resource not found")
    if resource.get("case_manager_id") != current_user.case_manager_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

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
async def delete_brand_resource(resource_id: str, request: Request):
    current_user = require_authenticated_user(request)
    resource = workspace_store.get_brand_resource(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Brand resource not found")
    if resource.get("case_manager_id") != current_user.case_manager_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    file_path = BRAND_UPLOADS_DIR / resource["file_path"]
    try:
        workspace_store.delete_brand_resource(resource_id)
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        return {"success": True, "message": "Brand resource deleted"}
    except Exception as exc:
        logger.error("Failed to delete brand resource: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to delete brand resource") from exc
