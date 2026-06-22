"""Owner Support Queue v1 tests.

Covers the support store sanitization, the authenticated ``POST
/api/support/tickets`` endpoint, and the super-admin-only owner endpoints
(``GET /api/owner/support/tickets``, ``GET /api/owner/support/summary``,
``PATCH /api/owner/support/tickets/{id}``). ``DB_DIR`` is repointed at a tmp dir so
the support SQLite file is throwaway. No Stripe env var is required and no Stripe
code is exercised — the "billing" category is just a tag.
"""
import json
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.support.routes as support_routes
import backend.support.store as support_store_mod
import backend.shared.db_path as db_path_mod
from backend.support.store import SupportStore, sanitize_extra, scan_phi_risk
from backend.auth.service import (
    AuthenticatedUser,
    FirebaseAuthService,
    ORG_ADMIN_ROLE,
    ORG_MEMBER_ROLE,
)
from backend.shared.tenancy import DEFAULT_ORG_ID

SUPER_EMAIL = "blackulaphotography@gmail.com"
PHI_KEYS = ("first_name", "last_name", "client_name", "ssn", "dob", "diagnosis", "note")
SECRET_KEYS = ("sk_live", "sk_test", "whsec_", "api_key", "secret_key")


def _token(uid, email, name="User"):
    return {"uid": uid, "email": email, "name": name}


def _super_admin_user():
    return AuthenticatedUser(
        firebase_uid="owner", email=SUPER_EMAIL, full_name="Owner", role="admin",
        case_manager_id="cm_owner", auth_provider="test", is_active=True,
        org_id=DEFAULT_ORG_ID, org_role=ORG_ADMIN_ROLE,
    )


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp_path)

    # Only used to mint realistic AuthenticatedUser objects to inject via middleware.
    # The routes call the real require_user / require_super_admin (which read
    # request.state.auth_user and the genuine platform super-admin allowlist).
    svc = FirebaseAuthService(db_path=tmp_path / "auth.db")

    store = SupportStore()
    monkeypatch.setattr(support_store_mod, "support_store", store)
    monkeypatch.setattr(support_routes, "support_store", store)

    # A normal org + member to file tickets as.
    svc.upsert_profile_from_token(_token("admin_a", "admin_a@a.test", "Admin A"))
    oa = svc.create_organization("admin_a", "Org A", "case_management_agency").org_id
    svc.upsert_profile_from_token(_token("m_a", "m_a@a.test", "Member A"))
    inv = svc.create_invite(oa, "m_a@a.test", ORG_MEMBER_ROLE, invited_by="admin_a")
    svc.accept_invite("m_a", inv["token"])

    holder = {"user": None}
    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        if holder["user"] is not None:
            request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(support_routes.ticket_router)
    app.include_router(support_routes.owner_router)
    client = TestClient(app)

    def as_user(uid):
        holder["user"] = svc.get_profile_by_uid(uid)

    def as_super():
        holder["user"] = _super_admin_user()

    return {"svc": svc, "store": store, "client": client, "holder": holder,
            "as_user": as_user, "as_super": as_super, "oa": oa}


# ── Store-level sanitization (pure, no DB) ───────────────────────────────────

def test_sanitize_extra_strips_phi_keys():
    clean, dropped = sanitize_extra({
        "client_name": "John Doe",
        "ssn": "111-22-3333",
        "note": "private",
        "browser": "Chrome",   # safe
        "build": 42,           # safe
    })
    assert clean == {"browser": "Chrome", "build": 42}
    for k in ("client_name", "ssn", "note"):
        assert k in dropped and k not in clean


def test_sanitize_extra_drops_nested_and_caps_length():
    clean, _ = sanitize_extra({"nested": {"a": 1}, "list": [1, 2], "long": "x" * 999})
    assert "nested" not in clean and "list" not in clean
    assert len(clean["long"]) <= 200


# ── Free-text PHI-risk scanner (pure, no DB) ─────────────────────────────────

@pytest.mark.parametrize("text", [
    "Client DOB is 1990-01-01",
    "patient name is hidden",
    "His SSN 123-45-6789 shows up",
    "social security number leaked",
    "MRN 4455 not matching",
    "see the medical record attached",
    "call me at 555-123-4567",
    "reach me at (555) 123-4567",
    "phone 5551234567 broken",
    "email me jane@example.com",
    "the client is John and it broke",
    "case note text is wrong",
    "progress note won't save",
])
def test_scan_phi_risk_flags_unsafe_text(text):
    assert scan_phi_risk(text) is not None


