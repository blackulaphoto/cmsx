"""Backend tests for the Phase 1 Client ROI Manager (structured roi_records).

Covers additive table init, CRUD, defensive status derivation, revoked-history
preservation, the printable-form generation route, and the access guard.
"""

from datetime import datetime, timedelta
from io import BytesIO

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import clients as clients_api
from backend.auth.service import FirebaseAuthService
from backend.shared.database import workspace_store as ws_mod
from backend.shared.database.workspace_store import workspace_store


def _test_app(tmp_path):
    service = FirebaseAuthService(tmp_path / "auth.db")
    app = FastAPI()

    @app.middleware("http")
    async def inject_test_auth_user(request, call_next):
        request.state.auth_user = service.test_user_from_request(request)
        return await call_next(request)

    app.include_router(clients_api.router)
    return app


def _headers(case_manager_id="cm_test", email="case.manager@example.test"):
    return {
        "X-Test-Auth-Email": email,
        "X-Test-Auth-Case-Manager-Id": case_manager_id,
        "X-Test-Auth-Role": "case_manager",
    }


def _seed_core_client(client_id="client-roi-1", case_manager_id="cm_test"):
    with clients_api.get_database_connection("core_clients", "ADMIN") as conn:
        clients_api.ensure_core_clients_schema(conn)
        conn.execute(
            """INSERT INTO clients
               (client_id, first_name, last_name, case_manager_id, risk_level,
                intake_date, created_at, date_of_birth)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                client_id, "Roi", "Client", case_manager_id, "medium",
                "2026-06-01", datetime.utcnow().isoformat(), "1990-01-01",
            ),
        )
        conn.commit()
    return client_id


def _use_temp_workspace_store(tmp_path):
    original = workspace_store.db_path
    workspace_store.db_path = tmp_path / "workspace_content.db"
    workspace_store._initialize()
    return original


def test_roi_table_init_is_additive(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = _use_temp_workspace_store(tmp_path)
    try:
        with workspace_store._connect() as conn:
            tables = {
                r["name"]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        # New table present, and pre-existing tables untouched (additive only).
        assert "roi_records" in tables
        assert "client_documents" in tables
        assert "client_notes" in tables
    finally:
        workspace_store.db_path = original
        workspace_store._initialize()


def test_create_list_and_multiple_records(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = _use_temp_workspace_store(tmp_path)
    client_id = _seed_core_client()
    api = TestClient(_test_app(tmp_path))
    try:
        r1 = api.post(
            f"/api/clients/{client_id}/roi-records",
            headers=_headers(),
            json={
                "authorized_party": "County Probation",
                "relationship_type": "Probation/parole",
                "purpose": "Court/legal",
                "info_to_release": ["Attendance", "Drug test results"],
                "release_method": "Secure email/portal",
            },
        )
        assert r1.status_code == 200, r1.text
        rec1 = r1.json()["roi_record"]
        assert rec1["authorized_party"] == "County Probation"
        assert rec1["info_to_release"] == ["Attendance", "Drug test results"]
        # No signed/linked document yet, so it cannot be "active".
        assert rec1["status"] == "draft"

        r2 = api.post(
            f"/api/clients/{client_id}/roi-records",
            headers=_headers(),
            json={"authorized_party": "Mother (Jane Doe)", "relationship_type": "Family"},
        )
        assert r2.status_code == 200

        listing = api.get(f"/api/clients/{client_id}/roi-records", headers=_headers())
        assert listing.status_code == 200
        body = listing.json()
        assert body["success"] is True
        assert len(body["roi_records"]) == 2
        parties = {rec["authorized_party"] for rec in body["roi_records"]}
        assert parties == {"County Probation", "Mother (Jane Doe)"}
        assert "does not guarantee HIPAA" in body["compliance_notice"]
    finally:
        workspace_store.db_path = original
        workspace_store._initialize()


def test_active_status_not_claimed_without_signed_document(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = _use_temp_workspace_store(tmp_path)
    client_id = _seed_core_client()
    api = TestClient(_test_app(tmp_path))
    try:
        r = api.post(
            f"/api/clients/{client_id}/roi-records",
            headers=_headers(),
            json={
                "authorized_party": "Employer",
                "info_to_release": ["Attendance"],
                "status": "active",  # requested, but no linked signed doc
            },
        )
        assert r.status_code == 200
        # Defensive derivation downgrades to needs_signature (data is sufficient
        # but there is no signed/linked document on file).
        assert r.json()["roi_record"]["status"] == "needs_signature"
    finally:
        workspace_store.db_path = original
        workspace_store._initialize()


def test_patch_edits_record(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = _use_temp_workspace_store(tmp_path)
    client_id = _seed_core_client()
    api = TestClient(_test_app(tmp_path))
    try:
        created = api.post(
            f"/api/clients/{client_id}/roi-records",
            headers=_headers(),
            json={"authorized_party": "Provider A"},
        ).json()["roi_record"]
        roi_id = created["roi_id"]

        patched = api.patch(
            f"/api/clients/{client_id}/roi-records/{roi_id}",
            headers=_headers(),
            json={
                "authorized_party": "Provider B",
                "purpose": "Continuity of care",
                "info_to_release": ["Treatment plan"],
            },
        )
        assert patched.status_code == 200
        rec = patched.json()["roi_record"]
        assert rec["authorized_party"] == "Provider B"
        assert rec["purpose"] == "Continuity of care"
        assert rec["info_to_release"] == ["Treatment plan"]
    finally:
        workspace_store.db_path = original
        workspace_store._initialize()


def test_revoked_state_preserved_in_history(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = _use_temp_workspace_store(tmp_path)
    client_id = _seed_core_client()
    api = TestClient(_test_app(tmp_path))
    try:
        created = api.post(
            f"/api/clients/{client_id}/roi-records",
            headers=_headers(),
            json={"authorized_party": "Sober Living House"},
        ).json()["roi_record"]
        roi_id = created["roi_id"]

        revoked = api.patch(
            f"/api/clients/{client_id}/roi-records/{roi_id}",
            headers=_headers(),
            json={"revoked": True},
        )
        assert revoked.status_code == 200
        rec = revoked.json()["roi_record"]
        assert rec["revoked"] is True
        assert rec["revoked_at"]
        assert rec["status"] == "revoked"

        # Still present in history (not deleted).
        listing = api.get(f"/api/clients/{client_id}/roi-records", headers=_headers())
        ids = [r["roi_id"] for r in listing.json()["roi_records"]]
        assert roi_id in ids
    finally:
        workspace_store.db_path = original
        workspace_store._initialize()


def test_expired_status_is_derived(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = _use_temp_workspace_store(tmp_path)
    client_id = _seed_core_client()
    api = TestClient(_test_app(tmp_path))
    try:
        past = (datetime.now() - timedelta(days=2)).date().isoformat()
        created = api.post(
            f"/api/clients/{client_id}/roi-records",
            headers=_headers(),
            json={
                "authorized_party": "Court",
                "expiration_date": past,
                "status": "active",
            },
        )
        assert created.status_code == 200
        assert created.json()["roi_record"]["status"] == "expired"
    finally:
        workspace_store.db_path = original
        workspace_store._initialize()


def test_generate_document_creates_printable_and_links(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = _use_temp_workspace_store(tmp_path)
    # Keep generated files out of the repo's uploads/ dir.
    monkeypatch.setattr(clients_api, "CLIENT_UPLOADS_ROOT", tmp_path / "uploads")
    monkeypatch.setattr(clients_api, "CLIENT_UPLOADS_DIR", tmp_path / "uploads" / "clients")
    client_id = _seed_core_client()
    api = TestClient(_test_app(tmp_path))
    try:
        created = api.post(
            f"/api/clients/{client_id}/roi-records",
            headers=_headers(),
            json={
                "authorized_party": "County Probation",
                "purpose": "Court/legal",
                "info_to_release": ["Attendance"],
            },
        ).json()["roi_record"]
        roi_id = created["roi_id"]

        gen = api.post(
            f"/api/clients/{client_id}/roi-records/{roi_id}/generate-document",
            headers=_headers(),
        )
        assert gen.status_code == 200, gen.text
        payload = gen.json()
        doc = payload["document"]
        assert doc["doc_type"] == "roi_generated"
        assert doc["file_mime"] == "text/html"
        # Record is linked to the generated document.
        assert payload["roi_record"]["linked_document_id"] == doc["doc_id"]
        assert payload["view_url"].endswith(f"/documents/{doc['doc_id']}/view")

        # The printable file exists on disk and contains the structured content
        # plus the compliance + draft labeling.
        written = (tmp_path / "uploads" / "clients" / client_id)
        files = list(written.glob("roi_form_*.html"))
        assert len(files) == 1
        html = files[0].read_text(encoding="utf-8")
        assert "County Probation" in html
        assert "DRAFT" in html
        assert "does not guarantee HIPAA" in html
    finally:
        workspace_store.db_path = original
        workspace_store._initialize()


def test_uploaded_text_document_views_from_runtime_uploads_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = _use_temp_workspace_store(tmp_path)
    monkeypatch.setattr(clients_api, "CLIENT_UPLOADS_ROOT", tmp_path / "runtime-volume" / "uploads")
    monkeypatch.setattr(clients_api, "CLIENT_UPLOADS_DIR", tmp_path / "runtime-volume" / "uploads" / "clients")
    clients_api.CLIENT_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    client_id = _seed_core_client(client_id="client-doc-1")
    api = TestClient(_test_app(tmp_path))
    try:
        upload = api.post(
            f"/api/clients/{client_id}/documents",
            headers=_headers(),
            data={"title": "Letter of Presence", "doc_type": "presence_letter"},
            files={"file": ("letter-of-presence.txt", BytesIO(b"Client attended treatment."), "text/plain")},
        )
        assert upload.status_code == 200, upload.text
        doc = upload.json()["document"]
        assert doc["file_path"].startswith("uploads/clients/")

        view = api.get(
            f"/api/clients/{client_id}/documents/{doc['doc_id']}/view",
            headers=_headers(),
        )
        assert view.status_code == 200, view.text
        assert "text/plain" in view.headers["content-type"]
        assert view.text == "Client attended treatment."
    finally:
        workspace_store.db_path = original
        workspace_store._initialize()


def test_view_client_document_returns_404_when_record_points_to_missing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = _use_temp_workspace_store(tmp_path)
    monkeypatch.setattr(clients_api, "CLIENT_UPLOADS_ROOT", tmp_path / "runtime-volume" / "uploads")
    monkeypatch.setattr(clients_api, "CLIENT_UPLOADS_DIR", tmp_path / "runtime-volume" / "uploads" / "clients")
    clients_api.CLIENT_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    client_id = _seed_core_client(client_id="client-doc-2")
    api = TestClient(_test_app(tmp_path))
    try:
        doc = workspace_store.create_client_document(
            client_id,
            {
                "title": "Missing Generated Letter",
                "doc_type": "presence_letter",
                "file_name": "missing.txt",
                "file_mime": "text/plain",
                "file_path": "uploads/clients/client-doc-2/missing.txt",
            },
        )

        view = api.get(
            f"/api/clients/{client_id}/documents/{doc['doc_id']}/view",
            headers=_headers(),
        )
        assert view.status_code == 404
        assert view.json() == {"detail": "File not found on disk"}
    finally:
        workspace_store.db_path = original
        workspace_store._initialize()


def test_workspace_store_resolves_db_path_from_db_dir(tmp_path, monkeypatch):
    """Regression: the store must live under the central DB_DIR (the Railway
    persistent volume in production / CMSX_DB_DIR in the harness), NOT a
    repo-relative path that is ephemeral and git-tracked."""
    monkeypatch.setattr(ws_mod, "DB_DIR", tmp_path)
    store = ws_mod.WorkspaceStore()
    assert store.db_path == tmp_path / "workspace_content.db"
    # The resolved file is under DB_DIR, not the repository's databases/ dir.
    assert store.db_path.parent == tmp_path


def test_roi_record_persists_across_a_new_store_instance(tmp_path, monkeypatch):
    """Core persistence proof: a record created by one store instance is readable
    by a brand-new instance pointed at the same DB_DIR — i.e. it survives the
    process/container restart that happens on every deploy (the live failure)."""
    monkeypatch.setattr(ws_mod, "DB_DIR", tmp_path)
    store_a = ws_mod.WorkspaceStore()
    created = store_a.create_client_roi_record(
        "client-persist-1",
        {"authorized_party": "County Probation", "relationship_type": "Probation/parole"},
        created_by="cm_test",
    )
    roi_id = created["roi_id"]

    # Simulate a fresh process (new deploy / new worker): a new store object,
    # same on-disk DB_DIR. The previously written record must still be there.
    store_b = ws_mod.WorkspaceStore()
    records = store_b.list_client_roi_records("client-persist-1")
    assert any(r["roi_id"] == roi_id for r in records)
    # And it is a real file on disk under DB_DIR, not an in-memory artifact.
    assert (tmp_path / "workspace_content.db").exists()


def test_draft_record_is_included_in_list_and_total(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = _use_temp_workspace_store(tmp_path)
    client_id = _seed_core_client()
    api = TestClient(_test_app(tmp_path))
    try:
        created = api.post(
            f"/api/clients/{client_id}/roi-records",
            headers=_headers(),
            json={"authorized_party": "New Provider"},
        ).json()["roi_record"]
        # A bare record with no signed/linked document derives to 'draft'.
        assert created["status"] == "draft"

        listing = api.get(f"/api/clients/{client_id}/roi-records", headers=_headers())
        body = listing.json()
        # Draft records are NOT filtered out of the list or the total.
        ids = [r["roi_id"] for r in body["roi_records"]]
        assert created["roi_id"] in ids
        assert len(body["roi_records"]) == 1
    finally:
        workspace_store.db_path = original
        workspace_store._initialize()


def test_missing_authorized_party_returns_clear_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = _use_temp_workspace_store(tmp_path)
    client_id = _seed_core_client()
    api = TestClient(_test_app(tmp_path))
    try:
        r = api.post(
            f"/api/clients/{client_id}/roi-records",
            headers=_headers(),
            json={"authorized_party": "   "},  # blank after trim
        )
        assert r.status_code == 400
        assert "authorized_party" in r.json()["detail"]
        # Nothing was persisted.
        listing = api.get(f"/api/clients/{client_id}/roi-records", headers=_headers())
        assert len(listing.json()["roi_records"]) == 0
    finally:
        workspace_store.db_path = original
        workspace_store._initialize()


def test_access_guard_matches_client_subresources(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = _use_temp_workspace_store(tmp_path)
    client_id = _seed_core_client(case_manager_id="cm_owner")
    api = TestClient(_test_app(tmp_path))
    try:
        denied = api.get(
            f"/api/clients/{client_id}/roi-records",
            headers=_headers(case_manager_id="cm_other", email="other@example.test"),
        )
        assert denied.status_code == 403
    finally:
        workspace_store.db_path = original
        workspace_store._initialize()
