"""
SQLite helpers for case management dashboard data.
"""

import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _get_case_management_db_path() -> str:
    return "databases/case_management.db"


def _fetch_clients(case_manager_id: str) -> List[Dict[str, Any]]:
    db_path = _get_case_management_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT * FROM clients
            WHERE case_manager_id = ? AND is_active = 1
            """,
            (case_manager_id,),
        )
    except Exception:
        cursor.execute(
            """
            SELECT * FROM clients
            WHERE case_manager_id = ?
            """,
            (case_manager_id,),
        )

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_dashboard_stats_from_db(case_manager_id: str) -> Dict[str, Any]:
    """Return dashboard stats from SQLite."""
    try:
        clients = _fetch_clients(case_manager_id)
        total_clients = len(clients)
        active_clients = len([c for c in clients if str(c.get("case_status", "")).lower() == "active"])
        high_risk_clients = len([c for c in clients if str(c.get("risk_level", "")).lower() == "high"])

        recent_intakes = 0
        for client in clients:
            intake_date = client.get("intake_date")
            if not intake_date:
                continue
            for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    intake_dt = datetime.strptime(intake_date, fmt)
                    if (datetime.now() - intake_dt).days <= 30:
                        recent_intakes += 1
                    break
                except ValueError:
                    continue

        return {
            "success": True,
            "case_manager_id": case_manager_id,
            "statistics": {
                "total_clients": total_clients,
                "active_clients": active_clients,
                "high_risk_clients": high_risk_clients,
                "recent_intakes": recent_intakes,
            },
            "recent_clients": clients[:5],
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats from DB: {e}")
        return {
            "success": False,
            "case_manager_id": case_manager_id,
            "statistics": {
                "total_clients": 0,
                "active_clients": 0,
                "high_risk_clients": 0,
                "recent_intakes": 0,
            },
            "recent_clients": [],
            "error": str(e),
        }


def get_clients_from_db(case_manager_id: str) -> Dict[str, Any]:
    """Return clients from SQLite."""
    try:
        clients = _fetch_clients(case_manager_id)
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
    """Return case/client details from SQLite."""
    try:
        db_path = _get_case_management_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE client_id = ?", (case_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"success": False, "error": "Case not found", "case_id": case_id}

        return {"success": True, "case": dict(row), "case_id": case_id}
    except Exception as e:
        logger.error(f"Error getting case details from DB: {e}")
        return {"success": False, "case_id": case_id, "error": str(e)}
