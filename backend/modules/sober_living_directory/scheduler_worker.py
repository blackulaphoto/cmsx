from __future__ import annotations

import atexit
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .database import SoberLivingDirectoryDatabase
from .discovery import SoberLivingDiscoveryService

logger = logging.getLogger(__name__)


def _utcnow_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    try:
        parsed = int(raw) if raw is not None else default
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


class SoberLivingDiscoverySchedulerWorker:
    def __init__(
        self,
        db: SoberLivingDirectoryDatabase,
        discovery_service: SoberLivingDiscoveryService,
    ) -> None:
        self.db = db
        self.discovery_service = discovery_service
        self.poll_interval_seconds = _env_int(
            "SOBER_LIVING_DIRECTORY_SCHEDULER_POLL_SECONDS",
            default=300,
            minimum=30,
            maximum=3600,
        )
        self.max_jobs_per_cycle = _env_int(
            "SOBER_LIVING_DIRECTORY_SCHEDULER_MAX_JOBS_PER_CYCLE",
            default=3,
            minimum=1,
            maximum=25,
        )
        self.autostart_enabled = _env_bool("SOBER_LIVING_DIRECTORY_SCHEDULER_AUTOSTART", default=False)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._state_lock = threading.Lock()
        self._cycle_lock = threading.Lock()
        self.started_at: Optional[str] = None
        self.stopped_at: Optional[str] = None
        self.last_poll_at: Optional[str] = None
        self.last_cycle_started_at: Optional[str] = None
        self.last_cycle_finished_at: Optional[str] = None
        self.current_job_id: Optional[str] = None
        self.current_job_name: Optional[str] = None
        self.last_cycle_summary: Dict[str, Any] = {
            "checked_jobs": 0,
            "due_jobs": 0,
            "executed_jobs": 0,
            "failed_jobs": 0,
            "skipped_jobs": 0,
            "executed_job_ids": [],
            "failed_job_ids": [],
            "skipped_reasons": {},
            "trigger": None,
        }
        atexit.register(self.stop)

    def start(self) -> Dict[str, Any]:
        with self._state_lock:
            if self.is_running:
                return self.status()
            self._stop_event.clear()
            self.started_at = _utcnow_iso()
            self.stopped_at = None
            self._thread = threading.Thread(
                target=self._run_loop,
                name="sober-living-directory-scheduler",
                daemon=True,
            )
            self._thread.start()
            logger.info(
                "Sober living directory scheduler worker started with poll interval %s seconds",
                self.poll_interval_seconds,
            )
        return self.status()

    def stop(self) -> Dict[str, Any]:
        thread: Optional[threading.Thread]
        with self._state_lock:
            thread = self._thread
            if not thread:
                self.stopped_at = self.stopped_at or _utcnow_iso()
                return self.status()
            self._stop_event.set()
        if thread.is_alive():
            thread.join(timeout=5)
        with self._state_lock:
            if self._thread is thread:
                self._thread = None
            self.current_job_id = None
            self.current_job_name = None
            self.stopped_at = _utcnow_iso()
            logger.info("Sober living directory scheduler worker stopped")
        return self.status()

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def status(self) -> Dict[str, Any]:
        with self._state_lock:
            return {
                "running": self.is_running,
                "autostart_enabled": self.autostart_enabled,
                "poll_interval_seconds": self.poll_interval_seconds,
                "max_jobs_per_cycle": self.max_jobs_per_cycle,
                "started_at": self.started_at,
                "stopped_at": self.stopped_at,
                "last_poll_at": self.last_poll_at,
                "last_cycle_started_at": self.last_cycle_started_at,
                "last_cycle_finished_at": self.last_cycle_finished_at,
                "current_job_id": self.current_job_id,
                "current_job_name": self.current_job_name,
                "last_cycle_summary": dict(self.last_cycle_summary),
                "warning": (
                    "Scheduler worker is disabled by default. All discovered records remain raw review items; "
                    "no listings are auto-published or auto-merged."
                ),
            }

    def run_once(self, *, trigger: str = "manual") -> Dict[str, Any]:
        if not self._cycle_lock.acquire(blocking=False):
            return {
                **self.status(),
                "cycle_started": False,
                "blocked_reason": "scheduler_cycle_already_running",
            }
        try:
            cycle_started_at = _utcnow_iso()
            with self._state_lock:
                self.last_poll_at = cycle_started_at
                self.last_cycle_started_at = cycle_started_at

            preview_items = self.db.list_scheduler_preview()
            due_items = [item for item in preview_items if item.get("due")]
            runnable_items = [item for item in preview_items if item.get("can_run")]
            skipped_reasons: Dict[str, int] = {}
            for item in preview_items:
                if item.get("can_run"):
                    continue
                reason = item.get("blocked_reason") or "blocked"
                skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1

            executed_job_ids: List[str] = []
            failed_job_ids: List[str] = []
            executed_runs: List[Dict[str, Any]] = []
            for item in runnable_items[: self.max_jobs_per_cycle]:
                job_id = item["job_id"]
                with self._state_lock:
                    self.current_job_id = job_id
                    self.current_job_name = item.get("job_name")
                try:
                    run = self.discovery_service.run_job(job_id, trigger_type="scheduled")
                    executed_job_ids.append(job_id)
                    executed_runs.append(run)
                except Exception:
                    logger.exception("Scheduled discovery run failed for job %s", job_id)
                    failed_job_ids.append(job_id)
                finally:
                    with self._state_lock:
                        self.current_job_id = None
                        self.current_job_name = None

            cycle_finished_at = _utcnow_iso()
            summary = {
                "checked_jobs": len(preview_items),
                "due_jobs": len(due_items),
                "executed_jobs": len(executed_job_ids),
                "failed_jobs": len(failed_job_ids),
                "skipped_jobs": max(len(preview_items) - len(executed_job_ids) - len(failed_job_ids), 0),
                "executed_job_ids": executed_job_ids,
                "failed_job_ids": failed_job_ids,
                "skipped_reasons": skipped_reasons,
                "trigger": trigger,
                "runs": executed_runs,
            }
            with self._state_lock:
                self.last_cycle_finished_at = cycle_finished_at
                self.last_cycle_summary = summary
            return {
                **self.status(),
                "cycle_started": True,
                "cycle_finished": True,
            }
        finally:
            self._cycle_lock.release()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_once(trigger="worker")
            except Exception:
                logger.exception("Unhandled scheduler worker cycle failure")
            if self._stop_event.wait(self.poll_interval_seconds):
                break


_scheduler_worker: Optional[SoberLivingDiscoverySchedulerWorker] = None


def get_scheduler_worker(
    db: SoberLivingDirectoryDatabase,
    discovery_service: SoberLivingDiscoveryService,
) -> SoberLivingDiscoverySchedulerWorker:
    global _scheduler_worker
    if _scheduler_worker is None:
        _scheduler_worker = SoberLivingDiscoverySchedulerWorker(db, discovery_service)
        if _scheduler_worker.autostart_enabled:
            _scheduler_worker.start()
    return _scheduler_worker
