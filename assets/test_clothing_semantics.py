import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestClothingSemantics(unittest.TestCase):
    def test_rainy_bus_stop_target_has_high_weather_fit(self):
        from pipeline.clothing_semantics import build_clothing_target_vector

        target = build_clothing_target_vector("rainy_bus_stop", action_text="commuting", theme_key="rainy_day")

        self.assertGreaterEqual(target["weather_fit"], 0.8)
        self.assertGreaterEqual(target["movement_freedom"], 0.64)

    def test_office_target_prefers_formality_and_low_prominence(self):
        from pipeline.clothing_semantics import build_clothing_target_vector

        target = build_clothing_target_vector("modern_office", action_text="reviewing documents", theme_key="office_lady")

        self.assertGreaterEqual(target["formality"], 0.68)
        self.assertLessEqual(target["visual_prominence"], 0.35)

    def test_score_clothing_decision_prefers_matching_pack(self):
        from pipeline.clothing_semantics import build_clothing_target_vector, score_clothing_decision

        target = build_clothing_target_vector("rainy_bus_stop", action_text="commuting", theme_key="rainy_day")
        rainy = score_clothing_decision(
            {"theme": "rainy_day", "base_pack": "rainy_day_layers", "outerwear_pack": "rainproof_trench"},
            "rainy outfit",
            target,
        )
        office = score_clothing_decision(
            {"theme": "office_lady", "base_pack": "modern_office_attire", "outerwear_pack": ""},
            "office outfit",
            target,
        )

        self.assertGreater(rainy["score"], office["score"])
        self.assertLessEqual(rainy["semantic_penalty"], office["semantic_penalty"])

    def test_debug_payload_records_active_selection_and_candidates(self):
        from pipeline.clothing_semantics import build_clothing_target_vector, clothing_semantic_debug_payload

        target = build_clothing_target_vector("modern_office", action_text="working", theme_key="office_lady")
        payload = clothing_semantic_debug_payload(
            target_vector=target,
            candidate_scores=[
                {"attempt_index": 0, "score": 0.8, "distance": 0.1, "semantic_penalty": 0, "repeat_penalty": 2, "final_penalty": 2}
            ],
            selected_attempt_index=0,
            selected_by_semantic=True,
        )

        self.assertEqual(payload["mode"], "active")
        self.assertTrue(payload["selected_by_semantic"])
        self.assertEqual(payload["candidate_scores"][0]["repeat_penalty"], 2)


if __name__ == "__main__":
    unittest.main()
