import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path


from tools.aggregate_blind_prompt_review import aggregate_review
from tools.build_blind_prompt_review import build_review
from tools.compare_prompt_quality import _review_v3_selection
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


class TestReviewContractV3(unittest.TestCase):
    def setUp(self):
        results = ROOT / "assets" / "results"
        results.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="review-v3-", dir=results))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.policy = {
            "schema_version": "prompt-quality-review-contract/v3",
            "dimension_authority": {
                "consistency": "affected_seed_pairwise",
                "naturalness": "selected_pairwise",
                "image_prompt_suitability": "selected_pairwise",
                "protagonist_clarity": "selected_pairwise",
                "redundancy": "selected_pairwise",
                "diversity": "current_source_corpus_confirmation",
            },
            "hard_defect_codes": ["runtime_error", "consistency_rule_conflict"],
            "independent_lanes": 2,
            "minimum_valid_vote_fraction": 0.9,
            "minimum_valid_votes_cap": 36,
            "target_dimension_contract": {
                "min_improvement_support": 0.65,
                "max_candidate_worse_rate": 0.10,
                "require_lane_direction_agreement": True,
            },
            "guard_dimension_contract": {
                "max_candidate_worse_rate": 0.10,
                "require_lane_direction_agreement": False,
            },
        }
        before = [
            {"run_seed": seed, "cohort": "control", "cleaned_prompt": f"before {seed}"}
            for seed in range(40)
        ]
        after = [
            {**record, "cleaned_prompt": f"after {record['run_seed']}" if record["run_seed"] < 10 else record["cleaned_prompt"]}
            for record in before
        ]
        self.before_path = self.root / "before.jsonl"
        self.after_path = self.root / "after.jsonl"
        self.before_path.write_bytes(b"".join(canonical_json_bytes(item) for item in before))
        self.after_path.write_bytes(b"".join(canonical_json_bytes(item) for item in after))
        (self.root / "confirmation.json").write_bytes(canonical_json_bytes({
            "cohort_hash": "c" * 64, "source_tree_hash": "1" * 64,
        }))
        issue_seeds = [1, 2, 3, 4, 5, 6]
        before_issues = {
            "issues": [
                {"affected_seeds": issue_seeds[:4], "issue_code": "consistency_rule_conflict"},
                {"affected_seeds": issue_seeds[2:], "issue_code": "location_action_object_conflict"},
            ],
            "schema_version": "prompt-quality-issues/v1",
        }
        after_issues = {"issues": [], "schema_version": "prompt-quality-issues/v1"}
        selection = _review_v3_selection(
            "v3-test", before, after, self.policy, before_issues, after_issues,
            ["protagonist_clarity", "redundancy", "diversity"],
        )
        self.assertEqual(selection["selected_seeds"][:6], issue_seeds)
        self.assertEqual(selection["dimension_issue_code_mapping"], {
            "consistency": ["consistency_rule_conflict", "location_action_object_conflict"],
        })
        self.assertEqual(selection["dimensions"]["consistency"]["seeds"], issue_seeds)
        self.assertEqual(selection["dimensions"]["consistency"]["minimum_valid_votes"], 11)
        self.assertEqual(
            selection["dimensions"]["consistency"]["eligible_seed_hash"],
            selection["eligible_seed_hashes"]["consistency"],
        )
        self.assertEqual(selection["dimensions"]["naturalness"]["minimum_valid_votes"], 36)
        self.assertEqual(selection["dimensions"]["protagonist_clarity"]["minimum_valid_votes"], 0)
        self.assertEqual(selection["dimensions"]["redundancy"]["minimum_valid_votes"], 0)
        self.assertEqual(selection["dimensions"]["diversity"]["minimum_valid_votes"], 0)
        self.comparison_path = self.root / "comparison.json"
        targets = ["consistency", "naturalness", "image_prompt_suitability"]
        guards = ["protagonist_clarity", "redundancy", "diversity"]
        self.comparison_path.write_bytes(canonical_json_bytes({
            "experiment_id": "v3-test",
            "qualitative_scope_hash": hashlib.sha256(canonical_json_bytes({
                "guard_qualitative_dimensions": guards,
                "target_qualitative_dimensions": targets,
            })).hexdigest(),
            "record_artifact_hashes": {
                "before": hashlib.sha256(self.before_path.read_bytes()).hexdigest(),
                "after": hashlib.sha256(self.after_path.read_bytes()).hexdigest(),
            },
            "review_contract_hash": hashlib.sha256(canonical_json_bytes(self.policy)).hexdigest(),
            "review_selection": selection,
            "schema_version": "prompt-quality-comparison/v1",
        }))
        self.review_dir = self.root / "review"
        build_review(
            self.before_path, self.after_path, self.review_dir, "v3-test", [],
            target_dimensions=targets,
            guard_dimensions=guards,
            review_policy=self.policy, comparison=self.comparison_path,
        )

    def write_results(self, hard_defect=None):
        key = json.loads((self.review_dir / "assignment-key.json").read_text(encoding="utf-8"))
        for lane_key in key["lanes"]:
            lane_id = lane_key["lane_id"]
            lane_path = self.review_dir / f"{lane_id}.json"
            lane = json.loads(lane_path.read_text(encoding="utf-8"))
            assignments = {item["pair_id"]: item for item in lane_key["assignments"]}
            votes = []
            for index, pair in enumerate(lane["pairs"]):
                candidate = assignments[pair["pair_id"]]["candidate_side"]
                defects = {"A": [], "B": []}
                if hard_defect is not None and index == 0 and lane_id == "lane-1":
                    defects[candidate] = [hard_defect]
                votes.append({
                    "dimensions": {
                        dimension: ("equal" if dimension in {"protagonist_clarity", "redundancy", "diversity"} else f"{candidate}_better")
                        for dimension in lane["dimensions"]
                    },
                    "hard_defects": defects,
                    "pair_id": pair["pair_id"],
                    "run_seed": pair["run_seed"],
                })
            result = {
                "blinded": True,
                "input_hash": hashlib.sha256(lane_path.read_bytes()).hexdigest(),
                "lane_id": lane_id,
                "review_prompt_hash": lane["review_prompt_hash"],
                "reviewer_id": f"reviewer-{lane_id}",
                "reviewer_model_version": "fixture/v3",
                "reviewer_type": "fixture",
                "rubric_hash": lane["review_prompt_hash"],
                "rubric_version": lane["rubric_version"],
                "schema_version": "prompt-quality-blind-review-result/v3",
                "votes": votes,
            }
            (self.review_dir / f"{lane_id}-result.json").write_bytes(canonical_json_bytes(result))

    def aggregate(self):
        experiment = {
            "target_qualitative_dimensions": ["consistency", "naturalness", "image_prompt_suitability"],
            "guard_qualitative_dimensions": ["protagonist_clarity", "redundancy", "diversity"],
        }
        return aggregate_review(self.review_dir, None, experiment=experiment, policy={"review": self.policy})

    def test_v3_freezes_scope_minimums_and_excludes_diversity_pairwise_authority(self):
        self.write_results()
        result = self.aggregate()
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["dimensions"]["consistency"]["valid_votes"], 12)
        self.assertEqual(result["dimensions"]["diversity"]["authority"], "current_source_corpus_confirmation")
        self.assertEqual(result["dimensions"]["diversity"]["valid_votes"], 0)
        self.assertEqual(result["dimensions"]["protagonist_clarity"]["valid_votes"], 0)
        self.assertTrue(result["dimensions"]["protagonist_clarity"]["passed"])
        self.assertEqual(result["hash_validation"], "pass")

    def test_v3_real_consistency_issue_fixture_includes_every_eligible_seed_first(self):
        eligible = [14, 33, 36, 51, 7413556593436848660, 15346476473046071932]
        cohort = eligible + list(range(100, 114))
        before = [
            {"run_seed": seed, "cohort": "control", "cleaned_prompt": f"before {seed}"}
            for seed in cohort
        ]
        after = [
            {**record, "cleaned_prompt": f"after {record['run_seed']}"}
            for record in before
        ]
        issues = {
            "issues": [
                {"affected_seeds": eligible, "issue_code": "consistency_rule_conflict"},
                {"affected_seeds": eligible, "issue_code": "location_action_object_conflict"},
            ],
            "schema_version": "prompt-quality-issues/v1",
        }
        selection = _review_v3_selection(
            "real-g008-fixture", before, after, self.policy, issues,
            {"issues": [], "schema_version": "prompt-quality-issues/v1"},
            ["protagonist_clarity", "redundancy", "diversity"],
        )
        self.assertEqual(selection["selected_seeds"][:6], eligible)
        self.assertEqual(selection["dimensions"]["consistency"]["seeds"], eligible)
        self.assertEqual(selection["dimensions"]["consistency"]["minimum_valid_votes"], 11)

    def test_v3_rejects_free_string_and_unknown_hard_defects(self):
        for defect in ("runtime_error", {"code": "unknown", "evidence": "shown"}):
            with self.subTest(defect=defect):
                self.write_results(defect)
                result = self.aggregate()
                self.assertEqual(result["status"], "fail")
                self.assertIn("invalid_vote_contract", {item["code"] for item in result["failures"]})

    def test_v3_accepts_closed_code_with_free_evidence_and_rejects_candidate(self):
        self.write_results({"code": "runtime_error", "evidence": "trace observed"})
        result = self.aggregate()
        self.assertEqual(result["candidate_hard_defect_count"], 1)
        self.assertEqual(result["hard_defects"]["candidate_only"], {"runtime_error": 1})

    def test_v3_recomputes_bound_comparison_hash(self):
        self.write_results()
        self.comparison_path.write_bytes(canonical_json_bytes({"tampered": True}))
        result = self.aggregate()
        self.assertIn("comparison_artifact_hash_mismatch", {item["code"] for item in result["failures"]})


if __name__ == "__main__":
    unittest.main()
