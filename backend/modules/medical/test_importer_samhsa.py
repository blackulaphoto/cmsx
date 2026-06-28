"""
Tests for backend/modules/medical/importer_samhsa.py

Run with:
    python -m pytest backend/modules/medical/test_importer_samhsa.py -v
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from backend.modules.medical.importer_samhsa import (
    SOURCE_NAME,
    SAMHSA_DETAILS_URL_TEMPLATE,
    _build_services_list,
    _derive_population,
    _derive_type,
    _is_qualifying_record,
    _normalize_name,
    _services_by_code,
    dedupe_filter,
    ensure_optional_columns,
    load_fixture,
    normalize_record,
    run_fixture_mode,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "samhsa_sample.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_raw(
    frid: str = "abc123",
    name1: str = "Test Facility",
    name2: str = "",
    city: str = "Los Angeles",
    zip_code: str = "90012",
    phone: str = "213-555-0000",
    intake1: str = "",
    website: str = "https://example.org",
    latitude: str = "34.0522",
    longitude: str = "-118.2437",
    set_f3: str = "Residential; Short-term residential (30 days or less)",
    pay_f3: str = "Medicaid; Medicare; Private health insurance",
    sn_f3: str = "Female; Male",
    sg_f3: str = "",
    lca_f3: str = "",
    tc_f3: str = "Substance use treatment",
    extra_services: list | None = None,
) -> dict:
    services = [
        {"f1": "Type of Care", "f2": "TC", "f3": tc_f3},
        {"f1": "Service Setting", "f2": "SET", "f3": set_f3},
        {"f1": "Payment/Insurance/Funding Accepted", "f2": "PAY", "f3": pay_f3},
        {"f1": "Gender Accepted", "f2": "SN", "f3": sn_f3},
    ]
    if sg_f3:
        services.append({"f1": "Special Programs", "f2": "SG", "f3": sg_f3})
    if lca_f3:
        services.append({"f1": "Accreditation", "f2": "LCA", "f3": lca_f3})
    if extra_services:
        services.extend(extra_services)
    return {
        "frid": frid,
        "name1": name1,
        "name2": name2,
        "street1": "100 Test Street",
        "street2": "",
        "city": city,
        "state": "CA",
        "zip": zip_code,
        "phone": phone,
        "intake1": intake1,
        "hotline1": None,
        "website": website,
        "latitude": latitude,
        "longitude": longitude,
        "miles": "1.0",
        "typeFacility": "SA",
        "services": services,
    }


def _make_sqlite_db(schema_sql: str) -> sqlite3.Connection:
    """Return an in-memory SQLite connection with the given schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(schema_sql)
    return conn


_TREATMENT_CENTERS_SCHEMA = """
CREATE TABLE treatment_centers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    type TEXT,
    address TEXT,
    city TEXT,
    zipCode TEXT,
    phone TEXT,
    website TEXT,
    description TEXT,
    servesPopulation TEXT,
    acceptsMediCal INTEGER DEFAULT 0,
    acceptsMedicare INTEGER DEFAULT 0,
    acceptsPrivateInsurance INTEGER DEFAULT 0,
    acceptsRBH INTEGER DEFAULT 0,
    acceptsCouples INTEGER DEFAULT 0,
    servicesOffered TEXT,
    priceRange TEXT,
    latitude REAL,
    longitude REAL,
    isJointCommission INTEGER DEFAULT 0,
    isVerified INTEGER DEFAULT 1,
    isPublished INTEGER DEFAULT 1
);
"""

_TREATMENT_CENTERS_SCHEMA_WITH_OPTIONAL = """
CREATE TABLE treatment_centers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    type TEXT,
    address TEXT,
    city TEXT,
    zipCode TEXT,
    phone TEXT,
    website TEXT,
    description TEXT,
    servesPopulation TEXT,
    acceptsMediCal INTEGER DEFAULT 0,
    acceptsMedicare INTEGER DEFAULT 0,
    acceptsPrivateInsurance INTEGER DEFAULT 0,
    acceptsRBH INTEGER DEFAULT 0,
    acceptsCouples INTEGER DEFAULT 0,
    servicesOffered TEXT,
    priceRange TEXT,
    latitude REAL,
    longitude REAL,
    isJointCommission INTEGER DEFAULT 0,
    isVerified INTEGER DEFAULT 1,
    isPublished INTEGER DEFAULT 1,
    source_name TEXT,
    source_url TEXT,
    image_url TEXT
);
"""