@pytest.mark.parametrize("text", [
    "The client page is broken",
    "Case management module won't load",
    "Dashboard crashes when I click save",
    "Feature request: dark mode please",
    "The billing tab shows an error",
    "Login button does nothing",
    "",
    None,
])
def test_scan_phi_risk_allows_ordinary_support_text(text):
    assert scan_phi_risk(text) is None


# ── Ticket creation endpoint ─────────────────────────────────────────────────

def test_create_requires_auth(env):
    c = env["client"]
    env["holder"]["user"] = None
    r = c.post("/api/support/tickets", json={
        "category": "bug", "subject": "x", "description": "y",
    })
    assert r.status_code == 401


def test_create_persists_and_derives_identity(env):
    c = env["client"]
    env["as_user"]("admin_a")
    r = c.post("/api/support/tickets", json={
        "category": "bug", "priority": "high",
        "subject": "Login button does nothing", "description": "Clicking sign-in fails.",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True and body["ticket_id"] >= 1
    assert body["status"] == "open"

    # Identity derived from token, not the body.
    with sqlite3.connect(env["store"]._db_path()) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM support_tickets").fetchone()
    assert row["category"] == "bug" and row["priority"] == "high"
    assert row["status"] == "open"
    assert row["org_id"] == env["oa"]
    assert row["submitted_by_user_id"] == env["svc"].get_profile_by_uid("admin_a").case_manager_id
    assert row["submitted_by_email"] == "admin_a@a.test"


def test_create_rejects_unknown_category(env):
    c = env["client"]
    env["as_user"]("admin_a")
    r = c.post("/api/support/tickets", json={
        "category": "not_a_category", "subject": "x", "description": "y",
    })
    assert r.status_code == 422
    assert env["store"].summary()["total_tickets"] == 0


def test_create_rejects_unknown_priority(env):
    c = env["client"]
    env["as_user"]("admin_a")
    r = c.post("/api/support/tickets", json={
        "category": "bug", "priority": "super_urgent", "subject": "x", "description": "y",
    })
    assert r.status_code == 422
    assert env["store"].summary()["total_tickets"] == 0


def test_user_cannot_set_owner_only_fields(env):
    c = env["client"]
    env["as_user"]("admin_a")
    # Attempt to smuggle status / assigned_to / internal_notes / resolved_at.
    r = c.post("/api/support/tickets", json={
        "category": "feature_request", "subject": "Dark mode", "description": "Please.",
        "status": "closed", "assigned_to": "ceo", "internal_notes": "ignore me",
        "resolved_at": "2020-01-01",
    })
    assert r.status_code == 200
    ticket = env["store"].get_ticket(r.json()["ticket_id"])
    # None of the owner-only fields took effect — safe defaults instead.
    assert ticket["status"] == "open"
    assert ticket["assigned_to"] is None
    assert ticket["internal_notes"] is None
    assert ticket["resolved_at"] is None


def test_create_strips_phi_extra_metadata(env):
    c = env["client"]
    env["as_user"]("admin_a")
    r = c.post("/api/support/tickets", json={
        "category": "bug", "subject": "Crash", "description": "App crashes.",
        "extra": {
            "client_name": "John Doe",
            "ssn": "111-22-3333",
            "note_text": "confidential",
            "browser": "Firefox",   # safe survivor
        },
    })
    assert r.status_code == 200
    assert set(r.json()["dropped_metadata_keys"]) >= {"client_name", "ssn", "note_text"}
    with sqlite3.connect(env["store"]._db_path()) as conn:
        row = conn.execute("SELECT extra_json FROM support_tickets").fetchone()
    blob = (row[0] or "").lower()
    assert "john doe" not in blob and "111-22-3333" not in blob
    assert not any(k in blob for k in PHI_KEYS)
    assert "firefox" in blob  # the safe key survived


def test_create_length_caps_fields(env):
    c = env["client"]
    env["as_user"]("admin_a")
    # Subject over the 200-char Field cap is a 422 at the model layer.
    r = c.post("/api/support/tickets", json={
        "category": "other", "subject": "x" * 500, "description": "y",
    })
    assert r.status_code == 422


def test_create_rejects_phi_in_description(env):
    c = env["client"]
    env["as_user"]("admin_a")
    r = c.post("/api/support/tickets", json={
        "category": "bug", "subject": "Profile bug",
        "description": "The client DOB 1990-01-01 and SSN 123-45-6789 are wrong.",
    })
    assert r.status_code == 422
    assert r.json()["phi_risk"]
    assert env["store"].summary()["total_tickets"] == 0


def test_create_rejects_phi_in_subject(env):
    c = env["client"]
    env["as_user"]("admin_a")
    r = c.post("/api/support/tickets", json={
        "category": "bug", "subject": "patient name shows on wrong page",
        "description": "Generic issue text.",
    })
    assert r.status_code == 422
    assert env["store"].summary()["total_tickets"] == 0


def test_create_rejects_contact_info_in_description(env):
    c = env["client"]
    env["as_user"]("admin_a")
    r = c.post("/api/support/tickets", json={
        "category": "account", "subject": "Cannot log in",
        "description": "Call me at 555-123-4567 or jane@example.com.",
    })
    assert r.status_code == 422


def test_create_allows_ordinary_support_language(env):
    c = env["client"]
    env["as_user"]("admin_a")
    r = c.post("/api/support/tickets", json={
        "category": "bug", "subject": "Client page is broken",
        "description": "The case management module won't load when I click save.",
    })
    assert r.status_code == 200
    assert env["store"].summary()["total_tickets"] == 1


# ── Owner endpoints: authorization ───────────────────────────────────────────

def test_owner_summary_unauthenticated_401(env):
    c = env["client"]
    env["holder"]["user"] = None
    assert c.get("/api/owner/support/summary").status_code == 401


def test_owner_summary_requires_super_admin(env):
    c = env["client"]
    env["as_user"]("admin_a")  # org admin, not platform owner
    assert c.get("/api/owner/support/summary").status_code == 403


def test_owner_list_requires_super_admin(env):
    c = env["client"]
    env["as_user"]("admin_a")
    assert c.get("/api/owner/support/tickets").status_code == 403


def test_owner_patch_requires_super_admin(env):
    c = env["client"]
    env["as_user"]("admin_a")
    tid = env["store"].create_ticket(
        category="bug", priority="normal", subject="s", description="d"
    )["ticket_id"]
    assert c.patch(f"/api/owner/support/tickets/{tid}", json={"status": "resolved"}).status_code == 403


# ── Owner endpoints: content + triage ────────────────────────────────────────

def test_owner_summary_empty_state(env):
    c = env["client"]
    env["as_super"]()
    body = c.get("/api/owner/support/summary").json()
    assert body["success"] is True
    assert body["total_tickets"] == 0
    assert body["open_tickets"] == 0
    assert body["high_priority_tickets"] == 0
    assert body["recent_tickets"] == []
    # Breakdowns seed every known value at zero so the UI sees the full set.
    assert body["by_status"]["open"] == 0
    assert body["by_category"]["bug"] == 0
    assert body["stripe_activated"] is False


def test_owner_summary_counts_after_tickets(env):
    c = env["client"]
    env["as_user"]("admin_a")
    c.post("/api/support/tickets", json={"category": "bug", "priority": "urgent", "subject": "A", "description": "d"})
    c.post("/api/support/tickets", json={"category": "billing", "priority": "high", "subject": "B", "description": "d"})
    c.post("/api/support/tickets", json={"category": "other", "priority": "low", "subject": "C", "description": "d"})

    env["as_super"]()
    body = c.get("/api/owner/support/summary").json()
    assert body["total_tickets"] == 3
    assert body["open_tickets"] == 3
    assert body["high_priority_tickets"] == 2   # urgent + high
    assert body["by_category"]["bug"] == 1
    assert body["by_category"]["billing"] == 1
    assert len(body["recent_tickets"]) == 3
    # Recent feed is light — no description / internal_notes leaked.
    assert set(body["recent_tickets"][0].keys()) == {
        "id", "category", "priority", "status", "subject", "assigned_to",
        "created_at", "updated_at",
    }


def test_owner_list_returns_full_rows(env):
    c = env["client"]
    env["as_user"]("admin_a")
    c.post("/api/support/tickets", json={"category": "bug", "subject": "A", "description": "details"})
    env["as_super"]()
    body = c.get("/api/owner/support/tickets").json()
    assert body["success"] is True and body["count"] == 1
    t = body["tickets"][0]
    assert t["description"] == "details"
    assert t["category"] == "bug"


def test_owner_patch_updates_status_and_priority(env):
    c = env["client"]
    env["as_user"]("admin_a")
    tid = c.post("/api/support/tickets", json={
        "category": "bug", "subject": "A", "description": "d",
    }).json()["ticket_id"]

    env["as_super"]()
    r = c.patch(f"/api/owner/support/tickets/{tid}", json={
        "status": "in_progress", "priority": "urgent",
        "assigned_to": "owner", "internal_notes": "looking into it",
    })
    assert r.status_code == 200
    t = r.json()["ticket"]
    assert t["status"] == "in_progress"
    assert t["priority"] == "urgent"
    assert t["assigned_to"] == "owner"
    assert t["internal_notes"] == "looking into it"
    assert t["resolved_at"] is None


def test_owner_patch_stamps_and_clears_resolved_at(env):
    c = env["client"]
    env["as_user"]("admin_a")
    tid = c.post("/api/support/tickets", json={
        "category": "bug", "subject": "A", "description": "d",
    }).json()["ticket_id"]

    env["as_super"]()
    resolved = c.patch(f"/api/owner/support/tickets/{tid}", json={"status": "resolved"}).json()["ticket"]
    assert resolved["resolved_at"] is not None
    # Reopening clears resolved_at again.
    reopened = c.patch(f"/api/owner/support/tickets/{tid}", json={"status": "open"}).json()["ticket"]
    assert reopened["resolved_at"] is None


def test_owner_patch_rejects_unknown_status(env):
    c = env["client"]
    env["as_user"]("admin_a")
    tid = c.post("/api/support/tickets", json={
        "category": "bug", "subject": "A", "description": "d",
    }).json()["ticket_id"]
    env["as_super"]()
    r = c.patch(f"/api/owner/support/tickets/{tid}", json={"status": "banana"})
    assert r.status_code == 422


def test_owner_patch_rejects_phi_internal_note(env):
    c = env["client"]
    env["as_user"]("admin_a")
    tid = c.post("/api/support/tickets", json={
        "category": "bug", "subject": "A", "description": "d",
    }).json()["ticket_id"]
    env["as_super"]()
    r = c.patch(f"/api/owner/support/tickets/{tid}", json={
        "internal_notes": "client name is John Doe, SSN 123-45-6789",
    })
    assert r.status_code == 422
    assert r.json()["phi_risk"]
    # The unsafe note was not persisted.
    assert env["store"].get_ticket(tid)["internal_notes"] is None


def test_owner_patch_allows_normal_internal_note(env):
    c = env["client"]
    env["as_user"]("admin_a")
    tid = c.post("/api/support/tickets", json={
        "category": "bug", "subject": "A", "description": "d",
    }).json()["ticket_id"]
    env["as_super"]()
    r = c.patch(f"/api/owner/support/tickets/{tid}", json={
        "internal_notes": "Reproduced on staging, escalating to engineering.",
    })
    assert r.status_code == 200
    assert env["store"].get_ticket(tid)["internal_notes"].startswith("Reproduced")


def test_owner_recent_tickets_omit_description(env):
    c = env["client"]
    env["as_user"]("admin_a")
    c.post("/api/support/tickets", json={
        "category": "bug", "subject": "Visible subject", "description": "Hidden description body.",
    })
    env["as_super"]()
    body = c.get("/api/owner/support/summary").json()
    recent = body["recent_tickets"]
    assert len(recent) == 1
    # The recent feed must not expose full description text.
    assert "description" not in recent[0]
    blob = json.dumps(recent).lower()
    assert "hidden description body" not in blob


def test_owner_patch_missing_ticket_404(env):
    c = env["client"]
    env["as_super"]()
    r = c.patch("/api/owner/support/tickets/99999", json={"status": "resolved"})
    assert r.status_code == 404


def test_owner_summary_has_no_stripe_secrets(env):
    c = env["client"]
    env["as_super"]()
    body = c.get("/api/owner/support/summary").json()
    blob = json.dumps(body).lower()
    assert not any(k in blob for k in SECRET_KEYS)
