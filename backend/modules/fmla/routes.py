import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.auth.authorization import assert_client_access, effective_case_manager_id, get_client_org_id
from backend.auth.service import require_authenticated_user
from backend.shared.tenancy import multi_tenant_enabled, resolve_org_id

from .export_service import build_packet_pdf, generate_employer_safe_packet
from .store_factory import get_fmla_store


router = APIRouter(tags=["fmla"])
store = get_fmla_store()
logger = logging.getLogger(__name__)
FMLA_UPLOADS_DIR = Path(__file__).resolve().parents[3] / "uploads" / "fmla"
FMLA_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


class FMLACasePayload(BaseModel):
    case_subject_type: str = "client"
    client_id: Optional[str] = ""
    client_name: str = Field(..., min_length=1)
    staff_identifier: Optional[str] = ""
    staff_name: Optional[str] = ""
    staff_department: Optional[str] = ""
    staff_job_title: Optional[str] = ""
    date_of_birth: Optional[str] = ""
    assigned_case_manager: str = "cm_001"
    treatment_status: Optional[str] = ""
    employer_name: Optional[str] = ""
    hr_contact_name: Optional[str] = ""
    hr_phone: Optional[str] = ""
    hr_email: Optional[str] = ""
    employer_fax: Optional[str] = ""
    employer_address: Optional[str] = ""
    preferred_communication_method: Optional[str] = ""
    provider_name: Optional[str] = ""
    clinic_name: Optional[str] = ""
    provider_phone: Optional[str] = ""
    provider_fax: Optional[str] = ""
    provider_email: Optional[str] = ""
    provider_address: Optional[str] = ""
    roi_status: Optional[str] = ""
    fmla_request_type: str = "new request"
    leave_type: str = "continuous"
    leave_start_date: Optional[str] = ""
    leave_end_date: Optional[str] = ""
    expected_return_date: Optional[str] = ""
    employer_response_deadline: Optional[str] = ""
    certification_expiration_date: Optional[str] = ""
    return_to_work_date: Optional[str] = ""
    paperwork_deadline: Optional[str] = ""
    paperwork_received_date: Optional[str] = ""
    paperwork_completed_date: Optional[str] = ""
    paperwork_sent_date: Optional[str] = ""
    paperwork_sent_method: Optional[str] = ""
    confirmation_received: bool = False
    approval_status: str = "pending"
    status: str = "draft"
    notes: Optional[str] = ""
    internal_comments: Optional[str] = ""


class FMLADocumentPayload(BaseModel):
    batch_id: Optional[str] = ""
    batch_name: Optional[str] = ""
    document_type: str = "other"
    document_status: str = "needed"
    file_name: Optional[str] = ""
    file_path: Optional[str] = ""
    file_size: int = 0
    content_type: Optional[str] = ""
    date_requested: Optional[str] = ""
    date_received: Optional[str] = ""
    date_completed: Optional[str] = ""
    date_sent: Optional[str] = ""
    sent_to: Optional[str] = ""
    sent_by: Optional[str] = ""
    confirmation_number: Optional[str] = ""
    notes: Optional[str] = ""


class FMLACorrespondencePayload(BaseModel):
    correspondence_at: Optional[str] = ""
    contact_type: str = "phone"
    person_contacted: Optional[str] = ""
    organization: Optional[str] = ""
    contact_information: Optional[str] = ""
    summary: str
    outcome: Optional[str] = ""
    next_step_needed: Optional[str] = ""
    follow_up_date: Optional[str] = ""
    staff_member: Optional[str] = "cm_001"


class FMLAReminderPayload(BaseModel):
    reminder_text: str
    due_date: str
    priority: str = "Medium"
    case_manager_id: Optional[str] = "cm_001"
    reason: Optional[str] = ""


class FMLALeaveUsagePayload(BaseModel):
    usage_date: str
    duration_minutes: int = Field(..., ge=1)
    reason_category: str = "other"
    notes: Optional[str] = ""


class FMLAExportDraftPayload(BaseModel):
    export_type: str = "employer packet"
    custom_instructions: Optional[str] = ""
    draft_title: Optional[str] = ""
    draft_content: Optional[str] = ""
    review_notes: Optional[str] = ""