# ---------------------------------------------------------------------------
# 1. Normalize residential record
# ---------------------------------------------------------------------------

def test_normalize_residential_type():
    raw = _make_raw(set_f3="Residential; Short-term residential (30 days or less)")
    result = normalize_record(raw)
    assert result is not None
    assert result["type"] == "residential"


def test_normalize_residential_sets_isPublished():
    raw = _make_raw(set_f3="Residential")
    result = normalize_record(raw)
    assert result is not None
    assert result["isPublished"] == 1
    assert result["isVerified"] == 1


def test_normalize_residential_name_and_address():
    raw = _make_raw(name1="Sunrise House", set_f3="Residential")
    result = normalize_record(raw)
    assert result is not None
    assert result["name"] == "Sunrise House"
    assert "100 Test Street" in result["address"]
    assert result["city"] == "Los Angeles"
    assert result["zipCode"] == "90012"


# ---------------------------------------------------------------------------
# 2. Normalize intensive outpatient record
# ---------------------------------------------------------------------------

def test_normalize_intensive_outpatient_type():
    raw = _make_raw(set_f3="Intensive outpatient treatment")
    result = normalize_record(raw)
    assert result is not None
    assert result["type"] == "outpatient"


def test_normalize_partial_hospitalization_type():
    raw = _make_raw(set_f3="Partial hospitalization/day treatment")
    result = normalize_record(raw)
    assert result is not None
    assert result["type"] == "outpatient"


# ---------------------------------------------------------------------------
# 3. Normalize detox record
# ---------------------------------------------------------------------------

def test_normalize_detox_type_from_outpatient_detox():
    raw = _make_raw(set_f3="Outpatient detoxification; Regular outpatient treatment")
    result = normalize_record(raw)
    assert result is not None
    assert result["type"] == "detox"


def test_normalize_detox_type_from_residential_detox():
    raw = _make_raw(set_f3="Residential detoxification")
    result = normalize_record(raw)
    assert result is not None
    assert result["type"] == "detox"


def test_normalize_detox_priority_over_outpatient():
    """Detox priority (10) must beat regular outpatient (2)."""
    raw = _make_raw(
        set_f3="Regular outpatient treatment; Outpatient detoxification"
    )
    result = normalize_record(raw)
    assert result is not None
    assert result["type"] == "detox"


# ---------------------------------------------------------------------------
# 4. Filter — regular outpatient only records are excluded
# ---------------------------------------------------------------------------

def test_filter_out_regular_outpatient_only():
    raw = _make_raw(set_f3="Regular outpatient treatment")
    result = normalize_record(raw)
    assert result is None


def test_filter_out_brief_intervention_only():
    raw = _make_raw(set_f3="Brief intervention")
    result = normalize_record(raw)
    assert result is None


def test_filter_out_combined_regular_and_brief():
    raw = _make_raw(set_f3="Regular outpatient treatment; Brief intervention")
    result = normalize_record(raw)
    assert result is None


def test_qualifying_when_combined_regular_and_intensive():
    """Record that combines regular + intensive outpatient should be included."""
    raw = _make_raw(
        set_f3="Regular outpatient treatment; Intensive outpatient treatment"
    )
    result = normalize_record(raw)
    assert result is not None
    assert result["type"] == "outpatient"


# ---------------------------------------------------------------------------
# 5. Payment flag mapping
# ---------------------------------------------------------------------------

def test_payment_medi_cal_flag():
    raw = _make_raw(pay_f3="Medicaid; State substance abuse agency")
    result = normalize_record(raw)
    assert result is not None
    assert result["acceptsMediCal"] == 1
    assert result["acceptsMedicare"] == 0
    assert result["acceptsPrivateInsurance"] == 0


