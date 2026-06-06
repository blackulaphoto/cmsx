"""Sober living API routes — Phase 1 MVP."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .database import get_store
from .models import (
    BedCreate, BedTransfer, BedUpdate,
    HouseCreate, HouseUpdate,
    ResidentCreate,
    RoomCreate,
    StayCreate, StayDischarge, StayUpdate,
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
        raise HTTPException(status_code=404, detail="House not found")
    return house


@router.put("/houses/{house_id}")
def update_house(house_id: str, body: HouseUpdate):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    house = get_store().update_house(house_id, updates)
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
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
        raise HTTPException(status_code=404, detail="Bed not found")
    return bed


# ---------------------------------------------------------------------------
# Residents
# ---------------------------------------------------------------------------

@router.get("/houses/{house_id}/residents")
def list_residents(house_id: str):
    return get_store().list_residents_for_house(house_id)


@router.post("/residents", status_code=201)
def create_resident(body: ResidentCreate):
    return get_store().create_resident(body.dict())


# ---------------------------------------------------------------------------
# Stays
# ---------------------------------------------------------------------------

@router.post("/stays", status_code=201)
def create_stay(body: StayCreate):
    try:
        return get_store().create_stay(body.dict())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/stays/{stay_id}")
def update_stay(stay_id: str, body: StayUpdate):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    stay = get_store().update_stay(stay_id, updates)
    if not stay:
        raise HTTPException(status_code=404, detail="Stay not found")
    return stay


@router.post("/stays/{stay_id}/discharge")
def discharge_stay(stay_id: str, body: StayDischarge):
    try:
        result = get_store().discharge_stay(stay_id, body.dict())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not result:
        raise HTTPException(status_code=404, detail="Stay not found")
    return result


@router.post("/stays/{stay_id}/transfer-bed")
def transfer_bed(stay_id: str, body: BedTransfer):
    try:
        result = get_store().transfer_bed(stay_id, body.new_bed_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not result:
        raise HTTPException(status_code=404, detail="Stay not found or not active")
    return result
