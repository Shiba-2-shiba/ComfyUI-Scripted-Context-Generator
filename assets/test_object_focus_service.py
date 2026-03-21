import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from object_focus_service import (
    action_policy_weight,
    background_weight_map,
    classify_object_hotspot,
    extract_action_object_flags,
    extract_object_flags,
    is_symbolic_object_text,
    slot_object_policy_weight,
    summarize_slot_object_focus,
)


class TestObjectFocusService(unittest.TestCase):
    def test_extract_object_flags_covers_runtime_object_tokens(self):
        self.assertEqual(extract_object_flags("checking phone beside a monitor"), {"phone", "screen"})
        self.assertEqual(extract_action_object_flags("holding a surfboard and coffee"), {"surfboard", "coffee"})

    def test_symbolic_object_detection_uses_shared_object_rules(self):
        self.assertTrue(is_symbolic_object_text("leaning surfboard"))
        self.assertTrue(is_symbolic_object_text("large monitor screen displaying lyrics"))
        self.assertFalse(is_symbolic_object_text("quiet empty hallway"))

    def test_shared_policy_access_matches_expected_background_and_action_weights(self):
        self.assertEqual(background_weight_map("concert_stage", "props").get("microphone stands"), 0.2)
        self.assertEqual(action_policy_weight("commuter_transport", "standing and checking phone"), 0.25)

    def test_classify_object_hotspot_uses_shared_policy_payload(self):
        self.assertEqual(classify_object_hotspot("school_library", "book"), "thematic_anchor")
        self.assertEqual(classify_object_hotspot("commuter_transport", "phone"), "true_bias_action")
        self.assertEqual(classify_object_hotspot("antique_shop", "screen"), "audit_artifact")

    def test_slot_object_policy_weight_penalizes_true_bias_and_selected_objects(self):
        weight, objects, classifications = slot_object_policy_weight(
            "commuter_transport",
            "checking phone while waiting",
            selected_objects={"phone"},
        )
        self.assertEqual(objects, {"phone"})
        self.assertEqual(classifications["phone"], "true_bias_action")
        self.assertLess(weight, 0.2)

    def test_summarize_slot_object_focus_collects_slot_map_and_classifications(self):
        summary = summarize_slot_object_focus(
            "school_library",
            {
                "posture": "reading a book quietly",
                "gaze_target": "looking at the page",
                "time_or_weather": "late daylight stretching over the tables",
            },
            ("posture", "gaze_target", "time_or_weather"),
        )
        self.assertEqual(summary["detected_objects"], ["book"])
        self.assertEqual(summary["slot_map"]["posture"], ["book"])
        self.assertEqual(summary["classifications"]["book"], "thematic_anchor")


if __name__ == "__main__":
    unittest.main()
