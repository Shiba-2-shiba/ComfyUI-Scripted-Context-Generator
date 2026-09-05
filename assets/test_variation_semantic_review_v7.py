"""Prospective review-contract tests. Synthetic votes never serve as run evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from assets import test_variation_semantic_review as review_fixtures
from tools.aggregate_blind_prompt_review import aggregate_review
from tools.build_blind_prompt_review import build_review
from tools.workflow_prompt_runner import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]


class ProspectiveSemanticReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "assets/results")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.helper = review_fixtures.VariationSemanticReviewTests()

    def fixture(self, version=7):
        before, after, comparison_path, policy, targets, guards = self.helper._fixture(self.root, 6)
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        if version == 7:
            policy = json.loads((ROOT / "vocab/data/variation_semantic_review_policy_v4.json").read_text(encoding="utf-8"))["review"]
            targets = ["naturalness", "image_prompt_suitability"]
            guards = ["consistency", "protagonist_clarity", "redundancy", "diversity"]
            comparison["schema_version"] = "prompt-quality-comparison/v5"
            comparison["review_contract_hash"] = hashlib.sha256(canonical_json_bytes(policy)).hexdigest()
            comparison["qualitative_scope_hash"] = hashlib.sha256(canonical_json_bytes({"guard_qualitative_dimensions": guards, "target_qualitative_dimensions": targets})).hexdigest()
            selection = comparison["review_selection"]
            selection["dimensions"]["consistency"]["minimum_directional_votes"] = 0
            selection.pop("selection_hash")
            selection["selection_hash"] = hashlib.sha256(canonical_json_bytes(selection)).hexdigest()
            comparison_path.write_bytes(canonical_json_bytes(comparison))
        self.experiment = {"target_qualitative_dimensions": targets, "guard_qualitative_dimensions": guards}
        self.policy = policy
        self.inputs = (before, after, comparison_path)
        return before, after, comparison_path

    def lanes(self, version=7):
        before, after, comparison = self.fixture(version)
        self.review_dir = self.root / "review"
        build_review(before, after, self.review_dir, "semantic-test", [],
                     target_dimensions=self.experiment["target_qualitative_dimensions"], guard_dimensions=self.experiment["guard_qualitative_dimensions"],
                     review_policy=self.policy, comparison=comparison)
        self.helper._write_v5_results(self.review_dir, ["candidate_better"] * 40)
        self.votes("consistency", ["equal"] * 40)

    def votes(self, dimension, outcomes):
        key = json.loads((self.review_dir / "assignment-key.json").read_text(encoding="utf-8"))
        for number, lane in enumerate(key["lanes"], 1):
            path = self.review_dir / f"lane-{number}-result.json"
            result = json.loads(path.read_text(encoding="utf-8"))
            assignments = {row["pair_id"]: row for row in lane["assignments"]}
            for index, row in enumerate(result["votes"]):
                outcome = outcomes[(number - 1) * 20 + index]
                if outcome in {"candidate_better", "candidate_worse"}:
                    side = "candidate_side" if outcome == "candidate_better" else "incumbent_side"
                    outcome = assignments[row["pair_id"]][side] + "_better"
                row["dimensions"][dimension] = outcome
            path.write_bytes(canonical_json_bytes(result))

    def aggregate(self):
        return aggregate_review(self.review_dir, None, experiment=self.experiment)

    def test_v7_equal_consistency_passes_only_as_nonregression_guard(self):
        self.lanes()
        result = self.aggregate()
        self.assertEqual(result["schema_version"], "prompt-quality-review/v7")
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["dimensions"]["consistency"]["scope"], "guard")
        self.assertEqual(result["dimensions"]["consistency"]["non_abstain_votes"], 40)
        self.assertEqual(result["dimensions"]["consistency"]["directional_votes"], 0)
        self.assertEqual(result["dimensions"]["diversity"]["authority"], "current_source_corpus_confirmation")

    def test_old_v6_still_rejects_equal_consistency(self):
        self.lanes(6)
        result = self.aggregate()
        self.assertEqual(result["schema_version"], "prompt-quality-review/v6")
        self.assertEqual(result["verdict"], "reject")
        self.assertTrue(any(item["code"] == "insufficient_directional_votes" and item["dimension"] == "consistency" for item in result["failures"]))

    def test_consistency_still_requires36_nonabstain_and_regression_at_most_point1(self):
        self.lanes()
        for outcomes in (["abstain"] * 5 + ["equal"] * 35, ["candidate_worse"] * 5 + ["equal"] * 35):
            self.votes("consistency", outcomes)
            self.assertEqual(self.aggregate()["verdict"], "reject")

    def test_targets_and_other_guards_are_not_relaxed(self):
        self.lanes()
        self.votes("naturalness", ["equal"] * 40)
        self.assertEqual(self.aggregate()["verdict"], "reject")
        self.votes("naturalness", ["candidate_better"] * 40)
        self.votes("protagonist_clarity", ["candidate_worse"] * 5 + ["equal"] * 35)
        self.assertEqual(self.aggregate()["verdict"], "reject")

    def test_mismatched_result_generation_and_candidate_hard_defect_reject(self):
        self.lanes()
        path = self.review_dir / "lane-1-result.json"
        result = json.loads(path.read_text(encoding="utf-8"))
        result["schema_version"] = "prompt-quality-blind-review-result/v6"
        path.write_bytes(canonical_json_bytes(result))
        self.assertEqual(self.aggregate()["verdict"], "reject")
        result["schema_version"] = "prompt-quality-blind-review-result/v7"
        key = json.loads((self.review_dir / "assignment-key.json").read_text(encoding="utf-8"))
        assignment = next(row for row in key["lanes"][0]["assignments"] if row["pair_id"] == result["votes"][0]["pair_id"])
        result["votes"][0]["hard_defects"][assignment["candidate_side"]] = [{"code": "runtime_error", "evidence": "unit-only defect evidence"}]
        path.write_bytes(canonical_json_bytes(result))
        self.assertEqual(self.aggregate()["candidate_hard_defect_count"], 1)
        self.assertEqual(self.aggregate()["verdict"], "reject")

    def test_old_comparison_generation_cannot_be_reinterpreted(self):
        before, after, path = self.fixture()
        value = json.loads(path.read_text(encoding="utf-8"))
        value["schema_version"] = "prompt-quality-comparison/v4"
        path.write_bytes(canonical_json_bytes(value))
        with self.assertRaises(ValueError):
            build_review(before, after, self.root / "review", "semantic-test", [], review_policy=self.policy, comparison=path)

    def test_rehashed_target_threshold_tamper_is_rejected(self):
        before, after, path = self.fixture()
        value = json.loads(path.read_text(encoding="utf-8"))
        selection = value["review_selection"]
        selection["dimensions"]["naturalness"]["minimum_directional_votes"] = 0
        selection.pop("selection_hash")
        selection["selection_hash"] = hashlib.sha256(canonical_json_bytes(selection)).hexdigest()
        path.write_bytes(canonical_json_bytes(value))
        with self.assertRaises(ValueError):
            build_review(before, after, self.root / "review", "semantic-test", [],
                         target_dimensions=self.experiment["target_qualitative_dimensions"], guard_dimensions=self.experiment["guard_qualitative_dimensions"],
                         review_policy=self.policy, comparison=path)

    def test_v7_still_requires_independent_review_sessions(self):
        self.lanes()
        path = self.review_dir / "lane-2-result.json"
        result = json.loads(path.read_text(encoding="utf-8"))
        result["review_session_id"] = "session-1"
        path.write_bytes(canonical_json_bytes(result))
        report = self.aggregate()
        self.assertEqual(report["verdict"], "reject")
        self.assertTrue(any(item["code"] == "review_session_not_independent" for item in report["failures"]))


if __name__ == "__main__":
    unittest.main()
