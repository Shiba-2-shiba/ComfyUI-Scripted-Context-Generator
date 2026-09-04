import json
import random
import unittest
from pathlib import Path

from core.context_ops import patch_context
from pipeline.action_generator import (
    filter_obstacle_options_for_action_load,
    generate_action_for_location,
    normalize_action_pool_for_location,
)
from pipeline.context_pipeline import (
    apply_garnish,
    apply_scene_variation,
    resolved_action_meta_tags,
)
from pipeline.mood_builder import (
    _mood_description_compatible,
    apply_mood_expansion,
)


ROOT = Path(__file__).resolve().parents[1]


class TestVariationBlindReviewRemediation(unittest.TestCase):
    REVIEWED_SEEDS = {
        1: ("concert_stage", "checking her timing"),
        2: ("gothic_bedroom", "lying down reading a book"),
        9435136036924046218: ("commuter_transport", "listening to a podcast with earbuds"),
        1149853648275787818: ("karaoke_bar", "humming while choosing the next song"),
        16086608232758145338: ("street_cafe", "lifting a coffee cup between quiet sips"),
    }

    def test_scene_action_slots_replace_stale_source_meta_roles(self):
        tags = resolved_action_meta_tags(
            {"purpose": "work", "progress": "midway", "social_distance": "alone"},
            {"purpose": "wait", "progress_state": "preparing", "social_distance": "viewer"},
        )

        self.assertEqual(tags["purpose"], "wait")
        self.assertEqual(tags["progress"], "preparing")
        self.assertEqual(tags["social_distance"], "viewer")

    def test_concert_and_karaoke_reject_incompatible_quiet_work_descriptions(self):
        concert = patch_context(
            {},
            updates={"loc": "concert_stage"},
            extras={"action_frame": {"legacy_slots": {"purpose": "shop"}}},
        )
        karaoke = patch_context(
            {},
            updates={"loc": "karaoke_bar"},
            extras={"action_frame": {"legacy_slots": {"purpose": "wait"}}},
        )

        self.assertFalse(
            _mood_description_compatible(
                "a quiet room holding around her while the task in front of her sets the pace",
                concert,
            )
        )
        self.assertFalse(
            _mood_description_compatible(
                "a studious pause where the work in front of her matters more than the noise around it",
                karaoke,
            )
        )

    def test_outdoor_courtyard_rejects_quiet_room_description(self):
        courtyard = patch_context(
            {},
            updates={"loc": "university_campus_courtyard"},
            extras={"action_frame": {"legacy_slots": {"purpose": "rest"}}},
        )

        self.assertFalse(
            _mood_description_compatible(
                "a quiet room holding around her while the task in front of her sets the pace",
                courtyard,
            )
        )

    def test_mood_expansion_preserves_raw_key_for_garnish(self):
        ctx = patch_context(
            {},
            updates={"loc": "concert_stage"},
            meta={"mood": "quiet_focused", "tags": {"purpose": "shop"}},
            extras={"action_frame": {"legacy_slots": {"purpose": "shop"}}},
        )

        updated, expanded, _staging = apply_mood_expansion(
            ctx, 1, "mood_map.json", "quiet_focused"
        )

        self.assertEqual(updated.extras["raw_mood_key"], "quiet_focused")
        self.assertNotIn("quiet room holding around her", expanded)

    def test_calm_actions_filter_high_arousal_obstacles(self):
        options = [
            "patting pockets frantically",
            "turning back suddenly",
            "checking her pockets",
        ]

        self.assertEqual(
            filter_obstacle_options_for_action_load(options, "calm"),
            ["checking her pockets"],
        )
        self.assertEqual(
            filter_obstacle_options_for_action_load(options, "tense"),
            options,
        )

    def test_seed_2_calm_pool_action_filters_high_arousal_in_final_action(self):
        action, decision = generate_action_for_location(
            "gothic_bedroom",
            {},
            {},
            random.Random(2),
            pool=[{"text": "lying down reading a book", "load": "calm"}],
        )

        self.assertEqual(decision["base_action"], "lying down reading a book")
        self.assertEqual(decision["action_load"], "calm")
        self.assertFalse(
            any(marker in action.lower() for marker in ("frantically", "suddenly", "face-palm", "panic"))
        )

    def test_reviewed_seed_stage_chain_preserves_location_action_and_raw_mood(self):
        forbidden_by_location = {
            "concert_stage": ("quiet room holding around her",),
            "gothic_bedroom": ("patting pockets frantically", "hands fidgeting"),
            "commuter_transport": (
                "between train stops",
                "last train",
                "bus interior",
                "quiet room holding around her",
            ),
            "karaoke_bar": ("studious pause", "work in front of her"),
            "street_cafe": (
                "display area",
                "rows of neatly arranged products",
                "quiet room holding around her",
            ),
        }
        for seed, (location, raw_action) in self.REVIEWED_SEEDS.items():
            with self.subTest(seed=seed, location=location):
                ctx = patch_context(
                    {},
                    updates={"loc": location, "action": raw_action},
                    meta={"mood": "quiet_focused", "tags": {"purpose": "wait"}},
                )
                scene_ctx, _scene_debug = apply_scene_variation(ctx, seed, "original")
                mood_ctx, mood_text, _staging = apply_mood_expansion(
                    scene_ctx, seed, "mood_map.json", "quiet_focused"
                )
                final_ctx, garnish, garnish_debug = apply_garnish(
                    mood_ctx, seed, 3, False
                )
                combined = " ".join((final_ctx.action, mood_text, garnish)).lower()

                self.assertEqual(final_ctx.loc, location)
                self.assertEqual(final_ctx.action, raw_action)
                self.assertEqual(final_ctx.extras["raw_mood_key"], "quiet_focused")
                self.assertEqual(
                    garnish_debug["decision"]["target_vad_source"],
                    "legacy_mood",
                )
                for forbidden in forbidden_by_location[location]:
                    self.assertNotIn(forbidden, combined)

    def test_commuter_transport_pack_supports_bus_and_train_aliases_neutrally(self):
        packs = json.loads((ROOT / "vocab/data/background_packs.json").read_text(encoding="utf-8"))
        pack = packs["commuter_transport"]
        profile_text = (ROOT / "pipeline/action_profiles.py").read_text(encoding="utf-8")
        source_pool = json.loads(
            (ROOT / "vocab/source/action_pools/commuter_transport.json").read_text(encoding="utf-8")
        )
        rendered_pool = normalize_action_pool_for_location(
            "commuter_transport", source_pool["actions"]
        )
        combined = " ".join(
            pack["environment"]
            + pack["time"]
            + [item["text"] for item in rendered_pool]
        )

        self.assertIn("departing bus", pack["aliases"])
        self.assertIn("commuter train", pack["aliases"])
        self.assertTrue(all("public-transit interior" in item for item in pack["environment"]))
        self.assertNotIn("train", combined)
        self.assertNotIn("bus", combined)
        self.assertIn('"between stops"', profile_text)
        self.assertNotIn('"between train stops"', profile_text)

    def test_street_cafe_keeps_locked_twenty_but_renders_only_coherent_actions(self):
        pools = json.loads((ROOT / "vocab/data/action_pools.json").read_text(encoding="utf-8"))
        actions = [item["text"] for item in pools["street_cafe"]]
        rendered = normalize_action_pool_for_location(
            "street_cafe", pools["street_cafe"]
        )
        rendered_actions = [item["text"] for item in rendered]

        self.assertEqual(len(actions), 20)
        self.assertEqual(len(actions), len(set(actions)))
        self.assertEqual(len(rendered_actions), 20)
        self.assertEqual(len(rendered_actions), len(set(rendered_actions)))
        self.assertFalse(any("display area" in action for action in rendered_actions))


if __name__ == "__main__":
    unittest.main()
