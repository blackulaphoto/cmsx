import logging
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from backend.api.clients import (
    build_client_sync_payload,
    ensure_core_clients_schema,
    get_database_connection,
    normalize_client_record,
    propagate_client_to_modules,
)
from backend.auth.authorization import effective_case_manager_id
from backend.auth.service import require_authenticated_user
from backend.shared.database.railway_postgres import upsert_client_to_postgres

from .database import _resolve_attachment_path
from .store_factory import admissions_store
from .extractor import extract_admissions_data
from .models import (
    ALLOWED_FORM_STATUSES,
    ALLOWED_REVIEW_STATUSES,
    ALLOWED_SUPPRESSION_STATUSES,
    RecordTaskKeyPayload,
    SaveResponsePayload,
    StartPacketPayload,
    SuppressTaskPayload,
    UpdateFinancialCoordinationPayload,
    UpdateFormStatusPayload,
    UpdateReviewPayload,
)
from .profile import (
    apply_profile_defaults,
    build_shared_profile,
    build_shared_profile_from_client,
    extract_profile_updates,
    merge_shared_profile,
)
from .summary import build_operational_summary, bust_summary_cache
from .template_parser import parse_template

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admissions", tags=["admissions"])

_PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Storage backend: Railway volume > env override > default
_RAILWAY_VOLUME = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
_UPLOAD_DIR_ENV = os.environ.get("ADMISSIONS_UPLOAD_DIR")
if _RAILWAY_VOLUME:
    _ADMISSIONS_UPLOADS = Path(_RAILWAY_VOLUME) / "admissions"
elif _UPLOAD_DIR_ENV:
    _ADMISSIONS_UPLOADS = Path(_UPLOAD_DIR_ENV)
else:
    _ADMISSIONS_UPLOADS = _PROJECT_ROOT / "uploads" / "admissions"

_MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10 MB

_ALLOWED_ATTACHMENT_TYPES = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".jpg", ".jpeg", ".png", ".gif", ".tiff",
    ".txt", ".csv",
}


def _load_client_shared_profile(client_id: str) -> dict:
    try:
        with get_database_connection("core_clients", "READ_ONLY") as conn:
            ensure_core_clients_schema(conn)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
            row = cursor.fetchone()
    except Exception as exc:
        logger.warning("[ADMISSIONS] could not load client profile seed for %s: %s", client_id, exc)
        return {}
    if row is None:
        return {}
    return build_shared_profile_from_client(normalize_client_record(row))


def _sync_packet_profile_to_client(client_id: str, shared_profile: dict) -> None:
    client_updates = {
        "first_name": shared_profile.get("first_name"),
        "last_name": shared_profile.get("last_name"),
        "date_of_birth": shared_profile.get("date_of_birth"),
        "phone": shared_profile.get("phone"),
        "email": shared_profile.get("email"),
        "address": shared_profile.get("address"),
        "city": shared_profile.get("city"),
        "state": shared_profile.get("state"),
        "zip_code": shared_profile.get("zip"),
        "emergency_contact_name": shared_profile.get("emergency_contact_name"),
        "emergency_contact_phone": shared_profile.get("emergency_contact_phone"),
        "emergency_contact_relationship": shared_profile.get("emergency_contact_relationship"),
        "program_type": shared_profile.get("program"),
        "intake_date": shared_profile.get("admission_date"),
    }
    client_updates = {key: value for key, value in client_updates.items() if value not in (None, "")}
    if not client_updates:
        return

    with get_database_connection("core_clients", "ADMIN") as conn:
        ensure_core_clients_schema(conn)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
        existing = cursor.fetchone()
        if existing is None:
            return

        client_updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{column} = ?" for column in client_updates.keys())
        cursor.execute(
            f"UPDATE clients SET {set_clause} WHERE client_id = ?",
            [*client_updates.values(), client_id],
        )
        conn.commit()

    with get_database_connection("core_clients", "READ_ONLY") as conn:
        ensure_core_clients_schema(conn)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
        updated_row = cursor.fetchone()

    if updated_row is None:
        return
    normalized_client = normalize_client_record(updated_row)
    client_sync_payload = build_client_sync_payload(normalized_client)
    integration_results = propagate_client_to_modules(client_id, client_sync_payload)
    upsert_client_to_postgres(client_data=client_sync_payload, integration_results=integration_results)


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
        shared_profile = merge_shared_profile(
            _load_client_shared_profile(payload.client_id),
            build_shared_profile(payload.shared_profile),
        )
        packet = admissions_store.get_or_create_packet(
            client_id=payload.client_id,
            client_name=shared_profile.get("full_name") or payload.client_name,
            case_manager_id=case_manager_id,
            shared_profile=shared_profile,
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


@router.post("/packets/{client_id}/task-suppressions")
async def suppress_task(client_id: str, payload: SuppressTaskPayload, request: Request):
    """Dismiss or mark a suggested task as not-applicable. Idempotent."""
    require_authenticated_user(request)
    if payload.status not in ALLOWED_SUPPRESSION_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{payload.status}'. Allowed: {sorted(ALLOWED_SUPPRESSION_STATUSES)}",
        )
    admissions_store.suppress_task(
        client_id=client_id,
        task_key=payload.task_key,
        status=payload.status,
        reason=payload.reason,
        dismissed_by=payload.dismissed_by,
    )
    bust_summary_cache(client_id)
    return {"success": True}


