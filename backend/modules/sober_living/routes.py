"""Sober Living Management — API routes (Phase 1 + Phase 2 stubs)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .database import get_store
from .models import (
    BedCreate, BedTransfer, BedUpdate,
    HouseCreate, HouseUpdate,
    ResidentCreate, ResidentUpdate,
    RoomCreate, RoomUpdate,
    StayCreate, StayDischarge, StayUpdate,
    ChecklistUpdate,
    UATestCreate,
    IncidentCreate, IncidentUpdate,
    RentChargeCreate, RentPaymentCreate,
)

router = APIRouter(prefix="/api/sober-living", tags=["sober-living"])


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@router.get("/summary")
def get_summary():
    return get_store().get_summary()


# ---------------------------------------------------------------------------
# Houses
# ---------------------------------------------------------------------------

@router.get("/houses")
def list_houses():
    return get_store().list_houses()


@router.post("/houses", status_code=201)
def create_house(body: HouseCreate):
    return get_store().create_house(body.dict())


@router.get("/houses/{house_id}")
def get_house(house_id: str):
    house = get_store().get_house(house_id)
    if not house:
        raise HTTPException(404, "House not found")
    return house


@router.put("/houses/{house_id}")
def update_house(house_id: str, body: HouseUpdate):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    house = get_store().update_house(house_id, updates)
    if not house:
        raise HTTPException(404, "House not found")
    return house


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------

@router.get("/houses/{house_id}/rooms")
def list_rooms(house_id: str):
    return get_store().list_rooms(house_id)


@router.post("/houses/{house_id}/rooms", status_code=201)
def create_room(house_id: str, body: RoomCreate):
    return get_store().create_room(house_id, body.dict())


@router.put("/rooms/{room_id}")
def update_room(room_id: str, body: RoomUpdate):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    room = get_store().update_room(room_id, updates)
    if not room:
        raise HTTPException(404, "Room not found")
    return room


# ---------------------------------------------------------------------------
# Beds
# ---------------------------------------------------------------------------

@router.get("/houses/{house_id}/beds")
def list_beds(house_id: str):
    return get_store().list_beds(house_id)


@router.post("/houses/{house_id}/beds", status_code=201)
def create_bed(house_id: str, body: BedCreate):
    return get_store().create_bed(house_id, body.dict())


@router.put("/beds/{bed_id}")
def update_bed(bed_id: str, body: BedUpdate):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    bed = get_store().update_bed(bed_id, updates)
    if not bed:
        raise HTTPException(404, "Bed not found")
    return bed


# ---------------------------------------------------------------------------
# Residents
# ---------------------------------------------------------------------------

@router.get("/residents")
def list_all_residents():
    return get_store().list_all_residents()


@router.get("/houses/{house_id}/residents")
def list_residents(house_id: str):
    return get_store().list_residents_for_house(house_id)


@router.post("/residents", status_code=201)
def create_resident(body: ResidentCreate):
    return get_store().create_resident(body.dict())


@router.get("/residents/{resident_id}")
def get_resident(resident_id: str):
    r = get_store().get_resident(resident_id)
    if not r:
        raise HTTPException(404, "Resident not found")
    return r


@router.put("/residents/{resident_id}")
def update_resident(resident_id: str, body: ResidentUpdate):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    r = get_store().update_resident(resident_id, updates)
    if not r:
        raise HTTPException(404, "Resident not found")
    return r


# ---------------------------------------------------------------------------
# Stays
# ---------------------------------------------------------------------------

@router.post("/stays", status_code=201)
def create_stay(body: StayCreate):
    try:
        return get_store().create_stay(body.dict())
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.put("/stays/{stay_id}")
def update_stay(stay_id: str, body: StayUpdate):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    stay = get_store().update_stay(stay_id, updates)
    if not stay:
        raise HTTPException(404, "Stay not found")
    return stay


@router.post("/stays/{stay_id}/discharge")
def discharge_stay(stay_id: str, body: StayDischarge):
    try:
        result = get_store().discharge_stay(stay_id, body.dict())
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if not result:
        raise HTTPException(404, "Stay not found")
    return result


@router.post("/stays/{stay_id}/transfer-bed")
def transfer_bed(stay_id: str, body: BedTransfer):
    try:
        result = get_store().transfer_bed(stay_id, body.new_bed_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if not result:
        raise HTTPException(404, "Stay not found or not active")
    return result


# ---------------------------------------------------------------------------
# Compliance
# ---------------------------------------------------------------------------

@router.get("/stays/{stay_id}/compliance")
def get_checklist(stay_id: str):
    return get_store().get_checklist(stay_id) or {}


@router.put("/stays/{stay_id}/compliance")
def upsert_checklist(stay_id: str, body: ChecklistUpdate):
    stay = get_store()._get_stay(stay_id)
    if not stay:
        raise HTTPException(404, "Stay not found")
    data = {k: v for k, v in body.dict().items() if v is not None}
    return get_store().upsert_checklist(stay_id, stay["resident_id"], data)


# ---------------------------------------------------------------------------
# UA Tests
# ---------------------------------------------------------------------------

@router.get("/houses/{house_id}/ua-tests")
def list_ua_tests(house_id: str, resident_id: str = None):
    return get_store().list_ua_tests(house_id, resident_id)


@router.post("/ua-tests", status_code=201)
def create_ua_test(body: UATestCreate):
    return get_store().create_ua_test(body.dict())


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

@router.get("/houses/{house_id}/incidents")
def list_incidents(house_id: str):
    return get_store().list_incidents(house_id)


@router.post("/incidents", status_code=201)
def create_incident(body: IncidentCreate):
    return get_store().create_incident(body.dict())


@router.put("/incidents/{incident_id}")
def update_incident(incident_id: str, body: IncidentUpdate):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    result = get_store().update_incident(incident_id, updates)
    if not result:
        raise HTTPException(404, "Incident not found")
    return result


# ---------------------------------------------------------------------------
# Rent
# ---------------------------------------------------------------------------

@router.get("/stays/{stay_id}/ledger")
def get_ledger(stay_id: str):
    return get_store().get_rent_ledger(stay_id)


@router.get("/houses/{house_id}/rent-summary")
def get_rent_summary(house_id: str):
    return get_store().get_house_rent_summary(house_id)


@router.post("/rent-charges", status_code=201)
def create_charge(body: RentChargeCreate):
    return get_store().create_charge(body.dict())


@router.post("/rent-payments", status_code=201)
def create_payment(body: RentPaymentCreate):
    return get_store().create_payment(body.dict())
