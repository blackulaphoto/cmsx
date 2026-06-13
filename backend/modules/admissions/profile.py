from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable

PROFILE_META_KEY = "_profile_meta"

FORM_FIELD_TO_PROFILE = {
    "legal_first_name": "first_name",
    "legal_last_name": "last_name",
    "preferred_name": "preferred_name",
    "client_name": "full_name",
    "date_of_birth": "date_of_birth",
    "phone_mobile": "phone",
    "phone_home": "phone_home",
    "email": "email",
    "address_line1": "address",
    "address_line2": "address_line2",
    "city": "city",
    "state": "state",
    "zip": "zip",
    "emergency_contact_name": "emergency_contact_name",
    "emergency_contact_phone": "emergency_contact_phone",
    "emergency_contact_relationship": "emergency_contact_relationship",
    "assessment_date": "admission_date",
    "questionnaire_date": "admission_date",
    "authorization_effective_date": "admission_date",
    "program_releasing_information": "program",
    "releasing_facility": "program",
    "location": "program",
    "primary_payer_type": "insurance_provider",
    "primary_plan_name": "insurance_plan_name",
    "primary_member_id": "insurance_member_id",
    "financial_responsible_party": "financial_responsible_party",
    "current_legal_involvement": "legal_probation_status",
    "legal_details": "legal_probation_notes",
    "receiving_party_name": "roi_contact_name",
    "receiving_party_address": "roi_contact_address",
    "provisional_diagnoses": "primary_diagnosis",
    "medical_necessity_summary": "primary_diagnosis",
    "substances_primary": "substance_use_summary",
    "su_past_7_days": "substance_use_summary",
}

PROFILE_TO_FORM_FIELDS = {
    "first_name": ("legal_first_name",),
    "last_name": ("legal_last_name",),
    "full_name": ("client_name",),
    "date_of_birth": ("date_of_birth",),
    "phone": ("phone_mobile", "phone_home"),
    "phone_home": ("phone_home",),
    "email": ("email", "e_service_email"),
    "address": ("address_line1",),
    "address_line2": ("address_line2",),
    "city": ("city",),
    "state": ("state",),
    "zip": ("zip",),
    "emergency_contact_name": ("emergency_contact_name",),
    "emergency_contact_phone": ("emergency_contact_phone",),
    "emergency_contact_relationship": ("emergency_contact_relationship",),
    "admission_date": ("assessment_date", "questionnaire_date", "authorization_effective_date"),
    "program": ("releasing_facility", "location"),
    "insurance_provider": ("primary_payer_type",),
    "insurance_plan_name": ("primary_plan_name",),
    "insurance_member_id": ("primary_member_id",),
    "financial_responsible_party": ("financial_responsible_party",),
    "legal_probation_status": ("current_legal_involvement",),
    "legal_probation_notes": ("legal_details",),
    "roi_contact_name": ("receiving_party_name",),
    "roi_contact_address": ("receiving_party_address",),
    "primary_diagnosis": ("provisional_diagnoses",),
    "substance_use_summary": ("substances_primary", "su_past_7_days"),
}


