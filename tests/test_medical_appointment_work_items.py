from __future__ import annotations

import sqlite3

from backend.modules.medical import work_items
from backend.modules.reminders import repository


def test_medical_appointment_projection_is_stable_and_uses_reminder_lead_day(monkeypatch):
    calls = []
    monkeypatch.setattr(
        work_items,
        "sync_active_reminder",
        lambda **kwargs: calls.append(kwargs) or kwargs["reminder_id"],
    )
    record = {
        "id": "appointment-1",
        "client_id": "backend-client-key",
        "case_manager_id": "case-manager-1",
        "appointment_type": "Primary care",
        "provider_name": "Dr. Rivera",
        "appointment_date": "2026-08-10",
        "appointment_time": "09:30",
        "status": "scheduled",
        "reminder_enabled": 1,
    }

    first_id = work_items.sync_medical_appointment_reminder(record, source="medical")
    second_id = work_items.sync_medical_appointment_reminder(record, source="medical")

    assert first_id == second_id
    assert calls[0]["due_date"] == "2026-08-09"
    assert calls[0]["active"] is True
    assert "backend-client-key" not in calls[0]["message"]
    assert calls[0]["message"] == "Primary care with Dr. Rivera on 2026-08-10 at 09:30"


def test_cancelled_or_disabled_appointment_removes_projection(monkeypatch):
    calls = []
    monkeypatch.setattr(
        work_items,
        "sync_active_reminder",
        lambda **kwargs: calls.append(kwargs) or kwargs["reminder_id"],
    )
    base = {
        "apt_id": "appointment-2",
        "client_id": "backend-client-key",
        "title": "Dental appointment",
        "appointment_date": "2026-08-12",
    }

    work_items.sync_medical_appointment_reminder(
        {**base, "status": "cancelled"},
        source="workspace",
        case_manager_id="case-manager-1",
    )
    work_items.sync_medical_appointment_reminder(
        {**base, "status": "scheduled", "reminder_enabled": 0},
        source="workspace",
        case_manager_id="case-manager-1",
    )

    assert [call["active"] for call in calls] == [False, False]


def test_reconcile_projects_medical_and_workspace_appointments(monkeypatch, tmp_path):
    db_path = tmp_path / "case_management.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE appointments (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                case_manager_id TEXT,
                appointment_type TEXT,
                provider_name TEXT,
                appointment_date TEXT,
                appointment_time TEXT,
                status TEXT,
                reminder_enabled INTEGER
            )
            """
        )
        conn.execute(
            """
            INSERT INTO appointments VALUES
            ('medical-1', 'client-1', 'case-manager-1', 'Psychiatry', 'Dr. Lee',
             '2026-08-15', '14:00', 'scheduled', 1)
            """
        )
        conn.commit()

    calls = []
    monkeypatch.setattr(work_items, "CASE_MGMT_DB_PATH", db_path)
    monkeypatch.setattr(
        work_items,
        "sync_medical_appointment_reminder",
        lambda record, **kwargs: calls.append((record, kwargs)) or "reminder",
    )
    monkeypatch.setattr(
        work_items.workspace_store,
        "list_client_appointments",
        lambda client_id: [
            {
                "apt_id": f"workspace-{client_id}",
                "client_id": client_id,
                "title": "Dental",
                "appointment_date": "2026-08-16",
                "status": "scheduled",
            }
        ],
    )

    work_items.reconcile_medical_appointment_reminders(
        "case-manager-1", ["client-1"], org_id="org-1"
    )

    assert len(calls) == 2
    assert calls[0][1] == {"source": "medical", "org_id": "org-1"}
    assert calls[1][1] == {
        "source": "workspace",
        "case_manager_id": "case-manager-1",
        "org_id": "org-1",
    }


def test_stable_projection_follows_case_manager_reassignment_without_reopening(monkeypatch):
    monkeypatch.setattr(
        repository,
        "get_active_reminder",
        lambda _reminder_id: {
            "client_id": "client-1",
            "case_manager_id": "old-case-manager",
            "message": "Psychiatry on 2026-08-15",
            "due_date": "2026-08-14",
            "priority": "High",
            "reminder_type": "Medical Appointment",
            "status": "Completed",
        },
    )
    updates = []
    monkeypatch.setattr(
        repository,
        "update_active_reminder",
        lambda *args, **kwargs: updates.append(kwargs) or True,
    )
    reopened = []
    monkeypatch.setattr(
        repository,
        "reopen_active_reminder",
        lambda *args, **kwargs: reopened.append(args) or True,
    )

    repository.sync_active_reminder(
        reminder_id="stable-reminder",
        client_id="client-1",
        case_manager_id="new-case-manager",
        reminder_type="Medical Appointment",
        message="Psychiatry on 2026-08-15",
        priority="High",
        due_date="2026-08-14",
    )

    assert updates[0]["case_manager_id"] == "new-case-manager"
    assert reopened == []
