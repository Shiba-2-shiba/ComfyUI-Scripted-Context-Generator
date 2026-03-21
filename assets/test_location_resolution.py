import os
import sys
import unittest
import json
from pathlib import Path
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)
DATA_DIR = Path(ROOT) / "vocab" / "data"

import location_service
from location_service import (
    build_location_alias_layers,
    resolve_location,
    resolve_location_key,
)
from registry import resolve_location_alias_map


class TestLocationResolution(unittest.TestCase):
    def test_migrated_alias_files_classify_previous_entries(self):
        canonical = json.loads((DATA_DIR / "loc_aliases_canonical.json").read_text(encoding="utf-8"))
        legacy = json.loads((DATA_DIR / "loc_aliases_legacy.json").read_text(encoding="utf-8"))
        fallback = json.loads((DATA_DIR / "loc_aliases_fallback.json").read_text(encoding="utf-8"))
        deprecated = json.loads((DATA_DIR / "loc_aliases.json").read_text(encoding="utf-8"))

        self.assertEqual(
            canonical["aliases"],
            {
                "shopping_mall": "shopping_mall_atrium",
                "spaceship": "spaceship_bridge",
                "workshop": "clockwork_workshop",
            },
        )
        self.assertEqual(
            legacy["aliases"],
            {
                "steampunk_airship": "airship_deck",
            },
        )
        self.assertEqual(
            fallback["aliases"],
            {
                "rainy_bus_stop": "rainy_alley",
                "luxury_hotel_room": "bedroom_boudoir",
                "elegant_dining_room": "street_cafe",
                "luxury_bathroom": "bedroom_boudoir",
                "bamboo_forest": "fantasy_forest",
                "suburban_neighborhood": "winter_street",
                "rural_town_street": "winter_street",
            },
        )
        self.assertEqual(deprecated["aliases"], {})

    def test_resolve_location_prefers_pack_key(self):
        resolved = resolve_location("modern_office")
        self.assertEqual(resolved["canonical_key"], "modern_office")
        self.assertEqual(resolved["source"], "pack_key")
        self.assertEqual(resolved["layer"], "canonical")

    def test_resolve_location_uses_pack_alias(self):
        resolved = resolve_location("tea room")
        self.assertEqual(resolved["canonical_key"], "tea_room")
        self.assertEqual(resolved["matched_alias"], "tea room")
        self.assertEqual(resolved["source"], "pack_alias")
        self.assertEqual(resolved["layer"], "canonical")

    def test_resolve_location_uses_migrated_canonical_alias(self):
        resolved = resolve_location("spaceship")
        self.assertEqual(resolved["canonical_key"], "spaceship_bridge")
        self.assertEqual(resolved["source"], "canonical_alias")
        self.assertEqual(resolved["layer"], "canonical")

    def test_resolve_location_uses_override_before_legacy(self):
        resolved = resolve_location("library")
        self.assertEqual(resolved["canonical_key"], "cozy_bookstore")
        self.assertEqual(resolved["source"], "override")
        self.assertEqual(resolved["layer"], "canonical")
        self.assertEqual(resolve_location_alias_map()["library"][0], "cozy_bookstore")

    def test_resolve_location_key_handles_spacing_variants(self):
        self.assertEqual(resolve_location_key("modern office"), "modern_office")
        self.assertEqual(resolve_location_key("classroom"), "school_classroom")

    def test_resolve_location_can_fall_back_to_fallback_map(self):
        with patch.object(location_service, "load_background_packs", return_value={}):
            with patch.object(
                location_service,
                "build_location_alias_layers",
                return_value={"canonical": {}, "legacy": {}, "fallback": {"legacy alley": ["rainy_alley"]}},
            ):
                with patch.object(location_service, "_load_alias_layer_json", return_value={}):
                    with patch.object(location_service, "load_background_alias_overrides", return_value={}):
                        resolved = location_service.resolve_location("legacy alley")
        self.assertEqual(resolved["canonical_key"], "rainy_alley")
        self.assertEqual(resolved["source"], "legacy_fallback")
        self.assertEqual(resolved["layer"], "fallback")

    def test_resolve_location_uses_legacy_alias_layer_file(self):
        with patch.object(location_service, "load_background_packs", return_value={}):
            with patch.object(
                location_service,
                "build_location_alias_layers",
                return_value={"canonical": {}, "legacy": {"legacy workshop": ["clockwork_workshop"]}, "fallback": {}},
            ):
                with patch.object(location_service, "_load_alias_layer_json", return_value={}):
                    with patch.object(location_service, "load_background_alias_overrides", return_value={}):
                        resolved = location_service.resolve_location("legacy workshop")
        self.assertEqual(resolved["canonical_key"], "clockwork_workshop")
        self.assertEqual(resolved["source"], "legacy_alias")
        self.assertEqual(resolved["layer"], "legacy")

    def test_build_location_alias_layers_exposes_explicit_order(self):
        layers = build_location_alias_layers()
        self.assertEqual(tuple(layers.keys()), ("canonical", "legacy", "fallback"))
        self.assertIn("tea room", layers["canonical"])
        self.assertIn("steampunk_airship", layers["legacy"])
        self.assertIn("rainy_bus_stop", layers["fallback"])


if __name__ == "__main__":
    unittest.main()
