import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from core.prompt_ir import build_prompt_ir
from core.prompt_ir_validator import (
    layout_order_score,
    plural_artifact_score,
    solo_conflict_score,
    validate_prompt_ir,
)


class TestPromptIRValidator(unittest.TestCase):
    def test_known_solo_conflict_phrases_score_above_clean_prompt(self):
        clean = "1girl, solo, in a quiet classroom, reading notes"
        risky = "1girl, solo, in a cafe with customers in the background, talking with friends"

        self.assertGreater(solo_conflict_score(risky), solo_conflict_score(clean))

    def test_known_plural_artifacts_are_scored(self):
        self.assertGreater(plural_artifact_score("1girl, solo, with pile of decorative pillows"), 0)

    def test_clean_solo_prompt_scores_zero_after_active_sanitization(self):
        prompt = "1girl, solo in white blouse, sitting on a sofa, in cozy living room"

        report = validate_prompt_ir(prompt)

        self.assertEqual(report["total_risk"], 0)
        self.assertEqual(report["issues"], [])

    def test_layout_order_scores_location_first_prompt_worse(self):
        good = "1girl, solo, in a quiet classroom, reading notes"
        bad = "in a quiet classroom, 1girl, solo, reading notes"

        self.assertGreater(layout_order_score(bad), layout_order_score(good))

    def test_validator_returns_structured_report_without_mutating_prompt(self):
        prompt = "1girl, solo, in a living room with framed family photos on the wall"
        prompt_ir = build_prompt_ir(
            {
                "subject": "1girl, solo",
                "background_context": "framed family photos on the wall",
            },
            source="test",
        )

        report = validate_prompt_ir(prompt_ir, rendered_text=prompt)

        self.assertIn("scores", report)
        self.assertIn("total_risk", report)
        self.assertFalse(report["mutated"])
        self.assertTrue(any(issue["family"] == "family_artifact" for issue in report["issues"]))


if __name__ == "__main__":
    unittest.main()
