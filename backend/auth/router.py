from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .service import ADMIN_ROLE, CASE_MANAGER_ROLE, auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterProfileRequest(BaseModel):
    role: Optional[str] = Field(default=None, pattern="^(admin|case_manager)?$")
    case_manager_id: Optional[str] = None


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
    return {"success": True, "user": user.__dict__}
