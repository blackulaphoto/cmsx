"""
Builds the operational summary for an admissions packet.

Reads saved form responses, extracts key fields via extractor.py, and
generates suggested tasks using stable task_keys — no writes to any
external system. Callers decide whether to present tasks, push them, etc.
"""
import logging
import time as _time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .store_factory import admissions_store
from .extractor import extract_admissions_data

logger = logging.getLogger(__name__)

_INSTALLMENT_ARRANGEMENTS = {"Installment plan", "To be determined with billing"}

_SUMMARY_CACHE: Dict[str, Any] = {}
_CACHE_TTL_S = 30


def bust_summary_cache(client_id: str) -> None:
    _SUMMARY_CACHE.pop(client_id, None)


def build_operational_summary(client_id: str) -> Dict[str, Any]:
    _now = _time.time()
    _hit = _SUMMARY_CACHE.get(client_id)
    if _hit is not None and _now - _hit[0] < _CACHE_TTL_S:
        return _hit[1]
    _result = _build_operational_summary_uncached(client_id)
    _SUMMARY_CACHE[client_id] = (_now, _result)
    return _result


def _days_until(date_str: str) -> Optional[int]:
    if not date_str:
        return None
    try:
        # Accept ISO date (YYYY-MM-DD) and ISO datetime
        dt = datetime.fromisoformat(date_str.replace("Z", "").split("+")[0])
        return (dt.date() - datetime.utcnow().date()).days
    except Exception:
        return None


def _priority_for_days(days: Optional[int], default: str = "medium") -> str:
    if days is None:
        return default
    if days <= 0:
        return "critical"
    if days <= 7:
        return "high"
    if days <= 14:
        return "medium"
    return "low"


# ── Core builder ──────────────────────────────────────────────────────────────

