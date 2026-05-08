import unittest

from tools.build_compatibility_review import build_check_report, build_generated_rows
from tools.check_variation_scope import load_variation_scope


class TestBuildCompatibilityReview(unittest.TestCase):
    def test_generated_rows_stay_inside_variation_scope(self):
        scope = load_variation_scope()
        scope_subjects = set(scope["variation_subjects"])
        scope_locations = set(scope["variation_locations"])

        rows = build_generated_rows(scope)

        self.assertGreater(len(rows), 0)
        self.assertTrue({row["subj"] for row in rows} <= scope_subjects)
        self.assertTrue({row["canonical_loc"] for row in rows} <= scope_locations)

    def test_check_report_has_no_pair_drift(self):
        report = build_check_report()

        self.assertEqual(report["ERROR"], [])
        self.assertEqual(report["WARNING"], [])

        summary = [item for item in report["INFO"] if item["code"] == "compatibility_review_generation_summary"][0]
        self.assertEqual(summary["current_row_count"], 1637)
        self.assertEqual(summary["generated_row_count"], summary["current_row_count"])
        self.assertEqual(summary["missing_current_pairs"], 0)
        self.assertEqual(summary["extra_generated_pairs"], 0)

    def test_check_report_has_no_metadata_drift_after_generation(self):
        report = build_check_report()

        warning_codes = {item["code"] for item in report["WARNING"]}
        self.assertNotIn("compatibility_review_metadata_drift", warning_codes)


if __name__ == "__main__":
    unittest.main()
