"""Sober Living Management — API routes (Phase 1 + Phase 2 stubs)."""

from __future__ import annotations

import logging
import traceback

from fastapi import APIRouter, HTTPException

from .database import get_store, _use_postgres, _pg_conn, _database_url
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
    MeetingCreate, MeetingUpdate,
    ChoreCreate, ChoreUpdate,
    PassCreate, PassUpdate,
    CurfewCheckUpsert,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sober-living", tags=["sober-living"])


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@router.get("/summary")
def get_summary():
    return get_store().get_summary()


@router.get("/diagnostics")
def diagnostics():
    """Returns schema state and backend info — no secrets, safe to call authenticated."""
    result = {
        "backend": "postgres" if _use_postgres() else "sqlite",
        "store_loaded": False,
        "tables": {},
        "errors": [],
    }
    try:
        get_store()
        result["store_loaded"] = True
    except Exception as e:
        result["errors"].append(f"get_store: {e}")

    if _use_postgres():
        try:
            with _pg_conn() as conn:
                cur = conn.cursor()
                for table in [
                    "sober_living_houses", "sober_living_rooms",
                    "sober_living_beds", "sober_living_residents", "sober_living_stays",
                ]:
                    cur.execute(
                        "SELECT column_name FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position",
                        (table,),
                    )
                    cols = [r["column_name"] for r in cur.fetchall()]
                    result["tables"][table] = cols
        except Exception as e:
            result["errors"].append(f"schema_inspect: {e}")

    return result


# ---------------------------------------------------------------------------
# Houses
# ---------------------------------------------------------------------------

@router.get("/houses")
def list_houses():
    return get_store().list_houses()


@router.post("/houses", status_code=201)
def create_house(body: HouseCreate):
    data = body.dict()
    log.info(f"[sober_living] create_house payload keys={list(data.keys())} house_name={data.get('house_name')!r}")
    try:
        result = get_store().create_house(data)
        log.info(f"[sober_living] create_house success house_id={result.get('house_id') if result else None}")
        return result
    except Exception as e:
        log.error(f"[sober_living] create_house FAILED: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


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


# ---------------------------------------------------------------------------
# Phase 3: Meetings
# ---------------------------------------------------------------------------

@router.get("/houses/{house_id}/meetings")
def list_meetings(house_id: str):
    return get_store().list_meetings(house_id)


@router.post("/meetings", status_code=201)
def create_meeting(body: MeetingCreate):
    return get_store().create_meeting(body.dict())


@router.put("/meetings/{meeting_id}")
def update_meeting(meeting_id: str, body: MeetingUpdate):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    result = get_store().update_meeting(meeting_id, updates)
    if not result:
        raise HTTPException(404, "Meeting not found")
    return result


# ---------------------------------------------------------------------------
# Phase 3: Chores
# ---------------------------------------------------------------------------

@router.get("/houses/{house_id}/chores")
def list_chores(house_id: str, due_date: str = None):
    return get_store().list_chores(house_id, due_date)


@router.post("/chores", status_code=201)
def create_chore(body: ChoreCreate):
    return get_store().create_chore(body.dict())


@router.put("/chores/{chore_id}")
def update_chore(chore_id: str, body: ChoreUpdate):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    result = get_store().update_chore(chore_id, updates)
    if not result:
        raise HTTPException(404, "Chore not found")
    return result


# ---------------------------------------------------------------------------
# Phase 3: Passes
# ---------------------------------------------------------------------------

@router.get("/houses/{house_id}/passes")
def list_passes(house_id: str):
    return get_store().list_passes(house_id)


@router.post("/passes", status_code=201)
def create_pass(body: PassCreate):
    return get_store().create_pass(body.dict())


@router.put("/passes/{pass_id}")
def update_pass(pass_id: str, body: PassUpdate):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    result = get_store().update_pass(pass_id, updates)
    if not result:
        raise HTTPException(404, "Pass not found")
    return result


# ---------------------------------------------------------------------------
# Phase 3: Curfew checks
# ---------------------------------------------------------------------------

@router.get("/houses/{house_id}/curfew")
def list_curfew(house_id: str, check_date: str):
    return get_store().list_curfew_checks(house_id, check_date)


@router.put("/houses/{house_id}/curfew")
def upsert_curfew(house_id: str, body: CurfewCheckUpsert):
    return get_store().upsert_curfew_check(
        house_id=house_id,
        check_date=__import__("datetime").datetime.utcnow().strftime("%Y-%m-%d"),
        resident_id=body.resident_id,
        stay_id=body.stay_id,
        status=body.status,
        checked_by=body.checked_by,
        method=body.method,
        notes=body.notes,
    )


# ---------------------------------------------------------------------------
# Phase 3: Dashboard
# ---------------------------------------------------------------------------

@router.get("/houses/{house_id}/dashboard")
def get_dashboard(house_id: str):
    return get_store().get_dashboard(house_id)
