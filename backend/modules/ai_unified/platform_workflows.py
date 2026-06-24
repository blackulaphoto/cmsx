"""
Structured workflow recipes for popup AI retrieval.
"""

from __future__ import annotations

from typing import Dict, List


PLATFORM_WORKFLOWS: List[Dict[str, object]] = [
    {
        "key": "full_new_client_intake",
        "display_name": "Full New Client Intake",
        "aliases": ["full intake", "new client", "admission", "intake workflow", "start intake"],
        "trigger_question_examples": [
            "How do I do a full intake?",
            "I'm about to get a new client, walk me through intake.",
            "Where do I start a new admission?"
        ],
        "modules_to_open_in_order": ["admissions", "case_management", "documentation", "treatment_plan", "smart_daily"],
        "step_by_step_actions": [
            "Start in Admissions to create or open the full admission packet.",
            "Complete forms, demographics, contacts, insurance, consent, and referral-source fields.",
            "Open Case Management to confirm the client profile and identify immediate needs.",
            "Use Documentation for the initial CM note or intake note.",
            "Use Treatment Plan if goals, needs, strengths, and barriers need to be formalized.",
            "Create reminders in Smart Daily for deadlines, verifications, appointments, and follow-up calls.",
            "Open specialty modules like Benefits, Medical, Legal, Housing, or Jobs based on identified needs."
        ],
        "data_needed": ["Client demographics", "insurance", "contacts", "consents", "immediate needs", "goals", "barriers"],
        "documentation_output": "Initial intake forms in Admissions plus intake-facing note in Documentation.",
        "reminders_tasks_to_create": ["Insurance verification", "appointments", "court deadlines", "document collection", "housing calls"],
        "related_modules": ["benefits", "medical", "legal", "housing", "jobs"],
        "compliance_cautions": ["Do not invent saved forms or completed documents.", "Preserve HIPAA-aware language."],
        "incomplete_or_unclear_fallback": "If a form or packet step is unclear, tell the user the closest available place is Admissions and then Documentation or Smart Daily for follow-up."
    },
    {
        "key": "daily_case_manager_morning_workflow",
        "display_name": "Daily Case Manager Morning Workflow",
        "aliases": ["morning workflow", "start my day", "what should I check every morning", "daily workflow"],
        "trigger_question_examples": ["What should I check every morning?", "How do I use this app day to day?"],
        "modules_to_open_in_order": ["dashboard", "smart_daily", "messages", "case_management"],
        "step_by_step_actions": [
            "Start on Dashboard for high-level caseload status and alerts.",
            "Move to Smart Daily for the actual work queue and deadlines.",
            "Check Messages for internal staff communication that may affect today's priorities.",
            "Open the specific client or module for the highest-priority work."
        ],
        "data_needed": ["Caseload view", "today's tasks", "messages", "selected client when work becomes client-specific"],
        "documentation_output": "Document actual client work later in Documentation or the relevant module.",
        "reminders_tasks_to_create": ["Any missing follow-up surfaced during the morning review"],
        "related_modules": ["documentation", "legal", "benefits", "medical", "housing"],
        "compliance_cautions": ["Do not claim tasks were completed unless confirmed."],
        "incomplete_or_unclear_fallback": "If the user asks generally how to use Ember daily, anchor them in Dashboard then Smart Daily first."
    },
    {
        "key": "client_profile_update",
        "display_name": "Client Profile Update",
        "aliases": ["update client", "client profile update", "edit client", "update profile"],
        "trigger_question_examples": ["How do I update a client profile?"],
        "modules_to_open_in_order": ["case_management", "client_dashboard", "documentation"],
        "step_by_step_actions": [
            "Open Case Management and locate the client.",
            "Edit or review core profile details.",
            "Open the Client Dashboard for client-specific linked context if needed.",
            "Use Documentation if the update also needs a narrative case note."
        ],
        "data_needed": ["Client demographics", "status changes", "need updates"],
        "documentation_output": "Client profile fields plus optional narrative note in Documentation.",
        "reminders_tasks_to_create": ["Any follow-up created by the profile change"],
        "related_modules": ["smart_daily", "housing", "benefits", "legal", "medical"],
        "compliance_cautions": ["Do not invent profile changes."],
        "incomplete_or_unclear_fallback": "If the exact field location is unclear, direct the user to Case Management first."
    },
    {
        "key": "initial_cm_note",
        "display_name": "Initial CM Note",
        "aliases": ["initial cm note", "intake note", "first note", "case management note"],
        "trigger_question_examples": ["How do I write the initial CM note?"],
        "modules_to_open_in_order": ["documentation", "admissions", "case_management"],
        "step_by_step_actions": [
            "Open Documentation and select the client first.",
            "Choose the appropriate note type for the initial case-management note.",
            "Pull in relevant intake details from Admissions and need context from Case Management.",
            "Use internal template or playbook rules when drafting the note."
        ],
        "data_needed": ["Selected client", "intake details", "needs", "goals", "interventions", "referrals", "next steps"],
        "documentation_output": "Initial CM note in Documentation.",
        "reminders_tasks_to_create": ["Follow-up tasks named in the note should be added in Smart Daily."],
        "related_modules": ["smart_daily", "treatment_plan"],
        "compliance_cautions": ["Use playbook or template rules.", "Do not say the note was saved unless confirmed."],
        "incomplete_or_unclear_fallback": "If a specialized note type is unavailable, say the closest available place in Ember is Documentation with the nearest note category."
    },
    {
        "key": "treatment_plan_creation",
        "display_name": "Treatment Plan Creation",
        "aliases": ["create treatment plan", "treatment plan", "goals and interventions"],
        "trigger_question_examples": ["How do I create a treatment plan?"],
        "modules_to_open_in_order": ["treatment_plan", "documentation", "smart_daily"],
        "step_by_step_actions": [
            "Open Treatment Plan and select the client.",
            "Create or review the plan sections for problems, goals, objectives, interventions, aftercare, and completion criteria.",
            "Use Documentation if a supporting narrative note or review note is required.",
            "Use Smart Daily for plan-related follow-up items."
        ],
        "data_needed": ["Selected client", "needs", "barriers", "strengths", "goals", "interventions", "aftercare details"],
        "documentation_output": "Structured treatment plan plus any supporting note in Documentation.",
        "reminders_tasks_to_create": ["Plan review dates", "aftercare follow-up", "client tasks"],
        "related_modules": ["case_management", "documentation", "smart_daily"],
        "compliance_cautions": ["Keep plan details grounded in client needs; do not invent approval status."],
        "incomplete_or_unclear_fallback": "If the user only needs narrative review text, route to Documentation as the closest available note surface."
    },
    {
        "key": "group_session_documentation",
        "display_name": "Group Session Documentation",
        "aliases": ["group notes", "group session", "facilitate group", "group documentation"],
        "trigger_question_examples": ["How do I write group notes?"],
        "modules_to_open_in_order": ["groups", "documentation"],
        "step_by_step_actions": [
            "Open Groups to set up or review the session structure.",
            "Capture topic, purpose, key points, discussion prompts, and activities.",
            "Use Documentation if a narrative group note is also needed."
        ],
        "data_needed": ["Group topic", "population", "discussion points", "activities", "facilitator tips"],
        "documentation_output": "Group setup in Groups plus narrative note in Documentation if needed.",
        "reminders_tasks_to_create": ["Any follow-up from the group session"],
        "related_modules": ["treatment_plan", "smart_daily"],
        "compliance_cautions": ["Do not imply group notes are auto-created everywhere."],
        "incomplete_or_unclear_fallback": "If the session note destination is unclear, tell the user to use Documentation for the narrative record."
    },
    {
        "key": "ur_workflow",
        "display_name": "Utilization Review Workflow",
        "aliases": ["ur workflow", "utilization review", "authorization", "continued stay", "medical necessity"],
        "trigger_question_examples": ["How do I use the UR module?"],
        "modules_to_open_in_order": ["ur", "documentation", "smart_daily"],
        "step_by_step_actions": [
            "Open UR and select the client.",
            "Use the workflow coach to review the current UR step.",
            "Capture coverage, placement, authorization detail, reviewer communication, deadlines, and medical necessity summary.",
            "Document the narrative update where needed and set follow-up reminders for deadlines or escalation."
        ],
        "data_needed": ["Payer", "program", "level of care", "reviewer", "authorization status", "deadline", "medical necessity summary"],
        "documentation_output": "UR data in the UR module plus supporting narrative documentation if required.",
        "reminders_tasks_to_create": ["Authorization deadlines", "reviewer callback", "appeal or escalation deadlines"],
        "related_modules": ["benefits", "medical", "documentation", "smart_daily"],
        "compliance_cautions": ["Keep the answer operational, not generic insurance advice."],
        "incomplete_or_unclear_fallback": "If a downstream action is unclear, the closest available place in Ember is UR for tracking and Smart Daily for follow-up."
    },
    {
        "key": "housing_referral_workflow",
        "display_name": "Housing Referral Workflow",
        "aliases": ["housing referral", "housing follow-up", "housing coordination", "placement search"],
        "trigger_question_examples": ["How do I coordinate housing?", "Where do I put housing follow-up?"],
        "modules_to_open_in_order": ["housing", "documentation", "smart_daily"],
        "step_by_step_actions": [
            "Open Housing to search or review case-manager housing tools.",
            "Record the outreach outcome or referral status in Documentation if narrative tracking is needed.",
            "Create Smart Daily tasks for callbacks, site visits, application deadlines, or placement follow-up."
        ],
        "data_needed": ["Location", "housing need", "referral targets", "outreach outcome"],
        "documentation_output": "Housing outreach note or case note in Documentation.",
        "reminders_tasks_to_create": ["Callbacks", "site visits", "application deadlines", "placement check-ins"],
        "related_modules": ["sober_living", "sober_living_directory", "client_dashboard"],
        "compliance_cautions": ["Do not claim placement happened unless confirmed."],
        "incomplete_or_unclear_fallback": "If the user needs sober-living research rather than housing search, route to Sober Living Directory as the closest available place."
    },
    {
        "key": "sober_living_coordination",
        "display_name": "Sober Living Coordination",
        "aliases": ["sober living coordination", "sober living placement", "sober house", "directory review"],
        "trigger_question_examples": ["How do I coordinate sober living?"],
        "modules_to_open_in_order": ["sober_living_directory", "sober_living", "documentation", "smart_daily"],
        "step_by_step_actions": [
            "Use Sober Living Directory when researching options and comparing listings.",
            "Use Sober Living when the work is house-specific or operational.",
            "Document outreach or placement notes, then create Smart Daily follow-up tasks."
        ],
        "data_needed": ["Location", "certification", "rent or funding notes", "MAT or call notes"],
        "documentation_output": "Case note or placement note in Documentation if needed.",
        "reminders_tasks_to_create": ["Calls", "follow-up review", "placement status check"],
        "related_modules": ["housing", "services"],
        "compliance_cautions": ["Do not present directory results as guaranteed placements."],
        "incomplete_or_unclear_fallback": "If discovery or scheduler controls are unavailable, say the closest stable workflow is the main directory search plus Documentation and Smart Daily."
    },
    {
        "key": "benefits_medi_cal_dpss_workflow",
        "display_name": "Benefits, Medi-Cal, and DPSS Workflow",
        "aliases": ["benefits workflow", "medi-cal", "dpss", "calfresh", "gr", "insurance verification"],
        "trigger_question_examples": ["How do I use Benefits?", "Where do I put Medi-Cal info?"],
        "modules_to_open_in_order": ["benefits", "admissions", "documentation", "smart_daily"],
        "step_by_step_actions": [
            "Open Benefits and select the client.",
            "Review benefits or insurance fields and supporting documents.",
            "Refer back to Admissions for intake-time insurance details when needed.",
            "Document any outcome requiring a note, then create Smart Daily follow-up tasks."
        ],
        "data_needed": ["Selected client", "insurance details", "benefit type", "income or work limitation data", "supporting documents"],
        "documentation_output": "Benefits or insurance note if the workflow requires narrative documentation.",
        "reminders_tasks_to_create": ["Verification deadlines", "document collection", "enrollment follow-up"],
        "related_modules": ["medical", "fmla"],
        "compliance_cautions": ["Do not invent benefit approval or coverage status."],
        "incomplete_or_unclear_fallback": "If a specific benefit action is unclear, the closest stable places are Benefits for tracking and Smart Daily for follow-up."
    },
    {
        "key": "medical_appointment_coordination",
        "display_name": "Medical Appointment Coordination",
        "aliases": ["medical appointment", "pcp appointment", "therapy referral", "psychiatry follow-up", "dental visit"],
        "trigger_question_examples": ["How do I coordinate a medical appointment?"],
        "modules_to_open_in_order": ["medical", "benefits", "documentation", "smart_daily"],
        "step_by_step_actions": [
            "Open Medical and select the client.",
            "Review providers or appointments and confirm the care need.",
            "Use Benefits if insurance verification affects access.",
            "Document the coordination and create Smart Daily follow-up."
        ],
        "data_needed": ["Selected client", "provider type", "insurance coverage", "appointment details"],
        "documentation_output": "Medical coordination note if required.",
        "reminders_tasks_to_create": ["Appointment date", "transportation follow-up", "insurance verification"],
        "related_modules": ["case_management"],
        "compliance_cautions": ["No medical diagnosis or treatment advice."],
        "incomplete_or_unclear_fallback": "If provider search detail is incomplete, the closest available place is the Medical module plus Benefits verification and Smart Daily follow-up."
    },
    {
        "key": "legal_probation_court_update",
        "display_name": "Legal, Probation, and Court Update Workflow",
        "aliases": ["court update", "legal update", "probation", "parole", "court workflow"],
        "trigger_question_examples": ["Where do I document a court update?"],
        "modules_to_open_in_order": ["legal", "documentation", "smart_daily"],
        "step_by_step_actions": [
            "Open Legal and select the client.",
            "Update or review legal status and any supporting file references.",
            "Use Documentation for the narrative court or legal note.",
            "Use Smart Daily for court dates, probation deadlines, or follow-up tasks."
        ],
        "data_needed": ["Selected client", "court date", "probation status", "charges", "notice or letter"],
        "documentation_output": "Court or legal note in Documentation plus tracked legal details in Legal.",
        "reminders_tasks_to_create": ["Court date reminder", "probation check-in", "document deadline"],
        "related_modules": ["case_management"],
        "compliance_cautions": ["No definitive legal advice."],
        "incomplete_or_unclear_fallback": "If the specific legal field is unclear, the closest stable workflow is Legal for tracking and Documentation for the narrative record."
    },
    {
        "key": "fmla_tracking",
        "display_name": "FMLA Tracking Workflow",
        "aliases": ["fmla workflow", "leave paperwork", "std workflow", "return to work"],
        "trigger_question_examples": ["How do I use FMLA?"],
        "modules_to_open_in_order": ["fmla", "documentation", "smart_daily"],
        "step_by_step_actions": [
            "Open FMLA and review the case workflow stage.",
            "Track deadlines, missing paperwork, and return-to-work or denial stages.",
            "Use Documentation for narrative tracking if needed and Smart Daily for deadlines."
        ],
        "data_needed": ["Workflow stage", "employer info", "forms", "deadlines"],
        "documentation_output": "FMLA or leave-tracking note if needed.",
        "reminders_tasks_to_create": ["Paperwork deadlines", "employer follow-up", "return-to-work tasks"],
        "related_modules": ["benefits"],
        "compliance_cautions": ["Do not overstate employer-policy or legal interpretation."],
        "incomplete_or_unclear_fallback": "If a leave sub-feature is unclear, use FMLA for tracking and Smart Daily for operational follow-up."
    },
    {
        "key": "discharge_planning",
        "display_name": "Discharge Planning",
        "aliases": ["discharge planning", "step-down", "transition plan", "aftercare planning"],
        "trigger_question_examples": ["How do I do discharge planning?"],
        "modules_to_open_in_order": ["case_management", "documentation", "treatment_plan", "housing", "benefits", "medical", "legal", "jobs", "smart_daily"],
        "step_by_step_actions": [
            "Review the client’s current needs and transition readiness in Case Management.",
            "Document the discharge or transition plan in Documentation.",
            "Update Treatment Plan or aftercare sections if appropriate.",
            "Open specialty modules like Housing, Benefits, Medical, Legal, or Jobs based on discharge needs.",
            "Create Smart Daily tasks for all transition follow-up."
        ],
        "data_needed": ["Discharge date", "aftercare needs", "housing plan", "benefits status", "medical follow-up", "legal obligations", "employment goals"],
        "documentation_output": "Discharge or transition note plus treatment-plan updates if needed.",
        "reminders_tasks_to_create": ["Aftercare appointments", "housing follow-up", "benefits deadlines", "legal dates", "employment follow-up"],
        "related_modules": ["sober_living", "resume"],
        "compliance_cautions": ["Do not claim a discharge plan is complete unless the documented pieces actually exist."],
        "incomplete_or_unclear_fallback": "If no dedicated discharge feature exists for a subtask, the closest stable workflow is Documentation plus the relevant specialty module plus Smart Daily."
    },
    {
        "key": "employment_reentry",
        "display_name": "Employment and Reentry Workflow",
        "aliases": ["employment workflow", "job search workflow", "resume workflow", "reentry employment"],
        "trigger_question_examples": ["How do I support employment planning in Ember?"],
        "modules_to_open_in_order": ["resume", "jobs", "documentation", "smart_daily"],
        "step_by_step_actions": [
            "Open Resume to build or review the employment profile and resume.",
            "Open Jobs to search client-specific opportunities.",
            "Document meaningful employment planning when needed.",
            "Use Smart Daily for interview, application, or follow-up tasks."
        ],
        "data_needed": ["Selected client", "employment profile", "job targets", "location"],
        "documentation_output": "Employment planning note if needed.",
        "reminders_tasks_to_create": ["Applications", "interviews", "resume revisions", "follow-up calls"],
        "related_modules": ["case_management"],
        "compliance_cautions": ["Do not invent fully built job-search automation."],
        "incomplete_or_unclear_fallback": "If a job-search tool is incomplete, the closest stable workflow is Resume plus Jobs plus Smart Daily."
    },
    {
        "key": "supervisor_review",
        "display_name": "Supervisor Review Workflow",
        "aliases": ["supervisor workflow", "review staff workload", "team review"],
        "trigger_question_examples": ["How do supervisors review team work?"],
        "modules_to_open_in_order": ["supervisor_dashboard", "smart_daily", "team_management", "messages"],
        "step_by_step_actions": [
            "Open Supervisor Dashboard to review oversight metrics.",
            "Use Smart Daily if the issue is task flow or overdue work.",
            "Use Team Management if staffing or access changes are needed.",
            "Use Messages for staff coordination."
        ],
        "data_needed": ["Supervisor metrics", "team status", "message threads"],
        "documentation_output": "Operational follow-up only; no client note unless client work changes elsewhere.",
        "reminders_tasks_to_create": ["Oversight follow-up tasks if the org uses Smart Daily that way"],
        "related_modules": ["dashboard"],
        "compliance_cautions": ["Admin-only workflow."],
        "incomplete_or_unclear_fallback": "If the user is not an admin, do not present this as available."
    },
    {
        "key": "admin_team_workflow",
        "display_name": "Admin and Team Workflow",
        "aliases": ["admin workflow", "team workflow", "invite staff", "manage team", "org admin"],
        "trigger_question_examples": ["How do I invite staff?", "Where do I manage my team?"],
        "modules_to_open_in_order": ["settings", "team_management", "support"],
        "step_by_step_actions": [
            "Open Settings to find admin-facing links.",
            "Use Team Management for invites and staff management.",
            "Use Support if the issue is account or system related."
        ],
        "data_needed": ["Admin access", "staff name", "staff email", "role"],
        "documentation_output": "Operational admin changes only.",
        "reminders_tasks_to_create": ["Admin follow-up tasks if needed"],
        "related_modules": ["supervisor_dashboard", "billing"],
        "compliance_cautions": ["Hide admin modules from non-admins."],
        "incomplete_or_unclear_fallback": "If the user lacks admin access, tell them the closest path is Settings or Support depending on the need."
    },
    {
        "key": "support_settings_account_workflow",
        "display_name": "Support, Settings, and Account Workflow",
        "aliases": ["support workflow", "account workflow", "settings workflow", "profile workflow", "billing help"],
        "trigger_question_examples": ["Where do I change settings?", "How do I submit a support ticket?"],
        "modules_to_open_in_order": ["settings", "profile", "support", "billing"],
        "step_by_step_actions": [
            "Open Settings to choose the right account or org section.",
            "Use Profile for personal account information.",
            "Use Support for bugs, billing questions, or feature requests.",
            "Use Billing only for plan and usage review, not client benefits."
        ],
        "data_needed": ["User role", "support issue category", "billing question details without PHI"],
        "documentation_output": "Operational support ticket only.",
        "reminders_tasks_to_create": ["Optional account follow-up tasks in Smart Daily if the org uses it that way"],
        "related_modules": ["team_management", "super_admin"],
        "compliance_cautions": ["Do not include client names or PHI in support submissions."],
        "incomplete_or_unclear_fallback": "If the exact setting is unclear, the closest stable path is Settings first, then Support."
    },
]


WORKFLOWS_BY_KEY: Dict[str, Dict[str, object]] = {entry["key"]: entry for entry in PLATFORM_WORKFLOWS}

