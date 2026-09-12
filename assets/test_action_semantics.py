import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestActionSemantics(unittest.TestCase):
    def test_study_target_prefers_precision_and_object_coupling(self):
        from pipeline.action_semantics import build_action_target_vector, rank_action_slot_options

        target = build_action_target_vector("study")
        ranked = rank_action_slot_options(
            "hand_action",
            [
                "fingers keeping her notes in order",
                "hand shifting to keep her balance",
            ],
            target,
        )

        self.assertEqual(ranked[0]["text"], "fingers keeping her notes in order")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])

    def test_commute_target_prefers_motion_and_time_pressure(self):
        from pipeline.action_semantics import build_action_target_vector, rank_action_slot_options

        target = build_action_target_vector("commute", social_distance="crowd", loc="train_station_platform")
        ranked = rank_action_slot_options(
            "posture",
            [
                "leaning in over what she is doing",
                "braced to move at any second",
            ],
            target,
        )

        self.assertEqual(ranked[0]["text"], "braced to move at any second")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])

    def test_missing_data_or_unknown_slot_does_not_crash(self):
        from pipeline.action_semantics import build_action_target_vector, rank_action_slot_options

        target = build_action_target_vector("unknown")
        ranked = rank_action_slot_options("unknown_slot", ["plain action"], target)

        self.assertEqual(ranked[0]["text"], "plain action")
        self.assertIn("score", ranked[0])

    def test_semantic_descriptor_options_can_supply_slot_candidates(self):
        from pipeline.action_semantics import semantic_descriptor_options_for_slot

        options = semantic_descriptor_options_for_slot(
            "hand_action",
            purpose="study",
            action_verb="reading",
            object_flags={"book"},
        )

        self.assertIn("thumb keeping the page open", options)

    def test_semantic_descriptor_options_match_relation_keys(self):
        from pipeline import action_semantics

        original_lookup = action_semantics._descriptor_lookup

        def fake_lookup(slot_name):
            self.assertEqual(slot_name, "hand_action")
            return {
                "keeping the cup steady near her hands": {
                    "text": "keeping the cup steady near her hands",
                    "roles": ["hand_action"],
                    "relation_keys": ["drink:sipping"],
                },
                "turning a page with one finger": {
                    "text": "turning a page with one finger",
                    "roles": ["hand_action"],
                    "relation_keys": ["book:reading"],
                },
            }

        action_semantics._descriptor_lookup = fake_lookup
        try:
            options = action_semantics.semantic_descriptor_options_for_slot(
                "hand_action",
                relation_key="drink:sipping",
            )
            unrelated = action_semantics.semantic_descriptor_options_for_slot(
                "hand_action",
                relation_key="phone:checking",
            )
        finally:
            action_semantics._descriptor_lookup = original_lookup

        self.assertEqual(options, ["keeping the cup steady near her hands"])
        self.assertEqual(unrelated, [])

    def test_debug_payload_is_compact_and_uses_config_mode(self):
        from pipeline.action_semantics import build_action_target_vector, rank_action_slot_options, semantic_action_debug_payload

        target = build_action_target_vector("study")
        ranking = rank_action_slot_options("gaze_target", ["eyes following the detail she is working through"], target)
        payload = semantic_action_debug_payload(target_vector=target, slot_rankings={"gaze_target": ranking})

        self.assertEqual(payload["mode"], "active")
        self.assertFalse(payload["selected_by_semantic"])
        self.assertTrue(payload["semantic_scoring_enabled"])
        self.assertFalse(payload["selection_changed_by_semantic"])
        self.assertEqual(payload["changed_slots"], [])
        self.assertEqual(payload["slot_rankings"]["gaze_target"][0]["text"], "eyes following the detail she is working through")


if __name__ == "__main__":
    unittest.main()
