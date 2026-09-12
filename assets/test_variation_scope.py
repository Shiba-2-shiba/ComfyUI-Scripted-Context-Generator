import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.check_variation_scope import build_scope_report, load_variation_scope


class TestVariationScope(unittest.TestCase):
    def test_variation_scope_matches_current_review_surface(self):
        report = build_scope_report()
        self.assertEqual(report["ERROR"], [])

        summary = [item for item in report["INFO"] if item.get("code") == "variation_scope_summary"][0]
        expected = load_variation_scope()["expected_metrics"]
        self.assertEqual(summary["scope_subject_count"], expected["unique_subjects"])
        self.assertEqual(summary["scope_location_count"], expected["unique_locations"])
        self.assertEqual(summary["compatibility_review_row_count"], expected["row_count"])
        self.assertEqual(summary["total_base_variations"], expected["total_base_variations"])

    def test_next_candidate_locations_are_not_already_in_scope(self):
        scope = load_variation_scope()
        current = set(scope["variation_locations"])
        candidates = set(scope["next_candidate_locations"])
        self.assertFalse(current & candidates)


if __name__ == "__main__":
    unittest.main()
