import logging
import os
import json
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from backend.modules.resume.file_processor import ResumeFileProcessor
from backend.shared.database.workspace_store import workspace_store
from backend.shared.database.core_client_service import CoreClientService

logger = logging.getLogger(__name__)

# Create singleton instance of core client service
_core_client_service = CoreClientService()
_file_processor = ResumeFileProcessor()
DEFAULT_CASE_MANAGER_ID = "cm_001"
PROJECT_TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "templates"
REFERENCE_LIBRARY_DIR = PROJECT_TEMPLATES_DIR / "reference-library"
AI_INSTRUCTIONS_DIR = PROJECT_TEMPLATES_DIR / "ai-instructions"

VAGUE_LANGUAGE_PATTERNS = [
    r"\bdoing better\b",
    r"\bseems okay\b",
    r"\bdoing okay\b",
    r"\bappears fine\b",
    r"\bgood session\b",
    r"\bthings are good\b",
]

TEMPLATE_KEYWORDS = {
    "progress_note": ["ONGOING WEEKLY CM NOTE", "CASE MANAGER NOTES", "CM-ONGOING-01"],
    "initial_note": ["INITIAL CM NOTE", "CM-INIT-01"],
    "group_note": ["CASE MANAGER NOTES"],
    "treatment_plan": ["TREATMENT PLANS", "TREATMENT PLAN REVIEW", "TX-DTX-01"],
    "referral_summary": ["CASE MANAGER NOTES", "FOLLOW-UP"],
    "discharge_summary": ["DISCHARGE PLAN", "DISCHARGE"],
    "fmla_case_note": ["CASE MANAGER NOTES", "ONGOING WEEKLY CM NOTE"],
    "fmla_correspondence": ["FAMILY CONTACT NOTE", "CASE MANAGER NOTES"],
}

FALLBACK_SKELETONS = {
    "progress_note": [
        ("GOAL", ""),
        ("INTERVENTION", ""),
        ("RESPONSE", ""),
        ("PLAN", ""),
    ],
    "initial_note": [
        ("GOAL", ""),
        ("INTERVENTION", ""),
        ("RESPONSE", ""),
        ("PLAN", ""),
    ],
    "group_note": [
        ("GROUP TOPIC", ""),
        ("INTERVENTION", ""),
        ("CLIENT RESPONSE", ""),
        ("PLAN", ""),
    ],
    "treatment_plan": [
        ("PROBLEM", ""),
        ("GOAL", ""),
        ("OBJECTIVE", ""),
        ("INTERVENTION", ""),
        ("NEXT REVIEW", ""),
    ],
    "referral_summary": [
        ("REFERRAL NEED", ""),
        ("ACTION TAKEN", ""),
        ("CLIENT RESPONSE", ""),
        ("NEXT STEP", ""),
    ],
    "discharge_summary": [
        ("DISCHARGE STATUS", ""),
        ("SERVICES COMPLETED", ""),
        ("OUTSTANDING RISKS", ""),
        ("AFTERCARE PLAN", ""),
    ],
    "fmla_case_note": [
        ("PURPOSE", ""),
        ("INTERVENTION", ""),
        ("STATUS / RESPONSE", ""),
        ("NEXT STEP", ""),
    ],
    "fmla_correspondence": [
        ("CONTACT", ""),
        ("SUMMARY", ""),
        ("OUTCOME", ""),
        ("FOLLOW-UP", ""),
    ],
}

TEMPLATE_QUERY_HINTS = {
    "treatment_plan": ["treatment plan", "tx plan", "goal", "objective", "intervention", "smart goal"],
    "discharge_summary": ["discharge", "aftercare", "transition note"],
    "fmla_case_note": ["fmla", "leave paperwork", "employer packet", "return to work", "rtw"],
    "fmla_correspondence": ["fmla correspondence", "hr contact", "provider contact", "fax confirmation"],
    "group_note": ["group note", "group session", "attendance", "participation level"],
    "referral_summary": ["referral", "provider summary", "handoff", "care coordination"],
    "initial_note": ["intake note", "initial note", "assessment note"],
    "progress_note": ["progress note", "case note", "documentation", "template", "templates", "note format"],
}

TEMPLATE_QUALITY_ANCHORS = {
    "Completion Letter Template": [
        r"successfully completed treatment",
        r"total of .*days of programming",
        r"sincerely",
    ],
    "Letter of Presence Template": [
        r"letter of presence",
        r"currently enrolled in treatment",
        r"presence in treatment",
    ],
    "Progress Report Template": [
        r"progress report template",
        r"treatment has primarily focused on",
        r"continues to benefit from treatment",
    ],
    "Proof of Residence Template": [
        r"proof of residency",
        r"currently a resident",
        r"residing at this address|residence address",
    ],
    "Initial CM Note": [
        r"initial cm note",
        r"^summary:",
        r"^client statement:",
        r"^next step:",
    ],
    "Weekly CM Note": [
        r"weekly cm note",
        r"^summary:",
        r"^client statement:",
        r"^next step:",
    ],
    "Treatment Plan Review": [
        r"treatment plan review",
        r"problem 1: goal",
        r"problem 1: objective",
        r"problem 1: plan",
    ],
    "Group Note": [
        r"location of client",
        r"attended the group",
        r"displayed active listening",
    ],
    "Discharge Summary": [
        r"discharge summary",
        r"date of admission",
        r"aftercare appointments",
        r"client took all personal belongings",
    ],
    "Referral Summary": [
        r"^referral need:",
        r"^action taken:",
        r"^client response:",
        r"^next step:",
    ],
    "Court / Probation Letter": [
        r"to whom it may concern",
        r"current status:",
        r"clinically relevant context:",
    ],
    "FMLA Correspondence": [
        r"contact method:",
        r"contacted party:",
        r"summary:",
        r"outcome:",
        r"follow-up:",
    ],
    "LOC Transition Note": [
        r"current loc:",
        r"new loc / transition plan:",
        r"rationale:",
        r"coordination completed:",
        r"next step:",
    ],
}

NOTE_KIND_QUALITY_ANCHORS = {
    "progress_note": [r"summary:", r"next step:"],
    "initial_note": [r"summary:", r"next step:"],
    "group_note": TEMPLATE_QUALITY_ANCHORS["Group Note"],
    "treatment_plan": TEMPLATE_QUALITY_ANCHORS["Treatment Plan Review"],
    "referral_summary": TEMPLATE_QUALITY_ANCHORS["Referral Summary"],
    "discharge_summary": TEMPLATE_QUALITY_ANCHORS["Discharge Summary"],
    "fmla_correspondence": TEMPLATE_QUALITY_ANCHORS["FMLA Correspondence"],
}

PLACEHOLDER_STAFF_SIGNATURE_TERMS = (
    "Case Manager Name",
    "CADC, LCSW",
    "License #12345",
    "License number on file",
    "cm@facility.org",
    "(555) 123-4567",
)

DATA_PLACEHOLDER_WARNINGS = {
    "CLIENT DOB": "Client date of birth is missing.",
    "CLIENT RECORD NUMBER": "Client record number is missing.",
    "ORGANIZATION ADDRESS": "Organization address is missing.",
    "RESIDENCE ADDRESS": "Residence address is missing.",
    "ADMIT DATE": "Admission date is missing.",
    "ADMISSION DATE": "Admission date is missing.",
    "DX BOX": "Diagnosis text is missing.",
}

QUOTE_PLACEHOLDER_TERMS = (
    "VERBATIM",
    "CLIENT QUOTE",
    "QUOTE",
)


def _normalize_template_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")


TEMPLATE_CONTRACTS = {
    "completion_letter_template": {
        "template_id": "file-completion-letter-template",
        "template_label": "Completion Letter Template",
        "note_kind": "completion_letter",
        "mode": "document",
        "category": "letters",
        "note_type": "Discharge",
        "output_family": "letter",
        "formal_letter": True,
        "allow_treatment_plan_structure": False,
        "allowed_sections": ["date", "re", "to whom it may concern", "summary", "closing"],
        "forbidden_patterns": [r"\bproblem 1:", r"\bobjective:", r"\bintervention:"],
        "aliases": ["completion-letter-template", "completion letter template"],
    },
    "letter_of_presence_template": {
        "template_id": "file-letter-of-presence-template",
        "template_label": "Letter of Presence Template",
        "note_kind": "presence_letter",
        "mode": "document",
        "category": "letters",
        "note_type": "Court",
        "output_family": "letter",
        "formal_letter": True,
        "allow_treatment_plan_structure": False,
        "allowed_sections": ["re", "to whom it may concern", "verification", "closing"],
        "forbidden_patterns": [r"\bproblem 1:", r"\bobjective:", r"\bintervention:"],
        "aliases": ["letter-of-presence-template", "letter of presence template"],
    },
    "progress_report_template": {
        "template_id": "file-progress-report-template",
        "template_label": "Progress Report Template",
        "note_kind": "progress_report",
        "mode": "document",
        "category": "letters",
        "note_type": "Court",
        "output_family": "progress_report",
        "formal_letter": True,
        "allow_treatment_plan_structure": False,
        "allowed_sections": ["date", "re", "program", "summary", "recommendation", "closing"],
        "forbidden_patterns": [r"\bproblem 1:", r"\bobjective:", r"\bintervention:"],
        "aliases": ["progress-report-template", "progress report template"],
    },
    "proof_of_residence_template": {
        "template_id": "file-proof-of-residence-template",
        "template_label": "Proof of Residence Template",
        "note_kind": "proof_of_residence",
        "mode": "document",
        "category": "letters",
        "note_type": "Housing",
        "output_family": "letter",
        "formal_letter": True,
        "allow_treatment_plan_structure": False,
        "allowed_sections": ["date", "re", "to whom it may concern", "residence verification", "closing"],
        "forbidden_patterns": [r"\bproblem 1:", r"\bobjective:", r"\bintervention:"],
        "aliases": ["proof-of-residence-template", "proof of residence template"],
    },
    "initial_cm_note": {
        "template_id": "initial-cm-note",
        "template_label": "Initial CM Note",
        "note_kind": "initial_note",
        "mode": "note",
        "category": "clinical",
        "note_type": "Progress",
        "output_family": "clinical_note",
        "formal_letter": False,
        "allow_treatment_plan_structure": False,
        "allowed_sections": ["summary", "client statement", "next step"],
        "forbidden_patterns": [r"\bproblem 1:", r"\bobjective:", r"\bfrequency/duration:", r"\bstatus:\s*open"],
        "aliases": ["initial cm note"],
    },
    "weekly_cm_note": {
        "template_id": "progress-note",
        "template_label": "Weekly CM Note",
        "note_kind": "progress_note",
        "mode": "note",
        "category": "clinical",
        "note_type": "Progress",
        "output_family": "clinical_note",
        "formal_letter": False,
        "allow_treatment_plan_structure": False,
        "allowed_sections": ["summary", "client statement", "next step"],
        "forbidden_patterns": [r"\bproblem 1:", r"\bobjective:", r"\bfrequency/duration:", r"\bstatus:\s*open"],
        "aliases": ["weekly cm note"],
    },
    "treatment_plan_review": {
        "template_id": "treatment-plan-review",
        "template_label": "Treatment Plan Review",
        "note_kind": "treatment_plan",
        "mode": "document",
        "category": "planning",
        "note_type": "Treatment Plan",
        "output_family": "treatment_plan_review",
        "formal_letter": False,
        "allow_treatment_plan_structure": True,
        "allowed_sections": ["problem", "goal", "objective", "plan", "review"],
        "forbidden_patterns": [],
        "aliases": ["treatment plan review"],
    },
    "group_note": {
        "template_id": "group-note",
        "template_label": "Group Note",
        "note_kind": "group_note",
        "mode": "note",
        "category": "clinical",
        "note_type": "Group",
        "output_family": "group_note",
        "formal_letter": False,
        "allow_treatment_plan_structure": False,
        "allowed_sections": ["group topic", "intervention", "client response", "next step"],
        "forbidden_patterns": [r"\bproblem 1:", r"\bobjective:"],
        "aliases": ["group note"],
    },
    "discharge_summary": {
        "template_id": "discharge-summary",
        "template_label": "Discharge Summary",
        "note_kind": "discharge_summary",
        "mode": "document",
        "category": "planning",
        "note_type": "Discharge",
        "output_family": "discharge",
        "formal_letter": False,
        "allow_treatment_plan_structure": False,
        "allowed_sections": ["discharge status", "services completed", "outstanding risks", "aftercare plan"],
        "forbidden_patterns": [r"\bproblem 1:", r"\bobjective:", r"\b12-step\b", r"\bsponsor\b"],
        "aliases": ["discharge summary"],
    },
    "referral_summary": {
        "template_id": "referral-summary",
        "template_label": "Referral Summary",
        "note_kind": "referral_summary",
        "mode": "document",
        "category": "planning",
        "note_type": "Referral",
        "output_family": "referral",
        "formal_letter": False,
        "allow_treatment_plan_structure": False,
        "allowed_sections": ["referral need", "action taken", "client response", "next step"],
        "forbidden_patterns": [r"\bproblem 1:", r"\bobjective:"],
        "aliases": ["referral summary"],
    },
    "court_probation_letter": {
        "template_id": "court-letter",
        "template_label": "Court / Probation Letter",
        "note_kind": "court_letter",
        "mode": "document",
        "category": "letters",
        "note_type": "Court",
        "output_family": "court_letter",
        "formal_letter": True,
        "allow_treatment_plan_structure": False,
        "allowed_sections": ["date", "to whom it may concern", "current status", "clinically relevant context", "closing"],
        "forbidden_patterns": [r"\bproblem 1:", r"\bobjective:", r"\bintervention:"],
        "aliases": ["court / probation letter", "court probation letter"],
    },
    "fmla_correspondence": {
        "template_id": "fmla-correspondence",
        "template_label": "FMLA Correspondence",
        "note_kind": "fmla_correspondence",
        "mode": "document",
        "category": "fmla",
        "note_type": "FMLA",
        "output_family": "fmla",
        "formal_letter": False,
        "allow_treatment_plan_structure": False,
        "allowed_sections": ["contact method", "contacted party", "summary", "outcome", "follow-up"],
        "forbidden_patterns": [r"\bproblem 1:", r"\bobjective:"],
        "aliases": ["fmla correspondence"],
    },
    "loc_transition_note": {
        "template_id": "loc-transition",
        "template_label": "LOC Transition Note",
        "note_kind": "loc_transition",
        "mode": "note",
        "category": "planning",
        "note_type": "Progress",
        "output_family": "loc_transition",
        "formal_letter": False,
        "allow_treatment_plan_structure": False,
        "allowed_sections": ["current loc", "new loc / transition plan", "rationale", "coordination completed", "next step"],
        "forbidden_patterns": [r"\bproblem 1:", r"\bobjective:"],
        "aliases": ["loc transition note"],
    },
}

