from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.aggregate_blind_prompt_review import ALL_DIMENSIONS, aggregate_review
from tools.build_blind_prompt_review import build_review
from tools.workflow_prompt_runner import canonical_json_bytes


class VariationSemanticReviewTests(unittest.TestCase):
    def _fixture(self, root: Path, version: int = 4):
        baseline = root / "baseline.jsonl"
        candidate = root / "candidate.jsonl"
        pairs = [{"pair_id": f"pair-{index:02d}", "cohort": "semantic", "run_seed": index} for index in range(1, 21)]
        baseline.write_text("\n".join(json.dumps({**pair, "cleaned_prompt": f"baseline {pair['pair_id']}"}) for pair in pairs) + "\n", encoding="utf-8")
        candidate.write_text("\n".join(json.dumps({**pair, "cleaned_prompt": f"candidate {pair['pair_id']}"}) for pair in pairs) + "\n", encoding="utf-8")
        policy = {
            "schema_version": f"prompt-quality-review-contract/v{version}",
            "hard_defect_codes": ["runtime_error"],
            "target_dimension_contract": {"max_candidate_worse_rate": 0.1, "min_improvement_support": 0.65, "require_lane_direction_agreement": True},
            "guard_dimension_contract": {"max_candidate_worse_rate": 0.1, "minimum_valid_votes": 0, "require_lane_direction_agreement": False},
        }
        targets = ["consistency", "naturalness", "image_prompt_suitability"] if version == 6 else ["consistency", "naturalness", "protagonist_clarity", "image_prompt_suitability"]
        guards = ["protagonist_clarity", "redundancy", "diversity"] if version == 6 else ["redundancy", "diversity"]
        scope_hash = hashlib.sha256(canonical_json_bytes({"guard_qualitative_dimensions": guards, "target_qualitative_dimensions": targets})).hexdigest()
        dimensions = {}
        for dimension in ALL_DIMENSIONS:
            eligibility = {
                "authority": "current_source_corpus_confirmation" if dimension == "diversity" else "semantic_pairwise",
                "pair_ids": [] if dimension == "diversity" else [pair["pair_id"] for pair in pairs],
            }
            if version >= 5:
                eligibility.update({
                    "minimum_non_abstain_votes": 36 if (dimension in targets or (version == 6 and dimension in guards and dimension != "diversity")) else 0,
                    "minimum_directional_votes": 20 if dimension in targets else 0,
                })
            else:
                eligibility["minimum_valid_votes"] = 36 if dimension in targets else 0
            dimensions[dimension] = eligibility
        selection = {"pairs": pairs, "dimensions": dimensions}
        selection["selection_hash"] = hashlib.sha256(canonical_json_bytes(selection)).hexdigest()
        comparison = {
            "schema_version": f"prompt-quality-comparison/v{4 if version == 6 else 3 if version == 5 else 2}", "experiment_id": "semantic-test",
            "review_contract_hash": hashlib.sha256(canonical_json_bytes(policy)).hexdigest(),
            "qualitative_scope_hash": scope_hash, "automatic_comparison_path": "automatic.json",
            "automatic_comparison_hash": "a" * 64, "automatic_comparison_verdict": "pass",
            "candidate_source_tree_sha256": "b" * 64, "candidate_snapshot_content_sha256": "2" * 64,
            "uses_output_metrics_for_selection": False,
            "semantic_pair_contract_sha256": "c" * 64, "pair_generation_receipt_sha256": "d" * 64,
            "pair_validation_sha256": "e" * 64, "selection_salt_sha256": "f" * 64,
            "compatibility_graph_sha256": "1" * 64,
            "baseline_records_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
            "candidate_records_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
            "review_selection": selection,
        }
        comparison_path = root / "comparison.json"
        comparison_path.write_bytes(canonical_json_bytes(comparison))
        return baseline, candidate, comparison_path, policy, targets, guards

    def _write_v5_results(self, review_dir: Path, outcomes):
        key = json.loads((review_dir / "assignment-key.json").read_text(encoding="utf-8"))
        index = 0
        for lane_number, lane_key in enumerate(key["lanes"], 1):
            lane_path = review_dir / f"lane-{lane_number}.json"
            lane = json.loads(lane_path.read_text(encoding="utf-8"))
            assignments = {item["pair_id"]: item for item in lane_key["assignments"]}
            votes = []
            for pair in lane["pairs"]:
                assignment = assignments[pair["pair_id"]]
                outcome = outcomes[index]
                index += 1
                if outcome == "candidate_better":
                    raw = f"{assignment['candidate_side']}_better"
                elif outcome == "candidate_worse":
                    raw = f"{assignment['incumbent_side']}_better"
                else:
                    raw = outcome
                votes.append({
                    "pair_id": pair["pair_id"],
                    "dimensions": {dimension: raw for dimension in ALL_DIMENSIONS},
                    "hard_defects": {"A": [], "B": []},
                })
            result = {
                "schema_version": lane["result_contract"]["schema_version"],
                "lane_id": lane["lane_id"], "reviewer_id": f"reviewer-{lane_number}",
                "review_session_id": f"session-{lane_number}", "reviewer_type": "independent",
                "reviewer_model_version": "test", "blinded": True,
                "rubric_version": lane["rubric_version"], "rubric_hash": lane["review_prompt_hash"],
                "review_prompt_hash": lane["review_prompt_hash"],
                "input_hash": hashlib.sha256(lane_path.read_bytes()).hexdigest(), "votes": votes,
            }
            (review_dir / f"lane-{lane_number}-result.json").write_bytes(canonical_json_bytes(result))

    def _aggregate_v5(self, root: Path, outcomes):
        baseline, candidate, comparison, policy, targets, guards = self._fixture(root, 5)
        review_dir = root / "review"
        build_review(baseline, candidate, review_dir, "semantic-test", [], target_dimensions=targets, guard_dimensions=guards, review_policy=policy, comparison=comparison)
        self._write_v5_results(review_dir, outcomes)
        return aggregate_review(review_dir, None, experiment={"target_qualitative_dimensions": targets, "guard_qualitative_dimensions": guards})

    def _aggregate_version(self, root: Path, version: int, outcomes):
        baseline, candidate, comparison, policy, targets, guards = self._fixture(root, version)
        review_dir = root / "review"
        build_review(baseline, candidate, review_dir, "semantic-test", [], target_dimensions=targets, guard_dimensions=guards, review_policy=policy, comparison=comparison)
        self._write_v5_results(review_dir, outcomes)
        return aggregate_review(review_dir, None, experiment={"target_qualitative_dimensions": targets, "guard_qualitative_dimensions": guards})

    def test_v4_builds_pair_id_only_lanes_and_aggregates(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            baseline, candidate, comparison, policy, targets, guards = self._fixture(root)
            review_dir = root / "review"
            built = build_review(baseline, candidate, review_dir, "semantic-test", [], target_dimensions=targets, guard_dimensions=guards, review_policy=policy, comparison=comparison)
            key = json.loads((review_dir / "assignment-key.json").read_text(encoding="utf-8"))
            self.assertEqual(key["schema_version"], "prompt-quality-review-assignment-key/v4")
            for lane_number in (1, 2):
                lane_path = review_dir / f"lane-{lane_number}.json"
                lane = json.loads(lane_path.read_text(encoding="utf-8"))
                self.assertEqual(lane["schema_version"], "prompt-quality-blind-review-lane/v4")
                self.assertEqual(set(lane["pairs"][0]), {"pair_id", "prompts"})
                self.assertNotIn("target_qualitative_dimensions", lane)
                assignments = {item["pair_id"]: item for item in key["lanes"][lane_number - 1]["assignments"]}
                votes = []
                for pair in lane["pairs"]:
                    assignment = assignments[pair["pair_id"]]
                    vote = f"{assignment['candidate_side']}_better"
                    votes.append({"pair_id": pair["pair_id"], "dimensions": {dimension: vote for dimension in ALL_DIMENSIONS}, "hard_defects": {"A": [], "B": []}})
                result = {
                    "schema_version": "prompt-quality-blind-review-result/v4", "lane_id": lane["lane_id"],
                    "reviewer_id": f"reviewer-{lane_number}", "review_session_id": f"session-{lane_number}",
                    "reviewer_type": "independent", "reviewer_model_version": "test", "blinded": True,
                    "rubric_version": lane["rubric_version"], "rubric_hash": lane["review_prompt_hash"],
                    "review_prompt_hash": lane["review_prompt_hash"],
                    "input_hash": hashlib.sha256(lane_path.read_bytes()).hexdigest(), "votes": votes,
                }
                (review_dir / f"lane-{lane_number}-result.json").write_bytes(canonical_json_bytes(result))
            aggregated = aggregate_review(review_dir, None, experiment={"target_qualitative_dimensions": targets, "guard_qualitative_dimensions": guards})
            self.assertEqual(aggregated["schema_version"], "prompt-quality-review/v4")
            self.assertEqual(aggregated["verdict"], "pass")
            self.assertEqual(aggregated["dimensions"]["consistency"]["valid_votes"], 40)
            self.assertEqual(aggregated["candidate_source_tree_sha256"], "b" * 64)
            self.assertEqual(aggregated["candidate_snapshot_content_sha256"], "2" * 64)
            self.assertEqual(len(built["selected_seeds"]), 20)

    def test_v4_rejects_unknown_comparison_and_review_schemas(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            baseline, candidate, comparison, policy, targets, guards = self._fixture(root)
            value = json.loads(comparison.read_text(encoding="utf-8"))
            value["schema_version"] = "prompt-quality-comparison/v999"
            comparison.write_bytes(canonical_json_bytes(value))
            with self.assertRaisesRegex(ValueError, "comparison/v2"):
                build_review(baseline, candidate, root / "review", "semantic-test", [], target_dimensions=targets, guard_dimensions=guards, review_policy=policy, comparison=comparison)
            policy["schema_version"] = "prompt-quality-review-contract/v999"
            with self.assertRaisesRegex(ValueError, "unsupported review contract schema"):
                build_review(baseline, candidate, root / "review-2", "semantic-test", [], review_policy=policy)

    def test_v5_schemas_rubric_and_directional_coverage(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            baseline, candidate, comparison, policy, targets, guards = self._fixture(root, 5)
            review_dir = root / "review"
            build_review(baseline, candidate, review_dir, "semantic-test", [], target_dimensions=targets, guard_dimensions=guards, review_policy=policy, comparison=comparison)
            key = json.loads((review_dir / "assignment-key.json").read_text(encoding="utf-8"))
            lane = json.loads((review_dir / "lane-1.json").read_text(encoding="utf-8"))
            self.assertEqual(key["schema_version"], "prompt-quality-review-assignment-key/v5")
            self.assertEqual(lane["schema_version"], "prompt-quality-blind-review-lane/v5")
            self.assertEqual(lane["result_contract"]["schema_version"], "prompt-quality-blind-review-result/v5")
            self.assertIn("Equal means both prompts are assessable", lane["rubric"])
            self.assertIn("abstain means the dimension cannot be assessed", lane["rubric"])
            self._write_v5_results(review_dir, ["candidate_better"] * 2 + ["equal"] * 38)
            review = aggregate_review(review_dir, None, experiment={"target_qualitative_dimensions": targets, "guard_qualitative_dimensions": guards})
            dimension = review["dimensions"]["consistency"]
            self.assertEqual(review["schema_version"], "prompt-quality-review/v5")
            self.assertEqual(dimension["non_abstain_votes"], 40)
            self.assertEqual(dimension["directional_votes"], 2)
            self.assertEqual(dimension["improvement_support"], 1.0)
            self.assertIn("insufficient_directional_votes", {item["code"] for item in review["failures"]})

    def test_v5_rejects_each_threshold_and_lane_disagreement(self):
        scenarios = {
            "non_abstain": (["candidate_better"] * 35 + ["abstain"] * 5, "insufficient_non_abstain_votes"),
            "support": (["candidate_better"] * 24 + ["candidate_worse"] * 16, "insufficient_improvement_support"),
            "worse_rate": (["candidate_better"] * 35 + ["candidate_worse"] * 5, "candidate_regression_rate"),
            "lanes": (["candidate_better"] * 20 + ["candidate_worse"] * 20, "lane_direction_disagreement"),
        }
        for name, (outcomes, expected) in scenarios.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
                review = self._aggregate_v5(Path(directory), outcomes)
                self.assertIn(expected, {item["code"] for item in review["failures"]})

    def test_v5_rejects_v4_comparison_mixing(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            baseline, candidate, comparison, policy, targets, guards = self._fixture(root, 5)
            value = json.loads(comparison.read_text(encoding="utf-8"))
            value["schema_version"] = "prompt-quality-comparison/v2"
            comparison.write_bytes(canonical_json_bytes(value))
            with self.assertRaisesRegex(ValueError, "comparison/v3"):
                build_review(baseline, candidate, root / "review", "semantic-test", [], target_dimensions=targets, guard_dimensions=guards, review_policy=policy, comparison=comparison)

    def test_v6_guard_regression_uses_non_abstain_denominator(self):
        for name, outcomes, expected_rate in (
            ("one_worse", ["equal"] * 39 + ["candidate_worse"], 0.025),
            ("all_equal", ["equal"] * 40, 0.0),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
                review = self._aggregate_version(Path(directory), 6, outcomes)
                guard = review["dimensions"]["redundancy"]
                self.assertEqual(review["schema_version"], "prompt-quality-review/v6")
                self.assertEqual(guard["candidate_regression_rate"], expected_rate)
                self.assertNotIn("worse_rate", guard)
                self.assertTrue(guard["passed"], review["failures"])

    def test_v6_guard_all_abstain_fails_coverage(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            review = self._aggregate_version(Path(directory), 6, ["abstain"] * 40)
            self.assertFalse(review["dimensions"]["redundancy"]["passed"])
            self.assertIn("insufficient_non_abstain_votes", {item["code"] for item in review["failures"]})

    def test_v6_target_directional_support_and_lane_failures(self):
        scenarios = {
            "directional": (["candidate_better"] * 2 + ["equal"] * 38, "insufficient_directional_votes"),
            "support": (["candidate_better"] * 24 + ["candidate_worse"] * 16, "insufficient_improvement_support"),
            "lanes": (["candidate_better"] * 20 + ["candidate_worse"] * 20, "lane_direction_disagreement"),
        }
        for name, (outcomes, expected) in scenarios.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
                review = self._aggregate_version(Path(directory), 6, outcomes)
                self.assertIn(expected, {item["code"] for item in review["failures"]})

    def test_v6_rejects_v5_comparison_mixing(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            baseline, candidate, comparison, policy, targets, guards = self._fixture(root, 6)
            value = json.loads(comparison.read_text(encoding="utf-8"))
            value["schema_version"] = "prompt-quality-comparison/v3"
            comparison.write_bytes(canonical_json_bytes(value))
            with self.assertRaisesRegex(ValueError, "comparison/v4"):
                build_review(baseline, candidate, root / "review", "semantic-test", [], target_dimensions=targets, guard_dimensions=guards, review_policy=policy, comparison=comparison)


if __name__ == "__main__":
    unittest.main()
