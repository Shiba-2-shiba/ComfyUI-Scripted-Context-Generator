import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from pipeline.context_pipeline import (
    _build_scene_candidate_weights,
    can_generate_action_for_location,
    apply_garnish,
    apply_scene_variation,
)
from core.context_ops import append_history, patch_context
from core.schema import DebugInfo
from pipeline.location_builder import apply_location_expansion


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

    def test_apply_scene_variation_uses_source_subject_key_when_profile_overwrites_subj(self):
        ctx = patch_context(
            {},
            updates={
                "subj": "A solo girl with long hair",
                "costume": "office_lady",
                "loc": "modern_office",
                "action": "writing at a desk",
                "seed": 101,
            },
            extras={
                "source_subj_key": "business girl",
                "character_name": "Fiona (Nature)",
            },
        )
        updated, debug = apply_scene_variation(ctx, 101, "full")
        self.assertEqual(debug.node, "ContextSceneVariator")
        self.assertEqual(debug.decision["compat_subject_key"], "business girl")
        self.assertGreater(debug.decision["compatible_unique_count"], 0)
        self.assertFalse(updated.warnings)

    def test_apply_scene_variation_bridges_named_profile_without_source_subject_key(self):
        ctx = patch_context(
            {},
            updates={
                "subj": "A solo girl with long curly hair",
                "costume": "mori_natural",
                "loc": "cozy_bookstore",
                "action": "checking a small stack of books",
                "seed": 101,
            },
            extras={
                "character_name": "Fiona (Nature)",
            },
        )
        updated, debug = apply_scene_variation(ctx, 101, "full")
        self.assertEqual(debug.node, "ContextSceneVariator")
        self.assertEqual(debug.decision["compat_subject_key"], "mori girl")
        self.assertGreater(debug.decision["compatible_unique_count"], 0)
        self.assertTrue(updated.loc)

    def test_scene_candidate_weights_use_family_totals_not_candidate_count(self):
        candidates = [
            ("existing", "modern_office"),
            ("tag:office", "boardroom"),
            ("tag:office", "office_elevator"),
            ("universal", "street_cafe"),
            ("universal", "commuter_transport"),
            ("universal", "cozy_bookstore"),
            ("daily_life", "suburban_neighborhood"),
        ]
        weights = _build_scene_candidate_weights(candidates, 10.0, 40.0, 20.0, 30.0, 123, {"universal_locs": [], "loc_tags": {}})
        existing_total = sum(weight for candidate, weight in zip(candidates, weights) if candidate[0] == "existing")
        tag_total = sum(weight for candidate, weight in zip(candidates, weights) if candidate[0].startswith("tag:"))
        universal_total = sum(weight for candidate, weight in zip(candidates, weights) if candidate[0] == "universal")
        daily_life_total = sum(weight for candidate, weight in zip(candidates, weights) if candidate[0] == "daily_life")
        self.assertAlmostEqual(existing_total, 10.0, places=6)
        self.assertAlmostEqual(tag_total, 40.0, places=6)
        self.assertAlmostEqual(universal_total, 20.0, places=6)
        self.assertAlmostEqual(daily_life_total, 30.0, places=6)

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

    def test_scene_variation_uses_fallback_action_for_missing_action_pool(self):
        ctx = patch_context(
            {},
            updates={
                "subj": "business girl",
                "loc": "modern_office",
                "action": "writing at a desk",
                "seed": 101,
            },
            extras={"source_subj_key": "business girl"},
        )
        ctx = append_history(
            ctx,
            DebugInfo(node="ContextSceneVariator", seed=100, decision={"selected_loc": "modern_office", "new_action": "writing at a desk"}),
        )
        updated, debug = apply_scene_variation(ctx, 101, "full")
        self.assertNotEqual(updated.loc, "modern_office")
        self.assertTrue(can_generate_action_for_location(updated.loc))
        self.assertTrue(debug.decision.get("action_refresh_reason") in {"compositional_fallback", "location_changed"})
        self.assertIsInstance(updated.action, str)
        self.assertTrue(updated.action)
        if debug.decision.get("action_refresh_reason") == "compositional_fallback":
            self.assertEqual(debug.decision.get("generator_mode"), "compositional")
            self.assertIn("slots", debug.decision)
            self.assertIn("slot_sources", debug.decision)
            self.assertEqual(debug.decision.get("normalized_action"), updated.action)

    def test_scene_variation_penalizes_recent_location_history(self):
        ctx = patch_context(
            {},
            updates={
                "subj": "business girl",
                "loc": "modern_office",
                "action": "writing at a desk",
                "seed": 101,
            },
            extras={"source_subj_key": "business girl"},
        )
        ctx = append_history(
            ctx,
            DebugInfo(node="ContextSceneVariator", seed=100, decision={"selected_loc": "modern_office", "new_action": "writing at a desk"}),
        )
        updated, debug = apply_scene_variation(ctx, 101, "full")
        self.assertIn("recent_loc_penalty", debug.decision)
        self.assertEqual(debug.decision["recent_loc_penalty"], ["modern_office"])
        self.assertNotEqual(updated.loc, "modern_office")

    def test_scene_variation_updates_raw_loc_tag_for_downstream_location_expansion(self):
        ctx = patch_context(
            {},
            updates={
                "subj": "business girl",
                "loc": "modern_office",
                "action": "writing at a desk",
                "seed": 101,
            },
            extras={"source_subj_key": "business girl", "raw_loc_tag": "modern_office"},
        )
        ctx = append_history(
            ctx,
            DebugInfo(node="ContextSceneVariator", seed=100, decision={"selected_loc": "modern_office", "new_action": "writing at a desk"}),
        )
        updated, debug = apply_scene_variation(ctx, 101, "full")
        self.assertEqual(updated.extras["raw_loc_tag"], updated.loc)
        expanded, _location_prompt = apply_location_expansion(updated, 101, "detailed", "off")
        self.assertEqual(expanded.loc, updated.loc)
        self.assertEqual(debug.decision["selected_loc"], updated.loc)


if __name__ == "__main__":
    unittest.main()
