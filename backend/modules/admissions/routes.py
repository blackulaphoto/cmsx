import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from backend.auth.authorization import effective_case_manager_id
from backend.auth.service import require_authenticated_user

from .database import admissions_store
from .extractor import extract_admissions_data
from .models import (
    ALLOWED_FORM_STATUSES,
    ALLOWED_REVIEW_STATUSES,
    RecordTaskKeyPayload,
    SaveResponsePayload,
    StartPacketPayload,
    UpdateFinancialCoordinationPayload,
    UpdateFormStatusPayload,
    UpdateReviewPayload,
)
from .summary import build_operational_summary
from .template_parser import parse_template

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admissions", tags=["admissions"])

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ADMISSIONS_UPLOADS = _PROJECT_ROOT / "uploads" / "admissions"
_MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10 MB

_ALLOWED_ATTACHMENT_TYPES = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".jpg", ".jpeg", ".png", ".gif", ".tiff",
    ".txt", ".csv",
}


# ── Templates ─────────────────────────────────────────────────────────────────

@router.get("/templates")
async def get_templates(request: Request):
    require_authenticated_user(request)
    templates = admissions_store.get_templates()
    return {"success": True, "templates": templates, "total": len(templates)}


@router.get("/templates/{form_key}")
async def get_template(form_key: str, request: Request):
    require_authenticated_user(request)
    template = parse_template(form_key)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{form_key}' not found")
    return {"success": True, "template": template}


# ── Packets ────────────────────────────────────────────────────────────────────

@router.post("/packets")
async def start_or_get_packet(payload: StartPacketPayload, request: Request):
    current_user = require_authenticated_user(request)
    case_manager_id = effective_case_manager_id(current_user, None) or current_user.case_manager_id
    try:
        packet = admissions_store.get_or_create_packet(
            client_id=payload.client_id,
            client_name=payload.client_name,
            case_manager_id=case_manager_id,
        )
        return {"success": True, "packet": packet}
    except Exception as exc:
        logger.exception(f"[ADMISSIONS] Failed to create/get packet for {payload.client_id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to create admissions packet")


@router.get("/packets/{client_id}/operational-summary")
async def get_operational_summary(client_id: str, request: Request):
    """Return operational summary including flags, suggested tasks, and created_task_keys."""
    require_authenticated_user(request)
    summary = build_operational_summary(client_id)
    return {"success": True, "summary": summary}


@router.get("/packets/{client_id}/task-keys")
async def get_task_keys(client_id: str, request: Request):
    """Return task_keys that have already been added to Smart Daily for this client."""
    require_authenticated_user(request)
    keys = admissions_store.get_created_task_keys(client_id)
    return {"success": True, "task_keys": keys}


@router.post("/packets/{client_id}/task-keys")
async def record_task_key(client_id: str, payload: RecordTaskKeyPayload, request: Request):
    """Record that a suggested task was added to Smart Daily. Idempotent."""
    require_authenticated_user(request)
    admissions_store.record_task_key(
        client_id=client_id,
        task_key=payload.task_key,
        reminder_id=payload.reminder_id,
        case_manager_id=payload.case_manager_id,
    )
    return {"success": True}


