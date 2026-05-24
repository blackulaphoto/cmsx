import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from backend.shared.database.workspace_store import workspace_store

logger = logging.getLogger(__name__)

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

    def _build_fallback_draft(self, payload: Dict[str, Any], recent_notes: List[Dict[str, Any]]) -> str:
        """Build a complete template-style draft using bracket placeholders."""
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

        # Build complete template-formatted content
        output: List[str] = []

        for heading, body in sections:
            output.append(f"{heading}:")
            section_text = body

            # Generate full, template-formatted content for each section
            if heading in {"RESPONSE", "STATUS / RESPONSE", "CLIENT RESPONSE"}:
                # Follow the CM-ONGOING-01 template format
                if prompt:
                    section_text = f"CM and client discussed {prompt}. "
                else:
                    section_text = "CM and client discussed aftercare plans, which is an ongoing conversation. "

                if direct_quotes:
                    section_text += "Client stated, \"" + direct_quotes[0] + "\". "
                else:
                    section_text += "Client stated, \"[VERBATIM CLIENT QUOTE THIS WEEK]\". "

                if current_text:
                    section_text += current_text + " "

                section_text += "CM and client will continue making progress toward discharge plans and treatment plan goals."

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

        return "\n".join(output).strip()

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

    async def generate_note_draft(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        recent_notes = self._get_recent_note_context(payload.get("client_id"))
        template_excerpt = self._get_template_excerpt(payload.get("note_kind", "progress_note"))
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

        user_prompt = (payload.get("user_prompt") or "").strip()
        client_name = payload.get("client_name") or "[Client Name]"
        note_kind = payload.get("note_kind", "progress_note")
        current_date = datetime.now().strftime("%B %d, %Y")

        prompt = [
            "You are an AI documentation assistant for a case management suite.",
            "",
            "CRITICAL INSTRUCTIONS:",
            "1. Use the template from the library below as your PRIMARY FORMAT",
            "2. Generate COMPLETE, FULLY-WRITTEN professional documentation",
            "3. Use placeholder brackets EXACTLY like the template: [FACILITY NAME], [CT NAME], [DATE], [VERBATIM QUOTE]",
            "4. DO NOT write generic descriptions - write full narrative paragraphs like the template shows",
            "5. Follow the EXACT structure and formatting from the template library",
            "",
            "TEMPLATE LIBRARY EXCERPT (your primary format guide):",
            "─────────────────────────────────────────────────────────────",
            template_excerpt or "No template available.",
            "─────────────────────────────────────────────────────────────",
            "",
            "User context for this specific note:",
            f"• Client: {client_name}",
            f"• Date: {current_date}",
            f"• User's notes: {user_prompt or '(none provided)'}",
            f"• Note type: {note_kind.replace('_', ' ')}",
            "",
            "Recent history:" if recent_notes else "",
            "\n".join([
                f"  - {n.get('note_type')}: {(n.get('content') or '')[:80]}..."
                for n in recent_notes[:2]
            ]) if recent_notes else "",
            "",
            "INSTRUCTIONS:",
            "- Copy the template format EXACTLY as shown above",
            "- Fill in realistic placeholder content in brackets",
            "- If user provided notes/context, incorporate them into the RESPONSE/CLIENT RESPONSE section",
            "- Use professional case management language like the template",
            "- Include specific examples in brackets: [specific barrier], [concrete intervention], [observable detail]",
            "- Add quote placeholders: Client stated, \"[insert verbatim client quote about...] \"",
            "",
            "Return ONLY the formatted note - no explanations, no meta-commentary.",
        ]
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=0.3,
                max_tokens=900,
                messages=[
                    {"role": "system", "content": "You produce concise, audit-safe case management documentation drafts."},
                    {"role": "user", "content": "\n\n".join(prompt)},
                ],
            )
            draft = (response.choices[0].message.content or "").strip() or fallback_draft
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
