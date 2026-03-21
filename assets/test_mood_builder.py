import json
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from core.context_ops import patch_context
from pipeline.mood_builder import (
    DEFAULT_STAGING_TAG_LIMIT,
    apply_mood_expansion,
    expand_dictionary_value,
    select_staging_tags,
    serialize_staging_tags,
)


class TestMoodBuilder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mood_map_path = os.path.join(ROOT, "mood_map.json")
        with open(cls.mood_map_path, "r", encoding="utf-8") as handle:
            cls.mood_map = json.load(handle)

    def test_select_staging_tags_is_deterministic_for_same_seed(self):
        staging = self.mood_map["quiet_focused"]["staging_tags"]
        first = select_staging_tags(staging, seed=17, max_items=2)
        second = select_staging_tags(staging, seed=17, max_items=2)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 2)

    def test_select_staging_tags_preserves_source_order_in_sampled_subset(self):
        staging = self.mood_map["quiet_focused"]["staging_tags"]
        selected = select_staging_tags(staging, seed=23, max_items=3)
        source_positions = [staging.index(tag) for tag in selected]
        self.assertEqual(source_positions, sorted(source_positions))

    def test_select_staging_tags_can_produce_multiple_signatures_across_seeds(self):
        staging = self.mood_map["quiet_focused"]["staging_tags"]
        signatures = {
            tuple(select_staging_tags(staging, seed=seed, max_items=2))
            for seed in range(12)
        }
        self.assertGreater(
            len(signatures),
            1,
            msg=f"sampled signatures did not vary: {signatures}",
        )

    def test_expand_dictionary_value_default_path_keeps_full_staging_bundle(self):
        _description, staging_text = expand_dictionary_value(
            "quiet_focused",
            self.mood_map_path,
            "quiet_focused",
            seed=10,
        )
        self.assertEqual(
            staging_text,
            ", ".join(self.mood_map["quiet_focused"]["staging_tags"]),
        )

    def test_expand_dictionary_value_supports_deterministic_staging_limit(self):
        _description, staging_text = expand_dictionary_value(
            "quiet_focused",
            self.mood_map_path,
            "quiet_focused",
            seed=10,
            staging_tag_limit=2,
        )
        expected = serialize_staging_tags(
            select_staging_tags(self.mood_map["quiet_focused"]["staging_tags"], seed=10, max_items=2)
        )
        self.assertEqual(staging_text, expected)
        self.assertEqual(len([tag for tag in staging_text.split(", ") if tag.strip()]), 2)

    def test_apply_mood_expansion_forwards_staging_limit(self):
        ctx = patch_context({}, updates={"seed": 10}, meta={"mood": "quiet_focused"})
        updated, _expanded, staging = apply_mood_expansion(
            ctx,
            10,
            self.mood_map_path,
            "quiet_focused",
            staging_tag_limit=2,
        )
        self.assertEqual(updated.extras.get("staging_tags", ""), staging)
        self.assertEqual(len([tag for tag in staging.split(", ") if tag.strip()]), 2)

    def test_apply_mood_expansion_defaults_to_runtime_staging_limit(self):
        ctx = patch_context({}, updates={"seed": 10}, meta={"mood": "quiet_focused"})
        updated, _expanded, staging = apply_mood_expansion(
            ctx,
            10,
            self.mood_map_path,
            "quiet_focused",
        )
        expected = serialize_staging_tags(
            select_staging_tags(
                self.mood_map["quiet_focused"]["staging_tags"],
                seed=10,
                max_items=DEFAULT_STAGING_TAG_LIMIT,
            )
        )
        self.assertEqual(updated.extras.get("staging_tags", ""), staging)
        self.assertEqual(staging, expected)
        self.assertEqual(
            len([tag for tag in staging.split(", ") if tag.strip()]),
            DEFAULT_STAGING_TAG_LIMIT,
        )


if __name__ == "__main__":
    unittest.main()
