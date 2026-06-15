import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestLocationSemantics(unittest.TestCase):
    def test_library_study_target_prefers_orderly_quiet_segments(self):
        from pipeline.location_semantics import build_scene_target_vector, rank_location_segment_options

        target = build_scene_target_vector("school_library", action_text="reading a book")
        ranked = rank_location_segment_options(
            "props",
            ["overhead transit signs", "neatly arranged shelves"],
            target,
            loc_key="school_library",
        )

        self.assertEqual(ranked[0]["text"], "neatly arranged shelves")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])

    def test_commuter_waiting_target_prefers_crowd_and_time_pressure(self):
        from pipeline.location_semantics import build_scene_target_vector, rank_location_segment_options

        target = build_scene_target_vector("commuter_transport", action_text="waiting for the next train", mood_text="tense")
        ranked = rank_location_segment_options(
            "crowd",
            ["completely empty", "commuters moving through the background"],
            target,
            loc_key="commuter_transport",
        )

        self.assertEqual(ranked[0]["text"], "commuters moving through the background")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])

    def test_unknown_location_uses_neutral_vector_without_crashing(self):
        from pipeline.location_semantics import build_scene_target_vector, rank_location_segment_options

        target = build_scene_target_vector("unknown_place", action_text="walking")
        ranked = rank_location_segment_options("props", ["plain prop"], target, loc_key="unknown_place")

        self.assertEqual(ranked[0]["text"], "plain prop")
        self.assertIn("score", ranked[0])

    def test_debug_payload_uses_config_mode_and_is_compact(self):
        from pipeline.location_semantics import (
            build_scene_target_vector,
            rank_location_segment_options,
            semantic_location_debug_payload,
        )

        target = build_scene_target_vector("school_library", action_text="studying")
        ranking = rank_location_segment_options("core", ["quiet reading tables"], target)
        payload = semantic_location_debug_payload(target_vector=target, segment_rankings={"core": ranking})

        self.assertEqual(payload["mode"], "active")
        self.assertFalse(payload["selected_by_semantic"])
        self.assertEqual(payload["segment_rankings"]["core"][0]["text"], "quiet reading tables")


if __name__ == "__main__":
    unittest.main()