def _build_operational_summary_uncached(client_id: str) -> Dict[str, Any]:
    """Build a complete operational summary. Call build_operational_summary() instead."""
    packet = admissions_store.get_packet_by_client(client_id)
    if not packet:
        return {"has_packet": False, "client_id": client_id}

    packet_id = packet["id"]
    forms: List[Dict[str, Any]] = packet.get("forms", [])

    # ── Form categorisation ───────────────────────────────────────────────────
    missing_required = [
        f for f in forms
        if f.get("required") and f.get("status") in ("Not Started", "Missing Attachment")
    ]
    needs_signature = [f for f in forms if f.get("status") == "Needs Signature"]
    in_progress = [f for f in forms if f.get("status") == "In Progress"]
    completed = [f for f in forms if f.get("status") == "Completed"]
    due_72h = [
        f for f in forms
        if f.get("timing_group") == "72_hours"
        and f.get("status") not in ("Completed", "Revoked", "Expired")
    ]
    due_7d = [
        f for f in forms
        if f.get("timing_group") == "7_days"
        and f.get("status") not in ("Completed", "Revoked", "Expired")
    ]

    # ── Extracted data ────────────────────────────────────────────────────────
    extracted = extract_admissions_data(packet_id, admissions_store)
    face_sheet = extracted["face_sheet"]
    health = extracted["health"]
    financial = extracted["financial"]
    roi = extracted["roi"]
    asam = extracted["asam"]

    # ── Medical flags ─────────────────────────────────────────────────────────
    medical_flags: List[Dict[str, Any]] = []

    if health["recent_suicidal_thoughts"] or health["suicide_attempts_2yrs"]:
        medical_flags.append({
            "type": "suicide_risk",
            "label": "Suicide / self-harm risk indicated",
            "priority": "critical",
            "source": "health_questionnaire",
        })
    if health["self_harm_violence_history"]:
        medical_flags.append({
            "type": "self_harm_history",
            "label": "History of self-harm / violence reported",
            "priority": "high",
            "source": "health_questionnaire",
        })
    if health["current_psychosis_symptoms"]:
        medical_flags.append({
            "type": "psychosis_symptoms",
            "label": "Current psychosis symptoms reported",
            "priority": "critical",
            "source": "health_questionnaire",
        })
    if health["needs_dental_care"]:
        medical_flags.append({
            "type": "dental_need",
            "label": "Dental care needed",
            "priority": "medium",
            "source": "health_questionnaire",
        })
    if health["current_psych_treatment"]:
        medical_flags.append({
            "type": "psych_treatment",
            "label": "Currently in psychiatric / MH treatment",
            "priority": "medium",
            "source": "health_questionnaire",
        })
    pregnancy = health["pregnancy_status"]
    if pregnancy and pregnancy not in ("", "Not pregnant"):
        medical_flags.append({
            "type": "pregnancy",
            "label": f"Pregnancy: {pregnancy}",
            "priority": "high",
            "source": "health_questionnaire",
        })
    if health["hx_seizures_dt"]:
        medical_flags.append({
            "type": "seizure_history",
            "label": "History of seizures / delirium tremens",
            "priority": "medium",
            "source": "health_questionnaire",
        })

    # ── Legal flags ───────────────────────────────────────────────────────────
    legal_flags: List[Dict[str, Any]] = []
    if face_sheet["current_legal_involvement"]:
        legal_flags.append({
            "type": "legal_involvement",
            "label": "Court / probation / CPS involvement",
            "details": face_sheet["legal_details"],
            "priority": "high",
            "source": "client_face_sheet",
        })

    # ── Payer / financial state ───────────────────────────────────────────────
    # Prefer face sheet payer; fall back to financial agreement
    payer_type = face_sheet["payer_type"] or financial["payer_type"]
    plan_name = face_sheet["plan_name"] or financial["plan_name"]
    payer_incomplete = bool(payer_type) and not bool(plan_name) and payer_type not in ("Self-pay",)
    payment_arrangement = financial["payment_arrangement_type"]
    needs_payment_followup = payment_arrangement in _INSTALLMENT_ARRANGEMENTS

    # ── ROI expiry ────────────────────────────────────────────────────────────
    roi_expiry = roi["authorization_expiration_date"]
    roi_days = _days_until(roi_expiry) if roi_expiry else None

    # ── ASAM LOC ──────────────────────────────────────────────────────────────
    asam_loc = asam["level_of_care_recommended"]

    # ── Suggested tasks (stable keys, no external writes) ────────────────────
    suggested_tasks: List[Dict[str, Any]] = []

    # Missing required forms
    for f in missing_required:
        suggested_tasks.append({
            "task_key": f"admissions:{client_id}:{f['form_key']}:missing",
            "title": f"Complete: {f['form_name']}",
            "description": f"Required admission form '{f['form_name']}' has not been started or is missing. ({f.get('timing_label', '')})",
            "priority": "high",
            "category": "admissions",
            "form_key": f["form_key"],
            "due_context": f.get("timing_label", ""),
        })

    # Forms needing signature
    for f in needs_signature:
        suggested_tasks.append({
            "task_key": f"admissions:{client_id}:{f['form_key']}:needs_signature",
            "title": f"Collect signature: {f['form_name']}",
            "description": f"'{f['form_name']}' is complete and ready for in-person signature collection.",
            "priority": "medium",
            "category": "admissions",
            "form_key": f["form_key"],
            "due_context": "",
        })

    # Medical / clinical flags → tasks
    for flag in medical_flags:
        if flag["type"] in ("suicide_risk", "psychosis_symptoms"):
            suggested_tasks.append({
                "task_key": f"admissions:{client_id}:medical:{flag['type']}",
                "title": f"URGENT: {flag['label']}",
                "description": (
                    f"Health Questionnaire indicates {flag['label'].lower()}. "
                    "Immediate clinical review and safety planning required."
                ),
                "priority": "critical",
                "category": "medical",
                "form_key": "health_questionnaire",
                "due_context": "Immediate",
            })
        elif flag["type"] == "self_harm_history":
            suggested_tasks.append({
                "task_key": f"admissions:{client_id}:medical:self_harm_history",
                "title": "Clinical safety review: self-harm history",
                "description": "Health Questionnaire reports history of self-harm or violence. Review with clinical supervisor.",
                "priority": "high",
                "category": "medical",
                "form_key": "health_questionnaire",
                "due_context": "Within 24 hours",
            })
        elif flag["type"] == "dental_need":
            suggested_tasks.append({
                "task_key": f"admissions:{client_id}:medical:dental",
                "title": "Arrange dental care referral",
                "description": "Health Questionnaire indicates client needs dental care.",
                "priority": "medium",
                "category": "medical",
                "form_key": "health_questionnaire",
                "due_context": "Within 7 days",
            })
        elif flag["type"] == "pregnancy":
            suggested_tasks.append({
                "task_key": f"admissions:{client_id}:medical:pregnancy",
                "title": f"Prenatal care coordination ({pregnancy})",
                "description": "Client is pregnant. Coordinate prenatal care, OB referral, and program accommodations.",
                "priority": "high",
                "category": "medical",
                "form_key": "health_questionnaire",
                "due_context": "Within 72 hours",
            })

    # Legal follow-up
    for flag in legal_flags:
        suggested_tasks.append({
            "task_key": f"admissions:{client_id}:legal:involvement",
            "title": "Legal involvement follow-up",
            "description": (
                f"Client Face Sheet indicates court/probation/CPS involvement. "
                f"{flag.get('details', '')}".strip()
            ),
            "priority": "high",
            "category": "legal",
            "form_key": "client_face_sheet",
            "due_context": "Within 72 hours",
        })

    # Payer / benefits
    if payer_incomplete:
        suggested_tasks.append({
            "task_key": f"admissions:{client_id}:financial:payer_incomplete",
            "title": "Complete insurance / payer information",
            "description": f"Payer type is '{payer_type}' but plan details are missing. Complete benefits verification.",
            "priority": "medium",
            "category": "benefits",
            "form_key": "client_face_sheet",
            "due_context": "",
        })

    if needs_payment_followup:
        suggested_tasks.append({
            "task_key": f"admissions:{client_id}:financial:payment_arrangement",
            "title": f"Finalize payment plan ({payment_arrangement})",
            "description": f"Financial Agreement lists '{payment_arrangement}'. Confirm schedule with billing.",
            "priority": "medium",
            "category": "financial",
            "form_key": "financial_agreement",
            "due_context": "Within 7 days",
        })

    # ROI expiry warning
    if roi_days is not None and roi_days <= 30:
        suggested_tasks.append({
            "task_key": f"admissions:{client_id}:roi:expiring",
            "title": f"ROI expires in {roi_days} day(s) — review and renew",
            "description": f"Release of Information for '{roi['receiving_party_name']}' expires {roi_expiry}.",
            "priority": _priority_for_days(roi_days),
            "category": "legal",
            "form_key": "roi",
            "due_context": roi_expiry,
        })

    # ── Financial coordination tasks ──────────────────────────────────────────
    fc = admissions_store.get_financial_coordination_readonly(client_id)

    if fc.get("billing_explained_status", "Not Started") != "Explained":
        suggested_tasks.append({
            "task_key": f"admissions:{client_id}:financial:billing_explained",
            "title": "Explain billing to client",
            "description": "Client billing structure and financial responsibility have not been explained.",
            "priority": "medium",
            "category": "financial",
            "form_key": None,
            "due_context": "Within 48 hours of admission",
        })

    iv_status = fc.get("insurance_verification_status", "Not Started")
    if iv_status not in ("Verified",):
        suggested_tasks.append({
            "task_key": f"admissions:{client_id}:financial:insurance_verification",
            "title": "Verify insurance benefits",
            "description": f"Insurance verification status: {iv_status}. Complete benefits verification with the payer.",
            "priority": "high" if iv_status == "Issue Found" else "medium",
            "category": "financial",
            "form_key": "client_face_sheet",
            "due_context": "Within 24 hours",
        })

    cob_st = fc.get("cob_status", "Not Needed")
    if cob_st in ("Needs Review", "Client Must Call", "Pending") or fc.get("cob_issue_identified"):
        suggested_tasks.append({
            "task_key": f"admissions:{client_id}:financial:cob",
            "title": "Resolve coordination of benefits issue",
            "description": f"COB status: {cob_st}."
            + (" Client must call payer to resolve COB." if cob_st == "Client Must Call" else ""),
            "priority": "high",
            "category": "financial",
            "form_key": None,
            "due_context": "Within 72 hours",
        })

    pmt_st = fc.get("payment_plan_status", "Not Needed")
    if pmt_st in ("Needed", "Pending", "Escalated"):
        suggested_tasks.append({
            "task_key": f"admissions:{client_id}:financial:payment_plan",
            "title": f"Follow up on payment plan ({pmt_st.lower()})",
            "description": "Client has a payment plan that needs action. Confirm schedule with billing.",
            "priority": "high" if pmt_st == "Escalated" else "medium",
            "category": "financial",
            "form_key": None,
            "due_context": "Within 7 days",
        })

    if fc.get("std_needed") == "Yes" and fc.get("std_status", "Not Started") not in (
        "Approved", "Denied", "Not Applicable"
    ):
        suggested_tasks.append({
            "task_key": f"admissions:{client_id}:leave:std",
            "title": "Start STD / short-term disability paperwork",
            "description": f"STD identified as needed. Status: {fc.get('std_status', 'Not Started')}. Initiate paperwork.",
            "priority": "medium",
            "category": "financial",
            "form_key": None,
            "due_context": "Within 7 days",
        })

    if fc.get("fmla_needed") == "Yes" and not fc.get("linked_fmla_case_id"):
        suggested_tasks.append({
            "task_key": f"admissions:{client_id}:leave:fmla",
            "title": "Link or create FMLA case",
            "description": "FMLA identified as needed but no FMLA case is linked. Open the FMLA module to start the leave request.",
            "priority": "medium",
            "category": "legal",
            "form_key": None,
            "due_context": "Within 7 days",
        })

    if not fc.get("discharge_planning_started"):
        suggested_tasks.append({
            "task_key": f"admissions:{client_id}:discharge:start",
            "title": "Start discharge planning",
            "description": "Discharge planning has not been initiated. Begin the process to ensure a smooth transition.",
            "priority": "low",
            "category": "admissions",
            "form_key": None,
            "due_context": "",
        })
    elif not fc.get("discharge_destination"):
        suggested_tasks.append({
            "task_key": f"admissions:{client_id}:discharge:destination",
            "title": "Confirm discharge destination",
            "description": "Discharge planning is started but destination has not been set.",
            "priority": "medium",
            "category": "admissions",
            "form_key": None,
            "due_context": "",
        })

    # ── Task dedup: keys already added to Smart Daily ────────────────────────
    created_task_keys = admissions_store.get_created_task_keys(client_id)

    # ── Suppressed / N/A tasks ───────────────────────────────────────────────
    suppressions = admissions_store.get_task_suppressions(client_id)
    suppressed_task_keys = [k for k, v in suppressions.items() if v == "dismissed"]
    not_applicable_task_keys = [k for k, v in suppressions.items() if v == "not_applicable"]

    # ── Assemble response ─────────────────────────────────────────────────────
    return {
        "has_packet": True,
        "packet_id": packet_id,
        "client_id": client_id,
        "client_name": packet.get("client_name", ""),
        "case_manager_id": packet.get("case_manager_id", ""),
        "packet_status": packet.get("status", ""),
        "progress_percent": packet.get("progress_percent", 0),
        # Form state lists
        "missing_required_forms": [
            {
                "form_key": f["form_key"],
                "form_name": f["form_name"],
                "timing_label": f.get("timing_label", ""),
            }
            for f in missing_required
        ],
        "forms_needing_signature": [
            {"form_key": f["form_key"], "form_name": f["form_name"]}
            for f in needs_signature
        ],
        "forms_in_progress": [
            {"form_key": f["form_key"], "form_name": f["form_name"]}
            for f in in_progress
        ],
        "completed_forms_count": len(completed),
        "due_72h": [
            {"form_key": f["form_key"], "form_name": f["form_name"], "status": f["status"]}
            for f in due_72h
        ],
        "due_7d": [
            {"form_key": f["form_key"], "form_name": f["form_name"], "status": f["status"]}
            for f in due_7d
        ],
        # Extracted key data
        "key_admissions_data": {
            "payer_type": payer_type,
            "plan_name": plan_name,
            "member_id": face_sheet["member_id"] or financial["member_id"],
            "payer_incomplete": payer_incomplete,
            "financial_responsible_party": face_sheet["financial_responsible_party"],
            "payment_arrangement": payment_arrangement,
            "payment_notes": financial["payment_notes"],
            "referral_source_type": face_sheet["referral_source_type"],
            "referral_source_details": face_sheet["referral_source_details"],
            "interpreter_needed": face_sheet["interpreter_needed"],
            "primary_language": face_sheet["primary_language"],
            "asam_loc": asam_loc,
            "asam_medical_necessity": asam["medical_necessity_summary"],
            "asam_provisional_diagnoses": asam["provisional_diagnoses"],
            "practical_needs": asam["d6_practical_needs"],
            "treatment_recommendations": asam["treatment_recommendations"],
            "roi_receiving_party": roi["receiving_party_name"],
            "roi_purpose": roi["purpose_of_disclosure"],
            "roi_info_authorized": roi["info_to_release"],
            "roi_expiry": roi_expiry,
            "roi_days_until_expiry": roi_days,
            "has_medications": bool(health["current_rx_meds"]),
            "medications": health["current_rx_meds"],
            "allergies": health["allergies"],
            "su_past_7_days": health["su_past_7_days"],
        },
        # Flags and tasks
        "medical_flags": medical_flags,
        "legal_flags": legal_flags,
        "derived_needs": medical_flags + legal_flags,
        "suggested_tasks": suggested_tasks,
        "suggested_tasks_count": len(suggested_tasks),
        "critical_task_count": sum(1 for t in suggested_tasks if t.get("priority") == "critical"),
        "created_task_keys": created_task_keys,
        "suppressed_task_keys": suppressed_task_keys,
        "not_applicable_task_keys": not_applicable_task_keys,
        "financial_coordination": fc,
    }


