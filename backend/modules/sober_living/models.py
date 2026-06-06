"""Pydantic models for sober living module — Phase 1 MVP."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# House
# ---------------------------------------------------------------------------

class HouseCreate(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    manager_name: Optional[str] = None
    gender_policy: Optional[str] = "any"
    total_capacity: Optional[int] = 0
    notes: Optional[str] = None
    status: Optional[str] = "active"


class HouseUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    manager_name: Optional[str] = None
    gender_policy: Optional[str] = None
    total_capacity: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[str] = None


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------

class RoomCreate(BaseModel):
    room_number: str
    floor: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Bed
# ---------------------------------------------------------------------------

class BedCreate(BaseModel):
    bed_label: str
    room_id: Optional[str] = None
    status: Optional[str] = "available"
    notes: Optional[str] = None


class BedUpdate(BaseModel):
    bed_label: Optional[str] = None
    room_id: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Resident
# ---------------------------------------------------------------------------

class ResidentCreate(BaseModel):
    first_name: str
    last_name: str
    client_id: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    sobriety_date: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = "active"


# ---------------------------------------------------------------------------
# Stay
# ---------------------------------------------------------------------------

class StayCreate(BaseModel):
    resident_id: str
    house_id: str
    bed_id: Optional[str] = None
    move_in_date: str


class StayUpdate(BaseModel):
    bed_id: Optional[str] = None
    move_in_date: Optional[str] = None
    move_out_date: Optional[str] = None
    discharge_reason: Optional[str] = None
    discharge_notes: Optional[str] = None
    status: Optional[str] = None


class StayDischarge(BaseModel):
    discharge_reason: Optional[str] = None
    discharge_notes: Optional[str] = None
    move_out_date: Optional[str] = None


class BedTransfer(BaseModel):
    new_bed_id: str


# ---------------------------------------------------------------------------
# Rent Agreement (Phase 2)
# ---------------------------------------------------------------------------

class RentAgreementCreate(BaseModel):
    stay_id: str
    resident_id: str
    house_id: str
    rent_amount: float
    frequency: Optional[str] = "monthly"
    due_day: Optional[int] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class RentAgreementUpdate(BaseModel):
    rent_amount: Optional[float] = None
    frequency: Optional[str] = None
    due_day: Optional[int] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


# ---------------------------------------------------------------------------
# Rent Payment (Phase 2)
# ---------------------------------------------------------------------------

class RentPaymentCreate(BaseModel):
    agreement_id: str
    stay_id: str
    resident_id: str
    house_id: str
    amount: float
    payment_date: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    recorded_by: Optional[str] = None
