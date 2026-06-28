from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.auth.authorization import assert_client_access, effective_case_manager_id, get_client_org_id
from backend.auth.service import require_authenticated_user
from backend.shared.tenancy import multi_tenant_enabled, resolve_org_id

from .postgres_store import ALLOWED_UR_EVENT_TYPES, ALLOWED_UR_STATUSES
from .store_factory import get_ur_store


router = APIRouter(tags=["ur"])
store = get_ur_store()


class URCasePayload(BaseModel):
    client_id: Optional[str] = ""
    client_name: str = Field(..., min_length=1)
    assigned_case_manager: Optional[str] = ""
    payer: str = Field(..., min_length=1)
    member_id: Optional[str] = ""
    policy_group_number: Optional[str] = ""
    facility: Optional[str] = ""
    program: Optional[str] = ""
    current_level_of_care: Optional[str] = ""
    requested_level_of_care: Optional[str] = ""
    approved_level_of_care: Optional[str] = ""
    admit_date: str = Field(..., min_length=1)
    diagnosis: Optional[str] = ""
    asam_level: Optional[str] = ""
    auth_required: bool = True
    auth_number: Optional[str] = ""
    requested_days: int = Field(default=0, ge=0)
    approved_days: int = Field(default=0, ge=0)
    denied_days: Optional[int] = Field(default=None, ge=0)
    approved_start_date: Optional[str] = ""
    approved_end_date: Optional[str] = ""
    next_review_date: Optional[str] = ""
    reviewer_name: Optional[str] = ""
    reviewer_company: Optional[str] = ""
    reviewer_phone: Optional[str] = ""
    reviewer_fax: Optional[str] = ""
    reviewer_email: Optional[str] = ""
    auth_submission_method: Optional[str] = ""
    decision_received_method: Optional[str] = ""
    clinical_criteria_used: Optional[str] = "ASAM"
    clinical_justification_summary: Optional[str] = ""
    denial_reason: Optional[str] = ""
    peer_review_deadline: Optional[str] = ""
    appeal_deadline: Optional[str] = ""
    revenue_at_risk_amount: float = 0.0
    status: str = "auth_needed"


class UREventPayload(BaseModel):
    event_type: str
    event_date: Optional[str] = ""
    status: Optional[str] = ""
    notes: Optional[str] = ""
    requested_days: int = Field(default=0, ge=0)
    approved_days: int = Field(default=0, ge=0)
    denied_days: Optional[int] = Field(default=None, ge=0)
    approved_start_date: Optional[str] = ""
    approved_end_date: Optional[str] = ""
    reviewer_name: Optional[str] = ""
    reviewer_company: Optional[str] = ""
    reviewer_phone: Optional[str] = ""
    reviewer_fax: Optional[str] = ""
    reviewer_email: Optional[str] = ""
    auth_submission_method: Optional[str] = ""
    decision_received_method: Optional[str] = ""
    denial_reason: Optional[str] = ""
    peer_review_deadline: Optional[str] = ""
    appeal_deadline: Optional[str] = ""


def _authorize_case_payload(request: Request, payload: URCasePayload):
    current_user = require_authenticated_user(request)
    if payload.client_id:
        assert_client_access(current_user, payload.client_id)
    return current_user


def _authorize_case_access(request: Request, case_record: Dict[str, Any]):
    current_user = require_authenticated_user(request)
    if case_record.get("client_id"):
        assert_client_access(current_user, case_record["client_id"])
    elif multi_tenant_enabled() and case_record.get("org_id") != resolve_org_id(current_user):
        raise HTTPException(status_code=404, detail="UR case not found")
    elif not current_user.is_admin and case_record.get("assigned_case_manager") != current_user.case_manager_id:
        raise HTTPException(status_code=403, detail="Access denied to this UR case")
    return current_user


def _org_for_new_case(current_user, payload: Dict[str, Any]) -> str:
    client_org = get_client_org_id(payload.get("client_id") or "")
    if client_org:
        return client_org
    return resolve_org_id(current_user)


