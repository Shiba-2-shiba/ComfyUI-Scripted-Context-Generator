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
        self.assertTrue(payload["semantic_scoring_enabled"])
        self.assertFalse(payload["selection_changed_by_semantic"])
        self.assertEqual(payload["baseline_selected_attempt_index"], 0)
        self.assertEqual(payload["semantic_selected_attempt_index"], 0)
        self.assertEqual(payload["candidate_scores"][0]["repeat_penalty"], 2)

    def test_clothing_candidate_renderer_filters_state_details_by_location(self):
        from pipeline.clothing_candidate_renderer import location_allows_state_detail, render_clothing_candidate

        self.assertFalse(location_allows_state_detail("modern_office", "covered in snow"))
        self.assertTrue(location_allows_state_detail("winter_street", "covered in snow"))

        indoor_prompt, _indoor_decision = render_clothing_candidate(
            "winter_date",
            12,
            "dresses",
            0.0,
            "navy, white",
            recent_packs=set(),
            recent_types=set(),
            recent_outerwear=set(),
            recent_signatures=set(),
            loc="modern_office",
        )
        self.assertNotIn("covered in snow", indoor_prompt)

    def test_clothing_candidate_selector_reports_repeat_and_tpo_scores(self):
        from pipeline.clothing_candidate_selector import select_clothing_candidate
        from pipeline.clothing_semantics import build_clothing_target_vector

        target = build_clothing_target_vector("rainy_bus_stop", action_text="commuting", theme_key="rainy_day")
        prompt, decision, candidate_scores, baseline_index = select_clothing_candidate(
            "rainy_day",
            31,
            "random",
            1.0,
            "navy, white",
            loc="rainy_bus_stop",
            recent_packs=set(),
            recent_types=set(),
            recent_outerwear=set(),
            recent_signatures=set(),
            clothing_tpo_enabled=True,
            clothing_tpo_active=True,
            clothing_target_vector=target,
        )

        self.assertTrue(prompt)
        self.assertEqual(decision["attempt_index"], decision.get("attempt_index", 0))
        self.assertTrue(candidate_scores)
        self.assertIn("semantic_tpo_final_penalty", decision)
        self.assertIsInstance(baseline_index, int)
        for item in candidate_scores:
            self.assertGreaterEqual(item["final_penalty"], item["repeat_penalty"])


if __name__ == "__main__":
    unittest.main()