def _case_subject_type(case_record: Dict[str, Any]) -> str:
    return (case_record.get("case_subject_type") or "client").strip().lower()


def _authorize_case_access(request: Request, case_record: Dict[str, Any]):
    current_user = require_authenticated_user(request)
    if _case_subject_type(case_record) == "staff":
        if multi_tenant_enabled() and case_record.get("org_id") != resolve_org_id(current_user):
            raise HTTPException(status_code=404, detail="FMLA case not found")
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Staff FMLA records require admin access")
        return current_user

    if case_record.get("client_id"):
        assert_client_access(current_user, case_record["client_id"])
    elif multi_tenant_enabled() and case_record.get("org_id") != resolve_org_id(current_user):
        raise HTTPException(status_code=404, detail="FMLA case not found")
    elif not current_user.is_admin and case_record.get("assigned_case_manager") != current_user.case_manager_id:
        raise HTTPException(status_code=403, detail="Access denied to this FMLA case")
    return current_user


def _authorize_case_payload(request: Request, payload: FMLACasePayload):
    current_user = require_authenticated_user(request)
    subject_type = (payload.case_subject_type or "client").strip().lower()
    if subject_type == "staff":
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Staff FMLA records require admin access")
        return current_user
    if payload.client_id:
        assert_client_access(current_user, payload.client_id)
    return current_user


def _org_for_new_case(current_user, payload: Dict[str, Any]) -> str:
    client_org = get_client_org_id(payload.get("client_id") or "")
    if client_org:
        return client_org
    return resolve_org_id(current_user)


def _audit(case_id: Optional[str], action: str, current_user, metadata: Optional[Dict[str, Any]] = None):
    store.log_audit(
        action=action,
        case_id=case_id,
        actor_case_manager_id=current_user.case_manager_id,
        actor_name=current_user.full_name,
        metadata=metadata or {},
    )


def _safe_case_path(case_id: str) -> Path:
    safe_case_id = "".join(char for char in case_id if char.isalnum() or char in {"-", "_"})
    case_upload_dir = FMLA_UPLOADS_DIR / safe_case_id
    case_upload_dir.mkdir(parents=True, exist_ok=True)
    return case_upload_dir


@router.get("/fmla")
async def list_fmla_cases(
    request: Request,
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    employer: Optional[str] = Query(None),
    deadline: Optional[str] = Query(None),
    case_manager: Optional[str] = Query(None),
    case_subject_type: Optional[str] = Query(None),
):
    current_user = require_authenticated_user(request)
    requested_subject = (case_subject_type or "").strip().lower()
    if requested_subject == "staff" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Staff FMLA records require admin access")
    cases = store.list_cases(
        {
            "search": search,
            "status": status,
            "employer": employer,
            "deadline": deadline,
            "case_subject_type": case_subject_type,
            "case_manager": effective_case_manager_id(current_user, case_manager),
            "org_id": resolve_org_id(current_user) if multi_tenant_enabled() else None,
        }
    )
    if not current_user.is_admin:
        cases = [item for item in cases if _case_subject_type(item) != "staff"]
    return {"success": True, "cases": cases, "total_count": len(cases)}


@router.get("/fmla/summary")
async def get_fmla_summary(request: Request, case_manager_id: Optional[str] = Query(None)):
    current_user = require_authenticated_user(request)
    summary = store.get_summary(
        effective_case_manager_id(current_user, case_manager_id),
        resolve_org_id(current_user) if multi_tenant_enabled() else None,
    )
    if not current_user.is_admin:
        summary["cases"] = [item for item in summary["cases"] if _case_subject_type(item) != "staff"]
    return {"success": True, **summary}


@router.post("/fmla")
async def create_fmla_case(payload: FMLACasePayload, request: Request):
    current_user = _authorize_case_payload(request, payload)
    data = payload.model_dump()
    data["assigned_case_manager"] = current_user.case_manager_id if not current_user.is_admin else (
        payload.assigned_case_manager or current_user.case_manager_id
    )
    data["org_id"] = _org_for_new_case(current_user, data)
    record = store.create_case(data)
    _audit(record["case_id"], "case_created", current_user, {"case_subject_type": record.get("case_subject_type"), "status": record.get("status")})
    return {"success": True, "case": record}