@router.get("/packets/{client_id}/financial-coordination")
async def get_financial_coordination(client_id: str, request: Request):
    """Return financial coordination record, creating defaults on first access.
    Prefills payer fields from face sheet / financial agreement if still empty."""
    require_authenticated_user(request)
    fc = admissions_store.get_financial_coordination(client_id)
    needs_prefill = not fc.get("primary_payer_type") and not fc.get("primary_plan_name")
    if needs_prefill:
        packet = admissions_store.get_packet_by_client(client_id)
        if packet:
            try:
                extracted = extract_admissions_data(packet["id"], admissions_store)
                fs = extracted.get("face_sheet", {})
                fin = extracted.get("financial", {})
                prefill: dict = {}
                if not fc.get("primary_payer_type"):
                    v = fs.get("payer_type") or fin.get("payer_type")
                    if v:
                        prefill["primary_payer_type"] = v
                if not fc.get("primary_plan_name"):
                    v = fs.get("plan_name") or fin.get("plan_name")
                    if v:
                        prefill["primary_plan_name"] = v
                if not fc.get("primary_member_id"):
                    v = fs.get("member_id") or fin.get("member_id")
                    if v:
                        prefill["primary_member_id"] = v
                if not fc.get("payment_arrangement_type"):
                    v = fin.get("payment_arrangement_type")
                    if v:
                        prefill["payment_arrangement_type"] = v
                if prefill:
                    fc = admissions_store.upsert_financial_coordination(
                        client_id, packet.get("id", ""), prefill
                    )
            except Exception as exc:
                logger.warning(f"[ADMISSIONS] FC prefill skipped for {client_id}: {exc}")
    return {"success": True, "financial_coordination": fc}


@router.put("/packets/{client_id}/financial-coordination")
async def update_financial_coordination(
    client_id: str, payload: UpdateFinancialCoordinationPayload, request: Request
):
    """Partial-update financial coordination. Only explicitly provided fields are saved."""
    require_authenticated_user(request)
    packet = admissions_store.get_packet_by_client(client_id)
    packet_id = packet["id"] if packet else ""
    fields = payload.model_dump(exclude_unset=True)
    fc = admissions_store.upsert_financial_coordination(client_id, packet_id, fields)
    return {"success": True, "financial_coordination": fc}


@router.get("/packets/{client_id}")
async def get_packet_by_client(client_id: str, request: Request):
    require_authenticated_user(request)
    packet = admissions_store.get_packet_by_client(client_id)
    if not packet:
        raise HTTPException(status_code=404, detail="No admissions packet found for this client")
    return {"success": True, "packet": packet}


# ── Form status ────────────────────────────────────────────────────────────────

