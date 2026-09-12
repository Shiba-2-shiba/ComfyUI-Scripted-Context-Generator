import hashlib
import json
import unittest
from pathlib import Path


from assets import test_prompt_quality_compare as compare_tests
from tools.workflow_prompt_runner import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]


class TestPromptQualityStateSurface(unittest.TestCase):
    def test_state_contract_suite_is_exposed_as_a_dedicated_module(self):
        state_suite = compare_tests.TestPromptQualityExperimentState
        self.assertTrue(issubclass(state_suite, unittest.TestCase))
        self.assertTrue(hasattr(state_suite, "test_locked_hypothesis_is_immutable"))
        self.assertTrue(hasattr(state_suite, "test_two_manual_experiment_state_sequences_are_reconstructable"))

    def test_ledger_attestation_matches_policy_analyzer_fixture_and_manual_records(self):
        ledger_path = ROOT / "docs" / "prompt_quality" / "ledger.jsonl"
        entries = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        manual = entries[:2]
        attestation = entries[-1]
        fixture_path = ROOT / "assets" / "fixtures" / "prompt_quality" / "manual_experiments.json"
        policy_path = ROOT / "vocab" / "data" / "prompt_quality_policy.json"
        analyzer_path = ROOT / "tools" / "analyze_prompt_quality.py"

        self.assertEqual(attestation["schema_version"], "prompt-quality-ledger-attestation/v1")
        self.assertEqual(attestation["fixture_hash"], hashlib.sha256(fixture_path.read_bytes()).hexdigest())
        self.assertEqual(attestation["policy_hash"], hashlib.sha256(policy_path.read_bytes()).hexdigest())
        self.assertEqual(attestation["analyzer_hash"], hashlib.sha256(analyzer_path.read_bytes()).hexdigest())
        self.assertEqual(
            attestation["experiment_records"],
            {
                entry["experiment_id"]: hashlib.sha256(canonical_json_bytes(entry)).hexdigest()
                for entry in manual
            },
        )

        fixture_by_id = {
            item["experiment_id"]: item
            for item in json.loads(fixture_path.read_text(encoding="utf-8"))["experiments"]
        }
        for entry in manual:
            case = fixture_by_id[entry["experiment_id"]]
            self.assertEqual(entry["source_tree_hash"], case["source_tree_hash"])
            self.assertEqual(entry["candidate_patch_hash"], case["candidate_patch_hash"])


if __name__ == "__main__":
    unittest.main()