def test_payment_medicare_flag():
    raw = _make_raw(pay_f3="Medicare; Private health insurance")
    result = normalize_record(raw)
    assert result is not None
    assert result["acceptsMedicare"] == 1
    assert result["acceptsPrivateInsurance"] == 1
    assert result["acceptsMediCal"] == 0


def test_payment_all_three_flags():
    raw = _make_raw(pay_f3="Medicaid; Medicare; Private health insurance")
    result = normalize_record(raw)
    assert result is not None
    assert result["acceptsMediCal"] == 1
    assert result["acceptsMedicare"] == 1
    assert result["acceptsPrivateInsurance"] == 1


def test_payment_no_flags():
    raw = _make_raw(pay_f3="State substance abuse agency; Federal")
    result = normalize_record(raw)
    assert result is not None
    assert result["acceptsMediCal"] == 0
    assert result["acceptsMedicare"] == 0
    assert result["acceptsPrivateInsurance"] == 0


# ---------------------------------------------------------------------------
# 6. Services list construction
# ---------------------------------------------------------------------------

def test_services_list_includes_tc_items():
    raw = _make_raw(
        set_f3="Residential",
        tc_f3="Substance use treatment; Detoxification; Buprenorphine treatment",
    )
    result = normalize_record(raw)
    assert result is not None
    services = json.loads(result["servicesOffered"])
    assert "Substance use treatment" in services
    assert "Detoxification" in services


def test_services_list_includes_mat_tag():
    raw = _make_raw(
        set_f3="Residential",
        extra_services=[{"f1": "Opioid Meds", "f2": "OM", "f3": "Methadone; Buprenorphine"}],
    )
    result = normalize_record(raw)
    assert result is not None
    services = json.loads(result["servicesOffered"])
    assert "Opioid treatment / MAT" in services


def test_services_list_includes_rss_tag():
    raw = _make_raw(
        set_f3="Long-term residential (more than 30 days)",
        extra_services=[{"f1": "Recovery Support", "f2": "RSS", "f3": "Case management; Housing"}],
    )
    result = normalize_record(raw)
    assert result is not None
    services = json.loads(result["servicesOffered"])
    assert "Recovery support services" in services


def test_services_list_capped_at_15():
    extra = [
        {"f1": f"X{i}", "f2": f"X{i}", "f3": f"Service item {i}"}
        for i in range(20)
    ]
    raw = _make_raw(set_f3="Residential", extra_services=extra)
    result = normalize_record(raw)
    assert result is not None
    services = json.loads(result["servicesOffered"])
    assert len(services) <= 15


# ---------------------------------------------------------------------------
# 7. Dedupe by source_url / frid
# ---------------------------------------------------------------------------

def test_dedupe_skips_existing_source_url():
    frid = "abc123"
    url = SAMHSA_DETAILS_URL_TEMPLATE.format(frid=frid)
    raw = _make_raw(frid=frid, set_f3="Residential")
    norm = normalize_record(raw)
    assert norm is not None

    unique, skipped = dedupe_filter([norm], existing_urls={url}, existing_name_city=set())
    assert len(unique) == 0
    assert skipped == 1


def test_dedupe_passes_new_source_url():
    frid = "newrecord999"
    raw = _make_raw(frid=frid, set_f3="Residential")
    norm = normalize_record(raw)
    assert norm is not None

    unique, skipped = dedupe_filter([norm], existing_urls=set(), existing_name_city=set())
    assert len(unique) == 1
    assert skipped == 0


def test_dedupe_deduplicates_within_batch():
    frid = "same_frid_001"
    raw = _make_raw(frid=frid, name1="Duplicate Facility", set_f3="Residential")
    norm1 = normalize_record(raw)
    norm2 = normalize_record(raw)
    assert norm1 is not None and norm2 is not None

    unique, skipped = dedupe_filter([norm1, norm2], existing_urls=set(), existing_name_city=set())
    assert len(unique) == 1
    assert skipped == 1


# ---------------------------------------------------------------------------
# 8. Fallback dedupe by normalized name + city
# ---------------------------------------------------------------------------

