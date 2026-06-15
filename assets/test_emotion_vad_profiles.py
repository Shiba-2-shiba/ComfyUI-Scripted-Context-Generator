import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestEmotionVadProfiles(unittest.TestCase):
    def test_profiles_cover_garnish_categories(self):
        from vocab import emotion_vad
        from vocab.garnish.logic import EMOTION_CATEGORIES

        self.assertEqual(emotion_vad.validate_profiles(EMOTION_CATEGORIES), [])

    def test_legacy_aliases_resolve_to_categories(self):
        from vocab import emotion_vad
        from vocab.garnish.logic import LEGACY_MAP

        for mood_key, (category, _intensity) in LEGACY_MAP.items():
            with self.subTest(mood_key=mood_key):
                self.assertEqual(emotion_vad.alias_category(mood_key), category)

    def test_vad_distance_prefers_matching_quadrants(self):
        from vocab import emotion_vad

        joy = emotion_vad.category_vad("joy")
        sadness = emotion_vad.category_vad("sadness")
        self.assertIsNotNone(joy)
        self.assertIsNotNone(sadness)
        self.assertEqual(emotion_vad.closest_category(joy, ["joy", "sadness"]), "joy")
        self.assertEqual(emotion_vad.closest_category(sadness, ["joy", "sadness"]), "sadness")


if __name__ == "__main__":
    unittest.main()
