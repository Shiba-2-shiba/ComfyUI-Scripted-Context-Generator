import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from core.context_ops import patch_context
from core.context_state import generation_state_from_context
from pipeline.clothing_builder import apply_clothing_expansion
from pipeline.prompt_orchestrator import build_prompt_from_context


class TestContextStateAdapter(unittest.TestCase):
    def test_generation_state_reads_legacy_context_fields(self):
        ctx = patch_context(
            {},
            updates={
                "subj": "business girl",
                "costume": "office_lady",
                "loc": "modern_office",
                "action": "reviewing notes",
                "seed": 7,
            },
            extras={
                "character_name": "Fiona (Nature)",
                "personality": "serious",
                "character_palette_str": "navy, white",
                "clothing_prompt": "white blouse and navy skirt",
                "location_prompt": "sunlit office",
                "garnish": "focused gaze",
                "staging_tags": "clean composition",
            },
        )

        state = generation_state_from_context(ctx)

        self.assertEqual(state.character.character_name, "Fiona (Nature)")
        self.assertEqual(state.character.personality, "serious")
        self.assertEqual(state.character.palette, ["navy", "white"])
        self.assertEqual(state.character.source_subj_key, "business girl")
        self.assertEqual(state.clothing.raw_costume_key, "office_lady")
        self.assertEqual(state.clothing.clothing_prompt, "white blouse and navy skirt")
        self.assertEqual(state.location.raw_loc_tag, "modern_office")
        self.assertEqual(state.location.location_prompt, "sunlit office")
        self.assertEqual(state.fragments.garnish, "focused gaze")
        self.assertEqual(state.fragments.staging_tags, "clean composition")

    def test_apply_clothing_expansion_backfills_state_from_top_level_costume(self):
        ctx = patch_context(
            {},
            updates={"costume": "office_lady", "seed": 11},
            extras={"character_palette_str": "navy, white"},
        )

        updated, clothing_prompt = apply_clothing_expansion(ctx, 11, "random", 0.3)

        self.assertTrue(clothing_prompt)
        self.assertEqual(updated.extras["raw_costume_key"], "office_lady")
        self.assertEqual(updated.extras["clothing_prompt"], clothing_prompt)
        self.assertEqual(updated.extras["character_palette_str"], "navy, white")

    def test_build_prompt_from_context_uses_state_managed_prompt_fields(self):
        ctx = patch_context(
            {},
            updates={
                "subj": "A solo girl",
                "costume": "office_lady",
                "loc": "classroom",
                "action": "reading",
                "seed": 13,
            },
            meta={"mood": "quiet", "style": "photo"},
            extras={
                "clothing_prompt": "white blouse and navy skirt",
                "location_prompt": "sunlit classroom",
                "garnish": "soft smile",
                "staging_tags": "clean composition",
            },
        )

        _updated, prompt = build_prompt_from_context(ctx, "", False, 13)

        self.assertIn("white blouse and navy skirt", prompt)
        self.assertIn("sunlit classroom", prompt)
        self.assertIn("soft smile", prompt)
        self.assertNotIn("photo", prompt.lower())


if __name__ == "__main__":
    unittest.main()