def _clean_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _calculate_age(date_of_birth: str) -> int | None:
    if not date_of_birth:
        return None
    try:
        birth_date = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
    except ValueError:
        return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def build_shared_profile(profile: Dict[str, Any] | None = None) -> Dict[str, Any]:
    normalized = dict(profile or {})
    first_name = _clean_string(normalized.get("first_name"))
    last_name = _clean_string(normalized.get("last_name"))
    full_name = _clean_string(normalized.get("full_name"))

    if not full_name:
        full_name = " ".join(part for part in (first_name, last_name) if part).strip()

    date_of_birth = _clean_string(normalized.get("date_of_birth"))
    age = _calculate_age(date_of_birth)

    normalized.update(
        {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "preferred_name": _clean_string(normalized.get("preferred_name")),
            "date_of_birth": date_of_birth,
            "age": age,
            "phone": _clean_string(normalized.get("phone")),
            "phone_home": _clean_string(normalized.get("phone_home")),
            "email": _clean_string(normalized.get("email")),
            "address": _clean_string(normalized.get("address")),
            "address_line2": _clean_string(normalized.get("address_line2")),
            "city": _clean_string(normalized.get("city")),
            "state": _clean_string(normalized.get("state")),
            "zip": _clean_string(normalized.get("zip") or normalized.get("zip_code")),
            "emergency_contact_name": _clean_string(normalized.get("emergency_contact_name")),
            "emergency_contact_phone": _clean_string(normalized.get("emergency_contact_phone")),
            "emergency_contact_relationship": _clean_string(normalized.get("emergency_contact_relationship")),
            "admission_date": _clean_string(normalized.get("admission_date") or normalized.get("intake_date")),
            "program": _clean_string(normalized.get("program") or normalized.get("program_type")),
            "level_status": _clean_string(normalized.get("level_status")),
            "insurance_provider": _clean_string(normalized.get("insurance_provider")),
            "insurance_plan_name": _clean_string(normalized.get("insurance_plan_name")),
            "insurance_member_id": _clean_string(normalized.get("insurance_member_id")),
            "primary_diagnosis": _clean_string(normalized.get("primary_diagnosis")),
            "substance_use_summary": _clean_string(normalized.get("substance_use_summary")),
            "legal_probation_status": normalized.get("legal_probation_status"),
            "legal_probation_notes": _clean_string(normalized.get("legal_probation_notes")),
            "roi_contact_name": _clean_string(normalized.get("roi_contact_name")),
            "roi_contact_address": _clean_string(normalized.get("roi_contact_address")),
            "financial_responsible_party": _clean_string(normalized.get("financial_responsible_party")),
        }
    )
    return normalized


def build_shared_profile_from_client(client: Dict[str, Any] | None = None) -> Dict[str, Any]:
    base = dict(client or {})
    base["zip"] = base.get("zip_code") or base.get("zip")
    base["program"] = base.get("program_type") or base.get("program")
    base["admission_date"] = base.get("admission_date") or base.get("intake_date")
    return build_shared_profile(base)


def extract_profile_updates(form_key: str, response_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    data = dict(response_data or {})
    updates: Dict[str, Any] = {}

    for field_name, profile_key in FORM_FIELD_TO_PROFILE.items():
        if field_name not in data:
            continue
        value = data.get(field_name)
        if not _has_value(value):
            continue
        updates[profile_key] = value

    if form_key == "client_face_sheet":
        if _has_value(data.get("legal_first_name")):
            updates["first_name"] = data.get("legal_first_name")
        if _has_value(data.get("legal_last_name")):
            updates["last_name"] = data.get("legal_last_name")

    return build_shared_profile(updates)


def merge_shared_profile(
    current_profile: Dict[str, Any] | None,
    profile_updates: Dict[str, Any] | None,
) -> Dict[str, Any]:
    merged = build_shared_profile(current_profile)
    for key, value in (profile_updates or {}).items():
        if _has_value(value):
            merged[key] = value
    return build_shared_profile(merged)


def get_profile_meta(response_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    data = response_data or {}
    meta = data.get(PROFILE_META_KEY)
    if not isinstance(meta, dict):
        return {"touched_fields": {}}
    touched_fields = meta.get("touched_fields")
    if not isinstance(touched_fields, dict):
        touched_fields = {}
    return {"touched_fields": touched_fields}


def strip_profile_meta(response_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    data = dict(response_data or {})
    data.pop(PROFILE_META_KEY, None)
    return data


def with_profile_meta(response_data: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(response_data)
    payload[PROFILE_META_KEY] = {
        "touched_fields": dict(meta.get("touched_fields") or {}),
    }
    return payload


def iter_profile_form_fields() -> Iterable[tuple[str, tuple[str, ...]]]:
    return PROFILE_TO_FORM_FIELDS.items()


def apply_profile_defaults(
    response_data: Dict[str, Any] | None,
    shared_profile: Dict[str, Any] | None,
) -> Dict[str, Any]:
    base = dict(response_data or {})
    meta = get_profile_meta(base)
    touched_fields = meta.get("touched_fields") or {}
    merged = strip_profile_meta(base)
    profile = build_shared_profile(shared_profile)

    for profile_key, field_names in PROFILE_TO_FORM_FIELDS.items():
        profile_value = profile.get(profile_key)
        if not _has_value(profile_value):
            continue
        for field_name in field_names:
            if touched_fields.get(field_name):
                continue
            if _has_value(merged.get(field_name)):
                continue
            merged[field_name] = profile_value

    return with_profile_meta(merged, meta)