@router.get("/fmla/{case_id}")
async def get_fmla_case(case_id: str, request: Request):
    record = store.get_case(case_id)
    if not record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    _authorize_case_access(request, record)
    documents = store.list_documents(case_id)
    correspondence = store.list_correspondence(case_id)
    reminders = store.list_case_reminders(case_id)
    leave_usage = store.list_leave_usage(case_id)
    leave_usage_summary = store.get_leave_usage_summary(case_id)
    exports = store.list_export_records(case_id)
    audit_log = store.list_audit_logs(case_id)
    return {
        "success": True,
        "case": record,
        "documents": documents,
        "correspondence": correspondence,
        "reminders": reminders,
        "leave_usage": leave_usage,
        "leave_usage_summary": leave_usage_summary,
        "exports": exports,
        "audit_log": audit_log,
    }


@router.put("/fmla/{case_id}")
async def update_fmla_case(case_id: str, payload: FMLACasePayload, request: Request):
    current_user = require_authenticated_user(request)
    existing = store.get_case(case_id)
    if not existing:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    _authorize_case_access(request, existing)
    requested_subject_type = (payload.case_subject_type or existing.get("case_subject_type") or "client").strip().lower()
    if requested_subject_type == "staff" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Staff FMLA records require admin access")
    data = payload.model_dump()
    data["assigned_case_manager"] = current_user.case_manager_id if not current_user.is_admin else (
        payload.assigned_case_manager or existing.get("assigned_case_manager") or current_user.case_manager_id
    )
    record = store.update_case(case_id, data)
    if not record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    _audit(case_id, "case_updated", current_user, {"case_subject_type": record.get("case_subject_type"), "status": record.get("status")})
    return {"success": True, "case": record}


