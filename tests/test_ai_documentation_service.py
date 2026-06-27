import asyncio
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.modules.ai_documentation.service import DocumentationAIService
from backend.shared.database.workspace_store import workspace_store


class DocumentationAIServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = DocumentationAIService()
        self.service.client = None
        self._brand_resource_ids = []

    def _build_template_fallback(self, template_label, note_kind, brief, requested_output_mode="document"):
        return self.service._build_fallback_draft(
            {
                "note_kind": note_kind,
                "client_name": "QA TestClient-Eval",
                "user_prompt": brief,
                "context": {
                    "template_label": template_label,
                    "requested_output_mode": requested_output_mode,
                    "case_manager_brief": brief,
                },
            },
            [],
        )

    def test_fallback_progress_note_contains_sections(self):
        result = self.service._build_fallback_draft(
            {
                "note_kind": "progress_note",
                "client_name": "Taylor Jones",
                "user_prompt": "Client discussed housing barriers and probation follow-up.",
                "context": {
                    "goals": "Secure stable housing",
                    "interventions": "Reviewed referrals and housing resources",
                    "next_steps": "Call housing lead and probation officer",
                    "direct_quotes": ["I need housing this week."],
                },
            },
            [],
        )
        self.assertIn("WEEKLY CM NOTE", result)
        self.assertIn("SUMMARY:", result)
        self.assertIn("CLIENT STATEMENT:", result)
        self.assertIn("NEXT STEP:", result)

    def test_selected_template_fallback_uses_template_body_and_not_raw_prompt(self):
        prompt = "Client reported stable mood, housing needs, probation documentation needs, and outpatient follow-up."
        result = self.service._build_fallback_draft(
            {
                "note_kind": "discharge_summary",
                "client_name": "Taylor Jones",
                "user_prompt": prompt,
                "current_text": "# Completion Letter Template\n\n**Date:** [DATE]\n\n**Client Name:** [CLIENT_NAME]\n\nTo Whom It May Concern,\n\nThis letter is to confirm that **[CLIENT_NAME] successfully completed treatment with [PROGRAM_NAME]**.\n\nSincerely,\n\n[STAFF_NAME]",
                "context": {
                    "template_label": "Completion Letter Template",
                    "template_category": "letters",
                },
            },
            [],
        )

        self.assertNotEqual(result, prompt)
        self.assertIn("COMPLETION LETTER TEMPLATE", result)
        self.assertIn("housing needs", result)
        self.assertIn("Next step:", result)

    def test_template_guardrails_keep_weekly_note_out_of_treatment_plan_format(self):
        guardrails = self.service._build_template_guardrails(
            "progress_note",
            {
                "template_label": "Weekly CM Note",
                "requested_output_mode": "note",
            },
        )

        self.assertIn("Keep the output in concise case-management note structure only.", guardrails)
        self.assertTrue(any("Problem 1" in item for item in guardrails))

    def test_template_guardrails_allow_treatment_plan_review_structure(self):
        guardrails = self.service._build_template_guardrails(
            "treatment_plan",
            {
                "template_label": "Treatment Plan Review",
                "requested_output_mode": "document",
            },
        )

        self.assertIn(
            "Produce a treatment plan review structure with problem, goal, objective, plan, and review details.",
            guardrails,
        )

    def test_fallback_handles_null_client_database_fields(self):
        self.service._get_comprehensive_client_data = lambda _client_id: {
            "case_management": {
                "first_name": "Taylor",
                "last_name": "Jones",
                "prior_convictions": None,
            }
        }
        result = self.service._auto_fill_placeholders(
            "Client: [CLIENT_NAME]\nPrior convictions: [PRIOR CONVICTIONS]",
            client_id="client-with-null-fields",
            client_name="Taylor Jones",
        )

        self.assertIn("Taylor Jones", result)
        self.assertIn("None documented", result)

    def test_compliance_review_flags_missing_sections(self):
        review = self.service.compliance_review({"content": "Client reported stress and asked for help."})
        self.assertFalse(review["is_complete"])
        self.assertTrue(review["missing_intervention"])
        self.assertTrue(review["missing_next_step"])
        self.assertGreaterEqual(len(review["warnings"]), 2)

    def test_treatment_plan_suggestions_include_goal_objective_and_interventions(self):
        result = self.service.generate_treatment_plan_suggestions(
            {
                "client_name": "Taylor Jones",
                "context": {
                    "client_goals": "stabilize housing and improve treatment attendance",
                    "barriers": "missed appointments and unstable housing",
                    "needs": ["housing", "treatment engagement"],
                },
            }
        )
        self.assertIn("goal", result)
        self.assertIn("objective", result)
        self.assertTrue(result["interventions"])
        self.assertTrue(result["smart_formatting_help"])

    def test_group_note_compliance_review_uses_context(self):
        review = self.service.compliance_review(
            {
                "note_kind": "group_note",
                "content": "Intervention: Staff facilitated discussion. Client response: client participated. Plan: follow up next week.",
                "context": {},
            }
        )
        self.assertIn("Group note is missing the documented group topic.", review["warnings"])
        self.assertIn("Group note is missing attendance details.", review["warnings"])
        self.assertIn("Group note is missing participation level.", review["warnings"])

    def test_template_quality_review_passes_when_selected_template_anchors_exist(self):
        review = self.service.compliance_review(
            {
                "note_kind": "progress_note",
                "content": (
                    "WEEKLY CM NOTE\n\n"
                    "SUMMARY:\nCM reviewed housing and probation follow-up needs documented in the brief.\n\n"
                    "CLIENT STATEMENT:\nClient stated, \"I want to stay on track.\"\n\n"
                    "NEXT STEP:\nCM will verify outpatient appointment and housing documentation."
                ),
                "context": {"template_label": "Weekly CM Note"},
            }
        )

        quality = review["quality_review"]
        self.assertEqual("pass", quality["status"])
        self.assertGreaterEqual(quality["score"], 90)
        self.assertEqual([], quality["missing_template_anchors"])

    def test_template_quality_review_flags_missing_residence_data(self):
        review = self.service.compliance_review(
            {
                "note_kind": "referral_summary",
                "content": (
                    "# Proof of Residence Template\n\n"
                    "### RE: Proof of Residency for Taylor Jones\n\n"
                    "This letter is to verify Taylor Jones is currently a resident of our program located at:\n\n"
                    "[RESIDENCE ADDRESS]\n\n"
                    "Taylor Jones has been residing at this address since June 08, 2026."
                ),
                "context": {"template_label": "Proof of Residence Template"},
            }
        )

        quality = review["quality_review"]
        self.assertEqual("needs_review", quality["status"])
        self.assertIn("Residence address is missing.", quality["data_warnings"])
        self.assertIn("RESIDENCE ADDRESS", quality["unresolved_placeholders"])

    def test_weekly_note_evidence_bound_fallback_uses_only_brief_and_blocks_generic_filler(self):
        draft = self.service._build_fallback_draft(
            {
                "note_kind": "progress_note",
                "client_name": "Taylor Jones",
                "user_prompt": (
                    'Client asked for probation paperwork support and dental scheduling help. '
                    'CM will call the probation officer tomorrow. '
                    'Client stated "I need help getting this paperwork done."'
                ),
                "context": {
                    "template_label": "Weekly CM Note",
                    "requested_output_mode": "note",
                    "case_manager_brief": (
                        'Client asked for probation paperwork support and dental scheduling help. '
                        'CM will call the probation officer tomorrow. '
                        'Client stated "I need help getting this paperwork done."'
                    ),
                },
            },
            [],
        )

        self.assertIn("WEEKLY CM NOTE", draft)
        self.assertIn("probation paperwork support", draft)
        self.assertIn("dental scheduling help", draft)
        self.assertIn("I need help getting this paperwork done.", draft)
        self.assertIn("CM will call the probation officer tomorrow.", draft)
        self.assertNotIn("12-step", draft.lower())
        self.assertNotIn("sponsor", draft.lower())
        self.assertNotIn("aftercare", draft.lower())
        self.assertNotIn("discharge", draft.lower())
        self.assertNotIn("problem 1:", draft.lower())

    def test_weekly_note_evidence_bound_fallback_uses_no_additional_information_when_brief_is_sparse(self):
        draft = self.service._build_fallback_draft(
            {
                "note_kind": "progress_note",
                "client_name": "Taylor Jones",
                "user_prompt": "",
                "context": {
                    "template_label": "Weekly CM Note",
                    "requested_output_mode": "note",
                },
            },
            [],
        )

        self.assertIn("WEEKLY CM NOTE", draft)
        self.assertIn("No additional information was provided.", draft)
        self.assertIn("No direct client quote was documented.", draft)

    def test_progress_report_fallback_keeps_progress_report_structure(self):
        draft = self._build_template_fallback(
            "Progress Report Template",
            "progress_report",
            'Client attended meetings this week and requested help coordinating housing documents. Client stated "I want to stay consistent." CM will follow up on the document request tomorrow.',
        )

        self.assertIn("PROGRESS REPORT TEMPLATE", draft)
        self.assertIn("To Whom It May Concern,", draft)
        self.assertIn("I want to stay consistent.", draft)
        self.assertNotIn("Problem 1:", draft)
        self.assertNotIn("OBJECTIVE:", draft)

    def test_letter_of_presence_fallback_keeps_formal_letter_format(self):
        draft = self._build_template_fallback(
            "Letter of Presence Template",
            "presence_letter",
            "Client remains engaged in services this week and requested verification for an outside party.",
        )

        self.assertIn("LETTER OF PRESENCE TEMPLATE", draft)
        self.assertIn("To Whom It May Concern,", draft)
        self.assertNotIn("SUMMARY:", draft)
        self.assertNotIn("INTERVENTION:", draft)

    def test_court_probation_letter_fallback_uses_verified_legal_style_only(self):
        brief = (
            'CT came to my office he appeared agitated. CT stated "I have court next weekend and I know they are going to lock me up on the spot." '
            "CM asked if CT would like CM to contact CT's lawyer to request a zoom court appearance. "
            "CT agreed. CM will contact CT's lawyer tomorrow 6/26/2026 during business hours."
        )
        draft = self._build_template_fallback(
            "Court / Probation Letter",
            "court_letter",
            brief,
        )

        self.assertIn("COURT / PROBATION LETTER", draft)
        self.assertIn("To Whom It May Concern,", draft)
        self.assertIn("I have court next weekend and I know they are going to lock me up on the spot.", draft)
        self.assertIn("CM will contact CT's lawyer tomorrow 6/26/2026 during business hours.", draft)
        self.assertNotIn("12-step", draft.lower())
        self.assertNotIn("sponsor", draft.lower())
        self.assertNotIn("Problem 1:", draft)

    def test_fmla_correspondence_fallback_avoids_invented_medical_details(self):
        draft = self._build_template_fallback(
            "FMLA Correspondence",
            "fmla_correspondence",
            "CM faxed the requested paperwork to HR and confirmed receipt. CM will follow up next week for any missing signatures.",
        )

        self.assertIn("FMLA CORRESPONDENCE", draft)
        self.assertIn("CONTACT METHOD:", draft)
        self.assertIn("FOLLOW-UP:", draft)
        self.assertNotIn("diagnosis", draft.lower())
        self.assertNotIn("medication", draft.lower())

    def test_treatment_plan_review_allows_treatment_plan_structure(self):
        draft = self.service._build_selected_template_fallback(
            {
                "note_kind": "treatment_plan",
                "client_id": "client-1",
                "client_name": "QA TestClient-Eval",
                "user_prompt": "Client needs housing stabilization and legal follow-up.",
                "context": {
                    "template_label": "Treatment Plan Review",
                    "requested_output_mode": "document",
                },
            },
            "Problem 1: Goal\nProblem 1: Objective\nProblem 1: Plan",
        )

        self.assertIn("Problem 1: Goal", draft)
        self.assertIn("Problem 1: Objective", draft)
        self.assertIn("Problem 1: Plan", draft)

    def test_group_note_fallback_uses_group_note_structure(self):
        draft = self._build_template_fallback(
            "Group Note",
            "group_note",
            'Group discussed coping skills for stressful legal events. Client stated "I need to stay calm." CM will review coping tools next session.',
            requested_output_mode="note",
        )

        self.assertIn("GROUP TOPIC:", draft)
        self.assertIn("INTERVENTION:", draft)
        self.assertIn("CLIENT RESPONSE:", draft)
        self.assertIn("NEXT STEP:", draft)

    def test_loc_transition_note_fallback_uses_loc_transition_structure(self):
        draft = self._build_template_fallback(
            "LOC Transition Note",
            "loc_transition",
            "Client is stepping down to outpatient services next week. CM coordinated the handoff and will confirm transportation tomorrow.",
            requested_output_mode="note",
        )

        self.assertIn("CURRENT LOC:", draft)
        self.assertIn("NEW LOC / TRANSITION PLAN:", draft)
        self.assertIn("COORDINATION COMPLETED:", draft)
        self.assertNotIn("Problem 1:", draft)

    def test_discharge_and_referral_fallbacks_stay_in_their_own_structures(self):
        discharge = self._build_template_fallback(
            "Discharge Summary",
            "discharge_summary",
            "Client completed current services and will continue with outpatient care. CM provided the handoff details for follow-up next week.",
        )
        referral = self._build_template_fallback(
            "Referral Summary",
            "referral_summary",
            "Client requested dental care coordination. CM sent the referral and will verify scheduling tomorrow.",
        )

        self.assertIn("DISCHARGE STATUS:", discharge)
        self.assertIn("AFTERCARE PLAN:", discharge)
        self.assertNotIn("12-step", discharge.lower())
        self.assertIn("REFERRAL NEED:", referral)
        self.assertIn("ACTION TAKEN:", referral)
        self.assertNotIn("Problem 1:", referral)

    def test_generation_returns_provider_status_when_openai_is_unavailable(self):
        previous_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            self.service.client = None
            result = asyncio.run(
                self.service.generate_note_draft(
                    {
                        "note_kind": "progress_note",
                        "client_name": "Taylor Jones",
                        "user_prompt": "Client requested housing support.",
                        "context": {"template_label": "Weekly CM Note"},
                    }
                )
            )
        finally:
            if previous_key is not None:
                os.environ["OPENAI_API_KEY"] = previous_key

        self.assertEqual("template_fallback", result["source"])
        self.assertEqual("missing_openai_api_key", result["provider_status"]["reason"])

    def test_template_quality_review_fails_quote_placeholders(self):
        review = self.service.compliance_review(
            {
                "note_kind": "group_note",
                "content": (
                    "Location of Client: Sober Living. The client attended the group virtually via Zoom. "
                    "The client displayed active listening and self-awareness. "
                    "The client participated in each group activity. "
                    "The client stated, \"[VERBATIM TOPIC-RELATED QUOTE]\""
                ),
                "context": {"template_label": "Group Note"},
            }
        )

        quality = review["quality_review"]
        self.assertEqual("needs_review", quality["status"])
        self.assertLess(quality["score"], 100)
        self.assertIn("VERBATIM TOPIC-RELATED QUOTE", quality["unresolved_placeholders"])
        self.assertIn("VERBATIM TOPIC-RELATED QUOTE", quality["quote_placeholders"])
        self.assertIn("Draft still needs case-manager quote verification.", quality["warnings"])

    def test_template_quality_review_ignores_checkbox_markers(self):
        review = self.service.compliance_review(
            {
                "note_kind": "discharge_summary",
                "content": (
                    "DISCHARGE SUMMARY\n\n"
                    "Date of Admission: June 01, 2026\n"
                    "Date of Discharge: June 08, 2026\n"
                    "Reason for Discharge: Completed treatment\n"
                    "Initiated By: [☑] Mutual [ ] Patient [ ] Family [ ] Clinical\n\n"
                    "NARRATIVE:\nClient completed treatment and transitioned to outpatient care.\n\n"
                    "Aftercare Appointments & Recommendations: outpatient follow-up scheduled.\n"
                    "Return to Independent Residence: 1840 Recovery Way, Los Angeles, CA 90015\n"
                    "Patient Diagnosis: diagnosis documented in the clinical record"
                ),
                "context": {"template_label": "Discharge Summary"},
            }
        )

        quality = review["quality_review"]
        self.assertNotIn("☑", quality["unresolved_placeholders"])
        self.assertNotIn(" ", quality["unresolved_placeholders"])

    def test_template_quality_review_flags_placeholder_staff_signature_text(self):
        review = self.service.compliance_review(
            {
                "note_kind": "progress_note",
                "content": (
                    "WEEKLY CM NOTE\n\n"
                    "SUMMARY:\nClient requested housing follow-up.\n\n"
                    "CLIENT STATEMENT:\nNo direct client quote was documented.\n\n"
                    "NEXT STEP:\nCase Manager Name, CADC, LCSW, License #12345"
                ),
                "context": {"template_label": "Weekly CM Note"},
            }
        )

        quality = review["quality_review"]
        self.assertEqual("needs_review", quality["status"])
        self.assertIn("Case Manager Name", quality["placeholder_staff_signature"])
        self.assertIn(
            "Draft still contains placeholder staff signature or credential text.",
            quality["warnings"],
        )

    def test_auto_fill_replaces_step8_document_placeholders(self):
        self.service._get_comprehensive_client_data = lambda _client_id: {
            "core": {
                "client_id": "client-123",
                "first_name": "StepEight",
                "last_name": "TemplateClient",
                "date_of_birth": "1989-04-12",
                "address": "1840 Recovery Way, Unit 12",
                "city": "Los Angeles",
                "state": "CA",
                "zip_code": "90015",
                "intake_date": "2026-06-01",
                "program_type": "Residential SUD Treatment",
                "medical_conditions": "hypertension",
                "legal_status": "Probation",
                "benefits_status": "Medi-Cal active",
                "goals": "Complete treatment and transition to outpatient care",
                "barriers": "transportation and probation documentation",
            },
            "case_management": {
                "housing_status": "Sober living",
                "legal_status": "Probation",
                "address": "1840 Recovery Way, Unit 12",
            },
        }
        draft = self.service._auto_fill_placeholders(
            (
                "MR: [CLIENT_RECORD_NUMBER]\n"
                "Days: [TOTAL_DAYS_IN_PROGRAM]\n"
                "Org: [ORGANIZATION_ADDRESS_LINE_1]\n"
                "Admit: [ADMIT DATE]\n"
                "Dx: [COPY FROM DX BOX]\n"
                "Program: [PROGRAM_NAME]\n"
                "Focus: [PRIMARY_TREATMENT_FOCUS]\n"
                "Aftercare: [SEE TABLE BELOW]\n"
                "Quote: [VERBATIM CLIENT QUOTE THIS WEEK]"
            ),
            client_id="client-123",
            client_name="StepEight TemplateClient",
        )

        self.assertNotRegex(draft, r"\[[^\]]+\]")
        self.assertIn("client-123", draft)
        self.assertIn("Treatment Facility address on file", draft)
        self.assertIn("Diagnosis is not documented in the intake/profile", draft)
        self.assertIn("Residential SUD Treatment", draft)
        self.assertIn("Complete treatment and transition to outpatient care", draft)
        self.assertIn("transportation and probation documentation", draft)
        self.assertIn("I need structure that helps me keep moving forward.", draft)

    def test_shared_intake_context_prefers_real_client_fields(self):
        context = self.service._build_shared_intake_context(
            {
                "core": {
                    "client_id": "client-456",
                    "first_name": "Jordan",
                    "last_name": "Rivera",
                    "intake_date": "2026-06-02",
                    "program_type": "Intensive Outpatient Program",
                    "medical_conditions": "diabetes",
                    "legal_status": "Pending court date",
                    "benefits_status": "Needs Medi-Cal screening",
                    "goals": "Stabilize medication and complete IOP",
                    "barriers": "transportation",
                    "background": {
                        "diagnosis": "F10.20 Alcohol use disorder, severe",
                        "aftercare_plan": "IOP step-down and recovery meetings",
                    },
                }
            },
            client_name="Jordan Rivera",
        )

        self.assertEqual("Jordan Rivera", context["full_name"])
        self.assertEqual("Intensive Outpatient Program", context["program_type"])
        self.assertEqual("diabetes", context["medical_conditions"])
        self.assertEqual("Needs Medi-Cal screening", context["benefits_status"])
        self.assertEqual("Pending court date", context["legal_status"])
        self.assertEqual("F10.20 Alcohol use disorder, severe", context["diagnosis_summary"])
        self.assertEqual("IOP step-down and recovery meetings", context["aftercare_plan_summary"])

    def test_template_reference_context_exposes_internal_templates(self):
        context = self.service.get_template_reference_context("Do you have access to treatment plan templates?")
        self.assertIsNotNone(context)
        self.assertIn("UNIVERSAL_CM_TEMPLATES.md", context)
        self.assertIn("treatment_plan", context)

    def test_reference_library_loads_case_management_playbook(self):
        self.assertIn("Case Management Playbook.txt", self.service.reference_library_text)
        self.assertIn("Kipu", self.service.reference_library_text)

    def test_template_reference_context_includes_internal_playbook_context(self):
        context = self.service.get_template_reference_context("Write a weekly CM note using Brandon's Kipu workflow")
        self.assertIsNotNone(context)
        self.assertIn("UNIVERSAL_CM_TEMPLATES.md", context)
        self.assertIn("INTERNAL DOCUMENTATION PLAYBOOK", context)
        self.assertIn("Case Management Playbook.txt", context)

    def test_brand_guidance_context_uses_uploaded_company_material(self):
        resource = workspace_store.create_brand_resource(
            case_manager_id="cm_001",
            resource_id="test_brand_resource_context",
            name="Weekly CM Brand Guide.txt",
            category="style guide",
            description="Preferred clinical voice and signature line",
            size=120,
            content_type="text/plain",
            file_path="test_brand_resource_context.txt",
            extracted_text="Use GOAL, INTERVENTION, RESPONSE, PLAN headers. End every weekly note with the organization's signature format.",
            extraction_status="ready",
        )
        self._brand_resource_ids.append(resource["id"])

        context = self.service.get_brand_guidance_context(
            query="write a weekly case management note",
            note_kind="progress_note",
            case_manager_id="cm_001",
        )
        self.assertIsNotNone(context)
        self.assertIn("Weekly CM Brand Guide.txt", context)
        self.assertIn("organization-specific materials", context)

    def tearDown(self):
        for resource_id in self._brand_resource_ids:
            workspace_store.delete_brand_resource(resource_id)


if __name__ == "__main__":
    unittest.main()
