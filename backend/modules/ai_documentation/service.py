import logging
import os
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


class DocumentationAIService:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("OPENAI_DOCUMENTATION_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o"))
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        self.template_library_text = self._load_template_library()

    @staticmethod
    def _normalize_text(text: str, limit: int = 12000) -> str:
        normalized = re.sub(r"\s+", " ", (text or "")).strip()
        return normalized[:limit]

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
            with sqlite3.connect('databases/case_management.db') as conn:
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

        except Exception as exc:
            logger.warning("Error gathering comprehensive client data: %s", exc)

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
        return (
            "Internal documentation template library is available from UNIVERSAL_CM_TEMPLATES.md.\n"
            "Do not claim you lack access to templates or documentation guidance.\n"
            f"Relevant template category: {note_kind}.\n"
            f"Available template families: {available_templates}.\n"
            "Use this internal guidance before answering template or documentation questions.\n"
            "Relevant template excerpt:\n"
            f"{excerpt}"
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

        # Auto-fill client name variations
        if core_data or case_mgmt_data:
            first_name = core_data.get('first_name') or case_mgmt_data.get('first_name', '[CLIENT FIRST NAME]')
            last_name = core_data.get('last_name') or case_mgmt_data.get('last_name', '[CLIENT LAST NAME]')
            full_name = f"{first_name} {last_name}".strip()
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
        dob = core_data.get('date_of_birth') or case_mgmt_data.get('date_of_birth')
        if dob:
            try:
                dob_date = datetime.strptime(dob, '%Y-%m-%d')
                age = (datetime.now() - dob_date).days // 365
                age_str = str(age)
            except:
                pass

        # Get demographic and status information
        gender = case_mgmt_data.get('gender', '[GENDER]')
        race = case_mgmt_data.get('race', '[RACE]')
        housing_status = case_mgmt_data.get('housing_status', 'Unknown')
        employment_status = case_mgmt_data.get('employment_status', 'Unemployed')
        legal_status = case_mgmt_data.get('legal_status', 'No Active Cases')
        substance_history = case_mgmt_data.get('substance_abuse_history', 'No documented history')
        mental_health = case_mgmt_data.get('mental_health_status', 'Stable')
        prior_convictions = case_mgmt_data.get('prior_convictions', 'None documented')

        # Replace all client name placeholders
        filled = filled.replace("[CT NAME]", full_name)
        filled = filled.replace("[Client Name]", full_name)
        filled = filled.replace("[CLIENT NAME]", full_name)
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
        filled = filled.replace("[FACILITY NAME]", "Treatment Facility")

        return filled

    def _build_fallback_draft(self, payload: Dict[str, Any], recent_notes: List[Dict[str, Any]]) -> str:
        """Build a complete template-style draft using bracket placeholders and real client data."""
        note_kind = payload.get("note_kind", "progress_note")
        sections = FALLBACK_SKELETONS.get(note_kind, FALLBACK_SKELETONS["progress_note"])
        prompt = (payload.get("user_prompt") or "").strip()
        current_text = (payload.get("current_text") or "").strip()
        context = payload.get("context") or {}
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
        return self._auto_fill_placeholders(draft, payload.get("client_id"), payload.get("client_name"))

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

    def compliance_review(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        text = (payload.get("content") or payload.get("draft") or "").strip()
        lowered = text.lower()
        note_kind = payload.get("note_kind", "progress_note")
        context = payload.get("context") or {}
        warnings: List[str] = []

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
            }

    def generate_treatment_plan_suggestions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        recent_notes = self._get_recent_note_context(payload.get("client_id"))
        context = payload.get("context") or {}
        client_goal = context.get("client_goals") or payload.get("client_goals") or "Improve stability and functioning"
        barriers = context.get("barriers") or payload.get("barriers") or "Current barriers need further assessment"
        needs = context.get("needs") or []

        progress_summary = "No recent notes available to summarize."
        if recent_notes:
            progress_summary = " ".join(
                f"{note.get('note_type', 'Note')}: {(note.get('content', '') or '')[:140]}"
                for note in recent_notes[:2]
            )

        suggestions = {
            "goal": f"Client will make measurable progress toward {client_goal.lower()} while reducing the impact of current barriers.",
            "objective": "Client will complete at least one documented follow-up action per week toward the identified goal and review progress with case management.",
            "interventions": [
                "Case manager will review barriers, provide coordination support, and reinforce follow-through on referrals and appointments.",
                "Case manager will use motivational interviewing and problem-solving to support progress toward the identified goal.",
                "Case manager will document client response, barriers, and next steps during each contact."
            ],
            "smart_formatting_help": [
                "Specific: name the service area or functional issue being addressed.",
                "Measurable: include a count, deadline, or review frequency.",
                "Achievable: keep the objective realistic for the current level of stability.",
                "Relevant: tie the objective to housing, employment, legal, benefits, health, or recovery needs.",
                "Time-bound: include a target date or review cadence."
            ],
            "progress_summary": progress_summary,
            "golden_thread_suggestions": [
                f"Problem: {barriers}",
                f"Goal: {client_goal}",
                "Intervention: document what case management support was actually provided.",
                "Next step: record the next action, responsible party, and due date."
            ],
            "needs_considered": needs,
        }
        return suggestions

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

        if not self.client:
            return {
                "draft": fallback_draft,
                "source": "template_fallback",
                "template_excerpt": template_excerpt,
                "compliance_preview": review,
                "suggested_tasks": self._build_suggested_tasks(payload, fallback_draft, review),
            }

        # Pull comprehensive client data for intelligent auto-population
        client_id = payload.get("client_id")
        comprehensive_data = self._get_comprehensive_client_data(client_id) if client_id else {}
        core_data = comprehensive_data.get('core', {})
        case_mgmt_data = comprehensive_data.get('case_management', {})
        recent_case_notes = comprehensive_data.get('recent_notes', [])

        user_prompt = (payload.get("user_prompt") or "").strip()
        client_name = payload.get("client_name") or "[Client Name]"
        note_kind = payload.get("note_kind", "progress_note")
        template_label = (payload.get("context") or {}).get("template_label", note_kind.replace("_", " ").title())
        template_category = (payload.get("context") or {}).get("template_category", "")
        current_date = datetime.now().strftime("%B %d, %Y")
        brand_guidance_context = self.get_brand_guidance_context(
            query=user_prompt or payload.get("current_text") or note_kind,
            note_kind=note_kind,
            case_manager_id=payload.get("case_manager_id") or DEFAULT_CASE_MANAGER_ID,
        )

        # Build comprehensive client context for AI
        client_context_parts = []
        if core_data or case_mgmt_data:
            first_name = core_data.get('first_name') or case_mgmt_data.get('first_name', '')
            last_name = core_data.get('last_name') or case_mgmt_data.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip() or client_name

            # Calculate age
            age_str = "unknown age"
            dob = core_data.get('date_of_birth') or case_mgmt_data.get('date_of_birth')
            if dob:
                try:
                    dob_date = datetime.strptime(dob, '%Y-%m-%d')
                    age = (datetime.now() - dob_date).days // 365
                    age_str = f"{age} years old"
                except:
                    pass

            # Gather all available client information
            gender = case_mgmt_data.get('gender', 'unknown gender')
            race = case_mgmt_data.get('race', 'unknown race')
            housing_status = case_mgmt_data.get('housing_status', 'Unknown housing')
            employment_status = case_mgmt_data.get('employment_status', 'Unknown employment')
            legal_status = case_mgmt_data.get('legal_status', 'No documented legal status')
            substance_history = case_mgmt_data.get('substance_abuse_history', 'No documented substance history')
            mental_health = case_mgmt_data.get('mental_health_status', 'Unknown mental health status')
            barriers = case_mgmt_data.get('barriers', 'No documented barriers')
            goals = case_mgmt_data.get('goals', 'No documented goals')

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
        else:
            client_context_parts.append(f"CLIENT: {client_name} (limited data available)")

        # Add recent notes context
        if recent_case_notes:
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

        client_context_str = "\n".join(client_context_parts)

        prompt = [
            "You are an AI documentation assistant for a case management suite competing with professional tools like Twofold Health, Clinical Notes AI, and Mentalyc.",
            "",
            "CRITICAL INSTRUCTIONS:",
            "1. Use the template from the library below as your PRIMARY FORMAT",
            "2. Generate COMPLETE, FULLY-WRITTEN professional documentation using ALL available client data",
            "3. AUTO-FILL ALL POSSIBLE FIELDS using the client profile data provided",
            "4. DO NOT leave demographic/status brackets empty if data is available",
            "5. Write full narrative paragraphs integrating client-specific details",
            "6. Follow the EXACT structure and formatting from the selected template",
            "7. ONLY leave [VERBATIM QUOTE] brackets for case manager to fill - everything else should be populated",
            "8. Follow organization-specific guidance materials when they are provided below",
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
            "- Fill in ALL demographic/status fields using the CLIENT PROFILE data",
            "- For RESPONSE section: Write complete paragraph using: demographics (age/race/gender), substance history, legal status, employment status, recent barriers",
            "- If case manager provided session notes, incorporate them into the narrative",
            "- If no session notes provided, use recent case notes to write continuity note",
            "- Include realistic placeholder for client quote: Client stated, \"[VERBATIM CLIENT QUOTE]\"",
            "- Use professional case management language matching the template style",
            "- Make it comprehensive so case manager only needs to add the verbatim quote",
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
            review = self.compliance_review(
                {
                    "draft": draft,
                    "note_kind": payload.get("note_kind", "progress_note"),
                    "context": payload.get("context") or {},
                }
            )
            return {
                "draft": draft,
                "source": "openai",
                "template_excerpt": template_excerpt,
                "compliance_preview": review,
                "suggested_tasks": self._build_suggested_tasks(payload, draft, review),
            }
        except Exception as exc:
            logger.warning("Documentation AI draft generation failed, using fallback: %s", exc)
            return {
                "draft": fallback_draft,
                "source": "template_fallback",
                "template_excerpt": template_excerpt,
                "compliance_preview": review,
                "suggested_tasks": self._build_suggested_tasks(payload, fallback_draft, review),
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