@router.patch("/packets/{packet_id}/forms/{form_key}/status")
async def update_form_status(
    packet_id: str,
    form_key: str,
    payload: UpdateFormStatusPayload,
    request: Request,
):
    require_authenticated_user(request)
    if payload.status not in ALLOWED_FORM_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{payload.status}'. Allowed: {sorted(ALLOWED_FORM_STATUSES)}",
        )
    updated = admissions_store.update_form_status(
        packet_id=packet_id,
        form_key=form_key,
        status=payload.status,
        notes=payload.notes,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Form not found in this packet")

    refreshed_packet = admissions_store.get_packet_by_id(packet_id)
    progress = refreshed_packet.get("progress_percent") if refreshed_packet else None

    return {"success": True, "form": updated, "progress_percent": progress}


# ── Form response ──────────────────────────────────────────────────────────────

@router.get("/packets/{packet_id}/forms/{form_key}/response")
async def get_form_response(packet_id: str, form_key: str, request: Request):
    require_authenticated_user(request)
    response = admissions_store.get_form_response(packet_id, form_key)
    return {
        "success": True,
        "response": response or {
            "packet_id": packet_id,
            "form_key": form_key,
            "response_data": {},
        },
    }


@router.put("/packets/{packet_id}/forms/{form_key}/response")
async def save_form_response(
    packet_id: str,
    form_key: str,
    payload: SaveResponsePayload,
    request: Request,
):
    require_authenticated_user(request)
    packet = admissions_store.get_packet_by_id(packet_id)
    if not packet:
        raise HTTPException(status_code=404, detail="Packet not found")
    try:
        saved = admissions_store.save_form_response(packet_id, form_key, payload.response_data)
        return {"success": True, "response": saved}
    except Exception as exc:
        logger.exception(f"[ADMISSIONS] Failed to save response {packet_id}/{form_key}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to save form response")


# ── Staff review ───────────────────────────────────────────────────────────────

@router.patch("/packets/{packet_id}/forms/{form_key}/review")
async def update_form_review(
    packet_id: str,
    form_key: str,
    payload: UpdateReviewPayload,
    request: Request,
):
    require_authenticated_user(request)
    if payload.review_status not in ALLOWED_REVIEW_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid review_status '{payload.review_status}'. Allowed: {sorted(ALLOWED_REVIEW_STATUSES)}",
        )
    updated = admissions_store.update_form_review(
        packet_id=packet_id,
        form_key=form_key,
        review_status=payload.review_status,
        review_notes=payload.review_notes,
        reviewed_by=payload.reviewed_by,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Form not found in this packet")
    return {"success": True, "form": updated}


# ── Attachments ────────────────────────────────────────────────────────────────

@router.get("/packets/{packet_id}/forms/{form_key}/attachments")
async def list_attachments(packet_id: str, form_key: str, request: Request):
    require_authenticated_user(request)
    attachments = admissions_store.get_attachments(packet_id, form_key)
    return {"success": True, "attachments": attachments}


@router.post("/packets/{packet_id}/forms/{form_key}/attachments")
async def upload_attachment(
    packet_id: str,
    form_key: str,
    request: Request,
    file: UploadFile = File(...),
):
    current_user = require_authenticated_user(request)

    packet = admissions_store.get_packet_by_id(packet_id)
    if not packet:
        raise HTTPException(status_code=404, detail="Packet not found")

    # Verify form allows attachments
    form_entry = next(
        (f for f in packet.get("forms", []) if f["form_key"] == form_key), None
    )
    if not form_entry:
        raise HTTPException(status_code=404, detail="Form not found in packet")
    if not form_entry.get("allow_attachments"):
        raise HTTPException(status_code=400, detail="This form does not allow attachments")

    # Validate file extension
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in _ALLOWED_ATTACHMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file_ext}' not allowed. Allowed: {sorted(_ALLOWED_ATTACHMENT_TYPES)}",
        )

    # Read and size-check
    contents = await file.read()
    if len(contents) > _MAX_ATTACHMENT_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds 10 MB limit ({len(contents) // 1024 // 1024} MB uploaded)",
        )

    # Save to disk
    dest_dir = _ADMISSIONS_UPLOADS / packet_id / form_key
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4()}{file_ext}"
    dest_path = dest_dir / safe_name
    try:
        dest_path.write_bytes(contents)
    except Exception as exc:
        logger.exception(f"[ADMISSIONS] Failed to write attachment: {exc}")
        raise HTTPException(status_code=500, detail="Failed to save attachment file")

    # Record in DB (store relative path so it's portable)
    storage_path = str(Path("uploads") / "admissions" / packet_id / form_key / safe_name)
    uploaded_by = getattr(current_user, "case_manager_id", "") or getattr(current_user, "uid", "")

    attachment = admissions_store.add_attachment(
        packet_id=packet_id,
        form_key=form_key,
        client_id=packet["client_id"],
        file_name=file.filename or safe_name,
        file_type=file.content_type or "",
        file_size=len(contents),
        storage_path=storage_path,
        uploaded_by=uploaded_by,
    )
    return {"success": True, "attachment": attachment}


@router.delete("/attachments/{attachment_id}")
async def delete_attachment(attachment_id: str, request: Request):
    require_authenticated_user(request)
    att = admissions_store.get_attachment_by_id(attachment_id)
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Remove file from disk (non-fatal if missing)
    try:
        full_path = _PROJECT_ROOT / att["storage_path"]
        if full_path.exists():
            full_path.unlink()
    except Exception as exc:
        logger.warning(f"[ADMISSIONS] Could not delete attachment file: {exc}")

    deleted = admissions_store.delete_attachment(attachment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return {"success": True}


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(attachment_id: str, request: Request):
    require_authenticated_user(request)
    att = admissions_store.get_attachment_by_id(attachment_id)
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")

    full_path = _PROJECT_ROOT / att["storage_path"]
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Attachment file not found on server")

    return FileResponse(
        path=str(full_path),
        filename=att["file_name"],
        media_type=att.get("file_type") or "application/octet-stream",
    )
