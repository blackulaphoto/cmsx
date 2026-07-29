from backend.modules.fmla import work_items


def _case(**overrides):
    record = {
        "case_id": "fmla-case-1",
        "case_subject_type": "client",
        "client_id": "client-1",
        "client_name": "John Collins",
        "assigned_case_manager": "cm-1",
        "org_id": "org-1",
        "status": "submitted",
        "approval_status": "pending",
        "paperwork_deadline": "2026-08-01",
        "paperwork_completed_date": "",
        "employer_response_deadline": "2026-08-03",
        "certification_expiration_date": "2026-09-01",
        "return_to_work_date": "2026-09-05",
    }
    record.update(overrides)
    return record


def test_sync_fmla_deadlines_projects_only_actionable_dates(monkeypatch):
    calls = []
    monkeypatch.setattr(work_items, "sync_active_reminder", lambda **kwargs: calls.append(kwargs))

    work_items.sync_fmla_deadline_reminders(_case())

    assert [call["reminder_id"] for call in calls] == [
        "fmla:fmla-case-1:paperwork",
        "fmla:fmla-case-1:employer_response",
        "fmla:fmla-case-1:certification_expiration",
        "fmla:fmla-case-1:return_to_work",
    ]
    assert calls[0]["message"] == "FMLA paperwork due for John Collins"
    assert calls[0]["active"] is True
    assert calls[1]["active"] is True
    assert calls[2]["active"] is True
    assert calls[3]["active"] is False


def test_sync_fmla_deadlines_respects_completion_conditions(monkeypatch):
    calls = []
    monkeypatch.setattr(work_items, "sync_active_reminder", lambda **kwargs: calls.append(kwargs))

    work_items.sync_fmla_deadline_reminders(
        _case(
            status="approved",
            approval_status="approved",
            paperwork_completed_date="2026-07-30",
        )
    )

    assert calls[0]["active"] is False
    assert calls[1]["active"] is False
    assert calls[2]["active"] is True
    assert calls[3]["active"] is True


def test_sync_fmla_deadlines_removes_client_projections_for_staff_case(monkeypatch):
    calls = []
    monkeypatch.setattr(work_items, "sync_active_reminder", lambda **kwargs: calls.append(kwargs))

    work_items.sync_fmla_deadline_reminders(
        _case(case_subject_type="staff", client_id="")
    )

    assert all(call["active"] is False for call in calls)


def test_sync_fmla_deadlines_removes_projections_for_inactive_case(monkeypatch):
    calls = []
    monkeypatch.setattr(work_items, "sync_active_reminder", lambda **kwargs: calls.append(kwargs))

    work_items.sync_fmla_deadline_reminders(_case(status="denied"))

    assert all(call["active"] is False for call in calls)
