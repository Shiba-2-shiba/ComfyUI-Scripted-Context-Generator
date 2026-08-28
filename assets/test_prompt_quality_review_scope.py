import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path


from tools.aggregate_blind_prompt_review import aggregate_review
from tools.build_blind_prompt_review import build_review
from tools.workflow_prompt_runner import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
TARGETS = ["consistency", "protagonist_clarity", "image_prompt_suitability"]
GUARDS = ["naturalness", "redundancy", "diversity"]
POLICY = {
    "review": {
        "target_dimension_contract": {
            "minimum_valid_votes": 36,
            "min_improvement_support": 0.65,
            "max_candidate_worse_rate": 0.10,
            "require_lane_direction_agreement": True,
        },
        "guard_dimension_contract": {
            "max_candidate_worse_rate": 0.10,
            "require_improvement": False,
            "require_lane_direction_agreement": False,
        },
    }
}
EXPERIMENT = {
    "target_qualitative_dimensions": TARGETS,
    "guard_qualitative_dimensions": GUARDS,
}


class TestHypothesisScopedReview(unittest.TestCase):
    def setUp(self):
        results = ROOT / "assets" / "results"
        results.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="review-scope-", dir=results))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        records = [
            {"run_seed": seed, "cohort": "repro_cohort", "cleaned_prompt": f"prompt {seed}"}
            for seed in range(20)
        ]
        for name in ("before", "after"):
            (self.root / f"{name}.jsonl").write_bytes(b"".join(canonical_json_bytes(item) for item in records))
        (self.root / "confirmation.json").write_bytes(canonical_json_bytes({
            "cohort_hash": "c" * 64,
            "source_tree_hash": "1" * 64,
        }))
        self.review_dir = self.root / "review"
        build_review(
            self.root / "before.jsonl", self.root / "after.jsonl", self.review_dir,
            "scope-test", [], selected_seeds=range(20),
            target_dimensions=TARGETS, guard_dimensions=GUARDS,
            review_policy=POLICY["review"],
        )

    def write_results(self, *, target_equal=False, guard_worse=0, guard_better_lane1=False, candidate_hard=False):
        key = json.loads((self.review_dir / "assignment-key.json").read_text(encoding="utf-8"))
        for lane_number, lane_key in enumerate(key["lanes"], start=1):
            lane_id = f"lane-{lane_number}"
            lane_path = self.review_dir / f"{lane_id}.json"
            lane = json.loads(lane_path.read_text(encoding="utf-8"))
            assignments = {item["pair_id"]: item for item in lane_key["assignments"]}
            votes = []
            for index, pair in enumerate(lane["pairs"]):
                assignment = assignments[pair["pair_id"]]
                candidate = assignment["candidate_side"]
                incumbent = assignment["incumbent_side"]
                dimensions = {
                    dimension: "equal" if target_equal else f"{candidate}_better"
                    for dimension in TARGETS
                }
                dimensions.update({dimension: "equal" for dimension in GUARDS})
                if guard_better_lane1 and lane_number == 1:
                    dimensions["naturalness"] = f"{candidate}_better"
                if index < guard_worse:
                    dimensions["naturalness"] = f"{incumbent}_better"
                hard = {"A": [], "B": []}
                if candidate_hard and index == 0 and lane_number == 1:
                    hard[candidate] = ["candidate_hard_defect"]
                votes.append({
                    "dimensions": dimensions,
                    "hard_defects": hard,
                    "pair_id": pair["pair_id"],
                    "run_seed": pair["run_seed"],
                })
            result = {
                "blinded": True,
                "input_hash": hashlib.sha256(lane_path.read_bytes()).hexdigest(),
                "lane_id": lane_id,
                "review_prompt_hash": lane["review_prompt_hash"],
                "reviewer_id": f"reviewer-{lane_number}",
                "reviewer_model_version": "fixture-model/v1",
                "reviewer_type": "fixture",
                "rubric_hash": lane["review_prompt_hash"],
                "rubric_version": lane["rubric_version"],
                "schema_version": "prompt-quality-blind-review-result/v1",
                "votes": votes,
            }
            (self.review_dir / f"{lane_id}-result.json").write_bytes(canonical_json_bytes(result))

    def aggregate(self):
        return aggregate_review(
            self.review_dir, self.root / "review.json", experiment=EXPERIMENT, policy=POLICY
        )

    def test_only_target_dimensions_require_improvement_votes(self):
        self.write_results(guard_better_lane1=True)
        result = self.aggregate()
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["dimensions"]["naturalness"]["valid_votes"], 20)
        self.assertTrue(result["dimensions"]["naturalness"]["passed"])
        self.assertEqual(
            result["dimensions"]["naturalness"]["lane_directions"],
            {"lane-1": "improvement", "lane-2": "no_change"},
        )

    def test_assignment_side_inversion_is_rejected(self):
        key_path = self.review_dir / "assignment-key.json"
        key = json.loads(key_path.read_text(encoding="utf-8"))
        assignment = key["lanes"][0]["assignments"][0]
        assignment["candidate_side"], assignment["incumbent_side"] = (
            assignment["incumbent_side"], assignment["candidate_side"]
        )
        key_path.write_bytes(canonical_json_bytes(key))
        self.write_results()
        result = self.aggregate()
        self.assertEqual(result["status"], "fail")
        self.assertIn("assignment_side_drift", {item["code"] for item in result["failures"]})

    def test_extra_duplicate_vote_and_missing_hard_defects_are_rejected(self):
        for mutation in ("duplicate", "missing_hard_defects"):
            with self.subTest(mutation=mutation):
                self.write_results()
                path = self.review_dir / "lane-1-result.json"
                result_payload = json.loads(path.read_text(encoding="utf-8"))
                if mutation == "duplicate":
                    result_payload["votes"].append(dict(result_payload["votes"][0]))
                else:
                    result_payload["votes"][0].pop("hard_defects")
                path.write_bytes(canonical_json_bytes(result_payload))
                result = self.aggregate()
                self.assertEqual(result["status"], "fail")
                self.assertIn("invalid_vote_contract", {item["code"] for item in result["failures"]})

    def test_blank_or_non_string_reviewer_metadata_is_rejected(self):
        for field, value in (("reviewer_id", ""), ("reviewer_type", None), ("reviewer_model_version", 7)):
            with self.subTest(field=field):
                self.write_results()
                path = self.review_dir / "lane-1-result.json"
                payload = json.loads(path.read_text(encoding="utf-8"))
                payload[field] = value
                path.write_bytes(canonical_json_bytes(payload))
                result = self.aggregate()
                self.assertEqual(result["status"], "fail")
                self.assertIn("invalid_result_metadata", {item["code"] for item in result["failures"]})

    def test_lane_blindness_or_extra_implementation_detail_is_rejected(self):
        for field, value in (("blinded", False), ("implementation_hint", "candidate is A")):
            with self.subTest(field=field):
                path = self.review_dir / "lane-1.json"
                original = json.loads(path.read_text(encoding="utf-8"))
                lane = dict(original)
                lane[field] = value
                path.write_bytes(canonical_json_bytes(lane))
                self.write_results()
                result = self.aggregate()
                self.assertEqual(result["status"], "fail")
                self.assertIn("invalid_lane_contract", {item["code"] for item in result["failures"]})
                path.write_bytes(canonical_json_bytes(original))

    def test_permissive_review_contract_with_stale_hash_is_rejected(self):
        key_path = self.review_dir / "assignment-key.json"
        key = json.loads(key_path.read_text(encoding="utf-8"))
        key["review_contract"]["target_dimension_contract"]["minimum_valid_votes"] = 0
        key_path.write_bytes(canonical_json_bytes(key))
        self.write_results(target_equal=True)
        result = aggregate_review(self.review_dir, self.root / "tampered-review.json", experiment=EXPERIMENT, policy={})
        self.assertEqual(result["status"], "fail")
        self.assertIn("review_contract_hash_mismatch", {item["code"] for item in result["failures"]})

    def test_target_dimension_still_requires_36_valid_votes(self):
        self.write_results(target_equal=True)
        result = self.aggregate()
        self.assertEqual(result["status"], "fail")
        self.assertIn("insufficient_valid_votes", {item["code"] for item in result["failures"]})

    def test_guard_candidate_worse_rate_over_ten_percent_rejects(self):
        self.write_results(guard_worse=3)
        result = self.aggregate()
        self.assertEqual(result["status"], "fail")
        failure = next(item for item in result["failures"] if item["code"] == "candidate_regression_rate")
        self.assertEqual(failure["dimension"], "naturalness")

    def test_candidate_only_hard_defect_rejects(self):
        self.write_results(candidate_hard=True)
        result = self.aggregate()
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["candidate_hard_defect_count"], 1)


if __name__ == "__main__":
    unittest.main()
