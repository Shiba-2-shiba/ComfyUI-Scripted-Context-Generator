import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.compare_prompt_quality import compare_runs, promote_check
from tools import build_prompt_quality_confirmation as confirmation
from tools.aggregate_blind_prompt_review import aggregate_review
from tools.build_blind_prompt_review import build_review
from tools.prompt_quality_loop import commit_transition, experiment_writer_lock, load_state_records, recover_experiment
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


FIXTURE = ROOT / "assets" / "fixtures" / "prompt_quality" / "manual_experiments.json"


def valid_blind_review(comparison=None):
    dimensions = {}
    for name in (
        "protagonist_clarity", "consistency", "naturalness",
        "redundancy", "diversity", "image_prompt_suitability",
    ):
        dimensions[name] = {
            "passed": True,
            "valid_votes": 36 if name in {"consistency", "naturalness"} else 0,
        }
    return {
        "assignment_key_hash": "a" * 64,
        "candidate_hard_defect_count": 0,
        "dimensions": dimensions,
        "failures": [],
        "guard_qualitative_dimensions": [
            "protagonist_clarity", "redundancy", "diversity", "image_prompt_suitability",
        ],
        "hash_validation": "pass",
        "lane_input_hashes": {"lane-1": "b" * 64, "lane-2": "c" * 64},
        "lane_result_hashes": {"lane-1": "d" * 64, "lane-2": "e" * 64},
        "pair_count_per_lane": 20,
        "reviewers": [
            {"reviewer_id": "reviewer-1"},
            {"reviewer_id": "reviewer-2"},
        ],
        "reviewed_record_hashes": dict((comparison or {}).get("record_artifact_hashes", {"before": "f" * 64, "after": "0" * 64})),
        "reviewed_run_provenance": {
            side: {
                "cohort_hash": (comparison or {}).get("cohort_hashes", {}).get(side, "2" * 64),
                "source_tree_hash": (comparison or {}).get("source_tree_hashes", {}).get(side, "3" * 64),
            }
            for side in ("before", "after")
        },
        "review_contract_hash": (comparison or {}).get("review_contract_hash", "4" * 64),
        "schema_version": "prompt-quality-review/v1",
        "status": "pass",
        "target_qualitative_dimensions": ["consistency", "naturalness"],
        "verdict": "pass",
    }


def valid_verification(comparison, root, comparison_path, review_path):
    evidence_dir = Path(root) / "verification-evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    gates = {}
    gate_names = (
        "action_pools", "blind_review", "browser", "compatibility_review",
        "data_validation", "frontend", "full_flow", "prompt_quality_confirmation",
        "python_tests", "target_comparison", "widgets",
    )
    for gate_name in gate_names:
        if gate_name == "blind_review":
            result_path = Path(review_path)
        elif gate_name == "target_comparison":
            result_path = Path(comparison_path)
        else:
            result_path = evidence_dir / f"{gate_name}-result.json"
            summary = {"checks_passed": 1}
            if gate_name == "python_tests":
                summary = {"errors": 0, "failures": 0, "skipped": 0, "tests_passed": 505, "tests_run": 505}
            elif gate_name == "data_validation":
                summary = {"errors": 0, "warnings": 0}
            elif gate_name == "frontend":
                summary = {"failures": 0, "tests_passed": 4}
            elif gate_name == "browser":
                summary = {"failures": 0, "tests_passed": 2}
            elif gate_name == "prompt_quality_confirmation":
                summary = {"hard_gate_failures": 0, "objectives_passed": 3}
            elif gate_name == "full_flow":
                summary = {"checks_passed": 1, "failures": 0}
            elif gate_name == "widgets":
                summary = {"issues": 0}
            elif gate_name == "compatibility_review":
                summary = {"errors": 0, "extra_rows": 0, "missing_rows": 0}
            elif gate_name == "action_pools":
                summary = {"errors": 0, "missing_pools": 0}
            result_path.write_bytes(canonical_json_bytes({
                "exit_code": 0,
                "gate_name": gate_name,
                "schema_version": "prompt-quality-gate-result/v1",
                "source_tree_hash": comparison["source_tree_hashes"]["after"],
                "status": "pass",
                "summary": summary,
            }))
        evidence_path = evidence_dir / f"{gate_name}.json"
        evidence_path.write_bytes(canonical_json_bytes({
            "command": f"fixture {gate_name}",
            "exit_code": 0,
            "gate_name": gate_name,
            "result_hash": hashlib.sha256(result_path.read_bytes()).hexdigest(),
            "result_path": result_path.relative_to(ROOT).as_posix(),
            "schema_version": "prompt-quality-verification-evidence/v1",
            "source_tree_hash": comparison["source_tree_hashes"]["after"],
            "status": "pass",
        }))
        gates[gate_name] = {
            "evidence_hash": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
            "evidence_path": evidence_path.relative_to(ROOT).as_posix(),
            "status": "pass",
        }
    payload = {
        "artifacts": {
            "comparison_hash": hashlib.sha256(canonical_json_bytes(comparison)).hexdigest(),
            "source_tree_hash": comparison["source_tree_hashes"]["after"],
        },
        "quality_gates": gates,
        "schema_version": "prompt-quality-verification/v2",
        "status": "pass",
    }
    path = Path(root) / "verification.json"
    path.write_bytes(canonical_json_bytes(payload))
    return path


def deep_update(target, patch):
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_update(target[key], value)
        else:
            target[key] = copy.deepcopy(value)
    return target


