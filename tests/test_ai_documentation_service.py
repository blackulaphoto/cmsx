import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.modules.ai_documentation.service import DocumentationAIService


class DocumentationAIServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = DocumentationAIService()
        self.service.client = None

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


if __name__ == "__main__":
    unittest.main()
