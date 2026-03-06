# -*- coding: utf-8 -*-
import json
import os
import random
import re
import unittest

from nodes_dictionary_expand import ThemeLocationExpander
from nodes_scene_variator import _choose_action_with_bias_guard, _get_compatible_locs
from nodes_scene_variator import _build_exclusion_set, _load_compatibility
from tools.run_bias_audit import detect_objects


class TestBiasControls(unittest.TestCase):
    def test_theme_location_surfboard_rate_reduced(self):
        node = ThemeLocationExpander()
        n = 600
        hits = 0
        for seed in range(n):
            out = node.expand_location("wave_barrel", seed, "detailed", "auto")[0].lower()
            if re.search(r"\bsurfboard\b|\bboard\b", out):
                hits += 1
        # Guardrail: keep board/surfboard occurrence for wave_barrel below 25%
        self.assertLess(hits / n, 0.25)

    def test_theme_location_karaoke_screen_rate_reduced(self):
        node = ThemeLocationExpander()
        n = 400
        hits = 0
        for seed in range(n):
            out = node.expand_location("karaoke_bar", seed, "detailed", "auto")[0]
            if "screen" in detect_objects(out)[0]:
                hits += 1
        self.assertLess(hits / n, 0.45)

    def test_theme_location_street_cafe_coffee_rate_reduced(self):
        node = ThemeLocationExpander()
        n = 400
        hits = 0
        for seed in range(n):
            out = node.expand_location("street_cafe", seed, "detailed", "auto")[0]
            if "coffee" in detect_objects(out)[0]:
                hits += 1
        self.assertLess(hits / n, 0.35)

    def test_theme_location_tropical_beach_surfboard_rate_reduced(self):
        node = ThemeLocationExpander()
        n = 400
        hits = 0
        for seed in range(n):
            out = node.expand_location("tropical_beach", seed, "detailed", "auto")[0]
            if "surfboard" in detect_objects(out)[0]:
                hits += 1
        self.assertLess(hits / n, 0.20)

    def test_scene_compatible_locs_are_deduplicated(self):
        compat = _load_compatibility()
        excluded = _build_exclusion_set(compat)
        locs = _get_compatible_locs("shrine maiden", compat, excluded, mode="full")
        names = [loc for loc, _ in locs]
        self.assertEqual(len(names), len(set(names)))

    def test_weighted_action_choice_penalizes_dominant_object(self):
        pool = [
            {"text": "standing on a surfboard", "load": "calm"},
            {"text": "crouching on the surfboard", "load": "calm"},
            {"text": "walking with a surfboard", "load": "calm"},
            {"text": "holding a surfboard", "load": "calm"},
            {"text": "watching the waves", "load": "calm"},
            {"text": "adjusting breathing rhythm", "load": "calm"},
        ]
        n = 2000
        surf_hits = 0
        rng = random.Random(12345)
        for _ in range(n):
            item, _, _ = _choose_action_with_bias_guard(pool, rng)
            txt = str(item.get("text", "")).lower()
            if "surfboard" in txt:
                surf_hits += 1
        # Unweighted expectation would be ~66.7%; bias guard should reduce materially.
        self.assertLess(surf_hits / n, 0.50)

    def test_commuter_transport_policy_penalizes_phone_action(self):
        pool = [
            {"text": "standing in the train, holding a strap", "load": "calm"},
            {"text": "sitting by the window, looking outside", "load": "calm"},
            {"text": "standing and checking phone", "load": "calm"},
            {"text": "holding a bag on lap tightly", "load": "calm"},
        ]
        n = 2000
        phone_hits = 0
        rng = random.Random(6789)
        for _ in range(n):
            item, _, _ = _choose_action_with_bias_guard(pool, rng, "commuter_transport")
            txt = str(item.get("text", "")).lower()
            if "phone" in txt:
                phone_hits += 1
        self.assertLess(phone_hits / n, 0.15)

    def test_scene_compatibility_duplicates_removed(self):
        path = os.path.join("vocab", "data", "scene_compatibility.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(
            len(data.get("universal_locs", [])),
            len(set(data.get("universal_locs", []))),
        )
        urban = data.get("loc_tags", {}).get("urban", [])
        self.assertEqual(len(urban), len(set(urban)))


if __name__ == "__main__":
    unittest.main()
