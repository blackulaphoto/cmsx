"""Pydantic models for sober living module — Phase 1 + Phase 2."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# House
# ---------------------------------------------------------------------------

class HouseCreate(BaseModel):
    house_name: str
    house_manager_name: Optional[str] = None
    house_manager_phone: Optional[str] = None
    house_manager_email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    house_type: Optional[str] = "any"
    certification_level: Optional[str] = None
    certification_notes: Optional[str] = None
    total_beds: Optional[int] = 0
    monthly_rent: Optional[float] = None
    house_rules_version: Optional[str] = None
    affiliated_clinical_program: Optional[str] = None
    notes: Optional[str] = None
    payment_type: Optional[str] = "unknown"
    accepts_insurance: Optional[str] = "unknown"
    insurance_plans_accepted: Optional[str] = None
    funding_notes: Optional[str] = None
    requires_clinical_program: Optional[int] = 0
    billing_contact_name: Optional[str] = None
    billing_contact_phone: Optional[str] = None
    billing_contact_email: Optional[str] = None


class HouseUpdate(BaseModel):
    house_name: Optional[str] = None
    house_manager_name: Optional[str] = None
    house_manager_phone: Optional[str] = None
    house_manager_email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    house_type: Optional[str] = None
    certification_level: Optional[str] = None
    certification_notes: Optional[str] = None
    total_beds: Optional[int] = None
    monthly_rent: Optional[float] = None
    house_rules_version: Optional[str] = None
    affiliated_clinical_program: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[int] = None
    payment_type: Optional[str] = None
    accepts_insurance: Optional[str] = None
    insurance_plans_accepted: Optional[str] = None
    funding_notes: Optional[str] = None
    requires_clinical_program: Optional[int] = None
    billing_contact_name: Optional[str] = None
    billing_contact_phone: Optional[str] = None
    billing_contact_email: Optional[str] = None


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------

class RoomCreate(BaseModel):
    room_name: str
    floor: Optional[str] = None
    room_type: Optional[str] = None
    max_occupancy: Optional[int] = 1
    notes: Optional[str] = None


class RoomUpdate(BaseModel):
    room_name: Optional[str] = None
    floor: Optional[str] = None
    room_type: Optional[str] = None
    max_occupancy: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[int] = None


# ---------------------------------------------------------------------------
# Bed
# ---------------------------------------------------------------------------

class BedCreate(BaseModel):
    bed_label: str
    room_id: str
    bed_status: Optional[str] = "available"
    reserved_for_client_id: Optional[str] = None
    reserved_until: Optional[str] = None
    notes: Optional[str] = None


class BedUpdate(BaseModel):
    bed_label: Optional[str] = None
    room_id: Optional[str] = None
    bed_status: Optional[str] = None
    reserved_for_client_id: Optional[str] = None
    reserved_until: Optional[str] = None
    notes: Optional[str] = None


class BedTransfer(BaseModel):
    new_bed_id: str


# ---------------------------------------------------------------------------
# Resident
# ---------------------------------------------------------------------------

class ResidentCreate(BaseModel):
    first_name: str
    last_name: str
    linked_client_id: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    primary_substance: Optional[str] = None
    sobriety_date: Optional[str] = None
    notes: Optional[str] = None


class ResidentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    primary_substance: Optional[str] = None
    sobriety_date: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Stay
# ---------------------------------------------------------------------------

class StayCreate(BaseModel):
    resident_id: str
    house_id: str
    bed_id: Optional[str] = None
    move_in_date: str
    expected_move_out_date: Optional[str] = None
    clinical_program: Optional[str] = None
    case_manager_name: Optional[str] = None
    referral_source: Optional[str] = None
    step_down_from_level: Optional[str] = None


class StayUpdate(BaseModel):
    bed_id: Optional[str] = None
    move_in_date: Optional[str] = None
    expected_move_out_date: Optional[str] = None
    clinical_program: Optional[str] = None
    case_manager_name: Optional[str] = None
    referral_source: Optional[str] = None
    step_down_from_level: Optional[str] = None
    resident_status: Optional[str] = None


class StayDischarge(BaseModel):
    actual_move_out_date: Optional[str] = None
    move_out_reason: Optional[str] = None
    discharge_destination: Optional[str] = None


# ---------------------------------------------------------------------------
# Compliance
# ---------------------------------------------------------------------------

class ChecklistUpdate(BaseModel):
    house_rules_signed: Optional[int] = None
    house_rules_signed_date: Optional[str] = None
    photo_id_on_file: Optional[int] = None
    emergency_contact_on_file: Optional[int] = None
    intake_form_complete: Optional[int] = None
    consent_to_coordinate_care: Optional[int] = None
    medication_policy_signed: Optional[int] = None
    ua_policy_signed: Optional[int] = None
    financial_agreement_signed: Optional[int] = None
    grievance_policy_acknowledged: Optional[int] = None
    good_neighbor_policy_acknowledged: Optional[int] = None
    release_of_information_on_file: Optional[int] = None
    missing_items_summary: Optional[str] = None


# ---------------------------------------------------------------------------
# UA Tests
# ---------------------------------------------------------------------------

class UATestCreate(BaseModel):
    house_id: str
    resident_id: str
    stay_id: str
    test_date: str
    test_time: Optional[str] = None
    test_type: Optional[str] = None
    test_method: Optional[str] = None
    administered_by_name: Optional[str] = None
    result: Optional[str] = None
    substances_tested_json: Optional[str] = None
    positive_substances_json: Optional[str] = None
    specimen_validity: Optional[str] = None
    action_taken: Optional[str] = None
    clinical_notified: Optional[int] = 0
    clinical_notified_at: Optional[str] = None
    case_manager_notified: Optional[int] = 0
    case_manager_notified_at: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

class IncidentCreate(BaseModel):
    house_id: str
    incident_date: str
    incident_type: str
    resident_id: Optional[str] = None
    stay_id: Optional[str] = None
    incident_time: Optional[str] = None
    severity: Optional[str] = None
    location_in_house: Optional[str] = None
    description: Optional[str] = None
    immediate_safety_concern: Optional[int] = 0
    response_taken: Optional[str] = None
    clinical_notified: Optional[int] = 0
    clinical_notified_at: Optional[str] = None
    case_manager_notified: Optional[int] = 0
    law_enforcement_involved: Optional[int] = 0
    emergency_services_involved: Optional[int] = 0
    witness_names: Optional[str] = None
    reported_by_name: Optional[str] = None
    follow_up_required: Optional[int] = 0
    follow_up_due_date: Optional[str] = None
    incident_resolved: Optional[int] = 0
    resolution_notes: Optional[str] = None


class IncidentUpdate(BaseModel):
    incident_type: Optional[str] = None
    severity: Optional[str] = None
    location_in_house: Optional[str] = None
    description: Optional[str] = None
    immediate_safety_concern: Optional[int] = None
    response_taken: Optional[str] = None
    clinical_notified: Optional[int] = None
    clinical_notified_at: Optional[str] = None
    case_manager_notified: Optional[int] = None
    law_enforcement_involved: Optional[int] = None
    emergency_services_involved: Optional[int] = None
    witness_names: Optional[str] = None
    reported_by_name: Optional[str] = None
    follow_up_required: Optional[int] = None
    follow_up_due_date: Optional[str] = None
    incident_resolved: Optional[int] = None
    resolution_notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Rent
# ---------------------------------------------------------------------------

class RentChargeCreate(BaseModel):
    resident_id: str
    stay_id: str
    house_id: str
    charge_month: str
    amount: float
    charge_type: Optional[str] = "rent"
    due_date: Optional[str] = None
    status: Optional[str] = "unpaid"
    notes: Optional[str] = None


class RentPaymentCreate(BaseModel):
    resident_id: str
    stay_id: str
    house_id: str
    amount: float
    payment_date: Optional[str] = None
    payment_method: Optional[str] = None
    payment_for_month: Optional[str] = None
    applied_charge_id: Optional[str] = None
    is_late: Optional[int] = 0
    late_fee_charged: Optional[float] = 0
    receipt_number: Optional[str] = None
    received_by: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Meetings
# ---------------------------------------------------------------------------

class MeetingCreate(BaseModel):
    house_id: str
    scheduled_date: str
    meeting_type: Optional[str] = "house"
    scheduled_time: Optional[str] = None
    topic: Optional[str] = None
    facilitator_name: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = "scheduled"
    attendance_json: Optional[str] = None
    notes: Optional[str] = None


class MeetingUpdate(BaseModel):
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    meeting_type: Optional[str] = None
    topic: Optional[str] = None
    facilitator_name: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    attendance_json: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Chores
# ---------------------------------------------------------------------------

class ChoreCreate(BaseModel):
    house_id: str
    chore_name: str
    due_date: str
    resident_id: Optional[str] = None
    stay_id: Optional[str] = None
    location: Optional[str] = None
    recurrence: Optional[str] = "once"
    assigned_by: Optional[str] = None
    notes: Optional[str] = None


class ChoreUpdate(BaseModel):
    chore_name: Optional[str] = None
    resident_id: Optional[str] = None
    stay_id: Optional[str] = None
    location: Optional[str] = None
    due_date: Optional[str] = None
    recurrence: Optional[str] = None
    assigned_by: Optional[str] = None
    completed: Optional[int] = None
    completed_at: Optional[str] = None
    verified_by: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Passes
# ---------------------------------------------------------------------------

class PassCreate(BaseModel):
    house_id: str
    resident_id: str
    stay_id: str
    leave_date: str
    expected_return_date: str
    pass_type: Optional[str] = "day"
    destination: Optional[str] = None
    leave_time: Optional[str] = None
    expected_return_time: Optional[str] = None
    approved_by: Optional[str] = None
    status: Optional[str] = "approved"
    is_blackout: Optional[int] = 0
    notes: Optional[str] = None


class PassUpdate(BaseModel):
    pass_type: Optional[str] = None
    destination: Optional[str] = None
    leave_date: Optional[str] = None
    leave_time: Optional[str] = None
    expected_return_date: Optional[str] = None
    expected_return_time: Optional[str] = None
    actual_return_date: Optional[str] = None
    actual_return_time: Optional[str] = None
    approved_by: Optional[str] = None
    status: Optional[str] = None
    is_blackout: Optional[int] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Curfew checks
# ---------------------------------------------------------------------------

class CurfewCheckUpsert(BaseModel):
    resident_id: str
    stay_id: str
    status: str
    check_date: Optional[str] = None  # defaults to today UTC on server if omitted
    checked_by: Optional[str] = None
    method: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Bulk bed creation
# ---------------------------------------------------------------------------

class BulkBedCreate(BaseModel):
    room_id: str
    quantity: int
    label_prefix: Optional[str] = ""
    start_number: Optional[int] = 1
    bed_status: Optional[str] = "available"