@router.delete("/fmla/{case_id}")
async def delete_fmla_case(case_id: str, request: Request):
    existing = store.get_case(case_id)
    if not existing:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    current_user = _authorize_case_access(request, existing)
    deleted = store.delete_case(case_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    _audit(case_id, "case_deleted", current_user, {"case_subject_type": existing.get("case_subject_type"), "client_name": existing.get("client_name")})
    return {"success": True, "case_id": case_id}


@router.post("/fmla/{case_id}/documents")
async def add_fmla_document(case_id: str, payload: FMLADocumentPayload, request: Request):
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    current_user = _authorize_case_access(request, case_record)
    record = store.create_document(
        case_id,
        {
            **payload.model_dump(),
            "uploader_name": current_user.full_name,
            "uploader_case_manager_id": current_user.case_manager_id,
        },
    )
    _audit(case_id, "document_created", current_user, {"document_type": record.get("document_type"), "status": record.get("document_status")})
    return {"success": True, "document": record}


@router.post("/fmla/{case_id}/documents/upload")
async def upload_fmla_document(
    case_id: str,
    request: Request,
    files: List[UploadFile] = File(...),
    batch_name: str = Form(""),
    document_type: str = Form("other"),
    document_status: str = Form("received"),
    date_requested: str = Form(""),
    date_received: str = Form(""),
    date_completed: str = Form(""),
    date_sent: str = Form(""),
    sent_to: str = Form(""),
    sent_by: str = Form(""),
    confirmation_number: str = Form(""),
    notes: str = Form(""),
):
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    current_user = _authorize_case_access(request, case_record)
    valid_files = [file for file in files if file and file.filename]
    if not valid_files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    case_upload_dir = _safe_case_path(case_id)
    batch_id = uuid4().hex
    packet_name = batch_name.strip() or f"{document_type.title()} packet"

    try:
        created_records = []
        stored_paths: List[Path] = []
        for file in valid_files:
            file_extension = Path(file.filename).suffix
            stored_name = f"{uuid4().hex}{file_extension}"
            stored_path = case_upload_dir / stored_name
            content = await file.read()
            with open(stored_path, "wb") as buffer:
                buffer.write(content)
            stored_paths.append(stored_path)

            safe_case_id = case_upload_dir.name
            relative_path = str(Path(safe_case_id) / stored_name)
            record = store.create_document(
                case_id,
                {
                    "batch_id": batch_id,
                    "batch_name": packet_name,
                    "document_type": document_type,
                    "document_status": document_status,
                    "uploader_name": current_user.full_name,
                    "uploader_case_manager_id": current_user.case_manager_id,
                    "file_name": file.filename,
                    "file_path": relative_path,
                    "file_size": len(content),
                    "content_type": file.content_type or "application/octet-stream",
                    "date_requested": date_requested,
                    "date_received": date_received,
                    "date_completed": date_completed,
                    "date_sent": date_sent,
                    "sent_to": sent_to,
                    "sent_by": sent_by,
                    "confirmation_number": confirmation_number,
                    "notes": notes,
                },
            )
            created_records.append(record)

        _audit(case_id, "document_uploaded", current_user, {"document_type": document_type, "count": len(created_records)})
        return {"success": True, "documents": created_records, "document_count": len(created_records)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error uploading FMLA document: %s", exc)
        for stored_path in locals().get("stored_paths", []):
            if stored_path.exists():
                stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Failed to upload FMLA document") from exc


@router.get("/fmla/{case_id}/documents")
async def get_fmla_documents(case_id: str, request: Request):
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    _authorize_case_access(request, case_record)
    return {"success": True, "documents": store.list_documents(case_id)}


@router.get("/fmla/documents/{document_id}/download")
async def download_fmla_document(document_id: str, request: Request):
    document = store.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="FMLA document not found")
    case_record = store.get_case(document["case_id"])
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    _authorize_case_access(request, case_record)
    if not document.get("file_path"):
        raise HTTPException(status_code=404, detail="No uploaded file is attached to this document")

    file_path = (FMLA_UPLOADS_DIR / document["file_path"]).resolve()
    uploads_root = FMLA_UPLOADS_DIR.resolve()
    try:
        file_path.relative_to(uploads_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid file path") from exc
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Uploaded file not found")

    return FileResponse(
        path=file_path,
        filename=document.get("file_name") or os.path.basename(file_path),
        media_type=document.get("content_type") or "application/octet-stream",
    )


@router.post("/fmla/{case_id}/correspondence")
async def add_fmla_correspondence(case_id: str, payload: FMLACorrespondencePayload, request: Request):
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    current_user = _authorize_case_access(request, case_record)
    data = payload.model_dump()
    data["staff_member"] = current_user.full_name
    record = store.create_correspondence(case_id, data)
    _audit(case_id, "correspondence_created", current_user, {"contact_type": record.get("contact_type")})
    return {"success": True, "correspondence": record}


@router.get("/fmla/{case_id}/correspondence")
async def get_fmla_correspondence(case_id: str, request: Request):
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    _authorize_case_access(request, case_record)
    return {"success": True, "correspondence": store.list_correspondence(case_id)}


@router.post("/fmla/{case_id}/reminders")
async def create_fmla_reminder(case_id: str, payload: FMLAReminderPayload, request: Request):
    try:
        case_record = store.get_case(case_id)
        if not case_record:
            raise HTTPException(status_code=404, detail="FMLA case not found")
        current_user = _authorize_case_access(request, case_record)
        data = payload.model_dump()
        data["case_manager_id"] = current_user.case_manager_id
        reminder = store.create_reminder(case_id, data)
        _audit(case_id, "reminder_created", current_user, {"priority": reminder.get("priority")})
        return {"success": True, "reminder": reminder}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/fmla/{case_id}/reminders")
async def get_fmla_reminders(case_id: str, request: Request):
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    _authorize_case_access(request, case_record)
    return {"success": True, "reminders": store.list_case_reminders(case_id)}


@router.post("/fmla/{case_id}/leave-usage")
async def add_fmla_leave_usage(case_id: str, payload: FMLALeaveUsagePayload, request: Request):
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    current_user = _authorize_case_access(request, case_record)
    record = store.create_leave_usage(case_id, payload.model_dump())
    _audit(case_id, "leave_usage_created", current_user, {"duration_minutes": record.get("duration_minutes"), "reason_category": record.get("reason_category")})
    return {"success": True, "leave_usage": record, "summary": store.get_leave_usage_summary(case_id)}


@router.get("/fmla/{case_id}/leave-usage")
async def get_fmla_leave_usage(case_id: str, request: Request):
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    _authorize_case_access(request, case_record)
    return {"success": True, "leave_usage": store.list_leave_usage(case_id), "summary": store.get_leave_usage_summary(case_id)}


@router.post("/fmla/{case_id}/exports/draft")
async def generate_fmla_export_draft(case_id: str, payload: FMLAExportDraftPayload, request: Request):
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    current_user = _authorize_case_access(request, case_record)
    generated = generate_employer_safe_packet(case_record, payload.custom_instructions or payload.review_notes or "")
    draft = store.create_export_record(
        case_id,
        {
            "export_type": payload.export_type,
            "draft_title": payload.draft_title or generated["draft_title"],
            "draft_content": payload.draft_content or generated["draft_content"],
            "review_notes": payload.review_notes or payload.custom_instructions or "",
            "warning_text": generated["warning_text"],
            "created_by": current_user.full_name,
        },
    )
    _audit(case_id, "export_draft_created", current_user, {"export_type": draft.get("export_type")})
    return {"success": True, "export": draft}


@router.post("/fmla/{case_id}/exports/{export_id}/pdf")
async def export_fmla_packet_pdf(case_id: str, export_id: str, payload: FMLAExportDraftPayload, request: Request):
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    current_user = _authorize_case_access(request, case_record)
    export_record = store.get_export_record(export_id)
    if not export_record or export_record.get("case_id") != case_id:
        raise HTTPException(status_code=404, detail="FMLA export draft not found")

    draft_title = payload.draft_title or export_record.get("draft_title") or "FMLA Employer Packet"
    draft_content = payload.draft_content or export_record.get("draft_content") or ""
    pdf_bytes = build_packet_pdf(draft_title, draft_content)
    safe_filename = store.build_safe_export_filename(case_record, export_record.get("export_type") or payload.export_type)
    export_dir = _safe_case_path(case_id) / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    file_path = export_dir / safe_filename
    with open(file_path, "wb") as buffer:
        buffer.write(pdf_bytes)

    updated = store.update_export_record(
        export_id,
        {
            "draft_title": draft_title,
            "draft_content": draft_content,
            "review_notes": payload.review_notes or export_record.get("review_notes") or "",
            "safe_filename": safe_filename,
            "file_path": str(Path(case_id) / "exports" / safe_filename),
            "content_type": "application/pdf",
            "reviewed_at": store.get_case(case_id).get("updated_at"),
        },
    )
    _audit(case_id, "export_pdf_created", current_user, {"export_type": export_record.get("export_type"), "safe_filename": safe_filename})
    return {"success": True, "export": updated}


@router.get("/fmla/{case_id}/exports")
async def get_fmla_exports(case_id: str, request: Request):
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    _authorize_case_access(request, case_record)
    return {"success": True, "exports": store.list_export_records(case_id)}


@router.get("/fmla/exports/{export_id}/download")
async def download_fmla_export(export_id: str, request: Request):
    export_record = store.get_export_record(export_id)
    if not export_record:
        raise HTTPException(status_code=404, detail="FMLA export not found")
    case_record = store.get_case(export_record["case_id"])
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    _authorize_case_access(request, case_record)
    if not export_record.get("file_path"):
        raise HTTPException(status_code=404, detail="This export has not been finalized to PDF")

    file_path = (FMLA_UPLOADS_DIR / export_record["file_path"]).resolve()
    uploads_root = FMLA_UPLOADS_DIR.resolve()
    try:
        file_path.relative_to(uploads_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid file path") from exc
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Export file not found")

    return FileResponse(
        path=file_path,
        filename=export_record.get("safe_filename") or os.path.basename(file_path),
        media_type=export_record.get("content_type") or "application/pdf",
    )
