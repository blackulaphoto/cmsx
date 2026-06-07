from __future__ import annotations

import logging
from typing import Optional

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from .database import SoberLivingDirectoryDatabase
from .discovery import SoberLivingDiscoveryService
from .importer import SoberLivingDirectoryImporter
from .scheduler_worker import SoberLivingDiscoverySchedulerWorker
from .models import (
    DiscoveryJobCreate,
    DiscoveryJobScheduleUpdate,
    DiscoveryJobUpdate,
    DuplicateResolutionRequest,
    ListingVerifyRequest,
    LiveDirectorySearchRequest,
    RawRecordApproveRequest,
    RawRecordMarkErrorRequest,
    RawRecordRejectRequest,
    SoberLivingDirectorySourceCreate,
    SoberLivingDirectorySourceUpdate,
    SoberLivingDirectoryListingCreate,
    SoberLivingDirectoryListingUpdate,
    VerificationTaskCreate,
    VerificationTaskUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sober-living-directory"])
directory_db: Optional[SoberLivingDirectoryDatabase] = None
scheduler_worker: Optional[SoberLivingDiscoverySchedulerWorker] = None
scheduler_db_path: Optional[str] = None
UPLOADS_DIR = Path(__file__).resolve().parents[3] / "uploads" / "sober_living_directory"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def get_directory_db() -> SoberLivingDirectoryDatabase:
    global directory_db
    if directory_db is None:
        directory_db = SoberLivingDirectoryDatabase()
    return directory_db


def get_importer() -> SoberLivingDirectoryImporter:
    return SoberLivingDirectoryImporter(get_directory_db())


def get_discovery_service() -> SoberLivingDiscoveryService:
    return SoberLivingDiscoveryService(get_directory_db())


def get_scheduler():
    global scheduler_worker, scheduler_db_path
    db = get_directory_db()
    if scheduler_worker is None or scheduler_db_path != db.db_path:
        if scheduler_worker is not None:
            scheduler_worker.stop()
        scheduler_worker = SoberLivingDiscoverySchedulerWorker(db, SoberLivingDiscoveryService(db))
        scheduler_db_path = db.db_path
    return scheduler_worker


@router.get("/listings")
async def get_listings(
    search: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    population_served: Optional[str] = Query(None),
    certification: Optional[str] = Query(None),
    accepts_mat: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    min_trust_score: Optional[int] = Query(None),
):
    try:
        listings = get_directory_db().list_listings(
            {
                "search": search,
                "city": city,
                "population_served": population_served,
                "certification": certification,
                "accepts_mat": accepts_mat,
                "status": status,
                "min_trust_score": min_trust_score,
            }
        )
        return {
            "success": True,
            "listings": listings,
            "total_count": len(listings),
        }
    except Exception as exc:
        logger.error("Failed to get sober living directory listings: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/listings")
async def create_listing(payload: SoberLivingDirectoryListingCreate):
    try:
        listing = get_directory_db().create_listing(payload)
        return {"success": True, "listing": listing}
    except Exception as exc:
        logger.error("Failed to create sober living directory listing: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/search/live")
async def search_live_directory(payload: LiveDirectorySearchRequest):
    try:
        external_results = get_discovery_service().search_live_results(
            query=payload.query,
            city=payload.city,
            state=payload.state,
            zip_code=payload.zip_code,
            sources=payload.sources,
        )
        return {
            "success": True,
            "external_results": external_results,
            "total_count": len(external_results),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to search live sober living sources: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/listings/{listing_id}")
async def get_listing(listing_id: str):
    listing = get_directory_db().get_listing(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"success": True, "listing": listing}


@router.put("/listings/{listing_id}")
async def update_listing(listing_id: str, payload: SoberLivingDirectoryListingUpdate):
    try:
        listing = get_directory_db().update_listing(listing_id, payload)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        return {"success": True, "listing": listing}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update sober living directory listing: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/listings/{listing_id}/verify")
async def verify_listing(listing_id: str, payload: ListingVerifyRequest):
    try:
        listing = get_directory_db().verify_listing(listing_id, payload)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        return {"success": True, "listing": listing}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to verify sober living directory listing: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/listings/{listing_id}/archive")
async def archive_listing(listing_id: str):
    try:
        listing = get_directory_db().archive_listing(listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        return {"success": True, "listing": listing}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to archive sober living directory listing: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/review")
async def get_review_queue():
    try:
        listings = get_directory_db().get_review_queue()
        duplicates = get_directory_db().get_duplicate_candidates()
        raw_records = get_directory_db().get_raw_review_queue()
        return {
            "success": True,
            "listings": listings,
            "duplicate_candidates": duplicates,
            "raw_records": raw_records,
            "total_count": len(listings),
            "duplicate_count": len(duplicates),
        }
    except Exception as exc:
        logger.error("Failed to get sober living directory review queue: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/raw-records")
async def get_raw_records(
    review_status: Optional[str] = Query(None),
    source_id: Optional[str] = Query(None),
    run_id: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
):
    try:
        raw_records = get_directory_db().list_raw_records(
            review_statuses=[review_status] if review_status else None,
            source_id=source_id,
            run_id=run_id,
            city=city,
            state=state,
        )
        return {"success": True, "raw_records": raw_records, "total_count": len(raw_records)}
    except Exception as exc:
        logger.error("Failed to list raw records: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/raw-records/{raw_id}")
async def get_raw_record(raw_id: str):
    try:
        detail = get_directory_db().get_raw_record(raw_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Raw record not found")
        return {"success": True, **detail}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get raw record detail: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/raw-records/{raw_id}/approve")
async def approve_raw_record(raw_id: str, payload: RawRecordApproveRequest):
    try:
        result = get_directory_db().approve_raw_record(
            raw_id,
            direct_approve=payload.direct_approve,
            force=payload.force,
            review_notes=payload.review_notes,
        )
        return {"success": True, **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to approve raw record: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/raw-records/{raw_id}/reject")
async def reject_raw_record(raw_id: str, payload: RawRecordRejectRequest):
    try:
        detail = get_directory_db().reject_raw_record(raw_id, review_notes=payload.review_notes)
        return {"success": True, "raw_record": detail["raw_record"]}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to reject raw record: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/raw-records/{raw_id}/mark-error")
async def mark_raw_record_error(raw_id: str, payload: RawRecordMarkErrorRequest):
    try:
        detail = get_directory_db().mark_raw_record_error(raw_id, review_notes=payload.review_notes)
        return {"success": True, "raw_record": detail["raw_record"]}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to mark raw record error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/sources")
async def get_sources():
    try:
        sources = get_directory_db().list_sources()
        return {"success": True, "sources": sources, "total_count": len(sources)}
    except Exception as exc:
        logger.error("Failed to get sober living directory sources: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/sources")
async def create_source(payload: SoberLivingDirectorySourceCreate):
    try:
        source = get_directory_db().create_source(payload)
        return {"success": True, "source": source}
    except Exception as exc:
        logger.error("Failed to create sober living directory source: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/sources/{source_id}")
async def get_source(source_id: str):
    source = get_directory_db().get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return {"success": True, "source": source}


@router.put("/sources/{source_id}")
async def update_source(source_id: str, payload: SoberLivingDirectorySourceUpdate):
    try:
        source = get_directory_db().update_source(source_id, payload)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return {"success": True, "source": source}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update sober living directory source: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/discovery/jobs")
async def get_discovery_jobs():
    try:
        jobs = get_directory_db().list_discovery_jobs()
        return {"success": True, "jobs": jobs, "total_count": len(jobs)}
    except Exception as exc:
        logger.error("Failed to get discovery jobs: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/discovery/jobs")
async def create_discovery_job(payload: DiscoveryJobCreate):
    try:
        job = get_directory_db().create_discovery_job(payload)
        return {"success": True, "job": job}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to create discovery job: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/discovery/jobs/{job_id}")
async def get_discovery_job(job_id: str):
    job = get_directory_db().get_discovery_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Discovery job not found")
    return {"success": True, "job": job}


@router.put("/discovery/jobs/{job_id}")
async def update_discovery_job(job_id: str, payload: DiscoveryJobUpdate):
    try:
        job = get_directory_db().update_discovery_job(job_id, payload)
        if not job:
            raise HTTPException(status_code=404, detail="Discovery job not found")
        return {"success": True, "job": job}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update discovery job: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/discovery/jobs/{job_id}/schedule")
async def update_discovery_job_schedule(job_id: str, payload: DiscoveryJobScheduleUpdate):
    try:
        job = get_directory_db().update_discovery_job_schedule(job_id, payload)
        if not job:
            raise HTTPException(status_code=404, detail="Discovery job not found")
        return {"success": True, "job": job}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update discovery job schedule: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/discovery/runs")
async def get_discovery_runs(job_id: Optional[str] = Query(None)):
    try:
        runs = get_directory_db().list_discovery_runs(job_id=job_id)
        return {"success": True, "runs": runs, "total_count": len(runs)}
    except Exception as exc:
        logger.error("Failed to get discovery runs: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/discovery/runs/{run_id}")
async def get_discovery_run(run_id: str):
    run = get_directory_db().get_discovery_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Discovery run not found")
    return {"success": True, "run": run}


@router.get("/discovery/scheduler/preview")
async def get_scheduler_preview():
    try:
        preview = get_directory_db().list_scheduler_preview()
        return {"success": True, "jobs": preview, "total_count": len(preview)}
    except Exception as exc:
        logger.error("Failed to get scheduler preview: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/discovery/scheduler/status")
async def get_scheduler_status():
    try:
        return {"success": True, "scheduler": get_scheduler().status()}
    except Exception as exc:
        logger.error("Failed to get scheduler status: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/discovery/scheduler/start")
async def start_scheduler_worker():
    try:
        return {"success": True, "scheduler": get_scheduler().start()}
    except Exception as exc:
        logger.error("Failed to start scheduler worker: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/discovery/scheduler/stop")
async def stop_scheduler_worker():
    try:
        return {"success": True, "scheduler": get_scheduler().stop()}
    except Exception as exc:
        logger.error("Failed to stop scheduler worker: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/discovery/scheduler/run-once")
async def run_scheduler_once():
    try:
        return {"success": True, "scheduler": get_scheduler().run_once(trigger="manual_tick")}
    except Exception as exc:
        logger.error("Failed to execute scheduler poll once: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/discovery/jobs/{job_id}/run-test")
async def run_discovery_job_test(job_id: str):
    try:
        run = get_directory_db().run_manual_discovery_job_test(job_id)
        return {"success": True, "run": run}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to run discovery job test: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/discovery/jobs/{job_id}/run")
async def run_discovery_job(job_id: str):
    try:
        run = get_discovery_service().run_job(job_id)
        return {"success": True, "run": run}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to run discovery job connector: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/duplicates/{candidate_id}")
async def get_duplicate_candidate(candidate_id: str):
    try:
        detail = get_directory_db().get_duplicate_candidate_detail(candidate_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Duplicate candidate not found")
        return {"success": True, **detail}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get duplicate candidate detail: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/tasks")
async def get_tasks(listing_id: Optional[str] = Query(None)):
    try:
        tasks = get_directory_db().list_tasks(listing_id=listing_id)
        return {"success": True, "tasks": tasks, "total_count": len(tasks)}
    except Exception as exc:
        logger.error("Failed to get sober living directory tasks: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/tasks")
async def create_task(payload: VerificationTaskCreate):
    try:
        task = get_directory_db().create_task(payload)
        return {"success": True, "task": task}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to create sober living directory task: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/tasks/{task_id}")
async def update_task(task_id: str, payload: VerificationTaskUpdate):
    try:
        task = get_directory_db().update_task(task_id, payload)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"success": True, "task": task}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update sober living directory task: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/duplicates/{candidate_id}/merge")
async def merge_duplicate_candidate(candidate_id: str, payload: DuplicateResolutionRequest):
    try:
        candidate = get_directory_db().resolve_duplicate_candidate(
            candidate_id,
            action="merged",
            resolution_notes=payload.resolution_notes,
            selected_imported_fields=payload.selected_imported_fields,
        )
        if not candidate:
            raise HTTPException(status_code=404, detail="Duplicate candidate not found")
        return {"success": True, "candidate": candidate}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to merge duplicate candidate: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/duplicates/{candidate_id}/keep-separate")
async def keep_duplicate_candidate_separate(candidate_id: str, payload: DuplicateResolutionRequest):
    try:
        candidate = get_directory_db().resolve_duplicate_candidate(
            candidate_id,
            action="kept_separate",
            resolution_notes=payload.resolution_notes,
        )
        if not candidate:
            raise HTTPException(status_code=404, detail="Duplicate candidate not found")
        return {"success": True, "candidate": candidate}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to keep duplicate candidate separate: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/duplicates/{candidate_id}/reject")
async def reject_duplicate_candidate(candidate_id: str, payload: DuplicateResolutionRequest):
    try:
        candidate = get_directory_db().resolve_duplicate_candidate(
            candidate_id,
            action="rejected",
            resolution_notes=payload.resolution_notes,
        )
        if not candidate:
            raise HTTPException(status_code=404, detail="Duplicate candidate not found")
        return {"success": True, "candidate": candidate}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to reject duplicate candidate: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/import")
async def import_directory_file(
    file: UploadFile = File(...),
    source_name: str = Form("Manual directory import"),
    source_type: str = Form("spreadsheet_import"),
):
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Import file is required")

        suffix = Path(file.filename).suffix.lower()
        if suffix not in {".xlsx", ".csv"}:
            raise HTTPException(status_code=400, detail="Only .xlsx and .csv files are supported")

        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded import file is empty")

        stored_path = UPLOADS_DIR / f"{source_name.strip().replace(' ', '_')}_{Path(file.filename).name}"
        stored_path.write_bytes(content)

        summary = get_importer().import_file(
            file_name=file.filename,
            content=content,
            source_name=source_name,
            source_type=source_type,
        )
        summary["stored_path"] = str(stored_path)
        return {"success": True, "summary": summary}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to import sober living directory file: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
