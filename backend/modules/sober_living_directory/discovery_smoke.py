from __future__ import annotations

import tempfile
from pathlib import Path
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.sober_living_directory.database import SoberLivingDirectoryDatabase
from backend.modules.sober_living_directory.models import SoberLivingDirectoryListingCreate
from backend.modules.sober_living_directory.routes import router
import backend.modules.sober_living_directory.routes as directory_routes


def _build_client(db: SoberLivingDirectoryDatabase) -> TestClient:
    app = FastAPI()
    directory_routes.directory_db = db
    app.include_router(router, prefix="/api/sober-living-directory")
    return TestClient(app)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db = SoberLivingDirectoryDatabase(db_path=str(Path(temp_dir) / "sober_living_directory.db"))
        client = _build_client(db)
        workspace_root = Path(__file__).resolve().parents[3]
        spreadsheet_path = workspace_root / f"tmp_discovery_smoke_{uuid.uuid4().hex[:8]}.csv"
        try:
            source_response = client.post(
                "/api/sober-living-directory/sources",
                json={
                    "source_name": "Manual Test Source",
                    "source_type": "manual",
                    "base_url": "https://example.test/manual",
                    "trust_level": "low",
                    "supports_api": False,
                    "supports_scraping": False,
                    "requires_manual_review": True,
                    "is_active": True,
                },
            )
            assert source_response.status_code == 200, source_response.text
            source_id = source_response.json()["source"]["source_id"]

            existing_listing = db.create_listing(
                SoberLivingDirectoryListingCreate(
                    name="Los Angeles Sober Living Test Home 1",
                    city="Los Angeles",
                    state="CA",
                    phone="555-301-001",
                    website="https://sober-living-1.example.com",
                    status="approved",
                )
            )

            job_response = client.post(
                "/api/sober-living-directory/discovery/jobs",
                json={
                    "source_id": source_id,
                    "job_name": "Los Angeles manual test",
                    "job_type": "manual_test",
                    "target_city": "Los Angeles",
                    "target_state": "CA",
                    "query": "sober living",
                    "schedule_label": "ad hoc",
                    "is_active": True,
                },
            )
            assert job_response.status_code == 200, job_response.text
            job_id = job_response.json()["job"]["job_id"]

            run_response = client.post(f"/api/sober-living-directory/discovery/jobs/{job_id}/run-test")
            assert run_response.status_code == 200, run_response.text
            run_payload = run_response.json()["run"]
            run_id = run_payload["run_id"]
            assert run_payload["status"] == "completed"
            assert run_payload["records_found"] >= 1
            assert run_payload["raw_records_created"] >= 1

            runs_response = client.get("/api/sober-living-directory/discovery/runs")
            assert runs_response.status_code == 200, runs_response.text
            assert any(run["run_id"] == run_id for run in runs_response.json()["runs"])

            run_detail_response = client.get(f"/api/sober-living-directory/discovery/runs/{run_id}")
            assert run_detail_response.status_code == 200, run_detail_response.text
            run_detail = run_detail_response.json()["run"]
            assert len(run_detail["raw_records"]) >= 1

            duplicate_candidates = db.get_duplicate_candidates()
            assert len(duplicate_candidates) >= 1
            assert any(candidate["existing_listing_id"] == existing_listing["listing_id"] for candidate in duplicate_candidates)

            review_response = client.get("/api/sober-living-directory/review")
            assert review_response.status_code == 200, review_response.text
            review_payload = review_response.json()
            assert "raw_records" in review_payload
            assert len(review_payload["raw_records"]) >= 1
            assert any(record["review_status"] in {"new", "possible_duplicate"} for record in review_payload["raw_records"])

            spreadsheet_path.write_text(
                "Name,Location,Phone,Website,Serves,Price,Contact\n"
                "Oak Recovery House,Los Angeles,555-111-2222,https://oak.example.com,Men,$1200,Manual Test Contact\n"
                "Beacon House,Long Beach,555-444-5555,https://beacon.example.com,Women,$900,Beacon Contact\n",
                encoding="utf-8",
            )
            spreadsheet_source_response = client.post(
                "/api/sober-living-directory/sources",
                json={
                    "source_name": "Controlled Spreadsheet Source",
                    "source_type": "spreadsheet_import",
                    "base_url": spreadsheet_path.name,
                    "trust_level": "medium",
                    "supports_api": False,
                    "supports_scraping": False,
                    "requires_manual_review": True,
                    "is_active": True,
                },
            )
            assert spreadsheet_source_response.status_code == 200, spreadsheet_source_response.text
            spreadsheet_source_id = spreadsheet_source_response.json()["source"]["source_id"]

            connector_listing = db.create_listing(
                SoberLivingDirectoryListingCreate(
                    name="Oak Recovery House",
                    city="Los Angeles",
                    state="CA",
                    phone="555-111-2222",
                    website="https://oak.example.com",
                    status="approved",
                )
            )

            spreadsheet_job_response = client.post(
                "/api/sober-living-directory/discovery/jobs",
                json={
                    "source_id": spreadsheet_source_id,
                    "job_name": "Controlled spreadsheet connector",
                    "job_type": "import_recheck",
                    "target_city": "Los Angeles",
                    "target_state": "CA",
                    "query": "sober living",
                    "schedule_label": "manual",
                    "is_active": True,
                },
            )
            assert spreadsheet_job_response.status_code == 200, spreadsheet_job_response.text
            spreadsheet_job_id = spreadsheet_job_response.json()["job"]["job_id"]

            connector_run_response = client.post(f"/api/sober-living-directory/discovery/jobs/{spreadsheet_job_id}/run")
            assert connector_run_response.status_code == 200, connector_run_response.text
            connector_run = connector_run_response.json()["run"]
            assert connector_run["status"] == "completed"
            assert connector_run["records_found"] == 2
            assert connector_run["raw_records_created"] == 2

            spreadsheet_duplicates = db.get_duplicate_candidates()
            assert any(candidate["existing_listing_id"] == connector_listing["listing_id"] for candidate in spreadsheet_duplicates)

            print("Discovery smoke test passed")
        finally:
            if spreadsheet_path.exists():
                spreadsheet_path.unlink()
            client.close()
            if db.connection is not None:
                db.connection.close()
                db.connection = None


if __name__ == "__main__":
    main()
