import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from tools.validate_prompt_data import build_report


class TestDataConsistency(unittest.TestCase):
    def test_validator_has_no_errors(self):
        report = build_report()
        self.assertEqual(report["ERROR"], [])

    def test_validator_reports_expansion_summary(self):
        report = build_report()
        summaries = [item for item in report["INFO"] if item.get("code") == "expansion_summary"]
        self.assertEqual(len(summaries), 1)
        summary = summaries[0]

        self.assertGreaterEqual(summary["subject_count"], 28)
        self.assertGreaterEqual(summary["variation_subject_count"], 58)
        self.assertGreaterEqual(summary["variation_location_count"], 58)
        self.assertGreaterEqual(summary["background_pack_count"], 58)
        self.assertEqual(summary["location_candidate_count"], summary["action_generatable_count"])
        self.assertGreaterEqual(summary["alias_entry_count"], 300)


if __name__ == "__main__":
    unittest.main()
