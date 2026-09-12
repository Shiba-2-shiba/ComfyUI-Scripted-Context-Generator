from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.compare_variation_prompt_pair import build_semantic_pair_comparison
from tools.plan_variation_semantic_pairs import value_hash
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


class VariationSemanticComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

        def write(name, value):
            path = self.root / name
            path.write_bytes(canonical_json_bytes(value))
            return path

        self.automatic = write(
            "automatic.json",
            {
                "schema_version": "variation-nonselected-quality-comparison/v2",
                "experiment_id": "semantic-exp",
                "quality_verdict": "pass",
                "validation_verdict": "pass",
                "review_ready": True,
                "promotion_ready": False,
            },
        )
        pairs = [
            {
                "pair_id": f"vsp-{index:02d}",
                "cohort": "control" if index <= 16 else "exploration",
                "run_seed": index,
            }
            for index in range(1, 21)
        ]
        contract = {
            "schema_version": "variation-semantic-pair-contract/v1",
            "experiment_id": "semantic-exp",
            "automatic_comparison": {
                "path": str(self.automatic),
                "sha256": hashlib.sha256(self.automatic.read_bytes()).hexdigest(),
            },
            "candidate_snapshot": {
                "candidate_source_tree_sha256": "a" * 64,
                "candidate_snapshot_content_sha256": "b" * 64,
            },
            "selection_salt_sha256": "c" * 64,
            "compatibility_graph_sha256": "d" * 64,
            "pair_count": 20,
            "pairs": pairs,
        }
        contract["contract_sha256"] = value_hash(contract)
        self.contract = write("contract.json", contract)

        self.baseline_records = self.root / "baseline.jsonl"
        self.candidate_records = self.root / "candidate.jsonl"
        self.baseline_records.write_text("\n".join(json.dumps({**pair, "cleaned_prompt": "before"}) for pair in pairs) + "\n", encoding="utf-8")
        self.candidate_records.write_text("\n".join(json.dumps({**pair, "cleaned_prompt": "after"}) for pair in pairs) + "\n", encoding="utf-8")

        generation = {
            "schema_version": "variation-semantic-pair-generation-receipt/v1",
            "experiment_id": "semantic-exp",
            "contract_sha256": contract["contract_sha256"],
            "baseline_records_sha256": hashlib.sha256(self.baseline_records.read_bytes()).hexdigest(),
            "candidate_records_sha256": hashlib.sha256(self.candidate_records.read_bytes()).hexdigest(),
            "status": "generated",
        }
        generation["generation_receipt_sha256"] = value_hash(generation)
        self.generation = write("generation.json", generation)

        validation = {
            "schema_version": "variation-semantic-pair-validation/v1",
            "experiment_id": "semantic-exp",
            "contract_sha256": contract["contract_sha256"],
            "generation_receipt_sha256": generation["generation_receipt_sha256"],
            "validated_pair_count": 20,
            "identity_mismatch_count": 0,
            "seed_mismatch_count": 0,
            "record_hash_mismatch_count": 0,
            "mismatches": [],
            "status": "pass",
        }
        validation["validation_sha256"] = value_hash(validation)
        self.validation = write("validation.json", validation)
        self.review_policy = {
            "schema_version": "prompt-quality-review-contract/v4",
            "hard_defect_codes": ["runtime_error"],
            "target_dimension_contract": {
                "max_candidate_worse_rate": 0.1,
                "min_improvement_support": 0.65,
                "require_lane_direction_agreement": True,
            },
            "guard_dimension_contract": {
                "max_candidate_worse_rate": 0.1,
                "minimum_valid_votes": 0,
                "require_lane_direction_agreement": False,
            },
        }

    def tearDown(self):
        self.temp.cleanup()

    def build(self):
        return build_semantic_pair_comparison(
            automatic_comparison_path=self.automatic,
            contract_path=self.contract,
            generation_receipt_path=self.generation,
            validation_path=self.validation,
            baseline_records_path=self.baseline_records,
            candidate_records_path=self.candidate_records,
            review_policy=self.review_policy,
        )

    def test_builds_closed_v2_adapter(self):
        comparison = self.build()
        self.assertEqual(comparison["schema_version"], "prompt-quality-comparison/v2")
        self.assertEqual(len(comparison["review_selection"]["pairs"]), 20)
        self.assertEqual(comparison["review_selection"]["dimensions"]["consistency"]["minimum_valid_votes"], 36)
        self.assertFalse(comparison["uses_output_metrics_for_selection"])

    def test_builds_v5_comparison_with_separate_vote_thresholds(self):
        self.review_policy["schema_version"] = "prompt-quality-review-contract/v5"
        comparison = self.build()
        self.assertEqual(comparison["schema_version"], "prompt-quality-comparison/v3")
        eligibility = comparison["review_selection"]["dimensions"]["consistency"]
        self.assertEqual(
            set(eligibility),
            {"authority", "minimum_non_abstain_votes", "minimum_directional_votes", "pair_ids"},
        )
        self.assertEqual(eligibility["minimum_non_abstain_votes"], 36)
        self.assertEqual(eligibility["minimum_directional_votes"], 20)

    def test_builds_v6_comparison_with_guard_coverage(self):
        self.review_policy["schema_version"] = "prompt-quality-review-contract/v6"
        comparison = self.build()
        self.assertEqual(comparison["schema_version"], "prompt-quality-comparison/v4")
        protagonist = comparison["review_selection"]["dimensions"]["protagonist_clarity"]
        redundancy = comparison["review_selection"]["dimensions"]["redundancy"]
        diversity = comparison["review_selection"]["dimensions"]["diversity"]
        self.assertEqual((protagonist["minimum_non_abstain_votes"], protagonist["minimum_directional_votes"]), (36, 0))
        self.assertEqual((redundancy["minimum_non_abstain_votes"], redundancy["minimum_directional_votes"]), (36, 0))
        self.assertEqual((diversity["minimum_non_abstain_votes"], diversity["minimum_directional_votes"], diversity["pair_ids"]), (0, 0, []))

    def test_rejects_generation_record_drift(self):
        self.candidate_records.write_text("{}\n", encoding="utf-8")
        with self.assertRaises(WorkflowValidationError) as caught:
            self.build()
        self.assertEqual(caught.exception.code, "semantic_pair_record_hash_mismatch")

    def test_v7_comparison_changes_only_consistency_to_guard(self):
        root = Path(__file__).resolve().parents[1]
        self.review_policy = json.loads((root / "vocab/data/variation_semantic_review_policy_v4.json").read_text(encoding="utf-8"))["review"]
        comparison = self.build()
        self.assertEqual(comparison["schema_version"], "prompt-quality-comparison/v5")
        dimensions = comparison["review_selection"]["dimensions"]
        for name in ("consistency", "protagonist_clarity", "redundancy"):
            self.assertEqual((dimensions[name]["minimum_non_abstain_votes"], dimensions[name]["minimum_directional_votes"]), (36, 0))
        for name in ("naturalness", "image_prompt_suitability"):
            self.assertEqual((dimensions[name]["minimum_non_abstain_votes"], dimensions[name]["minimum_directional_votes"]), (36, 20))
        self.review_policy["target_dimension_contract"]["min_improvement_support"] = 0
        with self.assertRaises(ValueError):
            self.build()

    def test_rejects_unknown_schema(self):
        value = json.loads(self.validation.read_text(encoding="utf-8"))
        value["schema_version"] = "variation-semantic-pair-validation/v999"
        self.validation.write_bytes(canonical_json_bytes(value))
        with self.assertRaises(WorkflowValidationError) as caught:
            self.build()
        self.assertEqual(caught.exception.code, "semantic_pair_validation_schema_mismatch")


if __name__ == "__main__":
    unittest.main()
