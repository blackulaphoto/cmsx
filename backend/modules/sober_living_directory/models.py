from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


ALLOWED_LISTING_STATUSES = {
    "pending_review",
    "approved",
    "needs_reverification",
    "use_caution",
    "do_not_refer",
    "archived",
}

ALLOWED_TASK_STATUSES = {"open", "completed", "skipped"}
ALLOWED_TASK_PRIORITIES = {"low", "medium", "high"}
DUPLICATE_CANDIDATE_STATUSES = {"open", "merged", "kept_separate", "rejected"}
ALLOWED_SOURCE_TYPES = {
    "spreadsheet_import",
    "manual",
    "certification_directory",
    "public_directory",
    "google_places",
    "treatment_referral",
    "other",
}
ALLOWED_SOURCE_TRUST_LEVELS = {"high", "medium", "low"}
ALLOWED_DISCOVERY_JOB_TYPES = {
    "manual_test",
    "scheduled_source_check",
    "city_search",
    "reverification_check",
    "import_recheck",
}
ALLOWED_DISCOVERY_RUN_STATUSES = {"running", "completed", "failed", "cancelled"}
ALLOWED_RAW_REVIEW_STATUSES = {
    "new",
    "possible_duplicate",
    "changed",
    "error",
    "rejected",
    "approved",
    "merged",
}


class SoberLivingDirectoryListingBase(BaseModel):
    name: str = Field(..., min_length=1)
    operator_name: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: str = Field(..., min_length=1)
    state: str = Field(default="CA", min_length=2, max_length=2)
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    neighborhood: Optional[str] = None
    population_served: Optional[str] = None
    house_type: Optional[str] = None
    certification_status: Optional[str] = None
    certification_body: Optional[str] = None
    certification_expiration_date: Optional[str] = None
    monthly_rent_min: Optional[float] = None
    monthly_rent_max: Optional[float] = None
    deposit_required: Optional[bool] = None
    accepts_insurance: Optional[bool] = None
    accepts_mat: Optional[bool] = None
    accepts_probation_parole: Optional[bool] = None
    pets_allowed: Optional[bool] = None
    bed_availability_status: Optional[str] = None
    last_availability_check_date: Optional[str] = None
    last_verified_date: Optional[str] = None
    verification_method: Optional[str] = None
    primary_source_id: Optional[str] = None
    risk_flags_json: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    internal_referral_notes: Optional[str] = None
    source_urls_json: List[str] = Field(default_factory=list)
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None
    status: str = "pending_review"

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in ALLOWED_LISTING_STATUSES:
            raise ValueError(f"Invalid listing status: {value}")
        return value

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str) -> str:
        return (value or "CA").upper()

    @field_validator("monthly_rent_max")
    @classmethod
    def validate_rent_range(cls, value: Optional[float], info):
        min_value = info.data.get("monthly_rent_min")
        if value is not None and min_value is not None and value < min_value:
            raise ValueError("monthly_rent_max cannot be less than monthly_rent_min")
        return value


class SoberLivingDirectoryListingCreate(SoberLivingDirectoryListingBase):
    pass


