import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from core.prompt_ir import build_prompt_ir
from core.prompt_ir_validator import validate_prompt_ir
from pipeline.prompt_candidate_generator import generate_prompt_candidates
from pipeline.prompt_candidate_selector import select_prompt_candidate, summarize_prompt_candidates


class TestPromptCandidateRerank(unittest.TestCase):
    def test_same_seed_produces_same_candidates(self):
        prompt_ir = build_prompt_ir(
            {
                "subject": "1girl, solo",
                "location_core": "living room",
                "background_context": "framed family photos on the wall",
            },
            source="test",
        )

        first = generate_prompt_candidates(prompt_ir, rendered_text="1girl, solo, in living room", seed=42)
        second = generate_prompt_candidates(prompt_ir, rendered_text="1girl, solo, in living room", seed=42)

        self.assertEqual(
            [(item["candidate_id"], item["branch_seed"], item["rendered_text"]) for item in first],
            [(item["candidate_id"], item["branch_seed"], item["rendered_text"]) for item in second],
        )

    def test_branch_ids_are_distinct_and_subject_does_not_branch(self):
        prompt_ir = build_prompt_ir(
            {
                "subject": "1girl, solo",
                "background_context": "framed family photos on the wall",
            },
            source="test",
        )

        candidates = generate_prompt_candidates(prompt_ir, rendered_text="1girl, solo, framed family photos", seed=7)

        self.assertEqual(len(candidates), 2)
        self.assertNotEqual(candidates[0]["candidate_id"], candidates[1]["candidate_id"])
        self.assertEqual(candidates[1]["ir"]["subject"][0].text, "1girl, solo")
        self.assertEqual(candidates[1]["dropped_components"][0]["component"], "background_context")

    def test_selector_prefers_lower_risk_candidate_with_requested_mode(self):
        prompt_ir = build_prompt_ir(
            {
                "subject": "1girl, solo",
                "background_context": "framed family photos on the wall",
            },
            source="test",
        )
        candidates = generate_prompt_candidates(
            prompt_ir,
            rendered_text="1girl, solo, framed family photos on the wall",
            seed=9,
        )

        selected = select_prompt_candidate(candidates, mode="active_selection")
        summary = summarize_prompt_candidates(candidates, mode="active_selection")

        self.assertEqual(selected["candidate_id"], "seed:9:branch:1")
        self.assertEqual(selected["selection"]["mode"], "active_selection")
        self.assertNotIn("family photos", selected["rendered_text"])
        self.assertEqual(summary["selected_candidate_id"], "seed:9:branch:1")
        self.assertEqual(summary["mode"], "active_selection")

    def test_sanitizing_candidate_preserves_clean_clause_remainder(self):
        prompt_ir = build_prompt_ir(
            {
                "subject": "1girl, solo",
                "location_core": "cozy living room with framed family photos on the wall",
                "foreground_action": "sitting on a sofa with pile of decorative pillows",
            },
            source="test",
        )
        candidates = generate_prompt_candidates(
            prompt_ir,
            rendered_text=(
                "1girl, solo, sitting on a sofa with pile of decorative pillows, "
                "in cozy living room with framed family photos on the wall"
            ),
            seed=10,
        )

        sanitized = candidates[1]["rendered_text"].lower()

        self.assertIn("sitting on a sofa", sanitized)
        self.assertIn("in cozy living room", sanitized)
        self.assertNotIn("decorative pillows", sanitized)
        self.assertNotIn("family photos", sanitized)

    def test_person_context_cleanup_removes_orphaned_social_fragment(self):
        prompt_ir = build_prompt_ir(
            {
                "subject": "1girl, solo",
                "background_context": "talking with friends near the school gate",
            },
            source="test",
        )
        candidates = generate_prompt_candidates(
            prompt_ir,
            rendered_text="1girl, solo, talking with friends near the school gate",
            seed=11,
        )
        selected = select_prompt_candidate(candidates, mode="active_selection")
        selected_text = selected["rendered_text"].lower()

        self.assertEqual(selected["candidate_id"], "seed:11:branch:1")
        self.assertNotIn("friends", selected_text)
        self.assertNotIn("talking", selected_text)

    def test_location_first_candidate_uses_layout_repair(self):
        prompt_ir = build_prompt_ir(
            {
                "subject": "1girl, solo",
                "location_core": "pristine modern kitchen",
                "foreground_action": "wiping down the marble counter",
                "clothing": "blue dress",
            },
            source="test",
        )
        candidates = generate_prompt_candidates(
            prompt_ir,
            rendered_text="At the edge of pristine modern kitchen, 1girl, solo in blue dress, wiping down the marble counter.",
            seed=14,
        )
        selected = select_prompt_candidate(candidates, mode="active_selection")
        baseline_report = validate_prompt_ir(prompt_ir, rendered_text=candidates[0]["rendered_text"])

        self.assertEqual(selected["candidate_id"], "seed:14:branch:1")
        self.assertTrue(selected["rendered_text"].lower().startswith("1girl, solo"))
        self.assertIn("layout_first_repair", selected["warnings"])
        self.assertLess(selected["scores"]["layout_order"], baseline_report["scores"]["layout_order"])

    def test_prompt_ir_audit_report_includes_active_selection_preview(self):
        from tools.audit_prompt_ir_candidates import build_report

        report = build_report(seed_count=0)
        risky_records = [
            record
            for record in report["records"]
            if record["name"] in {"plural_prop_overload", "family_photo_artifact", "ineffective_motion"}
        ]

        self.assertEqual(report["mode"], "read_only_with_active_preview")
        self.assertGreaterEqual(report["case_count"], 40)
        self.assertEqual(report["summary"]["false_positive_cases"], [])
        self.assertEqual(report["summary"]["false_negative_cases"], [])
        self.assertEqual(report["summary"]["failed_expectation_cases"], [])
        self.assertTrue(risky_records)
        self.assertTrue(any(record["active_selection"]["applied"] for record in risky_records))
        for record in risky_records:
            selected = record["active_selection"]["rendered_text"].lower()
            self.assertNotIn("decorative pillows", selected)
            self.assertNotIn("family photos", selected)
            self.assertNotIn("quick step", selected)

    def test_prompt_ir_audit_keeps_social_only_cases_passive(self):
        from tools.audit_prompt_ir_candidates import build_report

        report = build_report(seed_count=0)
        social_only_records = [
            record
            for record in report["records"]
            if record["name"] in {"social_talk_only_variant", "conversation_without_viewer_variant"}
        ]

        self.assertEqual(len(social_only_records), 2)
        for record in social_only_records:
            self.assertFalse(record["active_selection"]["applied"])
            self.assertIn("social_interaction", record["expectation"]["detected_risk_families"])

    def test_prompt_ir_audit_report_detects_fixture_expectation_failures(self):
        from tools.audit_prompt_ir_candidates import _evaluate_case

        evaluation = _evaluate_case(
            {"expected_risk_families": ["family_artifact"], "expected_min_total_risk": 1},
            {"total_risk": 0, "issues": []},
            {"applied": False, "rendered_text": "1girl, solo"},
        )

        self.assertIn("family_artifact", evaluation["false_negative_families"])
        self.assertIn("total_risk_below_expected_min", evaluation["failures"])


if __name__ == "__main__":
    unittest.main()
