"""Resume Builder import / AI rewrite / save / retrieval workflow tests.

Covers the fixes for the broken Resume Builder import pipeline:
- import populates the builder profile and persists it for the selected client
  (including the first-import CREATE fallback that previously dropped data)
- unsupported file types return a friendly 400
- `ai_rewrite_applied` is honest: False when the AI rewrite did not run
- /rewrite-profile fails loudly (503) instead of claiming a rewrite happened
- profile reads return no fabricated placeholder content
- no cross-client leakage

DB access is isolated to a tmp dir (backend.shared.db_path.DB_DIR for the
clients API + backend.shared.database.new_access_layer.DATABASES_DIR for the
resume bridge; authorization.CORE_CLIENTS_DB is patched to match).
"""
import io
import os
import sqlite3
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.shared.db_path as db_path_mod
import backend.shared.database.new_access_layer as nal
from backend.api import clients as clients_api
from backend.auth import authorization as authz
from backend.auth.service import AuthenticatedUser
from backend.modules.resume import routes as resume_routes
# Import the bridge eagerly so its `shared.database.new_access_layer` module
# instance exists before the fixture patches DATABASES_DIR on it.
import backend.services.resume_client_bridge  # noqa: F401
from backend.shared.tenancy import DEFAULT_ORG_ID


def _user(case_manager_id="cm_a", role="admin"):
    return AuthenticatedUser(
        firebase_uid=f"uid-{case_manager_id}",
        email=f"{case_manager_id}@example.test",
        full_name="Test User",
        role=role,
        case_manager_id=case_manager_id,
        auth_provider="test",
        is_active=True,
        org_id=DEFAULT_ORG_ID,
        org_role="org_admin" if role == "admin" else "member",
    )


EMPLOYMENT_SCHEMA = """
CREATE TABLE IF NOT EXISTS client_employment_profiles (
    profile_id TEXT PRIMARY KEY,
    client_id TEXT,
    work_history TEXT,
    skills TEXT,
    education TEXT,
    preferred_industries TEXT,
    background_friendly_only INTEGER,
    created_at TEXT,
    certifications TEXT,
    career_objective TEXT,
    updated_at TEXT,
    professional_references TEXT
);
CREATE TABLE IF NOT EXISTS resumes (
    resume_id TEXT PRIMARY KEY,
    client_id TEXT,
    template_type TEXT,
    content TEXT,
    pdf_path TEXT,
    created_at TEXT,
    profile_id TEXT,
    resume_title TEXT,
    ats_score INTEGER,
    is_active INTEGER,
    updated_at TEXT
);
"""


def _seed_client(client_id, case_manager_id="cm_a"):
    with clients_api.get_database_connection("core_clients", "ADMIN") as conn:
        clients_api.ensure_core_clients_schema(conn)
        conn.execute(
            """
            INSERT INTO clients (client_id, first_name, last_name, case_manager_id,
                                 org_id, intake_date, created_at)
            VALUES (?, 'Import', 'TestClient', ?, ?, '2026-01-01', '2026-01-01T00:00:00')
            """,
            (client_id, case_manager_id, DEFAULT_ORG_ID),
        )
        conn.commit()


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.setattr(db_path_mod, "DB_DIR", tmp_path)
    monkeypatch.setattr(nal, "DATABASES_DIR", tmp_path)
    # The resume bridge imports the access layer as `shared.database...` (it
    # appends backend/ to sys.path), which is a separate module instance from
    # `backend.shared.database...` — patch every loaded instance.
    for mod_name in ("shared.database.new_access_layer",):
        alt = sys.modules.get(mod_name)
        if alt is not None:
            monkeypatch.setattr(alt, "DATABASES_DIR", tmp_path)
    monkeypatch.setattr(authz, "CORE_CLIENTS_DB", tmp_path / "core_clients.db")
    # Reset the module-level cached DB handle so it binds to the tmp dir.
    monkeypatch.setattr(resume_routes, "employment_db", None)
    # No AI configured in tests: rewrites must be reported honestly.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    conn = sqlite3.connect(tmp_path / "employment.db")
    conn.executescript(EMPLOYMENT_SCHEMA)
    conn.commit()
    conn.close()

    # Keep uploaded temp files out of the repo tree during tests.
    from backend.modules.resume import file_processor as fp_mod

    def _tmp_upload_init(self):
        self.upload_dir = str(tmp_path / "uploads")
        os.makedirs(self.upload_dir, exist_ok=True)

    monkeypatch.setattr(fp_mod.ResumeFileProcessor, "__init__", _tmp_upload_init)

    holder = {"user": _user()}
    app = FastAPI()

    @app.middleware("http")
    async def inject(request, call_next):
        if holder["user"] is not None:
            request.state.auth_user = holder["user"]
        return await call_next(request)

    app.include_router(resume_routes.router, prefix="/api/resume")
    app.include_router(clients_api.router)
    return TestClient(app), holder


