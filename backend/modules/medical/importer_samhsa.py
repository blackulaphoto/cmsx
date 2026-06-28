#!/usr/bin/env python3
"""
SAMHSA FindTreatment.gov importer for CMSX treatment_centers table.

Source:
    POST https://findtreatment.gov/locator/listing
    robots.txt: User-agent: *  Disallow:  (all paths allowed — federal public domain)
    No authentication required.

Usage:
    python -m backend.modules.medical.importer_samhsa               # dry-run (default)
    python -m backend.modules.medical.importer_samhsa --dry-run
    python -m backend.modules.medical.importer_samhsa --dry-run --sample-size 20
    python -m backend.modules.medical.importer_samhsa --fixture backend/modules/medical/fixtures/samhsa_sample.json
    python -m backend.modules.medical.importer_samhsa --import-mode
    python -m backend.modules.medical.importer_samhsa --import-mode --max-rows 200 --confirm-large-import
    python -m backend.modules.medical.importer_samhsa --import-mode --include-court-programs
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAMHSA_API_URL = "https://findtreatment.gov/locator/listing"
SAMHSA_DETAILS_URL_TEMPLATE = "https://findtreatment.gov/locator/details?frid={frid}"
SOURCE_NAME = "SAMHSA FindTreatment.gov"

from backend.shared.db_path import (
    resolve_virgil_db_path as _resolve_virgil_db,
    is_durable_db_configured as _is_durable_configured,
    _durable_virgil_db_path,
)
VIRGIL_DB_PATH: Path = _resolve_virgil_db()

OPTIONAL_COLUMNS: dict[str, str] = {
    "source_name": "TEXT",
    "source_url": "TEXT",
    "image_url": "TEXT",
}

# Default parameters — conservative caps for safety
DEFAULT_PAGE_SIZE = 25
DEFAULT_MAX_PAGES = 2
DEFAULT_MAX_ROWS = 50
DEFAULT_SADDR = "34.0522,-118.2437"   # downtown LA
DEFAULT_DISTANCE = 25                  # miles
DEFAULT_SAMPLE_SIZE = 10

# ---------------------------------------------------------------------------
# Encoding cleanup
# ---------------------------------------------------------------------------

# U+FFFD (REPLACEMENT CHARACTER) appears in SAMHSA data when the source record
# had a corrupt or unencodable byte.  fetch_page() decodes the HTTP response as
# UTF-8, so any U+FFFD in the JSON value arrives in Python as the single
# character U+FFFD -- not as the three-character Latin-1 sequence (ï¿½).
_REPLACEMENT_CHAR = "�"


# ---------------------------------------------------------------------------
# Court/DUI program filter — module-level constants
# ---------------------------------------------------------------------------

# Name patterns that signal a facility is primarily a court-mandated, DUI,
# driver-education, or legal-compliance program rather than a clinical
# treatment center.  Applied to combined (name1 + name2).
_COURT_DUI_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bDUI\b",                              re.IGNORECASE),
    re.compile(r"\bDWI\b",                              re.IGNORECASE),
    re.compile(r"\bdriver\s+education\b",               re.IGNORECASE),
    re.compile(r"\bdriver\s+improvement\b",             re.IGNORECASE),
    re.compile(r"\bdriver\s+safety\s+(school|class|program)\b", re.IGNORECASE),
    re.compile(r"\bevaluaciones?\b",                    re.IGNORECASE),
    re.compile(r"\bevaluation\s+center\b",              re.IGNORECASE),
    re.compile(r"\bcourt\s+(program|assessment|evaluation|compliance|mandated)\b",
               re.IGNORECASE),
    re.compile(r"\btraffic\s+safety\s+(school|program|class)\b", re.IGNORECASE),
]

# Service settings that indicate a real clinical treatment program.
# If a record's SET includes any of these, the court/DUI name filter is
# overridden — the facility offers real residential/detox treatment even
# if the name contains court-program signals.
_TREATMENT_OVERRIDE_SETTINGS: frozenset[str] = frozenset([
    "outpatient detoxification",
    "residential detoxification",
    "hospital inpatient",
    "short-term residential",
    "long-term residential",
    "residential",
])

# ---------------------------------------------------------------------------
# Service setting → treatment type mapping
# Higher priority value wins when multiple settings are present.
# ---------------------------------------------------------------------------

_SETTING_TYPE_PRIORITY: list[tuple[str, str, int]] = [
    ("outpatient detoxification",              "detox",       10),
    ("residential detoxification",             "detox",       10),
    ("hospital inpatient",                     "residential", 8),
    ("short-term residential",                 "residential", 8),
    ("long-term residential",                  "residential", 8),
    ("residential",                            "residential", 6),
    ("intensive outpatient treatment",         "outpatient",  4),
    ("partial hospitalization",                "outpatient",  4),
    ("regular outpatient treatment",           "outpatient",  2),
    ("brief intervention",                     "outpatient",  1),
]

# SET f3 tokens that qualify a record for inclusion in treatment_centers.
# Records whose SET contains ONLY "Regular outpatient" or "Brief intervention" are excluded.
_QUALIFYING_SETTINGS: frozenset[str] = frozenset([
    "outpatient detoxification",
    "residential detoxification",
    "hospital inpatient",
    "short-term residential",
    "long-term residential",
    "residential",
    "intensive outpatient treatment",
    "partial hospitalization",
])

# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _services_by_code(services: list[dict[str, Any]]) -> dict[str, str]:
    """Return mapping of f2 service code → f3 text from a services array."""
    return {s.get("f2", ""): s.get("f3", "") for s in (services or []) if s.get("f2")}


def _split_f3(text: str) -> list[str]:
    """Split semicolon-delimited f3 text into a list of stripped tokens."""
    if not text:
        return []
    return [t.strip() for t in text.split(";") if t.strip()]


def _normalize_name(name: str) -> str:
    """Lowercase alphanumeric-only name for dedupe comparison."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _clean_text(text: str) -> str:
    """
    Clean encoding artifacts from SAMHSA API text fields.

    Handles:
    - U+FFFD (replacement character) where the source record had a corrupt byte
    - Non-breaking spaces (U+00A0), zero-width spaces (U+200B), soft hyphens (U+00AD)
    - Common HTML entities (&amp;, &nbsp;, etc.)

    Safe to call on already-clean strings.
    """
    if not text:
        return text

    # Replace U+FFFD with a plain space.  In SAMHSA data this appears where
    # an em dash or special separator was corrupted at the source.
    text = text.replace(_REPLACEMENT_CHAR, " ")

    # Invisible / non-printing Unicode
    text = text.replace("\xa0", " ")    # non-breaking space -> regular space
    text = text.replace("​", "")  # zero-width space -> remove
    text = text.replace("­", "")  # soft hyphen -> remove

    # Basic HTML entities (rare in SAMHSA data but defensive)
    text = (
        text.replace("&amp;", "&")
            .replace("&nbsp;", " ")
            .replace("&#160;", " ")
            .replace("&apos;", "'")
            .replace("&quot;", '"')
    )

    # Collapse runs of spaces introduced by replacements above
    text = re.sub(r" {2,}", " ", text).strip()

    return text
# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _derive_type(set_f3: str) -> str:
    """Derive treatment_centers.type from SET service setting text."""
    tokens = [t.lower() for t in _split_f3(set_f3)]
    best_type = "outpatient"
    best_priority = 0
    for token in tokens:
        for keyword, ttype, priority in _SETTING_TYPE_PRIORITY:
            if keyword in token and priority > best_priority:
                best_type = ttype
                best_priority = priority
    return best_type


def _is_qualifying_record(set_f3: str) -> bool:
    """
    Return True if this facility has a qualifying service setting.

    Excludes facilities whose only settings are "Regular outpatient treatment"
    or "Brief intervention" — these are too broad (primary-care offices, etc.)
    and do not represent the residential/intensive treatment center context
    CMSX Medical Access is scoped to.
    """
    tokens = [t.lower() for t in _split_f3(set_f3)]
    for token in tokens:
        for qual in _QUALIFYING_SETTINGS:
            if qual in token:
                return True
    return False


def _is_court_dui_program(name1: str, name2: str, set_f3: str) -> bool:
    """
    Return True if this record appears to be primarily a court-mandated,
    DUI/DWI, driver-education, or legal-compliance evaluation program rather
    than a clinical treatment center.

    Important: does NOT exclude facilities that merely serve justice-involved
    clients — only facilities whose name strongly signals they are
    court/evaluation programs AND that do not have residential or detox settings
    (which would indicate real clinical treatment regardless of name).
    """
    # If the record has residential or detox settings it is a real treatment
    # program regardless of its name — do not exclude.
    set_lower = set_f3.lower()
    for override in _TREATMENT_OVERRIDE_SETTINGS:
        if override in set_lower:
            return False

    # Check combined name for court/DUI signal patterns
    combined = _clean_text(f"{name1} {name2}").strip()
    for pattern in _COURT_DUI_PATTERNS:
        if pattern.search(combined):
            return True

    return False


