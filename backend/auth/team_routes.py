"""Team management endpoints (invites + staff) for organization admins.

All routes are admin-gated via ``require_org_admin`` and derive ``org_id`` from
the authenticated caller — the client can never name another org. Accepting an
invite is handled by the onboarding join flow (``POST /api/auth/onboarding/join``);
this router covers create / list / resend / cancel and staff management.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from .service import auth_service, require_org_admin

router = APIRouter(prefix="/api/team", tags=["team"])


class CreateInviteRequest(BaseModel):
    """Note: NO org_id field — the org is the caller's own, resolved from the
    token. ``role`` is restricted to the two real org roles."""
    email: str = Field(min_length=3, max_length=200)
    role: str = Field(pattern="^(org_admin|member)$")
    name: Optional[str] = Field(default=None, max_length=120)


class RoleUpdateRequest(BaseModel):
    role: str = Field(pattern="^(org_admin|member)$")


# ── Invites ─────────────────────────────────────────────────────────────────

@router.post("/invites")
async def create_invite(payload: CreateInviteRequest, request: Request):
    user = require_org_admin(request)
    invite = auth_service.create_invite(
        user.org_id, payload.email, payload.role,
        invited_by=user.firebase_uid, invited_name=payload.name,
    )
    return {"success": True, "invite": invite}


@router.get("/invites")
async def list_invites(request: Request):
    user = require_org_admin(request)
    return {"success": True, "invites": auth_service.list_invites(user.org_id)}


@router.post("/invites/{invite_id}/resend")
async def resend_invite(invite_id: str, request: Request):
    user = require_org_admin(request)
    return {"success": True, "invite": auth_service.resend_invite(user.org_id, invite_id)}


@router.post("/invites/{invite_id}/cancel")
async def cancel_invite(invite_id: str, request: Request):
    user = require_org_admin(request)
    return {"success": True, "invite": auth_service.cancel_invite(user.org_id, invite_id)}


# ── Staff ───────────────────────────────────────────────────────────────────

@router.get("/staff")
async def list_staff(request: Request):
    user = require_org_admin(request)
    return {"success": True, "staff": auth_service.list_staff(user.org_id)}


@router.post("/staff/{firebase_uid}/role")
async def update_staff_role(firebase_uid: str, payload: RoleUpdateRequest, request: Request):
    user = require_org_admin(request)
    return {"success": True, "staff": auth_service.update_staff_role(user.org_id, firebase_uid, payload.role)}


@router.post("/staff/{firebase_uid}/remove")
async def remove_staff(firebase_uid: str, request: Request):
    user = require_org_admin(request)
    return {"success": True, "staff": auth_service.disable_staff(user.org_id, firebase_uid)}
