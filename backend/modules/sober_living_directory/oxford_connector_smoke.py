from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.sober_living_directory.database import SoberLivingDirectoryDatabase
from backend.modules.sober_living_directory.discovery import SoberLivingDiscoveryService
from backend.modules.sober_living_directory.models import SoberLivingDirectoryListingCreate
from backend.modules.sober_living_directory.routes import router
import backend.modules.sober_living_directory.routes as directory_routes


OXFORD_FIXTURE_HTML = """
<html>
  <body>
    <table>
      <tr>
        <th>House Name</th>
        <th>Gender</th>
        <th>City</th>
        <th>House #</th>
        <th>County</th>
        <th>Contact</th>
        <th>Contact #</th>
        <th>Interviews</th>
        <th>Capacity</th>
        <th>Vacancies</th>
        <th>Distance</th>
        <th>Last Updated</th>
      </tr>
      <tr>
        <td>37th Street</td>
        <td>M</td>
        <td>New Bern</td>
        <td>(252) 631-2005</td>
        <td>Craven</td>
        <td>Derrick</td>
        <td>(252) 229-9071</td>
        <td>Daily 6:00am</td>
        <td>8</td>
        <td>2</td>
        <td>Search by Zip</td>
        <td>06/04/2026 6:49AM</td>
      </tr>
      <tr>
        <td>Abbeywood</td>
        <td>W</td>
        <td>Clarksville</td>
        <td>(812) 590-1541</td>
        <td>Clark</td>
        <td>Brooke</td>
        <td>(502) 676-0450</td>
        <td>Sat 6:00pm</td>
        <td>7</td>
        <td>0</td>
        <td>Search by Zip</td>
        <td>05/25/2026 3:18PM</td>
      </tr>
    </table>
  </body>
</html>
"""


def _build_client(db: SoberLivingDirectoryDatabase, service: SoberLivingDiscoveryService) -> TestClient:
    app = FastAPI()
    directory_routes.directory_db = db
    directory_routes.get_discovery_service = lambda: service
    app.include_router(router, prefix="/api/sober-living-directory")
    return TestClient(app)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db = SoberLivingDirectoryDatabase(db_path=str(Path(temp_dir) / "sober_living_directory.db"))
        service = SoberLivingDiscoveryService(db)
        service._fetch_remote_text = lambda url: OXFORD_FIXTURE_HTML
        client = _build_client(db, service)
        try:
            source_response = client.post(
                "/api/sober-living-directory/sources",
                json={
                    "source_name": "Oxford House",
                    "source_type": "public_directory",
                    "base_url": "https://www.oxfordvacancies.com/",
                    "trust_level": "high",
                    "supports_api": False,
                    "supports_scraping": True,
                    "requires_manual_review": True,
                    "is_active": True,
                },
            )
            assert source_response.status_code == 200, source_response.text
            source_id = source_response.json()["source"]["source_id"]

            existing_listing = db.create_listing(
                SoberLivingDirectoryListingCreate(
                    name="Oxford House - 37th Street",
                    city="New Bern",
                    state="NC",
                    phone="(252) 229-9071",
                    status="approved",
                )
            )

            job_response = client.post(
                "/api/sober-living-directory/discovery/jobs",
                json={
                    "source_id": source_id,
                    "job_name": "Oxford New Bern connector run",
                    "job_type": "scheduled_source_check",
                    "target_city": "New Bern",
                    "target_state": "NC",
                    "query": "vacancy locator",
                    "schedule_label": "manual",
                    "is_active": True,
                },
            )
            assert job_response.status_code == 200, job_response.text
            job_id = job_response.json()["job"]["job_id"]

            run_response = client.post(f"/api/sober-living-directory/discovery/jobs/{job_id}/run")
            assert run_response.status_code == 200, run_response.text
            run_payload = run_response.json()["run"]
            assert run_payload["status"] == "completed"
            assert run_payload["records_found"] == 1
            assert run_payload["raw_records_created"] == 1
            assert run_payload["duplicates_detected"] == 1

            run_detail_response = client.get(f"/api/sober-living-directory/discovery/runs/{run_payload['run_id']}")
            assert run_detail_response.status_code == 200, run_detail_response.text
            run_detail = run_detail_response.json()["run"]
            assert len(run_detail["raw_records"]) == 1
            raw_record = run_detail["raw_records"][0]
            assert raw_record["raw_name"] == "Oxford House - 37th Street"
            assert raw_record["source_url"] == "https://www.oxfordvacancies.com/"
            assert raw_record["review_status"] == "possible_duplicate"

            raw_detail_response = client.get(f"/api/sober-living-directory/raw-records/{raw_record['raw_id']}")
            assert raw_detail_response.status_code == 200, raw_detail_response.text
            raw_detail = raw_detail_response.json()
            normalized = raw_detail["normalized_preview_fields"]
            assert normalized["city"] == "New Bern"
            assert normalized["state"] == "NC"
            assert normalized["population_served"] == "Men"
            assert normalized["certification_body"] == "Oxford House"
            assert normalized["bed_availability_status"] == "available"

            duplicate_candidates = db.get_duplicate_candidates()
            assert len(duplicate_candidates) == 1
            assert duplicate_candidates[0]["existing_listing_id"] == existing_listing["listing_id"]
            assert len(db.list_listings()) == 1

            review_response = client.get("/api/sober-living-directory/review")
            assert review_response.status_code == 200, review_response.text
            review_payload = review_response.json()
            assert len(review_payload["raw_records"]) == 1
            assert review_payload["raw_records"][0]["duplicate_candidate_count"] == 1

            failing_service = SoberLivingDiscoveryService(db)
            failing_service._fetch_remote_text = lambda url: (_ for _ in ()).throw(ValueError("Oxford connector blocked for smoke test"))
            directory_routes.get_discovery_service = lambda: failing_service

            failing_job_response = client.post(
                "/api/sober-living-directory/discovery/jobs",
                json={
                    "source_id": source_id,
                    "job_name": "Oxford blocked connector run",
                    "job_type": "scheduled_source_check",
                    "target_city": "Clarksville",
                    "target_state": "TN",
                    "query": "vacancy locator",
                    "schedule_label": "manual",
                    "is_active": True,
                },
            )
            assert failing_job_response.status_code == 200, failing_job_response.text
            failing_job_id = failing_job_response.json()["job"]["job_id"]

            failing_run_response = client.post(f"/api/sober-living-directory/discovery/jobs/{failing_job_id}/run")
            assert failing_run_response.status_code == 400, failing_run_response.text
            assert "blocked for smoke test" in failing_run_response.json()["detail"]

            runs_response = client.get("/api/sober-living-directory/discovery/runs")
            assert runs_response.status_code == 200, runs_response.text
            runs = runs_response.json()["runs"]
            failed_runs = [run for run in runs if run["job_id"] == failing_job_id]
            assert len(failed_runs) == 1
            assert failed_runs[0]["status"] == "failed"
            assert failed_runs[0]["raw_records_created"] == 0
            assert failed_runs[0]["errors_count"] == 1
            assert "blocked for smoke test" in (failed_runs[0]["error_message"] or "")

            print("Oxford connector smoke test passed")
        finally:
            client.close()
            if db.connection is not None:
                db.connection.close()
                db.connection = None


if __name__ == "__main__":
    main()
