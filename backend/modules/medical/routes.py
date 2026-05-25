#!/usr/bin/env python3
"""
Medical access routes for provider search, referrals, and appointment coordination.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["medical"])

BASE_DIR = Path(__file__).resolve().parents[3]
VIRGIL_DB_PATH = BASE_DIR / "databases" / "virgil_st_dev.db"
MEDICAL_DB_PATH = BASE_DIR / "databases" / "medical.db"
CASE_MGMT_DB_PATH = BASE_DIR / "databases" / "case_management.db"
CORE_CLIENTS_DB_PATH = BASE_DIR / "databases" / "core_clients.db"
REMINDERS_DB_PATH = BASE_DIR / "databases" / "reminders.db"


MEDICAL_PATHS = {
    "medi-cal": {
        "label": "Medi-Cal Providers",
        "description": "Doctors and clinics accepting Medi-Cal.",
    },
    "private-insurance": {
        "label": "Private Insurance",
        "description": "Programs and treatment options that accept private insurance.",
    },
    "dental-urgent": {
        "label": "Dental & Urgent Care",
        "description": "Dental clinics and urgent-care style intake resources.",
    },
    "treatment-centers": {
        "label": "Treatment Centers",
        "description": "Outpatient, residential, detox, and dual-diagnosis treatment options.",
    },
    "suboxone-mat": {
        "label": "Suboxone & MAT",
        "description": "Medication-assisted treatment and recovery support options.",
    },
}


class MedicalReferralCreate(BaseModel):
    client_id: str
    provider_name: str
    provider_category: str
    provider_type: str = ""
    address: str = ""
    phone: str = ""
    website: str = ""
    city: str = ""
    insurance_type: str = ""
    notes: str = ""
    referral_status: str = "Identified"


class MedicalAppointmentCreate(BaseModel):
    client_id: str
    appointment_date: str
    appointment_time: str
    appointment_type: str
    provider_name: str
    location: str = ""
    notes: str = ""
    case_manager_id: Optional[str] = None
    create_reminder: bool = True


class MedicalAppointmentUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class ReferralStatusUpdate(BaseModel):
    referral_status: str
    notes: Optional[str] = None


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_case_management_appointments_table() -> None:
    with _connect(CASE_MGMT_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                case_manager_id TEXT,
                appointment_type TEXT NOT NULL,
                provider_name TEXT,
                appointment_date DATETIME NOT NULL,
                appointment_time TEXT,
                location TEXT,
                notes TEXT,
                status TEXT DEFAULT 'scheduled',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def _ensure_medical_tables() -> None:
    with _connect(MEDICAL_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS medical_referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referral_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                provider_category TEXT NOT NULL,
                provider_type TEXT,
                address TEXT,
                phone TEXT,
                website TEXT,
                city TEXT,
                insurance_type TEXT,
                referral_status TEXT DEFAULT 'Identified',
                appointment_id TEXT,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        conn.commit()


def _ensure_reminders_table() -> None:
    with _connect(REMINDERS_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS active_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                case_manager_id TEXT NOT NULL,
                reminder_type TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT DEFAULT 'Medium',
                due_date TEXT,
                status TEXT DEFAULT 'Active',
                created_at TEXT
            )
            """
        )
        conn.commit()


