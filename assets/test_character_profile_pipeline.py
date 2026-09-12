import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from nodes_context import ContextCharacterProfile
from pipeline.character_profile_pipeline import (
    build_character_profile,
    character_profile_input_types,
    load_character_profiles,
)


class TestCharacterProfilePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_path = os.path.join(ROOT, "vocab", "data", "character_profiles.json")
        cls.profiles = load_character_profiles(cls.data_path)

    def test_shared_profile_builder_returns_expected_fields(self):
        result = build_character_profile(123, "fixed", "Aiko (Quiet)", self.profiles)
        self.assertIn("A solo girl", result["subj_prompt"])
        self.assertEqual(result["selected_name"], "Aiko (Quiet)")
        self.assertEqual(result["compatibility_key"], "student")
        self.assertEqual(result["default_costume"], "school_uniform")
        self.assertIsInstance(result["personality"], str)
        self.assertIsInstance(result["color_palette_str"], str)
        self.assertIsInstance(result["color_palette"], list)

    def test_input_types_share_same_character_dropdown_contract(self):
        shared = character_profile_input_types(data_path=self.data_path)
        context_required = ContextCharacterProfile.INPUT_TYPES()["required"]
        self.assertEqual(shared["required"], context_required)


if __name__ == "__main__":
    unittest.main()
