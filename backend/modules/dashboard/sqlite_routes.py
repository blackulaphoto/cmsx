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
from backend.auth.authorization import effective_case_manager_id
from backend.auth.service import require_authenticated_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats")
async def get_stats(request: Request, case_manager_id: str = Query(...)) -> Dict[str, Any]:
    try:
        current_user = require_authenticated_user(request)
        scoped_id = effective_case_manager_id(current_user, case_manager_id) or current_user.case_manager_id
        return get_dashboard_stats_from_db(scoped_id)
    except Exception as exc:
        logger.error(f"Dashboard stats error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/clients")
async def get_clients(request: Request, case_manager_id: str = Query(...)) -> Dict[str, Any]:
    try:
        current_user = require_authenticated_user(request)
        scoped_id = effective_case_manager_id(current_user, case_manager_id) or current_user.case_manager_id
        return get_clients_from_db(scoped_id)
    except Exception as exc:
        logger.error(f"Dashboard clients error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/case/{case_id}")
async def get_case(case_id: str, request: Request) -> Dict[str, Any]:
    try:
        require_authenticated_user(request)
        return get_case_details_from_db(case_id)
    except Exception as exc:
        logger.error(f"Dashboard case error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
