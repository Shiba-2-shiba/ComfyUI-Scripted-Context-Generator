import json
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

    def test_prompt_repetition_thresholds_pass_for_default_audit_shape(self):
        report = build_prompt_repetition_report(samples_per_row=4)
        evaluation = evaluate_prompt_repetition_thresholds(report)
        self.assertTrue(
            evaluation["passed"],
            msg=f"threshold failures: {evaluation['failures']}",
        )

    def test_prompt_repetition_baseline_artifact_matches_current_summary(self):
        report = build_prompt_repetition_report(samples_per_row=8)
        artifact_path = os.path.join(ROOT, "assets", "results", "prompt_repetition_active_source_8.json")
        with open(artifact_path, "r", encoding="utf-8") as handle:
            artifact = json.load(handle)

        self.assertEqual(artifact["summary"]["row_count"], report["summary"]["row_count"])
        self.assertEqual(artifact["summary"]["samples_per_row"], report["summary"]["samples_per_row"])
        self.assertEqual(artifact["summary"]["total_samples"], report["summary"]["total_samples"])
        self.assertEqual(artifact["summary"]["mood_row_counts"], report["summary"]["mood_row_counts"])
        self.assertEqual(artifact["summary"]["top_staging_tags"][:6], report["summary"]["top_staging_tags"][:6])
        self.assertEqual(artifact["summary"]["top_garnish_tags"][:6], report["summary"]["top_garnish_tags"][:6])
        self.assertEqual(artifact["summary"]["top_final_tags"][:6], report["summary"]["top_final_tags"][:6])
        self.assertEqual(
            artifact["summary"]["moods_with_single_staging_signature"],
            report["summary"]["moods_with_single_staging_signature"],
        )


if __name__ == "__main__":
    unittest.main()
