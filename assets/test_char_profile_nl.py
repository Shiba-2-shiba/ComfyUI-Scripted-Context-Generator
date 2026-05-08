import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pipeline.character_profile_pipeline import build_character_profile, load_character_profiles  # noqa: E402


class TestCharacterProfileNaturalLanguage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = load_character_profiles()

    def test_random_mode_returns_sentence_like_subject_prompt(self):
        result = build_character_profile(123, "random", "", self.profiles)

        self.assertIn("subj_prompt", result)
        self.assertIn("A solo girl", result["subj_prompt"])
        self.assertIn("with", result["subj_prompt"])

    def test_fixed_mode_uses_known_character_profile(self):
        result = build_character_profile(0, "fixed", "Akane (Warrior)", self.profiles)

        self.assertEqual(result["selected_name"], "Akane (Warrior)")
        self.assertIn("high ponytail", result["subj_prompt"])
        self.assertIn("red hair", result["subj_prompt"])
        self.assertIn("green eyes", result["subj_prompt"])

    def test_fixed_mode_handles_another_known_character(self):
        result = build_character_profile(0, "fixed", "Sarah (Sunny)", self.profiles)

        self.assertEqual(result["selected_name"], "Sarah (Sunny)")
        self.assertIn("blonde hair", result["subj_prompt"])
        self.assertIn("blue eyes", result["subj_prompt"])


if __name__ == "__main__":
    unittest.main()
