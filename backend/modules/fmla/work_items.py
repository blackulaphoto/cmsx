"""Project actionable FMLA deadlines into the canonical reminder store."""

from typing import Any, Dict

from backend.modules.reminders.repository import sync_active_reminder

from .store import ACTIVE_FMLA_STATUSES


def sync_fmla_deadline_reminders(case_record: Dict[str, Any]) -> None:
    case_id = str(case_record.get("case_id") or "")
    if not case_id:
        return

    client_id = str(case_record.get("client_id") or "")
    case_manager_id = str(case_record.get("assigned_case_manager") or "")
    client_name = str(case_record.get("client_name") or "client")
    status = str(case_record.get("status") or "").strip().lower()
    approval_status = str(case_record.get("approval_status") or "").strip().lower()
    subject_type = str(case_record.get("case_subject_type") or "client").strip().lower()
    linked_client_case = subject_type == "client" and bool(client_id and case_manager_id)
    active_case = linked_client_case and status in ACTIVE_FMLA_STATUSES
    org_id = case_record.get("org_id")

    deadlines = (
        (
            "paperwork_deadline",
            "paperwork",
            "FMLA paperwork due",
            "High",
            active_case and not bool(case_record.get("paperwork_completed_date")),
        ),
        (
            "employer_response_deadline",
            "employer_response",
            "FMLA employer response due",
            "High",
            active_case
            and status in {"draft", "pending documents", "submitted"}
            and approval_status not in {"approved", "denied"},
        ),
        (
            "certification_expiration_date",
            "certification_expiration",
            "FMLA certification expires",
            "High",
            active_case,
        ),
        (
            "return_to_work_date",
            "return_to_work",
            "FMLA return-to-work action due",
            "Medium",
            active_case and status == "approved",
        ),
    )

    for field, suffix, label, priority, should_be_active in deadlines:
        due_date = str(case_record.get(field) or "").strip()
        sync_active_reminder(
            reminder_id=f"fmla:{case_id}:{suffix}",
            client_id=client_id,
            case_manager_id=case_manager_id,
            reminder_type="fmla",
            message=f"{label} for {client_name}",
            priority=priority,
            due_date=due_date or None,
            active=bool(due_date) and should_be_active,
            org_id=org_id,
        )
