import sqlite3

from backend.modules.ur import work_items
from backend.modules.reminders import repository


def _case(**overrides):
    record = {
        "case_id": "ur-case-1",
        "client_id": "client-1",
        "client_name": "John Collins",
        "assigned_case_manager": "cm-1",
        "org_id": "org-1",
        "status": "approved",
        "next_review_date": "2026-08-01",
        "approved_end_date": "2026-08-05",
        "peer_review_deadline": "",
        "appeal_deadline": "",
    }
    record.update(overrides)
    return record


def test_sync_ur_deadlines_creates_stable_client_reminders(monkeypatch):
    calls = []
    monkeypatch.setattr(work_items, "sync_active_reminder", lambda **kwargs: calls.append(kwargs))

    work_items.sync_ur_deadline_reminders(_case())

    assert [call["reminder_id"] for call in calls] == [
        "ur:ur-case-1:review",
        "ur:ur-case-1:authorization_end",
        "ur:ur-case-1:peer_review",
        "ur:ur-case-1:appeal",
    ]
    assert calls[0]["client_id"] == "client-1"
    assert calls[0]["case_manager_id"] == "cm-1"
    assert calls[0]["message"] == "UR review due for John Collins"
    assert calls[0]["due_date"] == "2026-08-01"
    assert calls[0]["active"] is True
    assert calls[2]["active"] is False


def test_sync_ur_deadlines_closes_projected_items_when_case_closes(monkeypatch):
    calls = []
    monkeypatch.setattr(work_items, "sync_active_reminder", lambda **kwargs: calls.append(kwargs))

    work_items.sync_ur_deadline_reminders(_case(status="closed"))

    assert all(call["active"] is False for call in calls)


def test_sync_ur_deadlines_skips_unlinked_or_unassigned_cases(monkeypatch):
    calls = []
    monkeypatch.setattr(work_items, "sync_active_reminder", lambda **kwargs: calls.append(kwargs))

    work_items.sync_ur_deadline_reminders(_case(client_id=""))
    work_items.sync_ur_deadline_reminders(_case(assigned_case_manager=""))

    assert calls == []


def test_sync_active_reminder_preserves_completed_unchanged_deadline(monkeypatch):
    monkeypatch.setattr(repository, "get_active_reminder", lambda _reminder_id: {
        "message": "UR review due for John Collins",
        "due_date": "2026-08-01",
        "priority": "High",
        "reminder_type": "ur",
        "status": "Completed",
    })
    reopened = []
    monkeypatch.setattr(repository, "reopen_active_reminder", lambda *args, **kwargs: reopened.append(args))

    repository.sync_active_reminder(
        reminder_id="ur:ur-case-1:review",
        client_id="client-1",
        case_manager_id="cm-1",
        reminder_type="ur",
        message="UR review due for John Collins",
        priority="High",
        due_date="2026-08-01",
    )

    assert reopened == []


def test_sync_active_reminder_reopens_completed_changed_deadline(monkeypatch):
    monkeypatch.setattr(repository, "get_active_reminder", lambda _reminder_id: {
        "message": "UR review due for John Collins",
        "due_date": "2026-08-01",
        "priority": "High",
        "reminder_type": "ur",
        "status": "Completed",
    })
    monkeypatch.setattr(repository, "update_active_reminder", lambda *args, **kwargs: True)
    reopened = []
    monkeypatch.setattr(repository, "reopen_active_reminder", lambda *args, **kwargs: reopened.append(args))

    repository.sync_active_reminder(
        reminder_id="ur:ur-case-1:review",
        client_id="client-1",
        case_manager_id="cm-1",
        reminder_type="ur",
        message="UR review due for John Collins",
        priority="High",
        due_date="2026-08-02",
    )

    assert reopened == [("ur:ur-case-1:review",)]


def test_sync_active_reminder_removes_inactive_projection(monkeypatch):
    monkeypatch.setattr(repository, "get_active_reminder", lambda _reminder_id: {"status": "Active"})
    deleted = []
    monkeypatch.setattr(repository, "delete_active_reminder", lambda *args, **kwargs: deleted.append(args))

    repository.sync_active_reminder(
        reminder_id="ur:ur-case-1:review",
        client_id="client-1",
        case_manager_id="cm-1",
        reminder_type="ur",
        message="UR review due for John Collins",
        priority="High",
        due_date=None,
        active=False,
    )

    assert deleted == [("ur:ur-case-1:review",)]


def test_ur_deadline_round_trip_through_sqlite_reminder_store(tmp_path, monkeypatch):
    reminders_path = tmp_path / "reminders.db"
    with sqlite3.connect(reminders_path) as conn:
        conn.execute(
            """
            CREATE TABLE active_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                case_manager_id TEXT NOT NULL,
                reminder_type TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT,
                due_date TEXT,
                status TEXT DEFAULT 'Active',
                created_at TEXT,
                org_id TEXT
            )
            """
        )
    monkeypatch.setattr(repository, "_SQLITE_REMINDERS_PATH", str(reminders_path))
    monkeypatch.setattr(repository, "_sqlite_tenancy_ready", False)
    monkeypatch.setattr(repository, "use_postgres", lambda: False)

    work_items.sync_ur_deadline_reminders(_case())

    review = repository.get_active_reminder("ur:ur-case-1:review")
    assert review["client_id"] == "client-1"
    assert review["due_date"] == "2026-08-01"
    assert review["status"] == "Active"

    work_items.sync_ur_deadline_reminders(_case(status="closed"))

    assert repository.get_active_reminder("ur:ur-case-1:review") is None
