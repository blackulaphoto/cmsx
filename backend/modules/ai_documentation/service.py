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
        ("GOAL", "Support progress toward current treatment, housing, legal, employment, and stability goals."),
        ("INTERVENTION", "Case manager reviewed current needs, addressed barriers, provided coordination support, and discussed next action steps."),
        ("RESPONSE", "Client engaged in discussion regarding current progress, barriers, and supports. Staff observations and client statements are documented below."),
        ("PLAN", "Continue follow-up on identified needs, update treatment/discharge planning, and complete any pending referrals or paperwork."),
    ],
    "initial_note": [
        ("GOAL", "Complete initial case management engagement and identify immediate needs, barriers, and discharge priorities."),
        ("INTERVENTION", "Case manager introduced services, reviewed immediate needs, assessed barriers, and discussed treatment/discharge priorities."),
        ("RESPONSE", "Client reviewed current needs, identified goals, and participated in planning discussion."),
        ("PLAN", "Maintain weekly contact, address identified barriers, and move forward with referrals and documentation needs."),
    ],
    "group_note": [
        ("GROUP TOPIC", "Document the focus of the group session."),
        ("INTERVENTION", "Staff facilitated discussion, encouraged participation, and linked the topic to recovery and treatment goals."),
        ("CLIENT RESPONSE", "Document participation level, engagement, observed affect, and any direct quotes provided by staff."),
        ("PLAN", "Reinforce coping skills, follow up on barriers, and monitor progress toward treatment goals."),
    ],
    "treatment_plan": [
        ("PROBLEM", "Summarize the primary treatment need affecting functioning and recovery."),
        ("GOAL", "Describe the target outcome in client-centered language."),
        ("OBJECTIVE", "Describe a measurable short-term objective tied to the goal."),
        ("INTERVENTION", "Describe the specific staff intervention or service support."),
        ("NEXT REVIEW", "Document how progress will be reviewed and when follow-up is needed."),
    ],
    "referral_summary": [
        ("REFERRAL NEED", "Summarize the presenting need and why referral is indicated."),
        ("ACTION TAKEN", "Document outreach, referral details, and information provided to the client."),
        ("CLIENT RESPONSE", "Document the client response to the referral and any barriers discussed."),
        ("NEXT STEP", "Document required follow-up, verification, and timeline."),
    ],
    "discharge_summary": [
        ("DISCHARGE STATUS", "Summarize current stability, functioning, and treatment readiness."),
        ("SERVICES PROVIDED", "Document the services coordinated during the reporting period."),
        ("BARRIERS / RISKS", "Document unresolved issues that may affect transition."),
        ("AFTERCARE PLAN", "Document appointments, referrals, housing, benefits, and follow-up needs."),
    ],
    "fmla_case_note": [
        ("PURPOSE", "Document the current FMLA paperwork or coordination purpose."),
        ("INTERVENTION", "Document contacts, paperwork actions, follow-up efforts, and coordination completed."),
        ("STATUS / RESPONSE", "Document the current status of the packet and any response from client, employer, or provider."),
        ("NEXT STEP", "Document deadlines, follow-up, and pending items."),
    ],
    "fmla_correspondence": [
        ("CONTACT", "Document who was contacted and by what method."),
        ("SUMMARY", "Summarize what was discussed, requested, or confirmed."),
        ("OUTCOME", "Document what was learned or completed."),
        ("FOLLOW-UP", "Document next required action and due date."),
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
        if not self.template_library_text:
            return ""
        keywords = TEMPLATE_KEYWORDS.get(note_kind, ["CASE MANAGER NOTES"])
        lower_text = self.template_library_text.lower()
        for keyword in keywords:
            idx = lower_text.find(keyword.lower())
            if idx >= 0:
                return self.template_library_text[idx: idx + 2200]
        return self.template_library_text[:1800]

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
        note_kind = payload.get("note_kind", "progress_note")
        sections = FALLBACK_SKELETONS.get(note_kind, FALLBACK_SKELETONS["progress_note"])
        prompt = (payload.get("user_prompt") or "").strip()
        current_text = (payload.get("current_text") or "").strip()
        context = payload.get("context") or {}
        direct_quotes = context.get("direct_quotes") or []
        observations = context.get("observations") or ""
        client_name = payload.get("client_name") or "Client"
        recent_excerpt = ""
        if recent_notes:
            recent_excerpt = " Recent documentation themes: " + " | ".join(
                f"{note.get('note_type', 'Note')}: {(note.get('content', '') or '')[:120]}"
                for note in recent_notes
            )

        output: List[str] = []
        for heading, body in sections:
            output.append(f"{heading}:")
            section_text = body
            if heading in {"RESPONSE", "STATUS / RESPONSE", "CLIENT RESPONSE"}:
                detail_parts = []
                if prompt:
                    detail_parts.append(prompt)
                if observations:
                    detail_parts.append(f"Observed: {observations}")
                if direct_quotes:
                    detail_parts.append("Client stated: " + "; ".join(direct_quotes[:2]))
                if current_text:
                    detail_parts.append(current_text)
                if recent_excerpt:
                    detail_parts.append(recent_excerpt.strip())
                if detail_parts:
                    section_text = " ".join(detail_parts)
            elif heading in {"INTERVENTION", "ACTION TAKEN"} and context.get("interventions"):
                section_text = f"{body} Interventions addressed: {context.get('interventions')}."
            elif heading in {"PLAN", "NEXT STEP", "FOLLOW-UP"} and context.get("next_steps"):
                section_text = f"{body} Next steps: {context.get('next_steps')}."
            elif heading == "GOAL" and context.get("goals"):
                section_text = f"{body} Current goal focus: {context.get('goals')}."
            output.append(section_text)
            output.append("")

        output.append(f"Client reference: {client_name}.")
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

        prompt = [
            "You are an AI documentation assistant embedded in a case management suite.",
            "Draft documentation only. Do not fabricate facts, quotes, dates, diagnoses, or contacts.",
            "Preserve current workflow and produce editable documentation in the organization's existing style.",
            "Use the following template guidance when relevant:",
            template_excerpt or "No template excerpt available.",
            "Case context JSON:",
            str(
                {
                    "module": payload.get("module"),
                    "note_kind": payload.get("note_kind"),
                    "client_name": payload.get("client_name"),
                    "user_prompt": payload.get("user_prompt"),
                    "current_text": payload.get("current_text"),
                    "context": payload.get("context") or {},
                    "recent_notes": recent_notes,
                }
            ),
            "Return only the draft note text with clear documentation sections.",
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
