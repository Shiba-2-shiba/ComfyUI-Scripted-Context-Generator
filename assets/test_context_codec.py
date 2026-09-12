import os
import sys
import unittest


sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from core.context_codec import (
    append_warning,
    context_from_json,
    context_to_dict,
    context_to_json,
    make_empty_context,
    normalize_context_data,
)


class TestContextCodec(unittest.TestCase):
    def test_make_empty_context_uses_seed(self):
        ctx = make_empty_context(seed=42)
        self.assertEqual(ctx.seed, 42)
        self.assertEqual(ctx.context_version, "2.0")

    def test_normalize_legacy_payload_adds_warning(self):
        ctx = normalize_context_data({
            "subj": "girl",
            "meta": {"mood": "quiet"},
        })
        self.assertEqual(ctx.subj, "girl")
        self.assertEqual(ctx.meta.mood, "quiet")
        self.assertEqual(ctx.context_version, "2.0")
        self.assertIn("Legacy context payload normalized to v2", ctx.warnings)

    def test_normalize_non_dict_falls_back(self):
        ctx = normalize_context_data(["bad"], default_seed=5)
        self.assertEqual(ctx.seed, 5)
        self.assertTrue(ctx.warnings)

    def test_context_from_json_invalid_payload(self):
        ctx = context_from_json("{broken", default_seed=7)
        self.assertEqual(ctx.seed, 7)
        self.assertTrue(ctx.warnings)

    def test_context_from_json_empty_payload(self):
        ctx = context_from_json("", default_seed=3)
        self.assertEqual(ctx.seed, 3)
        self.assertEqual(ctx.subj, "")

    def test_context_to_json_roundtrip(self):
        json_str = context_to_json({
            "subj": "runner",
            "extras": {"garnish": "wind-swept hair"},
        })
        ctx = context_from_json(json_str)
        self.assertEqual(ctx.subj, "runner")
        self.assertEqual(ctx.extras["garnish"], "wind-swept hair")

    def test_context_to_dict_from_promptcontext(self):
        ctx = make_empty_context(seed=8)
        ctx.subj = "student"
        data = context_to_dict(ctx)
        self.assertEqual(data["seed"], 8)
        self.assertEqual(data["subj"], "student")

    def test_append_warning_returns_copy(self):
        ctx = make_empty_context()
        updated = append_warning(ctx, "hello")
        self.assertEqual(ctx.warnings, [])
        self.assertEqual(updated.warnings, ["hello"])


if __name__ == "__main__":
    unittest.main()
