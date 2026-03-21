import os
import sys
import unittest
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from character_service import load_character_profiles, resolve_character
from registry import resolve_character_key


class TestCharacterResolution(unittest.TestCase):
    def test_named_profile_resolves_to_generic_compatibility_archetype(self):
        resolved = resolve_character(character_name="Fiona (Nature)")
        self.assertEqual(resolved["profile_key"], "Fiona (Nature)")
        self.assertEqual(resolved["compatibility_key"], "mori girl")
        self.assertEqual(resolved["default_costume"], "mori_natural")
        self.assertIn("nature", resolved["compatibility_tags"])

    def test_source_subject_key_takes_priority_over_named_profile_bridge(self):
        resolved = resolve_character(
            raw="A solo girl with long curly hair",
            source_subj_key="business girl",
            character_name="Fiona (Nature)",
        )
        self.assertEqual(resolved["compatibility_key"], "business girl")
        self.assertEqual(resolved["profile_key"], "Fiona (Nature)")

    def test_generic_archetype_resolves_case_insensitively(self):
        self.assertEqual(resolve_character_key("ceo"), "CEO")

    def test_profile_without_compatibility_returns_warning(self):
        with patch("character_service.load_character_profiles", return_value={
            "Custom Idol": {
                "visual_traits": {"hair_color": "pink", "eye_color": "blue"},
                "personality": "bright",
                "default_costume": "idols_stage",
                "color_palette": ["pink", "white"],
            }
        }):
            with patch("character_service.load_scene_compatibility", return_value={"characters": {}}):
                resolved = resolve_character(character_name="Custom Idol")
        self.assertEqual(resolved["compatibility_key"], "")
        self.assertTrue(any("No compatibility archetype found" in warning for warning in resolved["warnings"]))

    def test_current_named_profiles_with_custom_costume_themes_now_resolve(self):
        expected = {
            "Diana (Noble)": "noble lady",
            "Hana (Idol)": "idol performer",
            "Jasmine (Dancer)": "dancer girl",
            "Nina (Tech)": "steampunk inventor",
            "Penelope (Steam)": "steampunk inventor",
            "Rin (Cool)": "street girl",
            "Violet (Shy)": "quiet reader",
            "Zara (Exotic)": "street girl",
        }

        for profile_name, compatibility_key in expected.items():
            with self.subTest(profile_name=profile_name):
                resolved = resolve_character(character_name=profile_name)
                self.assertEqual(resolved["compatibility_key"], compatibility_key)
                self.assertFalse(
                    any("No compatibility archetype found" in warning for warning in resolved["warnings"])
                )

    def test_all_named_profiles_resolve_without_orphan_warning(self):
        orphan_profiles = []

        for profile_name in sorted(load_character_profiles().keys()):
            resolved = resolve_character(character_name=profile_name)
            if any("No compatibility archetype found" in warning for warning in resolved["warnings"]):
                orphan_profiles.append(profile_name)

        self.assertEqual(
            orphan_profiles,
            [],
            msg=f"Named profiles missing compatibility archetypes: {', '.join(orphan_profiles)}",
        )


if __name__ == "__main__":
    unittest.main()