def _parse_json_array(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return [str(item) for item in parsed if isinstance(item, (str, int, float))]
    except Exception:
        return []


def _normalize_text(value: Optional[str]) -> str:
    return " ".join((value or "").split()).strip()


def _normalized_upper(value: Optional[str]) -> str:
    return _normalize_text(value).upper()


GENERIC_PROVIDER_NAMES = {
    "PHYSICIAN",
    "PRACTITIONER",
    "ASSISTANT",
    "NONE REPORTED",
    "SPANISH",
    "FARSI",
    "PRESBYTERIAN",
    "ORTHOPEDIC",
    "INTERVENTIONAL RADIOLOGY",
    "ARABIC",
    "KOREAN",
    "RUSSIAN",
    "VIETNAMESE",
    "TAGALOG",
    "HINDI",
    "THERAPIST",
    "REGISTERED",
}


SPECIALTY_ONLY_PROVIDER_PATTERNS = [
    re.compile(r".+\s+PHYSICIAN$"),
    re.compile(r".+\s+PRACTITIONER$"),
    re.compile(r"^MEDICINE\s+PHYSICIAN$"),
    re.compile(r"^DISEASE\s+PHYSICIAN$"),
    re.compile(r"^[A-Z]?\d{4,}(?:\s+GROUP)?$"),
]


ORG_KEYWORDS = (
    "CLINIC",
    "MEDICAL",
    "HEALTH",
    "CENTER",
    "GROUP",
    "CARE",
    "HOSPITAL",
    "IPA",
    "PROJECT",
    "ALTAMED",
    "KAISER",
    "COMMUNITY",
)


def _is_generic_provider_name(name: Optional[str]) -> bool:
    normalized = _normalized_upper(name)
    if not normalized:
        return True
    if normalized in GENERIC_PROVIDER_NAMES:
        return True
    if normalized == "GROUP":
        return True
    return any(pattern.match(normalized) for pattern in SPECIALTY_ONLY_PROVIDER_PATTERNS)


def _is_address_fragment(value: Optional[str]) -> bool:
    normalized = _normalized_upper(value)
    if not normalized:
        return True
    if "DISTANCE:" in normalized:
        return True
    if re.search(r"\bSTE\b", normalized):
        return True
    if re.search(r"\b(?:BLVD|AVE|AVENUE|STREET|ST\b|RD\b|ROAD|DR\b|DRIVE|LN\b|LANE|WAY|HWY|PKWY|FLOOR|FL)\b", normalized):
        return True
    if re.search(r"\bCA\b", normalized) and re.search(r"\b\d{5}\b", normalized):
        return True
    if re.fullmatch(r"\d{5}", normalized):
        return True
    return normalized[0].isdigit()


def _select_best_org_label(*groups: List[str]) -> str:
    seen: set[str] = set()
    for group in groups:
        for raw_value in group:
            candidate = _normalize_text(raw_value)
            if not candidate:
                continue
            candidate_upper = candidate.upper()
            if candidate_upper in seen or _is_address_fragment(candidate):
                continue
            seen.add(candidate_upper)
            if any(keyword in candidate_upper for keyword in ORG_KEYWORDS):
                return candidate
    return ""


def _strip_provider_code_prefix(name: Optional[str]) -> str:
    normalized = _normalize_text(name)
    return re.sub(r"^[A-Z]?\d{4,}\s+", "", normalized).strip()


def _clean_metadata_values(values: List[str]) -> List[str]:
    cleaned: List[str] = []
    seen: set[str] = set()
    for raw_value in values:
        candidate = _normalize_text(raw_value)
        if not candidate or _is_address_fragment(candidate):
            continue
        if any(pattern.match(_normalized_upper(candidate)) for pattern in SPECIALTY_ONLY_PROVIDER_PATTERNS):
            continue
        candidate_upper = candidate.upper()
        if candidate_upper in seen:
            continue
        seen.add(candidate_upper)
        cleaned.append(candidate)
    return cleaned


def _build_provider_display_name(
    provider_name: Optional[str],
    medical_groups: List[str],
    hospital_affiliations: List[str],
    networks: List[str],
) -> str:
    normalized_name = _strip_provider_code_prefix(provider_name)
    if normalized_name and not _is_generic_provider_name(normalized_name):
        return normalized_name

    org_label = _select_best_org_label(medical_groups, hospital_affiliations, networks)
    if org_label:
        return org_label

    return normalized_name


def _score_medi_cal_row(
    row: sqlite3.Row,
    display_name: str,
    specialty_list: List[str],
    medical_groups: List[str],
    search: str,
    specialty: str,
    city: str,
) -> int:
    score = 0
    if display_name and not _is_generic_provider_name(display_name):
        score += 8
    else:
        score -= 10

    if row["isVerified"]:
        score += 3
    if _normalize_text(row["phone"]):
        score += 3
    if _normalize_text(row["address"]):
        score += 2
    if _normalize_text(row["city"]):
        score += 2
    if specialty_list:
        score += 2
    if medical_groups:
        score += 1

    haystacks = [
        _normalized_upper(display_name),
        _normalized_upper(" ".join(specialty_list)),
        _normalized_upper(" ".join(medical_groups)),
    ]
    if search:
        search_upper = _normalized_upper(search)
        if any(search_upper in haystack for haystack in haystacks if haystack):
            score += 5
    if specialty:
        specialty_upper = _normalized_upper(specialty)
        if any(specialty_upper in haystack for haystack in haystacks if haystack):
            score += 4
    if city:
        city_upper = _normalized_upper(city)
        if city_upper and city_upper in _normalized_upper(row["city"]):
            score += 4

    return score


def _get_client_case_manager(client_id: str) -> str:
    try:
        with _connect(CORE_CLIENTS_DB_PATH) as conn:
            row = conn.execute(
                "SELECT case_manager_id FROM clients WHERE client_id = ?",
                (client_id,),
            ).fetchone()
            return (row["case_manager_id"] if row and row["case_manager_id"] else "default_cm")
    except Exception as exc:
        logger.warning("Unable to resolve case manager for client %s: %s", client_id, exc)
        return "default_cm"


def _get_client_name_map() -> Dict[str, str]:
    names: Dict[str, str] = {}
    try:
        with _connect(CORE_CLIENTS_DB_PATH) as conn:
            rows = conn.execute("SELECT client_id, first_name, last_name FROM clients").fetchall()
            for row in rows:
                full_name = f"{(row['first_name'] or '').strip()} {(row['last_name'] or '').strip()}".strip()
                names[row["client_id"]] = full_name or row["client_id"]
    except Exception as exc:
        logger.warning("Unable to load client names for medical module: %s", exc)
    return names


def _format_provider_result(
    provider_id: str,
    category: str,
    provider_name: str,
    provider_type: str,
    address: str,
    city: str,
    phone: str,
    website: str,
    description: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "provider_id": provider_id,
        "category": category,
        "provider_name": provider_name,
        "provider_type": provider_type,
        "address": address,
        "city": city,
        "phone": phone,
        "website": website,
        "description": description,
        "extra": extra or {},
    }


def _query_medi_cal(city: str, search: str, specialty: str, limit: int) -> List[Dict[str, Any]]:
    with _connect(VIRGIL_DB_PATH) as conn:
        clauses = ["1=1"]
        params: List[Any] = []
        if city:
            clauses.append("LOWER(COALESCE(city, '')) LIKE ?")
            params.append(f"%{city.lower()}%")
        if specialty:
            clauses.append("LOWER(COALESCE(specialties, '')) LIKE ?")
            params.append(f"%{specialty.lower()}%")
        if search:
            search_pattern = f"%{search.lower()}%"
            clauses.append(
                "("
                "LOWER(COALESCE(providerName, '')) LIKE ? OR "
                "LOWER(COALESCE(facilityName, '')) LIKE ? OR "
                "LOWER(COALESCE(specialties, '')) LIKE ?"
                ")"
            )
            params.extend([search_pattern, search_pattern, search_pattern])

        rows = conn.execute(
            f"""
            SELECT id, providerName, facilityName, address, city, state, zipCode, phone,
                   specialties, languagesSpoken, networks, medicalGroups,
                   hospitalAffiliations, boardCertifications, isVerified
            FROM medi_cal_providers
            WHERE {' AND '.join(clauses)}
            LIMIT ?
            """,
            [*params, max(limit * 8, 100)],
        ).fetchall()

    merged_results: Dict[tuple[str, str, str], Dict[str, Any]] = {}
    for row in rows:
        specialty_list = _parse_json_array(row["specialties"])
        languages = _parse_json_array(row["languagesSpoken"])
        networks = _clean_metadata_values(_parse_json_array(row["networks"]))
        medical_groups = _clean_metadata_values(_parse_json_array(row["medicalGroups"]))
        hospital_affiliations = _clean_metadata_values(_parse_json_array(row["hospitalAffiliations"]))
        board_certifications = _clean_metadata_values(_parse_json_array(row["boardCertifications"]))

        name = _build_provider_display_name(
            row["facilityName"] or row["providerName"],
            medical_groups,
            hospital_affiliations,
            networks,
        )
        if not name or _is_generic_provider_name(name):
            continue

        address = ", ".join(
            [part for part in [row["address"], row["city"], row["state"], row["zipCode"]] if part]
        )
        score = _score_medi_cal_row(row, name, specialty_list, medical_groups, search, specialty, city)
        if score < 6:
            continue

        dedupe_key = (
            _normalized_upper(name),
            _normalized_upper(row["address"]),
            _normalized_upper(row["phone"]),
        )
        existing = merged_results.get(dedupe_key)
        if existing:
            existing["score"] = max(existing["score"], score)
            existing["specialties"].update(specialty_list)
            existing["languages"].update(languages)
            existing["networks"].update(networks)
            existing["medical_groups"].update(medical_groups)
            existing["hospital_affiliations"].update(hospital_affiliations)
            existing["board_certifications"].update(board_certifications)
            existing["verified"] = existing["verified"] or bool(row["isVerified"])
            continue

        merged_results[dedupe_key] = {
            "provider_id": f"medi_cal_{row['id']}",
            "provider_name": name,
            "address": address,
            "city": row["city"] or "",
            "phone": row["phone"] or "",
            "verified": bool(row["isVerified"]),
            "specialties": set(specialty_list),
            "languages": set(languages),
            "networks": set(networks),
            "medical_groups": set(medical_groups),
            "hospital_affiliations": set(hospital_affiliations),
            "board_certifications": set(board_certifications),
            "score": score,
        }

    sorted_results = sorted(
        merged_results.values(),
        key=lambda item: (
            -item["score"],
            item["city"].upper(),
            item["provider_name"].upper(),
        ),
    )[:limit]

    results = []
    for item in sorted_results:
        description_parts = []
        specialties = sorted(item["specialties"])
        languages = sorted(item["languages"])
        networks = sorted(item["networks"])
        medical_groups = sorted(item["medical_groups"])
        hospital_affiliations = sorted(item["hospital_affiliations"])

        if specialties:
            description_parts.append(f"Specialties: {', '.join(specialties[:3])}")
        if languages:
            description_parts.append(f"Languages: {', '.join(languages[:3])}")
        if medical_groups:
            description_parts.append(f"Groups: {', '.join(medical_groups[:2])}")
        elif networks:
            description_parts.append(f"Networks: {', '.join(networks[:2])}")

        results.append(
            _format_provider_result(
                provider_id=item["provider_id"],
                category="medi-cal",
                provider_name=item["provider_name"],
                provider_type="Medi-Cal Provider",
                address=item["address"],
                city=item["city"],
                phone=item["phone"],
                website="",
                description=". ".join(description_parts) or "Medi-Cal provider",
                extra={
                    "specialties": specialties,
                    "languages": languages,
                    "networks": networks,
                    "medical_groups": medical_groups,
                    "hospital_affiliations": hospital_affiliations,
                    "board_certifications": sorted(item["board_certifications"]),
                    "verified": item["verified"],
                    "quality_score": item["score"],
                },
            )
        )
    return results


def _query_dental_urgent(city: str, search: str, limit: int) -> List[Dict[str, Any]]:
    with _connect(VIRGIL_DB_PATH) as conn:
        clauses = ["LOWER(COALESCE(type, '')) = 'dental'"]
        params: List[Any] = []
        if city:
            clauses.append("LOWER(COALESCE(address, '')) LIKE ?")
            params.append(f"%{city.lower()}%")
        if search:
            pattern = f"%{search.lower()}%"
            clauses.append(
                "("
                "LOWER(COALESCE(name, '')) LIKE ? OR "
                "LOWER(COALESCE(description, '')) LIKE ?"
                ")"
            )
            params.extend([pattern, pattern])

        rows = conn.execute(
            f"""
            SELECT id, name, description, address, phone, website
            FROM resources
            WHERE {' AND '.join(clauses)}
            ORDER BY CASE WHEN LOWER(COALESCE(description, '')) LIKE '%urgent%' THEN 0 ELSE 1 END, name ASC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()

    return [
        _format_provider_result(
            provider_id=f"dental_{row['id']}",
            category="dental-urgent",
            provider_name=row["name"],
            provider_type="Dental / Urgent Care",
            address=row["address"] or "",
            city=city or "",
            phone=row["phone"] or "",
            website=row["website"] or "",
            description=row["description"] or "Dental clinic",
        )
        for row in rows
    ]


def _query_treatment_centers(city: str, search: str, limit: int, private_only: bool = False, mat_only: bool = False) -> List[Dict[str, Any]]:
    with _connect(VIRGIL_DB_PATH) as conn:
        clauses = ["isPublished = 1", "LOWER(COALESCE(type, '')) != 'sober_living'"]
        params: List[Any] = []

        if city:
            clauses.append("LOWER(COALESCE(city, '')) LIKE ?")
            params.append(f"%{city.lower()}%")

        if private_only:
            clauses.append("acceptsPrivateInsurance = 1")

        if mat_only:
            clauses.append(
                "("
                "LOWER(COALESCE(name, '')) LIKE ? OR "
                "LOWER(COALESCE(description, '')) LIKE ? OR "
                "LOWER(COALESCE(servicesOffered, '')) LIKE ?"
                ")"
            )
            params.extend(["%suboxone%", "%suboxone%", "%suboxone%"])
        elif search:
            pattern = f"%{search.lower()}%"
            clauses.append(
                "("
                "LOWER(COALESCE(name, '')) LIKE ? OR "
                "LOWER(COALESCE(description, '')) LIKE ? OR "
                "LOWER(COALESCE(servicesOffered, '')) LIKE ? OR "
                "LOWER(COALESCE(type, '')) LIKE ?"
                ")"
            )
            params.extend([pattern, pattern, pattern, pattern])

        rows = conn.execute(
            f"""
            SELECT id, name, type, address, city, zipCode, phone, website, description,
                   servesPopulation, acceptsMediCal, acceptsPrivateInsurance, servicesOffered, priceRange
            FROM treatment_centers
            WHERE {' AND '.join(clauses)}
            ORDER BY city ASC, name ASC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()

    results = []
    for row in rows:
        services = _parse_json_array(row["servicesOffered"])
        description_parts = [row["description"]] if row["description"] else []
        if services:
            description_parts.append(f"Services: {', '.join(services[:4])}")
        if row["acceptsMediCal"]:
            description_parts.append("Accepts Medi-Cal")
        if row["acceptsPrivateInsurance"]:
            description_parts.append("Accepts private insurance")
        if row["priceRange"]:
            description_parts.append(f"Price range: {row['priceRange']}")

        results.append(
            _format_provider_result(
                provider_id=f"treatment_{row['id']}",
                category="private-insurance" if private_only else ("suboxone-mat" if mat_only else "treatment-centers"),
                provider_name=row["name"],
                provider_type=(row["type"] or "treatment").replace("_", " ").title(),
                address=", ".join([part for part in [row["address"], row["city"], row["zipCode"]] if part]),
                city=row["city"] or "",
                phone=row["phone"] or "",
                website=row["website"] or "",
                description=". ".join([part for part in description_parts if part]) or "Treatment center",
                extra={
                    "services": services,
                    "serves_population": row["servesPopulation"] or "",
                },
            )
        )
    return results


def _get_provider_results(category: str, city: str, search: str, specialty: str, limit: int) -> List[Dict[str, Any]]:
    if category == "medi-cal":
        return _query_medi_cal(city, search, specialty, limit)
    if category == "dental-urgent":
        return _query_dental_urgent(city, search, limit)
    if category == "private-insurance":
        return _query_treatment_centers(city, search, limit, private_only=True)
    if category == "suboxone-mat":
        results = _query_treatment_centers(city, search, limit, mat_only=True)
        if results:
            return results
        return _query_treatment_centers(city, "", limit)
    return _query_treatment_centers(city, search, limit)


@router.get("/")
async def medical_info():
    return {
        "message": "Medical module ready",
        "paths": MEDICAL_PATHS,
    }


@router.get("/paths")
async def get_medical_paths():
    return {
        "success": True,
        "paths": [
            {"key": key, **value} for key, value in MEDICAL_PATHS.items()
        ],
    }


@router.get("/providers")
async def get_medical_providers(
    category: str = Query("medi-cal"),
    city: str = Query(""),
    search: str = Query(""),
    specialty: str = Query(""),
    limit: int = Query(25, ge=1, le=100),
):
    if category not in MEDICAL_PATHS:
        raise HTTPException(status_code=400, detail="Invalid medical category")

    try:
        results = _get_provider_results(category, city.strip(), search.strip(), specialty.strip(), limit)
        return {
            "success": True,
            "providers": results,
            "total_count": len(results),
            "category": category,
            "category_label": MEDICAL_PATHS[category]["label"],
        }
    except Exception as exc:
        logger.error("Medical provider search failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/appointments")
async def get_medical_appointments(client_id: Optional[str] = Query(None)):
    _ensure_case_management_appointments_table()
    client_names = _get_client_name_map()

    try:
        with _connect(CASE_MGMT_DB_PATH) as conn:
            query = """
                SELECT id, client_id, case_manager_id, appointment_type, provider_name,
                       appointment_date, appointment_time, location, notes, status, created_at, updated_at
                FROM appointments
                WHERE LOWER(COALESCE(appointment_type, '')) LIKE '%medical%'
            """
            params: List[Any] = []
            if client_id:
                query += " AND client_id = ?"
                params.append(client_id)
            query += " ORDER BY appointment_date ASC, appointment_time ASC"
            rows = conn.execute(query, params).fetchall()

        appointments = []
        for row in rows:
            appointments.append({
                "appointment_id": row["id"],
                "client_id": row["client_id"],
                "client_name": client_names.get(row["client_id"], row["client_id"]),
                "case_manager_id": row["case_manager_id"] or "",
                "appointment_type": row["appointment_type"],
                "provider_name": row["provider_name"] or "",
                "appointment_date": row["appointment_date"],
                "appointment_time": row["appointment_time"] or "",
                "location": row["location"] or "",
                "notes": row["notes"] or "",
                "status": row["status"] or "scheduled",
                "created_at": row["created_at"] or "",
                "updated_at": row["updated_at"] or "",
            })

        return {
            "success": True,
            "appointments": appointments,
            "total_count": len(appointments),
        }
    except Exception as exc:
        logger.error("Medical appointments fetch failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/appointments")
async def create_medical_appointment(payload: MedicalAppointmentCreate):
    _ensure_case_management_appointments_table()
    _ensure_reminders_table()

    appointment_id = str(uuid4())
    case_manager_id = payload.case_manager_id or _get_client_case_manager(payload.client_id)
    created_at = datetime.now().isoformat()

    try:
        with _connect(CASE_MGMT_DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO appointments (
                    id, client_id, case_manager_id, appointment_type, provider_name,
                    appointment_date, appointment_time, location, notes, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    appointment_id,
                    payload.client_id,
                    case_manager_id,
                    payload.appointment_type,
                    payload.provider_name,
                    payload.appointment_date,
                    payload.appointment_time,
                    payload.location,
                    payload.notes,
                    "scheduled",
                    created_at,
                    created_at,
                ),
            )
            conn.commit()

        if payload.create_reminder:
            due_date = (
                datetime.fromisoformat(payload.appointment_date) - timedelta(days=1)
            ).date().isoformat()
            with _connect(REMINDERS_DB_PATH) as conn:
                conn.execute(
                    """
                    INSERT INTO active_reminders (
                        reminder_id, client_id, case_manager_id, reminder_type,
                        message, priority, due_date, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        payload.client_id,
                        case_manager_id,
                        "Medical Appointment",
                        f"Medical appointment: {payload.provider_name} on {payload.appointment_date} at {payload.appointment_time}",
                        "High",
                        due_date,
                        "Active",
                        created_at,
                    ),
                )
                conn.commit()

        return {
            "success": True,
            "appointment_id": appointment_id,
            "message": "Medical appointment scheduled successfully",
        }
    except Exception as exc:
        logger.error("Create medical appointment failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/appointments/{appointment_id}")
async def update_medical_appointment(appointment_id: str, payload: MedicalAppointmentUpdate):
    _ensure_case_management_appointments_table()
    try:
        with _connect(CASE_MGMT_DB_PATH) as conn:
            cursor = conn.execute(
                """
                UPDATE appointments
                SET status = ?, notes = COALESCE(?, notes), updated_at = ?
                WHERE id = ?
                """,
                (payload.status, payload.notes, datetime.now().isoformat(), appointment_id),
            )
            conn.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Appointment not found")

        return {"success": True, "message": "Appointment updated successfully"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Update medical appointment failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/referrals")
async def get_medical_referrals(client_id: Optional[str] = Query(None)):
    _ensure_medical_tables()
    client_names = _get_client_name_map()
    try:
        with _connect(MEDICAL_DB_PATH) as conn:
            query = """
                SELECT referral_id, client_id, provider_name, provider_category, provider_type,
                       address, phone, website, city, insurance_type, referral_status,
                       appointment_id, notes, created_at, updated_at
                FROM medical_referrals
            """
            params: List[Any] = []
            if client_id:
                query += " WHERE client_id = ?"
                params.append(client_id)
            query += " ORDER BY updated_at DESC, created_at DESC"
            rows = conn.execute(query, params).fetchall()

        referrals = []
        for row in rows:
            referrals.append({
                "referral_id": row["referral_id"],
                "client_id": row["client_id"],
                "client_name": client_names.get(row["client_id"], row["client_id"]),
                "provider_name": row["provider_name"],
                "provider_category": row["provider_category"],
                "provider_type": row["provider_type"] or "",
                "address": row["address"] or "",
                "phone": row["phone"] or "",
                "website": row["website"] or "",
                "city": row["city"] or "",
                "insurance_type": row["insurance_type"] or "",
                "referral_status": row["referral_status"] or "Identified",
                "appointment_id": row["appointment_id"] or "",
                "notes": row["notes"] or "",
                "created_at": row["created_at"] or "",
                "updated_at": row["updated_at"] or "",
            })
        return {"success": True, "referrals": referrals, "total_count": len(referrals)}
    except Exception as exc:
        logger.error("Medical referrals fetch failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/referrals")
async def create_medical_referral(payload: MedicalReferralCreate):
    _ensure_medical_tables()
    referral_id = str(uuid4())
    timestamp = datetime.now().isoformat()
    try:
        with _connect(MEDICAL_DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO medical_referrals (
                    referral_id, client_id, provider_name, provider_category, provider_type,
                    address, phone, website, city, insurance_type, referral_status,
                    notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    referral_id,
                    payload.client_id,
                    payload.provider_name,
                    payload.provider_category,
                    payload.provider_type,
                    payload.address,
                    payload.phone,
                    payload.website,
                    payload.city,
                    payload.insurance_type,
                    payload.referral_status,
                    payload.notes,
                    timestamp,
                    timestamp,
                ),
            )
            conn.commit()
        return {"success": True, "referral_id": referral_id, "message": "Medical referral saved"}
    except Exception as exc:
        logger.error("Create medical referral failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/referrals/{referral_id}")
async def update_medical_referral(referral_id: str, payload: ReferralStatusUpdate):
    _ensure_medical_tables()
    try:
        with _connect(MEDICAL_DB_PATH) as conn:
            cursor = conn.execute(
                """
                UPDATE medical_referrals
                SET referral_status = ?, notes = COALESCE(?, notes), updated_at = ?
                WHERE referral_id = ?
                """,
                (payload.referral_status, payload.notes, datetime.now().isoformat(), referral_id),
            )
            conn.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Referral not found")
        return {"success": True, "message": "Referral updated successfully"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Update medical referral failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
