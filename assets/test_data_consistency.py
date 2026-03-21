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


if __name__ == "__main__":
    unittest.main()
