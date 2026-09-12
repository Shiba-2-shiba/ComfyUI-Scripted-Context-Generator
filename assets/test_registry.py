import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

import asset_validator
import character_service
import clothing_service
import location_service
import pipeline.action_generator as action_generator
import pipeline.clothing_builder as clothing_builder
import pipeline.context_pipeline as context_pipeline
import pipeline.location_builder as location_builder
import registry
import scene_service
from registry import (
    load_clothing_theme_map,
    load_scene_compatibility,
    resolve_character_key,
    resolve_clothing_theme,
    resolve_location_alias_map,
    resolve_location_key,
)


class TestRegistry(unittest.TestCase):
    def test_registry_exposes_only_forwarding_surface_symbols(self):
        expected_public_names = {
            "build_location_alias_layers",
            "build_location_alias_map",
            "iter_location_candidates",
            "load_action_pools",
            "load_background_alias_overrides",
            "load_background_packs",
            "load_character_profiles",
            "load_clothing_theme_map",
            "load_fallback_location_alias_map",
            "load_legacy_location_alias_map",
            "load_scene_axes",
            "load_scene_compatibility",
            "location_alias_collisions",
            "resolve_character_key",
            "resolve_clothing_theme",
            "resolve_location",
            "resolve_location_alias_map",
            "resolve_location_key",
            "unresolved_character_costumes",
        }
        self.assertEqual(set(registry.__all__), expected_public_names)
        self.assertFalse(hasattr(registry, "_load_json"))
        self.assertFalse(hasattr(registry, "DATA_DIR"))
        self.assertFalse(hasattr(registry, "_CLOTHING_THEME_ALIASES"))

    def test_registry_forwards_service_owned_helpers(self):
        self.assertIs(load_clothing_theme_map, clothing_service.load_clothing_theme_map)
        self.assertIs(resolve_clothing_theme, clothing_service.resolve_clothing_theme)
        self.assertIs(resolve_character_key, character_service.resolve_character_key)
        self.assertIs(load_scene_compatibility, scene_service.load_scene_compatibility)

    def test_repo_owned_runtime_callers_import_services_directly(self):
        self.assertIs(clothing_builder.resolve_clothing_theme, clothing_service.resolve_clothing_theme)
        self.assertIs(action_generator.resolve_location_key, location_service.resolve_location_key)
        self.assertIs(location_builder.resolve_location_key, location_service.resolve_location_key)
        self.assertIs(context_pipeline.resolve_location_key, location_service.resolve_location_key)
        self.assertIs(context_pipeline.resolve_character, character_service.resolve_character)
        self.assertIs(asset_validator.resolve_clothing_theme, clothing_service.resolve_clothing_theme)
        self.assertIs(asset_validator.load_clothing_theme_map, clothing_service.load_clothing_theme_map)
        self.assertIs(asset_validator.load_character_profiles, character_service.load_character_profiles)
        self.assertIs(asset_validator.load_scene_compatibility, scene_service.load_scene_compatibility)

    def test_location_alias_map_prefers_auto_generated_aliases(self):
        alias_map = resolve_location_alias_map()
        self.assertIn("tea room", alias_map)
        self.assertEqual(alias_map["tea room"][0], "tea_room")

    def test_resolve_location_key_handles_aliases_deterministically(self):
        self.assertEqual(resolve_location_key("classroom"), "school_classroom")
        self.assertEqual(resolve_location_key("tea room"), "tea_room")

    def test_resolve_clothing_theme_handles_legacy_aliases(self):
        self.assertEqual(resolve_clothing_theme("business girl"), "office_lady")
        self.assertEqual(resolve_clothing_theme("street casual"), "street_casual")

    def test_daily_life_themes_keep_expanded_clothing_pack_space(self):
        theme_map = load_clothing_theme_map()
        minimum_totals = {
            "office_lady": 6,
            "school_uniform": 6,
            "winter_date": 7,
            "gym_workout": 6,
            "beach_resort": 6,
            "urban_shopping": 7,
        }
        for theme, expected_total in minimum_totals.items():
            with self.subTest(theme=theme):
                groups = theme_map[theme]
                total = sum(len(groups.get(key, [])) for key in ("dresses", "separates", "outerwear"))
                self.assertGreaterEqual(total, expected_total)
                self.assertGreaterEqual(len(groups.get("dresses", [])), 2)
                self.assertGreaterEqual(len(groups.get("separates", [])), 2)
                self.assertGreaterEqual(len(groups.get("outerwear", [])), 2)

    def test_resolve_character_key_is_case_insensitive(self):
        self.assertEqual(resolve_character_key("ceo"), "CEO")


if __name__ == "__main__":
    unittest.main()