def _derive_population(sn_f3: str, sg_f3: str) -> str:
    """Derive servesPopulation from gender-accepted and special-group fields."""
    sn = (sn_f3 or "").lower()
    # "Female and Male" appears as a single unsplit token in some SAMHSA records
    if "female and male" in sn:
        return "coed"
    # Split on semicolons and check tokens directly — avoids the false positive
    # where "male" is a substring of "female" (e.g. "Female only" must → "women")
    tokens = {t.strip() for t in sn.split(";") if t.strip()}
    has_female = any(t == "female" or t.startswith("female ") for t in tokens)
    # Must match "male" or "male only" as a token — not as a substring of "female"
    has_male = any(t == "male" or t.startswith("male ") for t in tokens)
    if has_female and has_male:
        return "coed"
    if has_female:
        return "women"
    if has_male:
        return "men"
    return ""


def _build_services_list(svc: dict[str, str]) -> list[str]:
    """Build a compact list of service tags from SAMHSA service code blocks."""
    tags: list[str] = []

    def _add(items: list[str], cap: int = 4) -> None:
        for item in items[:cap]:
            if item and item not in tags:
                tags.append(item)

    if svc.get("TC"):
        _add(_split_f3(svc["TC"]))
    if svc.get("DETOX"):
        _add(["Detoxification"])
    if svc.get("OM"):
        _add(["Opioid treatment / MAT"])
    if svc.get("AUT"):
        _add(["Alcohol use disorder treatment"])
    if svc.get("TAP"):
        _add(_split_f3(svc["TAP"]), cap=3)
    if svc.get("RSS"):
        _add(["Recovery support services"])
    if svc.get("ECS"):
        _add(["Education & counseling"])
    if svc.get("MSRV"):
        _add(["Medical services"])
    if svc.get("AS"):
        _add(_split_f3(svc["AS"]), cap=2)

    return tags[:15]


def _build_description(svc: dict[str, str]) -> str:
    """Build a short factual description from TC + SET service fields only."""
    parts: list[str] = []
    if svc.get("TC"):
        parts.append(_clean_text(svc["TC"]))
    if svc.get("SET"):
        parts.append(f"Settings: {_clean_text(svc['SET'])}")
    combined = ". ".join(parts)
    return combined[:300]


# ---------------------------------------------------------------------------
# Record classifier and normalizer
# ---------------------------------------------------------------------------

