"""
Extracts structured operational fields from saved admission_form_responses.

Each extractor reads the raw JSON response_data blob for a specific form
and returns a typed dict of the fields we care about operationally.
All values default gracefully so callers never need to key-guard.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _yes(value: Any) -> bool:
    """Coerce yesno / checkbox / bool field values to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("yes", "y", "true", "1", "checked")
    return bool(value)


def _str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(x) for x in value if x]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


# ── Per-form extractors ────────────────────────────────────────────────────────

def extract_face_sheet(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "payer_type": _str(data.get("primary_payer_type")),
        "plan_name": _str(data.get("primary_plan_name")),
        "member_id": _str(data.get("primary_member_id")),
        "financial_responsible_party": _str(data.get("financial_responsible_party")),
        "referral_source_type": _str(data.get("referral_source_type")),
        "referral_source_details": _str(data.get("referral_source_details")),
        "current_legal_involvement": _yes(data.get("current_legal_involvement")),
        "legal_details": _str(data.get("legal_details")),
        "emergency_contact_name": _str(data.get("emergency_contact_name")),
        "emergency_contact_phone": _str(data.get("emergency_contact_phone")),
        "emergency_contact_relationship": _str(data.get("emergency_contact_relationship")),
        "primary_language": _str(data.get("primary_language")),
        "interpreter_needed": _yes(data.get("interpreter_needed")),
    }


def extract_health_questionnaire(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "needs_dental_care": _yes(data.get("needs_dental_care")),
        "last_dental_exam_date": _str(data.get("last_dental_exam_date")),
        "recent_suicidal_thoughts": _yes(data.get("recent_suicidal_thoughts")),
        "suicide_attempts_2yrs": _yes(data.get("suicide_attempts_2yrs")),
        "self_harm_violence_history": _yes(data.get("self_harm_violence_history")),
        "current_psych_treatment": _yes(data.get("current_psych_treatment")),
        "current_psychosis_symptoms": _yes(data.get("current_psychosis_symptoms")),
        "current_rx_meds": _str(data.get("current_rx_meds")),
        "allergies": _str(data.get("allergies")),
        "pregnancy_status": _str(data.get("pregnancy_status")),
        "hx_seizures_dt": _yes(data.get("hx_seizures_dt")),
        "hx_hepatitis_liver": _yes(data.get("hx_hepatitis_liver")),
        "hx_hiv_aids": _yes(data.get("hx_hiv_aids")),
        "hx_diabetes": _yes(data.get("hx_diabetes")),
        "interpersonal_violence_history": _yes(data.get("interpersonal_violence_history")),
        "su_past_7_days": _str(data.get("su_past_7_days")),
        "prior_sud_treatment": _str(data.get("prior_sud_treatment")),
    }


def extract_financial_agreement(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "payer_type": _str(data.get("primary_payer_type")),
        "plan_name": _str(data.get("primary_plan_name")),
        "member_id": _str(data.get("primary_member_id")),
        "assignment_of_benefits": _yes(data.get("assignment_of_benefits")),
        "payment_arrangement_type": _str(data.get("payment_arrangement_type")),
        "payment_notes": _str(data.get("payment_notes")),
    }


def extract_roi(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "receiving_party_name": _str(data.get("receiving_party_name")),
        "receiving_party_address": _str(data.get("receiving_party_address")),
        "purpose_of_disclosure": _str(data.get("purpose_of_disclosure")),
        "purpose_other": _str(data.get("purpose_other")),
        "authorization_effective_date": _str(data.get("authorization_effective_date")),
        "authorization_expiration_date": _str(data.get("authorization_expiration_date")),
        "info_to_release": _list(data.get("info_to_release")),
        "method_of_release": _str(data.get("method_of_release")),
        "revocation_rights_explained": _yes(data.get("revocation_rights_explained")),
        "redisclosure_warning_given": _yes(data.get("redisclosure_warning_given")),
    }


def extract_asam(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "level_of_care_recommended": _str(data.get("asam_level_of_care_recommended")),
        "loc_rationale": _str(data.get("loc_rationale")),
        "medical_necessity_summary": _str(data.get("medical_necessity_summary")),
        "provisional_diagnoses": _str(data.get("provisional_diagnoses")),
        "treatment_recommendations": _str(data.get("treatment_recommendations")),
        "d6_practical_needs": _str(data.get("d6_practical_needs")),
        "d6_living_environment": _str(data.get("d6_living_environment")),
        "d6_family_support": _str(data.get("d6_family_support")),
        "d1_severity": _str(data.get("d1_severity_rating")),
        "d2_severity": _str(data.get("d2_severity_rating")),
        "d3_severity": _str(data.get("d3_severity_rating")),
        "d4_severity": _str(data.get("d4_severity_rating")),
        "d5_severity": _str(data.get("d5_severity_rating")),
        "d6_severity": _str(data.get("d6_severity_rating")),
        "chief_complaint": _str(data.get("chief_complaint")),
        "substances_primary": _str(data.get("substances_primary")),
    }


# ── Top-level loader ───────────────────────────────────────────────────────────

_FORM_EXTRACTORS = {
    "client_face_sheet": extract_face_sheet,
    "health_questionnaire": extract_health_questionnaire,
    "financial_agreement": extract_financial_agreement,
    "roi": extract_roi,
    "asam_assessment": extract_asam,
}


def extract_admissions_data(packet_id: str, store: Any) -> Dict[str, Any]:
    """
    Load saved form responses for a packet and extract structured operational data.

    Args:
        packet_id: UUID of the admission packet.
        store:     AdmissionsStore singleton (or compatible object with get_form_response).

    Returns dict with keys: face_sheet, health, financial, roi, asam, forms_with_data.
    """
    raw: Dict[str, Dict[str, Any]] = {}
    for form_key, extractor in _FORM_EXTRACTORS.items():
        try:
            row = store.get_form_response(packet_id, form_key)
            if row and row.get("response_data"):
                raw[form_key] = row["response_data"]
        except Exception as exc:
            logger.warning(f"[EXTRACTOR] Could not load {form_key} for packet {packet_id}: {exc}")

    return {
        "face_sheet": extract_face_sheet(raw.get("client_face_sheet", {})),
        "health": extract_health_questionnaire(raw.get("health_questionnaire", {})),
        "financial": extract_financial_agreement(raw.get("financial_agreement", {})),
        "roi": extract_roi(raw.get("roi", {})),
        "asam": extract_asam(raw.get("asam_assessment", {})),
        "forms_with_data": list(raw.keys()),
    }
