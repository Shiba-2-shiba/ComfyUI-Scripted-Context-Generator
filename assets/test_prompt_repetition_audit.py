import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from tools.audit_prompt_repetition import build_prompt_repetition_report, evaluate_prompt_repetition_thresholds


class TestPromptRepetitionAudit(unittest.TestCase):
    def test_prompt_repetition_report_returns_summary_and_moods(self):
        report = build_prompt_repetition_report(samples_per_row=2, row_limit=6)
        self.assertIn("summary", report)
        self.assertIn("moods", report)
        self.assertIn("samples", report)
        self.assertEqual(report["summary"]["row_count"], 6)
        self.assertEqual(report["summary"]["samples_per_row"], 2)
        self.assertEqual(report["summary"]["total_samples"], 12)
        self.assertTrue(report["moods"])
        self.assertTrue(report["samples"])

    def test_prompt_repetition_report_includes_semantic_family_counts_for_each_surface(self):
        report = build_prompt_repetition_report(samples_per_row=2, row_limit=12)
        summary = report["summary"]
        for key in ("staging_family_counts", "garnish_family_counts", "final_family_counts"):
            self.assertIn(key, summary)
            self.assertEqual(
                set(summary[key]),
                {"breath", "gaze", "posture", "hands", "smile_mouth", "expression"},
            )
        self.assertGreater(
            summary["final_family_counts"]["gaze"]["count"],
            0,
            msg=f"final family counts: {summary['final_family_counts']}",
        )

    def test_prompt_repetition_thresholds_pass_for_unit_audit_shape(self):
        report = build_prompt_repetition_report(samples_per_row=2, row_limit=12)
        evaluation = evaluate_prompt_repetition_thresholds(report)
        self.assertTrue(
            evaluation["passed"],
            msg=f"threshold failures: {evaluation['failures']}",
        )

    def test_prompt_repetition_unit_report_has_artifact_metadata_without_generated_file_dependency(self):
        report = build_prompt_repetition_report(samples_per_row=2, row_limit=6)
        summary = report["summary"]

        self.assertEqual(summary["artifact_version"], 1)
        self.assertTrue(summary["prompt_source_path"].endswith("prompts.jsonl"))
        self.assertEqual(summary["row_count"], 6)
        self.assertEqual(summary["samples_per_row"], 2)
        self.assertEqual(summary["total_samples"], 12)
        self.assertIn("top_staging_tags", summary)
        self.assertIn("top_garnish_tags", summary)
        self.assertIn("top_final_tags", summary)


if __name__ == "__main__":
    unittest.main()