def test_dedupe_fallback_name_city_match():
    raw = _make_raw(
        frid="",       # no frid → no source_url
        name1="Muse Treatment",
        city="Los Angeles",
        set_f3="Residential",
    )
    norm = normalize_record(raw)
    assert norm is not None
    norm["source_url"] = ""  # blank source_url — simulates hand-entered row

    existing_name_city = {(_normalize_name("Muse Treatment"), "los angeles")}
    unique, skipped = dedupe_filter([norm], existing_urls=set(), existing_name_city=existing_name_city)
    assert len(unique) == 0
    assert skipped == 1


def test_dedupe_fallback_passes_different_city():
    raw = _make_raw(
        frid="",
        name1="Hope House",
        city="Long Beach",
        set_f3="Residential",
    )
    norm = normalize_record(raw)
    assert norm is not None
    norm["source_url"] = ""

    # Same name but different city — should NOT be treated as a duplicate
    existing_name_city = {(_normalize_name("Hope House"), "los angeles")}
    unique, skipped = dedupe_filter([norm], existing_urls=set(), existing_name_city=existing_name_city)
    assert len(unique) == 1
    assert skipped == 0


# ---------------------------------------------------------------------------
# 9. Optional column creation
# ---------------------------------------------------------------------------

def test_ensure_optional_columns_adds_missing_columns():
    conn = _make_sqlite_db(_TREATMENT_CENTERS_SCHEMA)
    ensure_optional_columns(conn)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(treatment_centers)").fetchall()}
    assert "source_name" in cols
    assert "source_url" in cols
    assert "image_url" in cols
    conn.close()


def test_ensure_optional_columns_idempotent():
    """Running ensure_optional_columns twice must not raise."""
    conn = _make_sqlite_db(_TREATMENT_CENTERS_SCHEMA_WITH_OPTIONAL)
    ensure_optional_columns(conn)  # columns already exist — must not error
    ensure_optional_columns(conn)
    conn.close()


def test_ensure_optional_columns_does_not_alter_other_columns():
    conn = _make_sqlite_db(_TREATMENT_CENTERS_SCHEMA)
    pre_cols = {row[1] for row in conn.execute("PRAGMA table_info(treatment_centers)").fetchall()}
    ensure_optional_columns(conn)
    post_cols = {row[1] for row in conn.execute("PRAGMA table_info(treatment_centers)").fetchall()}
    # Original columns are all still present
    assert pre_cols.issubset(post_cols)
    conn.close()


# ---------------------------------------------------------------------------
# 10. Fixture mode (offline)
# ---------------------------------------------------------------------------

def test_fixture_mode_returns_qualifying_rows():
    results = run_fixture_mode(FIXTURE_PATH)
    # Fixture has 5 rows: 4 qualifying + 1 regular-outpatient-only (should be excluded)
    assert len(results) == 4


def test_fixture_mode_excludes_regular_outpatient_only():
    results = run_fixture_mode(FIXTURE_PATH)
    # Community Counseling Clinic (fixture record 4) is regular outpatient only — excluded
    names = [r["name"] for r in results]
    assert "Community Counseling Clinic" not in names
    assert not any("Community Counseling" in n for n in names)


def test_fixture_mode_includes_residential():
    results = run_fixture_mode(FIXTURE_PATH)
    residential = [r for r in results if r["type"] == "residential"]
    assert len(residential) >= 2


def test_fixture_mode_includes_detox():
    results = run_fixture_mode(FIXTURE_PATH)
    detox = [r for r in results if r["type"] == "detox"]
    assert len(detox) >= 1


def test_fixture_mode_source_metadata():
    results = run_fixture_mode(FIXTURE_PATH)
    for row in results:
        assert row["source_name"] == SOURCE_NAME
        # source_url should contain frid or be empty
        assert "findtreatment.gov" in row["source_url"] or row["source_url"] == ""


def test_fixture_mode_population_women_record():
    """Westside Women's Recovery House has SN=Female only → should map to 'women'."""
    results = run_fixture_mode(FIXTURE_PATH)
    women_rows = [r for r in results if r["servesPopulation"] == "women"]
    assert len(women_rows) >= 1


