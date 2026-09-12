import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nodes_prompt_cleaner import PromptCleaner
from tools.run_bias_audit import (
    SampleRow,
    build_quality_metric_rows,
    classify_object_hotspot,
    detect_disallowed_fx_hits,
    detect_objects,
    detect_pattern_hits,
    detect_unwanted_noun_hits,
    get_effective_object_threshold,
    has_emotion_embodiment,
    infer_broad_scene,
    is_daily_life_loc,
    load_scene_compatibility,
    ABSTRACT_STYLE_PATTERNS,
    UNWANTED_NOUN_PATTERNS,
)


def _sample_row(**overrides):
    base = dict(
        seed=1,
        subj="girl",
        costume_key="school_uniform",
        costume_prompt="school uniform",
        input_loc="school_classroom",
        input_loc_tag="school_classroom",
        selected_loc="school_classroom",
        broad_scene="daily_life",
        is_daily_life=1,
        selected_source="existing",
        selected_action="waiting by the window",
        action_pool_loc="",
        selected_pack_key="school_classroom",
        props_included=0,
        props_count=0,
        selected_props=[],
        meta_mood_key="quiet_focused",
        meta_mood_text="the room staying still around her while she keeps her breathing even",
        garnish="steady gaze, hands held close",
        emotion_embodied=1,
        abstract_style_hits=[],
        unwanted_noun_hits=[],
        disallowed_fx_hits=[],
        location_prompt="quiet classroom with late light",
        raw_prompt="girl in school uniform, waiting by the window, steady gaze, hands held close.",
        final_prompt="girl in school uniform, waiting by the window, steady gaze, hands held close.",
        objects_bg_norm=[],
        objects_action_norm=[],
        objects_final_norm=[],
        objects_final_raw={},
    )
    base.update(overrides)
    return SampleRow(**base)


class TestBiasAuditMetrics(unittest.TestCase):
    def test_broad_scene_and_daily_life_classification(self):
        compat = load_scene_compatibility()
        self.assertTrue(is_daily_life_loc("street_cafe", compat))
        self.assertEqual(infer_broad_scene("street_cafe", compat), "daily_life")
        self.assertEqual(infer_broad_scene("spaceship_bridge", compat), "scifi")

    def test_prompt_quality_hit_detection(self):
        cleaner = PromptCleaner()
        prompt = "anime style illustration, bokeh, light leaks, trash on the floor"
        style_prompt = "photorealistic anime style illustration"
        self.assertTrue(has_emotion_embodiment("bright smile, hands held close", "bright smile, hands held close"))
        self.assertIn("anime_style", detect_pattern_hits(style_prompt, ABSTRACT_STYLE_PATTERNS))
        self.assertIn("trash", detect_pattern_hits(prompt, UNWANTED_NOUN_PATTERNS))
        self.assertEqual(detect_unwanted_noun_hits("gloom backstreet with overturned trash cans", True, "rainy_alley"), [])
        self.assertEqual(detect_unwanted_noun_hits("quiet kitchen with trash on the floor", True, "messy_kitchen"), ["trash"])
        fx_hits = detect_disallowed_fx_hits(prompt, cleaner)
        self.assertTrue(any(hit in fx_hits for hit in ["bokeh", "light leaks"]))

    def test_object_normalization_and_policy_classification(self):
        self.assertNotIn("screen", detect_objects("wooden display cart of staff picks")[0])
        self.assertNotIn("screen", detect_objects("glass display counter with accessories")[0])
        self.assertNotIn("screen", detect_objects("bright storefront displays at the mall")[0])
        self.assertNotIn("coffee", detect_objects("coffee table with books")[0])
        self.assertNotIn("surfboard", detect_objects("dark green blackboard covered in chalk equations")[0])
        self.assertIn("screen", detect_objects("large monitor screen displaying lyrics")[0])
        self.assertEqual(classify_object_hotspot("school_library", "book"), "thematic_anchor")
        self.assertEqual(classify_object_hotspot("commuter_transport", "phone"), "true_bias_action")
        self.assertEqual(get_effective_object_threshold("school_library", "book"), 0.6)

    def test_quality_metrics_gate_rows(self):
        samples = [
            _sample_row(),
            _sample_row(
                seed=2,
                selected_loc="spaceship_bridge",
                broad_scene="scifi",
                is_daily_life=0,
                emotion_embodied=0,
                abstract_style_hits=["cinematic"],
                final_prompt="cinematic girl in a spaceship corridor",
            ),
        ]
        object_rate_rows = [
            {
                "scope": "final_prompt",
                "location_name": "school_classroom",
                "object_token": "book",
                "count_location_samples": 5,
                "conditional_rate": 0.40,
                "classification": "general",
                "effective_threshold": 0.40,
            },
            {
                "scope": "final_prompt",
                "location_name": "commuter_transport",
                "object_token": "phone",
                "count_location_samples": 5,
                "conditional_rate": 0.62,
                "classification": "true_bias_action",
                "effective_threshold": 0.40,
            },
        ]

        rows = {row["metric_name"]: row for row in build_quality_metric_rows("test_run", samples, object_rate_rows)}
        self.assertEqual(rows["daily_life_share"]["status"], "fail")
        self.assertEqual(rows["emotion_embodiment_rate"]["status"], "fail")
        self.assertEqual(rows["abstract_style_term_rate"]["status"], "warn")
        self.assertEqual(rows["max_object_concentration_final_prompt"]["status"], "warn")
        self.assertEqual(rows["max_object_concentration_true_bias"]["status"], "warn")
        self.assertEqual(rows["unwanted_noun_rate"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
