"""Canonical Smart Daily projections for persisted medical appointments."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, Optional
from uuid import NAMESPACE_URL, uuid5

from backend.modules.reminders.repository import sync_active_reminder
from backend.shared.database.workspace_store import workspace_store
from backend.shared.db_path import DB_DIR


CASE_MGMT_DB_PATH = DB_DIR / "case_management.db"
_INACTIVE_STATUSES = {
    "cancelled",
    "canceled",
    "completed",
    "missed",
    "no show",
    "no-show",
    "no_show",
}


def medical_appointment_reminder_id(source: str, appointment_id: str) -> str:
    """Return the stable backend identity for one appointment reminder."""
    return str(uuid5(NAMESPACE_URL, f"cmsx:medical-appointment:{source}:{appointment_id}"))


def _date_minus_days(value: Any, days: int) -> Optional[str]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        try:
            parsed = datetime.strptime(str(value)[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return (parsed - timedelta(days=days)).date().isoformat()


def _is_active(record: Dict[str, Any]) -> bool:
    status = str(record.get("status") or "scheduled").strip().lower()
    enabled = record.get("reminder_enabled", 1)
    return bool(enabled) and status not in _INACTIVE_STATUSES


def sync_medical_appointment_reminder(
    record: Dict[str, Any],
    *,
    source: str,
    case_manager_id: Optional[str] = None,
    org_id: Optional[str] = None,
) -> str:
    """Create, update, reopen, or remove the reminder for one appointment."""
    appointment_id = str(record.get("id") or record.get("apt_id") or "")
    if not appointment_id:
        raise ValueError("Appointment identity is required")

    assigned_to = str(case_manager_id or record.get("case_manager_id") or "").strip()
    if not assigned_to:
        raise ValueError("Appointment case manager is required")

    is_medical_module = source == "medical"
    appointment_date = record.get("appointment_date")
    due_date = _date_minus_days(appointment_date, 1 if is_medical_module else 0)
    provider = str(record.get("provider_name") or record.get("doctor_name") or "").strip()
    appointment_type = str(
        record.get("appointment_type")
        or record.get("title")
        or record.get("service_type")
        or "Medical appointment"
    ).strip()

    message = appointment_type
    if provider:
        message += f" with {provider}"
    if appointment_date:
        message += f" on {str(appointment_date)[:10]}"
    appointment_time = str(record.get("appointment_time") or "").strip()
    if appointment_time:
        message += f" at {appointment_time}"

    return sync_active_reminder(
        reminder_id=medical_appointment_reminder_id(source, appointment_id),
        client_id=str(record.get("client_id") or ""),
        case_manager_id=assigned_to,
        reminder_type="Medical Appointment",
        message=message,
        priority="High",
        due_date=due_date,
        active=_is_active(record),
        org_id=org_id,
    )


def remove_medical_appointment_reminder(
    appointment_id: str,
    *,
    source: str,
    client_id: str,
    case_manager_id: str,
    org_id: Optional[str] = None,
) -> str:
    """Remove the stable projection after its source appointment is deleted."""
    return sync_active_reminder(
        reminder_id=medical_appointment_reminder_id(source, appointment_id),
        client_id=client_id,
        case_manager_id=case_manager_id,
        reminder_type="Medical Appointment",
        message="Medical appointment",
        priority="High",
        due_date=None,
        active=False,
        org_id=org_id,
    )


def reconcile_medical_appointment_reminders(
    case_manager_id: str,
    client_ids: Iterable[str],
    *,
    org_id: Optional[str] = None,
) -> None:
    """Project pre-existing appointments assigned to a case manager."""
    if CASE_MGMT_DB_PATH.exists():
        with sqlite3.connect(CASE_MGMT_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            table_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='appointments'"
            ).fetchone()
            if table_exists:
                columns = {
                    row[1] for row in conn.execute("PRAGMA table_info(appointments)").fetchall()
                }
                reminder_enabled = (
                    "reminder_enabled" if "reminder_enabled" in columns else "1 AS reminder_enabled"
                )
                rows = conn.execute(
                    f"""
                    SELECT id, client_id, case_manager_id, appointment_type, provider_name,
                           appointment_date, appointment_time, status, {reminder_enabled}
                    FROM appointments
                    WHERE case_manager_id = ?
                    """,
                    (case_manager_id,),
                ).fetchall()
                for row in rows:
                    sync_medical_appointment_reminder(
                        dict(row), source="medical", org_id=org_id
                    )

    for client_id in client_ids:
        for appointment in workspace_store.list_client_appointments(client_id):
            sync_medical_appointment_reminder(
                appointment,
                source="workspace",
                case_manager_id=case_manager_id,
                org_id=org_id,
            )
