import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from pipeline.action_generator import action_verb
from tools.audit_action_diversity import build_action_diversity_report, evaluate_action_diversity_thresholds


class TestActionDiversityAudit(unittest.TestCase):
    def test_daily_life_audit_returns_summary_and_locations(self):
        report = build_action_diversity_report(scope="daily_life", seed_count=8)
        self.assertEqual(report["scope"], "daily_life")
        self.assertEqual(report["seed_count"], 8)
        self.assertIn("summary", report)
        self.assertIn("locations", report)
        self.assertTrue(report["locations"])
        first = report["locations"][0]
        self.assertIn("unique_action_rate", first)
        self.assertIn("unique_slot_signature_rate", first)
        self.assertIn("generator_modes", first)

    def test_daily_life_32_seed_audit_meets_phase3_thresholds(self):
        report = build_action_diversity_report(scope="daily_life", seed_count=32)
        evaluation = evaluate_action_diversity_thresholds(report)
        self.assertTrue(
            evaluation["passed"],
            msg=f"threshold failures: {evaluation['failures']}",
        )

    def test_fragment_subject_verb_normalization_survives_generic_anchor_removal(self):
        action = "hands settling and then shifting again near the part of the scene she is using"
        self.assertEqual(action_verb(action), "settling")


if __name__ == "__main__":
    unittest.main()
