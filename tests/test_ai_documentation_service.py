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
        self.assertIn("GOAL:", result)
        self.assertIn("INTERVENTION:", result)
        self.assertIn("RESPONSE:", result)
        self.assertIn("PLAN:", result)

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
        self.assertIn("Completion Letter Template", result)
        self.assertIn("Taylor Jones", result)
        self.assertIn("CLIENT CONTEXT:", result)
        self.assertIn("NEXT STEP:", result)

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
                    "Template: Weekly CM Note\n\n"
                    "GOAL:\nTo discuss and plan a comprehensive discharge from treatment.\n\n"
                    "INTERVENTION:\nCM reviewed housing and probation follow-up.\n\n"
                    "RESPONSE:\nClient stated, \"I want to stay on track.\"\n\n"
                    "PLAN:\nCM will verify outpatient appointment and housing documentation."
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

    def test_auto_fill_replaces_step8_document_placeholders(self):
        self.service._get_comprehensive_client_data = lambda _client_id: {
            "core": {
                "client_id": "client-123",
                "first_name": "StepEight",
                "last_name": "TemplateClient",
                "date_of_birth": "1989-04-12",
                "address": "1840 Recovery Way, Unit 12",
                "intake_date": "2026-06-01",
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
                "Quote: [VERBATIM CLIENT QUOTE THIS WEEK]"
            ),
            client_id="client-123",
            client_name="StepEight TemplateClient",
        )

        self.assertNotRegex(draft, r"\[[^\]]+\]")
        self.assertIn("client-123", draft)
        self.assertIn("Treatment Facility address on file", draft)
        self.assertIn("diagnosis documented in the clinical record", draft)
        self.assertIn("I need structure that helps me keep moving forward.", draft)

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
