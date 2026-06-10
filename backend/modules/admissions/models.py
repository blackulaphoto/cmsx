from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

ALLOWED_FORM_STATUSES = {
    "Not Started",
    "In Progress",
    "Needs Signature",
    "Completed",
    "Expired",
    "Revoked",
    "Missing Attachment",
    "Staff Review Needed",
}

ALLOWED_PACKET_STATUSES = {
    "In Progress",
    "Completed",
    "On Hold",
    "Cancelled",
}

ALLOWED_REVIEW_STATUSES = {
    "Not Reviewed",
    "Needs Correction",
    "Approved",
}


class StartPacketPayload(BaseModel):
    client_id: str = Field(..., min_length=1)
    client_name: str = Field(..., min_length=1)


class UpdateFormStatusPayload(BaseModel):
    status: str = Field(..., min_length=1)
    notes: Optional[str] = None


class SaveResponsePayload(BaseModel):
    response_data: Dict[str, Any] = Field(default_factory=dict)


class UpdateReviewPayload(BaseModel):
    review_status: str = Field(..., min_length=1)
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = None


class RecordTaskKeyPayload(BaseModel):
    task_key: str = Field(..., min_length=1)
    reminder_id: Optional[str] = None
    case_manager_id: Optional[str] = None


ALLOWED_SUPPRESSION_STATUSES = {"dismissed", "not_applicable"}


class SuppressTaskPayload(BaseModel):
    task_key: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)
    reason: Optional[str] = None
    dismissed_by: Optional[str] = None


class UpdateFinancialCoordinationPayload(BaseModel):
    billing_explained_status: Optional[str] = None
    billing_explained_date: Optional[str] = None
    billing_notes: Optional[str] = None
    insurance_verification_status: Optional[str] = None
    primary_payer_type: Optional[str] = None
    primary_plan_name: Optional[str] = None
    primary_member_id: Optional[str] = None
    verification_date: Optional[str] = None
    verification_rep_name: Optional[str] = None
    verification_reference_number: Optional[str] = None
    deductible: Optional[str] = None
    copay: Optional[str] = None
    coinsurance: Optional[str] = None
    out_of_pocket_max: Optional[str] = None
    auth_required: Optional[str] = None
    cob_status: Optional[str] = None
    cob_issue_identified: Optional[bool] = None
    cob_notes: Optional[str] = None
    cob_followup_needed: Optional[bool] = None
    payment_plan_status: Optional[str] = None
    payment_arrangement_type: Optional[str] = None
    payment_amount: Optional[str] = None
    payment_due_date: Optional[str] = None
    payment_notes: Optional[str] = None
    std_needed: Optional[str] = None
    std_status: Optional[str] = None
    std_notes: Optional[str] = None
    fmla_needed: Optional[str] = None
    linked_fmla_case_id: Optional[str] = None
    discharge_planning_started: Optional[bool] = None
    discharge_destination: Optional[str] = None
    sober_living_needed: Optional[bool] = None
    pcp_dental_psych_needed: Optional[bool] = None
    legal_probation_followup_needed: Optional[bool] = None
    benefits_followup_needed: Optional[bool] = None
    employment_resume_needed: Optional[bool] = None
    transportation_plan: Optional[str] = None
    discharge_notes: Optional[str] = None
