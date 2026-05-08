import unittest


from tools.report_expansion_delta import build_expansion_delta


class TestExpansionDelta(unittest.TestCase):
    def test_delta_report_passes_when_variation_counts_increase(self):
        before = {
            "base": {
                "unique_subjects": 58,
                "unique_locations": 58,
                "total_base_variations": 11916,
                "missing_pools_count": 0,
            },
            "garnish": {
                "mood_keys": 9,
                "mood_tags_unique": 172,
                "micro_actions_unique": 280,
                "background_context_tags_unique": 771,
                "semantic_units_unique": 1223,
            },
            "combined": {
                "garnish_universe_size": 11007,
                "theoretical_upper_bound": 131159412,
            },
        }
        after = {
            "base": {
                "unique_subjects": 60,
                "unique_locations": 59,
                "total_base_variations": 12400,
                "missing_pools_count": 0,
            },
            "garnish": {
                "mood_keys": 9,
                "mood_tags_unique": 175,
                "micro_actions_unique": 284,
                "background_context_tags_unique": 790,
                "semantic_units_unique": 1249,
            },
            "combined": {
                "garnish_universe_size": 11241,
                "theoretical_upper_bound": 139388400,
            },
        }

        delta = build_expansion_delta(before, after)

        self.assertTrue(delta["summary"]["passed"])
        self.assertEqual(delta["summary"]["regression_count"], 0)

    def test_delta_report_flags_missing_pool_regression(self):
        before = {"base": {"missing_pools_count": 0}}
        after = {"base": {"missing_pools_count": 1}}

        delta = build_expansion_delta(before, after)

        self.assertFalse(delta["summary"]["passed"])
        self.assertEqual(delta["regressions"][0]["metric"], "missing_pools_count")


if __name__ == "__main__":
    unittest.main()
