import os
import sys
import unittest
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from vocab.garnish import logic as garnish_logic


AMBIENT_SECONDARY_PERSON_PHRASES = (
    "a few residents checking the bulletin board",
    "small groups gathering",
    "teacher supervising",
    "one child waiting near the poster board",
    "families sharing meals",
    "neighbors browsing from store to store",
    "a few shoppers scanning labels",
    "clusters of teenagers",
)


class TestSoloSafety(unittest.TestCase):
    def test_implied_crowd_occupancy_is_unsafe_without_blocking_empty_quiet_scenes(self):
        from core.solo_safety import is_solo_safe_text

        for phrase in ("standing room only", "packed like sardines"):
            with self.subTest(unsafe=phrase):
                self.assertFalse(is_solo_safe_text(phrase))
        for phrase in (
            "mostly empty seats",
            "nearly empty",
            "quiet private room",
            "quiet midday",
            "wide open aisle space",
        ):
            with self.subTest(safe=phrase):
                self.assertTrue(is_solo_safe_text(phrase))

    def test_ambient_secondary_person_phrases_are_not_solo_safe(self):
        from core.solo_safety import has_other_person_conflict, is_solo_safe_text

        for phrase in AMBIENT_SECONDARY_PERSON_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertTrue(has_other_person_conflict(phrase))
                self.assertFalse(is_solo_safe_text(phrase))

    def test_garnish_filters_people_and_spill_artifacts(self):
        unsafe_model = {
            "expression": ["looking at someone with care"],
            "gaze": ["watching people pass by"],
            "mouth": ["dabbing stain with napkin"],
            "posture": ["standing calmly"],
            "hands": ["holding wet sleeve away"],
            "behavior": ["keeping close without crowding"],
        }

        with patch.dict(garnish_logic.EMOTION_MODEL, {"care": unsafe_model}):
            tags = garnish_logic.sample_garnish(
                seed=7,
                meta_mood="care",
                action_text="standing still",
                max_items=6,
                context_loc="modern_office",
            )

        lowered = ", ".join(tags).lower()
        self.assertIn("standing calmly", lowered)
        self.assertNotIn("someone", lowered)
        self.assertNotIn("people", lowered)
        self.assertNotIn("pass by", lowered)
        self.assertNotIn("stain", lowered)
        self.assertNotIn("napkin", lowered)
        self.assertNotIn("wet sleeve", lowered)
        self.assertNotIn("crowd", lowered)


if __name__ == "__main__":
    unittest.main()
