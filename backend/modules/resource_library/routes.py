"""
Resource Library Routes - Master resource API.
GET  /api/resources         - filtered list
GET  /api/resources/{id}    - single record
POST /api/resources         - create (default verification_status: needs_review)
PATCH /api/resources/{id}   - update / review
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from .database import (
    initialize_db,
    search_resources,
    get_resource_by_id,
    insert_resource,
    update_resource,
    get_resource_count,
    VALID_VERIFICATION_STATUSES,
)
from .models import ResourceCreate, ResourceUpdate

logger = logging.getLogger(__name__)
router = APIRouter(tags=["resource-library"])

# Initialize DB on first import
try:
    initialize_db()
except Exception as _e:
    logger.error(f"Resource library DB init failed: {_e}")


@router.get("/")
async def resource_library_info():
    try:
        count = get_resource_count()
    except Exception:
        count = 0
    return {
        "message": "CMSX Master Resource Library",
        "version": "1.0",
        "description": (
            "Single source of truth for all programs and resources. "
            "Modules filter via category, pathways, and tags."
        ),
        "total_resources": count,
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health")
async def health():
    try:
        count = get_resource_count()
        return {"status": "healthy", "resource_count": count, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/search")
async def search(
    category: Optional[str] = Query(None, description="Primary category filter"),
    pathway: Optional[str] = Query(None, description="Pathway tag filter"),
    tag: Optional[str] = Query(None, description="Tag keyword filter"),
    search: Optional[str] = Query(None, description="Full-text search"),
    city: Optional[str] = Query(None),
    county: Optional[str] = Query(None),
    verification_status: Optional[str] = Query(None),
    active: Optional[bool] = Query(True),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Search the master resource library with filters."""
    try:
        result = search_resources(
            category=category,
            pathway=pathway,
            tag=tag,
            search=search,
            city=city,
            county=county,
            verification_status=verification_status,
            active=active,
            page=page,
            per_page=per_page,
        )
        return result
    except Exception as e:
        logger.error(f"Resource library search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_resource(data: ResourceCreate):
    """Add a new resource. Default verification_status is needs_review."""
    try:
        payload = data.model_dump()
        resource_id = insert_resource(payload)
        resource = get_resource_by_id(resource_id)
        return {"success": True, "resource": resource, "id": resource_id}
    except Exception as e:
        logger.error(f"Resource create error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{resource_id}")
async def patch_resource(resource_id: int, data: ResourceUpdate):
    """Update fields on an existing resource."""
    existing = get_resource_by_id(resource_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")

    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "verification_status" in payload:
        if payload["verification_status"] not in VALID_VERIFICATION_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid verification_status. Allowed: {sorted(VALID_VERIFICATION_STATUSES)}",
            )

    # Merge with existing so callers can send partial updates
    merged = {**existing, **payload}
    updated = update_resource(resource_id, merged)
    return {"success": True, "resource": updated}


@router.get("/{resource_id}")
async def get_resource(resource_id: int):
    """Get a single resource by ID."""
    resource = get_resource_by_id(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")
    return {"success": True, "resource": resource}