@router.get("/ur")
async def list_ur_cases(
    request: Request,
    search: Optional[str] = Query(None),
    payer: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    case_manager: Optional[str] = Query(None),
    due_window: Optional[str] = Query(None),
):
    current_user = require_authenticated_user(request)
    if status and status not in ALLOWED_UR_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported UR status filter")
    cases = store.list_cases(
        {
            "search": search,
            "payer": payer,
            "status": status,
            "case_manager": effective_case_manager_id(current_user, case_manager),
            "due_window": due_window,
            "org_id": resolve_org_id(current_user) if multi_tenant_enabled() else None,
        }
    )
    return {"success": True, "cases": cases, "total_count": len(cases)}


@router.get("/ur/summary")
async def get_ur_summary(request: Request, case_manager_id: Optional[str] = Query(None)):
    current_user = require_authenticated_user(request)
    summary = store.get_summary(
        effective_case_manager_id(current_user, case_manager_id),
        resolve_org_id(current_user) if multi_tenant_enabled() else None,
    )
    return {"success": True, **summary}


@router.post("/ur")
async def create_ur_case(payload: URCasePayload, request: Request):
    current_user = _authorize_case_payload(request, payload)
    data = payload.model_dump()
    if data["status"] not in ALLOWED_UR_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported UR status")
    data["assigned_case_manager"] = current_user.case_manager_id if not current_user.is_admin else (
        payload.assigned_case_manager or current_user.case_manager_id
    )
    data["org_id"] = _org_for_new_case(current_user, data)
    record = store.create_case(data)
    return {"success": True, "case": record}


@router.get("/ur/{case_id}")
async def get_ur_case(case_id: str, request: Request):
    detail = store.get_case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="UR case not found")
    _authorize_case_access(request, detail["case"])
    return {"success": True, **detail}


@router.put("/ur/{case_id}")
async def update_ur_case(case_id: str, payload: URCasePayload, request: Request):
    current_user = require_authenticated_user(request)
    existing = store.get_case(case_id)
    if not existing:
        raise HTTPException(status_code=404, detail="UR case not found")
    _authorize_case_access(request, existing)
    if payload.client_id:
        assert_client_access(current_user, payload.client_id)
    data = payload.model_dump()
    if data["status"] not in ALLOWED_UR_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported UR status")
    data["assigned_case_manager"] = current_user.case_manager_id if not current_user.is_admin else (
        payload.assigned_case_manager or existing.get("assigned_case_manager") or current_user.case_manager_id
    )
    record = store.update_case(case_id, data)
    return {"success": True, "case": record}


@router.delete("/ur/{case_id}")
async def delete_ur_case(case_id: str, request: Request):
    existing = store.get_case(case_id)
    if not existing:
        raise HTTPException(status_code=404, detail="UR case not found")
    current_user = require_authenticated_user(request)
    if not current_user.is_admin and existing.get("assigned_case_manager") != current_user.case_manager_id:
        raise HTTPException(status_code=403, detail="Access denied to this UR case")
    deleted = store.delete_case(case_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="UR case not found")
    return {"success": True, "case_id": case_id}


@router.post("/ur/{case_id}/events")
async def create_ur_event(case_id: str, payload: UREventPayload, request: Request):
    current_user = require_authenticated_user(request)
    existing = store.get_case(case_id)
    if not existing:
        raise HTTPException(status_code=404, detail="UR case not found")
    _authorize_case_access(request, existing)
    if payload.event_type not in ALLOWED_UR_EVENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported UR event type")
    record = store.create_event(case_id, {**payload.model_dump(), "created_by": current_user.case_manager_id})
    return {"success": True, "event": record}


@router.get("/ur/{case_id}/events")
async def list_ur_events(case_id: str, request: Request):
    existing = store.get_case(case_id)
    if not existing:
        raise HTTPException(status_code=404, detail="UR case not found")
    _authorize_case_access(request, existing)
    return {"success": True, "events": store.list_events(case_id)}
