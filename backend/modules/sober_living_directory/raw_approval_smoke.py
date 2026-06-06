from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.sober_living_directory.database import SoberLivingDirectoryDatabase
from backend.modules.sober_living_directory.models import SoberLivingDirectoryListingCreate, SoberLivingDirectorySourceCreate
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
        try:
            source = db.create_source(
                SoberLivingDirectorySourceCreate(
                    source_name="Smoke Source",
                    source_type="manual",
                    trust_level="medium",
                    supports_api=False,
                    supports_scraping=False,
                    requires_manual_review=True,
                    is_active=True,
                )
            )

            raw_id = db.create_raw_listing(
                source_id=source["source_id"],
                source_url="https://raw.example.com",
                raw_name="Approval Candidate",
                raw_address="100 Review St",
                raw_phone="555-123-4567",
                raw_email=None,
                raw_website="https://raw.example.com",
                raw_text="approval candidate",
                extracted_json={
                    "name": "Approval Candidate",
                    "city": "Los Angeles",
                    "state": "CA",
                    "address": "100 Review St",
                    "phone": "555-123-4567",
                    "website": "https://raw.example.com",
                    "source_urls_json": ["https://raw.example.com"],
                },
                review_status="new",
            )

            approve_response = client.post(
                f"/api/sober-living-directory/raw-records/{raw_id}/approve",
                json={"review_notes": "Looks valid"},
            )
            assert approve_response.status_code == 200, approve_response.text
            approved_payload = approve_response.json()
            listing_id = approved_payload["listing"]["listing_id"]
            assert approved_payload["listing"]["status"] == "pending_review"
            assert approved_payload["raw_record"]["review_status"] == "approved"
            change_log_types = {entry["change_type"] for entry in db.get_change_log(listing_id)}
            assert "raw_record_approved" in change_log_types

            reject_raw_id = db.create_raw_listing(
                source_id=source["source_id"],
                source_url=None,
                raw_name="Reject Candidate",
                raw_address=None,
                raw_phone=None,
                raw_email=None,
                raw_website=None,
                raw_text="reject candidate",
                extracted_json={"name": "Reject Candidate", "city": "Pasadena", "state": "CA"},
                review_status="new",
            )
            reject_response = client.post(
                f"/api/sober-living-directory/raw-records/{reject_raw_id}/reject",
                json={"review_notes": "Not enough signal"},
            )
            assert reject_response.status_code == 200, reject_response.text
            assert db.get_raw_record(reject_raw_id)["raw_record"]["review_status"] == "rejected"

            missing_raw_id = db.create_raw_listing(
                source_id=source["source_id"],
                source_url=None,
                raw_name="Missing State Candidate",
                raw_address=None,
                raw_phone=None,
                raw_email=None,
                raw_website=None,
                raw_text="missing state candidate",
                extracted_json={"name": "Missing State Candidate", "city": "Burbank", "state": ""},
                review_status="new",
            )
            missing_response = client.post(
                f"/api/sober-living-directory/raw-records/{missing_raw_id}/approve",
                json={},
            )
            assert missing_response.status_code == 400, missing_response.text
            assert "missing required fields" in missing_response.json()["detail"].lower()

            existing_listing = db.create_listing(
                SoberLivingDirectoryListingCreate(
                    name="Duplicate House",
                    city="Torrance",
                    state="CA",
                    phone="555-999-0000",
                    website="https://duplicate.example.com",
                    status="approved",
                )
            )
            duplicate_raw_id = db.create_raw_listing(
                source_id=source["source_id"],
                source_url="https://duplicate.example.com",
                raw_name="Duplicate House",
                raw_address=None,
                raw_phone="555-999-0000",
                raw_email=None,
                raw_website="https://duplicate.example.com",
                raw_text="duplicate candidate",
                extracted_json={
                    "name": "Duplicate House",
                    "city": "Torrance",
                    "state": "CA",
                    "phone": "555-999-0000",
                    "website": "https://duplicate.example.com",
                },
                matched_listing_id=existing_listing["listing_id"],
                review_status="possible_duplicate",
            )
            db.create_duplicate_candidate(
                raw_id=duplicate_raw_id,
                existing_listing_id=existing_listing["listing_id"],
                proposed_name="Duplicate House",
                existing_name="Duplicate House",
                match_reasons=["phone_match"],
                confidence_score=90,
            )
            duplicate_block_response = client.post(
                f"/api/sober-living-directory/raw-records/{duplicate_raw_id}/approve",
                json={},
            )
            assert duplicate_block_response.status_code == 400, duplicate_block_response.text
            assert "duplicate" in duplicate_block_response.json()["detail"].lower()

            print("Raw approval smoke test passed")
        finally:
            client.close()
            if db.connection is not None:
                db.connection.close()
                db.connection = None


if __name__ == "__main__":
    main()