class SoberLivingDirectoryListingUpdate(BaseModel):
    name: Optional[str] = None
    operator_name: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    neighborhood: Optional[str] = None
    population_served: Optional[str] = None
    house_type: Optional[str] = None
    certification_status: Optional[str] = None
    certification_body: Optional[str] = None
    certification_expiration_date: Optional[str] = None
    monthly_rent_min: Optional[float] = None
    monthly_rent_max: Optional[float] = None
    deposit_required: Optional[bool] = None
    accepts_insurance: Optional[bool] = None
    accepts_mat: Optional[bool] = None
    accepts_probation_parole: Optional[bool] = None
    pets_allowed: Optional[bool] = None
    bed_availability_status: Optional[str] = None
    last_availability_check_date: Optional[str] = None
    last_verified_date: Optional[str] = None
    verification_method: Optional[str] = None
    primary_source_id: Optional[str] = None
    risk_flags_json: Optional[List[str]] = None
    notes: Optional[str] = None
    internal_referral_notes: Optional[str] = None
    source_urls_json: Optional[List[str]] = None
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_optional_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in ALLOWED_LISTING_STATUSES:
            raise ValueError(f"Invalid listing status: {value}")
        return value

    @field_validator("state")
    @classmethod
    def normalize_optional_state(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value


class ListingVerifyRequest(BaseModel):
    verification_method: str = Field(default="manual_review", min_length=1)
    result_notes: Optional[str] = None


class VerificationTaskCreate(BaseModel):
    listing_id: str = Field(..., min_length=1)
    task_type: str = Field(..., min_length=1)
    priority: str = Field(default="medium")
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    status: str = Field(default="open")
    result_notes: Optional[str] = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        if value not in ALLOWED_TASK_PRIORITIES:
            raise ValueError(f"Invalid task priority: {value}")
        return value

    @field_validator("status")
    @classmethod
    def validate_task_status(cls, value: str) -> str:
        if value not in ALLOWED_TASK_STATUSES:
            raise ValueError(f"Invalid task status: {value}")
        return value


class VerificationTaskUpdate(BaseModel):
    task_type: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None
    result_notes: Optional[str] = None

    @field_validator("priority")
    @classmethod
    def validate_optional_priority(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in ALLOWED_TASK_PRIORITIES:
            raise ValueError(f"Invalid task priority: {value}")
        return value

    @field_validator("status")
    @classmethod
    def validate_optional_task_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in ALLOWED_TASK_STATUSES:
            raise ValueError(f"Invalid task status: {value}")
        return value


class DuplicateResolutionRequest(BaseModel):
    resolution_notes: Optional[str] = None
    selected_imported_fields: List[str] = Field(default_factory=list)


class RawRecordApproveRequest(BaseModel):
    direct_approve: bool = False
    force: bool = False
    review_notes: Optional[str] = None


class RawRecordRejectRequest(BaseModel):
    review_notes: Optional[str] = None


class RawRecordMarkErrorRequest(BaseModel):
    review_notes: Optional[str] = None


class SoberLivingDirectorySourceBase(BaseModel):
    source_name: str = Field(..., min_length=1)
    source_type: str = Field(..., min_length=1)
    base_url: Optional[str] = None
    trust_level: str = Field(default="medium")
    supports_api: bool = False
    supports_scraping: bool = False
    requires_manual_review: bool = True
    is_active: bool = True
    last_checked_at: Optional[str] = None

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, value: str) -> str:
        if value not in ALLOWED_SOURCE_TYPES:
            raise ValueError(f"Invalid source type: {value}")
        return value

    @field_validator("trust_level")
    @classmethod
    def validate_trust_level(cls, value: str) -> str:
        if value not in ALLOWED_SOURCE_TRUST_LEVELS:
            raise ValueError(f"Invalid trust level: {value}")
        return value


class SoberLivingDirectorySourceCreate(SoberLivingDirectorySourceBase):
    pass


class SoberLivingDirectorySourceUpdate(BaseModel):
    source_name: Optional[str] = None
    source_type: Optional[str] = None
    base_url: Optional[str] = None
    trust_level: Optional[str] = None
    supports_api: Optional[bool] = None
    supports_scraping: Optional[bool] = None
    requires_manual_review: Optional[bool] = None
    is_active: Optional[bool] = None
    last_checked_at: Optional[str] = None

    @field_validator("source_type")
    @classmethod
    def validate_optional_source_type(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in ALLOWED_SOURCE_TYPES:
            raise ValueError(f"Invalid source type: {value}")
        return value

    @field_validator("trust_level")
    @classmethod
    def validate_optional_trust_level(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in ALLOWED_SOURCE_TRUST_LEVELS:
            raise ValueError(f"Invalid trust level: {value}")
        return value


class DiscoveryJobBase(BaseModel):
    source_id: str = Field(..., min_length=1)
    job_name: str = Field(..., min_length=1)
    job_type: str = Field(..., min_length=1)
    target_city: Optional[str] = None
    target_state: Optional[str] = None
    query: Optional[str] = None
    schedule_label: Optional[str] = None
    is_active: bool = True
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None

    @field_validator("job_type")
    @classmethod
    def validate_job_type(cls, value: str) -> str:
        if value not in ALLOWED_DISCOVERY_JOB_TYPES:
            raise ValueError(f"Invalid discovery job type: {value}")
        return value

    @field_validator("target_state")
    @classmethod
    def normalize_target_state(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value


class DiscoveryJobCreate(DiscoveryJobBase):
    pass


class DiscoveryJobUpdate(BaseModel):
    source_id: Optional[str] = None
    job_name: Optional[str] = None
    job_type: Optional[str] = None
    target_city: Optional[str] = None
    target_state: Optional[str] = None
    query: Optional[str] = None
    schedule_label: Optional[str] = None
    is_active: Optional[bool] = None
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None

    @field_validator("job_type")
    @classmethod
    def validate_optional_job_type(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in ALLOWED_DISCOVERY_JOB_TYPES:
            raise ValueError(f"Invalid discovery job type: {value}")
        return value

    @field_validator("target_state")
    @classmethod
    def normalize_optional_target_state(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value


class ReviewSummary(BaseModel):
    listing_id: str
    name: str
    status: str
    city: str
    state: str
    trust_score: int
    missing_verification_fields: List[str]
    is_stale: bool
    last_verified_date: Optional[str] = None
    updated_at: str


def utcnow_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()
