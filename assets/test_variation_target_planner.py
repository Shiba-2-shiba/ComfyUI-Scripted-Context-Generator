import unittest

from tools.plan_variation_target import (
    action_backed_compatible_locations,
    build_target_report,
    location_candidate_deltas,
    scenario_metrics,
    subject_candidate_deltas,
)
from tools.check_variation_scope import load_variation_scope


class TestVariationTargetPlanner(unittest.TestCase):
    def test_current_scope_matches_base_variation_baseline(self):
        scope = load_variation_scope()
        metrics = scenario_metrics(scope["variation_subjects"], scope["variation_locations"], scope=scope)

        self.assertEqual(metrics["unique_subjects"], 120)
        self.assertEqual(metrics["unique_locations"], 91)
        self.assertEqual(metrics["row_count"], 5926)
        self.assertEqual(metrics["total_base_variations"], 105612)
        self.assertEqual(metrics["missing_pools_count"], 0)

    def test_planning_scenarios_match_current_p11_surface(self):
        report = build_target_report(target=100000)
        scenarios = {row["name"]: row for row in report["scenarios"]}

        self.assertEqual(scenarios["all_known_subjects_current_locations"]["total_base_variations"], 105612)
        self.assertEqual(
            scenarios["current_subjects_all_action_backed_compatible_locations"]["total_base_variations"],
            105612,
        )
        self.assertEqual(
            scenarios["all_known_subjects_all_action_backed_compatible_locations"]["total_base_variations"],
            105612,
        )

        action_scenarios = {row["minimum_actions"]: row for row in report["minimum_action_scenarios"]}
        self.assertEqual(action_scenarios[12]["total_base_variations"], 105612)
        self.assertEqual(action_scenarios[16]["total_base_variations"], 107660)
        self.assertEqual(action_scenarios[20]["total_base_variations"], 118520)
        self.assertEqual(report["first_minimum_action_target_met"]["minimum_actions"], 12)

    def test_candidate_deltas_are_empty_after_p11_action_refactor(self):
        self.assertEqual(subject_candidate_deltas(limit=5), [])
        self.assertEqual(location_candidate_deltas(), [])

    def test_action_backed_location_pool_matches_current_scope(self):
        locations = action_backed_compatible_locations()

        self.assertEqual(len(locations), 91)
        self.assertIn("local_market_street", locations)
        self.assertIn("train_station_platform", locations)


if __name__ == "__main__":
    unittest.main()
