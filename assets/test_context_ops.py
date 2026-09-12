import os
import sys
import unittest


sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from core.context_ops import add_note, add_warning, append_history, ensure_context, merge_context, patch_context
from core.schema import LEGACY_STYLE_NOTE
from core.schema import DebugInfo


class TestContextOps(unittest.TestCase):
    def test_ensure_context_from_dict(self):
        ctx = ensure_context({"subj": "girl"})
        self.assertEqual(ctx.subj, "girl")

    def test_patch_context_updates_top_level_and_meta(self):
        ctx = patch_context(
            {},
            updates={"subj": "runner", "seed": "9"},
            meta={"mood": "calm", "style": "soft light", "tags": {"time": "morning"}},
            extras={"garnish": "soft smile"},
        )
        self.assertEqual(ctx.subj, "runner")
        self.assertEqual(ctx.seed, 9)
        self.assertEqual(ctx.meta.mood, "calm")
        self.assertEqual(ctx.meta.style, "soft light")
        self.assertEqual(ctx.meta.tags["time"], "morning")
        self.assertEqual(ctx.extras["garnish"], "soft smile")
        self.assertIn(LEGACY_STYLE_NOTE, ctx.notes)
        self.assertEqual(ctx.warnings, [])

    def test_merge_context_prefers_overlay_non_empty_values(self):
        merged = merge_context(
            {"subj": "student", "meta": {"mood": "quiet"}},
            {"loc": "classroom", "meta": {"style": "soft light"}},
        )
        self.assertEqual(merged.subj, "student")
        self.assertEqual(merged.loc, "classroom")
        self.assertEqual(merged.meta.mood, "quiet")
        self.assertEqual(merged.meta.style, "soft light")
        self.assertIn(LEGACY_STYLE_NOTE, merged.notes)
        self.assertEqual(merged.warnings, [])

    def test_append_history_accepts_dict_and_debuginfo(self):
        ctx = append_history({}, {"node": "ContextSceneVariator", "seed": 1})
        ctx = append_history(ctx, DebugInfo(node="ContextGarnish", seed=2))
        self.assertEqual(len(ctx.history), 2)
        self.assertEqual(ctx.history[0].node, "ContextSceneVariator")
        self.assertEqual(ctx.history[1].node, "ContextGarnish")

    def test_add_warning_returns_updated_context(self):
        ctx = add_warning({}, "warn")
        self.assertEqual(ctx.warnings, ["warn"])

    def test_add_note_returns_updated_context(self):
        ctx = add_note({}, "note")
        self.assertEqual(ctx.notes, ["note"])


if __name__ == "__main__":
    unittest.main()
