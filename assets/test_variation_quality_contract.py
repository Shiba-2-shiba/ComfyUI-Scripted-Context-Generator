import copy
import json
import unittest
from pathlib import Path

from assets.variation_test_fixtures import fixture_environment, fixture_repository
from tools.variation_quality_contract import validate_variation_quality_contract
from tools.workflow_prompt_runner import WorkflowValidationError


ROOT = fixture_repository()
CONTRACT_PATH = ROOT / "docs/variation_expansion/experiments/v150-candidate-shape-iteration-008/nonselected-quality-contract.json"


class TestVariationQualityContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_fixture_contract_reproduces_parent_evidence_and_fixed_cohort(self):
        result = validate_variation_quality_contract(
            self.contract,
            repository_root=ROOT,
        )

        self.assertEqual(result["status"], "pass")
        self.assertEqual(len(self.contract["cohort"]["control_seeds"]), 64)
        self.assertEqual(len(self.contract["cohort"]["exploration_seeds"]), 16)
        self.assertTrue(self.contract["authority"]["quality_evidence"])
        self.assertFalse(self.contract["authority"]["promotion_ready"])

    def test_contract_authority_tamper_fails_closed(self):
        tampered = copy.deepcopy(self.contract)
        tampered["authority"]["promotion_ready"] = True
        tampered.pop("contract_sha256")
        from tools.variation_quality_contract import _hash_value

        tampered["contract_sha256"] = _hash_value(tampered)

        with self.assertRaises(WorkflowValidationError) as raised:
            validate_variation_quality_contract(tampered, repository_root=ROOT)

        self.assertEqual(raised.exception.code, "variation_quality_contract_widens_authority")

    def test_parent_receipt_hash_tamper_is_rejected(self):
        tampered = copy.deepcopy(self.contract)
        tampered["coverage_receipt_sha256"] = "0" * 64
        tampered.pop("contract_sha256")
        from tools.variation_quality_contract import _hash_value

        tampered["contract_sha256"] = _hash_value(tampered)

        with self.assertRaises(WorkflowValidationError) as raised:
            validate_variation_quality_contract(tampered, repository_root=ROOT)

        self.assertEqual(raised.exception.code, "variation_quality_parent_evidence_mismatch")

    def test_contract_unknown_and_missing_fields_fail_closed(self):
        from tools.variation_quality_contract import _hash_value

        cases = []
        unknown = copy.deepcopy(self.contract)
        unknown["unexpected_authority"] = True
        unknown.pop("contract_sha256")
        unknown["contract_sha256"] = _hash_value(unknown)
        cases.append(unknown)
        missing = copy.deepcopy(self.contract)
        missing.pop("surface")
        missing.pop("contract_sha256")
        missing["contract_sha256"] = _hash_value(missing)
        cases.append(missing)

        for contract in cases:
            with self.subTest(fields=sorted(contract)):
                with self.assertRaises(WorkflowValidationError) as raised:
                    validate_variation_quality_contract(contract, repository_root=ROOT)
                self.assertEqual(
                    raised.exception.code,
                    "invalid_variation_quality_contract_fields",
                )

    def test_absolute_contract_path_is_rejected(self):
        from tools.variation_quality_contract import _hash_value

        tampered = copy.deepcopy(self.contract)
        tampered["current_source_refresh_path"] = str(
            (ROOT / "absolute-refresh.json").resolve()
        )
        tampered.pop("contract_sha256")
        tampered["contract_sha256"] = _hash_value(tampered)

        with self.assertRaises(WorkflowValidationError) as raised:
            validate_variation_quality_contract(tampered, repository_root=ROOT)

        self.assertEqual(
            raised.exception.code,
            "invalid_variation_quality_contract_path",
        )


def setUpModule():
    global _fixture_context
    _fixture_context = fixture_environment(ROOT)
    _fixture_context.__enter__()


def tearDownModule():
    _fixture_context.__exit__(None, None, None)


if __name__ == "__main__":
    unittest.main()
