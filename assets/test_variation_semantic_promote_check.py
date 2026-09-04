from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.aggregate_blind_prompt_review import ALL_DIMENSIONS, aggregate_review
from tools.build_blind_prompt_review import build_review
from tools.compare_prompt_quality import REQUIRED_VERIFICATION_GATES, promote_check
from tools.workflow_prompt_runner import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]


class VariationSemanticPromoteCheckTests(unittest.TestCase):
    def _assert_promotion_recursively_binds_review_and_verification(self, version):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            baseline, candidate = root / "baseline.jsonl", root / "candidate.jsonl"
            pairs = [{"pair_id": f"pair-{index:02d}", "cohort": "control" if index <= 16 else "exploration", "run_seed": index * 101} for index in range(1, 21)]
            baseline.write_text("\n".join(json.dumps({**pair, "cleaned_prompt": f"baseline {pair['pair_id']}"}) for pair in pairs) + "\n", encoding="utf-8")
            candidate.write_text("\n".join(json.dumps({**pair, "cleaned_prompt": f"candidate {pair['pair_id']}"}) for pair in pairs) + "\n", encoding="utf-8")
            policy = {
                "schema_version": f"prompt-quality-review-contract/v{version}", "hard_defect_codes": ["runtime_error"],
                "target_dimension_contract": {"max_candidate_worse_rate": 0.1, "min_improvement_support": 0.65, "require_lane_direction_agreement": True},
                "guard_dimension_contract": {"max_candidate_worse_rate": 0.1, "minimum_valid_votes": 0, "require_lane_direction_agreement": False},
            }
            targets = ["consistency", "naturalness", "image_prompt_suitability"] if version == 6 else ["consistency", "naturalness", "protagonist_clarity", "image_prompt_suitability"]
            guards = ["protagonist_clarity", "redundancy", "diversity"] if version == 6 else ["redundancy", "diversity"]
            dimensions = {}
            for dimension in ALL_DIMENSIONS:
                eligibility = {"authority": "current_source_corpus_confirmation" if dimension == "diversity" else "semantic_pairwise", "pair_ids": [] if dimension == "diversity" else [pair["pair_id"] for pair in pairs]}
                if version >= 5:
                    eligibility.update({"minimum_non_abstain_votes": 36 if (dimension in targets or (version == 6 and dimension in guards and dimension != "diversity")) else 0, "minimum_directional_votes": 20 if dimension in targets else 0})
                else:
                    eligibility["minimum_valid_votes"] = 36 if dimension in targets else 0
                dimensions[dimension] = eligibility
            selection = {"pairs": pairs, "dimensions": dimensions}
            selection["selection_hash"] = hashlib.sha256(canonical_json_bytes(selection)).hexdigest()
            automatic = root / "automatic.json"
            automatic.write_bytes(canonical_json_bytes({"status": "pass"}))
            source_hash, content_hash = "a" * 64, "b" * 64
            comparison_value = {
                "schema_version": f"prompt-quality-comparison/v{4 if version == 6 else 3 if version == 5 else 2}", "experiment_id": "semantic-promote",
                "review_contract_hash": hashlib.sha256(canonical_json_bytes(policy)).hexdigest(),
                "qualitative_scope_hash": hashlib.sha256(canonical_json_bytes({"guard_qualitative_dimensions": guards, "target_qualitative_dimensions": targets})).hexdigest(),
                "automatic_comparison_path": automatic.relative_to(ROOT).as_posix(), "automatic_comparison_hash": hashlib.sha256(automatic.read_bytes()).hexdigest(),
                "automatic_comparison_verdict": "pass", "candidate_source_tree_sha256": source_hash,
                "candidate_snapshot_content_sha256": content_hash, "uses_output_metrics_for_selection": False,
                "semantic_pair_contract_sha256": "c" * 64, "pair_generation_receipt_sha256": "d" * 64,
                "pair_validation_sha256": "e" * 64, "selection_salt_sha256": "f" * 64,
                "compatibility_graph_sha256": "1" * 64, "baseline_records_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
                "candidate_records_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(), "review_selection": selection,
            }
            comparison = root / "comparison.json"
            comparison.write_bytes(canonical_json_bytes(comparison_value))
            review_dir = root / "review"
            build_review(baseline, candidate, review_dir, "semantic-promote", [], target_dimensions=targets, guard_dimensions=guards, review_policy=policy, comparison=comparison)
            key = json.loads((review_dir / "assignment-key.json").read_text(encoding="utf-8"))
            for lane_number, lane_key in enumerate(key["lanes"], 1):
                lane_path = review_dir / f"lane-{lane_number}.json"
                lane = json.loads(lane_path.read_text(encoding="utf-8"))
                assignments = {item["pair_id"]: item for item in lane_key["assignments"]}
                votes = [{"pair_id": pair["pair_id"], "dimensions": {dimension: f"{assignments[pair['pair_id']]['candidate_side']}_better" for dimension in ALL_DIMENSIONS}, "hard_defects": {"A": [], "B": []}} for pair in lane["pairs"]]
                lane_result = {"schema_version": f"prompt-quality-blind-review-result/v{version}", "lane_id": lane["lane_id"], "reviewer_id": f"reviewer-{lane_number}", "review_session_id": f"session-{lane_number}", "reviewer_type": "independent", "reviewer_model_version": "test", "blinded": True, "rubric_version": lane["rubric_version"], "rubric_hash": lane["review_prompt_hash"], "review_prompt_hash": lane["review_prompt_hash"], "input_hash": hashlib.sha256(lane_path.read_bytes()).hexdigest(), "votes": votes}
                (review_dir / f"lane-{lane_number}-result.json").write_bytes(canonical_json_bytes(lane_result))
            review_value = aggregate_review(review_dir, None, experiment={"target_qualitative_dimensions": targets, "guard_qualitative_dimensions": guards})
            review_value.update({"candidate_source_tree_sha256": source_hash, "candidate_snapshot_content_sha256": content_hash})
            review = review_dir / "review.json"
            review.write_bytes(canonical_json_bytes(review_value))
            gates = {}
            for gate_name in REQUIRED_VERIFICATION_GATES:
                evidence = root / f"{gate_name}-evidence.json"
                evidence.write_bytes(canonical_json_bytes({"status": "pass"}))
                result = comparison if gate_name == "target_comparison" else review if gate_name == "blind_review" else root / f"{gate_name}-result.json"
                if not result.exists():
                    result.write_bytes(canonical_json_bytes({"status": "pass"}))
                gates[gate_name] = {"evidence_path": str(evidence.resolve()), "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(), "result_path": str(result.resolve()), "result_sha256": hashlib.sha256(result.read_bytes()).hexdigest(), "status": "pass"}
            verification = root / "verification.json"
            verification.write_bytes(canonical_json_bytes({"schema_version": "variation-v150-verification-receipt/v1", "status": "pass", "experiment_id": "semantic-promote", "candidate_root": str(root.resolve()), "candidate_root_identity_sha256": "2" * 64, "candidate_source_tree_sha256": source_hash, "candidate_snapshot_content_sha256": content_hash, "comparison_artifact_sha256": hashlib.sha256(comparison.read_bytes()).hexdigest(), "review_artifact_sha256": hashlib.sha256(review.read_bytes()).hexdigest(), "quality_gates": gates}))
            promoted = promote_check(comparison, review=review, verification=verification)
            self.assertEqual(promoted["verdict"], "promote", promoted["failures"])
            verification_value = json.loads(verification.read_text(encoding="utf-8"))
            verification_value["candidate_snapshot_content_sha256"] = "9" * 64
            verification.write_bytes(canonical_json_bytes(verification_value))
            rejected = promote_check(comparison, review=review, verification=verification)
            self.assertEqual(rejected["verdict"], "reject")
            self.assertIn("verification_artifacts_invalid", rejected["failures"])

    def test_v4_promotion_recursively_binds_review_and_verification(self):
        self._assert_promotion_recursively_binds_review_and_verification(4)

    def test_v5_promotion_recursively_binds_review_and_verification(self):
        self._assert_promotion_recursively_binds_review_and_verification(5)

    def test_v6_promotion_recursively_binds_review_and_verification(self):
        self._assert_promotion_recursively_binds_review_and_verification(6)

    def test_unknown_comparison_schema_has_no_legacy_fallback(self):
        rejected = promote_check({"schema_version": "prompt-quality-comparison/v999", "automatic_verdict": "pass"})
        self.assertEqual(rejected["failures"], ["invalid_comparison_schema"])


if __name__ == "__main__":
    unittest.main()