def _docx_bytes(paragraphs):
    from docx import Document

    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


RESUME_PARAGRAPHS = [
    "Import TestClient",
    "SUMMARY",
    "Dependable warehouse associate with forklift experience.",
    "EXPERIENCE",
    "Warehouse Associate - Acme Logistics",
    "2021 - 2023",
    "Picked and packed orders, operated forklifts, maintained safety standards.",
    "SKILLS",
    "Forklift operation, Inventory management, Teamwork",
    "EDUCATION",
    "Van Nuys High School - Diploma",
]


def _import_resume(client, client_id, ai_rewrite=False, filename="resume.docx", payload=None):
    payload = payload if payload is not None else _docx_bytes(RESUME_PARAGRAPHS)
    return client.post(
        f"/api/resume/import?client_id={client_id}&ai_rewrite={'true' if ai_rewrite else 'false'}",
        files={
            "resume_file": (
                filename,
                payload,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )


# ── Import ───────────────────────────────────────────────────────────────────

def test_import_docx_populates_profile_and_persists(ctx):
    client, _ = ctx
    _seed_client("c1")

    resp = _import_resume(client, "c1")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["success"] is True
    assert "forklift" in data["raw_text"].lower()
    assert isinstance(data["profile"], dict)
    assert data["client_id"] == "c1"

    # Persistence proof: first import for a client with no prior profile must
    # be retrievable after a fresh read (previously dropped by a 0-row UPDATE).
    read = client.get("/api/resume/profile/c1")
    assert read.status_code == 200, read.text
    stored = read.json()["profile"]
    assert stored is not None, "imported profile was not persisted"
    assert stored["client_id"] == "c1"
    stored_blob = str(stored).lower()
    assert "forklift" in stored_blob or "warehouse" in stored_blob


def test_import_unsupported_file_type_friendly_error(ctx):
    client, _ = ctx
    _seed_client("c1")
    resp = _import_resume(client, "c1", filename="resume.txt", payload=b"plain text resume")
    assert resp.status_code == 400
    assert "Unsupported file format" in resp.json()["detail"]


def test_import_empty_file_friendly_error(ctx):
    client, _ = ctx
    _seed_client("c1")
    resp = _import_resume(client, "c1", filename="resume.docx", payload=b"")
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


# ── Import + AI rewrite honesty ──────────────────────────────────────────────

def test_import_ai_rewrite_flag_is_honest_when_ai_unavailable(ctx):
    client, _ = ctx
    _seed_client("c1")
    resp = _import_resume(client, "c1", ai_rewrite=True)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Import succeeds, but the response must not claim an AI rewrite happened.
    assert data["success"] is True
    assert data["ai_rewrite_applied"] is False


def test_rewrite_profile_fails_loudly_when_ai_unavailable(ctx):
    client, _ = ctx
    _seed_client("c1")
    resp = client.post(
        "/api/resume/rewrite-profile",
        json={
            "client_id": "c1",
            "instructions": "Rewrite for warehouse jobs",
            "profile": {"career_objective": "original objective", "work_history": []},
        },
    )
    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"].lower()
    # Nothing may be persisted on a failed rewrite.
    read = client.get("/api/resume/profile/c1")
    assert read.json()["profile"] is None


def test_rewrite_profile_requires_instructions(ctx):
    client, _ = ctx
    _seed_client("c1")
    resp = client.post(
        "/api/resume/rewrite-profile",
        json={"client_id": "c1", "instructions": "   ", "profile": {}},
    )
    assert resp.status_code == 400


# ── Save + retrieval ─────────────────────────────────────────────────────────

def test_save_profile_roundtrip(ctx):
    client, _ = ctx
    _seed_client("c1")
    payload = {
        "client_id": "c1",
        "career_objective": "Entry-level office administration",
        "work_history": [
            {
                "job_title": "Office Clerk",
                "company": "Valley Nonprofit",
                "start_date": "2022",
                "end_date": "2024",
                "description": "Filing, scheduling, phones",
                "achievements": [],
            }
        ],
        "skills": [{"category": "Office", "skill_list": ["Filing", "Scheduling"]}],
        "education": [],
        "certifications": [],
        "professional_references": [],
        "preferred_industries": ["Administration"],
    }
    save = client.post("/api/resume/profile", json=payload)
    assert save.status_code == 200, save.text
    assert save.json()["success"] is True

    read = client.get("/api/resume/profile/c1")
    stored = read.json()["profile"]
    assert stored["career_objective"] == "Entry-level office administration"
    assert stored["work_history"][0]["company"] == "Valley Nonprofit"

    # Saving again must update, not duplicate.
    payload["career_objective"] = "Updated objective"
    assert client.post("/api/resume/profile", json=payload).status_code == 200
    assert client.get("/api/resume/profile/c1").json()["profile"]["career_objective"] == "Updated objective"


def test_profile_read_returns_no_fabricated_content(ctx):
    client, _ = ctx
    _seed_client("c-empty")
    read = client.get("/api/resume/profile/c-empty")
    assert read.status_code == 200
    body = read.json()
    # Previously a fake "Professional seeking opportunities..." profile was served.
    assert body["profile"] is None


def test_no_cross_client_leakage(ctx):
    client, _ = ctx
    _seed_client("c1")
    _seed_client("c2")
    assert _import_resume(client, "c1").status_code == 200

    other = client.get("/api/resume/profile/c2").json()["profile"]
    assert other is None, "client c2 must not see c1's imported resume profile"


# ── Client Dashboard Employment tab propagation ──────────────────────────────

def test_unified_view_includes_saved_resumes(ctx, tmp_path):
    client, _ = ctx
    _seed_client("c1")
    conn = sqlite3.connect(tmp_path / "employment.db")
    conn.execute(
        """
        INSERT INTO resumes (resume_id, client_id, template_type, content, created_at,
                             resume_title, ats_score, is_active, updated_at)
        VALUES ('r-1', 'c1', 'classic', '{}', '2026-06-30T12:00:00',
                'Classic Professional Resume', 80, 1, '2026-06-30T12:00:00')
        """
    )
    conn.commit()
    conn.close()

    resp = client.get("/api/clients/c1/unified-view")
    assert resp.status_code == 200, resp.text
    employment = resp.json()["client_data"]["employment"]
    resumes = employment.get("resumes") or []
    assert any(r["resume_id"] == "r-1" for r in resumes)
    hit = next(r for r in resumes if r["resume_id"] == "r-1")
    assert hit["resume_name"] == "Classic Professional Resume"
    assert hit["download_url"] == "/api/resume/download/r-1"


def test_unified_view_no_resumes_keeps_prior_shape(ctx):
    client, _ = ctx
    _seed_client("c1")
    resp = client.get("/api/clients/c1/unified-view")
    assert resp.status_code == 200, resp.text
    employment = resp.json()["client_data"]["employment"]
    # Empty state unchanged: key omitted so the dashboard's conditional
    # "Resumes" section does not render an empty block.
    assert "resumes" not in employment
