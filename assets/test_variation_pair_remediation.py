import json
import unittest
from pathlib import Path

from pipeline.clothing_candidate_renderer import render_clothing_candidate
from vocab.garnish.logic import TASK_FOCUSED_ACTION_VERBS, _guess_action_load


ROOT = Path(__file__).resolve().parents[1]
OVERRIDES = (
    ROOT
    / "docs"
    / "variation_expansion"
    / "experiments"
    / "v150-candidate-shape-iteration-019"
    / "location-overrides.json"
)


class VariationPairRemediationTests(unittest.TestCase):
    def test_reviewed_pairs_use_concrete_tpo_safe_actions(self):
        payload = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        locations = {item["id"]: item for item in payload["locations"]}
        expected = {
            "bike_station": "checking the route map before departure",
            "clinic_waiting_room": "checking an appointment slip against the reception display",
            "community_garden": "checking the planting chart beside the tool shed",
            "forest_cabin": "checking a trail map beside the cabin door",
            "tram_platform": "checking the arrival display beside the wet rails",
            "fire_station": "reviewing an equipment checklist beside the locker",
            "vehicle_repair_garage": "checking a vehicle service note against the panel label",
            "observatory_dome": "reviewing humidity readings before a telescope exposure",
        }

        for location_id, action_text in expected.items():
            with self.subTest(location=location_id):
                actions = locations[location_id]["action_plan"]["direct_actions"]
                self.assertIn(action_text, {item["text"] for item in actions})

    def test_pruning_is_classified_as_active(self):
        self.assertEqual(
            _guess_action_load("pruning a damaged stem with hand shears"),
            "active",
        )

    def test_followup_review_actions_are_concrete(self):
        payload = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        locations = {item["id"]: item for item in payload["locations"]}
        expected = {
            "bike_station": "checking the tire pressure guide against the pump gauge",
            "ferry_terminal": "watching ferry lights ripple across the water beneath the pier canopy",
            "forest_cabin": "checking the water-level gauge on the cabin storage tank",
            "public_plaza": "reading the event map beneath a civic information sign",
            "rooftop_cafe": "checking the skyline map beside the lit parapet",
        }
        for location_id, action_text in expected.items():
            with self.subTest(location=location_id):
                actions = locations[location_id]["action_plan"]["direct_actions"]
                self.assertIn(action_text, {item["text"] for item in actions})

        forest = locations["forest_cabin"]["background_pack"]
        greenhouse = locations["greenhouse_nursery"]["background_pack"]
        self.assertIn("amber-lit timber cabin in a conifer clearing", forest["environment"])
        self.assertIn(
            "orderly rows of labeled seedlings along the far wall",
            greenhouse["crowd"],
        )

    def test_filling_is_classified_as_active(self):
        self.assertEqual(
            _guess_action_load("filling a watering can at the utility sink"),
            "active",
        )

    def test_placing_is_classified_as_active(self):
        self.assertEqual(
            _guess_action_load("placing a price tag beside a potted plant"),
            "active",
        )

    def test_turning_is_active_and_comparing_is_task_focused(self):
        self.assertEqual(
            _guess_action_load("turning the dome slit toward the selected star field"),
            "active",
        )
        self.assertIn("comparing", TASK_FOCUSED_ACTION_VERBS)

    def test_unknown_clothing_theme_uses_concrete_fallback(self):
        prompt, _debug = render_clothing_candidate(
            "casual",
            1,
            "auto",
            0,
            "",
            [],
            [],
            [],
            [],
        )
        self.assertNotIn("generic outfit", prompt)
        self.assertEqual(prompt, "casual layered top and practical trousers")

    def test_q76_actions_remove_spatial_and_deictic_conflicts(self):
        payload = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        locations = {item["id"]: item for item in payload["locations"]}
        expected = {
            "forest_cabin": "studying fresh tracks across the cabin floor",
            "public_plaza": "walking toward the monument steps across the plaza",
            "canal_walkway": "walking beside the mossy towpath embankment",
            "community_theater_backstage": "checking a marked scene cue beside the stage entrance",
        }
        for location_id, action_text in expected.items():
            with self.subTest(location=location_id):
                actions = locations[location_id]["action_plan"]["direct_actions"]
                self.assertIn(action_text, {item["text"] for item in actions})

    def test_dense_backgrounds_bound_repeated_location_stems(self):
        payload = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        locations = {item["id"]: item for item in payload["locations"]}
        for location_id, stem in (("maker_space", "bench"), ("greenhouse_nursery", "greenhouse")):
            pack = locations[location_id]["background_pack"]
            text = " ".join(
                str(value)
                for values in pack.values()
                if isinstance(values, list)
                for value in values
            ).casefold()
            with self.subTest(location=location_id):
                self.assertLessEqual(text.count(stem), 1)

    def test_q80_actions_ground_the_protagonist_in_visible_objects(self):
        payload = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        locations = {item["id"]: item for item in payload["locations"]}
        expected = (
            ("bike_station", "checking the tire pressure guide against the pump gauge"),
            ("canal_walkway", "reading a folded towpath map beside the weathered railing"),
            ("community_theater_backstage", "checking a costume label beside the preparation table"),
            ("fire_station", "checking the station clock against a readiness checklist"),
            ("flower_market", "checking stem moisture before arranging the flower bucket"),
            ("public_plaza", "reading the bronze inscription beside the fountain"),
            ("tram_platform", "reading the next tram time from the arrival display"),
            ("vehicle_repair_garage", "checking a service note against the repair bay checklist"),
        )
        for location_id, action_text in expected:
            with self.subTest(location=location_id):
                actions = locations[location_id]["action_plan"]["direct_actions"]
                self.assertIn(action_text, {item["text"] for item in actions})

    def test_q82_actions_bind_body_motion_to_visible_scene_fixtures(self):
        payload = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        locations = {item["id"]: item for item in payload["locations"]}
        expected = (
            ("public_plaza", "studying the engraved monument map beside the fountain"),
            ("clinic_waiting_room", "checking the room number while opening the consultation door"),
            ("canal_walkway", "checking a water plant against a folded canal guide"),
            ("community_theater_backstage", "carrying a folded backdrop toward the marked storage wall"),
        )
        for location_id, action_text in expected:
            with self.subTest(location=location_id):
                actions = locations[location_id]["action_plan"]["direct_actions"]
                self.assertIn(action_text, {item["text"] for item in actions})


if __name__ == "__main__":
    unittest.main()
