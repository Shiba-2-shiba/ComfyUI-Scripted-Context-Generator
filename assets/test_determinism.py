# -*- coding: utf-8 -*-
"""
test_determinism.py

Ensures that the prompt generation is strictly deterministic based on the seed.
"""
import sys
import os
import json
import unittest

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
if ASSETS_DIR not in sys.path:
    sys.path.insert(0, ASSETS_DIR)

import test_bootstrap  # noqa: F401 — パッケージコンテキストを自動解決
from pipeline.content_pipeline import (
    build_prompt_text,
    expand_clothing_prompt,
    expand_dictionary_value,
    expand_location_prompt,
)
from pipeline.context_pipeline import sample_garnish_fields
from pipeline.source_pipeline import parse_prompt_source_fields

class TestDeterminism(unittest.TestCase):
    def setUp(self):
        self.template = "A of {subj} wearing {costume}. She is {action}, {garnish}. The background is {loc}, with {meta_mood}."
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.mood_map = os.path.join(base_dir, "mood_map.json")
        
        # Load a sample pack (first one from prompts.jsonl)
        with open(os.path.join(base_dir, "prompts.jsonl"), "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self.pack = json.loads(line)
                    break

    def generate_once(self, seed):
        js = json.dumps(self.pack, ensure_ascii=False)
        subj, costume_key, loc_tag, action_raw, meta_mood_key, raw_meta_style, scene_tags = parse_prompt_source_fields(js, seed)
        meta_style = raw_meta_style

        costume = expand_clothing_prompt(costume_key, seed, "random", 0.3)
        loc = expand_location_prompt(loc_tag, seed, "detailed")
        meta_mood = expand_dictionary_value(
            key=meta_mood_key,
            json_path=self.mood_map,
            default_value=meta_mood_key,
            seed=seed,
        )[0]

        garnish = sample_garnish_fields(
            action_text=action_raw,
            meta_mood_key=meta_mood_key,
            seed=seed,
            max_items=3,
            include_camera=False,
            context_loc=loc_tag,
            context_costume=costume_key,
        )[0]
        final = build_prompt_text(
            template=self.template,
            composition_mode=False,
            seed=seed,
            subj=subj,
            costume=costume,
            loc=loc,
            action=action_raw,
            garnish=garnish,
            meta_mood=meta_mood,
            meta_style=meta_style
        )
        return final

    def test_same_seed_produces_identical_output(self):
        seed = 12345
        out1 = self.generate_once(seed)
        out2 = self.generate_once(seed)
        self.assertEqual(out1, out2, "Output must be identical for the same seed")
        
    def test_different_seed_produces_different_output(self):
        out1 = self.generate_once(12345)
        out2 = self.generate_once(67890)
        # It's statistically very likely to be different, but technically possible to be same if the pack is very rigid.
        # But we expect difference in general.
        self.assertNotEqual(out1, out2, "Output should vary with different seeds")

if __name__ == "__main__":
    unittest.main()
