import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestSemanticEpigAudit(unittest.TestCase):
    def test_fixture_loads(self):
        from tools.audit_semantic_epig_outputs import load_cases

        cases = load_cases(Path(ROOT) / "assets" / "fixtures" / "semantic_epig_audit_cases.json")

        self.assertGreaterEqual(len(cases), 5)
        self.assertTrue(all(case.get("case_id") for case in cases))

    def test_audit_is_deterministic_for_same_seed(self):
        from tools.audit_semantic_epig_outputs import audit_case, load_cases

        case = load_cases(Path(ROOT) / "assets" / "fixtures" / "semantic_epig_audit_cases.json")[0]
        first = audit_case(case, 2)
        second = audit_case(case, 2)

        self.assertEqual(first["passive_prompt"], second["passive_prompt"])
        self.assertEqual(first["active_prompt"], second["active_prompt"])
        self.assertEqual(first["changed_domains"], second["changed_domains"])
        self.assertIn("active", first["semantic_debug"])
        self.assertIn("policy_issues", first)

    def test_audit_writes_json_output(self):
        from tools.audit_semantic_epig_outputs import audit_cases, load_cases, write_audit

        cases = load_cases(Path(ROOT) / "assets" / "fixtures" / "semantic_epig_audit_cases.json")[:1]
        result = audit_cases(cases, seed_start=0, seed_count=1)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = write_audit(result, Path(tmpdir) / "semantic_epig_audit.json")
            self.assertTrue(output_path.exists())

        self.assertEqual(result["record_count"], 1)
        self.assertIn("records", result)


if __name__ == "__main__":
    unittest.main()
