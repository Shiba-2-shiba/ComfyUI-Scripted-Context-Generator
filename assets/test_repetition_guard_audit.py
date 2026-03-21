import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from tools.audit_repetition_guard import build_repetition_guard_report, evaluate_repetition_guard_thresholds


class TestRepetitionGuardAudit(unittest.TestCase):
    def test_repetition_guard_report_returns_summary(self):
        report = build_repetition_guard_report(step_count=8, scenario_count=2, seed_start=0)
        self.assertIn("summary", report)
        self.assertIn("clothing_repetition", report)
        self.assertIn("scenarios", report)
        self.assertEqual(report["summary"]["scenario_count"], 2)
        self.assertEqual(report["summary"]["step_count"], 8)
        self.assertTrue(report["scenarios"])

    def test_repetition_guard_report_includes_explicit_clothing_kpi_block(self):
        report = build_repetition_guard_report(step_count=8, scenario_count=2, seed_start=0)
        clothing = report["clothing_repetition"]
        self.assertEqual(clothing["artifact_version"], 1)
        self.assertIn("kpi", clothing)
        self.assertIn("worst_recent4_signature_scenarios", clothing)
        self.assertIn("worst_adjacent_signature_scenarios", clothing)
        self.assertIn("lowest_unique_signature_scenarios", clothing)
        self.assertEqual(
            clothing["kpi"]["avg_recent4_signature_repeat_rate"],
            report["summary"]["avg_recent4_costume_signature_repeat_rate"],
        )
        self.assertEqual(
            clothing["kpi"]["avg_recent4_pack_repeat_rate"],
            report["summary"]["avg_recent4_costume_repeat_rate"],
        )
        self.assertEqual(
            clothing["thresholds"]["max_avg_recent4_signature_repeat_rate"],
            evaluate_repetition_guard_thresholds(report)["thresholds"]["max_avg_recent4_costume_signature_repeat_rate"],
        )

    def test_repetition_guard_clothing_summaries_distinguish_pack_and_signature_levels(self):
        report = build_repetition_guard_report(step_count=8, scenario_count=2, seed_start=0)
        for scenario in report["scenarios"]:
            self.assertLessEqual(
                scenario["adjacent_costume_signature_repeat_rate"],
                scenario["adjacent_costume_repeat_rate"],
            )
            self.assertLessEqual(
                scenario["recent4_costume_signature_repeat_rate"],
                scenario["recent4_costume_repeat_rate"],
            )
        for row in report["clothing_repetition"]["worst_recent4_signature_scenarios"]:
            self.assertIn("adjacent_pack_repeat_rate", row)
            self.assertIn("adjacent_signature_repeat_rate", row)
            self.assertIn("recent4_pack_repeat_rate", row)
            self.assertIn("recent4_signature_repeat_rate", row)
            self.assertLessEqual(row["adjacent_signature_repeat_rate"], row["adjacent_pack_repeat_rate"])
            self.assertLessEqual(row["recent4_signature_repeat_rate"], row["recent4_pack_repeat_rate"])

    def test_repetition_guard_thresholds_pass_for_default_audit(self):
        report = build_repetition_guard_report(step_count=32, scenario_count=8, seed_start=0)
        evaluation = evaluate_repetition_guard_thresholds(report)
        self.assertTrue(
            evaluation["passed"],
            msg=f"threshold failures: {evaluation['failures']}",
        )

    def test_repetition_guard_thresholds_pass_for_shifted_seed_window(self):
        report = build_repetition_guard_report(step_count=32, scenario_count=8, seed_start=40)
        evaluation = evaluate_repetition_guard_thresholds(report)
        self.assertTrue(
            evaluation["passed"],
            msg=f"threshold failures: {evaluation['failures']}",
        )


if __name__ == "__main__":
    unittest.main()
