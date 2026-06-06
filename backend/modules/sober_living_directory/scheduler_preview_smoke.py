from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.sober_living_directory.database import SoberLivingDirectoryDatabase
from backend.modules.sober_living_directory.models import (
    DiscoveryJobScheduleUpdate,
    DiscoveryJobUpdate,
    SoberLivingDirectorySourceUpdate,
)
from backend.modules.sober_living_directory.routes import router
import backend.modules.sober_living_directory.routes as directory_routes
from backend.modules.sober_living_directory.scheduling import calculate_next_run


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
            source_response = client.post(
                "/api/sober-living-directory/sources",
                json={
                    "source_name": "Schedulable Source",
                    "source_type": "public_directory",
                    "base_url": "https://example.com/directory",
                    "trust_level": "high",
                    "supports_api": False,
                    "supports_scraping": True,
                    "requires_manual_review": True,
                    "is_active": True,
                },
            )
            assert source_response.status_code == 200, source_response.text
            source_id = source_response.json()["source"]["source_id"]

            job_response = client.post(
                "/api/sober-living-directory/discovery/jobs",
                json={
                    "source_id": source_id,
                    "job_name": "Manual Only Job",
                    "job_type": "scheduled_source_check",
                    "target_city": "Los Angeles",
                    "target_state": "CA",
                    "query": "preview",
                    "is_active": True,
                },
            )
            assert job_response.status_code == 200, job_response.text
            job = job_response.json()["job"]
            assert job["schedule_enabled"] is False
            assert job["schedule_frequency"] == "manual_only"

            preview_response = client.get("/api/sober-living-directory/discovery/scheduler/preview")
            assert preview_response.status_code == 200, preview_response.text
            preview = preview_response.json()["jobs"][0]
            assert preview["due"] is False
            assert preview["can_run"] is False
            assert preview["blocked_reason"] == "schedule_disabled"

            bad_custom_response = client.put(
                f"/api/sober-living-directory/discovery/jobs/{job['job_id']}/schedule",
                json={
                    "schedule_enabled": True,
                    "schedule_frequency": "custom_hours",
                    "schedule_interval_hours": None,
                    "max_runs_per_day": 1,
                    "schedule_timezone": "America/Los_Angeles",
                    "auto_disable_after_failures": 3,
                },
            )
            assert bad_custom_response.status_code == 422, bad_custom_response.text

            bad_max_response = client.put(
                f"/api/sober-living-directory/discovery/jobs/{job['job_id']}/schedule",
                json={
                    "schedule_enabled": True,
                    "schedule_frequency": "daily",
                    "schedule_interval_hours": None,
                    "max_runs_per_day": 30,
                    "schedule_timezone": "America/Los_Angeles",
                    "auto_disable_after_failures": 3,
                },
            )
            assert bad_max_response.status_code == 422, bad_max_response.text

            enable_daily_response = client.put(
                f"/api/sober-living-directory/discovery/jobs/{job['job_id']}/schedule",
                json={
                    "schedule_enabled": True,
                    "schedule_frequency": "daily",
                    "schedule_interval_hours": None,
                    "max_runs_per_day": 1,
                    "schedule_timezone": "America/Los_Angeles",
                    "auto_disable_after_failures": 3,
                },
            )
            assert enable_daily_response.status_code == 200, enable_daily_response.text
            enabled_job = enable_daily_response.json()["job"]
            assert enabled_job["next_scheduled_run_at"]
            assert calculate_next_run(enabled_job)

            locked = db.mark_manual_run_started(job["job_id"])
            assert locked["run_lock_until"]
            locked_preview = client.get("/api/sober-living-directory/discovery/scheduler/preview").json()["jobs"][0]
            assert locked_preview["can_run"] is False
            assert locked_preview["blocked_reason"] == "run_locked"
            db.mark_manual_run_finished(job["job_id"], status="completed")

            due_job = db.update_discovery_job(
                job["job_id"],
                DiscoveryJobUpdate(next_scheduled_run_at="2000-01-01T00:00:00"),
            )
            due_preview = client.get("/api/sober-living-directory/discovery/scheduler/preview").json()["jobs"][0]
            assert due_preview["due"] is True
            assert due_preview["can_run"] is True

            run_id = db._create_discovery_run(
                job_id=job["job_id"],
                source_id=source_id,
                trigger_type="scheduled",
                notes="scheduled smoke",
            )
            db._finish_discovery_run(
                run_id,
                status="completed",
                records_found=0,
                raw_records_created=0,
                duplicates_detected=0,
                errors_count=0,
                notes="scheduled smoke",
            )
            maxed_preview = client.get("/api/sober-living-directory/discovery/scheduler/preview").json()["jobs"][0]
            assert maxed_preview["can_run"] is False
            assert maxed_preview["blocked_reason"] == "max_runs_per_day_reached"

            custom_job_response = client.post(
                "/api/sober-living-directory/discovery/jobs",
                json={
                    "source_id": source_id,
                    "job_name": "Custom Hours Job",
                    "job_type": "scheduled_source_check",
                    "target_city": "Sacramento",
                    "target_state": "CA",
                    "query": "custom",
                    "is_active": True,
                },
            )
            assert custom_job_response.status_code == 200, custom_job_response.text
            custom_job_id = custom_job_response.json()["job"]["job_id"]
            custom_schedule_response = client.put(
                f"/api/sober-living-directory/discovery/jobs/{custom_job_id}/schedule",
                json={
                    "schedule_enabled": True,
                    "schedule_frequency": "custom_hours",
                    "schedule_interval_hours": 6,
                    "max_runs_per_day": 4,
                    "schedule_timezone": "America/Los_Angeles",
                    "auto_disable_after_failures": 2,
                },
            )
            assert custom_schedule_response.status_code == 200, custom_schedule_response.text

            bypass_source_id = client.post(
                "/api/sober-living-directory/sources",
                json={
                    "source_name": "Unsafe Source",
                    "source_type": "other",
                    "base_url": "https://example.com/unsafe",
                    "trust_level": "low",
                    "supports_api": False,
                    "supports_scraping": False,
                    "requires_manual_review": False,
                    "is_active": True,
                },
            ).json()["source"]["source_id"]
            bypass_job_id = client.post(
                "/api/sober-living-directory/discovery/jobs",
                json={
                    "source_id": bypass_source_id,
                    "job_name": "Unsafe Schedule Job",
                    "job_type": "scheduled_source_check",
                    "target_city": "San Diego",
                    "target_state": "CA",
                    "query": "unsafe",
                    "is_active": True,
                },
            ).json()["job"]["job_id"]
            blocked_schedule_response = client.put(
                f"/api/sober-living-directory/discovery/jobs/{bypass_job_id}/schedule",
                json={
                    "schedule_enabled": True,
                    "schedule_frequency": "daily",
                    "schedule_interval_hours": None,
                    "max_runs_per_day": 1,
                    "schedule_timezone": "America/Los_Angeles",
                    "auto_disable_after_failures": 3,
                },
            )
            assert blocked_schedule_response.status_code == 400, blocked_schedule_response.text

            auto_disable_job = db.update_discovery_job(
                custom_job_id,
                DiscoveryJobUpdate(
                    consecutive_failures=2,
                    auto_disable_after_failures=2,
                    next_scheduled_run_at="2000-01-01T00:00:00",
                ),
            )
            auto_disable_preview = next(
                item
                for item in client.get("/api/sober-living-directory/discovery/scheduler/preview").json()["jobs"]
                if item["job_id"] == custom_job_id
            )
            assert auto_disable_preview["can_run"] is False
            assert auto_disable_preview["blocked_reason"] == "auto_disabled_after_failures"

            db.mark_scheduled_run_finished(custom_job_id, status="failed")
            disabled_job = db.get_discovery_job(custom_job_id)
            assert disabled_job["schedule_enabled"] is False

            runs_before = len(client.get("/api/sober-living-directory/discovery/runs").json()["runs"])
            client.get("/api/sober-living-directory/discovery/scheduler/preview")
            runs_after = len(client.get("/api/sober-living-directory/discovery/runs").json()["runs"])
            assert runs_before == runs_after

            inactive_source = db.update_source(
                source_id,
                SoberLivingDirectorySourceUpdate(is_active=False),
            )
            inactive_block = client.put(
                f"/api/sober-living-directory/discovery/jobs/{job['job_id']}/schedule",
                json={
                    "schedule_enabled": True,
                    "schedule_frequency": "weekly",
                    "schedule_interval_hours": None,
                    "max_runs_per_day": 1,
                    "schedule_timezone": "America/Los_Angeles",
                    "auto_disable_after_failures": 3,
                },
            )
            assert inactive_block.status_code == 400, inactive_block.text

            print("Scheduler preview smoke test passed")
        finally:
            client.close()
            if db.connection is not None:
                db.connection.close()
                db.connection = None


if __name__ == "__main__":
    main()
