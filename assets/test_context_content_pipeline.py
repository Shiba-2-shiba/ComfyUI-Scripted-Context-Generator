import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from core.context_ops import patch_context
from pipeline.content_pipeline import (
    apply_clothing_expansion,
    apply_location_expansion,
    apply_mood_expansion,
    build_prompt_from_context,
)


class TestContextContentPipeline(unittest.TestCase):
    def test_apply_mood_expansion_updates_context(self):
        ctx = patch_context({}, updates={"seed": 10}, meta={"mood": "quiet"})
        updated, expanded, staging = apply_mood_expansion(ctx, 10, "mood_map.json", "quiet")
        self.assertIsInstance(expanded, str)
        self.assertEqual(updated.meta.mood, expanded)
        self.assertEqual(updated.extras.get("staging_tags", ""), staging)

    def test_apply_clothing_expansion_writes_extras(self):
        ctx = patch_context({}, updates={"costume": "office_lady", "seed": 11}, extras={"raw_costume_key": "office_lady", "character_palette_str": "navy, white"})
        updated, clothing_prompt = apply_clothing_expansion(ctx, 11, "random", 0.3)
        self.assertIsInstance(clothing_prompt, str)
        self.assertEqual(updated.extras["clothing_prompt"], clothing_prompt)

    def test_apply_location_expansion_writes_extras(self):
        ctx = patch_context({}, updates={"loc": "classroom", "seed": 12}, extras={"raw_loc_tag": "classroom"})
        updated, location_prompt = apply_location_expansion(ctx, 12, "detailed", "auto")
        self.assertIsInstance(location_prompt, str)
        self.assertEqual(updated.extras["location_prompt"], location_prompt)

    def test_apply_location_expansion_off_avoids_lighting_segments(self):
        ctx = patch_context({}, updates={"loc": "street_cafe", "seed": 12}, extras={"raw_loc_tag": "street_cafe"})
        updated, location_prompt = apply_location_expansion(ctx, 12, "detailed", "off")
        self.assertEqual(updated.extras["location_prompt"], location_prompt)
        self.assertNotIn("golden hour", location_prompt.lower())
        self.assertNotIn("bright daylight", location_prompt.lower())
        self.assertNotIn("warm ambient", location_prompt.lower())

    def test_build_prompt_from_context_prefers_expanded_fields(self):
        ctx = patch_context(
            {},
            updates={"subj": "A solo girl", "costume": "office_lady", "loc": "classroom", "action": "reading", "seed": 13},
            meta={"mood": "quiet", "style": "photo"},
            extras={
                "clothing_prompt": "white blouse and navy skirt",
                "location_prompt": "sunlit classroom",
                "garnish": "soft smile",
                "staging_tags": "clean composition",
            },
        )
        updated, prompt = build_prompt_from_context(ctx, "", False, 13)
        self.assertEqual(updated.seed, 13)
        self.assertIsInstance(prompt, str)
        self.assertIn("sunlit classroom", prompt)


if __name__ == "__main__":
    unittest.main()