def build_admissions_context_for_operational(client_id: str) -> Dict[str, Any]:
    """
    Lightweight admissions slice for inclusion in the client operational-context endpoint.
    Never raises — returns {has_packet: False} on any failure so the parent handler
    can safely merge this without a try/except at the call site.
    """
    try:
        s = build_operational_summary(client_id)
        if not s.get("has_packet"):
            return {"has_packet": False}
        kad = s["key_admissions_data"]
        fc_ctx = s.get("financial_coordination", {})
        return {
            "has_packet": True,
            "packet_status": s["packet_status"],
            "progress_percent": s["progress_percent"],
            "missing_required_count": len(s["missing_required_forms"]),
            "forms_needing_signature_count": len(s["forms_needing_signature"]),
            "payer_summary": {
                "payer_type": kad["payer_type"],
                "plan_name": kad["plan_name"],
                "incomplete": kad["payer_incomplete"],
                "financial_responsible_party": kad["financial_responsible_party"],
            },
            "medical_flags": s["medical_flags"],
            "legal_flags": s["legal_flags"],
            "roi_summary": {
                "receiving_party": kad["roi_receiving_party"],
                "purpose": kad["roi_purpose"],
                "expiry": kad["roi_expiry"],
                "days_until_expiry": kad["roi_days_until_expiry"],
            },
            "asam_summary": {
                "level_of_care": kad["asam_loc"],
                "medical_necessity": kad["asam_medical_necessity"],
                "provisional_diagnoses": kad["asam_provisional_diagnoses"],
            },
            "financial_summary": {
                "payment_arrangement": kad["payment_arrangement"],
                "financial_responsible_party": kad["financial_responsible_party"],
            },
            "admissions_tasks_summary": {
                "suggested_count": s["suggested_tasks_count"],
                "critical_count": s["critical_task_count"],
                "high_count": sum(
                    1 for t in s["suggested_tasks"] if t.get("priority") == "high"
                ),
            },
            "financial_coordination_summary": {
                "billing_explained_status": fc_ctx.get("billing_explained_status"),
                "insurance_verification_status": fc_ctx.get("insurance_verification_status"),
                "cob_status": fc_ctx.get("cob_status"),
                "payment_plan_status": fc_ctx.get("payment_plan_status"),
                "std_needed": fc_ctx.get("std_needed"),
                "std_status": fc_ctx.get("std_status"),
                "fmla_needed": fc_ctx.get("fmla_needed"),
                "discharge_planning_started": fc_ctx.get("discharge_planning_started"),
                "discharge_destination": fc_ctx.get("discharge_destination"),
            },
        }
    except Exception as exc:
        logger.warning(f"[ADMISSIONS] admissions_context failed for {client_id}: {exc}")
        return {"has_packet": False, "error": str(exc)}