@router.get("/packets/{client_id}/financial-coordination")
async def get_financial_coordination(client_id: str, request: Request):
    """Return financial coordination record. Never creates a DB record (read-only).
    Prefills payer fields in-memory from face sheet / financial agreement if still empty."""
    require_authenticated_user(request)
    fc = admissions_store.get_financial_coordination_readonly(client_id)
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
                    fc = {**fc, **prefill}
            except Exception as exc:
                logger.warning(f"[ADMISSIONS] FC prefill skipped for {client_id}: {exc}")
    recent_events = admissions_store.get_recent_fc_events(client_id)
    return {"success": True, "financial_coordination": fc, "recent_events": recent_events}


@router.put("/packets/{client_id}/financial-coordination")
async def update_financial_coordination(
    client_id: str, payload: UpdateFinancialCoordinationPayload, request: Request
):
    """Partial-update financial coordination. Only explicitly provided fields are saved."""
    current_user = require_authenticated_user(request)
    packet = admissions_store.get_packet_by_client(client_id)
    packet_id = packet["id"] if packet else ""
    fields = payload.model_dump(exclude_unset=True)
    changed_by = (
        getattr(current_user, "case_manager_id", "") or getattr(current_user, "uid", "")
    )
    fc = admissions_store.upsert_financial_coordination(client_id, packet_id, fields, changed_by=changed_by)
    bust_summary_cache(client_id)
    return {"success": True, "financial_coordination": fc}


@router.get("/packets/{client_id}")
async def get_packet_by_client(client_id: str, request: Request):
    require_authenticated_user(request)
    packet = admissions_store.get_packet_by_client(client_id)
    if not packet:
        raise HTTPException(status_code=404, detail="No admissions packet found for this client")
    # If the packet's shared_profile is empty, seed it from the client record.
    # This handles packets created before the autofill feature was deployed.
    if not any(v for v in (packet.get("shared_profile") or {}).values() if v):
        seed = _load_client_shared_profile(client_id)
        if seed and any(v for v in seed.values() if v):
            try:
                updated = admissions_store.update_packet_profile(packet["id"], seed)
                if updated:
                    packet = updated
            except Exception as exc:
                logger.warning("[ADMISSIONS] could not seed empty shared_profile for %s: %s", client_id, exc)
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
    if refreshed_packet:
        bust_summary_cache(refreshed_packet.get("client_id", ""))

    return {"success": True, "form": updated, "progress_percent": progress}


# ── Form response ──────────────────────────────────────────────────────────────

@router.get("/packets/{packet_id}/forms/{form_key}/response")
async def get_form_response(packet_id: str, form_key: str, request: Request):
    require_authenticated_user(request)
    packet = admissions_store.get_packet_by_id(packet_id)
    if not packet:
        raise HTTPException(status_code=404, detail="Packet not found")
    response = admissions_store.get_form_response(packet_id, form_key)
    response_data = apply_profile_defaults(
        (response or {}).get("response_data") or {},
        packet.get("shared_profile") or {},
    )
    response_payload = response or {
        "packet_id": packet_id,
        "form_key": form_key,
        "response_data": {},
    }
    response_payload["response_data"] = response_data
    return {
        "success": True,
        "response": response_payload,
        "shared_profile": packet.get("shared_profile") or {},
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
        profile_updates = extract_profile_updates(form_key, payload.response_data)
        shared_profile = merge_shared_profile(packet.get("shared_profile") or {}, profile_updates)
        if shared_profile != (packet.get("shared_profile") or {}):
            packet = admissions_store.update_packet_profile(packet_id, shared_profile) or packet
            if packet.get("client_id"):
                try:
                    _sync_packet_profile_to_client(packet["client_id"], shared_profile)
                except Exception as exc:
                    logger.warning("[ADMISSIONS] client profile sync skipped for %s: %s", packet["client_id"], exc)
        bust_summary_cache(packet.get("client_id", ""))
        effective_response = apply_profile_defaults(
            saved.get("response_data") or {},
            (packet.get("shared_profile") or shared_profile),
        )
        saved["response_data"] = effective_response
        return {
            "success": True,
            "response": saved,
            "shared_profile": packet.get("shared_profile") or shared_profile,
        }
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
    packet_for_bust = admissions_store.get_packet_by_id(packet_id)
    if packet_for_bust:
        bust_summary_cache(packet_for_bust.get("client_id", ""))
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

    # Store path relative to _ADMISSIONS_UPLOADS so Railway Volume moves don't break reads
    storage_path = str(Path(packet_id) / form_key / safe_name)
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
        full_path = _resolve_attachment_path(att["storage_path"])
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

    full_path = _resolve_attachment_path(att["storage_path"])
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Attachment file not found on server")

    return FileResponse(
        path=str(full_path),
        filename=att["file_name"],
        media_type=att.get("file_type") or "application/octet-stream",
    )
