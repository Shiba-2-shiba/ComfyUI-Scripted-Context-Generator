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
    infer_object_relation_key,
    is_symbolic_object_text,
    relation_slots_for_action,
    slot_object_policy_weight,
    summarize_object_relation_focus,
    summarize_slot_object_focus,
)


class TestObjectFocusService(unittest.TestCase):
    def test_extract_object_flags_covers_runtime_object_tokens(self):
        self.assertEqual(extract_object_flags("checking phone beside a monitor"), {"phone", "screen"})
        self.assertEqual(extract_action_object_flags("holding a surfboard and coffee"), {"surfboard", "coffee"})
        self.assertEqual(
            extract_action_object_flags("dabbing stain with napkin while people pass by a display"),
            {"display", "napkin", "people", "stain"},
        )
        self.assertEqual(extract_action_object_flags("holding a towel and searching a bag"), {"bag", "towel"})

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

    def test_slot_object_policy_weight_penalizes_solo_safety_artifacts(self):
        weight, objects, classifications = slot_object_policy_weight(
            "modern_office",
            "dabbing stain with napkin while people pass by",
            selected_objects=set(),
        )
        self.assertEqual(objects, {"napkin", "people", "stain"})
        self.assertEqual(classifications["people"], "solo_safety_artifact")
        self.assertEqual(classifications["stain"], "solo_safety_artifact")
        self.assertLess(weight, 0.1)

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

    def test_infer_object_relation_key_matches_book_reading(self):
        relation_key = infer_object_relation_key("reading a book quietly", {"book"})
        self.assertEqual(relation_key, "book:reading")

    def test_relation_slots_for_action_returns_role_bound_slots(self):
        slots = relation_slots_for_action("checking phone while waiting", {"phone"})
        self.assertIn("hand_action", slots)
        self.assertIn("gaze_target", slots)
        self.assertIn("object_state", slots)
        self.assertTrue(any("phone" in item for item in slots["hand_action"]))

    def test_unknown_relation_returns_empty_slots(self):
        self.assertEqual(relation_slots_for_action("walking through the room", set()), {})
        summary = summarize_object_relation_focus("walking through the room", set())
        self.assertEqual(summary["relation_key"], "")
        self.assertEqual(summary["required_roles"], {})


if __name__ == "__main__":
    unittest.main()
