"""
Read-only platform data tools for the popup AI assistant (v1).

All functions receive an already-authenticated case_manager_id and org_id;
the LLM is never asked to supply identity parameters.  Any case_manager_id
the LLM includes in its tool-call arguments is silently ignored at call time —
the auth-bound values are injected by the caller (unified_service.py).
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _core_clients_db():
    from backend.shared.db_path import DB_DIR as _DB_DIR
    return _DB_DIR / "core_clients.db"


def _admissions_db():
    from backend.shared.db_path import DB_DIR as _DB_DIR
    return _DB_DIR / "admissions.db"


def _legal_db():
    from backend.shared.db_path import DB_DIR as _DB_DIR
    return _DB_DIR / "legal_cases.db"


def _reminders_db():
    from backend.shared.db_path import DB_DIR as _DB_DIR
    from backend.modules.reminders import repository as _repo
    return getattr(_repo, "_SQLITE_REMINDERS_PATH", _DB_DIR / "reminders.db")


def _name_matches(query: str, first: str, last: str) -> bool:
    q = query.strip().lower()
    full = f"{first} {last}".lower()
    return (
        q in full
        or q in first.lower()
        or q in last.lower()
    )


# ---------------------------------------------------------------------------
# Tool 1: list_current_clients
# ---------------------------------------------------------------------------

def list_current_clients(case_manager_id: str, org_id: Optional[str] = None) -> Dict[str, Any]:
    """Return the signed-in user's accessible clients (same as dashboard view)."""
    try:
        from backend.modules.services.case_management_api import get_clients_from_db
        result = get_clients_from_db(case_manager_id=case_manager_id, org_id=org_id)
        clients_raw = result.get("clients", [])
        clients = [
            {
                "client_id": c.get("client_id", ""),
                "name": f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
                "status": c.get("case_status", "Active"),
                "risk_level": c.get("risk_level", ""),
            }
            for c in clients_raw
        ]
        return {
            "success": True,
            "clients": clients,
            "total": len(clients),
            "source": "core_clients",
        }
    except Exception as exc:
        logger.error("list_current_clients failed: %s", exc)
        return {"success": False, "clients": [], "total": 0, "error": str(exc)}


# ---------------------------------------------------------------------------
# Tool 2: search_client_by_name
# ---------------------------------------------------------------------------

