"""Canonical Smart Daily projection for treatment-plan review deadlines."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional

from backend.modules.reminders.repository import sync_active_reminder
from backend.shared.database.workspace_store import workspace_store


_ACTIVE_PLAN_STATUSES = {"active", "review_due"}


def treatment_plan_review_reminder_id(plan_id: str) -> str:
    return f"treatment-plan:{plan_id}:review"


def sync_treatment_plan_review_reminder(
    plan: Dict[str, Any],
    *,
    case_manager_id: str,
    client_name: str = "",
    org_id: Optional[str] = None,
) -> str:
    """Synchronize one plan's review deadline with canonical reminders."""
    plan_id = str(plan.get("plan_id") or "").strip()
    client_id = str(plan.get("client_id") or "").strip()
    if not plan_id or not client_id:
        raise ValueError("Treatment plan and client identities are required")
    if not str(case_manager_id or "").strip():
        raise ValueError("Treatment plan case manager is required")

    review_due_date = plan.get("review_due_date")
    status = str(plan.get("status") or "").strip().lower()
    active = status in _ACTIVE_PLAN_STATUSES and bool(review_due_date)
    display_name = str(client_name or "").strip()
    message = "Treatment plan review due"
    if display_name:
        message += f" for {display_name}"

    return sync_active_reminder(
        reminder_id=treatment_plan_review_reminder_id(plan_id),
        client_id=client_id,
        case_manager_id=case_manager_id,
        reminder_type="Treatment Plan Review",
        message=message,
        priority="High",
        due_date=str(review_due_date) if review_due_date else None,
        active=active,
        org_id=org_id,
    )


def sync_client_treatment_plan_review_reminders(
    client_id: str,
    *,
    case_manager_id: str,
    client_name: str = "",
    org_id: Optional[str] = None,
) -> None:
    """Synchronize current and superseded plan projections for one client."""
    for plan in workspace_store.list_client_treatment_plans(client_id):
        sync_treatment_plan_review_reminder(
            plan,
            case_manager_id=case_manager_id,
            client_name=client_name,
            org_id=org_id,
        )


def reconcile_treatment_plan_review_reminders(
    case_manager_id: str,
    client_ids: Iterable[str],
    client_names: Mapping[str, str],
    *,
    org_id: Optional[str] = None,
) -> None:
    """Recover projections for approved plans that predate this integration."""
    for client_id in client_ids:
        sync_client_treatment_plan_review_reminders(
            client_id,
            case_manager_id=case_manager_id,
            client_name=client_names.get(client_id, ""),
            org_id=org_id,
        )
