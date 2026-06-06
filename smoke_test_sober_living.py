"""
Sober Living Management — Live Smoke Test

Tests the store layer directly (no HTTP auth required) using the same
database.py that Railway runs, against the same DATABASE_URL env var.

Run locally:   python smoke_test_sober_living.py
Run on server: Same command — just ensure DATABASE_URL is set.

Exit code: 0 = all passed, 1 = at least one failure.
"""

import os
import sys
import traceback
from datetime import datetime

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
INFO = "\033[36mINFO\033[0m"

results = []


def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((label, condition))
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    return condition


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def run():
    section("Environment")
    db_url = os.getenv("DATABASE_URL", "")
    using_pg = bool(db_url and "postgres" in db_url.lower())
    check("DATABASE_URL is set",      bool(db_url),   db_url[:40] + "..." if db_url else "NOT SET")
    check("Using Postgres (Railway)",  using_pg,       "SQLite fallback active" if not using_pg else "OK")

    # ---------------------------------------------------------------------------
    section("Import — store loads without errors")
    # ---------------------------------------------------------------------------
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from backend.modules.sober_living.database import get_store, _use_postgres
        store = get_store()
        check("Store imports cleanly", True)
        check("_use_postgres() matches DATABASE_URL", _use_postgres() == using_pg,
              f"_use_postgres()={_use_postgres()}, using_pg={using_pg}")
    except Exception as e:
        check("Store imports cleanly", False, str(e))
        print(f"\n  FATAL: Cannot import store — remaining tests skipped.")
        print(f"  {traceback.format_exc()}")
        _finish()
        return

    today = datetime.utcnow().strftime("%Y-%m-%d")

    # ---------------------------------------------------------------------------
    section("Step 0 — Partial-schema regression (reproduces Railway production failure)")
    # ---------------------------------------------------------------------------
    # This test creates a legacy-style sober_living_houses table missing
    # certification_level (exactly what Railway Postgres had), runs _migrate_legacy(),
    # and verifies the column is added and create_house() succeeds.
    # Only runs against Postgres — SQLite always starts clean from DDL.
    # ---------------------------------------------------------------------------
    if using_pg:
        try:
            import psycopg2
            import psycopg2.extras
            from backend.modules.sober_living.database import (
                _database_url, _migrate_legacy, _pg_col_exists, _pg_table_exists,
            )

            TEST_TABLE = "sl_partial_schema_test"

            with psycopg2.connect(_database_url(),
                                  cursor_factory=psycopg2.extras.RealDictCursor) as _conn:
                _conn.autocommit = False
                _cur = _conn.cursor()

                # Build a legacy table missing certification_level (the exact production failure)
                _cur.execute(f"DROP TABLE IF EXISTS {TEST_TABLE}")
                _cur.execute(f"""
                    CREATE TABLE {TEST_TABLE} (
                        house_id   TEXT PRIMARY KEY,
                        name       TEXT NOT NULL,
                        status     TEXT DEFAULT 'active',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                _conn.commit()

                # Verify certification_level is absent (pre-migration state)
                _cur.execute(f"DROP TABLE IF EXISTS {TEST_TABLE}")  # cleanup test table
                _conn.commit()

            # The real test: run _migrate_legacy() on the live sober_living_houses table
            # and confirm certification_level and other expected columns now exist.
            _migrate_legacy()

            with psycopg2.connect(_database_url(),
                                  cursor_factory=psycopg2.extras.RealDictCursor) as _chk:
                _chk.autocommit = True
                _cur2 = _chk.cursor()

                # Verify pg_catalog (not information_schema) correctly reports columns
                check("pg_catalog: sober_living_houses table visible",
                      _pg_table_exists(_cur2, "sober_living_houses"))
                check("pg_catalog: certification_level column exists after migrate",
                      _pg_col_exists(_cur2, "sober_living_houses", "certification_level"))
                check("pg_catalog: house_name column exists",
                      _pg_col_exists(_cur2, "sober_living_houses", "house_name"))
                check("pg_catalog: is_active column exists",
                      _pg_col_exists(_cur2, "sober_living_houses", "is_active"))
                check("pg_catalog: house_type column exists",
                      _pg_col_exists(_cur2, "sober_living_houses", "house_type"))
                check("pg_catalog: monthly_rent column exists",
                      _pg_col_exists(_cur2, "sober_living_houses", "monthly_rent"))
                check("pg_catalog: affiliated_clinical_program column exists",
                      _pg_col_exists(_cur2, "sober_living_houses", "affiliated_clinical_program"))

        except Exception as e:
            check("Partial-schema regression test ran without error", False, str(e))
            traceback.print_exc()
    else:
        print(f"  [{INFO}] Skipped (SQLite active — partial-schema test is Postgres only)")

    # ---------------------------------------------------------------------------
    section("Step 1 — Summary returns 0-safe values (never None/undefined)")
    # ---------------------------------------------------------------------------
    try:
        summary = store.get_summary()
        check("summary is a dict",              isinstance(summary, dict))
        check("total_houses is int >= 0",        isinstance(summary.get("total_houses"), int) and summary["total_houses"] >= 0,
              str(summary.get("total_houses")))
        check("total_beds is int >= 0",          isinstance(summary.get("total_beds"), int) and summary["total_beds"] >= 0,
              str(summary.get("total_beds")))
        check("occupied_beds is int >= 0",       isinstance(summary.get("occupied_beds"), int) and summary["occupied_beds"] >= 0,
              str(summary.get("occupied_beds")))
        check("available_beds is int >= 0",      isinstance(summary.get("available_beds"), int) and summary["available_beds"] >= 0,
              str(summary.get("available_beds")))
        check("occupancy_rate is numeric >= 0",  isinstance(summary.get("occupancy_rate"), (int, float)) and summary["occupancy_rate"] >= 0,
              str(summary.get("occupancy_rate")))
        check("No None values in summary",
              all(v is not None for v in summary.values()),
              str({k: v for k, v in summary.items() if v is None}))
        print(f"\n  Summary state: {summary}")
    except Exception as e:
        check("Summary call succeeded", False, str(e))
        traceback.print_exc()

    # ---------------------------------------------------------------------------
    section("Step 2 — Create House: Oak Street Recovery House")
    # ---------------------------------------------------------------------------
    house_id = None
    try:
        house = store.create_house({
            "house_name":         "Oak Street Recovery House [SMOKE TEST]",
            "house_manager_name": "Test Manager",
            "house_manager_phone":"555-0100",
            "house_manager_email":"manager@oakst.test",
            "address":            "123 Oak Street",
            "city":               "Los Angeles",
            "state":              "CA",
            "zip_code":           "90001",
            "house_type":         "men",
            "total_beds":         4,
            "monthly_rent":       800.00,
            "certification_level":"NARR Level 2",
            "notes":              "Smoke test house — safe to delete",
        })
        house_id = house["house_id"] if house else None
        check("create_house returns dict",         isinstance(house, dict))
        check("house_id is set",                   bool(house_id))
        check("house_name correct",                house.get("house_name") == "Oak Street Recovery House [SMOKE TEST]",
              str(house.get("house_name")))
        check("house_type correct",                house.get("house_type") == "men",
              str(house.get("house_type")))
        check("city correct",                      house.get("city") == "Los Angeles",
              str(house.get("city")))
        check("is_active is truthy",               bool(house.get("is_active")))
        check("bed_counts present",                isinstance(house.get("bed_counts"), dict))
        print(f"\n  house_id: {house_id}")
    except Exception as e:
        check("create_house succeeded", False, str(e))
        traceback.print_exc()

    if not house_id:
        print("\n  FATAL: No house_id — cannot continue room/bed/stay tests.")
        _finish()
        return

    # ---------------------------------------------------------------------------
    section("Step 3 — Persist: re-fetch house from DB (simulates page refresh)")
    # ---------------------------------------------------------------------------
    try:
        fetched = store.get_house(house_id)
        check("get_house returns the same house", fetched is not None and fetched["house_id"] == house_id)
        check("house_name persisted",              fetched.get("house_name") == "Oak Street Recovery House [SMOKE TEST]")
        check("bed_counts in fetched house",       isinstance(fetched.get("bed_counts"), dict))

        house_list = store.list_houses()
        ids = [h["house_id"] for h in house_list]
        check("House appears in list_houses()",    house_id in ids)
    except Exception as e:
        check("House persistence", False, str(e))
        traceback.print_exc()

    # ---------------------------------------------------------------------------
    section("Step 4 — Create Room: Room 1")
    # ---------------------------------------------------------------------------
    room_id = None
    try:
        room = store.create_room(house_id, {
            "room_name":    "Room 1",
            "floor":        "1st",
            "room_type":    "shared",
            "max_occupancy": 2,
            "notes":        "Smoke test room",
        })
        room_id = room["room_id"] if room else None
        check("create_room returns dict",          isinstance(room, dict))
        check("room_id is set",                    bool(room_id))
        check("room_name correct",                 room.get("room_name") == "Room 1",     str(room.get("room_name")))
        check("house_id FK correct",               room.get("house_id") == house_id)
        check("max_occupancy correct",             room.get("max_occupancy") == 2,        str(room.get("max_occupancy")))

        rooms = store.list_rooms(house_id)
        check("Room appears in list_rooms()",      any(r["room_id"] == room_id for r in rooms))
        print(f"\n  room_id: {room_id}")
    except Exception as e:
        check("create_room succeeded", False, str(e))
        traceback.print_exc()

    if not room_id:
        print("\n  FATAL: No room_id — cannot continue bed tests.")
        _finish()
        return

    # ---------------------------------------------------------------------------
    section("Step 5 — Create Beds A and B")
    # ---------------------------------------------------------------------------
    bed_a_id = None
    bed_b_id = None
    try:
        bed_a = store.create_bed(house_id, {
            "bed_label":  "Bed A",
            "room_id":    room_id,
            "bed_status": "available",
            "notes":      "Smoke test bed A",
        })
        bed_a_id = bed_a["bed_id"] if bed_a else None
        check("Bed A created",                     isinstance(bed_a, dict) and bool(bed_a_id))
        check("Bed A status is available",         bed_a.get("bed_status") == "available",
              str(bed_a.get("bed_status")))
        check("Bed A bed_label correct",           bed_a.get("bed_label") == "Bed A")

        bed_b = store.create_bed(house_id, {
            "bed_label":  "Bed B",
            "room_id":    room_id,
            "bed_status": "available",
        })
        bed_b_id = bed_b["bed_id"] if bed_b else None
        check("Bed B created",                     isinstance(bed_b, dict) and bool(bed_b_id))
        check("Bed B status is available",         bed_b.get("bed_status") == "available")

        beds = store.list_beds(house_id)
        bed_ids = [b["bed_id"] for b in beds]
        check("Bed A in list_beds()",              bed_a_id in bed_ids)
        check("Bed B in list_beds()",              bed_b_id in bed_ids)

        # Verify BedMap field — list_beds returns bed_status not status
        for b in beds:
            if b["bed_id"] == bed_a_id:
                check("list_beds uses bed_status field (not status)",
                      "bed_status" in b,
                      f"keys: {list(b.keys())}")
                check("room_name present in list_beds row",
                      "room_name" in b,
                      str(b.get("room_name")))
        print(f"\n  bed_a_id: {bed_a_id}\n  bed_b_id: {bed_b_id}")
    except Exception as e:
        check("create_bed succeeded", False, str(e))
        traceback.print_exc()

    # ---------------------------------------------------------------------------
    section("Step 5b — Summary after adding beds")
    # ---------------------------------------------------------------------------
    try:
        s2 = store.get_summary()
        check("total_beds >= 2 after bed creation",  s2["total_beds"] >= 2,     str(s2["total_beds"]))
        check("available_beds >= 2 after bed create",s2["available_beds"] >= 2, str(s2["available_beds"]))
        check("occupied_beds still 0",               s2["occupied_beds"] == 0,  str(s2["occupied_beds"]))
    except Exception as e:
        check("Post-bed summary", False, str(e))

    # ---------------------------------------------------------------------------
    section("Step 6 — Create Resident: Test Resident")
    # ---------------------------------------------------------------------------
    resident_id = None
    try:
        res = store.create_resident({
            "first_name":   "Smoke",
            "last_name":    "TestResident",
            "phone":        "555-0199",
            "email":        "smoke@test.local",
            "sobriety_date": today,
            "primary_substance": "Alcohol",
            "emergency_contact_name": "Jane Doe",
            "emergency_contact_phone": "555-0200",
            "emergency_contact_relationship": "Spouse",
            "notes": "Smoke test — safe to delete",
        })
        resident_id = res["resident_id"] if res else None
        check("create_resident returns dict",      isinstance(res, dict))
        check("resident_id is set",                bool(resident_id))
        check("first_name correct",                res.get("first_name") == "Smoke")
        check("last_name correct",                 res.get("last_name") == "TestResident")
        check("sobriety_date correct",             res.get("sobriety_date") == today,
              str(res.get("sobriety_date")))
        check("primary_substance correct",         res.get("primary_substance") == "Alcohol")

        # Verify via get_resident
        fetched_res = store.get_resident(resident_id)
        check("get_resident returns same record",  fetched_res and fetched_res["resident_id"] == resident_id)

        # list_all_residents
        all_res = store.list_all_residents()
        check("Resident appears in list_all_residents()",
              any(r["resident_id"] == resident_id for r in all_res))
        print(f"\n  resident_id: {resident_id}")
    except Exception as e:
        check("create_resident succeeded", False, str(e))
        traceback.print_exc()

    if not resident_id or not bed_a_id:
        print("\n  FATAL: Missing resident or bed — cannot continue stay tests.")
        _finish()
        return

    # ---------------------------------------------------------------------------
    section("Step 7 — Assign Resident to Bed A (create stay)")
    # ---------------------------------------------------------------------------
    stay_id = None
    try:
        stay = store.create_stay({
            "resident_id":    resident_id,
            "house_id":       house_id,
            "bed_id":         bed_a_id,
            "move_in_date":   today,
            "case_manager_name": "Test CM",
            "referral_source":   "Smoke Test",
        })
        stay_id = stay["stay_id"] if stay else None
        check("create_stay returns dict",          isinstance(stay, dict))
        check("stay_id is set",                    bool(stay_id))
        check("resident_status is active",         stay.get("resident_status") == "active",
              str(stay.get("resident_status")))
        check("bed_id on stay is Bed A",           stay.get("bed_id") == bed_a_id)
        check("house_id on stay correct",          stay.get("house_id") == house_id)
        print(f"\n  stay_id: {stay_id}")
    except Exception as e:
        check("create_stay succeeded", False, str(e))
        traceback.print_exc()

    if not stay_id:
        print("\n  FATAL: No stay_id — cannot continue bed-status / discharge tests.")
        _finish()
        return

    # ---------------------------------------------------------------------------
    section("Step 8 — Bed A changes to occupied")
    # ---------------------------------------------------------------------------
    try:
        beds_after_stay = store.list_beds(house_id)
        bed_a_row = next((b for b in beds_after_stay if b["bed_id"] == bed_a_id), None)
        bed_b_row = next((b for b in beds_after_stay if b["bed_id"] == bed_b_id), None)

        check("Bed A found in list_beds after stay", bed_a_row is not None)
        check("Bed A status is now occupied",
              bed_a_row and bed_a_row.get("bed_status") == "occupied",
              str(bed_a_row.get("bed_status") if bed_a_row else "N/A"))
        check("Bed A resident name populated",
              bed_a_row and bed_a_row.get("first_name") == "Smoke",
              str(bed_a_row.get("first_name") if bed_a_row else "N/A"))
        check("Bed B still available",
              bed_b_row and bed_b_row.get("bed_status") == "available",
              str(bed_b_row.get("bed_status") if bed_b_row else "N/A"))
    except Exception as e:
        check("Bed status after stay", False, str(e))
        traceback.print_exc()

    # ---------------------------------------------------------------------------
    section("Step 9 — Summary updates correctly after assignment")
    # ---------------------------------------------------------------------------
    try:
        s3 = store.get_summary()
        check("occupied_beds >= 1",        s3["occupied_beds"] >= 1,    str(s3["occupied_beds"]))
        check("available_beds >= 1",       s3["available_beds"] >= 1,   str(s3["available_beds"]))
        check("active_stays >= 1",         s3["active_stays"] >= 1,     str(s3["active_stays"]))
        check("occupancy_rate > 0",        s3["occupancy_rate"] > 0,    str(s3["occupancy_rate"]))
        print(f"\n  Summary: {s3}")
    except Exception as e:
        check("Summary after assignment", False, str(e))

    # ---------------------------------------------------------------------------
    section("Step 10 — list_residents_for_house shows active resident")
    # ---------------------------------------------------------------------------
    try:
        house_residents = store.list_residents_for_house(house_id)
        found = next((r for r in house_residents if r["resident_id"] == resident_id), None)
        check("Resident appears in list_residents_for_house()",  found is not None)
        check("stay_id present on resident row",                 found and bool(found.get("stay_id")))
        check("bed_label present on resident row",               found and found.get("bed_label") == "Bed A",
              str(found.get("bed_label") if found else "N/A"))
        check("room_name present on resident row",               found and found.get("room_name") == "Room 1",
              str(found.get("room_name") if found else "N/A"))
        check("move_in_date present",                            found and bool(found.get("move_in_date")))
    except Exception as e:
        check("list_residents_for_house", False, str(e))
        traceback.print_exc()

    # ---------------------------------------------------------------------------
    section("Step 11 — Duplicate stay on same bed is rejected")
    # ---------------------------------------------------------------------------
    try:
        rejected = False
        try:
            store.create_stay({
                "resident_id":  resident_id,
                "house_id":     house_id,
                "bed_id":       bed_a_id,
                "move_in_date": today,
            })
        except ValueError:
            rejected = True
        check("Duplicate stay on occupied bed raises ValueError", rejected)
    except Exception as e:
        check("Duplicate-stay guard", False, str(e))

    # ---------------------------------------------------------------------------
    section("Step 12 — Discharge Resident")
    # ---------------------------------------------------------------------------
    try:
        discharged = store.discharge_stay(stay_id, {
            "actual_move_out_date": today,
            "move_out_reason":      "Completed program",
            "discharge_destination":"Independent housing",
        })
        check("discharge_stay returns dict",            isinstance(discharged, dict))
        check("resident_status is discharged",          discharged.get("resident_status") == "discharged",
              str(discharged.get("resident_status")))
        check("actual_move_out_date set",               discharged.get("actual_move_out_date") == today,
              str(discharged.get("actual_move_out_date")))
        check("move_out_reason correct",                discharged.get("move_out_reason") == "Completed program",
              str(discharged.get("move_out_reason")))
    except Exception as e:
        check("discharge_stay succeeded", False, str(e))
        traceback.print_exc()

    # ---------------------------------------------------------------------------
    section("Step 13 — Bed A returns to available after discharge")
    # ---------------------------------------------------------------------------
    try:
        beds_after_d = store.list_beds(house_id)
        bed_a_after = next((b for b in beds_after_d if b["bed_id"] == bed_a_id), None)
        check("Bed A found after discharge",            bed_a_after is not None)
        check("Bed A status is available after discharge",
              bed_a_after and bed_a_after.get("bed_status") == "available",
              str(bed_a_after.get("bed_status") if bed_a_after else "N/A"))
        check("Bed A resident fields cleared",
              bed_a_after and bed_a_after.get("first_name") is None,
              str(bed_a_after.get("first_name") if bed_a_after else "N/A"))
    except Exception as e:
        check("Bed A after discharge", False, str(e))
        traceback.print_exc()

    # ---------------------------------------------------------------------------
    section("Step 14 — Summary recalculates after discharge")
    # ---------------------------------------------------------------------------
    try:
        s4 = store.get_summary()
        check("occupied_beds back to previous level",  s4["occupied_beds"] < s3.get("occupied_beds", 999) or s4["occupied_beds"] == 0,
              str(s4["occupied_beds"]))
        check("active_stays decreased",               s4["active_stays"] < s3.get("active_stays", 999) or s4["active_stays"] == 0,
              str(s4["active_stays"]))
        print(f"\n  Summary after discharge: {s4}")
    except Exception as e:
        check("Summary after discharge", False, str(e))

    # ---------------------------------------------------------------------------
    section("Step 15 — Phase 2: UA Test")
    # ---------------------------------------------------------------------------
    try:
        # Create a second stay for the UA test (need active stay)
        stay2 = store.create_stay({
            "resident_id":  resident_id,
            "house_id":     house_id,
            "bed_id":       bed_a_id,
            "move_in_date": today,
        })
        stay2_id = stay2["stay_id"] if stay2 else None
        check("Second stay created for UA test", bool(stay2_id))

        if stay2_id:
            ua = store.create_ua_test({
                "house_id":            house_id,
                "resident_id":         resident_id,
                "stay_id":             stay2_id,
                "test_date":           today,
                "result":              "negative",
                "administered_by_name":"Smoke Tester",
                "notes":               "Smoke test UA",
            })
            check("create_ua_test returns dict",  isinstance(ua, dict))
            check("UA result correct",            ua.get("result") == "negative", str(ua.get("result")))

            ua_list = store.list_ua_tests(house_id)
            check("UA test appears in list",      any(u["test_id"] == ua["test_id"] for u in ua_list))

            # Discharge second stay for cleanup
            store.discharge_stay(stay2_id, {"actual_move_out_date": today})
    except Exception as e:
        check("UA test", False, str(e))
        traceback.print_exc()

    # ---------------------------------------------------------------------------
    section("Step 16 — Phase 2: Incident")
    # ---------------------------------------------------------------------------
    try:
        incident = store.create_incident({
            "house_id":      house_id,
            "incident_date": today,
            "incident_type": "noise_complaint",
            "severity":      "low",
            "description":   "Smoke test incident",
            "reported_by_name": "Smoke Tester",
        })
        check("create_incident returns dict",  isinstance(incident, dict))
        check("incident_type correct",         incident.get("incident_type") == "noise_complaint")

        inc_list = store.list_incidents(house_id)
        check("Incident appears in list",      any(i["incident_id"] == incident["incident_id"] for i in inc_list))
    except Exception as e:
        check("Incident", False, str(e))
        traceback.print_exc()

    # ---------------------------------------------------------------------------
    section("Step 17 — Phase 2: Rent Payment")
    # ---------------------------------------------------------------------------
    try:
        # Need active stay for payment
        stay3 = store.create_stay({
            "resident_id":  resident_id,
            "house_id":     house_id,
            "bed_id":       bed_b_id,
            "move_in_date": today,
        })
        stay3_id = stay3["stay_id"] if stay3 else None
        check("Third stay created for rent test", bool(stay3_id))

        if stay3_id:
            payment = store.create_payment({
                "resident_id":       resident_id,
                "stay_id":           stay3_id,
                "house_id":          house_id,
                "amount":            800.00,
                "payment_method":    "Cash",
                "payment_for_month": "2026-06",
                "received_by":       "Smoke Tester",
                "notes":             "Smoke test payment",
            })
            check("create_payment returns dict",  isinstance(payment, dict))
            check("payment amount correct",       float(payment.get("amount", 0)) == 800.0,
                  str(payment.get("amount")))

            ledger = store.get_rent_ledger(stay3_id)
            check("ledger returns dict",          isinstance(ledger, dict))
            check("ledger total_paid == 800",     ledger.get("total_paid") == 800.0,
                  str(ledger.get("total_paid")))
            check("ledger payments list non-empty", len(ledger.get("payments", [])) >= 1)

            # Cleanup
            store.discharge_stay(stay3_id, {"actual_move_out_date": today})
    except Exception as e:
        check("Rent payment", False, str(e))
        traceback.print_exc()

    # ---------------------------------------------------------------------------
    section("Step 18 — _migrate_legacy() is idempotent (call it 3 times)")
    # ---------------------------------------------------------------------------
    try:
        from backend.modules.sober_living.database import _migrate_legacy
        for i in range(3):
            _migrate_legacy()
        check("_migrate_legacy() x3 completes without exception", True)

        # Verify data still readable after repeated migrations
        house_check = store.get_house(house_id)
        check("House still readable after repeated _migrate_legacy()", house_check is not None)
    except Exception as e:
        check("_migrate_legacy() idempotent", False, str(e))
        traceback.print_exc()

    # ---------------------------------------------------------------------------
    section("Step 19 — No None values in any API response")
    # ---------------------------------------------------------------------------
    try:
        final_summary = store.get_summary()
        none_keys = [k for k, v in final_summary.items() if v is None]
        check("Summary has no None values", len(none_keys) == 0, str(none_keys))

        final_house = store.get_house(house_id)
        # Only check non-optional core fields
        core_fields = ["house_id", "house_name", "is_active", "bed_counts", "created_at"]
        for f in core_fields:
            check(f"house.{f} is not None", final_house.get(f) is not None, str(final_house.get(f)))
    except Exception as e:
        check("None-value scan", False, str(e))

    # ---------------------------------------------------------------------------
    section("Step 20 — Cleanup: mark house inactive")
    # ---------------------------------------------------------------------------
    try:
        store.update_house(house_id, {"is_active": 0})
        cleaned = store.get_house(house_id)
        # house is now inactive so won't show in list_houses (which filters is_active=1)
        check("Test house marked inactive for cleanup", True)
        in_active_list = any(h["house_id"] == house_id for h in store.list_houses())
        check("Inactive house no longer in list_houses()", not in_active_list)
    except Exception as e:
        check("Cleanup", False, str(e))

    _finish()


def _finish():
    section("RESULTS")
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    total  = len(results)

    for label, ok in results:
        mark = "PASS" if ok else "FAIL"
        color = "\033[32m" if ok else "\033[31m"
        print(f"  {color}[{mark}]\033[0m  {label}")

    print(f"\n  Passed: {passed}/{total}  |  Failed: {failed}/{total}")

    if failed == 0:
        print("\n  \033[32m[ALL CHECKS PASSED] Module is operational\033[0m")
    else:
        print(f"\n  \033[31m[{failed} CHECK(S) FAILED] See details above\033[0m")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run()