def search_client_by_name(
    name: str,
    case_manager_id: str,
    org_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Find clients by partial name within the authenticated user's scope."""
    try:
        from backend.modules.services.case_management_api import get_clients_from_db
        result = get_clients_from_db(case_manager_id=case_manager_id, org_id=org_id)
        clients_raw = result.get("clients", [])
        matches = [
            {
                "client_id": c.get("client_id", ""),
                "name": f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
                "status": c.get("case_status", "Active"),
                "risk_level": c.get("risk_level", ""),
            }
            for c in clients_raw
            if _name_matches(name, c.get("first_name", ""), c.get("last_name", ""))
        ]
        if not matches:
            return {
                "success": True,
                "found": False,
                "matches": [],
                "message": f"No clients found matching '{name}' in your caseload.",
                "source": "core_clients",
            }
        if len(matches) == 1:
            return {
                "success": True,
                "found": True,
                "matches": matches,
                "client": matches[0],
                "source": "core_clients",
            }
        return {
            "success": True,
            "found": True,
            "multiple": True,
            "matches": matches,
            "message": f"Found {len(matches)} clients matching '{name}'. Please clarify which one.",
            "source": "core_clients",
        }
    except Exception as exc:
        logger.error("search_client_by_name failed: %s", exc)
        return {"success": False, "found": False, "matches": [], "error": str(exc)}


# ---------------------------------------------------------------------------
# Tool 3: get_client_insurance
# ---------------------------------------------------------------------------

def get_client_insurance(
    client_id: str,
    case_manager_id: str,
    org_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return insurance provider and member ID for a client from admissions data."""
    try:
        # Verify the client belongs to this case manager before revealing data
        from backend.modules.services.case_management_api import get_clients_from_db
        scope = get_clients_from_db(case_manager_id=case_manager_id, org_id=org_id)
        accessible_ids = {c.get("client_id") for c in scope.get("clients", [])}
        if client_id not in accessible_ids:
            return {
                "success": False,
                "error": "Client not found in your caseload.",
                "client_id": client_id,
            }

        db_path = _admissions_db()
        if not db_path.exists():
            return {
                "success": True,
                "client_id": client_id,
                "insurance_provider": None,
                "insurance_member_id": None,
                "source": "admissions",
                "note": "Admissions database not found; no insurance data available.",
            }

        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            # Check face-sheet data first (primary_payer_type, primary_member_id)
            row = conn.execute(
                """
                SELECT primary_payer_type, primary_plan_name, primary_member_id
                FROM face_sheets
                WHERE client_id = ?
                LIMIT 1
                """,
                (client_id,),
            ).fetchone()
            if not row:
                # Try admission_packets table
                row = conn.execute(
                    """
                    SELECT primary_payer_type, primary_plan_name, primary_member_id
                    FROM admission_packets
                    WHERE client_id = ?
                    LIMIT 1
                    """,
                    (client_id,),
                ).fetchone()

        if not row:
            return {
                "success": True,
                "client_id": client_id,
                "insurance_provider": None,
                "insurance_member_id": None,
                "source": "admissions",
                "note": "No admissions record found for this client.",
            }

        provider = (row["primary_payer_type"] or "").strip() or None
        plan = (row["primary_plan_name"] or "").strip() or None
        member_id = (row["primary_member_id"] or "").strip() or None

        return {
            "success": True,
            "client_id": client_id,
            "insurance_provider": provider,
            "insurance_plan": plan,
            "insurance_member_id": member_id,
            "source": "admissions",
            "note": None if (provider or member_id) else "Insurance fields are empty in this client's admissions record.",
        }
    except Exception as exc:
        logger.error("get_client_insurance failed for %s: %s", client_id, exc)
        return {"success": False, "client_id": client_id, "error": str(exc)}


# ---------------------------------------------------------------------------
# Tool 4: get_upcoming_court_dates
# ---------------------------------------------------------------------------

def get_upcoming_court_dates(
    case_manager_id: str,
    org_id: Optional[str] = None,
    days_ahead: int = 7,
) -> Dict[str, Any]:
    """Return upcoming court dates for clients in the case manager's caseload."""
    try:
        # Get the case manager's accessible client IDs
        from backend.modules.services.case_management_api import get_clients_from_db
        scope = get_clients_from_db(case_manager_id=case_manager_id, org_id=org_id)
        clients_raw = scope.get("clients", [])
        if not clients_raw:
            return {
                "success": True,
                "court_dates": [],
                "total": 0,
                "source": "legal",
                "note": "No clients in your caseload.",
            }

        name_map = {
            c["client_id"]: f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
            for c in clients_raw
        }
        accessible_ids = list(name_map.keys())

        today = datetime.now().date()
        future = (today + timedelta(days=max(1, days_ahead))).isoformat()
        today_iso = today.isoformat()

        court_dates: List[Dict[str, Any]] = []

        # --- Legal cases DB ---
        legal_path = _legal_db()
        if legal_path.exists():
            try:
                with sqlite3.connect(str(legal_path)) as conn:
                    conn.row_factory = sqlite3.Row
                    placeholders = ", ".join(["?"] * len(accessible_ids))
                    rows = conn.execute(
                        f"""
                        SELECT court_date_id, case_id, client_id,
                               hearing_date, hearing_time, court_name,
                               courtroom, hearing_type, status
                        FROM court_dates
                        WHERE hearing_date >= ? AND hearing_date <= ?
                          AND client_id IN ({placeholders})
                        ORDER BY hearing_date ASC, hearing_time ASC
                        """,
                        [today_iso, future] + accessible_ids,
                    ).fetchall()
                for row in rows:
                    days_until = None
                    if row["hearing_date"]:
                        try:
                            days_until = (
                                datetime.fromisoformat(row["hearing_date"]).date() - today
                            ).days
                        except Exception:
                            pass
                    court_dates.append({
                        "client_name": name_map.get(row["client_id"], "Unknown Client"),
                        "client_id": row["client_id"],
                        "hearing_date": row["hearing_date"],
                        "hearing_time": row["hearing_time"] or "",
                        "court_name": row["court_name"] or "",
                        "hearing_type": row["hearing_type"] or "",
                        "status": row["status"] or "Scheduled",
                        "days_until": days_until,
                        "source": "legal",
                    })
            except Exception as exc:
                logger.warning("Court dates legal DB query failed: %s", exc)

        # --- Reminders DB: reminder_type contains 'court' ---
        try:
            from backend.modules.reminders.repository import get_active_reminders_for_case_manager
            reminders = get_active_reminders_for_case_manager(case_manager_id, org_id=org_id)
            for r in reminders:
                rtype = (r.get("reminder_type") or "").lower()
                if "court" not in rtype:
                    continue
                due = r.get("due_date") or ""
                if not due:
                    continue
                try:
                    due_date = datetime.fromisoformat(due).date()
                except Exception:
                    continue
                if not (today <= due_date <= datetime.fromisoformat(future).date()):
                    continue
                days_until = (due_date - today).days
                client_id = r.get("client_id", "")
                court_dates.append({
                    "client_name": name_map.get(client_id, "Unknown Client"),
                    "client_id": client_id,
                    "hearing_date": due_date.isoformat(),
                    "hearing_time": "",
                    "court_name": "",
                    "hearing_type": "Court (from reminder)",
                    "status": r.get("status", "Active"),
                    "days_until": days_until,
                    "note": r.get("message", ""),
                    "source": "reminders",
                })
        except Exception as exc:
            logger.warning("Court dates reminders query failed: %s", exc)

        court_dates.sort(key=lambda x: (x.get("hearing_date") or "", x.get("hearing_time") or ""))

        if not court_dates:
            return {
                "success": True,
                "court_dates": [],
                "total": 0,
                "days_ahead": days_ahead,
                "source": "legal+reminders",
                "note": f"No court dates found in the next {days_ahead} days for your clients.",
            }
        return {
            "success": True,
            "court_dates": court_dates,
            "total": len(court_dates),
            "days_ahead": days_ahead,
            "source": "legal+reminders",
        }
    except Exception as exc:
        logger.error("get_upcoming_court_dates failed: %s", exc)
        return {"success": False, "court_dates": [], "total": 0, "error": str(exc)}
