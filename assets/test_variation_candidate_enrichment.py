from __future__ import annotations

import unittest
from pathlib import Path

from core.solo_safety import is_solo_safe_text
from tools.analyze_variation_candidates import load_candidate_catalog
from tools.plan_variation_semantic_pairs import classify_action, load_json


ROOT = Path(__file__).resolve().parents[1]
ITERATION = (
    ROOT
    / "docs/variation_expansion/experiments/v150-candidate-shape-iteration-019/candidate-iteration.json"
)
EXPECTED_LOCATIONS = {
    "bike_station", "canal_walkway", "clinic_waiting_room", "community_garden",
    "community_theater_backstage", "design_studio", "ferry_terminal", "fire_station",
    "flower_market", "forest_cabin", "greenhouse_nursery", "maker_space",
    "observatory_dome", "postal_service_counter", "print_shop", "public_plaza",
    "rooftop_cafe", "tram_platform", "vehicle_repair_garage",
}
MINIMUM_COUNTS = {
    "environment": 2,
    "core": 4,
    "texture": 2,
    "props": 3,
    "fx": 2,
    "time": 2,
    "crowd": 2,
    "weather": 2,
    "lighting": 2,
}
GENERIC_ACTIONS = {
    "walking through the space while loosening her posture",
    "moving carefully while leaving space for others nearby",
    "pausing before continuing the task at hand",
    "pausing to smooth out the next part of the routine",
    "adjusting her pace to match the quieter surroundings",
    "waiting calmly while the formal mood holds",
    "standing in the easy atmosphere while looking around",
    "waiting for the signal to begin again",
    "leaning in slightly while reassessing the scene",
    "moving through the routine without rushing",
    "leaning forward while keeping the task precise",
    "leaning closer while studying an unusual detail",
    "standing aside while waiting for the next cue",
    "pausing with a small smile before the next moment",
}


class VariationCandidateEnrichmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_candidate_catalog(ITERATION)

    def test_overlay_covers_exact_candidate_location_set(self) -> None:
        self.assertEqual({item["id"] for item in self.catalog["locations"]}, EXPECTED_LOCATIONS)

    def test_every_location_has_a_dense_structured_background_pack(self) -> None:
        for location in self.catalog["locations"]:
            with self.subTest(location=location["id"]):
                pack = location["background_pack"]
                self.assertEqual(set(pack), set(MINIMUM_COUNTS) | {"aliases"})
                for field, minimum in MINIMUM_COUNTS.items():
                    self.assertGreaterEqual(len(pack[field]), minimum, field)
                self.assertIsInstance(pack["aliases"], list)
                for field, values in pack.items():
                    for value in values:
                        self.assertTrue(is_solo_safe_text(value), msg=f"{location['id']}.{field}: {value}")

    def test_every_location_has_twenty_specific_direct_actions(self) -> None:
        for location in self.catalog["locations"]:
            with self.subTest(location=location["id"]):
                plan = location["action_plan"]
                self.assertEqual(plan["family_refs"], [])
                self.assertEqual(len(plan["direct_actions"]), 20)
                texts = [item["text"] for item in plan["direct_actions"]]
                self.assertEqual(len(texts), len(set(texts)))
                self.assertTrue(GENERIC_ACTIONS.isdisjoint(texts))
                self.assertTrue(all(item["load"] in {"calm", "active"} for item in plan["direct_actions"]))
                self.assertTrue(all(is_solo_safe_text(text) for text in texts))

    def test_every_direct_action_has_one_closed_semantic_class(self) -> None:
        classifier = load_json(
            ROOT / "vocab/data/variation_action_semantic_classifier.json",
            "variation-action-semantic-classifier/v1",
        )
        for location in self.catalog["locations"]:
            for action in location["action_plan"]["direct_actions"]:
                with self.subTest(location=location["id"], action=action["text"]):
                    classified = classify_action(action["text"], action["load"], classifier)
                    self.assertTrue(classified["action_family"])


if __name__ == "__main__":
    unittest.main()