class TestPromptQualityComparison(unittest.TestCase):
    def setUp(self):
        result_root = ROOT / "assets" / "results"
        result_root.mkdir(parents=True, exist_ok=True)
        self.temporary = Path(tempfile.mkdtemp(prefix="prompt-quality-compare-", dir=result_root))
        self.addCleanup(lambda: shutil.rmtree(self.temporary, ignore_errors=True))
        self.policy = {
            "policy_version": "test-policy/v1",
            "guard_max_absolute_regression": 0.02,
            "hard_gate_metrics": ["identity.hard_defect_count", "runtime.determinism_mismatch_count"],
            "non_regression_metrics": ["diversity.exact_duplicate_rate", "runtime.fallback_rate"],
            "metrics": {
                "identity.defect_count": {"kind": "behavior", "direction": "decrease", "min_absolute": 2, "min_relative": 0.10},
                "diversity.template_entropy": {"kind": "diversity", "direction": "increase", "min_relative": 0.05},
                "identity.single_female_rate": {"direction": "increase"},
            },
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
            },
            "context_size": {"p95_max_ratio": 1.10, "max_max_ratio": 1.25},
        }
        self.experiment = {
            "experiment_id": "fixture-experiment",
            "target_metric": "identity.defect_count",
            "guard_metrics": ["identity.single_female_rate"],
            "target_qualitative_dimensions": ["consistency", "naturalness"],
            "guard_qualitative_dimensions": [
                "protagonist_clarity", "redundancy", "diversity", "image_prompt_suitability",
            ],
        }
        self.base_metrics = {
            "schema_version": "prompt-quality-analysis-metrics/v1",
            "analyzer_version": "analyzer/v1",
            "policy_version": "test-policy/v1",
            "identity": {"defect_count": 10, "hard_defect_count": 0, "single_female_rate": 1.0},
            "diversity": {"template_entropy": 100.0, "exact_duplicate_rate": 0.0},
            "runtime": {"determinism_mismatch_count": 0, "fallback_rate": 0.0, "context_bytes_p95": 100.0, "context_bytes_max": 100.0},
        }

    def write_run(self, name, metrics_patch=None, *, workflow_hash="a" * 64, seeds=None):
        run_dir = self.temporary / name
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir()
        metrics = deep_update(copy.deepcopy(self.base_metrics), metrics_patch or {})
        (run_dir / "metrics.json").write_bytes(canonical_json_bytes(metrics))
        manifest = {
            "cohort_hash": "c" * 64,
            "workflow_hash": workflow_hash,
            "effective_workflow_hash": "e" * 64,
            "profile_hash": "p" * 64,
            "source_tree_hash": "1" * 64,
        }
        (run_dir / "run-manifest.json").write_bytes(canonical_json_bytes(manifest))
        selected_seeds = list(range(80)) if seeds is None else list(seeds)
        records = [
            {
                "run_seed": seed,
                "cohort": "control" if index < 64 else "exploration",
                "cleaned_prompt": f"A girl checks item {seed} in a quiet station.",
            }
            for index, seed in enumerate(selected_seeds)
        ]
        (run_dir / "records.jsonl").write_bytes(b"".join(canonical_json_bytes(item) for item in records))
        return run_dir

    def compare(self, before_patch=None, after_patch=None, *, experiment_patch=None):
        before = self.write_run("before", before_patch)
        after = self.write_run("after", after_patch)
        experiment = deep_update(copy.deepcopy(self.experiment), experiment_patch or {})
        return compare_runs(before, after, policy=self.policy, experiment=experiment)

    def bound_review(self, comparison):
        review_dir = self.temporary / "bound-review"
        shutil.rmtree(review_dir, ignore_errors=True)
        targets = ["consistency", "naturalness"]
        guards = [
            "protagonist_clarity", "redundancy", "diversity", "image_prompt_suitability",
        ]
        build_review(
            self.temporary / "before" / "records.jsonl",
            self.temporary / "after" / "records.jsonl",
            review_dir,
            comparison["experiment_id"],
            [],
            selected_seeds=range(20),
            target_dimensions=targets,
            guard_dimensions=guards,
            review_policy=self.policy["review"],
        )
        key = json.loads((review_dir / "assignment-key.json").read_text(encoding="utf-8"))
        for lane_key in key["lanes"]:
            lane_id = lane_key["lane_id"]
            lane_path = review_dir / f"{lane_id}.json"
            lane = json.loads(lane_path.read_text(encoding="utf-8"))
            assignments = {item["pair_id"]: item for item in lane_key["assignments"]}
            votes = []
            for pair in lane["pairs"]:
                candidate = assignments[pair["pair_id"]]["candidate_side"]
                votes.append({
                    "dimensions": {
                        dimension: f"{candidate}_better" if dimension in targets else "equal"
                        for dimension in lane["dimensions"]
                    },
                    "hard_defects": {"A": [], "B": []},
                    "pair_id": pair["pair_id"],
                    "run_seed": pair["run_seed"],
                })
            result = {
                "blinded": True,
                "input_hash": hashlib.sha256(lane_path.read_bytes()).hexdigest(),
                "lane_id": lane_id,
                "review_prompt_hash": lane["review_prompt_hash"],
                "reviewer_id": f"fixture-{lane_id}",
                "reviewer_model_version": "fixture/v1",
                "reviewer_type": "fixture",
                "rubric_hash": lane["review_prompt_hash"],
                "rubric_version": lane["rubric_version"],
                "schema_version": "prompt-quality-blind-review-result/v1",
                "votes": votes,
            }
            (review_dir / f"{lane_id}-result.json").write_bytes(canonical_json_bytes(result))
        review_path = review_dir / "review.json"
        aggregate_review(
            review_dir,
            review_path,
            experiment={"target_qualitative_dimensions": targets, "guard_qualitative_dimensions": guards},
            policy={},
        )
        return review_path

    def promotion_inputs(self, comparison):
        comparison_path = self.temporary / "comparison.json"
        comparison_path.write_bytes(canonical_json_bytes(comparison))
        review_path = self.bound_review(comparison)
        verification_path = valid_verification(
            comparison, self.temporary, comparison_path, review_path
        )
        return comparison_path, review_path, verification_path

    def test_behavior_boundary_two_fewer_defects_is_inclusive(self):
        comparison = self.compare(after_patch={"identity": {"defect_count": 8}})
        self.assertEqual(
            comparison["automatic_verdict"],
            "pass",
            comparison["hard_gate_failures"],
        )
        self.assertEqual(comparison["target_metric"]["signed_improvement"], 2)

    def test_confirmation_holdout_discovery_rejects_malformed_prior_records(self):
        isolated_root = self.temporary / "holdout-root"
        records_path = isolated_root / "assets" / "results" / "prompt_quality_loop" / "prior" / "records.jsonl"
        records_path.parent.mkdir(parents=True)
        records_path.write_text('{"cohort":"control"}\n', encoding="utf-8")
        with patch.object(confirmation, "ROOT", isolated_root):
            with self.assertRaises(WorkflowValidationError) as caught:
                confirmation._existing_seeds()
        self.assertEqual(caught.exception.code, "invalid_prior_cohort_record")

    def test_behavior_boundary_ten_percent_is_inclusive_but_just_below_rejects(self):
        at_boundary = self.compare(after_patch={"identity": {"defect_count": 9}})
        self.assertEqual(at_boundary["automatic_verdict"], "pass")
        shutil.rmtree(self.temporary / "before")
        shutil.rmtree(self.temporary / "after")
        below = self.compare(after_patch={"identity": {"defect_count": 9.000001}})
        self.assertEqual(below["automatic_verdict"], "reject")

    def test_diversity_five_percent_boundary_is_inclusive(self):
        comparison = self.compare(
            after_patch={"diversity": {"template_entropy": 105}},
            experiment_patch={"target_metric": "diversity.template_entropy", "guard_metrics": []},
        )
        self.assertEqual(comparison["automatic_verdict"], "pass")

    def test_diversity_zero_improvement_rejects_and_preserves_target_direction(self):
        comparison = self.compare(
            experiment_patch={
                "target_metric": "diversity.template_entropy",
                "guard_metrics": [],
            },
        )
        self.assertEqual(comparison["automatic_verdict"], "reject")
        self.assertFalse(comparison["target_metric"]["passed"])
        self.assertEqual(comparison["target_metric"]["direction"], "increase")

    def test_guard_regression_two_points_is_inclusive_but_more_rejects(self):
        boundary = self.compare(after_patch={"identity": {"defect_count": 8, "single_female_rate": 0.98}})
        self.assertEqual(boundary["automatic_verdict"], "pass")
        shutil.rmtree(self.temporary / "before")
        shutil.rmtree(self.temporary / "after")
        over = self.compare(after_patch={"identity": {"defect_count": 8, "single_female_rate": 0.979999}})
        self.assertEqual(over["automatic_verdict"], "reject")

    def test_unregistered_guard_metric_fails_closed(self):
        before = self.write_run("before")
        after = self.write_run("after", {"identity": {"defect_count": 8}})
        experiment = {**self.experiment, "guard_metrics": ["identity.unregistered_count"]}

        with self.assertRaises(WorkflowValidationError) as caught:
            compare_runs(before, after, policy=self.policy, experiment=experiment)
        self.assertEqual(caught.exception.code, "missing_metric")

    def test_hard_gate_failure_overrides_diversity_improvement(self):
        comparison = self.compare(
            after_patch={"identity": {"hard_defect_count": 1}, "diversity": {"template_entropy": 120}},
            experiment_patch={"target_metric": "diversity.template_entropy", "guard_metrics": []},
        )
        self.assertTrue(comparison["target_metric"]["passed"])
        self.assertEqual(comparison["automatic_verdict"], "reject")
        self.assertIn("identity.hard_defect_count", {item["metric"] for item in comparison["hard_gate_failures"]})

    def test_duplicate_and_fallback_regression_each_reject(self):
        for patch in (
            {"diversity": {"exact_duplicate_rate": 0.01}},
            {"runtime": {"fallback_rate": 0.01}},
        ):
            with self.subTest(patch=patch):
                comparison = self.compare(after_patch=deep_update({"identity": {"defect_count": 8}}, patch))
                self.assertEqual(comparison["automatic_verdict"], "reject")
                shutil.rmtree(self.temporary / "before")
                shutil.rmtree(self.temporary / "after")

    def test_context_size_ratio_boundaries(self):
        cases = (
            ({"runtime": {"context_bytes_p95": 110.0, "context_bytes_max": 125.0}}, "pass"),
            ({"runtime": {"context_bytes_p95": 110.001}}, "reject"),
            ({"runtime": {"context_bytes_max": 125.001}}, "reject"),
        )
        for patch, expected in cases:
            with self.subTest(patch=patch):
                comparison = self.compare(after_patch=deep_update({"identity": {"defect_count": 8}}, patch))
                self.assertEqual(comparison["automatic_verdict"], expected)
                shutil.rmtree(self.temporary / "before")
                shutil.rmtree(self.temporary / "after")

    def test_defect_count_guard_uses_explicit_decrease_direction(self):
        before = self.write_run(
            "before",
            {"naturalness": {"repeated_ngram_count": 7}},
        )
        after = self.write_run(
            "after",
            {
                "identity": {"defect_count": 8},
                "naturalness": {"repeated_ngram_count": 8},
            },
        )
        policy = copy.deepcopy(self.policy)
        policy["metrics"]["naturalness.repeated_ngram_count"] = {"direction": "decrease"}
        experiment = {
            **self.experiment,
            "guard_metrics": ["naturalness.repeated_ngram_count"],
        }

        comparison = compare_runs(before, after, policy=policy, experiment=experiment)
        guard = comparison["guard_metrics"][0]
        self.assertEqual(guard["regression"], 1)
        self.assertFalse(guard["passed"])
        self.assertEqual(comparison["automatic_verdict"], "reject")

    def test_context_size_guard_metrics_use_ratio_contract_not_generic_rate_threshold(self):
        experiment = {
            "guard_metrics": [
                "identity.single_female_rate",
                "runtime.context_bytes_p95",
                "runtime.context_bytes_max",
            ]
        }
        cases = (
            ({"runtime": {"context_bytes_p95": 90.0, "context_bytes_max": 90.0}}, "pass"),
            ({"runtime": {"context_bytes_p95": 110.0, "context_bytes_max": 125.0}}, "pass"),
            ({"runtime": {"context_bytes_p95": 110.001}}, "reject"),
            ({"runtime": {"context_bytes_max": 125.001}}, "reject"),
        )
        for patch, expected in cases:
            with self.subTest(patch=patch):
                comparison = self.compare(
                    after_patch=deep_update({"identity": {"defect_count": 8}}, patch),
                    experiment_patch=experiment,
                )
                self.assertEqual(comparison["automatic_verdict"], expected)
                shutil.rmtree(self.temporary / "before")
                shutil.rmtree(self.temporary / "after")

    def test_seed_cohort_and_workflow_hash_drift_are_rejected(self):
        before = self.write_run("before")
        after = self.write_run("after", {"identity": {"defect_count": 8}}, seeds=list(range(79)) + [999])
        with self.assertRaises(WorkflowValidationError) as caught:
            compare_runs(before, after, policy=self.policy, experiment=self.experiment)
        self.assertEqual(caught.exception.code, "cohort_mismatch")

        shutil.rmtree(before)
        shutil.rmtree(after)
        before = self.write_run("before")
        after = self.write_run("after", {"identity": {"defect_count": 8}}, workflow_hash="b" * 64)
        with self.assertRaises(WorkflowValidationError) as caught:
            compare_runs(before, after, policy=self.policy, experiment=self.experiment)
        self.assertEqual(caught.exception.code, "comparison_contract_mismatch")

    def test_control_scope_resolves_external_consistency_rules(self):
        from tools.analyze_prompt_quality import load_policy

        policy_path = ROOT / "vocab" / "data" / "prompt_quality_policy.json"
        policy_version = json.loads(policy_path.read_text(encoding="utf-8"))["policy_version"]
        scoped_policy = load_policy(policy_path)
        scoped_policy["review"] = dict(scoped_policy["review"])
        scoped_policy["review"].pop("schema_version", None)

        def write_scoped_run(name, conflicting):
            run_dir = self.temporary / name
            run_dir.mkdir()
            metrics = {
                "analyzer_version": "prompt-quality-analyzer/v1",
                "policy_version": policy_version,
            }
            (run_dir / "metrics.json").write_bytes(canonical_json_bytes(metrics))
            manifest = {
                "cohort_hash": "c" * 64,
                "workflow_hash": "w" * 64,
                "effective_workflow_hash": "e" * 64,
                "profile_hash": "p" * 64,
            }
            (run_dir / "run-manifest.json").write_bytes(canonical_json_bytes(manifest))
            records = []
            for seed in range(80):
                prompt = (
                    "A girl waits in a station at night during the morning rush."
                    if conflicting and seed < 4
                    else (
                        "A girl waits in a station at night during the late evening shift."
                        if seed < 4
                        else "A girl waits in a station at night during the late shift."
                    )
                )
                context = {
                    "subj": "1girl",
                    "loc": "station",
                    "action": "waiting",
                    "costume": "coat",
                    "extras": {"character_id": "fixture-girl"},
                    "warnings": [],
                }
                records.append({
                    "base_workflow_hash": "b" * 64,
                    "cleaned_prompt": prompt,
                    "cohort": "control" if seed < 64 else "exploration",
                    "context": context,
                    "execution_trace": [{"node_type": "ContextLocationExpander"}],
                    "final_context": context,
                    "resolved_seeds": {"8:seed": seed},
                    "run_seed": seed,
                })
            (run_dir / "records.jsonl").write_bytes(
                b"".join(canonical_json_bytes(record) for record in records)
            )
            return run_dir

        before = write_scoped_run("before", conflicting=True)
        after = write_scoped_run("after", conflicting=False)
        comparison = compare_runs(
            before,
            after,
            policy=scoped_policy,
            experiment={
                "experiment_id": "external-consistency-policy",
                "target_kind": "behavior",
                "target_metric": "consistency.domains.location_action_object.hard_conflict_count",
                "guard_metrics": [],
                "metric_scope": "control64",
                "target_qualitative_dimensions": ["consistency", "naturalness"],
                "guard_qualitative_dimensions": [
                    "protagonist_clarity", "redundancy", "diversity", "image_prompt_suitability",
                ],
            },
        )

        self.assertEqual(comparison["target_metric"]["before"], 4)
        self.assertEqual(comparison["target_metric"]["after"], 0)
        self.assertEqual(
            comparison["automatic_verdict"],
            "pass",
            comparison["hard_gate_failures"],
        )

    def test_promote_check_is_non_mutating_and_requires_review_and_verification(self):
        comparison = self.compare(after_patch={"identity": {"defect_count": 8}})
        source = ROOT / "prompt_renderer.py"
        before_hash = hashlib.sha256(source.read_bytes()).hexdigest()

        comparison_path, review_path, verification_path = self.promotion_inputs(comparison)
        promoted = promote_check(comparison_path, review=review_path, verification=verification_path)
        rejected = promote_check(comparison_path, review={"status": "fail"}, verification=verification_path)

        self.assertEqual(promoted["verdict"], "promote")
        self.assertFalse(promoted["source_mutated"])
        self.assertEqual(rejected["verdict"], "reject")
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before_hash)

    def test_status_only_review_cannot_promote(self):
        comparison = self.compare(after_patch={"identity": {"defect_count": 8}})
        comparison_path, _review_path, verification_path = self.promotion_inputs(comparison)
        result = promote_check(comparison_path, review={"status": "pass"}, verification=verification_path)
        self.assertEqual(result["verdict"], "reject")
        self.assertIn("review_schema_invalid", result["failures"])

    def test_structurally_valid_self_declared_review_cannot_promote_without_raw_artifacts(self):
        comparison = self.compare(after_patch={"identity": {"defect_count": 8}})
        comparison_path, _review_path, verification_path = self.promotion_inputs(comparison)
        result = promote_check(
            comparison_path,
            review=valid_blind_review(comparison),
            verification=verification_path,
        )
        self.assertEqual(result["verdict"], "reject")
        self.assertIn("review_artifact_path_required", result["failures"])

    def test_promotion_rejects_contradictory_verification_and_review_record_drift(self):
        comparison = self.compare(after_patch={"identity": {"defect_count": 8}})
        for status, verdict in (("fail", "pass"), ("pass", "reject")):
            comparison_path, review_path, verification = self.promotion_inputs(comparison)
            payload = json.loads(verification.read_text(encoding="utf-8"))
            payload.update({"status": status, "verdict": verdict})
            verification.write_bytes(canonical_json_bytes(payload))
            result = promote_check(comparison_path, review=review_path, verification=verification)
            self.assertEqual(result["verdict"], "reject")
            self.assertIn("verification_schema_or_status_invalid", result["failures"])

        comparison_path, drifted_review_path, verification_path = self.promotion_inputs(comparison)
        drifted_review = json.loads(drifted_review_path.read_text(encoding="utf-8"))
        drifted_review["reviewed_record_hashes"]["after"] = "9" * 64
        drifted_review_path.write_bytes(canonical_json_bytes(drifted_review))
        result = promote_check(comparison_path, review=drifted_review_path, verification=verification_path)
        self.assertEqual(result["verdict"], "reject")
        self.assertIn("reviewed_record_hashes_mismatch", result["failures"])

    def test_promotion_recomputes_raw_votes_and_requires_exact_two_lane_key(self):
        comparison = self.compare(after_patch={"identity": {"defect_count": 8}})
        comparison_path, review_path, verification_path = self.promotion_inputs(comparison)
        review = json.loads(review_path.read_text(encoding="utf-8"))
        review["dimensions"]["naturalness"]["candidate_better"] = 999
        review_path.write_bytes(canonical_json_bytes(review))
        result = promote_check(comparison_path, review=review_path, verification=verification_path)
        self.assertEqual(result["verdict"], "reject")
        self.assertIn("review_aggregate_recomputation_mismatch", result["failures"])

        comparison_path, review_path, verification_path = self.promotion_inputs(comparison)
        key_path = review_path.parent / "assignment-key.json"
        key = json.loads(key_path.read_text(encoding="utf-8"))
        key["lanes"] = []
        key_path.write_bytes(canonical_json_bytes(key))
        review = json.loads(review_path.read_text(encoding="utf-8"))
        review["assignment_key_hash"] = hashlib.sha256(key_path.read_bytes()).hexdigest()
        review_path.write_bytes(canonical_json_bytes(review))
        result = promote_check(comparison_path, review=review_path, verification=verification_path)
        self.assertEqual(result["verdict"], "reject")
        self.assertIn("review_assignment_lane_set_invalid", result["failures"])

    def test_promotion_rejects_lane_prompt_substitution_even_with_rehashed_artifacts(self):
        comparison = self.compare(after_patch={"identity": {"defect_count": 8}})
        comparison_path, review_path, verification_path = self.promotion_inputs(comparison)
        review_dir = review_path.parent
        lane_path = review_dir / "lane-1.json"
        result_path = review_dir / "lane-1-result.json"
        key_path = review_dir / "assignment-key.json"

        lane = json.loads(lane_path.read_text(encoding="utf-8"))
        lane["pairs"][0]["prompts"]["A"] = "substituted prompt not present in bound records"
        lane_path.write_bytes(canonical_json_bytes(lane))
        lane_hash = hashlib.sha256(lane_path.read_bytes()).hexdigest()
        lane_result = json.loads(result_path.read_text(encoding="utf-8"))
        lane_result["input_hash"] = lane_hash
        result_path.write_bytes(canonical_json_bytes(lane_result))
        result_hash = hashlib.sha256(result_path.read_bytes()).hexdigest()

        key = json.loads(key_path.read_text(encoding="utf-8"))
        next(item for item in key["lanes"] if item["lane_id"] == "lane-1")["lane_artifact_hash"] = lane_hash
        key_path.write_bytes(canonical_json_bytes(key))
        review = json.loads(review_path.read_text(encoding="utf-8"))
        review["assignment_key_hash"] = hashlib.sha256(key_path.read_bytes()).hexdigest()
        review["lane_input_hashes"]["lane-1"] = lane_hash
        review["lane_result_hashes"]["lane-1"] = result_hash
        review_path.write_bytes(canonical_json_bytes(review))

        result = promote_check(comparison_path, review=review_path, verification=verification_path)
        self.assertEqual(result["verdict"], "reject")
        self.assertTrue(any(item.startswith("review_prompt_record_mismatch") for item in result["failures"]))

    def test_verification_requires_raw_complete_inventory_and_untampered_gate_results(self):
        comparison = self.compare(after_patch={"identity": {"defect_count": 8}})
        comparison_path, review_path, verification_path = self.promotion_inputs(comparison)
        verification = json.loads(verification_path.read_text(encoding="utf-8"))
        result = promote_check(comparison_path, review=review_path, verification=verification)
        self.assertEqual(result["verdict"], "reject")
        self.assertIn("verification_artifact_path_required", result["failures"])

        comparison_path, review_path, verification_path = self.promotion_inputs(comparison)
        verification = json.loads(verification_path.read_text(encoding="utf-8"))
        verification["quality_gates"].pop("browser")
        verification_path.write_bytes(canonical_json_bytes(verification))
        result = promote_check(comparison_path, review=review_path, verification=verification_path)
        self.assertEqual(result["verdict"], "reject")
        self.assertIn("verification_gate_inventory_invalid", result["failures"])

        comparison_path, review_path, verification_path = self.promotion_inputs(comparison)
        verification = json.loads(verification_path.read_text(encoding="utf-8"))
        evidence_path = ROOT / verification["quality_gates"]["python_tests"]["evidence_path"]
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        result_path = ROOT / evidence["result_path"]
        gate_result = json.loads(result_path.read_text(encoding="utf-8"))
        gate_result["summary"]["tests_run"] = "many"
        result_path.write_bytes(canonical_json_bytes(gate_result))
        evidence["result_hash"] = hashlib.sha256(result_path.read_bytes()).hexdigest()
        evidence_path.write_bytes(canonical_json_bytes(evidence))
        verification["quality_gates"]["python_tests"]["evidence_hash"] = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        verification_path.write_bytes(canonical_json_bytes(verification))
        result = promote_check(comparison_path, review=review_path, verification=verification_path)
        self.assertEqual(result["verdict"], "reject")
        self.assertIn("verification_result_invalid:python_tests", result["failures"])

        comparison_path, review_path, verification_path = self.promotion_inputs(comparison)
        verification = json.loads(verification_path.read_text(encoding="utf-8"))
        evidence_path = ROOT / verification["quality_gates"]["python_tests"]["evidence_path"]
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        result_path = ROOT / evidence["result_path"]
        gate_result = json.loads(result_path.read_text(encoding="utf-8"))
        gate_result["summary"].update({"tests_run": 504, "tests_passed": 504})
        result_path.write_bytes(canonical_json_bytes(gate_result))
        evidence["result_hash"] = hashlib.sha256(result_path.read_bytes()).hexdigest()
        evidence_path.write_bytes(canonical_json_bytes(evidence))
        verification["quality_gates"]["python_tests"]["evidence_hash"] = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        verification_path.write_bytes(canonical_json_bytes(verification))
        result = promote_check(comparison_path, review=review_path, verification=verification_path)
        self.assertEqual(result["verdict"], "reject")
        self.assertIn("verification_result_invalid:python_tests", result["failures"])

    def test_two_manual_experiments_are_reconstructable(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        for case in fixture["experiments"]:
            with self.subTest(experiment_id=case["experiment_id"]):
                before = self.write_run("before", case["before"])
                after = self.write_run("after", case["after"])
                policy = copy.deepcopy(self.policy)
                experiment = {
                    "experiment_id": case["experiment_id"],
                    "target_metric": case["target_metric"],
                    "guard_metrics": case["guard_metrics"],
                    "target_qualitative_dimensions": ["consistency", "naturalness"],
                    "guard_qualitative_dimensions": [
                        "protagonist_clarity", "redundancy", "diversity", "image_prompt_suitability",
                    ],
                }
                comparison = compare_runs(before, after, policy=policy, experiment=experiment)
                comparison_path, review_path, verification_path = self.promotion_inputs(comparison)
                verdict = promote_check(comparison_path, review=review_path, verification=verification_path)
                self.assertEqual(comparison["automatic_verdict"], case["expected_automatic_verdict"])
                self.assertEqual(verdict["verdict"], case["expected_promotion_verdict"])
                self.assertRegex(case["source_tree_hash"], r"^[0-9a-f]{64}$")
                self.assertRegex(case["candidate_patch_hash"], r"^[0-9a-f]{64}$")
                self.assertEqual(
                    case["source_tree_hash"],
                    hashlib.sha256(case["source_snapshot"].encode("utf-8")).hexdigest(),
                )
                self.assertEqual(
                    case["candidate_patch_hash"],
                    hashlib.sha256(case["candidate_patch"].encode("utf-8")).hexdigest(),
                )
                shutil.rmtree(before)
                shutil.rmtree(after)


class TestPromptQualityExperimentState(unittest.TestCase):
    def setUp(self):
        result_root = ROOT / "assets" / "results"
        result_root.mkdir(parents=True, exist_ok=True)
        self.artifact_root = Path(tempfile.mkdtemp(prefix="prompt-quality-state-", dir=result_root))
        self.experiment_dir = self.artifact_root / "experiment"
        self.addCleanup(lambda: shutil.rmtree(self.artifact_root, ignore_errors=True))
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))["experiments"][0]

    @staticmethod
    def digest(label):
        return hashlib.sha256(label.encode("utf-8")).hexdigest()

    def hypothesis_payload(self, case=None):
        selected = case or self.fixture
        return {
            "hypothesis": selected["hypothesis"],
            "target_metric": selected["target_metric"],
            "guard_metrics": selected["guard_metrics"],
            "owned_files": selected["owned_files"],
            "policy_version": "prompt-quality-policy/v1",
            "cohort_version": "prompt-quality-control/v1",
            "source_tree_hash": selected["source_tree_hash"],
        }

    def transition_payload(self, state, case=None):
        selected = case or self.fixture
        patch_hash = selected["candidate_patch_hash"]
        artifact_content = f"{selected['experiment_id']}:{state}:records".encode("utf-8")
        artifact_path = self.artifact_root / "published" / state.lower() / "records.jsonl"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(artifact_content)
        artifacts = {"records.jsonl": hashlib.sha256(artifact_content).hexdigest()}
        artifact_paths = {"records.jsonl": artifact_path.relative_to(self.artifact_root).as_posix()}
        shared = {
            "workflow_hash": self.digest("workflow"),
            "policy_hash": self.digest("policy"),
            "runner_hash": self.digest("runner"),
            "analyzer_hash": self.digest("analyzer"),
            "cohort_hash": self.digest("cohort"),
        }
        payloads = {
            "BASELINE_READY": {**shared, "baseline_source_tree_hash": selected["source_tree_hash"], "artifact_hashes": artifacts, "artifact_paths": artifact_paths},
            "CANDIDATE_SNAPSHOT_LOCKED": {"candidate_source_tree_hash": self.digest("candidate-source"), "candidate_patch_hash": patch_hash},
            "GENERATED": {"candidate_patch_hash": patch_hash, "artifact_hashes": artifacts, "artifact_paths": artifact_paths},
            "ANALYZED": {"candidate_patch_hash": patch_hash, "analyzer_hash": shared["analyzer_hash"], "policy_hash": shared["policy_hash"], "artifact_hashes": artifacts, "artifact_paths": artifact_paths},
            "COMPARED": {"candidate_patch_hash": patch_hash, "workflow_hash": shared["workflow_hash"], "policy_hash": shared["policy_hash"], "analyzer_hash": shared["analyzer_hash"], "cohort_hash": shared["cohort_hash"], "artifact_hashes": artifacts, "artifact_paths": artifact_paths},
            "REVIEWED": {"candidate_patch_hash": patch_hash, "review_hash": self.digest("review")},
            "VERIFIED": {"candidate_patch_hash": patch_hash, "verification_hash": self.digest("verification")},
            "PROMOTED": {"candidate_patch_hash": patch_hash, "verdict_hash": self.digest("promote"), "artifact_hashes": artifacts, "artifact_paths": artifact_paths},
            "REJECTED": {"candidate_patch_hash": patch_hash, "verdict_hash": self.digest("reject"), "artifact_hashes": artifacts, "artifact_paths": artifact_paths},
        }
        return payloads[state]

    def commit(self, sequence, state, payload=None):
        return commit_transition(
            self.experiment_dir,
            f"{sequence:04d}-{state.lower()}",
            state,
            payload if payload is not None else self.transition_payload(state),
            artifact_root=self.artifact_root,
        )

    def lock_hypothesis(self):
        return self.commit(1, "HYPOTHESIS_LOCKED", self.hypothesis_payload())

    def advance_to_candidate_snapshot(self):
        self.lock_hypothesis()
        self.commit(2, "BASELINE_READY")
        self.commit(3, "CANDIDATE_SNAPSHOT_LOCKED")

    def advance_to_compared(self):
        self.advance_to_candidate_snapshot()
        self.commit(4, "GENERATED")
        self.commit(5, "ANALYZED")
        self.commit(6, "COMPARED")

    def test_hypothesis_lock_requires_one_target_and_all_immutable_fields(self):
        incomplete = self.hypothesis_payload()
        incomplete.pop("target_metric")
        with self.assertRaises(WorkflowValidationError) as caught:
            self.commit(1, "HYPOTHESIS_LOCKED", incomplete)
        self.assertEqual(caught.exception.code, "incomplete_hypothesis_lock")

        invalid = self.hypothesis_payload()
        invalid["target_metric"] = ["identity.a", "identity.b"]
        with self.assertRaises(WorkflowValidationError) as caught:
            self.commit(1, "HYPOTHESIS_LOCKED", invalid)
        self.assertEqual(caught.exception.code, "invalid_target_metric")

    def test_locked_hypothesis_is_immutable(self):
        self.lock_hypothesis()
        payload = self.transition_payload("BASELINE_READY")
        payload["target_metric"] = "diversity.template_entropy"
        with self.assertRaises(WorkflowValidationError) as caught:
            self.commit(2, "BASELINE_READY", payload)
        self.assertEqual(caught.exception.code, "immutable_hypothesis_changed")

    def test_transition_requires_reconstructability_hashes(self):
        self.lock_hypothesis()
        with self.assertRaises(WorkflowValidationError) as caught:
            self.commit(2, "BASELINE_READY", {"baseline_source_tree_hash": self.fixture["source_tree_hash"]})
        self.assertEqual(caught.exception.code, "missing_transition_hashes")

    def test_candidate_patch_drift_aborts_progress(self):
        self.advance_to_candidate_snapshot()
        payload = self.transition_payload("GENERATED")
        payload["candidate_patch_hash"] = self.digest("drifted-patch")
        with self.assertRaises(WorkflowValidationError) as caught:
            self.commit(4, "GENERATED", payload)
        self.assertEqual(caught.exception.code, "candidate_patch_drift")

    def test_transition_id_is_idempotent_only_for_identical_payload(self):
        first = self.lock_hypothesis()
        replay = self.lock_hypothesis()
        self.assertEqual(first, replay)

        changed = self.hypothesis_payload()
        changed["hypothesis"] = "different"
        with self.assertRaises(WorkflowValidationError) as caught:
            self.commit(1, "HYPOTHESIS_LOCKED", changed)
        self.assertEqual(caught.exception.code, "transition_id_conflict")

    def test_writer_lock_and_write_scope_fail_closed(self):
        with experiment_writer_lock(self.experiment_dir, "outer"):
            with self.assertRaises(WorkflowValidationError) as caught:
                self.lock_hypothesis()
            self.assertEqual(caught.exception.code, "experiment_locked")
        with self.assertRaises(WorkflowValidationError) as caught:
            commit_transition(
                self.artifact_root.parent / "outside",
                "0001-lock",
                "HYPOTHESIS_LOCKED",
                self.hypothesis_payload(),
                artifact_root=self.artifact_root,
            )
        self.assertEqual(caught.exception.code, "write_scope_violation")

    def test_recovery_quarantines_pre_publish_temporary_files_and_aborts(self):
        self.lock_hypothesis()
        staging = self.experiment_dir / ".staging"
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "interrupted.tmp").write_bytes(b"partial")

        result = recover_experiment(self.experiment_dir, artifact_root=self.artifact_root)
        records = load_state_records(self.experiment_dir)
        self.assertEqual(result["recovery"]["status"], "quarantined")
        self.assertEqual(records[-1]["state"], "ABORTED")
        self.assertFalse((staging / "interrupted.tmp").exists())
        self.assertTrue(list((self.experiment_dir / "recovery").rglob("recovery.json")))

    def test_recovery_completes_post_publish_state_commit_idempotently(self):
        self.lock_hypothesis()
        payload = self.transition_payload("BASELINE_READY")

        first = recover_experiment(
            self.experiment_dir,
            artifact_root=self.artifact_root,
            transition_id="recovered-baseline",
            next_state="BASELINE_READY",
            payload=payload,
        )
        second = recover_experiment(
            self.experiment_dir,
            artifact_root=self.artifact_root,
            transition_id="recovered-baseline",
            next_state="BASELINE_READY",
            payload=payload,
        )
        self.assertEqual(first["state_record"], second["state_record"])
        self.assertEqual(load_state_records(self.experiment_dir)[-1]["state"], "BASELINE_READY")

    def test_recovery_rejects_missing_or_content_drifted_published_artifacts(self):
        self.lock_hypothesis()
        payload = self.transition_payload("BASELINE_READY")
        published = self.artifact_root / payload["artifact_paths"]["records.jsonl"]
        published.unlink()
        with self.assertRaises(WorkflowValidationError) as missing:
            recover_experiment(
                self.experiment_dir,
                artifact_root=self.artifact_root,
                transition_id="missing-baseline",
                next_state="BASELINE_READY",
                payload=payload,
            )
        self.assertEqual(missing.exception.code, "artifact_missing")

        published.parent.mkdir(parents=True, exist_ok=True)
        published.write_bytes(b"drifted")
        with self.assertRaises(WorkflowValidationError) as drifted:
            recover_experiment(
                self.experiment_dir,
                artifact_root=self.artifact_root,
                transition_id="drifted-baseline",
                next_state="BASELINE_READY",
                payload=payload,
            )
        self.assertEqual(drifted.exception.code, "artifact_hash_mismatch")

    def test_hash_chain_is_append_only_and_corruption_gap_or_hash_drift_fail(self):
        self.advance_to_candidate_snapshot()
        records = load_state_records(self.experiment_dir)
        self.assertEqual([item["sequence"] for item in records], [1, 2, 3])
        self.assertIsNone(records[0]["previous_record_hash"])
        self.assertEqual(records[1]["previous_record_hash"], records[0]["record_hash"])
        self.assertEqual(records[2]["previous_record_hash"], records[1]["record_hash"])

        first_path = sorted((self.experiment_dir / "state").glob("*.json"))[0]
        original = first_path.read_bytes()
        first_path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(WorkflowValidationError) as caught:
            load_state_records(self.experiment_dir)
        self.assertEqual(caught.exception.code, "corrupt_state_record")
        first_path.write_bytes(original)

        first = json.loads(original)
        first["payload"]["hypothesis"] = "tampered"
        first_path.write_bytes(canonical_json_bytes(first))
        with self.assertRaises(WorkflowValidationError) as caught:
            load_state_records(self.experiment_dir)
        self.assertEqual(caught.exception.code, "state_hash_mismatch")
        first_path.write_bytes(original)

        second_path = sorted((self.experiment_dir / "state").glob("*.json"))[1]
        second_path.unlink()
        with self.assertRaises(WorkflowValidationError) as caught:
            load_state_records(self.experiment_dir)
        self.assertEqual(caught.exception.code, "state_sequence_gap")

    def test_rejected_snapshot_cannot_become_baseline_and_promotion_requires_review_verification(self):
        self.advance_to_compared()
        self.commit(7, "REJECTED")
        with self.assertRaises(WorkflowValidationError) as caught:
            self.commit(8, "BASELINE_READY", self.transition_payload("BASELINE_READY"))
        self.assertEqual(caught.exception.code, "invalid_state_transition")

        other = self.artifact_root / "unverified"
        self.experiment_dir = other
        self.advance_to_compared()
        with self.assertRaises(WorkflowValidationError) as caught:
            self.commit(7, "PROMOTED", self.transition_payload("PROMOTED"))
        self.assertEqual(caught.exception.code, "invalid_state_transition")

    def test_two_manual_experiment_state_sequences_are_reconstructable(self):
        cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["experiments"]
        for case_index, case in enumerate(cases, 1):
            with self.subTest(experiment_id=case["experiment_id"]):
                self.experiment_dir = self.artifact_root / case["experiment_id"]
                self.fixture = case
                self.advance_to_compared()
                if case["expected_promotion_verdict"] == "promote":
                    self.commit(7, "REVIEWED")
                    self.commit(8, "VERIFIED")
                    self.commit(9, "PROMOTED")
                else:
                    self.commit(7, "REJECTED")
                records = load_state_records(self.experiment_dir)
                expected_state = {"promote": "PROMOTED", "reject": "REJECTED"}[
                    case["expected_promotion_verdict"]
                ]
                self.assertEqual(records[-1]["state"], expected_state)
                self.assertEqual(records[0]["payload"]["source_tree_hash"], case["source_tree_hash"])
                self.assertTrue(all(item["record_hash"] for item in records))


if __name__ == "__main__":
    unittest.main()
