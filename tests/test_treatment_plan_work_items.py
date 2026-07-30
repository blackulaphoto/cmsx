from __future__ import annotations

from backend.modules.treatment_plan import work_items


def _plan(**overrides):
    plan = {
        "plan_id": "plan-1",
        "client_id": "backend-client-key",
        "status": "active",
        "review_due_date": "2026-08-20",
    }
    plan.update(overrides)
    return plan


def test_approved_plan_review_projects_stable_named_reminder(monkeypatch):
    calls = []
    monkeypatch.setattr(
        work_items,
        "sync_active_reminder",
        lambda **kwargs: calls.append(kwargs) or kwargs["reminder_id"],
    )

    first_id = work_items.sync_treatment_plan_review_reminder(
        _plan(),
        case_manager_id="case-manager-1",
        client_name="Jordan Rivera",
    )
    second_id = work_items.sync_treatment_plan_review_reminder(
        _plan(),
        case_manager_id="case-manager-1",
        client_name="Jordan Rivera",
    )

    assert first_id == second_id == "treatment-plan:plan-1:review"
    assert calls[0]["message"] == "Treatment plan review due for Jordan Rivera"
    assert "backend-client-key" not in calls[0]["message"]
    assert calls[0]["due_date"] == "2026-08-20"
    assert calls[0]["active"] is True


def test_draft_missing_date_and_superseded_plans_do_not_project(monkeypatch):
    calls = []
    monkeypatch.setattr(
        work_items,
        "sync_active_reminder",
        lambda **kwargs: calls.append(kwargs) or kwargs["reminder_id"],
    )

    work_items.sync_treatment_plan_review_reminder(
        _plan(status="draft"),
        case_manager_id="case-manager-1",
    )
    work_items.sync_treatment_plan_review_reminder(
        _plan(review_due_date=None),
        case_manager_id="case-manager-1",
    )
    work_items.sync_treatment_plan_review_reminder(
        _plan(status="superseded"),
        case_manager_id="case-manager-1",
    )

    assert [call["active"] for call in calls] == [False, False, False]


def test_client_sync_removes_old_plan_and_keeps_current_plan(monkeypatch):
    calls = []
    monkeypatch.setattr(
        work_items.workspace_store,
        "list_client_treatment_plans",
        lambda _client_id: [
            _plan(plan_id="current-plan"),
            _plan(plan_id="old-plan", status="superseded"),
        ],
    )
    monkeypatch.setattr(
        work_items,
        "sync_treatment_plan_review_reminder",
        lambda plan, **kwargs: calls.append((plan, kwargs)) or plan["plan_id"],
    )

    work_items.sync_client_treatment_plan_review_reminders(
        "backend-client-key",
        case_manager_id="case-manager-1",
        client_name="Jordan Rivera",
        org_id="org-1",
    )

    assert [plan["plan_id"] for plan, _ in calls] == ["current-plan", "old-plan"]
    assert all(call[1]["client_name"] == "Jordan Rivera" for call in calls)
    assert all(call[1]["org_id"] == "org-1" for call in calls)


def test_reconcile_uses_canonical_client_names(monkeypatch):
    calls = []
    monkeypatch.setattr(
        work_items,
        "sync_client_treatment_plan_review_reminders",
        lambda client_id, **kwargs: calls.append((client_id, kwargs)),
    )

    work_items.reconcile_treatment_plan_review_reminders(
        "case-manager-1",
        ["client-1", "client-2"],
        {"client-1": "Jordan Rivera", "client-2": "Taylor Morgan"},
        org_id="org-1",
    )

    assert calls == [
        (
            "client-1",
            {
                "case_manager_id": "case-manager-1",
                "client_name": "Jordan Rivera",
                "org_id": "org-1",
            },
        ),
        (
            "client-2",
            {
                "case_manager_id": "case-manager-1",
                "client_name": "Taylor Morgan",
                "org_id": "org-1",
            },
        ),
    ]
