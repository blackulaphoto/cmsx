from __future__ import annotations

import csv
import os
import tempfile
from pathlib import Path

from backend.modules.sober_living_directory.database import SoberLivingDirectoryDatabase
from backend.modules.sober_living_directory.discovery import SoberLivingDiscoveryService
from backend.modules.sober_living_directory.models import (
    DiscoveryJobCreate,
    DiscoveryJobUpdate,
    SoberLivingDirectorySourceCreate,
)
from backend.modules.sober_living_directory.scheduler_worker import SoberLivingDiscoverySchedulerWorker


def main() -> None:
    workspace_root = Path(__file__).resolve().parents[3]
    csv_path = workspace_root / "uploads" / "sober_living_directory" / "scheduler_worker_smoke.csv"
    os.makedirs(csv_path.parent, exist_ok=True)
    if csv_path.exists():
        csv_path.unlink()

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["name", "city", "state", "phone", "website", "population_served"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "name": "Scheduler Smoke House",
                "city": "Los Angeles",
                "state": "CA",
                "phone": "555-111-0000",
                "website": "https://scheduler-smoke.test",
                "population_served": "Men",
            }
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        db = SoberLivingDirectoryDatabase(str(Path(temp_dir) / "sober_living_directory.db"))
        discovery_service = SoberLivingDiscoveryService(db)
        worker = SoberLivingDiscoverySchedulerWorker(db, discovery_service)

        source = db.create_source(
            SoberLivingDirectorySourceCreate(
                source_name="Scheduler Smoke Spreadsheet",
                source_type="spreadsheet_import",
                base_url=str(csv_path.relative_to(workspace_root)),
                trust_level="medium",
                supports_api=False,
                supports_scraping=False,
                requires_manual_review=True,
                is_active=True,
            )
        )
        job = db.create_discovery_job(
            DiscoveryJobCreate(
                source_id=source["source_id"],
                job_name="Scheduler Smoke Job",
                job_type="scheduled_source_check",
                target_city="Los Angeles",
                target_state="CA",
                query=None,
                is_active=True,
                schedule_enabled=True,
                schedule_frequency="daily",
                max_runs_per_day=1,
                schedule_timezone="America/Los_Angeles",
                auto_disable_after_failures=3,
            )
        )
        db.update_discovery_job(
            job["job_id"],
            DiscoveryJobUpdate(
                next_scheduled_run_at="2000-01-01T00:00:00",
                last_scheduled_run_at="1999-12-31T00:00:00",
            ),
        )

        preview_before = db.list_scheduler_preview()
        smoke_preview = next(item for item in preview_before if item["job_id"] == job["job_id"])
        assert smoke_preview["due"] is True
        assert smoke_preview["can_run"] is True

        status_before = worker.status()
        assert status_before["running"] is False

        cycle_result = worker.run_once(trigger="manual_tick")
        assert cycle_result["last_cycle_summary"]["executed_jobs"] == 1

        runs = db.list_discovery_runs(job_id=job["job_id"])
        assert len(runs) == 1
        assert runs[0]["trigger_type"] == "scheduled"

        raw_records = db.list_raw_records(run_id=runs[0]["run_id"])
        assert len(raw_records) == 1
        assert db.list_listings({}) == []

        preview_after = db.list_scheduler_preview()
        smoke_preview_after = next(item for item in preview_after if item["job_id"] == job["job_id"])
        assert smoke_preview_after["can_run"] is False
        assert smoke_preview_after["blocked_reason"] in {"max_runs_per_day_reached", "not_due"}

        if db.connection is not None:
            db.connection.close()
            db.connection = None

    print("Scheduler worker smoke test passed", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
