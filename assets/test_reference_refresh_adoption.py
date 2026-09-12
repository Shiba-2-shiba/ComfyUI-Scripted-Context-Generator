import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestReferenceRefreshAdoption(unittest.TestCase):
    def _write_json(self, directory: Path, name: str, payload: dict) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_text(json.dumps(payload), encoding="utf-8")

    def _write_fixture_results(self, directory: Path) -> None:
        self._write_json(
            directory,
            "epig_reference_alignment.json",
            {
                "generated_kind": "reference_alignment_audit",
                "availability": {"source_count": 3, "warning_count": 0},
                "current_vocabulary": {"exact_reference_match_count": 12},
                "emotion_profile_alignment": {"matched_count": 4},
            },
        )
        self._write_json(
            directory,
            "epig_reference_overlay.local.json",
            {
                "generated_kind": "local_reference_overlay",
                "tracked_policy": "do_not_commit_by_default",
                "extracted_term_count": 20,
                "matched_term_count": 16,
                "unmatched_term_count": 4,
                "warnings": [],
            },
        )
        self._write_json(
            directory,
            "subject_centric_descriptor_candidates.json",
            {
                "generated_kind": "subject_centric_descriptor_candidates",
                "tracked_policy": "generated_local_only",
                "descriptor_count": 10,
                "direct_count": 1,
                "needs_phrase_count": 3,
                "reject_count": 5,
                "unmatched_count": 1,
                "warning_count": 0,
            },
        )
        self._write_json(
            directory,
            "reference_dimension_projection.json",
            {
                "generated_kind": "reference_dimension_projection_audit",
                "current_vocabulary_coverage": {"matched_term_count": 16},
                "personality_dominance_projection": {"comparison_count": 9, "high_risk_count": 2},
                "dominance_decision": {"runtime_axis_adoption": "deferred"},
            },
        )
        self._write_json(
            directory,
            "llm_expanded_prompt_policy_audit.json",
            {
                "generated_kind": "llm_expanded_prompt_policy_audit",
                "row_count": 2,
                "rows_with_policy_issues": 1,
                "policy_issue_count": 4,
                "domain_counts": {"body_type": 0, "camera": 1, "quality": 1, "render": 1, "style": 1},
            },
        )

    def test_adoption_review_defers_runtime_and_score_overlay(self):
        from tools.review_reference_refresh_adoption import review_reference_refresh_adoption

        with tempfile.TemporaryDirectory() as tmpdir:
            results = Path(tmpdir) / "results"
            self._write_fixture_results(results)

            decision = review_reference_refresh_adoption(results)

        self.assertEqual(decision["generated_kind"], "reference_refresh_adoption_decision")
        self.assertEqual(decision["overall_decision"], "no_runtime_adoption_now")
        self.assertFalse(decision["decisions"]["runtime_prompt_changes"]["adopt"])
        self.assertFalse(decision["decisions"]["score_bearing_overlay"]["adopt"])
        self.assertEqual(decision["decisions"]["dominance_runtime_axis"]["status"], "audit_only")
        self.assertTrue(decision["decisions"]["repo_authored_negative_fixture"]["adopt"])
        self.assertTrue(decision["q9_acceptance"]["current_implementation_is_sufficient_for_now"])

    def test_missing_inputs_are_reported_as_warnings(self):
        from tools.review_reference_refresh_adoption import review_reference_refresh_adoption

        with tempfile.TemporaryDirectory() as tmpdir:
            decision = review_reference_refresh_adoption(Path(tmpdir) / "missing")

        self.assertGreater(decision["input_status"]["missing_count"], 0)
        self.assertTrue(decision["warnings"])

    def test_write_decision_creates_json(self):
        from tools.review_reference_refresh_adoption import review_reference_refresh_adoption, write_decision

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            results = root / "results"
            output = root / "out" / "decision.json"
            self._write_fixture_results(results)

            decision = review_reference_refresh_adoption(results)
            written = write_decision(decision, output)
            payload = json.loads(written.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_version"], "1.0")
        self.assertEqual(payload["overall_decision"], "no_runtime_adoption_now")


if __name__ == "__main__":
    unittest.main()