def test_fixture_mode_medi_cal_flag():
    """Sunrise Recovery Center has Medicaid in PAY → acceptsMediCal=1."""
    results = run_fixture_mode(FIXTURE_PATH)
    medi_cal_rows = [r for r in results if r["acceptsMediCal"] == 1]
    assert len(medi_cal_rows) >= 1


def test_fixture_mode_joint_commission_flag():
    """Sunrise Recovery Center has The Joint Commission in LCA → isJointCommission=1."""
    results = run_fixture_mode(FIXTURE_PATH)
    jc_rows = [r for r in results if r["isJointCommission"] == 1]
    assert len(jc_rows) >= 1


def test_load_fixture_accepts_bare_list():
    """load_fixture should accept a bare list of rows, not just the API envelope."""
    fixture_data = load_fixture(FIXTURE_PATH)
    # Re-run with bare list (simulated)
    import tempfile, json as _json
    rows = fixture_data
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        _json.dump(rows, f)
        tmp_path = Path(f.name)
    loaded = load_fixture(tmp_path)
    assert isinstance(loaded, list)
    assert len(loaded) == len(fixture_data)
    tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 11. Route backward-compatibility: query works without optional columns
# ---------------------------------------------------------------------------

def test_route_query_without_optional_columns():
    """
    The SELECT in _query_treatment_centers uses PRAGMA introspection to include
    optional columns only when they exist. When absent, query must not raise.
    This test simulates a DB without optional columns and verifies the PRAGMA
    introspection path produces a valid column list.
    """
    conn = _make_sqlite_db(_TREATMENT_CENTERS_SCHEMA)
    # Introspect columns — mirror the logic in routes.py
    tc_cols = {row[1] for row in conn.execute("PRAGMA table_info(treatment_centers)").fetchall()}
    opt_cols = [c for c in ("source_name", "source_url", "image_url") if c in tc_cols]
    # Without the optional columns, opt_cols should be empty
    assert opt_cols == []
    # The base SELECT must work fine
    rows = conn.execute(
        "SELECT id, name, type, address, city, zipCode, phone, website, description,"
        " servesPopulation, acceptsMediCal, acceptsPrivateInsurance, servicesOffered, priceRange"
        " FROM treatment_centers WHERE isPublished = 1"
        " AND LOWER(COALESCE(type,'')) != 'sober_living'"
    ).fetchall()
    assert rows == []
    conn.close()


# ---------------------------------------------------------------------------
# 12. Route includes source metadata when optional columns exist
# ---------------------------------------------------------------------------

def test_route_query_with_optional_columns():
    """
    When optional columns exist and a row has source_name/source_url, those
    values should be retrievable via the dynamic SELECT (PRAGMA-driven).
    """
    conn = _make_sqlite_db(_TREATMENT_CENTERS_SCHEMA_WITH_OPTIONAL)
    conn.execute(
        "INSERT INTO treatment_centers "
        "(name, type, isPublished, source_name, source_url) "
        "VALUES (?, ?, ?, ?, ?)",
        ["Test Center", "residential", 1, "SAMHSA FindTreatment.gov",
         "https://findtreatment.gov/locator/details?frid=abc123"],
    )
    conn.commit()

    tc_cols = {row[1] for row in conn.execute("PRAGMA table_info(treatment_centers)").fetchall()}
    opt_cols = [c for c in ("source_name", "source_url", "image_url") if c in tc_cols]
    assert set(opt_cols) == {"source_name", "source_url", "image_url"}

    opt_select = ", " + ", ".join(opt_cols)
    rows = conn.execute(
        f"SELECT id, name, type, address, city, zipCode, phone, website, description,"
        f" servesPopulation, acceptsMediCal, acceptsPrivateInsurance, servicesOffered, priceRange"
        f"{opt_select}"
        f" FROM treatment_centers WHERE isPublished = 1"
        f" AND LOWER(COALESCE(type,'')) != 'sober_living'"
    ).fetchall()
    conn.close()

    assert len(rows) == 1
    row = rows[0]
    assert row["source_name"] == "SAMHSA FindTreatment.gov"
    assert "frid=abc123" in row["source_url"]
