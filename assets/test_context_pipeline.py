import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from pipeline.context_pipeline import apply_garnish, apply_scene_variation
from core.context_ops import patch_context


class TestContextPipeline(unittest.TestCase):
    def test_apply_scene_variation_original_preserves_fields_and_adds_history(self):
        ctx = patch_context({}, updates={
            "subj": "A solo girl with long hair",
            "costume": "office_lady",
            "loc": "modern_office",
            "action": "writing at a desk",
            "seed": 100,
        })
        updated, debug = apply_scene_variation(ctx, 100, "original")
        self.assertEqual(updated.loc, "modern_office")
        self.assertEqual(updated.action, "writing at a desk")
        self.assertEqual(debug.node, "ContextSceneVariator")
        self.assertEqual(len(updated.history), 1)

    def test_apply_scene_variation_updates_context_history(self):
        ctx = patch_context({}, updates={
            "subj": "business girl",
            "costume": "office_lady",
            "loc": "modern_office",
            "action": "writing at a desk",
            "seed": 101,
        })
        updated, debug = apply_scene_variation(ctx, 101, "full")
        self.assertEqual(debug.node, "ContextSceneVariator")
        self.assertGreaterEqual(len(updated.history), 1)
        self.assertIsInstance(updated.loc, str)
        self.assertIsInstance(updated.action, str)

    def test_apply_garnish_writes_extras_and_history(self):
        ctx = patch_context(
            {},
            updates={
                "action": "walking through a hallway",
                "loc": "school hallway",
                "costume": "school_uniform",
                "seed": 111,
            },
            meta={
                "mood": "quiet",
                "tags": {"time": "morning"},
            },
            extras={
                "personality": "shy",
            },
        )
        updated, garnish_text, debug = apply_garnish(ctx, 111, 3, False, personality="shy")
        self.assertIsInstance(garnish_text, str)
        self.assertIsInstance(debug, dict)
        self.assertEqual(updated.extras["garnish"], garnish_text)
        if debug:
            self.assertGreaterEqual(len(updated.history), 1)


if __name__ == "__main__":
    unittest.main()
