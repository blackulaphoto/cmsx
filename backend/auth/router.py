from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .service import ADMIN_ROLE, CASE_MANAGER_ROLE, auth_service
from backend.shared.tenancy import multi_tenant_enabled

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterProfileRequest(BaseModel):
    role: Optional[str] = Field(default=None, pattern="^(admin|case_manager)?$")
    case_manager_id: Optional[str] = None


class CreateOrgRequest(BaseModel):
    """Onboarding: create organization. Deliberately carries NO role/org_role —
    the server assigns owner/admin; the client cannot supply role authority."""
    name: str = Field(min_length=1, max_length=120)
    org_type: str = Field(min_length=1, max_length=60)


class JoinOrgRequest(BaseModel):
    token: str = Field(min_length=1, max_length=200)


def _profile_response(user) -> dict:
    return {
        "success": True,
        "user": user.__dict__,
        "needs_onboarding": not user.onboarding_completed,
        "multi_tenant_enabled": multi_tenant_enabled(),
        # Lets the frontend conditionally show the Super Admin link. Access is
        # always re-checked server-side on every super-admin endpoint.
        "is_super_admin": auth_service.is_platform_super_admin(user),
    }


@router.post("/register")
async def register_profile(payload: RegisterProfileRequest, request: Request):
    decoded = auth_service.verify_bearer_token(request.headers.get("Authorization"))
    if payload.role == ADMIN_ROLE:
        admin_emails = {
            item.strip().lower()
            for item in (__import__("os").getenv("AUTH_ADMIN_EMAILS") or "").split(",")
            if item.strip()
        }
        if (decoded.get("email") or "").strip().lower() not in admin_emails:
            raise HTTPException(status_code=403, detail="Admin role assignment is not allowed for this account")

    user = auth_service.upsert_profile_from_token(
        decoded,
        requested_role=payload.role or CASE_MANAGER_ROLE,
        requested_case_manager_id=payload.case_manager_id,
    )
    return {"success": True, "user": user.__dict__}


@router.get("/me")
async def get_current_profile(request: Request):
    decoded = auth_service.verify_bearer_token(request.headers.get("Authorization"))
    user = auth_service.upsert_profile_from_token(decoded)
    # `needs_onboarding` drives the first-login front door; `multi_tenant_enabled`
    # is the SaaS-mode flag (no secrets, no DB paths). Both sit alongside the
    # caller's own identity (user.__dict__).
    return _profile_response(user)


@router.post("/onboarding/individual")
async def onboarding_individual(request: Request):
    """Create a personal workspace for the signed-in user and route to dashboard."""
    decoded = auth_service.verify_bearer_token(request.headers.get("Authorization"))
    user = auth_service.upsert_profile_from_token(decoded)
    updated = auth_service.create_individual_workspace(user.firebase_uid)
    return _profile_response(updated)


@router.post("/onboarding/organization")
async def onboarding_organization(payload: CreateOrgRequest, request: Request):
    """Create an organization; the signed-in user becomes its owner/admin."""
    decoded = auth_service.verify_bearer_token(request.headers.get("Authorization"))
    user = auth_service.upsert_profile_from_token(decoded)
    updated = auth_service.create_organization(user.firebase_uid, payload.name, payload.org_type)
    return _profile_response(updated)


@router.post("/onboarding/join")
async def onboarding_join(payload: JoinOrgRequest, request: Request):
    """Join an organization via invite token. org_role comes from the invite."""
    decoded = auth_service.verify_bearer_token(request.headers.get("Authorization"))
    user = auth_service.upsert_profile_from_token(decoded)
    updated = auth_service.accept_invite(user.firebase_uid, payload.token)
    return _profile_response(updated)
