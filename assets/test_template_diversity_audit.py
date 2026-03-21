import json
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from tools.audit_template_diversity import build_template_diversity_report, evaluate_template_diversity_thresholds


class TestTemplateDiversityAudit(unittest.TestCase):
    def test_template_diversity_report_returns_summary(self):
        report = build_template_diversity_report(seed_count=8, seed_start=0)
        self.assertIn("summary", report)
        self.assertIn("samples", report)
        self.assertEqual(report["summary"]["seed_count"], 8)
        self.assertEqual(report["summary"]["seed_start"], 0)
        self.assertTrue(report["samples"])

    def test_template_diversity_thresholds_pass_for_32_seed_audit(self):
        report = build_template_diversity_report(seed_count=32, seed_start=0)
        evaluation = evaluate_template_diversity_thresholds(report)
        self.assertTrue(
            evaluation["passed"],
            msg=f"threshold failures: {evaluation['failures']}",
        )

    def test_template_diversity_reports_multiple_action_surfaces(self):
        report = build_template_diversity_report(seed_count=32, seed_start=0)
        counts = report["summary"].get("action_surface_counts", {})
        self.assertGreaterEqual(
            len([key for key in counts if str(key).strip()]),
            2,
            msg=f"action surface counts: {counts}",
        )

    def test_template_diversity_framed_surface_stays_on_expected_body_templates(self):
        report = build_template_diversity_report(seed_count=32, seed_start=0)
        body_key_counts = report["summary"].get("action_surface_body_key_counts", {})
        framed_counts = body_key_counts.get("framed", {})
        self.assertTrue(framed_counts, msg=f"missing framed surface counts: {body_key_counts}")
        self.assertTrue(
            set(framed_counts).issubset({"body_carrying_action", "body_room_for_action"}),
            msg=f"unexpected framed body keys: {framed_counts}",
        )
        examples = report["summary"].get("action_surface_examples", {}).get("framed", [])
        self.assertTrue(examples, msg="missing framed surface examples")
        self.assertTrue(
            any("in the middle of" in example["prompt"] for example in examples),
            msg=f"framed surface examples missing expected phrasing: {examples}",
        )

    def test_template_diversity_baseline_artifact_matches_surface_summary(self):
        report = build_template_diversity_report(seed_count=32, seed_start=0)
        artifact_path = os.path.join(ROOT, "assets", "results", "template_diversity_32.json")
        with open(artifact_path, "r", encoding="utf-8") as handle:
            artifact = json.load(handle)

        self.assertEqual(
            artifact["summary"].get("action_surface_counts"),
            report["summary"].get("action_surface_counts"),
        )
        self.assertEqual(
            artifact["summary"].get("action_surface_body_key_counts"),
            report["summary"].get("action_surface_body_key_counts"),
        )


if __name__ == "__main__":
    unittest.main()
