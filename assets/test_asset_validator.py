import json
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(str(ROOT))

from asset_validator import (
    _read_json_asset,
    load_alias_layer_asset,
    validate_assets,
    validate_alias_layer_assets,
    validate_banned_terms_in_asset,
    validate_character_assets,
    validate_location_aliases,
)
from tools.capture_asset_validator_baseline import (
    build_validator_baseline_text,
    capture_validator_baseline,
)


class TestAssetValidator(unittest.TestCase):
    def test_validate_assets_is_clean_after_targeted_cleanup(self):
        warnings = validate_assets()
        self.assertEqual(warnings, [])

    def test_capture_validator_baseline_writes_repeatable_artifact(self):
        output_path = ROOT / "assets" / "results" / "test_asset_validator_baseline.txt"
        self.addCleanup(lambda: output_path.unlink(missing_ok=True))

        written_path = capture_validator_baseline(output_path)

        self.assertEqual(written_path, output_path)
        self.assertEqual(
            output_path.read_text(encoding="utf-8"),
            build_validator_baseline_text(validate_assets()),
        )

    def test_validate_banned_terms_detects_known_collision_patterns(self):
        warnings = validate_banned_terms_in_asset(
            "fixture.json",
            {
                "details": ["depth of field"],
                "texture": ["highly detailed textures"],
                "framing": ["close-up"],
            },
        )
        self.assertTrue(any("depth of field" in item for item in warnings))
        self.assertTrue(any("highly detailed textures" in item for item in warnings))
        self.assertTrue(any("close-up" in item for item in warnings))

    def test_validate_banned_terms_ignores_slim_fit_false_positive(self):
        warnings = validate_banned_terms_in_asset(
            "clothing_packs.json",
            {"outerwear": [{"details": ["slim-fit jacket", "tailored coat"]}]},
        )
        self.assertEqual(warnings, [])

    def test_garnish_exclusive_groups_do_not_expose_banned_framing_terms(self):
        warnings = validate_banned_terms_in_asset(
            "garnish_exclusive_groups.json",
            _read_json_asset("garnish_exclusive_groups.json"),
        )
        self.assertEqual(warnings, [])

    def test_garnish_micro_actions_remove_explicit_camera_and_fx_phrases(self):
        payload = json.dumps(
            _read_json_asset("garnish_micro_actions.json"),
            ensure_ascii=False,
        ).lower()
        for phrase in (
            "taking a selfie",
            "holding a camera",
            "adjusting camera lens",
            "looking through viewfinder",
            "high speed",
            "floating particles",
            "glowing aura",
            "eyes glowing",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, payload)

    def test_clothing_packs_remove_body_shape_and_visual_emphasis_legacy_phrases(self):
        values_only = " ".join(
            text.lower()
            for _path, text in (
                validate_banned_terms_in_asset.__globals__["_iter_string_paths"](
                    _read_json_asset("clothing_packs.json")
                )
            )
        )
        for phrase in (
            "bodycon",
            "skin-tight",
            "thigh-high slit",
            "high slit",
            "slim-fit",
            "waist-cinched",
            "corseted waist",
            "sports bra",
            "bandeau top",
            "bikini top",
            "glowing piping",
            "glowing lines",
            "holographic visor",
            "tech visor",
            "large sunglasses",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, values_only)

    def test_background_packs_remove_banned_render_lighting_phrases(self):
        values_only = " ".join(
            text.lower()
            for _path, text in (
                validate_banned_terms_in_asset.__globals__["_iter_string_paths"](
                    _read_json_asset("background_packs.json")
                )
            )
        )
        for phrase in (
            "soft indoor light",
            "fluorescent white",
            "warm ambient",
            "desk lamp glow",
            "window light",
            "bright retail lighting",
            "spotlight display",
            "neon signs",
            "modern art abstract painting",
            "warm ambient lighting",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, values_only)

    def test_validate_location_aliases_detects_empty_and_duplicate_aliases(self):
        warnings = validate_location_aliases(
            {
                "pack_a": {"aliases": ["shared alias", "", "shared alias"]},
                "pack_b": {"aliases": ["shared alias"]},
            },
            {},
        )
        self.assertTrue(any("is empty" in item for item in warnings))
        self.assertTrue(any("duplicate alias 'shared alias'" in item for item in warnings))
        self.assertTrue(any("shared by multiple packs" in item for item in warnings))

    def test_validate_alias_layer_assets_accepts_current_migrated_files(self):
        warnings = validate_alias_layer_assets(
            {
                "shopping_mall_atrium": {},
                "spaceship_bridge": {},
                "clockwork_workshop": {},
                "airship_deck": {},
                "rainy_alley": {},
                "bedroom_boudoir": {},
                "street_cafe": {},
                "fantasy_forest": {},
                "winter_street": {},
            },
            {
                "canonical": load_alias_layer_asset("canonical"),
                "legacy": load_alias_layer_asset("legacy"),
                "fallback": load_alias_layer_asset("fallback"),
            },
        )
        self.assertEqual(warnings, [])

    def test_validate_alias_layer_assets_flags_canonical_scene_remap(self):
        warnings = validate_alias_layer_assets(
            {
                "existing_scene": {},
                "other_scene": {},
            },
            {
                "canonical": {
                    "filename": "loc_aliases_canonical.json",
                    "layer": "canonical",
                    "schema_version": "2.0",
                    "aliases": {"existing_scene": ["other_scene"]},
                    "notes": {"existing_scene": "bad canonical remap"},
                },
                "legacy": {
                    "filename": "loc_aliases_legacy.json",
                    "layer": "legacy",
                    "schema_version": "2.0",
                    "aliases": {},
                    "notes": {},
                },
                "fallback": {
                    "filename": "loc_aliases_fallback.json",
                    "layer": "fallback",
                    "schema_version": "2.0",
                    "aliases": {},
                    "notes": {},
                },
            },
        )
        self.assertTrue(any("must not remap canonical pack key" in item for item in warnings))

    def test_validate_alias_layer_assets_flags_unknown_targets_and_missing_notes(self):
        warnings = validate_alias_layer_assets(
            {
                "known_scene": {},
            },
            {
                "canonical": {
                    "filename": "loc_aliases_canonical.json",
                    "layer": "canonical",
                    "schema_version": "2.0",
                    "aliases": {"alias_one": ["missing_scene"]},
                    "notes": {},
                },
                "legacy": {
                    "filename": "loc_aliases_legacy.json",
                    "layer": "legacy",
                    "schema_version": "2.0",
                    "aliases": {},
                    "notes": {},
                },
                "fallback": {
                    "filename": "loc_aliases_fallback.json",
                    "layer": "fallback",
                    "schema_version": "2.0",
                    "aliases": {},
                    "notes": {},
                },
            },
        )
        self.assertTrue(any("targets unknown canonical location" in item for item in warnings))
        self.assertTrue(any("is missing migration note" in item for item in warnings))

    def test_validate_character_assets_detects_unresolved_costume_and_missing_bridge(self):
        warnings = validate_character_assets(
            {
                "Broken Hero": {"default_costume": "missing_theme"},
                "Isolated Idol": {"default_costume": "idols_stage"},
            },
            {
                "student": {"default_costume": "school_uniform"},
            },
            {
                "school_uniform": {},
                "idols_stage": {},
            },
        )
        self.assertTrue(any("Broken Hero" in item and "unresolved default costume" in item for item in warnings))
        self.assertTrue(any("Isolated Idol" in item and "not connected" in item for item in warnings))


if __name__ == "__main__":
    unittest.main()
