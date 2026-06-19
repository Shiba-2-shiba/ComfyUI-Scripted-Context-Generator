import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from core.prompt_ir import (
    COMPONENT_NAMES,
    build_prompt_ir,
    make_prompt_component,
    prompt_ir_summary,
    render_layout_first_prompt_ir,
)
from prompt_renderer import build_prompt_text


class TestPromptIR(unittest.TestCase):
    def test_prompt_ir_rejects_invalid_component_name(self):
        with self.assertRaises(ValueError):
            make_prompt_component("camera_angle", "close-up", source="test")

    def test_prompt_ir_rejects_empty_text(self):
        with self.assertRaises(ValueError):
            make_prompt_component("subject", "  ", source="test")

    def test_prompt_ir_build_skips_empty_fragments_and_preserves_order(self):
        prompt_ir = build_prompt_ir(
            {
                "subject": "1girl, solo",
                "clothing": "",
                "location_core": "quiet classroom",
                "foreground_action": "reading notes",
            },
            source="test",
        )

        self.assertEqual(list(prompt_ir), list(COMPONENT_NAMES))
        self.assertEqual(prompt_ir["subject"][0].text, "1girl, solo")
        self.assertEqual(prompt_ir["clothing"], [])
        self.assertEqual(prompt_ir["location_core"][0].text, "quiet classroom")

    def test_layout_first_rendering_keeps_subject_before_detail(self):
        prompt_ir = build_prompt_ir(
            {
                "garnish": "soft smile",
                "subject": "1girl, solo",
                "location_core": "quiet classroom",
                "foreground_action": "reading notes",
                "clothing": "white blouse",
            },
            source="test",
        )

        rendered = render_layout_first_prompt_ir(prompt_ir)

        self.assertLess(rendered.index("1girl"), rendered.index("quiet classroom"))
        self.assertLess(rendered.index("reading notes"), rendered.index("white blouse"))

    def test_prompt_renderer_adds_passive_ir_debug_without_changing_prompt(self):
        kwargs = dict(
            template="{subject_clause}, {action_clause}, {scene_clause}.",
            composition_mode=False,
            seed=12,
            subj="1girl, solo",
            costume="white blouse",
            loc="quiet classroom",
            action="reading notes",
            garnish="soft smile",
            meta_mood="calm afternoon",
        )
        baseline_prompt = build_prompt_text(**kwargs)
        prompt, debug = build_prompt_text(
            **kwargs,
            return_debug=True,
        )

        self.assertEqual(prompt, baseline_prompt)
        self.assertIn("prompt_ir", debug)
        self.assertIn("prompt_ir_validator", debug)
        self.assertIn("prompt_candidates", debug)
        self.assertEqual(debug["prompt_ir"]["component_counts"]["subject"], 1)
        self.assertIn("subject", debug["prompt_ir"]["present_components"])
        self.assertEqual(debug["prompt_ir_validator"]["mutated"], False)
        self.assertEqual(debug["prompt_candidates"]["mode"], "passive_debug")

    def test_prompt_renderer_actively_applies_lower_risk_candidate_for_solo_prompt(self):
        prompt, debug = build_prompt_text(
            template="{subject_clause}, {action_clause}, {scene_clause}.",
            composition_mode=False,
            seed=31,
            subj="1girl, solo",
            costume="white blouse",
            loc="cozy living room with framed family photos on the wall",
            action="sitting on a sofa with pile of decorative pillows",
            return_debug=True,
        )

        lowered = prompt.lower()
        self.assertIn("1girl, solo", lowered)
        self.assertIn("sitting on a sofa", lowered)
        self.assertIn("cozy living room", lowered)
        self.assertNotIn("decorative pillows", lowered)
        self.assertNotIn("family photos", lowered)
        self.assertEqual(debug["prompt_candidates"]["mode"], "active_selection")
        self.assertTrue(debug["prompt_candidates"]["active_result"]["applied"])

    def test_prompt_renderer_repairs_location_first_solo_prompt(self):
        prompt, debug = build_prompt_text(
            template="At the edge of {loc}, {subject_clause}, {action_clause}.",
            composition_mode=False,
            seed=32,
            subj="1girl, solo",
            costume="blue dress",
            loc="pristine modern kitchen",
            action="wiping down the marble counter",
            return_debug=True,
        )

        lowered = prompt.lower()
        self.assertTrue(lowered.startswith("1girl, solo"))
        self.assertNotIn("at the edge of", lowered)
        self.assertIn("pristine modern kitchen", lowered)
        self.assertTrue(debug["prompt_candidates"]["active_result"]["applied"])
        self.assertGreater(debug["prompt_candidates"]["active_result"]["baseline_scores"]["layout_order"], 0)

    def test_prompt_ir_summary_reports_risk_families(self):
        prompt_ir = build_prompt_ir(
            {
                "subject": "1girl, solo",
                "background_context": "framed family photos on the wall",
            },
            source="test",
        )

        summary = prompt_ir_summary(prompt_ir)

        self.assertIn("family_artifact", summary["risk_families"])


if __name__ == "__main__":
    unittest.main()
