import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from assets.calc_variations import calc_base_metrics, calc_garnish_metrics  # noqa: E402
from tools.check_variation_scope import load_variation_scope


class TestCalcVariations(unittest.TestCase):
    def test_base_metrics_still_report_current_action_pool_coverage(self):
        metrics = calc_base_metrics(ROOT)

        expected = load_variation_scope()["expected_metrics"]
        for key in ("unique_subjects", "unique_locations", "total_base_variations", "row_count"):
            self.assertEqual(metrics[key], expected[key], key)
        self.assertEqual(metrics["missing_pools_count"], 0)

    def test_garnish_metrics_are_semantic_only(self):
        metrics = calc_garnish_metrics(ROOT)

        self.assertNotIn("camera_configs", metrics)
        self.assertNotIn("effects_unique", metrics)
        self.assertGreater(metrics["semantic_units_unique"], metrics["micro_actions_unique"])
        self.assertGreater(metrics["background_context_tags_unique"], 0)
        self.assertGreater(metrics["legacy_disabled"]["camera_configs"], 0)
        self.assertGreater(metrics["legacy_disabled"]["effect_tags_unique"], 0)


if __name__ == "__main__":
    unittest.main()