def classify_record(
    raw: dict[str, Any],
    include_court_programs: bool = False,
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """
    Classify one raw SAMHSA API row.

    Returns:
        (normalized_dict, None)         — record is included; dict ready to insert
        (None, exclusion_reason_str)    — record is excluded; reason explains why

    Exclusion reasons:
        "non_qualifying_setting"  — SET contains only regular outpatient / brief intervention
        "wrong_facility_type"     — typeFacility is not SA
        "court_or_dui_program"    — name signals court/DUI/evaluation program (unless
                                     include_court_programs=True or has residential/detox)
    """
    services = raw.get("services") or []
    svc = _services_by_code(services)
    set_f3 = svc.get("SET", "")

    # Filter 1: must have a qualifying service setting
    if not _is_qualifying_record(set_f3):
        return None, "non_qualifying_setting"

    # Filter 2: belt-and-suspenders — skip MH-only records
    facility_type = raw.get("typeFacility", "SA")
    if facility_type and facility_type not in ("SA", ""):
        return None, "wrong_facility_type"

    # Filter 3: court/DUI/evaluation programs (skipped when include_court_programs=True)
    name1_raw = (raw.get("name1") or "").strip()
    name2_raw = (raw.get("name2") or "").strip()
    if not include_court_programs and _is_court_dui_program(name1_raw, name2_raw, set_f3):
        return None, "court_or_dui_program"

    # --- Build normalized record ---
    frid = (raw.get("frid") or "").strip()

    name1 = _clean_text(name1_raw)
    name2 = _clean_text(name2_raw)

    # Append name2 only if it survives cleanup and adds context
    name = name1
    if name2 and name2.lower() not in name1.lower():
        name = f"{name1} — {name2}"

    street1 = _clean_text((raw.get("street1") or "").strip())
    street2 = _clean_text((raw.get("street2") or "").strip())
    address = ", ".join([p for p in [street1, street2] if p])

    pay_f3 = (svc.get("PAY") or "").lower()
    lca_f3 = (svc.get("LCA") or "").lower()

    try:
        lat: Optional[float] = float(raw["latitude"]) if raw.get("latitude") else None
    except (ValueError, TypeError):
        lat = None
    try:
        lng: Optional[float] = float(raw["longitude"]) if raw.get("longitude") else None
    except (ValueError, TypeError):
        lng = None

    source_url = SAMHSA_DETAILS_URL_TEMPLATE.format(frid=frid) if frid else ""

    normalized: dict[str, Any] = {
        "name": name,
        "type": _derive_type(set_f3),
        "address": address,
        "city": _clean_text((raw.get("city") or "").strip()),
        "zipCode": (raw.get("zip") or "").strip(),
        "phone": _clean_text((raw.get("intake1") or raw.get("phone") or "").strip()),
        "website": _clean_text((raw.get("website") or "").strip()),
        "description": _build_description(svc),
        "servesPopulation": _derive_population(svc.get("SN", ""), svc.get("SG", "")),
        "acceptsMediCal": 1 if "medicaid" in pay_f3 else 0,
        "acceptsMedicare": 1 if "medicare" in pay_f3 else 0,
        "acceptsPrivateInsurance": 1 if "private health insurance" in pay_f3 else 0,
        "acceptsRBH": 0,
        "acceptsCouples": 0,
        "servicesOffered": json.dumps(_build_services_list(svc)),
        "latitude": lat,
        "longitude": lng,
        "isJointCommission": 1 if "the joint commission" in lca_f3 else 0,
        "isVerified": 1,
        "isPublished": 1,
        "source_name": SOURCE_NAME,
        "source_url": source_url,
        "image_url": None,
        # Internal dedupe keys — stripped before INSERT
        "_frid": frid,
        "_norm_name": _normalize_name(name1_raw),
    }
    return normalized, None


def normalize_record(
    raw: dict[str, Any],
    include_court_programs: bool = False,
) -> Optional[dict[str, Any]]:
    """
    Normalize one raw SAMHSA API row into a treatment_centers insert dict.

    Returns None if the record is filtered out.
    Use classify_record() when you also need the exclusion reason.
    """
    result, _ = classify_record(raw, include_court_programs)
    return result


# ---------------------------------------------------------------------------
# Dry-run processing (testable, no I/O)
# ---------------------------------------------------------------------------

def build_dry_report(
    raw_rows: list[dict[str, Any]],
    include_court_programs: bool = False,
) -> dict[str, Any]:
    """
    Process a list of raw API rows and return a structured classification report.
    No DB reads or writes.

    Returns:
        {
            "total_raw": int,
            "included": [normalized_dicts...],
            "excluded": [{"name": str, "city": str, "reason": str}, ...]
        }
    """
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []

    for raw in raw_rows:
        norm, reason = classify_record(raw, include_court_programs)
        if norm is not None:
            included.append(norm)
        else:
            excluded.append({
                "name": _clean_text((raw.get("name1") or "").strip()),
                "city": (raw.get("city") or "").strip(),
                "reason": reason or "unknown",
            })

    return {
        "total_raw": len(raw_rows),
        "included": included,
        "excluded": excluded,
    }


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def ensure_optional_columns(conn: sqlite3.Connection) -> None:
    """Add source_name / source_url / image_url to treatment_centers if absent."""
    existing = {
        row[1]
        for row in conn.execute("PRAGMA table_info(treatment_centers)").fetchall()
    }
    for col, col_type in OPTIONAL_COLUMNS.items():
        if col not in existing:
            conn.execute(
                f"ALTER TABLE treatment_centers ADD COLUMN {col} {col_type}"
            )
            logger.info("Added column '%s' to treatment_centers", col)
    conn.commit()


def _existing_source_urls(conn: sqlite3.Connection) -> set[str]:
    """Return set of non-empty source_url values already in treatment_centers."""
    try:
        rows = conn.execute(
            "SELECT source_url FROM treatment_centers"
            " WHERE source_url IS NOT NULL AND source_url != ''"
        ).fetchall()
        return {row[0] for row in rows}
    except sqlite3.OperationalError:
        # source_url column does not exist yet
        return set()


def _existing_name_city_set(conn: sqlite3.Connection) -> set[tuple[str, str]]:
    """Return (norm_name, lower_city) pairs already in treatment_centers."""
    rows = conn.execute(
        "SELECT name, city FROM treatment_centers WHERE name IS NOT NULL"
    ).fetchall()
    return {(_normalize_name(row[0]), (row[1] or "").lower()) for row in rows}


def dedupe_filter(
    normalized_rows: list[dict[str, Any]],
    existing_urls: set[str],
    existing_name_city: set[tuple[str, str]],
) -> tuple[list[dict[str, Any]], int]:
    """
    Remove duplicates from normalized_rows.

    Dedupe strategy (in order):
    1. source_url / frid match → skip (primary key from SAMHSA)
    2. normalized(name) + lower(city) match → skip (protects existing hand-entered rows)
    3. Within-batch deduplication using the same two keys

    Returns (unique_rows, skipped_count).
    """
    unique: list[dict[str, Any]] = []
    skipped = 0
    seen_urls: set[str] = set(existing_urls)
    seen_name_city: set[tuple[str, str]] = set(existing_name_city)

    for row in normalized_rows:
        src_url = row.get("source_url", "")
        name_city_key = (row.get("_norm_name", ""), (row.get("city") or "").lower())

        if src_url and src_url in seen_urls:
            skipped += 1
            continue
        if name_city_key[0] and name_city_key in seen_name_city:
            skipped += 1
            continue

        unique.append(row)
        if src_url:
            seen_urls.add(src_url)
        if name_city_key[0]:
            seen_name_city.add(name_city_key)

    return unique, skipped


def _insert_row(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    """Insert one normalized row, stripping internal dedupe keys."""
    insert = {k: v for k, v in row.items() if not k.startswith("_")}
    cols = list(insert.keys())
    placeholders = ", ".join("?" * len(cols))
    col_list = ", ".join(cols)
    conn.execute(
        f"INSERT INTO treatment_centers ({col_list}) VALUES ({placeholders})",
        [insert[c] for c in cols],
    )


# ---------------------------------------------------------------------------
# API fetch
# ---------------------------------------------------------------------------

def fetch_page(
    stype: str = "SA",
    saddr: str = DEFAULT_SADDR,
    distance: int = DEFAULT_DISTANCE,
    page_size: int = DEFAULT_PAGE_SIZE,
    page: int = 1,
    sort: int = 0,
) -> dict[str, Any]:
    """Fetch one page from the SAMHSA FindTreatment.gov API."""
    body = urllib.parse.urlencode({
        "sType": stype,
        "sAddr": saddr,
        "distance": str(distance),
        "pageSize": str(page_size),
        "page": str(page),
        "sort": str(sort),
    }).encode("utf-8")

    req = urllib.request.Request(
        SAMHSA_API_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": (
                "CMSX/1.0 (social services case management; "
                "contact blackulaphotography@gmail.com)"
            ),
            "Referer": "https://findtreatment.gov/",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Fixture loader
# ---------------------------------------------------------------------------

def load_fixture(path: Path) -> list[dict[str, Any]]:
    """
    Load a local SAMHSA fixture JSON file.
    Accepts either the full API envelope (with 'rows' key) or a bare list of rows.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "rows" in data:
        return data["rows"]
    raise ValueError(f"Unrecognized fixture format in {path}")


# ---------------------------------------------------------------------------
# Run modes
# ---------------------------------------------------------------------------

def run_dry(
    stype: str = "SA",
    saddr: str = DEFAULT_SADDR,
    distance: int = DEFAULT_DISTANCE,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int = DEFAULT_MAX_PAGES,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    include_court_programs: bool = False,
) -> None:
    """
    Fetch, normalize, filter, and dedupe — print a detailed inspection report.
    No DB writes.
    """
    print(
        f"[dry-run] sType={stype}  sAddr={saddr}  distance={distance}mi  "
        f"pageSize={page_size}  max_pages={max_pages}"
    )
    print(f"[dry-run] DB path : {VIRGIL_DB_PATH}")
    if include_court_programs:
        print("[dry-run] Court/DUI program filter: DISABLED (--include-court-programs)")

    conn = sqlite3.connect(str(VIRGIL_DB_PATH))
    try:
        existing_urls = _existing_source_urls(conn)
        existing_name_city = _existing_name_city_set(conn)
        pre_count = conn.execute("SELECT COUNT(*) FROM treatment_centers").fetchone()[0]
    finally:
        conn.close()

    print(f"[dry-run] DB treatment_centers (read-only): {pre_count} rows")
    print(f"[dry-run] Existing rows with source_url   : {len(existing_urls)}")

    all_included: list[dict[str, Any]] = []
    all_excluded: list[dict[str, str]] = []
    total_raw = 0

    for pg in range(1, max_pages + 1):
        print(f"[dry-run] Fetching page {pg} ...")
        try:
            data = fetch_page(stype, saddr, distance, page_size, pg)
        except Exception as exc:
            print(f"[dry-run] API error on page {pg}: {exc}")
            break

        rows = data.get("rows") or []
        total_raw += len(rows)
        if pg == 1:
            print(
                f"[dry-run] API: recordCount={data.get('recordCount')}  "
                f"totalPages={data.get('totalPages')}"
            )

        report = build_dry_report(rows, include_court_programs)
        all_included.extend(report["included"])
        all_excluded.extend(report["excluded"])

        if pg >= (data.get("totalPages") or 1):
            print("[dry-run] Reached last page.")
            break

        time.sleep(0.5)

    unique, skipped = dedupe_filter(all_included, existing_urls, existing_name_city)

    # --- Exclusion reason counts ---
    reason_counts: dict[str, int] = {}
    for ex in all_excluded:
        r = ex["reason"]
        reason_counts[r] = reason_counts.get(r, 0) + 1

    print(f"\n[dry-run] ---- Filter summary ----")
    print(f"  Fetched              : {total_raw}")
    print(f"  Included (qualifying): {len(all_included)}")
    print(f"  Excluded             : {len(all_excluded)}")
    for reason, count in sorted(reason_counts.items()):
        print(f"    {reason:<30}: {count}")
    print(f"  Duplicate candidates : {skipped}")
    print(f"  Net new rows         : {len(unique)}")

    # --- Excluded list ---
    if all_excluded:
        print(f"\n[dry-run] ---- Excluded records ({len(all_excluded)}) ----")
        for ex in all_excluded:
            print(f"  [{ex['city']}] {ex['name']}  ({ex['reason']})")

    # --- Would-insert sample ---
    n = min(sample_size, len(unique))
    if unique:
        print(f"\n[dry-run] ---- First {n} would-insert rows ----")
        for i, row in enumerate(unique[:n], 1):
            svc_list = json.loads(row.get("servicesOffered") or "[]")
            ins_flags = (
                f"Medi-Cal={'yes' if row['acceptsMediCal'] else 'no'}  "
                f"Medicare={'yes' if row['acceptsMedicare'] else 'no'}  "
                f"PrivateIns={'yes' if row['acceptsPrivateInsurance'] else 'no'}"
            )
            svcs_short = ", ".join(svc_list[:4]) + (" ..." if len(svc_list) > 4 else "")
            print(
                f"\n  [{i}] {row['name']}\n"
                f"       type      : {row['type']}\n"
                f"       city      : {row['city']} {row['zipCode']}\n"
                f"       phone     : {row['phone'] or '(none)'}\n"
                f"       website   : {row['website'] or '(none)'}\n"
                f"       insurance : {ins_flags}\n"
                f"       population: {row['servesPopulation'] or '(unspecified)'}\n"
                f"       JointComm : {'yes' if row['isJointCommission'] else 'no'}\n"
                f"       services  : {svcs_short}\n"
                f"       source_url: {row['source_url']}"
            )

    print(f"\n[dry-run] DB was NOT modified. Pass --import-mode to insert rows.")


def run_fixture_mode(
    fixture_path: Path,
    include_court_programs: bool = False,
) -> list[dict[str, Any]]:
    """
    Load fixture JSON, normalize, filter, and dedupe against an empty baseline.
    Returns the list of unique qualifying rows (used by tests and CLI --fixture mode).
    """
    raw_rows = load_fixture(fixture_path)
    report = build_dry_report(raw_rows, include_court_programs)
    unique, _ = dedupe_filter(report["included"], set(), set())
    return unique


def run_import(
    stype: str = "SA",
    saddr: str = DEFAULT_SADDR,
    distance: int = DEFAULT_DISTANCE,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_rows: int = DEFAULT_MAX_ROWS,
    confirm_large: bool = False,
    include_court_programs: bool = False,
) -> None:
    """Fetch from API, normalize, dedupe, and INSERT capped rows into treatment_centers."""
    if max_rows > 200 and not confirm_large:
        print(
            f"[import] max_rows={max_rows} exceeds the safe cap of 200. "
            f"Pass --confirm-large-import to proceed."
        )
        sys.exit(1)

    if _is_durable_configured():
        durable = _durable_virgil_db_path()
        if not durable.exists():
            print(f"[import] ERROR: A durable DB directory is configured but")
            print(f"[import]   {durable}")
            print(f"[import]   does not exist. Writing here would create an empty DB")
            print(f"[import]   that hides all seeded content.")
            print(f"[import]   Initialize the durable DB first, then retry:")
            print(f"[import]   cp databases/virgil_st_dev.db {durable}")
            sys.exit(1)

    print(f"[import] DB path  : {VIRGIL_DB_PATH}")
    print(
        f"[import] sType={stype}  sAddr={saddr}  distance={distance}mi  "
        f"pageSize={page_size}  max_pages={max_pages}  max_rows={max_rows}"
    )
    if include_court_programs:
        print("[import] Court/DUI program filter: DISABLED (--include-court-programs)")

    conn = sqlite3.connect(str(VIRGIL_DB_PATH))
    try:
        ensure_optional_columns(conn)
        existing_urls = _existing_source_urls(conn)
        existing_name_city = _existing_name_city_set(conn)

        pre_count = conn.execute(
            "SELECT COUNT(*) FROM treatment_centers"
        ).fetchone()[0]
        print(f"[import] treatment_centers before import: {pre_count}")

        all_included: list[dict[str, Any]] = []
        total_raw = 0
        total_excluded = 0

        for pg in range(1, max_pages + 1):
            print(f"[import] Fetching page {pg} ...")
            try:
                data = fetch_page(stype, saddr, distance, page_size, pg)
            except Exception as exc:
                print(f"[import] API error on page {pg}: {exc}")
                break

            rows = data.get("rows") or []
            total_raw += len(rows)
            if pg == 1:
                print(
                    f"[import] API: recordCount={data.get('recordCount')}  "
                    f"totalPages={data.get('totalPages')}"
                )

            report = build_dry_report(rows, include_court_programs)
            all_included.extend(report["included"])
            total_excluded += len(report["excluded"])

            if pg >= (data.get("totalPages") or 1):
                print("[import] Reached last page.")
                break
            time.sleep(0.5)

        unique, skipped = dedupe_filter(all_included, existing_urls, existing_name_city)
        to_insert = unique[:max_rows]

        print(
            f"\n[import] Raw: {total_raw}  Excluded: {total_excluded}  "
            f"Normalized: {len(all_included)}  Dupes: {skipped}  "
            f"Net new: {len(unique)}  Inserting: {len(to_insert)}"
        )

        for row in to_insert:
            _insert_row(conn, row)
        conn.commit()

        post_count = conn.execute(
            "SELECT COUNT(*) FROM treatment_centers"
        ).fetchone()[0]
        print(
            f"[import] treatment_centers after import: {post_count}  "
            f"(+{post_count - pre_count})"
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="SAMHSA FindTreatment.gov importer for CMSX treatment_centers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m backend.modules.medical.importer_samhsa\n"
            "  python -m backend.modules.medical.importer_samhsa --dry-run\n"
            "  python -m backend.modules.medical.importer_samhsa --dry-run --sample-size 20\n"
            "  python -m backend.modules.medical.importer_samhsa --fixture "
            "backend/modules/medical/fixtures/samhsa_sample.json\n"
            "  python -m backend.modules.medical.importer_samhsa --import-mode\n"
            "  python -m backend.modules.medical.importer_samhsa --import-mode "
            "--max-rows 200 --confirm-large-import\n"
        ),
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run", action="store_true",
        help="Fetch and inspect — no DB writes (default mode)",
    )
    mode_group.add_argument(
        "--import-mode", action="store_true",
        help="Insert approved rows into treatment_centers",
    )
    mode_group.add_argument(
        "--fixture", type=Path, metavar="PATH",
        help="Normalize a local fixture JSON instead of hitting the API",
    )
    parser.add_argument("--stype", default="SA", choices=["SA", "MH", "BOTH"])
    parser.add_argument(
        "--saddr", default=DEFAULT_SADDR,
        help=f"Lat,Long center (default: {DEFAULT_SADDR} = downtown LA)",
    )
    parser.add_argument(
        "--distance", type=int, default=DEFAULT_DISTANCE,
        help=f"Radius in miles (default: {DEFAULT_DISTANCE})",
    )
    parser.add_argument(
        "--page-size", type=int, default=DEFAULT_PAGE_SIZE,
        help=f"Results per API page (default: {DEFAULT_PAGE_SIZE})",
    )
    parser.add_argument(
        "--max-pages", type=int, default=DEFAULT_MAX_PAGES,
        help=f"Max pages to fetch (default: {DEFAULT_MAX_PAGES})",
    )
    parser.add_argument(
        "--max-rows", type=int, default=DEFAULT_MAX_ROWS,
        help=f"Max rows to insert in --import-mode (default: {DEFAULT_MAX_ROWS})",
    )
    parser.add_argument(
        "--confirm-large-import", action="store_true",
        help="Required when --max-rows > 200",
    )
    parser.add_argument(
        "--include-court-programs", action="store_true",
        help=(
            "Disable the court/DUI/evaluation program filter. "
            "By default, records whose names signal court/DUI/evaluation programs "
            "(without residential or detox settings) are excluded."
        ),
    )
    parser.add_argument(
        "--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE,
        help=f"Number of would-insert rows to show in dry-run (default: {DEFAULT_SAMPLE_SIZE})",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    if args.import_mode:
        run_import(
            stype=args.stype,
            saddr=args.saddr,
            distance=args.distance,
            page_size=args.page_size,
            max_pages=args.max_pages,
            max_rows=args.max_rows,
            confirm_large=args.confirm_large_import,
            include_court_programs=args.include_court_programs,
        )
    elif args.fixture:
        results = run_fixture_mode(args.fixture, args.include_court_programs)
        print(f"Fixture: {len(results)} qualifying rows after filter + dedupe.")
        for row in results:
            print(json.dumps(
                {k: v for k, v in row.items() if not k.startswith("_")},
                indent=2,
                default=str,
            ))
    else:
        run_dry(
            stype=args.stype,
            saddr=args.saddr,
            distance=args.distance,
            page_size=args.page_size,
            max_pages=args.max_pages,
            sample_size=args.sample_size,
            include_court_programs=args.include_court_programs,
        )


if __name__ == "__main__":
    main()