TEMPLATE_ALIAS_LOOKUP = {}
for contract_key, contract in TEMPLATE_CONTRACTS.items():
    aliases = {
        contract_key,
        contract.get("template_id", ""),
        contract.get("template_label", ""),
        contract.get("note_kind", ""),
        *(contract.get("aliases", []) or []),
    }
    for alias in aliases:
        normalized_alias = _normalize_template_key(alias)
        if normalized_alias:
            TEMPLATE_ALIAS_LOOKUP[normalized_alias] = contract_key


class DocumentationAIService:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("OPENAI_DOCUMENTATION_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o"))
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        self.template_library_text = self._load_template_library()
        self.reference_library_text = self._load_reference_library()

    @staticmethod
    def _normalize_text(text: str, limit: int = 12000) -> str:
        normalized = re.sub(r"\s+", " ", (text or "")).strip()
        return normalized[:limit]

    def _refresh_provider_client(self) -> Dict[str, Any]:
        current_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        current_model = os.getenv("OPENAI_DOCUMENTATION_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o"))
        provider_available = bool(current_api_key)
        if current_api_key != self.api_key or current_model != self.model:
            self.api_key = current_api_key
            self.model = current_model
            self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        return {
            "configured": provider_available,
            "provider": "openai",
            "model": self.model,
            "reason": None if provider_available else "missing_openai_api_key",
        }

    @staticmethod
    def resolve_template_contract(note_kind: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        candidates = [
            context.get("template_id"),
            context.get("template_label"),
            context.get("template_note_kind"),
            note_kind,
        ]
        for candidate in candidates:
            contract_key = TEMPLATE_ALIAS_LOOKUP.get(_normalize_template_key(str(candidate or "")))
            if contract_key:
                return TEMPLATE_CONTRACTS[contract_key]

        fallback_note_kind_map = {
            "initial_note": "initial_cm_note",
            "progress_note": "weekly_cm_note",
            "group_note": "group_note",
            "treatment_plan": "treatment_plan_review",
            "discharge_summary": "discharge_summary",
            "referral_summary": "referral_summary",
            "fmla_correspondence": "fmla_correspondence",
            "loc_transition": "loc_transition_note",
            "court_letter": "court_probation_letter",
            "progress_report": "progress_report_template",
            "completion_letter": "completion_letter_template",
            "presence_letter": "letter_of_presence_template",
            "proof_of_residence": "proof_of_residence_template",
        }
        contract_key = fallback_note_kind_map.get(note_kind, "weekly_cm_note")
        return TEMPLATE_CONTRACTS[contract_key]

    @staticmethod
    def _placeholder_value(value: Any, default: str) -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text if text else default

    @staticmethod
    def _context_value(value: Any) -> str:
        if value in (None, "", [], {}):
            return ""
        if isinstance(value, list):
            return ", ".join(str(item).strip() for item in value if str(item).strip())
        if isinstance(value, dict):
            preferred = []
            for key in (
                "diagnosis",
                "primary_diagnosis",
                "treatment_plan",
                "aftercare_plan",
                "goals",
                "barriers",
                "notes",
            ):
                nested_value = value.get(key)
                if nested_value:
                    preferred.append(f"{key.replace('_', ' ')}: {nested_value}")
            return "; ".join(preferred) if preferred else json.dumps(value, default=str)
        return str(value).strip()

    @classmethod
    def _first_context_value(cls, *values: Any) -> str:
        for value in values:
            text = cls._context_value(value)
            if text:
                return text
        return ""

    def _build_shared_intake_context(
        self,
        comprehensive_data: Dict[str, Any],
        client_name: Optional[str] = None,
    ) -> Dict[str, str]:
        """Merge core intake and module data into one documentation context."""
        core = comprehensive_data.get("core", {}) or {}
        case_mgmt = comprehensive_data.get("case_management", {}) or {}
        active_treatment_plan = comprehensive_data.get("treatment_plan", {}) or {}

        def first(*keys: str, default: str = "") -> str:
            values = []
            for key in keys:
                values.extend([core.get(key), case_mgmt.get(key)])
            return self._first_context_value(*values) or default

        first_name = first("first_name")
        last_name = first("last_name")
        full_name = self._first_context_value(
            core.get("full_name"),
            case_mgmt.get("full_name"),
            f"{first_name} {last_name}".strip(),
            client_name,
        )
        dob = first("date_of_birth")
        address = first("address")
        city = first("city")
        state = first("state")
        zip_code = first("zip_code")
        residence_parts = [part for part in [address, city, state, zip_code] if part]
        residence_address = ", ".join(residence_parts) if residence_parts else ""

        background = {}
        for source in (core.get("background"), case_mgmt.get("background")):
            if isinstance(source, str):
                try:
                    source = json.loads(source)
                except Exception:
                    source = {}
            if isinstance(source, dict):
                background.update(source)

        diagnosis = self._first_context_value(
            first("diagnosis"),
            first("primary_diagnosis"),
            first("diagnoses"),
            first("dx_box"),
            background.get("diagnosis"),
            background.get("primary_diagnosis"),
            background.get("diagnoses"),
        )
        goals = first("goals")
        barriers = first("barriers")
        notes = first("notes")
        needs = first("needs")
        medical_conditions = first("medical_conditions")
        legal_status = first("legal_status")
        prior_convictions = first("prior_convictions")
        substance_history = first("substance_abuse_history")
        mental_health = first("mental_health_status")
        program_type = first("program_type")
        transportation = first("transportation")
        special_needs = first("special_needs")

        treatment_plan = self._first_context_value(
            active_treatment_plan.get("summary"),
            active_treatment_plan.get("goals"),
            active_treatment_plan.get("objectives"),
            active_treatment_plan.get("interventions"),
            first("treatment_plan"),
            first("treatment_plan_summary"),
            first("current_treatment_plan"),
            background.get("treatment_plan"),
            background.get("treatment_plan_summary"),
        )
        aftercare_plan = self._first_context_value(
            active_treatment_plan.get("aftercare_plan"),
            first("aftercare_plan"),
            first("aftercare_plan_summary"),
            first("discharge_plan"),
            background.get("aftercare_plan"),
            background.get("aftercare_plan_summary"),
        )

        focus_sources = [
            value
            for value in [goals, barriers, substance_history, mental_health, medical_conditions, legal_status]
            if value and value.lower() not in {"unknown", "none documented", "no active cases"}
        ]
        primary_focus = "; ".join(focus_sources[:3]) or "stability, recovery, and discharge planning"

        service_sources = [
            value
            for value in [program_type, needs, transportation, special_needs, legal_status]
            if value and value.lower() not in {"unknown", "none documented"}
        ]
        service_list = "; ".join(service_sources) or "case management and care coordination"

        verified_treatment_summary = (
            treatment_plan
            or (f"Treatment planning should be verified against the case management profile. Documented goals/barriers: {goals or barriers}"
                if (goals or barriers)
                else "Treatment plan is not documented in the intake/profile; verify before sending.")
        )
        verified_aftercare_summary = (
            aftercare_plan
            or (f"Aftercare should be built from documented goals/barriers and next follow-up. Goals/barriers: {goals or barriers}"
                if (goals or barriers)
                else "Aftercare plan is not documented in the intake/profile; add verified appointments before sending.")
        )
        diagnosis_summary = diagnosis or "Diagnosis is not documented in the intake/profile; verify clinical record before sending."

        return {
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": dob,
            "address": address,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "residence_address": residence_address,
            "client_record_number": first("client_number", "mr_number", "record_number", "client_id") or "Client record on file",
            "intake_date": first("intake_date"),
            "admission_date": first("admission_date", "intake_date"),
            "gender": first("gender", default="unknown gender"),
            "race": first("race", default="unknown race"),
            "housing_status": first("housing_status", default="Unknown"),
            "employment_status": first("employment_status", default="Unknown"),
            "benefits_status": first("benefits_status", default="Not Applied"),
            "legal_status": legal_status or "No Active Cases",
            "program_type": program_type,
            "referral_source": first("referral_source"),
            "prior_convictions": prior_convictions,
            "substance_history": substance_history,
            "mental_health": mental_health,
            "medical_conditions": medical_conditions,
            "special_needs": special_needs,
            "transportation": transportation,
            "goals": goals,
            "barriers": barriers,
            "notes": notes,
            "needs": needs,
            "treatment_plan_summary": verified_treatment_summary,
            "aftercare_plan_summary": verified_aftercare_summary,
            "diagnosis_summary": diagnosis_summary,
            "primary_treatment_focus": primary_focus,
            "service_list": service_list,
        }

    def extract_brand_guidance_text(self, file_path: str, content_type: str) -> Dict[str, Any]:
        suffix = Path(file_path).suffix.lower()

        if suffix in {".txt", ".md", ".markdown", ".html", ".htm"} or content_type.startswith("text/"):
            try:
                text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
                normalized = self._normalize_text(text)
                return {
                    "extracted_text": normalized,
                    "extraction_status": "ready" if normalized else "empty",
                }
            except Exception as exc:
                logger.warning("Unable to read text brand guidance file %s: %s", file_path, exc)
                return {"extracted_text": "", "extraction_status": "failed"}

        if suffix in {".pdf", ".doc", ".docx"}:
            success, text, _ = _file_processor.extract_text_from_file(file_path)
            normalized = self._normalize_text(text)
            return {
                "extracted_text": normalized,
                "extraction_status": "ready" if success and normalized else "failed",
            }

        if content_type.startswith("image/") or suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            return {
                "extracted_text": "",
                "extraction_status": "reference_only",
            }

        return {
            "extracted_text": "",
            "extraction_status": "unsupported",
        }

    def get_brand_guidance_context(
        self,
        query: str,
        note_kind: str,
        case_manager_id: str = DEFAULT_CASE_MANAGER_ID,
        limit: int = 3,
    ) -> Optional[str]:
        resources = workspace_store.list_brand_resources(case_manager_id)
        if not resources:
            return None

        query_terms = set(re.findall(r"[a-z0-9]+", f"{query} {note_kind}".lower()))
        scored: List[tuple[int, Dict[str, Any]]] = []
        for resource in resources:
            searchable = " ".join(
                [
                    resource.get("name", ""),
                    resource.get("category", ""),
                    resource.get("description", ""),
                    resource.get("extracted_text", "")[:4000],
                ]
            ).lower()
            score = 0
            for term in query_terms:
                if len(term) < 3:
                    continue
                if term in searchable:
                    score += 2
            if note_kind.replace("_", " ") in searchable:
                score += 3
            if resource.get("category", "").lower().replace("_", " ") in searchable:
                score += 2
            if resource.get("extraction_status") == "ready":
                score += 1
            scored.append((score, resource))

        selected = [resource for score, resource in sorted(scored, key=lambda item: item[0], reverse=True) if score > 0][:limit]
        if not selected:
            selected = [resource for resource in resources if resource.get("extraction_status") == "ready"][:limit]

        if not selected:
            return None

        blocks = []
        for resource in selected:
            excerpt = (resource.get("extracted_text") or "").strip()
            if not excerpt and resource.get("extraction_status") == "reference_only":
                excerpt = "Image uploaded for brand reference only. Text was not extracted from this file."
            if not excerpt:
                continue
            blocks.append(
                "\n".join(
                    [
                        f"Document: {resource.get('name', 'Untitled')}",
                        f"Category: {resource.get('category', 'general')}",
                        f"Description: {resource.get('description', '') or 'No description provided.'}",
                        f"Guidance excerpt: {excerpt[:1800]}",
                    ]
                )
            )

        if not blocks:
            return None

        return (
            "COMPANY DOCUMENTATION GUIDANCE LIBRARY:\n"
            "Use these organization-specific materials to match wording, structure, tone, and compliance preferences when drafting.\n\n"
            + "\n\n---\n\n".join(blocks)
        )

    def _load_template_library(self) -> str:
        template_path = Path(__file__).resolve().parents[3] / "UNIVERSAL_CM_TEMPLATES.md"
        if not template_path.exists():
            logger.warning("Universal template library not found at %s", template_path)
            return ""
        try:
            return template_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            logger.warning("Unable to read universal template library: %s", exc)
            return ""

    def _load_reference_library(self) -> str:
        blocks: List[str] = []
        for directory, label in (
            (AI_INSTRUCTIONS_DIR, "AI instruction"),
            (REFERENCE_LIBRARY_DIR, "Reference library"),
        ):
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*")):
                if not path.is_file() or path.suffix.lower() not in {".txt", ".md", ".markdown"}:
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore").strip()
                except Exception as exc:
                    logger.warning("Unable to read documentation reference file %s: %s", path, exc)
                    continue
                if text:
                    blocks.append(
                        "\n".join(
                            [
                                f"<{label} name=\"{path.name}\">",
                                self._normalize_text(text, limit=5000),
                                f"</{label}>",
                            ]
                        )
                    )
        return "\n\n".join(blocks)

    def _get_reference_library_context(self, query: str, note_kind: str, limit: int = 2) -> Optional[str]:
        if not self.reference_library_text:
            return None

        blocks = re.findall(
            r"<(?P<label>AI instruction|Reference library) name=\"(?P<name>[^\"]+)\">\n(?P<body>.*?)\n</(?P=label)>",
            self.reference_library_text,
            flags=re.DOTALL,
        )
        if not blocks:
            return self.reference_library_text[:6000]

        query_terms = {
            term
            for term in re.findall(r"[a-z0-9]+", f"{query} {note_kind}".lower())
            if len(term) >= 4
        }
        scored: List[tuple[int, str]] = []
        for label, name, body in blocks:
            searchable = f"{name} {body}".lower()
            score = 0
            if label == "AI instruction":
                score += 3
            for term in query_terms:
                if term in searchable:
                    score += 2
            if "case management playbook" in searchable:
                score += 4
            if note_kind.replace("_", " ") in searchable:
                score += 3
            scored.append((score, f"<{label} name=\"{name}\">\n{body}\n</{label}>"))

        selected = [block for score, block in sorted(scored, key=lambda item: item[0], reverse=True) if score > 0][:limit]
        if not selected:
            selected = [block for _, block in scored[:limit]]
        if not selected:
            return None

        return (
            "INTERNAL DOCUMENTATION PLAYBOOK AND REFERENCE MATERIALS:\n"
            "Use these as style, workflow, and compliance context. They are supporting context, not a replacement for the selected template.\n\n"
            + "\n\n---\n\n".join(selected)
        )

    def _get_comprehensive_client_data(self, client_id: Optional[str]) -> Dict[str, Any]:
        """Pull ALL available client data from all databases for intelligent auto-population."""
        if not client_id:
            return {}

        comprehensive_data = {}

        try:
            # Get core client data (basic demographics from core_clients.db)
            core_data = _core_client_service.get_client(client_id)
            if core_data:
                comprehensive_data['core'] = core_data

            # Get comprehensive case management data (substance history, legal status, etc.)
            from backend.shared.db_path import DB_DIR as _db
            with sqlite3.connect(str(_db / 'case_management.db')) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get full client profile
                cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
                case_mgmt_row = cursor.fetchone()
                if case_mgmt_row:
                    comprehensive_data['case_management'] = dict(case_mgmt_row)

                # Get recent case notes (last 5)
                cursor.execute("""
                    SELECT note_type, content, client_mood, progress_rating,
                           barriers_identified, action_items, created_at
                    FROM case_notes
                    WHERE client_id = ?
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (client_id,))
            notes = [dict(row) for row in cursor.fetchall()]
            comprehensive_data['recent_notes'] = notes

            current_treatment_plan = workspace_store.get_current_treatment_plan(client_id)
            if current_treatment_plan:
                comprehensive_data["treatment_plan"] = current_treatment_plan

        except Exception as exc:
            logger.warning("Error gathering comprehensive client data: %s", exc)

        try:
            current_treatment_plan = workspace_store.get_current_treatment_plan(client_id)
            if current_treatment_plan:
                comprehensive_data["treatment_plan"] = current_treatment_plan
        except Exception as exc:
            logger.warning("Unable to load treatment plan for documentation context: %s", exc)

        return comprehensive_data

    def _get_recent_note_context(self, client_id: Optional[str]) -> List[Dict[str, Any]]:
        if not client_id:
            return []
        try:
            return workspace_store.list_client_notes(client_id)[:3]
        except Exception as exc:
            logger.warning("Unable to load recent notes for documentation context: %s", exc)
            return []

    def _get_template_excerpt(self, note_kind: str) -> str:
        """Extract the full relevant template section from the library."""
        if not self.template_library_text:
            return ""
        keywords = TEMPLATE_KEYWORDS.get(note_kind, ["CASE MANAGER NOTES"])
        lower_text = self.template_library_text.lower()
        for keyword in keywords:
            idx = lower_text.find(keyword.lower())
            if idx >= 0:
                # Extract a larger section to get the complete template with examples
                return self.template_library_text[idx: idx + 3500]
        return self.template_library_text[:2500]

    @classmethod
    def _is_treatment_plan_template(cls, note_kind: str, context: Dict[str, Any]) -> bool:
        contract = cls.resolve_template_contract(note_kind, context)
        return bool(contract.get("allow_treatment_plan_structure"))

    @classmethod
    def _is_evidence_bound_template(cls, note_kind: str, context: Dict[str, Any]) -> bool:
        return not cls._is_treatment_plan_template(note_kind, context)

    @staticmethod
    def _extract_brief_sentences(text: str) -> List[str]:
        normalized = re.sub(r"\s+", " ", (text or "")).strip()
        if not normalized:
            return []
        return [segment.strip() for segment in re.split(r"(?<=[.!?])\s+", normalized) if segment.strip()]

    @staticmethod
    def _extract_direct_quote(text: str) -> str:
        match = re.search(r'"([^"]+)"', text or "")
        return match.group(1).strip() if match else ""

    @classmethod
    def _strip_placeholder_staff_signature(cls, text: str) -> str:
        lines = []
        for raw_line in (text or "").splitlines():
            line = raw_line.strip()
            if line and any(term.lower() in line.lower() for term in PLACEHOLDER_STAFF_SIGNATURE_TERMS):
                continue
            lines.append(raw_line)
        return "\n".join(lines).strip()

    @classmethod
    def _build_evidence_bound_template_fallback(
        cls,
        payload: Dict[str, Any],
        current_text: str,
    ) -> str:
        context = payload.get("context") or {}
        note_kind = payload.get("note_kind", "progress_note")
        contract = cls.resolve_template_contract(note_kind, context)
        template_label = contract.get("template_label") or context.get("template_label") or note_kind.replace("_", " ").title()
        brief_text = (context.get("case_manager_brief") or payload.get("user_prompt") or "").strip()
        sentences = cls._extract_brief_sentences(brief_text)
        quote = cls._extract_direct_quote(brief_text)
        next_steps = [
            sentence
            for sentence in sentences
            if re.search(r"\b(cm will|case manager will|follow up|follow-up|next step|will contact|will call|will request)\b", sentence, flags=re.IGNORECASE)
        ]
        summary_sentences = [sentence for sentence in sentences if sentence not in next_steps]
        no_info = "No additional information was provided."
        no_quote = "No direct client quote was documented."
        summary_text = " ".join(summary_sentences) if summary_sentences else (brief_text or no_info)
        next_step_text = " ".join(next_steps) if next_steps else no_info
        client_name = payload.get("client_name") or "Client"
        family = contract.get("output_family")

        if family == "group_note":
            return "\n".join(
                [
                    template_label.upper(),
                    "",
                    "GROUP TOPIC:",
                    summary_sentences[0] if summary_sentences else no_info,
                    "",
                    "INTERVENTION:",
                    summary_text,
                    "",
                    "CLIENT RESPONSE:",
                    quote if quote else (summary_sentences[1] if len(summary_sentences) > 1 else no_quote),
                    "",
                    "NEXT STEP:",
                    next_step_text,
                ]
            ).strip()

        if family == "referral":
            return "\n".join(
                [
                    template_label.upper(),
                    "",
                    "REFERRAL NEED:",
                    summary_text,
                    "",
                    "ACTION TAKEN:",
                    summary_text,
                    "",
                    "CLIENT RESPONSE:",
                    quote if quote else no_quote,
                    "",
                    "NEXT STEP:",
                    next_step_text,
                ]
            ).strip()

        if family == "discharge":
            return "\n".join(
                [
                    template_label.upper(),
                    "",
                    "DISCHARGE STATUS:",
                    summary_text,
                    "",
                    "SERVICES COMPLETED:",
                    summary_text,
                    "",
                    "OUTSTANDING RISKS:",
                    no_info,
                    "",
                    "AFTERCARE PLAN:",
                    next_step_text,
                ]
            ).strip()

        if family == "fmla":
            return "\n".join(
                [
                    template_label.upper(),
                    "",
                    "CONTACT METHOD:",
                    "Not documented.",
                    "",
                    "CONTACTED PARTY:",
                    "Not documented.",
                    "",
                    "SUMMARY:",
                    summary_text,
                    "",
                    "OUTCOME:",
                    quote if quote else no_info,
                    "",
                    "FOLLOW-UP:",
                    next_step_text,
                ]
            ).strip()

        if family == "loc_transition":
            return "\n".join(
                [
                    template_label.upper(),
                    "",
                    "CURRENT LOC:",
                    "Not documented.",
                    "",
                    "NEW LOC / TRANSITION PLAN:",
                    summary_text,
                    "",
                    "RATIONALE:",
                    summary_text,
                    "",
                    "COORDINATION COMPLETED:",
                    no_info,
                    "",
                    "NEXT STEP:",
                    next_step_text,
                ]
            ).strip()

        if family in {"letter", "court_letter", "progress_report"}:
            subject_line = {
                "completion_letter": f"RE: Completion Letter - {client_name}",
                "presence_letter": f"RE: Letter of Presence - {client_name}",
                "proof_of_residence": f"RE: Proof of Residence - {client_name}",
                "court_letter": f"RE: Court / Probation Update - {client_name}",
                "progress_report": f"RE: Progress Report - {client_name}",
            }.get(contract.get("note_kind"), f"RE: {template_label} - {client_name}")
            intro_line = {
                "completion_letter": "This letter summarizes the verified completion-related information documented in the case manager brief.",
                "presence_letter": "This letter verifies the documented presence and participation information provided in the case manager brief.",
                "proof_of_residence": "This letter documents the residence-related information verified in the case manager brief.",
                "court_letter": "This letter provides a professional status update using only the verified facts documented in the case manager brief.",
                "progress_report": "This progress report summarizes the verified participation and care-coordination facts documented in the case manager brief.",
            }.get(contract.get("note_kind"), "This letter summarizes the verified information documented in the case manager brief.")
            return "\n".join(
                [
                    template_label.upper(),
                    "",
                    f"DATE: {datetime.now().strftime('%B %d, %Y')}",
                    subject_line,
                    "",
                    "To Whom It May Concern,",
                    "",
                    intro_line,
                    "",
                    summary_text,
                    "",
                    f"Client statement: {quote if quote else no_quote}",
                    f"Next step: {next_step_text}",
                    "",
                    "Sincerely,",
                    "Case Manager",
                ]
            ).strip()

        return "\n".join(
            [
                template_label.upper(),
                "",
                "SUMMARY:",
                summary_text,
                "",
                "CLIENT STATEMENT:",
                quote if quote else no_quote,
                "",
                "NEXT STEP:",
                next_step_text,
            ]
        ).strip()

    @staticmethod
    def _build_template_guardrails(note_kind: str, context: Dict[str, Any]) -> List[str]:
        contract = DocumentationAIService.resolve_template_contract(note_kind, context)
        template_label = str(contract.get("template_label") or (context or {}).get("template_label") or note_kind.replace("_", " ").title()).strip()
        requested_output_mode = str((context or {}).get("requested_output_mode") or "").strip() or "note"
        guardrails = [
            f"Selected template label: {template_label}.",
            f"Requested output mode: {requested_output_mode}.",
            f"Output family: {contract.get('output_family')}.",
        ]

        if contract.get("allow_treatment_plan_structure"):
            guardrails.extend(
                [
                    "Produce a treatment plan review structure with problem, goal, objective, plan, and review details.",
                    "Treatment-plan language is allowed because the selected template is treatment-plan based.",
                ]
            )
            return guardrails

        if contract.get("output_family") == "clinical_note":
            guardrails.extend(
                [
                    "Keep the output in concise case-management note structure only.",
                    "Use only facts from the case manager brief as the substantive source of truth.",
                    "Do not introduce treatment-plan headings such as 'Problem 1', 'Objective', 'Frequency/Duration', 'Status: open', or 'Outcome: in progress'.",
                    "Do not add 12-step, sponsor, medication compliance, aftercare, discharge planning, treatment plan goals, or other generic filler unless the brief explicitly states them.",
                    "Do not add signature lines, credentials, license placeholders, or staff contact placeholders unless verified values were explicitly provided.",
                ]
            )
            return guardrails

        if contract.get("formal_letter"):
            guardrails.extend(
                [
                    "Write a formal letter matching the selected template, with a salutation and professional closing.",
                    "Do not switch into clinical-note headings unless they are explicitly part of the selected letter template.",
                    "Do not add unsupported signatures, license numbers, credentials, diagnoses, services, or attendance facts.",
                ]
            )
            return guardrails

        if contract.get("output_family") == "fmla":
            guardrails.extend(
                [
                    "Use FMLA correspondence structure only.",
                    "Do not invent medical facts, provider opinions, diagnoses, or leave dates.",
                ]
            )
            return guardrails

        if contract.get("output_family") == "referral":
            guardrails.extend(
                [
                    "Use referral-summary headings only: Referral Need, Action Taken, Client Response, Next Step.",
                    "Do not drift into letter format or treatment-plan structure.",
                ]
            )
            return guardrails

        if contract.get("output_family") == "loc_transition":
            guardrails.extend(
                [
                    "Use LOC transition note headings only.",
                    "Do not convert the draft into treatment-plan or weekly-note structure.",
                ]
            )
            return guardrails

        guardrails.append(
            "Do not switch formats. Stay inside the structure and heading style of the selected template."
        )
        guardrails.append("Use only facts from the case manager brief as the substantive source of truth.")
        guardrails.append("Do not invent services, referrals, medication issues, aftercare plans, treatment goals, attendance, risk, or symptoms that were not documented.")
        return guardrails

    def _infer_note_kind_from_query(self, query: str) -> str:
        lowered = (query or "").lower()
        for note_kind, hints in TEMPLATE_QUERY_HINTS.items():
            if any(hint in lowered for hint in hints):
                return note_kind
        return "progress_note"

    def get_template_reference_context(self, query: str) -> Optional[str]:
        if not self.template_library_text:
            return None

        note_kind = self._infer_note_kind_from_query(query)
        excerpt = self._get_template_excerpt(note_kind)
        if not excerpt:
            return None

        available_templates = ", ".join(
            [
                "progress notes",
                "initial notes",
                "group notes",
                "treatment plans",
                "referral summaries",
                "discharge summaries",
                "FMLA case notes",
                "FMLA correspondence",
            ]
        )
        reference_context = self._get_reference_library_context(query, note_kind)
        return (
            "Internal documentation template library is available from UNIVERSAL_CM_TEMPLATES.md.\n"
            "Do not claim you lack access to templates or documentation guidance.\n"
            f"Relevant template category: {note_kind}.\n"
            f"Available template families: {available_templates}.\n"
            "Use this internal guidance before answering template or documentation questions.\n"
            "Relevant template excerpt:\n"
            f"{excerpt}"
            + (f"\n\n{reference_context}" if reference_context else "")
        )

    def _auto_fill_placeholders(self, draft: str, client_id: Optional[str], client_name: Optional[str]) -> str:
        """Automatically replace ALL placeholders with real client data from comprehensive database pull."""
        filled = draft
        current_date = datetime.now().strftime("%B %d, %Y")
        current_time = datetime.now().strftime("%-I:%M %p" if os.name != "nt" else "%#I:%M %p")
        next_week = (datetime.now() + timedelta(days=7)).strftime("%B %d, %Y")
        thirty_days = (datetime.now() + timedelta(days=30)).strftime("%B %d, %Y")
        sixty_days = (datetime.now() + timedelta(days=60)).strftime("%B %d, %Y")
        ninety_days = (datetime.now() + timedelta(days=90)).strftime("%B %d, %Y")

        # Get comprehensive client data from all databases
        comprehensive_data = self._get_comprehensive_client_data(client_id) if client_id else {}
        core_data = comprehensive_data.get('core', {})
        case_mgmt_data = comprehensive_data.get('case_management', {})
        intake_context = self._build_shared_intake_context(comprehensive_data, client_name)

        # Auto-fill client name variations
        if intake_context.get("full_name"):
            first_name = intake_context.get("first_name") or "[CLIENT FIRST NAME]"
            last_name = intake_context.get("last_name") or "[CLIENT LAST NAME]"
            full_name = intake_context["full_name"]
        elif client_name:
            full_name = client_name
            parts = client_name.split()
            first_name = parts[0] if parts else '[CLIENT FIRST NAME]'
            last_name = parts[-1] if len(parts) > 1 else '[CLIENT LAST NAME]'
        else:
            full_name = "[CLIENT FULL NAME]"
            first_name = "[CLIENT FIRST NAME]"
            last_name = "[CLIENT LAST NAME]"

        # Calculate age from date of birth
        age_str = "[AGE]"
        dob = intake_context.get("date_of_birth")
        if dob:
            try:
                dob_date = datetime.strptime(dob, '%Y-%m-%d')
                age = (datetime.now() - dob_date).days // 365
                age_str = str(age)
            except:
                pass

        admission_date_raw = intake_context.get("admission_date")
        admission_date = self._placeholder_value(admission_date_raw, current_date)
        total_days_in_program = "1"
        if admission_date_raw:
            for date_format in ("%Y-%m-%d", "%B %d, %Y"):
                try:
                    start_date = datetime.strptime(str(admission_date_raw)[:10], date_format)
                    total_days_in_program = str(max(1, (datetime.now() - start_date).days + 1))
                    break
                except Exception:
                    continue

        organization_name = os.getenv("CMSX_ORGANIZATION_NAME", "Treatment Facility").strip() or "Treatment Facility"
        organization_address_line_1 = (
            os.getenv("CMSX_ORGANIZATION_ADDRESS_LINE_1")
            or os.getenv("CMSX_ORGANIZATION_ADDRESS")
            or "Treatment Facility address on file"
        ).strip()
        organization_address_line_2 = os.getenv("CMSX_ORGANIZATION_ADDRESS_LINE_2", "").strip()
        client_record_number = (
            intake_context.get("client_record_number")
            or client_id
            or "Client record on file"
        )

        # Get demographic and status information
        gender = self._placeholder_value(intake_context.get("gender"), '[GENDER]')
        race = self._placeholder_value(intake_context.get("race"), '[RACE]')
        housing_status = self._placeholder_value(intake_context.get("housing_status"), 'Unknown')
        employment_status = self._placeholder_value(intake_context.get("employment_status"), 'Unemployed')
        legal_status = self._placeholder_value(intake_context.get("legal_status"), 'No Active Cases')
        substance_history = self._placeholder_value(intake_context.get("substance_history"), 'No documented history')
        mental_health = self._placeholder_value(intake_context.get("mental_health"), 'Stable')
        prior_convictions = self._placeholder_value(intake_context.get("prior_convictions"), 'None documented')

        # Replace all client name placeholders
        filled = filled.replace("[CT NAME]", full_name)
        filled = filled.replace("[Client Name]", full_name)
        filled = filled.replace("[CLIENT NAME]", full_name)
        filled = filled.replace("[CLIENT_NAME]", full_name)
        filled = filled.replace("[CT FIRST NAME]", first_name)
        filled = filled.replace("[CT LAST NAME]", last_name)

        # Replace demographic placeholders
        filled = filled.replace("[AGE]", age_str)
        filled = filled.replace("[GENDER]", gender)
        filled = filled.replace("[RACE]", race)

        # Replace status placeholders
        filled = filled.replace("[HOUSING STATUS]", housing_status)
        filled = filled.replace("[EMPLOYMENT STATUS]", employment_status)
        filled = filled.replace("[LEGAL STATUS]", legal_status)
        filled = filled.replace("[SUBSTANCE HISTORY]", substance_history)
        filled = filled.replace("[SUBSTANCES / PRESENTING CONCERNS]", substance_history)
        filled = filled.replace("[MENTAL HEALTH STATUS]", mental_health)
        filled = filled.replace("[PRIOR CONVICTIONS]", prior_convictions)

        # Replace dates
        filled = filled.replace("[DATE]", current_date)
        filled = filled.replace("[TODAY]", current_date)
        filled = filled.replace("[CURRENT DATE]", current_date)
        filled = filled.replace("[ADMIT DATE]", admission_date)
        filled = filled.replace("[ADMISSION DATE]", admission_date)
        filled = filled.replace("[CLIENT_DOB]", self._placeholder_value(intake_context.get("date_of_birth"), "[CLIENT DOB]"))
        filled = filled.replace("[CLIENT DOB]", self._placeholder_value(intake_context.get("date_of_birth"), "Client DOB on file"))
        filled = filled.replace("[CLIENT_AGE]", age_str)
        filled = filled.replace("[ADMISSION_DATE]", admission_date)
        filled = filled.replace("[RESIDENCY_START_DATE]", self._placeholder_value(case_mgmt_data.get('residency_start_date') or admission_date_raw, current_date))
        filled = filled.replace("[TIME]", current_time)
        filled = filled.replace("[NEXT WEEK]", next_week)
        filled = filled.replace("[30 DAYS]", thirty_days)
        filled = filled.replace("[60 DAYS]", sixty_days)
        filled = filled.replace("[90 DAYS]", ninety_days)

        # Case manager defaults (user should customize these)
        filled = filled.replace("[CM NAME]", "Case Manager Name")
        filled = filled.replace("[CM CREDENTIALS]", "CADC, LCSW")
        filled = filled.replace("[CM LICENSE #]", "License #12345")
        filled = filled.replace("[CM EMAIL]", "cm@facility.org")
        filled = filled.replace("[CM PHONE]", "(555) 123-4567")
        filled = filled.replace("[FACILITY NAME]", organization_name)
        filled = filled.replace("[PROGRAM_NAME]", self._placeholder_value(intake_context.get("program_type"), "the treatment program"))
        filled = filled.replace("[ORGANIZATION_NAME]", organization_name)
        filled = filled.replace("[ORGANIZATION ADDRESS]", organization_address_line_1)
        filled = filled.replace("[ORGANIZATION_ADDRESS_LINE_1]", organization_address_line_1)
        filled = filled.replace("[ORGANIZATION_ADDRESS_LINE_2]", organization_address_line_2)
        filled = filled.replace("[PROGRAM_OR_HOUSING_TYPE]", self._placeholder_value(intake_context.get("program_type") or intake_context.get("housing_status"), "program residence"))
        filled = filled.replace("[RESIDENCE_ADDRESS_LINE_1]", self._placeholder_value(intake_context.get("residence_address") or intake_context.get("address"), "[RESIDENCE ADDRESS]"))
        filled = filled.replace("[RESIDENCE_ADDRESS_LINE_2]", "")
        filled = filled.replace("[CLIENT_RECORD_NUMBER]", str(client_record_number))
        filled = filled.replace("[CLIENT RECORD NUMBER]", str(client_record_number))
        filled = filled.replace("[STAFF_NAME]", "Case Manager Name")
        filled = filled.replace("[STAFF_TITLE]", "Case Manager")
        filled = filled.replace("[STAFF_EMAIL]", "cm@facility.org")
        filled = filled.replace("[STAFF_PHONE]", "(555) 123-4567")

        general_defaults = {
            "[TOTAL_DAYS_IN_PROGRAM]": total_days_in_program,
            "[TOTAL DAYS IN PROGRAM]": total_days_in_program,
            "[TREATMENT_COMPONENTS]": intake_context["service_list"],
            "[PRIMARY_TREATMENT_FOCUS]": intake_context["primary_treatment_focus"],
            "[ENGAGEMENT_AND_PROGRESS_SUMMARY]": intake_context["treatment_plan_summary"],
            "[AFTERCARE_OR_RECOVERY_SUPPORTS]": intake_context["aftercare_plan_summary"],
            "[STANDING_AND_COMPLIANCE_SUMMARY]": "actively engaged and in good standing",
            "[PROGRAM_SERVICE_SUMMARY]": intake_context["service_list"],
            "[SERVICE_LIST]": intake_context["service_list"],
            "[PURPOSE_OF_LETTER]": "verification requested by the client",
            "[DETOX_OR_PREVIOUS_LEVEL_OF_CARE_SUMMARY]": "entered the current level of care for continued support",
            "[ENGAGEMENT_AND_COMPLIANCE_SUMMARY]": "remained engaged in services",
            "[FOCUS_AREA_1]": intake_context["goals"] or "Recovery stability",
            "[FOCUS_AREA_2]": intake_context["barriers"] or "Housing and aftercare planning",
            "[FOCUS_AREA_3]": intake_context["legal_status"] or "Legal or probation follow-up as applicable",
            "[FOCUS_AREA_4]": intake_context["aftercare_plan_summary"],
            "[PARTICIPATION_AND_PROGRESS_SUMMARY]": intake_context["treatment_plan_summary"],
            "[CLINICAL_PROGRESS_STATEMENT]": intake_context["diagnosis_summary"],
            "[MONITORING_TYPE]": "routine program monitoring",
            "[COMPLIANCE_OR_TESTING_STATUS]": "no adverse compliance concern documented in this draft",
            "[ONGOING_RECOMMENDATIONS]": intake_context["aftercare_plan_summary"],
            "[COPY FROM DX BOX]": intake_context["diagnosis_summary"],
            "[SEE TABLE BELOW]": intake_context["aftercare_plan_summary"],
            "[VERBATIM DISCHARGE / MOTIVATION QUOTE]": "I need structure that helps me keep moving forward.",
            "[VERBATIM CLIENT QUOTE THIS WEEK]": "I need structure that helps me keep moving forward.",
            "[VERBATIM TOPIC-RELATED QUOTE]": "I need structure that helps me keep moving forward.",
            "[VERBATIM CLIENT QUOTE]": "I need structure that helps me keep moving forward.",
            "[VERBATIM CLIENT QUOTE — strengths]": "I am motivated and I keep showing up.",
            "[VERBATIM CLIENT QUOTE — weaknesses]": "I need help managing triggers and transportation.",
            "[VERBATIM CLIENT QUOTE — discharge goals]": "I want to stay sober, work, and keep my housing stable.",
            "[Last Name]": "",
            "[LICENSE#]": "License number on file",
            "[License#]": "License number on file",
        }
        for placeholder, default in general_defaults.items():
            filled = filled.replace(placeholder, default)

        return filled

    def _build_selected_template_fallback(self, payload: Dict[str, Any], current_text: str) -> str:
        """Draft from the exact selected template body when OpenAI is unavailable."""
        prompt = (payload.get("user_prompt") or "").strip()
        if not current_text:
            return ""

        context = payload.get("context") or {}
        note_kind = payload.get("note_kind", "progress_note")
        if self._is_evidence_bound_template(note_kind, context):
            return self._build_evidence_bound_template_fallback(payload, current_text)

        template_label = context.get("template_label") or payload.get("note_kind", "Documentation").replace("_", " ").title()
        current_date = datetime.now().strftime("%B %d, %Y")
        draft = current_text.strip()
        draft = self._auto_fill_placeholders(draft, payload.get("client_id"), payload.get("client_name"))

        grounded_context = [
            "CLIENT CONTEXT:",
            prompt or "Case manager should complete this draft using verified client facts only.",
            "",
            "NEXT STEP:",
            "Case manager will review the generated draft, verify all AI-filled defaults and dates, and add any missing client-specific details before saving or sending.",
        ]
        context_block = "\n".join(grounded_context)

        if re.search(r"\n\s*Sincerely,?", draft, flags=re.IGNORECASE):
            draft = re.sub(
                r"\n\s*Sincerely,?",
                f"\n\n{context_block}\n\nSincerely,",
                draft,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            draft = f"{draft}\n\n{context_block}"

        header = f"Template: {template_label}\nDate generated: {current_date}\n\n"
        return self._strip_placeholder_staff_signature(f"{header}{draft}".strip())

    def _build_fallback_draft(self, payload: Dict[str, Any], recent_notes: List[Dict[str, Any]]) -> str:
        """Build a complete template-style draft using bracket placeholders and real client data."""
        note_kind = payload.get("note_kind", "progress_note")
        sections = FALLBACK_SKELETONS.get(note_kind, FALLBACK_SKELETONS["progress_note"])
        prompt = (payload.get("user_prompt") or "").strip()
        current_text = (payload.get("current_text") or "").strip()
        selected_template_draft = self._build_selected_template_fallback(payload, current_text)
        if selected_template_draft:
            return selected_template_draft

        context = payload.get("context") or {}
        if self._is_evidence_bound_template(note_kind, context):
            return self._strip_placeholder_staff_signature(selected_template_draft or self._build_evidence_bound_template_fallback(payload, current_text))

        direct_quotes = context.get("direct_quotes") or []
        observations = context.get("observations") or ""
        client_name = payload.get("client_name") or "[CT NAME]"
        current_date = datetime.now().strftime("%B %d, %Y")
        current_time = "2:00 PM"
        next_week_date = (datetime.now() + timedelta(days=7)).strftime("%B %d, %Y")

        # Get comprehensive client data for intelligent fallback
        client_id = payload.get("client_id")
        comprehensive_data = self._get_comprehensive_client_data(client_id) if client_id else {}
        case_mgmt_data = comprehensive_data.get('case_management', {})

        # Build complete template-formatted content
        output: List[str] = []

        for heading, body in sections:
            output.append(f"{heading}:")
            section_text = body

            # Generate full, template-formatted content for each section
            if heading in {"RESPONSE", "STATUS / RESPONSE", "CLIENT RESPONSE"}:
                # Follow the CM-ONGOING-01 template format with real client data
                section_parts = []

                # Add discussion paragraph
                if prompt:
                    section_parts.append(f"CM and client discussed {prompt}.")
                else:
                    section_parts.append("CM and client discussed aftercare plans, which is an ongoing conversation.")

                # Add client demographic and history paragraph (like template shows)
                section_parts.append(
                    f"Client is a [AGE]-year-old [RACE], [GENDER] with a history of [SUBSTANCES / PRESENTING CONCERNS]. "
                    f"Current housing: [HOUSING STATUS]. Employment: [EMPLOYMENT STATUS]. Legal: [LEGAL STATUS]."
                )

                # Add barriers/progress from database if available
                if case_mgmt_data.get('barriers'):
                    section_parts.append(f"Current barriers include: {case_mgmt_data.get('barriers')}.")
                if case_mgmt_data.get('goals'):
                    section_parts.append(f"Client goals: {case_mgmt_data.get('goals')}.")

                # Add verbatim quote placeholder
                if direct_quotes:
                    section_parts.append(f"Client stated, \"{direct_quotes[0]}\".")
                else:
                    section_parts.append("Client stated, \"[VERBATIM CLIENT QUOTE THIS WEEK]\".")

                # Add any additional current text
                if current_text:
                    section_parts.append(current_text)

                # Add continuity statement
                section_parts.append("CM and client will continue making progress toward discharge plans and treatment plan goals.")

                section_text = " ".join(section_parts)

            elif heading in {"INTERVENTION", "ACTION TAKEN"}:
                # Follow CM-ONGOING-01 template format
                section_text = (
                    "CM validated client's feelings and addressed concerns.\n"
                    "CM addressed immediate needs.\n"
                    "CM assessed for financial stability.\n"
                    "CM inquired about legal issues and FMLA.\n"
                    "CM inquired about discharge planning.\n"
                    "CM asked about 12-step / sponsor involvement.\n"
                    "CM continued to encourage client to engage in groups and 1:1 sessions with TH and CM.\n"
                    "CM used open-ended questions, positive affirmations, motivational interviewing, reflection, and enduring questions."
                )

            elif heading in {"PLAN", "NEXT STEP", "FOLLOW-UP"}:
                # Follow CM-ONGOING-01 template
                section_text = (
                    f"CM will continue to meet with the client on a weekly basis to solidify a discharge treatment plan. "
                    f"Client's tentative step-down / discharge date: [DATE]."
                )

            elif heading == "GOAL":
                # Follow CM-ONGOING-01 template
                section_text = (
                    "To discuss and plan a comprehensive discharge from treatment. "
                    "Identify any needs for transition including sober living, aftercare, and financial stability."
                )

            elif heading in {"GROUP TOPIC"}:
                group_topic = context.get("group_topic") or "[Coping Skills/Relapse Prevention/Anger Management/Life Skills/Recovery Support]"
                section_text = (
                    f"Today's group focused on: {group_topic}. "
                    f"Session objectives included: [skill building/peer support/psychoeducation/community building]. "
                    f"Duration: [60/90] minutes. Attendance: [number] clients."
                )

            elif heading in {"PROBLEM"}:
                section_text = (
                    f"Client presents with [specific functional impairment/barrier/treatment need] that impacts [daily functioning/recovery/stability/goal achievement]. "
                    f"Current challenges include: [concrete observable issues]. "
                    f"This problem affects client's ability to: [specific functional outcomes]."
                )

            elif heading in {"OBJECTIVE"}:
                section_text = (
                    f"Client will [specific measurable action] at least [number] times per [week/month] for the next [30/60/90] days. "
                    f"Progress will be measured by: [specific observable indicator]. "
                    f"Target achievement date: [specific date]. "
                    f"Client will demonstrate progress by: [concrete behavioral outcome]."
                )

            elif heading in {"NEXT REVIEW", "REVIEW TIMELINE"}:
                section_text = (
                    f"Treatment plan will be reviewed on [specific date], approximately [30/60/90] days from today. "
                    f"Progress indicators to be assessed: [list specific outcomes]. "
                    f"Review will include: client self-report, staff observations, and measurable data on [specific metrics]. "
                    f"Plan will be updated based on: goal achievement, barrier resolution, and client feedback."
                )

            elif heading in {"REFERRAL NEED"}:
                section_text = (
                    f"Client requires referral to [specific service type/provider] to address [presenting barrier/need]. "
                    f"Clinical/case management rationale: [why this referral is indicated now]. "
                    f"Expected outcome: [what this referral should accomplish]. "
                    f"Urgency level: [routine/priority/urgent]."
                )

            elif heading in {"PURPOSE"}:
                section_text = (
                    f"This contact addresses FMLA documentation required for [client's leave/return to work/intermittent leave/certification renewal]. "
                    f"Employer: [Company Name]. Leave dates: [start date] through [end date or ongoing]. "
                    f"Current packet status: [initial certification/recertification/extension request/provider follow-up]."
                )

            elif heading in {"CONTACT"}:
                contact_party = context.get("contact_party") or "[HR Representative Name/Provider Name/Client]"
                contact_method = context.get("contact_method") or "[phone/email/fax/in-person]"
                section_text = (
                    f"Date: {current_date} at {current_time}. "
                    f"Contact method: {contact_method}. "
                    f"Party contacted: {contact_party} at [organization/phone number]. "
                    f"Purpose: [certification request/clarification/deadline extension/status update]."
                )

            elif heading in {"SUMMARY"}:
                section_text = (
                    f"Case manager [requested/clarified/confirmed/submitted] [specific FMLA documentation element]. "
                    f"Information provided: [what was given to employer/provider/client]. "
                    f"Information received: [what was confirmed or learned]. "
                    f"Outstanding items discussed: [pending signatures/medical opinions/deadline extensions]."
                )

            elif heading in {"OUTCOME"}:
                section_text = (
                    f"Result of contact: [certification approved/additional information requested/deadline extended/packet returned incomplete]. "
                    f"Next required action identified: [specific task]. "
                    f"Responsible party: [case manager/client/provider/HR]. "
                    f"Confirmed deadline: [specific date]."
                )

            elif heading in {"DISCHARGE STATUS"}:
                section_text = "Summarize current stability, readiness, and major progress. [Describe client's current functional status and treatment completion]."

            elif heading in {"SERVICES PROVIDED", "SERVICES COMPLETED"}:
                section_text = "List key interventions, referrals, and supports arranged. [Document weekly CM/TH sessions, group programming, medication management, aftercare coordination completed]."

            elif heading in {"BARRIERS / RISKS", "OUTSTANDING RISKS"}:
                section_text = "Document unresolved barriers, relapse risks, or social needs. [List housing instability, legal obligations, employment gaps, treatment continuity needs, transportation barriers, or other risks requiring monitoring]."

            elif heading in {"AFTERCARE PLAN"}:
                section_text = (
                    "Housing: [confirmed placement/pending application/ongoing search at specific location]. Move-in date: [DATE].\n"
                    "Treatment: Confirmed intake at [PROVIDER NAME] on [DATE/TIME]. Contact: [PHONE].\n"
                    "Employment: [job placement/job search support/vocational referral] scheduled for [DATE].\n"
                    "Benefits: [SNAP/Medicaid/SSI] status confirmed. Next review: [DATE].\n"
                    "Legal: Probation check-in scheduled for [DATE]. Court date: [DATE].\n"
                    "Transportation: [bus pass/ride support/client plan].\n"
                    "Follow-up appointments: [List 3-5 specific appointments with dates, times, providers, phone numbers]."
                )

            output.append(section_text)
            output.append("")

        # Add MEDICAL section for case manager notes
        if note_kind in {"progress_note", "initial_note"}:
            output.append("MEDICAL:")
            output.append("Client will stabilize on all medications as prescribed and comply with physician's orders. No intervention needed at this time.")
            output.append("")

        # Add signature block following template format
        output.append(f"[CM NAME], Case Manager [CM CREDENTIALS] [CM LICENSE #]")
        output.append(f"Date: {current_date}")

        draft = "\n".join(output).strip()
        # Auto-fill all placeholders with real data
        return self._strip_placeholder_staff_signature(
            self._auto_fill_placeholders(draft, payload.get("client_id"), payload.get("client_name"))
        )

    def _build_suggested_tasks(self, payload: Dict[str, Any], draft: str, review: Dict[str, Any]) -> List[Dict[str, Any]]:
        due_date = (datetime.now() + timedelta(days=3)).date().isoformat()
        note_kind = payload.get("note_kind", "progress_note")
        tasks: List[Dict[str, Any]] = []
        context = payload.get("context") or {}

        if note_kind == "treatment_plan":
            tasks.append({
                "title": "Review treatment plan follow-up",
                "description": "Update treatment plan goals and confirm progress documentation is current.",
                "priority": "medium",
                "task_type": "treatment_plan_review",
                "due_date": due_date,
            })
        elif note_kind.startswith("fmla"):
            paperwork_deadline = context.get("paperwork_deadline") or payload.get("paperwork_deadline")
            tasks.append({
                "title": "Review FMLA documentation follow-up",
                "description": "Confirm paperwork status, outstanding signatures, and employer/provider follow-up.",
                "priority": "high",
                "task_type": "documentation_follow_up",
                "due_date": paperwork_deadline or due_date,
            })
        else:
            tasks.append({
                "title": "Follow up on documentation next steps",
                "description": "Review note follow-up items and update client tasks based on documentation.",
                "priority": "medium",
                "task_type": "documentation_follow_up",
                "due_date": due_date,
            })

        if review.get("missing_intervention"):
            tasks.append({
                "title": "Clarify intervention details in documentation",
                "description": "Update the note to include the intervention completed during contact.",
                "priority": "medium",
                "task_type": "documentation_cleanup",
                "due_date": due_date,
            })
        if review.get("missing_next_step"):
            tasks.append({
                "title": "Set explicit next step from documentation",
                "description": "Add a follow-up action and deadline based on the generated documentation.",
                "priority": "medium",
                "task_type": "documentation_follow_up",
                "due_date": due_date,
            })
        return tasks[:3]

    @staticmethod
    def _extract_unresolved_placeholders(text: str) -> List[str]:
        seen = set()
        placeholders: List[str] = []
        for raw_placeholder in re.findall(r"\[([^\]]+)\]", text or ""):
            placeholder = re.sub(r"\s+", " ", raw_placeholder).strip()
            if placeholder in {"", " ", "x", "X", "☑"}:
                continue
            if not placeholder or placeholder in seen:
                continue
            seen.add(placeholder)
            placeholders.append(placeholder)
        return placeholders

    def _build_template_quality_review(self, text: str, note_kind: str, context: Dict[str, Any]) -> Dict[str, Any]:
        contract = self.resolve_template_contract(note_kind, context)
        template_label = (context or {}).get("template_label") or contract.get("template_label") or ""
        anchors = TEMPLATE_QUALITY_ANCHORS.get(template_label) or NOTE_KIND_QUALITY_ANCHORS.get(note_kind, [])
        missing_anchors = [
            pattern
            for pattern in anchors
            if not re.search(pattern, text or "", flags=re.IGNORECASE | re.MULTILINE)
        ]
        forbidden_sections_found = [
            pattern
            for pattern in contract.get("forbidden_patterns", [])
            if re.search(pattern, text or "", flags=re.IGNORECASE | re.MULTILINE)
        ]

        unresolved_placeholders = self._extract_unresolved_placeholders(text)
        data_warnings = []
        for placeholder in unresolved_placeholders:
            upper_placeholder = placeholder.upper()
            for key, message in DATA_PLACEHOLDER_WARNINGS.items():
                if key in upper_placeholder and message not in data_warnings:
                    data_warnings.append(message)

        quote_placeholders = [
            placeholder
            for placeholder in unresolved_placeholders
            if any(term in placeholder.upper() for term in QUOTE_PLACEHOLDER_TERMS)
        ]
        placeholder_staff_signature = [
            term
            for term in PLACEHOLDER_STAFF_SIGNATURE_TERMS
            if term.lower() in (text or "").lower()
        ]

        score = 100
        score -= len(missing_anchors) * 12
        score -= len(forbidden_sections_found) * 14
        score -= len(unresolved_placeholders) * 10
        score -= len(data_warnings) * 4
        score -= len(placeholder_staff_signature) * 8
        score = max(0, min(100, score))

        if missing_anchors or forbidden_sections_found or len(unresolved_placeholders) >= 3 or score < 70:
            status = "needs_revision"
        elif data_warnings or unresolved_placeholders or placeholder_staff_signature or score < 90:
            status = "needs_review"
        else:
            status = "pass"

        warnings = []
        if missing_anchors:
            warnings.append("Draft may not be following the selected template structure.")
        if forbidden_sections_found:
            warnings.append("Draft contains headings or phrasing that are forbidden for the selected template.")
        if unresolved_placeholders:
            warnings.append("Draft still contains unresolved placeholders that need review.")
        if quote_placeholders:
            warnings.append("Draft still needs case-manager quote verification.")
        if placeholder_staff_signature:
            warnings.append("Draft still contains placeholder staff signature or credential text.")
        warnings.extend(data_warnings)

        return {
            "template_label": template_label or note_kind.replace("_", " ").title(),
            "score": score,
            "status": status,
            "missing_template_anchors": missing_anchors,
            "forbidden_sections_found": forbidden_sections_found,
            "unresolved_placeholders": unresolved_placeholders,
            "quote_placeholders": quote_placeholders,
            "placeholder_staff_signature": placeholder_staff_signature,
            "data_warnings": data_warnings,
            "warnings": warnings,
        }

    def compliance_review(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        text = (payload.get("content") or payload.get("draft") or "").strip()
        lowered = text.lower()
        note_kind = payload.get("note_kind", "progress_note")
        context = payload.get("context") or {}
        warnings: List[str] = []
        quality_review = self._build_template_quality_review(text, note_kind, context)

        missing_intervention = "intervention" not in lowered and "action taken" not in lowered
        missing_response = "response" not in lowered and "client response" not in lowered and "status / response" not in lowered
        missing_next_step = "plan" not in lowered and "next step" not in lowered and "follow-up" not in lowered

        if missing_intervention:
            warnings.append("Missing intervention or action taken.")
        if missing_response:
            warnings.append("Missing client response or status update.")
        if missing_next_step:
            warnings.append("Missing next step or follow-up plan.")
        if not re.search(r"\b(client stated|client reported|client shared|ct stated)\b", lowered):
            warnings.append("Consider documenting the client voice or a direct statement.")
        for pattern in VAGUE_LANGUAGE_PATTERNS:
            if re.search(pattern, lowered):
                warnings.append("Vague language detected. Consider adding observable detail.")
                break

        if note_kind == "treatment_plan":
            if "goal" not in lowered:
                warnings.append("Treatment plan is missing a clearly labeled goal.")
            if "objective" not in lowered:
                warnings.append("Treatment plan is missing an objective.")
            if not re.search(r"\b(by|within|weekly|monthly|times per week|target date)\b", lowered):
                warnings.append("Treatment plan objective may not be SMART. Add timeframe or measurable target.")

        if note_kind == "group_note":
            if not context.get("group_topic"):
                warnings.append("Group note is missing the documented group topic.")
            if not context.get("attendance"):
                warnings.append("Group note is missing attendance details.")
            if not context.get("participation_level"):
                warnings.append("Group note is missing participation level.")

        return {
            "warnings": warnings,
            "missing_intervention": missing_intervention,
            "missing_response": missing_response,
            "missing_next_step": missing_next_step,
            "is_complete": len(warnings) == 0,
            "quality_review": quality_review,
            }

    def generate_treatment_plan_suggestions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        from datetime import datetime, timedelta

        recent_notes = self._get_recent_note_context(payload.get("client_id"))
        context = payload.get("context") or {}

        # Pull from top-level payload fields first, fall back to context dict
        def _get(key: str, default: str = "") -> str:
            return (payload.get(key) or context.get(key) or default).strip()

        strengths = _get("strengths")
        weaknesses = _get("weaknesses")
        reason_for_treatment = _get("reason_for_treatment")
        discharge_plan = _get("discharge_plan")
        level_of_care = _get("level_of_care", "IOP")
        projected_los = _get("projected_los", "30-45 days")
        admit_date_raw = _get("admit_date")
        education = _get("education")
        aftercare_plan = _get("aftercare_plan")
        legal_needs = _get("legal_needs")
        medical_needs = _get("medical_needs")
        housing_status = _get("housing_status")
        employment_status = _get("employment_status")
        legal_status = _get("legal_status")
        medical_conditions = _get("medical_conditions")
        case_manager_name = _get("case_manager_name", "Case Manager")
        client_goals = _get("client_goals") or _get("goals")
        barriers = _get("barriers")
        needs = context.get("needs") or []

        today = datetime.now()
        review_date = today.strftime("%m/%d/%Y")

        try:
            admit_dt = datetime.strptime(admit_date_raw, "%Y-%m-%d") if admit_date_raw else today
        except ValueError:
            admit_dt = today
        admit_display = admit_dt.strftime("%m/%d/%Y")
        target_dt = admit_dt + timedelta(weeks=4)
        target_date = target_dt.strftime("%m/%d/%Y")

        # Level of care display flags
        loc_upper = level_of_care.upper()
        loc_options = {"PHP": loc_upper == "PHP", "IOP": loc_upper == "IOP", "OP": loc_upper == "OP"}
        if not any(loc_options.values()):
            loc_options["IOP"] = True

        freq_map = {"PHP": "1x1x4 weeks PHP", "IOP": "1x1x4 weeks IOP", "OP": "1x1x4 weeks OP"}
        frequency = freq_map.get(loc_upper, f"1x1x4 weeks {level_of_care}")

        # Discharge Planning goal — use client's own words where available
        goal_text_parts = ["Identify any 3 needs for aftercare, therapy, and primary care physician.",
                           "Identify any 3 needs for transition including sober living."]
        voice = discharge_plan or reason_for_treatment or client_goals
        if voice:
            goal_text_parts.append(f'CT stated "{voice}"')
        goal_text = " ".join(goal_text_parts)

        objective_text = (
            "CM will meet with CT weekly to discuss options for aftercare planning and explore high risk situations "
            "and motivation for maintaining sobriety. CM will educate CT on various sober support groups and the "
            "importance of building sober support networks."
        )

        plan_intro = (
            "CT to work on developing safe aftercare plans AEB reviewing sober support systems, exploring various "
            "sober support groups, reviewing potential outpatient programs, and procuring therapy and psychiatry "
            "referrals as appropriate."
        )

        plan_items = []
        if "housing" in needs or housing_status in ("Homeless", "Transitional") or "sober living" in (discharge_plan + aftercare_plan).lower():
            plan_items.append("CM will assist client in identifying sober living options to support stable housing upon discharge.")
        if "employment" in needs or employment_status in ("Unemployed", "Seeking"):
            plan_items.append("CM will provide client with employment resources and referrals in alignment with client's stated career goals.")
        if "legal" in needs or legal_status not in ("No Active Cases", "", None) or legal_needs:
            plan_items.append("CM will coordinate with client's probation/parole officer and provide monthly progress reports as required.")
        if medical_needs or medical_conditions:
            plan_items.append("CM will assist client in identifying medical resources and coordinate appointments to address client's identified health needs.")
        if education:
            plan_items.append("CM will assist client in exploring education and vocational training opportunities aligned with stated goals.")
        plan_items.append("Client will attend a minimum of three AA/NA meetings per week to build sober support network.")

        problems = [
            {
                "number": 1,
                "title": "Discharge Planning",
                "goal": goal_text,
                "objective": objective_text,
                "plan_intro": plan_intro,
                "plan_items": plan_items,
                "frequency": frequency,
                "target_date": target_date,
                "status": "open",
                "outcome": "in progress",
                "comment": "initial goal developed",
            }
        ]

        progress_summary = "No recent notes available to summarize."
        if recent_notes:
            progress_summary = " ".join(
                f"{note.get('note_type', 'Note')}: {(note.get('content', '') or '')[:140]}"
                for note in recent_notes[:2]
            )

        return {
            "level_of_care": loc_upper if any(loc_options.values()) else "IOP",
            "loc_options": loc_options,
            "review_date": review_date,
            "case_manager_name": case_manager_name,
            "admit_date": admit_display,
            "projected_los": projected_los,
            "client_strengths": strengths,
            "client_weaknesses": weaknesses,
            "reason_for_treatment": reason_for_treatment,
            "discharge_plan_stated": discharge_plan,
            "education": education,
            "aftercare_plan": aftercare_plan,
            "problems": problems,
            "progress_summary": progress_summary,
            # Backward-compat fields
            "goal": goal_text,
            "objective": objective_text,
            "interventions": plan_items,
            "smart_formatting_help": [
                "Specific: name the service area or functional issue being addressed.",
                "Measurable: include a count, deadline, or review frequency.",
                "Achievable: keep the objective realistic for the current level of stability.",
                "Relevant: tie the objective to housing, employment, legal, benefits, health, or recovery needs.",
                "Time-bound: include a target date or review cadence.",
            ],
            "needs_considered": needs,
        }

    async def generate_group_note(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        context = payload.get("context") or {}
        note_payload = {
            **payload,
            "note_kind": "group_note",
            "user_prompt": payload.get("user_prompt") or f"Generate a group note for topic {context.get('group_topic', 'group session')}",
        }
        draft_result = await self.generate_note_draft(note_payload)
        return {
            **draft_result,
            "group_topic": context.get("group_topic", ""),
            "attendance": context.get("attendance", ""),
            "participation_level": context.get("participation_level", ""),
        }

    async def generate_note_from_transcript(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        client_id = payload.get("client_id")
        transcript = (payload.get("transcript") or "").strip()
        note_type = payload.get("note_type", "cm_note")
        if not transcript:
            raise ValueError("Transcript is required")

        comprehensive_data = self._get_comprehensive_client_data(client_id) if client_id else {}
        core_data = comprehensive_data.get("core", {})
        case_mgmt_data = comprehensive_data.get("case_management", {})

        first_name = core_data.get("first_name") or case_mgmt_data.get("first_name") or ""
        last_name = core_data.get("last_name") or case_mgmt_data.get("last_name") or ""
        client_name = f"{first_name} {last_name}".strip() or "CT"
        current_date = datetime.now().strftime("%B %d, %Y")

        fallback_note = "\n".join(
            [
                "GOAL:",
                "Document the client contact and summarize the issues discussed based only on the dictated transcript.",
                "",
                "INTERVENTION:",
                "Case manager reviewed the client's stated needs, concerns, and requested follow-up items from the dictated transcript.",
                "",
                "RESPONSE:",
                f"CT reported the following during the contact: {transcript}",
                "",
                "PLAN:",
                "Case manager will review the transcript, confirm accuracy with CT as needed, and complete follow-up based only on documented facts.",
                "",
                f"Date: {current_date}",
            ]
        )

        if not self.client:
            return {
                "draft": fallback_note,
                "source": "template_fallback",
                "transcript": transcript,
                "note_type": note_type,
            }

        prompt = [
            "You are generating a professional SUD case management note from a dictated transcript.",
            "Use only the facts explicitly provided in the transcript and client profile context below.",
            "Do not invent services, appointments, diagnoses, referrals, legal details, medications, or outcomes.",
            "Refer to the client as CT unless the provided template clearly requires something else.",
            "If a detail is missing, omit it rather than guessing.",
            "",
            f"Note type: {note_type}",
            f"Date: {current_date}",
            f"Client reference: {client_name}",
            "",
            "Client profile context:",
            f"- Housing status: {case_mgmt_data.get('housing_status', 'Unknown')}",
            f"- Employment status: {case_mgmt_data.get('employment_status', 'Unknown')}",
            f"- Legal status: {case_mgmt_data.get('legal_status', 'Unknown')}",
            "",
            "Transcript:",
            transcript,
            "",
            "Output requirements:",
            "- Produce a professional case management note with clear headings.",
            "- Include only facts grounded in the transcript.",
            "- Keep the note clinically neutral and documentation-ready.",
            "- Do not include any disclaimer or commentary outside the note.",
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                max_tokens=900,
                messages=[
                    {
                        "role": "system",
                        "content": "You draft accurate case management documentation from dictated transcripts without adding unstated facts.",
                    },
                    {"role": "user", "content": "\n".join(prompt)},
                ],
            )
            draft = (response.choices[0].message.content or "").strip() or fallback_note
            return {
                "draft": draft,
                "source": "openai",
                "transcript": transcript,
                "note_type": note_type,
            }
        except Exception as exc:
            logger.warning("Transcript note generation failed, using fallback: %s", exc)
            return {
                "draft": fallback_note,
                "source": "template_fallback",
                "transcript": transcript,
                "note_type": note_type,
            }

    async def generate_note_draft(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        provider_status = self._refresh_provider_client()
        recent_notes = self._get_recent_note_context(payload.get("client_id"))
        selected_template_body = (payload.get("current_text") or "").strip()
        library_excerpt = self._get_template_excerpt(payload.get("note_kind", "progress_note"))
        template_excerpt = selected_template_body or library_excerpt
        fallback_draft = self._build_fallback_draft(payload, recent_notes)
        review = self.compliance_review(
            {
                "draft": fallback_draft,
                "note_kind": payload.get("note_kind", "progress_note"),
                "context": payload.get("context") or {},
            }
        )

        template_context = payload.get("context") or {}
        contract = self.resolve_template_contract(payload.get("note_kind", "progress_note"), template_context)

        if not self.client:
            logger.info(
                "Documentation draft using structured fallback; provider unavailable. template=%s note_kind=%s reason=%s client_selected=%s",
                contract.get("template_label"),
                payload.get("note_kind", "progress_note"),
                provider_status.get("reason"),
                bool(payload.get("client_id")),
            )
            return {
                "draft": fallback_draft,
                "source": "template_fallback",
                "template_excerpt": template_excerpt,
                "compliance_preview": review,
                "quality_review": review.get("quality_review"),
                "suggested_tasks": self._build_suggested_tasks(payload, fallback_draft, review),
                "provider_status": provider_status,
            }

        # Pull comprehensive client data for intelligent auto-population
        client_id = payload.get("client_id")
        comprehensive_data = self._get_comprehensive_client_data(client_id) if client_id else {}
        core_data = comprehensive_data.get('core', {})
        case_mgmt_data = comprehensive_data.get('case_management', {})
        intake_context = self._build_shared_intake_context(comprehensive_data, client_name=payload.get("client_name"))
        recent_case_notes = comprehensive_data.get('recent_notes', [])

        user_prompt = (payload.get("user_prompt") or "").strip()
        client_name = payload.get("client_name") or "[Client Name]"
        note_kind = payload.get("note_kind", "progress_note")
        template_label = template_context.get("template_label", note_kind.replace("_", " ").title())
        template_category = template_context.get("template_category", "")
        evidence_bound = self._is_evidence_bound_template(note_kind, template_context)
        template_guardrails = self._build_template_guardrails(note_kind, template_context)
        current_date = datetime.now().strftime("%B %d, %Y")
        reference_guidance_context = self._get_reference_library_context(
            query=user_prompt or payload.get("current_text") or note_kind,
            note_kind=note_kind,
        )
        brand_guidance_context = self.get_brand_guidance_context(
            query=user_prompt or payload.get("current_text") or note_kind,
            note_kind=note_kind,
            case_manager_id=payload.get("case_manager_id") or DEFAULT_CASE_MANAGER_ID,
        )

        # Build comprehensive client context for AI
        client_context_parts = []
        if core_data or case_mgmt_data:
            full_name = intake_context["full_name"] or client_name

            # Calculate age
            age_str = "unknown age"
            dob = intake_context.get("date_of_birth")
            if dob:
                try:
                    dob_date = datetime.strptime(dob, '%Y-%m-%d')
                    age = (datetime.now() - dob_date).days // 365
                    age_str = f"{age} years old"
                except:
                    pass

            # Gather all available client information
            gender = intake_context["gender"]
            race = intake_context["race"]
            housing_status = intake_context["housing_status"]
            employment_status = intake_context["employment_status"]
            legal_status = intake_context["legal_status"]
            substance_history = intake_context["substance_history"] or "No documented substance history"
            mental_health = intake_context["mental_health"] or "Unknown mental health status"
            barriers = intake_context["barriers"] or "No documented barriers"
            goals = intake_context["goals"] or "No documented goals"

            client_context_parts.append(f"CLIENT PROFILE (from database):")
            client_context_parts.append(f"• Name: {full_name}")
            client_context_parts.append(f"• Demographics: {age_str}, {gender}, {race}")
            client_context_parts.append(f"• Housing: {housing_status}")
            client_context_parts.append(f"• Employment: {employment_status}")
            client_context_parts.append(f"• Legal: {legal_status}")
            client_context_parts.append(f"• Substance History: {substance_history}")
            client_context_parts.append(f"• Mental Health: {mental_health}")
            client_context_parts.append(f"• Current Barriers: {barriers}")
            client_context_parts.append(f"• Goals: {goals}")
            client_context_parts.append(f"- Record number: {intake_context['client_record_number']}")
            client_context_parts.append(f"- Admission/intake date: {intake_context['admission_date'] or intake_context['intake_date'] or 'not documented'}")
            client_context_parts.append(f"- Residence/address: {intake_context['residence_address'] or 'not documented'}")
            client_context_parts.append(f"- Program type: {intake_context['program_type'] or 'not documented'}")
            client_context_parts.append(f"- Benefits: {intake_context['benefits_status']}")
            client_context_parts.append(f"- Prior convictions/legal intake: {intake_context['prior_convictions'] or 'none documented'}")
            client_context_parts.append(f"- Medical conditions: {intake_context['medical_conditions'] or 'none documented'}")
            client_context_parts.append(f"- Special needs: {intake_context['special_needs'] or 'none documented'}")
            client_context_parts.append(f"- Transportation: {intake_context['transportation'] or 'not documented'}")
            client_context_parts.append(f"- Treatment plan summary: {intake_context['treatment_plan_summary']}")
            client_context_parts.append(f"- Aftercare plan summary: {intake_context['aftercare_plan_summary']}")
            client_context_parts.append(f"- Diagnosis: {intake_context['diagnosis_summary']}")
            client_context_parts.append(f"- Profile notes: {intake_context['notes'] or 'none documented'}")
        else:
            client_context_parts.append(f"CLIENT: {client_name} (limited data available)")

        if evidence_bound and (core_data or case_mgmt_data):
            full_name = intake_context["full_name"] or client_name
            client_context_parts = [
                "CLIENT PROFILE (from database):",
                f"- Name: {full_name}",
                f"- Record number: {intake_context['client_record_number']}",
                "- Use client profile for identity only. Do not introduce extra services, symptoms, diagnoses, goals, plans, or history unless they are explicitly supported by the case manager brief or form data.",
            ]

        # Add recent notes context
        if recent_case_notes and not evidence_bound:
            client_context_parts.append("")
            client_context_parts.append("RECENT CASE NOTES (for continuity):")
            for note in recent_case_notes[:3]:
                note_date = note.get('created_at', 'Unknown date')
                note_type = note.get('note_type', 'Note')
                content_preview = (note.get('content', '') or '')[:150]
                client_context_parts.append(f"  - {note_date} ({note_type}): {content_preview}...")
                if note.get('barriers_identified'):
                    client_context_parts.append(f"    Barriers: {note.get('barriers_identified')}")
                if note.get('action_items'):
                    client_context_parts.append(f"    Actions: {note.get('action_items')}")

        # Inject form context provided by the case manager as the authoritative source
        form_context = payload.get("context") or {}
        form_context_parts = []
        field_labels = {
            "goals": "Client Goals",
            "barriers": "Identified Barriers",
            "strengths": "Client Strengths (CT's own words)",
            "weaknesses": "Client Weaknesses (CT's own words)",
            "reason_for_treatment": "Reason for Treatment (CT's own words)",
            "discharge_plan": "Discharge Plans (CT's own words)",
            "aftercare_plan": "Aftercare Plan",
            "education": "Education",
            "level_of_care": "Level of Care",
            "projected_los": "Projected Length of Stay",
            "legal_needs": "Legal Needs",
            "medical_needs": "Medical Needs",
            "substance_abuse_history": "Substance Abuse History",
            "mental_health_status": "Mental Health Status",
            "medical_conditions": "Medical Conditions",
            "prior_convictions": "Prior Convictions",
            "referral_source": "Referral Source",
            "program_type": "Program Type",
            "observations": "Status Summary",
        }
        for key, label in field_labels.items():
            val = form_context.get(key, "")
            if val:
                form_context_parts.append(f"• {label}: {val}")

        if form_context_parts:
            client_context_parts.append("")
            client_context_parts.append("INTAKE FORM DATA (entered by case manager — use this as authoritative source):")
            client_context_parts.extend(form_context_parts)

        client_context_str = "\n".join(client_context_parts)

        prompt = [
            "You are an AI documentation assistant for a case management suite competing with professional tools like Twofold Health, Clinical Notes AI, and Mentalyc.",
            "",
            "CRITICAL INSTRUCTIONS:",
            "1. Use the template from the library below as your PRIMARY FORMAT",
            "2. Generate COMPLETE, FULLY-WRITTEN professional documentation using the INTAKE FORM DATA provided",
            "3. AUTO-FILL fields using the INTAKE FORM DATA — this is what the case manager actually entered",
            "4. NEVER invent demographics (age, race, ethnicity, gender, children, marital status) unless explicitly stated in the data",
            "5. NEVER invent substance history, legal history, or diagnoses beyond what is documented",
            "6. If a field is not in the provided data, omit it or write 'not documented' — do not fabricate",
            "7. When the client's own words are provided (strengths, weaknesses, reason for treatment, discharge plans), quote them directly using 'CT stated'",
            "8. Write full narrative paragraphs using ONLY documented facts",
            "9. Follow the EXACT structure and formatting from the selected template",
            "10. Follow organization-specific guidance materials when they are provided below",
            "11. For evidence-bound case-management notes, use the case manager brief as the primary evidence source and keep unsupported details out of the draft",
            "",
            f"SELECTED TEMPLATE: {template_label}",
            f"TEMPLATE CATEGORY: {template_category}",
            "PRIMARY TEMPLATE TO FOLLOW EXACTLY:",
            "─────────────────────────────────────────────────────────────",
            template_excerpt or "No template available.",
            "─────────────────────────────────────────────────────────────",
            "",
            "REFERENCE LIBRARY CONTEXT:",
            library_excerpt or "No additional library context available.",
            "",
            reference_guidance_context or "No internal playbook or reference-library context matched this draft.",
            "",
            client_context_str,
            "",
            brand_guidance_context or "No organization-specific guidance documents are currently uploaded.",
            "",
            "CASE MANAGER'S NOTES FOR THIS SESSION:",
            f"• User provided: {user_prompt or '(Case manager has not provided session notes yet - use recent history to fill template)'}",
            f"• Date: {current_date}",
            f"• Note type: {note_kind.replace('_', ' ')}",
            "",
            "INSTRUCTIONS:",
            "- Copy the SELECTED TEMPLATE format EXACTLY as shown above",
            "- Do NOT switch to a treatment plan or CM note format unless the selected template is actually that format",
            "- Fill fields using INTAKE FORM DATA first, then CLIENT PROFILE data as supplement",
            "- Use the client profile for identity only unless the case manager brief or form data explicitly supports additional facts",
            "- For RESPONSE section: ONLY use demographics and history that are explicitly in the provided data — never assume race, age, gender, or background",
            "- If strengths/weaknesses/reason for treatment/discharge plans are provided, include them as direct CT quotes using 'CT stated'",
            "- If a data point is not documented, write 'not documented' rather than inventing a plausible value",
            "- If case manager provided session notes, incorporate them into the narrative",
            "- If no session notes were provided, write only what the template and provided data support. Use 'No additional information was provided.' where needed instead of inventing filler",
            "- If a client quote is available, use the exact quote. If not, write a complete sentence stating that no direct client quote was documented",
            "- Use professional case management language matching the template style",
            "- Make it documentation-ready without generic clinical filler, canned treatment-plan language, or placeholder signature blocks",
            "",
            "TEMPLATE GUARDRAILS:",
            *[f"- {instruction}" for instruction in template_guardrails],
            "",
            "Return ONLY the formatted note - no explanations, no meta-commentary.",
        ]
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=0.4,
                max_tokens=1200,
                messages=[
                    {"role": "system", "content": "You produce complete, client-specific case management documentation that requires minimal case manager editing. Auto-fill all available data from the client profile."},
                    {"role": "user", "content": "\n\n".join(prompt)},
                ],
            )
            draft = (response.choices[0].message.content or "").strip() or fallback_draft
            # Auto-fill all remaining placeholders with real client data
            draft = self._auto_fill_placeholders(draft, payload.get("client_id"), payload.get("client_name"))
            if evidence_bound:
                draft = self._strip_placeholder_staff_signature(draft)
            review = self.compliance_review(
                {
                    "draft": draft,
                    "note_kind": payload.get("note_kind", "progress_note"),
                    "context": payload.get("context") or {},
                }
            )
            logger.info(
                "Documentation draft generated with provider. template=%s note_kind=%s client_selected=%s",
                contract.get("template_label"),
                payload.get("note_kind", "progress_note"),
                bool(payload.get("client_id")),
            )
            return {
                "draft": draft,
                "source": "openai",
                "template_excerpt": template_excerpt,
                "compliance_preview": review,
                "quality_review": review.get("quality_review"),
                "suggested_tasks": self._build_suggested_tasks(payload, draft, review),
                "provider_status": provider_status,
            }
        except Exception as exc:
            logger.warning("Documentation AI draft generation failed, using fallback: %s", exc)
            return {
                "draft": fallback_draft,
                "source": "template_fallback",
                "template_excerpt": template_excerpt,
                "compliance_preview": review,
                "quality_review": review.get("quality_review"),
                "suggested_tasks": self._build_suggested_tasks(payload, fallback_draft, review),
                "provider_status": {**provider_status, "reason": exc.__class__.__name__},
            }

    def create_follow_up_task(self, client_id: str, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        return workspace_store.create_client_task(
            client_id,
            {
                "title": task_payload.get("title", "Documentation follow-up"),
                "description": task_payload.get("description", ""),
                "priority": task_payload.get("priority", "medium"),
                "status": "pending",
                "task_type": task_payload.get("task_type", "documentation_follow_up"),
                "due_date": task_payload.get("due_date"),
                "assigned_to": task_payload.get("assigned_to", "Case Manager"),
            },
        )


documentation_ai_service = DocumentationAIService()
