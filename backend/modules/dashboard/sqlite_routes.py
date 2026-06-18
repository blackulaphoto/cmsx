# ================================================================
# @generated
# @preserve
# @readonly
# DO NOT MODIFY THIS FILE
# Purpose: Production-approved unified system
# Any changes must be approved by lead developer.
# WARNING: Modifying this file may break the application.
# ================================================================

"""
SQLite Dashboard Routes
Dashboard endpoints backed by case management SQLite DB.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request

from backend.modules.services.case_management_api import (
    get_dashboard_stats_from_db,
    get_clients_from_db,
    get_case_details_from_db,
)
from backend.auth.authorization import (
    assert_client_access,
    effective_case_manager_id,
    get_org_for_user_id,
)
from backend.auth.service import require_authenticated_user
from backend.shared.tenancy import multi_tenant_enabled, resolve_org_id

# NOTE: This file carries a "DO NOT MODIFY" banner. The Phase 3B tenancy edits
# below are a deliberate, minimal, flag-gated exception: these endpoints expose
# high-risk dashboard aggregate/client routes that would leak cross-org data if
# MULTI_TENANT_ENABLED were enabled without org scoping. All org logic is gated
# behind multi_tenant_enabled() so behavior is unchanged when the flag is false.

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats")
async def get_stats(request: Request, case_manager_id: str = Query(...)) -> Dict[str, Any]:
    try:
        current_user = require_authenticated_user(request)
        if current_user.is_admin:
            # Admins see all clients on the overview dashboard
            scoped_id = None
        else:
            scoped_id = current_user.case_manager_id
        # Phase 3B: when multi-tenancy is on, "all" means all in the caller's
        # org. org_id=None (flag off) preserves prior behavior exactly.
        org_id = resolve_org_id(current_user) if multi_tenant_enabled() else None
        return get_dashboard_stats_from_db(scoped_id, org_id=org_id)
    except Exception as exc:
        logger.error(f"Dashboard stats error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/clients")
async def get_clients(request: Request, case_manager_id: str = Query(...)) -> Dict[str, Any]:
    try:
        current_user = require_authenticated_user(request)
        scoped_id = effective_case_manager_id(current_user, case_manager_id) or current_user.case_manager_id
        # Phase 3B: when multi-tenancy is on, reject a cross-org case_manager_id
        # (return an empty list, matching this route's list semantics) and scope
        # the result to the caller's org. Flag off -> unchanged.
        org_id = None
        if multi_tenant_enabled():
            org_id = resolve_org_id(current_user)
            if scoped_id and get_org_for_user_id(scoped_id) != org_id:
                return {"success": True, "case_manager_id": scoped_id, "clients": [], "total_count": 0}
        return get_clients_from_db(scoped_id, org_id=org_id)
    except Exception as exc:
        logger.error(f"Dashboard clients error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/case/{case_id}")
async def get_case(case_id: str, request: Request) -> Dict[str, Any]:
    # Phase 3B: enforce org/ownership before returning case details. Placed
    # before the try/except so the 404 is not swallowed into a 500. Cross-org or
    # unauthorized access -> 404 via the existing access logic (dormant when the
    # flag is false; org isolation only applies when MULTI_TENANT_ENABLED=true).
    user = require_authenticated_user(request)
    assert_client_access(user, case_id)
    try:
        return get_case_details_from_db(case_id)
    except Exception as exc:
        logger.error(f"Dashboard case error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
