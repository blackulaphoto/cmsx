"""
SQLite helpers for case management dashboard data.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.shared.database.core_client_service import CoreClientService

logger = logging.getLogger(__name__)

core_client_service = CoreClientService()


def _fetch_clients(case_manager_id: Optional[str], org_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if not case_manager_id:
        clients = core_client_service.get_all_clients(limit=10000) or []
    else:
        clients = core_client_service.get_clients_by_case_manager(case_manager_id) or []
    # Phase 3B multi-tenancy: filter by org only when an org_id is supplied
    # (callers pass it only while MULTI_TENANT_ENABLED is true). org_id=None
    # preserves the existing single-agency behavior exactly.
    if org_id is not None:
        clients = [c for c in clients if (c.get("org_id") or "") == org_id]
    return clients


def _is_active_client(client: Dict[str, Any]) -> bool:
    case_status = str(client.get("case_status", "active")).strip().lower()
    return case_status not in {"inactive", "closed", "deleted"}


def _build_dashboard_payload(case_manager_id: Optional[str], clients: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_clients = len(clients)
    active_clients = len([c for c in clients if _is_active_client(c)])
    high_risk_clients = len([c for c in clients if str(c.get("risk_level", "")).lower() == "high"])

    recent_intakes = 0
    for client in clients:
        intake_date = client.get("intake_date")
        if not intake_date:
            continue
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
            try:
                intake_dt = datetime.strptime(intake_date, fmt)
                if (datetime.now() - intake_dt).days <= 30:
                    recent_intakes += 1
                break
            except ValueError:
                continue

    stats = {
        "total_clients": total_clients,
        "active_clients": active_clients,
        "high_risk_clients": high_risk_clients,
        "recent_intakes": recent_intakes,
    }

    return {
        "success": True,
        "case_manager_id": case_manager_id,
        "stats": stats,
        "statistics": stats,
        "recent_clients": clients[:5],
    }


def get_dashboard_stats_from_db(case_manager_id: Optional[str] = None, org_id: Optional[str] = None) -> Dict[str, Any]:
    """Return dashboard stats from the core client source of truth.
    Pass None for case_manager_id to get stats across all clients (admin overview).
    Pass org_id to scope to a single org (Phase 3B); None preserves prior behavior.
    """
    try:
        clients = _fetch_clients(case_manager_id, org_id)
        return _build_dashboard_payload(case_manager_id, clients)
    except Exception as e:
        logger.error(f"Error getting dashboard stats from DB: {e}")
        return {
            "success": False,
            "case_manager_id": case_manager_id,
            "stats": {
                "total_clients": 0,
                "active_clients": 0,
                "high_risk_clients": 0,
                "recent_intakes": 0,
            },
            "statistics": {
                "total_clients": 0,
                "active_clients": 0,
                "high_risk_clients": 0,
                "recent_intakes": 0,
            },
            "recent_clients": [],
            "error": str(e),
        }


def get_clients_from_db(case_manager_id: str, org_id: Optional[str] = None) -> Dict[str, Any]:
    """Return clients from the core client source of truth.
    Pass org_id to scope to a single org (Phase 3B); None preserves prior behavior.
    """
    try:
        clients = _fetch_clients(case_manager_id, org_id)
        return {
            "success": True,
            "case_manager_id": case_manager_id,
            "clients": clients,
            "total_count": len(clients),
        }
    except Exception as e:
        logger.error(f"Error getting clients from DB: {e}")
        return {
            "success": False,
            "case_manager_id": case_manager_id,
            "clients": [],
            "total_count": 0,
            "error": str(e),
        }


def get_case_details_from_db(case_id: str) -> Dict[str, Any]:
    """Return case/client details from the core client source of truth."""
    try:
        client = core_client_service.get_client(case_id)
        if not client:
            return {"success": False, "error": "Case not found", "case_id": case_id}

        return {"success": True, "case": client, "case_id": case_id}
    except Exception as e:
        logger.error(f"Error getting case details from DB: {e}")
        return {"success": False, "case_id": case_id, "error": str(e)}
