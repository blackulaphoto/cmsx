"""
Case manager rolodex routes for trusted provider and resource tracking.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.shared.database.workspace_store import workspace_store
from backend.auth.service import require_authenticated_user
from backend.shared.tenancy import DEFAULT_ORG_ID, multi_tenant_enabled, resolve_org_id

logger = logging.getLogger(__name__)

router = APIRouter(tags=["rolodex"])

DEFAULT_CASE_MANAGER_ID = "cm_001"


def _rolodex_org_filter(request: Request) -> Optional[str]:
    """Phase 3C rolodex (Option A): when multi-tenancy is on, scope the shared
    rolodex to the caller's org; when off, return None so the existing global
    DEFAULT_CASE_MANAGER_ID behavior is preserved exactly."""
    if not multi_tenant_enabled():
        return None
    return resolve_org_id(require_authenticated_user(request))
ROLEDEX_CATEGORIES = [
    "Treatment Centers",
    "Primary Care",
    "Dental",
    "Mental Health",
    "Substance Use",
    "Housing",
    "Benefits",
    "Legal",
    "Employment",
    "Transportation",
    "Hospital / ER",
    "Pharmacy",
    "Support Group",
    "General Resource",
    "Custom",
]
TRUSTED_STATUS_OPTIONS = [
    "Trusted",
    "Use With Caution",
    "New Contact",
]


class RolodexEntryPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1, max_length=100)
    custom_category: Optional[str] = Field(default="", max_length=100)
    organization: Optional[str] = Field(default="", max_length=200)
    role_title: Optional[str] = Field(default="", max_length=150)
    phone: Optional[str] = Field(default="", max_length=50)
    email: Optional[str] = Field(default="", max_length=200)
    website: Optional[str] = Field(default="", max_length=300)
    address: Optional[str] = Field(default="", max_length=300)
    city: Optional[str] = Field(default="", max_length=120)
    trusted_status: Optional[str] = Field(default="Trusted", max_length=50)
    availability_notes: Optional[str] = Field(default="", max_length=500)
    referral_notes: Optional[str] = Field(default="", max_length=1000)
    general_notes: Optional[str] = Field(default="", max_length=1500)


def _normalize_entry(payload: RolodexEntryPayload) -> dict:
    entry = payload.model_dump()
    entry["category"] = (entry["category"] or "").strip()
    entry["custom_category"] = (entry["custom_category"] or "").strip()
    entry["trusted_status"] = (entry["trusted_status"] or "Trusted").strip()
    if entry["category"] == "Custom" and not entry["custom_category"]:
        raise HTTPException(status_code=400, detail="Custom category name is required")
    if entry["category"] != "Custom":
        entry["custom_category"] = ""
    if entry["trusted_status"] not in TRUSTED_STATUS_OPTIONS:
        raise HTTPException(status_code=400, detail="Invalid trusted status")
    return entry


def _apply_filters(entries: List[dict], category: str, search: str, city: str, trusted_status: str) -> List[dict]:
    filtered = entries
    if category and category != "All":
        filtered = [
            entry for entry in filtered
            if entry.get("category") == category
            or (category == "Custom" and entry.get("custom_category"))
        ]
    if city:
        city_lower = city.lower()
        filtered = [
            entry for entry in filtered
            if city_lower in (entry.get("city") or "").lower()
            or city_lower in (entry.get("address") or "").lower()
        ]
    if trusted_status and trusted_status != "All":
        filtered = [entry for entry in filtered if entry.get("trusted_status") == trusted_status]
    if search:
        search_lower = search.lower()
        searchable_fields = (
            "name",
            "category",
            "custom_category",
            "organization",
            "role_title",
            "phone",
            "email",
            "website",
            "address",
            "city",
            "availability_notes",
            "referral_notes",
            "general_notes",
        )
        filtered = [
            entry for entry in filtered
            if any(search_lower in (entry.get(field) or "").lower() for field in searchable_fields)
        ]
    return filtered


@router.get("/rolodex")
async def list_rolodex_entries(
    request: Request,
    category: str = Query("All"),
    search: str = Query(""),
    city: str = Query(""),
    trusted_status: str = Query("All"),
):
    try:
        entries = workspace_store.list_rolodex_entries(
            DEFAULT_CASE_MANAGER_ID, org_id=_rolodex_org_filter(request)
        )
        filtered = _apply_filters(entries, category.strip(), search.strip(), city.strip(), trusted_status.strip())
        return {
            "success": True,
            "entries": filtered,
            "total_count": len(filtered),
            "categories": ROLEDEX_CATEGORIES,
            "trusted_statuses": TRUSTED_STATUS_OPTIONS,
        }
    except Exception as exc:
        logger.error("Error loading rolodex entries: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load rolodex entries")


@router.get("/rolodex/categories")
async def get_rolodex_categories():
    return {
        "success": True,
        "categories": ROLEDEX_CATEGORIES,
        "trusted_statuses": TRUSTED_STATUS_OPTIONS,
    }


@router.post("/rolodex")
async def create_rolodex_entry(payload: RolodexEntryPayload, request: Request):
    try:
        entry = workspace_store.create_rolodex_entry(
            DEFAULT_CASE_MANAGER_ID,
            _normalize_entry(payload),
            org_id=_rolodex_org_filter(request) or DEFAULT_ORG_ID,
        )
        return {"success": True, "entry": entry}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error creating rolodex entry: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create rolodex entry")


@router.put("/rolodex/{entry_id}")
async def update_rolodex_entry(entry_id: str, payload: RolodexEntryPayload, request: Request):
    try:
        entry = workspace_store.update_rolodex_entry(
            entry_id, _normalize_entry(payload), org_id=_rolodex_org_filter(request)
        )
        if not entry:
            raise HTTPException(status_code=404, detail="Rolodex entry not found")
        return {"success": True, "entry": entry}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error updating rolodex entry: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update rolodex entry")


@router.delete("/rolodex/{entry_id}")
async def delete_rolodex_entry(entry_id: str, request: Request):
    try:
        deleted = workspace_store.delete_rolodex_entry(entry_id, org_id=_rolodex_org_filter(request))
        if not deleted:
            raise HTTPException(status_code=404, detail="Rolodex entry not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error deleting rolodex entry: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete rolodex entry")
