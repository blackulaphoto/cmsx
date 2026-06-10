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


CCAPP_FIXTURE_HTML = """
<html>
  <body>
    <div class="gh-card">
      <div class="facilityCard_facilityHeader__1JUiL">
        <a class="facilities_facilityItem__XOuQN gh-facilities-item css-0" href="#/facility/25364" id="25364">River City Recovery</a>
      </div>
      <div class="facilityCard_address__1LctV">
        <div><a class="facilities_facilityItem__XOuQN gh-facilities-item css-0" href="#/facility/25364" id="25364">Sacramento CA<span>, 95816</span></a></div>
      </div>
      <div class="facilityCard_badges__pfiPU">
        <div><a class="facilities_facilityItem__XOuQN gh-facilities-item css-0" href="#/facility/25364" id="25364"><span>Accredited</span></a></div>
        <div class="gh-distance"><a class="facilities_facilityItem__XOuQN gh-facilities-item css-0" href="#/facility/25364" id="25364">2.80 <span>mi.</span></a></div>
      </div>
    </div>
    <div class="gh-card">
      <div class="facilityCard_facilityHeader__1JUiL">
        <a class="facilities_facilityItem__XOuQN gh-facilities-item css-0" href="#/facility/99999" id="99999">Los Angeles Test Residence</a>
      </div>
      <div class="facilityCard_address__1LctV">
        <div><a class="facilities_facilityItem__XOuQN gh-facilities-item css-0" href="#/facility/99999" id="99999">Los Angeles CA<span>, 90012</span></a></div>
      </div>
      <div class="facilityCard_badges__pfiPU">
        <div><a class="facilities_facilityItem__XOuQN gh-facilities-item css-0" href="#/facility/99999" id="99999"><span>Accredited</span></a></div>
        <div class="gh-distance"><a class="facilities_facilityItem__XOuQN gh-facilities-item css-0" href="#/facility/99999" id="99999">8.40 <span>mi.</span></a></div>
      </div>
    </div>
    <div class="gh-card">
      <div class="facilityCard_facilityHeader__1JUiL">
        <a class="facilities_facilityItem__XOuQN gh-facilities-item css-0" href="#/facility/25364" id="25364">River City Recovery</a>
      </div>
      <div class="facilityCard_address__1LctV">
        <div><a class="facilities_facilityItem__XOuQN gh-facilities-item css-0" href="#/facility/25364" id="25364">Sacramento CA<span>, 95816</span></a></div>
      </div>
    </div>
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
        service._fetch_remote_text = lambda url: CCAPP_FIXTURE_HTML
        client = _build_client(db, service)
        try:
            source_response = client.post(
                "/api/sober-living-directory/sources",
                json={
                    "source_name": "CCAPP Certified Directory",
                    "source_type": "certification_directory",
                    "base_url": "https://ccapprecoveryresidences.org/search/",
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
                    name="River City Recovery",
                    city="Sacramento",
                    state="CA",
                    status="approved",
                )
            )

            job_response = client.post(
                "/api/sober-living-directory/discovery/jobs",
                json={
                    "source_id": source_id,
                    "job_name": "CCAPP Sacramento connector run",
                    "job_type": "scheduled_source_check",
                    "target_city": "Sacramento",
                    "target_state": "CA",
                    "query": "recovery residence",
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
            assert raw_record["raw_name"] == "River City Recovery"
            assert raw_record["source_url"] == "https://ccapprecoveryresidences.org/search/#/facility/25364"
            assert raw_record["review_status"] == "possible_duplicate"

            raw_detail_response = client.get(f"/api/sober-living-directory/raw-records/{raw_record['raw_id']}")
            assert raw_detail_response.status_code == 200, raw_detail_response.text
            raw_detail = raw_detail_response.json()
            assert raw_detail["normalized_preview_fields"]["certification_body"] == "CCAPP"
            assert raw_detail["normalized_preview_fields"]["certification_status"] == "Accredited"
            assert raw_detail["normalized_preview_fields"]["city"] == "Sacramento"
            assert "https://ccapprecoveryresidences.org/search/" in raw_detail["normalized_preview_fields"]["source_urls_json"]

            duplicate_candidates = db.get_duplicate_candidates()
            assert len(duplicate_candidates) == 1
            assert duplicate_candidates[0]["existing_listing_id"] == existing_listing["listing_id"]

            review_response = client.get("/api/sober-living-directory/review")
            assert review_response.status_code == 200, review_response.text
            review_payload = review_response.json()
            assert len(review_payload["raw_records"]) == 1
            assert review_payload["raw_records"][0]["duplicate_candidate_count"] == 1

            print("CCAPP connector smoke test passed")
        finally:
            client.close()
            if db.connection is not None:
                db.connection.close()
                db.connection = None


if __name__ == "__main__":
    main()
