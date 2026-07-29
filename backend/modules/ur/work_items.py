"""Project UR operational deadlines into the canonical reminder store."""

from typing import Any, Dict

from backend.modules.reminders.repository import sync_active_reminder


_DEADLINES = (
    ("next_review_date", "review", "UR review due", "High", {"closed"}),
    ("approved_end_date", "authorization_end", "UR authorization ends", "High", {"closed"}),
    ("peer_review_deadline", "peer_review", "UR peer review due", "Critical", {"closed"}),
    ("appeal_deadline", "appeal", "UR appeal due", "Critical", {"closed"}),
)


def sync_ur_deadline_reminders(case_record: Dict[str, Any]) -> None:
    case_id = str(case_record.get("case_id") or "")
    client_id = str(case_record.get("client_id") or "")
    case_manager_id = str(case_record.get("assigned_case_manager") or "")
    if not case_id or not client_id or not case_manager_id:
        return

    client_name = str(case_record.get("client_name") or "client")
    status = str(case_record.get("status") or "").strip().lower()
    org_id = case_record.get("org_id")
    for field, suffix, label, priority, inactive_statuses in _DEADLINES:
        due_date = str(case_record.get(field) or "").strip()
        sync_active_reminder(
            reminder_id=f"ur:{case_id}:{suffix}",
            client_id=client_id,
            case_manager_id=case_manager_id,
            reminder_type="ur",
            message=f"{label} for {client_name}",
            priority=priority,
            due_date=due_date or None,
            active=bool(due_date) and status not in inactive_statuses,
            org_id=org_id,
        )
