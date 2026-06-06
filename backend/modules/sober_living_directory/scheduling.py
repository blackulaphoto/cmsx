from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo


DEFAULT_SCHEDULE_TIMEZONE = "America/Los_Angeles"


def calculate_next_run(job: Dict[str, Any], from_time: Optional[datetime] = None) -> Optional[str]:
    frequency = (job.get("schedule_frequency") or "manual_only").strip()
    if frequency == "manual_only":
        return None

    reference_utc = _ensure_utc(from_time or datetime.now(timezone.utc))
    zone = _get_zone(job.get("schedule_timezone"))
    existing_next = _parse_iso(job.get("next_scheduled_run_at"))
    if existing_next and existing_next > reference_utc:
        return _to_storage_iso(existing_next)

    anchor = (
        _parse_iso(job.get("last_scheduled_run_at"))
        or _parse_iso(job.get("created_at"))
        or _parse_iso(job.get("updated_at"))
        or reference_utc
    )
    anchor_local = anchor.astimezone(zone)
    reference_local = reference_utc.astimezone(zone)

    candidate_local = anchor_local
    if frequency == "daily":
        candidate_local = candidate_local + timedelta(days=1)
    elif frequency == "weekly":
        candidate_local = candidate_local + timedelta(weeks=1)
    elif frequency == "monthly":
        candidate_local = _add_months(candidate_local, 1)
    elif frequency == "custom_hours":
        interval_hours = int(job.get("schedule_interval_hours") or 0)
        if interval_hours <= 0:
            return None
        candidate_local = candidate_local + timedelta(hours=interval_hours)
    else:
        return None

    iterations = 0
    while candidate_local <= reference_local and iterations < 500:
        if frequency == "daily":
            candidate_local = candidate_local + timedelta(days=1)
        elif frequency == "weekly":
            candidate_local = candidate_local + timedelta(weeks=1)
        elif frequency == "monthly":
            candidate_local = _add_months(candidate_local, 1)
        elif frequency == "custom_hours":
            candidate_local = candidate_local + timedelta(hours=int(job.get("schedule_interval_hours") or 0))
        iterations += 1

    return _to_storage_iso(candidate_local.astimezone(timezone.utc))


def is_job_due(job: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    if not job.get("schedule_enabled"):
        return False
    if (job.get("schedule_frequency") or "manual_only") == "manual_only":
        return False

    reference_utc = _ensure_utc(now or datetime.now(timezone.utc))
    next_run = _parse_iso(job.get("next_scheduled_run_at"))
    if not next_run:
        return False
    return next_run <= reference_utc


def can_run_job(
    job: Dict[str, Any],
    now: Optional[datetime] = None,
    *,
    source: Optional[Dict[str, Any]] = None,
    scheduled_runs_today: int = 0,
) -> tuple[bool, Optional[str]]:
    reference_utc = _ensure_utc(now or datetime.now(timezone.utc))

    if not job.get("is_active"):
        return False, "job_inactive"
    if not job.get("schedule_enabled"):
        return False, "schedule_disabled"
    if (job.get("schedule_frequency") or "manual_only") == "manual_only":
        return False, "manual_only"
    if source:
        if not source.get("is_active"):
            return False, "source_inactive"
        if not source.get("requires_manual_review"):
            return False, "source_bypasses_review"
    if should_auto_disable_job(job):
        return False, "auto_disabled_after_failures"
    lock_until = _parse_iso(job.get("run_lock_until"))
    if lock_until and lock_until > reference_utc:
        return False, "run_locked"
    if scheduled_runs_today >= int(job.get("max_runs_per_day") or 1):
        return False, "max_runs_per_day_reached"
    if not is_job_due(job, reference_utc):
        return False, "not_due"
    return True, None


def should_auto_disable_job(job: Dict[str, Any]) -> bool:
    consecutive_failures = int(job.get("consecutive_failures") or 0)
    threshold = int(job.get("auto_disable_after_failures") or 3)
    return threshold > 0 and consecutive_failures >= threshold


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _to_storage_iso(value: datetime) -> str:
    return _ensure_utc(value).replace(tzinfo=None, microsecond=0).isoformat()


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _get_zone(name: Optional[str]) -> ZoneInfo:
    try:
        return ZoneInfo(name or DEFAULT_SCHEDULE_TIMEZONE)
    except Exception:
        return ZoneInfo(DEFAULT_SCHEDULE_TIMEZONE)


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)
