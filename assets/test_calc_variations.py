import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from assets.calc_variations import calc_base_metrics, calc_garnish_metrics  # noqa: E402


class TestCalcVariations(unittest.TestCase):
    def test_base_metrics_still_report_current_action_pool_coverage(self):
        metrics = calc_base_metrics(ROOT)

        self.assertEqual(metrics["unique_subjects"], 58)
        self.assertEqual(metrics["unique_locations"], 68)
        self.assertEqual(metrics["total_base_variations"], 15034)
        self.assertEqual(metrics["row_count"], 1565)
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
