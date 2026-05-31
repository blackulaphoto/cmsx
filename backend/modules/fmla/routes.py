import logging
import os
from pathlib import Path
from uuid import uuid4

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .store import FMLAStore
from backend.auth.authorization import assert_client_access, effective_case_manager_id
from backend.auth.service import require_authenticated_user


router = APIRouter(tags=["fmla"])
store = FMLAStore()
logger = logging.getLogger(__name__)
FMLA_UPLOADS_DIR = Path(__file__).resolve().parents[3] / "uploads" / "fmla"
FMLA_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


class FMLACasePayload(BaseModel):
    client_id: Optional[str] = ""
    client_name: str = Field(..., min_length=1)
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
    leave_start_date: Optional[str] = ""
    expected_return_date: Optional[str] = ""
    paperwork_deadline: Optional[str] = ""
    paperwork_received_date: Optional[str] = ""
    paperwork_completed_date: Optional[str] = ""
    paperwork_sent_date: Optional[str] = ""
    paperwork_sent_method: Optional[str] = ""
    confirmation_received: bool = False
    approval_status: str = "pending"
    status: str = "Draft"
    notes: Optional[str] = ""


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


@router.get("/fmla")
async def list_fmla_cases(
    request: Request,
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    employer: Optional[str] = Query(None),
    deadline: Optional[str] = Query(None),
    case_manager: Optional[str] = Query(None),
):
    current_user = require_authenticated_user(request)
    cases = store.list_cases(
        {
            "search": search,
            "status": status,
            "employer": employer,
            "deadline": deadline,
            "case_manager": effective_case_manager_id(current_user, case_manager),
        }
    )
    return {"success": True, "cases": cases, "total_count": len(cases)}


@router.get("/fmla/summary")
async def get_fmla_summary(request: Request, case_manager_id: Optional[str] = Query(None)):
    current_user = require_authenticated_user(request)
    summary = store.get_summary(effective_case_manager_id(current_user, case_manager_id))
    return {"success": True, **summary}


@router.post("/fmla")
async def create_fmla_case(payload: FMLACasePayload, request: Request):
    current_user = require_authenticated_user(request)
    if payload.client_id:
        assert_client_access(current_user, payload.client_id)
    data = payload.model_dump()
    data["assigned_case_manager"] = current_user.case_manager_id if not current_user.is_admin else (
        payload.assigned_case_manager or current_user.case_manager_id
    )
    record = store.create_case(data)
    return {"success": True, "case": record}


@router.get("/fmla/{case_id}")
async def get_fmla_case(case_id: str, request: Request):
    current_user = require_authenticated_user(request)
    record = store.get_case(case_id)
    if not record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    if record.get("client_id"):
        assert_client_access(current_user, record["client_id"])
    elif not current_user.is_admin and record.get("assigned_case_manager") != current_user.case_manager_id:
        raise HTTPException(status_code=403, detail="Access denied to this FMLA case")
    documents = store.list_documents(case_id)
    correspondence = store.list_correspondence(case_id)
    reminders = store.list_case_reminders(case_id)
    return {
        "success": True,
        "case": record,
        "documents": documents,
        "correspondence": correspondence,
        "reminders": reminders,
    }


@router.put("/fmla/{case_id}")
async def update_fmla_case(case_id: str, payload: FMLACasePayload, request: Request):
    current_user = require_authenticated_user(request)
    existing = store.get_case(case_id)
    if not existing:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    if existing.get("client_id"):
        assert_client_access(current_user, existing["client_id"])
    elif not current_user.is_admin and existing.get("assigned_case_manager") != current_user.case_manager_id:
        raise HTTPException(status_code=403, detail="Access denied to this FMLA case")
    data = payload.model_dump()
    data["assigned_case_manager"] = current_user.case_manager_id if not current_user.is_admin else (
        payload.assigned_case_manager or existing.get("assigned_case_manager") or current_user.case_manager_id
    )
    record = store.update_case(case_id, data)
    if not record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    return {"success": True, "case": record}


@router.post("/fmla/{case_id}/documents")
async def add_fmla_document(case_id: str, payload: FMLADocumentPayload, request: Request):
    current_user = require_authenticated_user(request)
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    if case_record.get("client_id"):
        assert_client_access(current_user, case_record["client_id"])
    record = store.create_document(case_id, payload.model_dump())
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
    current_user = require_authenticated_user(request)
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    if case_record.get("client_id"):
        assert_client_access(current_user, case_record["client_id"])
    valid_files = [file for file in files if file and file.filename]
    if not valid_files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    safe_case_id = "".join(char for char in case_id if char.isalnum() or char in {"-", "_"})
    case_upload_dir = FMLA_UPLOADS_DIR / safe_case_id
    case_upload_dir.mkdir(parents=True, exist_ok=True)
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

            relative_path = str(Path(safe_case_id) / stored_name)
            record = store.create_document(
                case_id,
                {
                    "batch_id": batch_id,
                    "batch_name": packet_name,
                    "document_type": document_type,
                    "document_status": document_status,
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

        return {
            "success": True,
            "documents": created_records,
            "document_count": len(created_records),
        }
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
    current_user = require_authenticated_user(request)
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    if case_record.get("client_id"):
        assert_client_access(current_user, case_record["client_id"])
    return {"success": True, "documents": store.list_documents(case_id)}


@router.get("/fmla/documents/{document_id}/download")
async def download_fmla_document(document_id: str, request: Request):
    current_user = require_authenticated_user(request)
    document = store.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="FMLA document not found")
    case_record = store.get_case(document["case_id"])
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    if case_record.get("client_id"):
        assert_client_access(current_user, case_record["client_id"])
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
    current_user = require_authenticated_user(request)
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    if case_record.get("client_id"):
        assert_client_access(current_user, case_record["client_id"])
    data = payload.model_dump()
    data["staff_member"] = current_user.full_name
    record = store.create_correspondence(case_id, data)
    return {"success": True, "correspondence": record}


@router.get("/fmla/{case_id}/correspondence")
async def get_fmla_correspondence(case_id: str, request: Request):
    current_user = require_authenticated_user(request)
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    if case_record.get("client_id"):
        assert_client_access(current_user, case_record["client_id"])
    return {"success": True, "correspondence": store.list_correspondence(case_id)}


@router.post("/fmla/{case_id}/reminders")
async def create_fmla_reminder(case_id: str, payload: FMLAReminderPayload, request: Request):
    try:
        current_user = require_authenticated_user(request)
        case_record = store.get_case(case_id)
        if not case_record:
            raise HTTPException(status_code=404, detail="FMLA case not found")
        if case_record.get("client_id"):
            assert_client_access(current_user, case_record["client_id"])
        data = payload.model_dump()
        data["case_manager_id"] = current_user.case_manager_id
        reminder = store.create_reminder(case_id, data)
        return {"success": True, "reminder": reminder}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/fmla/{case_id}/reminders")
async def get_fmla_reminders(case_id: str, request: Request):
    current_user = require_authenticated_user(request)
    case_record = store.get_case(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="FMLA case not found")
    if case_record.get("client_id"):
        assert_client_access(current_user, case_record["client_id"])
    return {"success": True, "reminders": store.list_case_reminders(case_id)}
