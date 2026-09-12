import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.semantic_families import semantic_families_for_tags
from pipeline.context_pipeline import sample_garnish_fields


def _sample(action, mood, seed=42, nuance="random", max_items=3):
    garnish, debug = sample_garnish_fields(
        action_text=action,
        meta_mood_key=mood,
        seed=seed,
        max_items=max_items,
        include_camera=False,
        emotion_nuance=nuance,
        context_loc="school classroom",
        context_costume="school_uniform",
        scene_tags="{}",
        personality="",
    )
    return garnish, debug.get("decision", {})


class TestEmotionVadAlignment(unittest.TestCase):
    def test_debug_contract_includes_epig_lite_fields(self):
        garnish, decision = _sample("reading a book quietly", "quiet_focused")

        self.assertTrue(garnish)
        self.assertEqual(decision.get("emotion_role_mode"), "subject_only")
        self.assertEqual(decision.get("emotion_core"), "focus")
        self.assertIn("target_vad", decision)
        self.assertIn("vad_category_distances", decision)
        self.assertIn("vad_descriptor_rankings", decision)
        self.assertEqual(decision.get("stimulus_role"), "reading a book quietly")
        self.assertEqual(decision.get("context_role", {}).get("location"), "school classroom")

    def test_high_arousal_moods_have_higher_target_arousal_than_low_arousal_moods(self):
        _low_garnish, low = _sample("sitting and reading", "peaceful_relaxed", seed=7)
        _high_garnish, high = _sample("waiting in a dark hallway", "creepy_fear", seed=7)

        self.assertLess(low["target_vad"][1], high["target_vad"][1])
        self.assertEqual(low["emotion_core"], "relax")
        self.assertEqual(high["emotion_core"], "impatience")

    def test_tense_action_raises_target_arousal(self):
        _calm_garnish, calm = _sample("standing still", "quiet_focused", seed=8)
        _tense_garnish, tense = _sample("arguing in a hallway", "quiet_focused", seed=8)

        self.assertGreater(tense["target_vad"][1], calm["target_vad"][1])

    def test_max_items_and_physical_expression_are_preserved(self):
        for max_items in [1, 2, 3, 5]:
            with self.subTest(max_items=max_items):
                garnish, decision = _sample("running toward the station", "energetic_joy", seed=10, max_items=max_items)
                tags = [tag.strip() for tag in garnish.split(",") if tag.strip()]

                self.assertLessEqual(len(tags), max_items)
                self.assertTrue(semantic_families_for_tags(tags), msg=decision)

    def test_same_seed_is_deterministic(self):
        first = _sample("waiting by the door", "creepy_fear", seed=99)
        second = _sample("waiting by the door", "creepy_fear", seed=99)

        self.assertEqual(first, second)

    def test_context_descriptors_are_not_inserted_by_default(self):
        garnish, decision = _sample("reading a book quietly", "peaceful_relaxed", seed=11)
        tags = [tag.strip() for tag in garnish.split(",") if tag.strip()]

        self.assertEqual(decision.get("emotion_role_mode"), "subject_only")
        self.assertNotIn("dim room", tags)
        self.assertNotIn("chaotic background", tags)


if __name__ == "__main__":
    unittest.main()
