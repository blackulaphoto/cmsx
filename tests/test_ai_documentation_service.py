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

    def test_template_reference_context_exposes_internal_templates(self):
        context = self.service.get_template_reference_context("Do you have access to treatment plan templates?")
        self.assertIsNotNone(context)
        self.assertIn("UNIVERSAL_CM_TEMPLATES.md", context)
        self.assertIn("treatment_plan", context)

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
