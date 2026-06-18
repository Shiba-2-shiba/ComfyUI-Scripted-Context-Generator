import json
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(str(ROOT))


FIXTURE_PATH = ROOT / "assets" / "fixtures" / "solo_duplicate_prompt_cases.json"


class TestSoloDuplicateRiskDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_supplied_failure_cases_are_preserved_as_regression_fixtures(self):
        self.assertEqual(len(self.cases), 5)
        self.assertEqual(
            {case["image"] for case in self.cases},
            {
                "260618-052301_00001_.png",
                "260618-052432_00001_.png",
                "260618-052518_00001_.png",
                "260618-052649_00001_.png",
                "260618-052735_00001_.png",
            },
        )

    def test_supplied_failure_cases_are_classified_by_risk_family(self):
        from core.solo_safety import solo_duplicate_risk_flags

        for case in self.cases:
            with self.subTest(case=case["name"]):
                self.assertTrue(set(case["risk_families"]) <= solo_duplicate_risk_flags(case["prompt"]))

    def test_other_person_social_and_mirror_phrases_are_not_solo_action_safe(self):
        from core.solo_safety import is_solo_action_safe_text

        unsafe_phrases = [
            "waving to a friend approaching the cafe",
            "hands moving as she talks",
            "talking quietly with classmates over lunch",
            "standing by the mirror, adjusting clothes",
            "brushing hair in front of a mirror",
            "checking reflection in the mirrored wall",
        ]
        for phrase in unsafe_phrases:
            with self.subTest(phrase=phrase):
                self.assertFalse(is_solo_action_safe_text(phrase))

    def test_viewer_facing_social_text_remains_solo_safe(self):
        from core.solo_safety import is_solo_action_safe_text

        safe_phrases = [
            "meeting the viewer with a quiet look",
            "as if responding directly to the viewer",
            "leaving room for a quiet exchange with the viewer",
            "one hand lifted mid-gesture",
        ]
        for phrase in safe_phrases:
            with self.subTest(phrase=phrase):
                self.assertTrue(is_solo_action_safe_text(phrase))

    def test_solo_template_filter_removes_location_first_templates(self):
        from prompt_renderer import _filter_solo_template_entries

        entries = [
            {"key": "subject_first", "text": "{subject_clause}, {action_clause}, in {loc}", "roles": ["neutral"]},
            {"key": "location_first", "text": "At the edge of {loc}, {subject_clause}, {action_clause}", "roles": ["neutral"]},
        ]

        filtered, dropped = _filter_solo_template_entries(entries)

        self.assertEqual([entry["key"] for entry in filtered], ["subject_first"])
        self.assertEqual([entry["key"] for entry in dropped], ["location_first"])

    def test_solo_prompt_assembly_filters_location_first_and_compacts_support_tags(self):
        from prompt_renderer import build_prompt_text

        def template_entries(section):
            if section == "intro":
                return [
                    {"key": "intro_plain_subject", "text": "{subject_clause}", "roles": ["neutral", "social"]},
                    {"key": "intro_location_first", "text": "At the edge of {loc}, {subject_clause}", "roles": ["neutral", "social"]},
                ]
            if section == "body":
                return [{"key": "body_direct_clause", "text": "{action_clause}", "roles": ["neutral", "social"]}]
            if section == "end":
                return [{"key": "end_scene_direct", "text": "{scene_clause}", "roles": ["neutral", "social"]}]
            return []

        prompt, debug = build_prompt_text(
            template="",
            composition_mode=True,
            seed=3,
            subj="a solo girl",
            costume="blue dress",
            loc="pristine modern kitchen",
            action="wiping down the counter",
            garnish="one hand lifted mid-gesture, open posture, hands moving as she talks",
            meta_mood="calm morning",
            staging_tags="quick step",
            return_debug=True,
            template_entries_fn=template_entries,
        )

        lowered = prompt.lower()
        self.assertTrue(lowered.startswith("a solo girl"))
        self.assertNotIn("at the edge of", lowered)
        self.assertIn("one hand lifted mid-gesture", lowered)
        self.assertNotIn("open posture", lowered)
        self.assertNotIn("hands moving as she talks", lowered)
        self.assertNotIn("quick step", lowered)
        self.assertEqual(debug["solo_template_filtered_keys"]["intro"], ["intro_location_first"])
        self.assertIn("open posture", debug["solo_support_dropped_tags"])
        dropped_tags = set(debug["solo_support_dropped_tags"]) | set(
            debug["semantic_family_budget"]["garnish_dropped_tags"]
        )
        self.assertIn("hands moving as she talks", dropped_tags)

    def test_solo_pool_generation_filters_friend_and_mirror_actions(self):
        import random

        from pipeline.action_generator import generate_action_for_location
        from pipeline.context_pipeline import _load_compatibility, _load_scene_axes

        compat = _load_compatibility()
        scene_axes = _load_scene_axes()
        pool = [
            {"text": "waving to a friend approaching the cafe", "load": "light"},
            {"text": "standing by the mirror, adjusting clothes", "load": "light"},
            {"text": "checking the menu beside the cafe table", "load": "light"},
        ]

        action, debug = generate_action_for_location(
            "street_cafe",
            compat,
            scene_axes,
            random.Random(2),
            pool=pool,
            recent_verbs=[],
            recent_objects=[],
        )

        lowered = action.lower()
        self.assertEqual(debug["base_action"], "checking the menu beside the cafe table")
        self.assertNotIn("friend", lowered)
        self.assertNotIn("mirror", lowered)
        self.assertNotIn("reflection", lowered)
        self.assertGreaterEqual(debug["solo_safety_filtered_pool_count"], 2)

    def test_solo_duplicate_audit_reports_known_fixture_risks(self):
        from tools.audit_solo_duplicate_risk import build_report

        report = build_report()
        self.assertEqual(report["ERROR"], [])
        fixture_findings = [
            item for item in report["WARNING"] if item["source"] == "solo_duplicate_prompt_cases"
        ]

        self.assertEqual(len(fixture_findings), 5)
        self.assertTrue(any("mirror_clone" in item["risk_families"] for item in fixture_findings))
        self.assertTrue(any("location_first_template" in item["risk_families"] for item in fixture_findings))


if __name__ == "__main__":
    unittest.main()
