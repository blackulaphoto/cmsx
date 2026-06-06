from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.sober_living_directory.database import SoberLivingDirectoryDatabase
from backend.modules.sober_living_directory.models import SoberLivingDirectoryListingCreate
from backend.modules.sober_living_directory.routes import router
import backend.modules.sober_living_directory.routes as directory_routes


def _build_app(db: SoberLivingDirectoryDatabase) -> TestClient:
    app = FastAPI()
    directory_routes.directory_db = db
    app.include_router(router, prefix="/api/sober-living-directory")
    return TestClient(app)


def _create_candidate(
    db: SoberLivingDirectoryDatabase,
    *,
    listing_id: str,
    listing_name: str,
    normalized_import: dict,
    confidence_score: int = 80,
    reasons: list[str] | None = None,
) -> str:
    raw_id = db.create_raw_listing(
        source_id=None,
        source_url=normalized_import.get("website"),
        raw_name=normalized_import.get("name"),
        raw_address=normalized_import.get("address"),
        raw_phone=normalized_import.get("phone"),
        raw_email=normalized_import.get("email"),
        raw_website=normalized_import.get("website"),
        raw_text=str(normalized_import),
        extracted_json=normalized_import,
        matched_listing_id=listing_id,
        review_status="possible_duplicate",
    )
    candidate = db.create_duplicate_candidate(
        raw_id=raw_id,
        existing_listing_id=listing_id,
        proposed_name=normalized_import.get("name"),
        existing_name=listing_name,
        match_reasons=reasons or ["name_match", "city_match"],
        confidence_score=confidence_score,
    )
    return candidate["candidate_id"]


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = str(Path(temp_dir) / "sober_living_directory.db")
        db = SoberLivingDirectoryDatabase(db_path=db_path)
        client = _build_app(db)
        try:
            recent_verified = datetime.utcnow().replace(microsecond=0).isoformat()
            existing = db.create_listing(
                SoberLivingDirectoryListingCreate(
                    name="Oak Recovery House",
                    city="Los Angeles",
                    state="CA",
                    phone="555-111-2222",
                    website="https://oak.example.com",
                    address=None,
                    notes="Existing note",
                    source_urls_json=["https://oak.example.com"],
                    verification_method="phone",
                    last_verified_date=recent_verified,
                    status="approved",
                )
            )

            safe_candidate_id = _create_candidate(
                db,
                listing_id=existing["listing_id"],
                listing_name=existing["name"],
                normalized_import={
                    "name": "Oak Recovery House",
                    "city": "Los Angeles",
                    "state": "CA",
                    "phone": "555-999-0000",
                    "website": "https://oak.example.com",
                    "address": "123 Main St",
                    "notes": "Imported safe note",
                    "source_urls_json": ["https://directory.example.com/oak"],
                    "status": "pending_review",
                },
            )

            detail_response = client.get(f"/api/sober-living-directory/duplicates/{safe_candidate_id}")
            assert detail_response.status_code == 200, detail_response.text
            detail_payload = detail_response.json()
            diff_by_field = {entry["field"]: entry for entry in detail_payload["field_diff"]}
            assert diff_by_field["address"]["status"] == "existing_empty"
            assert diff_by_field["phone"]["status"] == "conflict"

            safe_merge_response = client.post(
                f"/api/sober-living-directory/duplicates/{safe_candidate_id}/merge",
                json={"resolution_notes": "safe merge"},
            )
            assert safe_merge_response.status_code == 200, safe_merge_response.text
            updated_existing = db.get_listing(existing["listing_id"])
            assert updated_existing["address"] == "123 Main St"
            assert updated_existing["phone"] == "555-111-2222"

            change_types = {entry["change_type"] for entry in db.get_change_log(existing["listing_id"])}
            assert "address_changed" in change_types

            selected_candidate_id = _create_candidate(
                db,
                listing_id=existing["listing_id"],
                listing_name=existing["name"],
                normalized_import={
                    "name": "Oak Recovery House",
                    "city": "Los Angeles",
                    "state": "CA",
                    "phone": "555-111-2222",
                    "website": "https://oak.example.com",
                    "notes": "Imported selected note",
                    "source_urls_json": ["https://directory.example.com/oak-2"],
                    "status": "pending_review",
                },
            )
            selected_merge_response = client.post(
                f"/api/sober-living-directory/duplicates/{selected_candidate_id}/merge",
                json={
                    "resolution_notes": "selected merge",
                    "selected_imported_fields": ["notes"],
                },
            )
            assert selected_merge_response.status_code == 200, selected_merge_response.text
            updated_existing = db.get_listing(existing["listing_id"])
            assert updated_existing["notes"] == "Imported selected note"
            change_types = {entry["change_type"] for entry in db.get_change_log(existing["listing_id"])}
            assert "notes_changed" in change_types

            for protected_status in ("do_not_refer", "use_caution", "archived"):
                protected = db.create_listing(
                    SoberLivingDirectoryListingCreate(
                        name=f"{protected_status} listing",
                        city="Long Beach",
                        state="CA",
                        status=protected_status,
                    )
                )
                protected_candidate_id = _create_candidate(
                    db,
                    listing_id=protected["listing_id"],
                    listing_name=protected["name"],
                    normalized_import={
                        "name": protected["name"],
                        "city": "Long Beach",
                        "state": "CA",
                        "status": "approved",
                    },
                )
                protected_merge_response = client.post(
                    f"/api/sober-living-directory/duplicates/{protected_candidate_id}/merge",
                    json={
                        "resolution_notes": "unsafe status overwrite attempt",
                        "selected_imported_fields": ["status"],
                    },
                )
                assert protected_merge_response.status_code == 400, protected_merge_response.text
                assert db.get_listing(protected["listing_id"])["status"] == protected_status

            print("Duplicate merge smoke test passed")
        finally:
            client.close()
            if db.connection is not None:
                db.connection.close()
                db.connection = None


if __name__ == "__main__":
    main()
