import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import compare_variation_prompt_pair as comparator
from tools.analyze_prompt_quality import analyze_records, load_policy
from tools.compare_variation_prompt_pair import compare_variation_prompt_pair
from tools.prompt_quality_loop import build_source_manifest
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes, load_profile


def _metrics(*, entropy):
    return {
        "diversity": {"location_signature_entropy": entropy, "exact_unique_ratio": 0.95},
        "naturalness": {
            "punctuation_anomaly_count": 0,
            "repeated_ngram_count": 1,
            "semantic_family_repetition_count": 0,
        },
        "identity": {
            "missing_female_protagonist_count": 0,
            "male_pronoun_drift_count": 0,
            "other_person_solo_conflict_count": 0,
            "duplicate_protagonist_mention_count": 0,
            "person_demographic_descriptor_count": 0,
        },
        "consistency": {"hard_conflict_count": 0},
        "policy": {"policy_issue_count": 0},
        "runtime": {
            "fallback_rate": 0.0,
            "deterministic_replay_mismatch_count": 0,
            "context_json_bytes_p95": 1000,
            "context_json_bytes_max": 1200,
        },
    }


def _write_json(path, value):
    path.write_bytes(canonical_json_bytes(value))


def _write_records(path, records):
    path.write_bytes(b"".join(canonical_json_bytes(record) for record in records))


class TestVariationPromptPair(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.snapshot = self.root / "snapshot"
        self.baseline_run = self.root / "baseline-run"
        self.candidate_run = self.root / "candidate-run"
        self.baseline_source_root = self.snapshot / "baseline-root"
        self.candidate_source_root = self.snapshot / "candidate-root"
        for source_root in (self.baseline_source_root, self.candidate_source_root):
            policy_path = source_root / "vocab" / "data" / "prompt_quality_policy.json"
            policy_path.parent.mkdir(parents=True)
            policy_path.write_bytes(
                (Path(__file__).resolve().parents[1] / "vocab" / "data" / "prompt_quality_policy.json").read_bytes()
            )
            _write_json(source_root / "workflow.json", {"nodes": [], "links": []})
            _write_json(
                source_root / "profile.json",
                {
                    "profile_id": "variation-pair-test",
                    "version": "1",
                    "allowed_node_types": ["ContextSource"],
                    "output_selectors": {"final_context": {"node_id": 1, "slot": 0}},
                },
            )
        self.policy = load_policy(
            self.candidate_source_root / "vocab" / "data" / "prompt_quality_policy.json"
        )
        _write_json(
            self.candidate_source_root / "vocab" / "data" / "action_pools.json",
            {
                "candidate_location_a": [{"text": "candidate action a", "load": "calm"}],
                "candidate_location_b": [{"text": "candidate action b", "load": "active"}],
            },
        )
        baseline_source_hash = build_source_manifest(self.baseline_source_root)["source_tree_hash"]
        candidate_source_hash = build_source_manifest(self.candidate_source_root)["source_tree_hash"]
        self.snapshot_manifest = {
            "state": "SNAPSHOT_READY",
            "prompt_generation_allowed": True,
            "baseline_source_tree_sha256": baseline_source_hash,
            "candidate_source_tree_sha256": candidate_source_hash,
            "candidate_ids": {
                "subjects": ["candidate_subject_a", "candidate_subject_b"],
                "locations": ["candidate_location_a", "candidate_location_b"],
            },
        }
        _write_json(self.snapshot / "snapshot-manifest.json", self.snapshot_manifest)
        workflow_hash = hashlib.sha256(
            canonical_json_bytes({"nodes": [], "links": []})
        ).hexdigest()
        profile_hash = load_profile(self.baseline_source_root / "profile.json").hash
        override_hash = hashlib.sha256(
            canonical_json_bytes({"explicit": {}, "profile": {}})
        ).hexdigest()
        effective_workflow_hash = hashlib.sha256(
            canonical_json_bytes(
                {"base_workflow_hash": workflow_hash, "override_hash": override_hash}
            )
        ).hexdigest()
        self.run_contract = {
            "workflow": "workflow.json",
            "profile": "profile.json",
            "overrides": {},
            "workflow_hash": workflow_hash,
            "profile_hash": profile_hash,
            "override_hash": override_hash,
            "effective_workflow_hash": effective_workflow_hash,
        }
        self.experiment = {
            "schema_version": "prompt-quality-experiment/v1",
            "workflow": "workflow.json",
            "profile": "profile.json",
            "run_contract": self.run_contract,
            "snapshot_manifest_sha256": hashlib.sha256(
                (self.snapshot / "snapshot-manifest.json").read_bytes()
            ).hexdigest(),
            "cohort": {
                "cohort_hash": "cohort-hash",
                "control_count": 64,
                "exploration_count": 16,
                "samples": 80,
            },
        }
        self._write_run(
            self.baseline_run,
            candidate=False,
            source_root=self.baseline_source_root,
            source_hash=baseline_source_hash,
        )
        self._write_run(
            self.candidate_run,
            candidate=True,
            source_root=self.candidate_source_root,
            source_hash=candidate_source_hash,
        )

    def _records(self, *, candidate):
        rows = []
        for seed in range(80):
            cohort = "control" if seed < 64 else "exploration"
            location_index = seed % 2
            location = f"candidate_location_{'a' if location_index == 0 else 'b'}"
            subject = f"candidate_subject_{'a' if location_index == 0 else 'b'}"
            action = f"candidate action {'a' if location_index == 0 else 'b'}"
            context = {
                "loc": location if candidate else "candidate_location_a",
                "extras": {"source_subj_key": subject},
                "history": [
                    {
                        "node": "ContextSceneVariator",
                        "decision": {"action": action, "selected_loc": location},
                    }
                ],
            }
            rows.append(
                {
                    "run_seed": seed,
                    "cohort": cohort,
                    "cleaned_prompt": (
                        f"a girl calmly reviews {'candidate' if candidate else 'incumbent'} route notes "
                        f"beside the quiet station display number {seed}"
                    ),
                    "final_context": context,
                }
            )
        return rows

    def _write_run(self, root, *, candidate, source_root, source_hash):
        root.mkdir(parents=True, exist_ok=True)
        records = self._records(candidate=candidate)
        _write_records(root / "records.jsonl", records)
        recomputed = analyze_records(records, self.policy)
        _write_json(root / "metrics.json", recomputed["metrics"])
        _write_json(root / "issues.json", recomputed["issues"])
        _write_json(root / "source-manifest.json", build_source_manifest(source_root))
        _write_json(root / "telemetry.json", {})
        manifest = {
            "source_tree_hash": source_hash,
            "cohort_hash": "cohort-hash",
            "workflow_hash": self.run_contract["workflow_hash"],
            "effective_workflow_hash": self.run_contract["effective_workflow_hash"],
            "profile_hash": self.run_contract["profile_hash"],
            "override_hash": self.run_contract["override_hash"],
            "replay_evidence": {"checked": 80, "mismatch_count": 0, "status": "pass"},
            "artifact_hashes": {
                name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in comparator.REQUIRED_RUN_ARTIFACTS
            },
        }
        _write_json(root / "run-manifest.json", manifest)

    def _rehash(self, run_dir, name):
        manifest_path = run_dir / "run-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["artifact_hashes"][name] = hashlib.sha256((run_dir / name).read_bytes()).hexdigest()
        _write_json(manifest_path, manifest)

    def _replace_records_and_recompute(self, run_dir, records):
        _write_records(run_dir / "records.jsonl", records)
        recomputed = analyze_records(records, self.policy)
        _write_json(run_dir / "metrics.json", recomputed["metrics"])
        _write_json(run_dir / "issues.json", recomputed["issues"])
        for name in ("records.jsonl", "metrics.json", "issues.json"):
            self._rehash(run_dir, name)

    def _compare(self):
        with patch.object(comparator, "validate_snapshot_manifest", return_value={"status": "pass"}):
            return compare_variation_prompt_pair(
                snapshot_root=self.snapshot,
                baseline_run=self.baseline_run,
                candidate_run=self.candidate_run,
                experiment=self.experiment,
            )

    def test_valid_pair_passes_target_guards_and_candidate_coverage(self):
        report = self._compare()

        self.assertEqual(report["verdict"], "pass")
        self.assertEqual(report["prompt_quality_state"], "COMPARED")
        self.assertFalse(report["promotion_ready"])
        self.assertEqual(comparator.comparison_exit_code(report), 0)
        self.assertEqual(report["record_count"], 80)
        self.assertEqual(report["changed_seed_count"], 80)
        self.assertEqual(report["cohort_hash"], "cohort-hash")
        self.assertEqual(
            report["experiment_sha256"],
            hashlib.sha256(canonical_json_bytes(self.experiment)).hexdigest(),
        )
        self.assertEqual(report["candidate_coverage"]["unseen_subjects"], [])
        self.assertEqual(report["candidate_coverage"]["unseen_locations"], [])
        self.assertEqual(report["candidate_coverage"]["unseen_action_pool_locations"], [])
        self.assertGreater(
            report["metric_comparisons"]["diversity.location_signature_entropy"]["delta"],
            0,
        )
        self.assertEqual(report["failures"], [])

    def test_snapshot_gate_is_required(self):
        manifest = copy.deepcopy(self.snapshot_manifest)
        manifest["state"] = "REJECTED"
        manifest["prompt_generation_allowed"] = False
        _write_json(self.snapshot / "snapshot-manifest.json", manifest)

        with self.assertRaises(WorkflowValidationError) as raised:
            self._compare()

        self.assertEqual(raised.exception.code, "snapshot_prompt_generation_blocked")

    def test_experiment_snapshot_and_cohort_bindings_are_required(self):
        cases = (
            ("snapshot_manifest_sha256", "0" * 64, "variation_experiment_snapshot_mismatch"),
            ("cohort", {**self.experiment["cohort"], "cohort_hash": "wrong"}, "variation_experiment_cohort_mismatch"),
        )
        for field, value, expected in cases:
            with self.subTest(field=field):
                self.setUp()
                self.experiment[field] = value
                with self.assertRaises(WorkflowValidationError) as raised:
                    self._compare()
                self.assertEqual(raised.exception.code, expected)

    def test_run_artifact_hash_and_snapshot_source_hash_are_exact(self):
        (self.candidate_run / "records.jsonl").write_bytes(
            (self.candidate_run / "records.jsonl").read_bytes() + b"\n"
        )
        with self.assertRaises(WorkflowValidationError) as raised:
            self._compare()
        self.assertEqual(raised.exception.code, "run_artifact_hash_mismatch")

        self.setUp()
        manifest_path = self.candidate_run / "run-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["source_tree_hash"] = "d" * 64
        _write_json(manifest_path, manifest)
        with self.assertRaises(WorkflowValidationError) as raised:
            self._compare()
        self.assertEqual(raised.exception.code, "run_snapshot_source_mismatch")

    def test_workflow_profile_and_other_shared_contract_drift_are_rejected(self):
        for field in ("workflow_hash", "profile_hash", "effective_workflow_hash", "override_hash"):
            with self.subTest(field=field):
                self.setUp()
                manifest_path = self.candidate_run / "run-manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest[field] = f"different-{field}"
                _write_json(manifest_path, manifest)
                with self.assertRaises(WorkflowValidationError) as raised:
                    self._compare()
                self.assertEqual(raised.exception.code, "variation_pair_contract_drift")

    def test_same_wrong_run_contract_on_both_sides_is_rejected(self):
        for run_dir in (self.baseline_run, self.candidate_run):
            manifest_path = run_dir / "run-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["workflow_hash"] = "same-wrong-workflow-hash"
            _write_json(manifest_path, manifest)

        with self.assertRaises(WorkflowValidationError) as raised:
            self._compare()

        self.assertEqual(raised.exception.code, "variation_experiment_run_contract_mismatch")

    def test_declared_run_contract_hash_must_match_snapshot_files(self):
        self.experiment["run_contract"]["profile_hash"] = "wrong-profile-hash"

        with self.assertRaises(WorkflowValidationError) as raised:
            self._compare()

        self.assertEqual(raised.exception.code, "variation_experiment_run_contract_mismatch")

    def test_seed_set_and_cohort_labels_must_match_exact_64_plus_16_contract(self):
        records = self._records(candidate=True)
        records[-1]["run_seed"] = 999
        self._replace_records_and_recompute(self.candidate_run, records)
        with self.assertRaises(WorkflowValidationError) as raised:
            self._compare()
        self.assertEqual(raised.exception.code, "variation_pair_seed_mismatch")

        self.setUp()
        records = self._records(candidate=True)
        records[0]["cohort"] = "exploration"
        self._replace_records_and_recompute(self.candidate_run, records)
        with self.assertRaises(WorkflowValidationError) as raised:
            self._compare()
        self.assertEqual(raised.exception.code, "variation_pair_cohort_label_mismatch")

        self.setUp()
        for run_dir, candidate in ((self.baseline_run, False), (self.candidate_run, True)):
            records = self._records(candidate=candidate)
            records[64]["cohort"] = "control"
            self._replace_records_and_recompute(run_dir, records)
        with self.assertRaises(WorkflowValidationError) as raised:
            self._compare()
        self.assertEqual(raised.exception.code, "variation_pair_cohort_label_mismatch")

    def test_replay_evidence_is_a_hard_gate(self):
        manifest_path = self.candidate_run / "run-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["replay_evidence"] = {"checked": 80, "mismatch_count": 1, "status": "fail"}
        _write_json(manifest_path, manifest)

        with self.assertRaises(WorkflowValidationError) as raised:
            self._compare()

        self.assertEqual(raised.exception.code, "run_replay_failed")

    def test_self_rehashed_metrics_tamper_is_rejected_by_record_recomputation(self):
        path = self.candidate_run / "metrics.json"
        metrics = json.loads(path.read_text(encoding="utf-8"))
        metrics["identity"]["missing_female_protagonist_count"] = 999
        _write_json(path, metrics)
        self._rehash(self.candidate_run, "metrics.json")

        with self.assertRaises(WorkflowValidationError) as raised:
            self._compare()

        self.assertEqual(raised.exception.code, "run_metrics_recompute_mismatch")

    def test_self_rehashed_source_manifest_tamper_is_rejected(self):
        path = self.candidate_run / "source-manifest.json"
        source_manifest = json.loads(path.read_text(encoding="utf-8"))
        source_manifest["source_tree_hash"] = "0" * 64
        _write_json(path, source_manifest)
        self._rehash(self.candidate_run, "source-manifest.json")

        with self.assertRaises(WorkflowValidationError) as raised:
            self._compare()

        self.assertEqual(raised.exception.code, "run_source_manifest_mismatch")

    def test_target_entropy_must_improve(self):
        records = self._records(candidate=True)
        for record in records:
            record["final_context"]["loc"] = "candidate_location_a"
        self._replace_records_and_recompute(self.candidate_run, records)

        report = self._compare()

        self.assertIn("target_not_improved:diversity.location_signature_entropy", report["failures"])
        self.assertEqual(report["verdict"], "reject")

    def test_candidate_subject_location_and_action_coverage_sentinels_reject(self):
        records = self._records(candidate=True)
        for record in records:
            record["final_context"] = {
                "loc": "candidate_location_a",
                "extras": {"source_subj_key": "candidate_subject_a"},
                "history": [
                    {"node": "ContextSceneVariator", "decision": {"action": "candidate action a"}}
                ],
            }
        self._replace_records_and_recompute(self.candidate_run, records)

        report = self._compare()

        self.assertIn("candidate_subject_coverage_incomplete", report["failures"])
        self.assertIn("candidate_location_coverage_incomplete", report["failures"])
        self.assertIn("candidate_action_pool_coverage_incomplete", report["failures"])

    def test_demographic_descriptor_is_recomputed_from_records(self):
        records = self._records(candidate=True)
        records[0]["cleaned_prompt"] = (
            "a pale-skinned girl calmly reviews candidate route notes beside the quiet station display"
        )
        self._replace_records_and_recompute(self.candidate_run, records)

        report = self._compare()

        self.assertIn(
            "guard_regressed:identity.person_demographic_descriptor_count",
            report["failures"],
        )

    def test_action_coverage_requires_actual_location_action_pair(self):
        records = self._records(candidate=True)
        for record in records:
            location = record["final_context"]["loc"]
            wrong_action = "candidate action b" if location.endswith("_a") else "candidate action a"
            record["final_context"]["history"][0]["decision"]["action"] = wrong_action
        self._replace_records_and_recompute(self.candidate_run, records)

        report = self._compare()

        self.assertEqual(
            report["candidate_coverage"]["unseen_action_pool_locations"],
            ["candidate_location_a", "candidate_location_b"],
        )
        self.assertIn("candidate_action_pool_coverage_incomplete", report["failures"])

    def test_action_coverage_uses_refreshed_pool_witness_after_location_change(self):
        records = self._records(candidate=True)
        for record in records:
            location = record["final_context"]["loc"]
            expected = "candidate action a" if location.endswith("_a") else "candidate action b"
            decision = record["final_context"]["history"][0]["decision"]
            decision.update(
                {
                    "action": "source action from another location",
                    "action_updated": True,
                    "base_action": expected,
                    "new_action": f"realized {expected}",
                }
            )
        self._replace_records_and_recompute(self.candidate_run, records)

        report = self._compare()

        self.assertEqual(report["candidate_coverage"]["unseen_action_pool_locations"], [])

    def test_refreshed_action_witness_never_falls_back_to_source_action(self):
        self.assertEqual(
            comparator.scene_action_pool_witness(
                {"action_updated": True, "action": "source action", "base_action": "", "new_action": ""}
            ),
            "",
        )
        self.assertEqual(
            comparator.scene_action_pool_witness(
                {"action_updated": False, "action": "source action", "base_action": "wrong fallback"}
            ),
            "source action",
        )
        self.assertEqual(
            comparator.scene_action_pool_witness(
                {"action_updated": True, "base_action": "  pool action  ", "new_action": "rendered"}
            ),
            "pool action",
        )
        self.assertEqual(
            comparator.scene_action_pool_witness(
                {"action_updated": True, "base_action": "", "new_action": "  rendered fallback  "}
            ),
            "",
        )
        for invalid in ("false", 1, None):
            with self.subTest(invalid=invalid):
                with self.assertRaises(WorkflowValidationError) as raised:
                    comparator.scene_action_pool_witness({"action_updated": invalid})
                self.assertEqual(raised.exception.code, "invalid_scene_action_update_flag")

    def test_only_final_scene_decision_can_supply_action_coverage(self):
        records = self._records(candidate=True)
        for record in records:
            record["final_context"]["history"].append(
                {
                    "node": "ContextSceneVariator",
                    "decision": {"selected_loc": "different_location", "action": "candidate action a"},
                }
            )
        self._replace_records_and_recompute(self.candidate_run, records)

        report = self._compare()

        self.assertEqual(
            report["candidate_coverage"]["unseen_action_pool_locations"],
            ["candidate_location_a", "candidate_location_b"],
        )

    def test_comparison_is_deterministic_and_does_not_mutate_inputs(self):
        protected = [path for path in self.root.rglob("*") if path.is_file()]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}

        first = self._compare()
        second = self._compare()

        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        self.assertEqual(after, before)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        body = dict(first)
        comparison_hash = body.pop("comparison_sha256")
        self.assertEqual(comparison_hash, hashlib.sha256(canonical_json_bytes(body)).hexdigest())

    def test_coverage_only_schedule_cannot_override_fixed_reject(self):
        schedule = {
            "schedule_sha256": "scheduled-hash",
            "coverage_is_quality_evidence": False,
            "fixed_verdict": "reject",
            "promotion_ready": False,
            "expected_location_actions": [
                {"location": "candidate_location_a", "action": "candidate action a"},
                {"location": "candidate_location_b", "action": "candidate action b"},
            ],
        }

        with patch.object(comparator, "_load_bound_prompt_schedule", return_value=schedule):
            report = self._compare()

        self.assertEqual(report["coverage_verdict"], "pass")
        self.assertEqual(report["diagnostic_pair_verdict"], "pass")
        self.assertEqual(report["fixed_quality_verdict"], "reject")
        self.assertEqual(report["verdict"], "reject")
        self.assertFalse(report["coverage_is_quality_evidence"])
        self.assertFalse(report["promotion_ready"])
        self.assertEqual(comparator.comparison_exit_code(report), 1)

    def test_nonselected_quality_authority_uses_prior_coverage_as_eligibility(self):
        self.experiment.update(
            {
                "schema_version": "variation-nonselected-quality-experiment/v2",
                "comparison_authority": "quality_non_selected",
                "surface_kind": "default_fixed_64_16",
                "prompt_selection": "default_unselected",
                "metric_scope": "control64",
            }
        )
        contract = {
            "contract_sha256": "quality-contract-hash",
            "coverage_receipt_sha256": "coverage-receipt-hash",
            "guard_remediation_receipt_sha256": "remediation-receipt-hash",
            "_validated_coverage_eligibility": {
                "candidate_action_pool_locations": 19,
                "candidate_locations": 19,
                "candidate_subjects": 15,
                "extra_seed_count": 0,
                "fixed_seed_count": 80,
                "prompt_schedule_sha256": "schedule-hash",
                "status": "pass",
                "witness_matrix_sha256": "matrix-hash",
            },
        }
        incomplete = {
            "subjects_seen": [],
            "locations_seen": [],
            "action_pool_locations_seen": [],
            "unseen_subjects": ["candidate_subject_a"],
            "unseen_locations": ["candidate_location_a"],
            "unseen_action_pool_locations": ["candidate_location_a"],
        }

        with (
            patch.object(comparator, "_load_bound_quality_contract", return_value=contract),
            patch.object(comparator, "candidate_coverage", return_value=incomplete),
        ):
            report = self._compare()

        self.assertEqual(report["schema_version"], "variation-nonselected-quality-comparison/v2")
        self.assertEqual(report["quality_verdict"], "pass")
        self.assertEqual(report["coverage_eligibility_verdict"], "pass")
        self.assertEqual(report["validation_verdict"], "pass")
        self.assertEqual(report["verdict"], "pass")
        self.assertTrue(report["review_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertEqual(len(report["informational_coverage_failures"]), 3)
        self.assertNotIn("candidate_location_coverage_incomplete", report["quality_failures"])
        self.assertEqual(comparator.comparison_exit_code(report), 0)

    def test_v2_quality_experiment_without_bound_contract_fails_closed(self):
        self.experiment.update(
            {
                "schema_version": "variation-nonselected-quality-experiment/v2",
                "comparison_authority": "quality_non_selected",
                "surface_kind": "default_fixed_64_16",
                "prompt_selection": "default_unselected",
                "metric_scope": "control64",
            }
        )

        with self.assertRaises(WorkflowValidationError) as raised:
            self._compare()

        self.assertEqual(raised.exception.code, "variation_quality_contract_required")

    def test_nonselected_quality_guard_failure_returns_authoritative_reject(self):
        self.experiment.update(
            {
                "schema_version": "variation-nonselected-quality-experiment/v2",
                "comparison_authority": "quality_non_selected",
                "surface_kind": "default_fixed_64_16",
                "prompt_selection": "default_unselected",
                "metric_scope": "control64",
            }
        )
        contract = {
            "contract_sha256": "quality-contract-hash",
            "coverage_receipt_sha256": "coverage-receipt-hash",
            "guard_remediation_receipt_sha256": "remediation-receipt-hash",
            "_validated_coverage_eligibility": {
                "candidate_action_pool_locations": 19,
                "candidate_locations": 19,
                "candidate_subjects": 15,
                "extra_seed_count": 0,
                "fixed_seed_count": 80,
                "prompt_schedule_sha256": "schedule-hash",
                "status": "pass",
                "witness_matrix_sha256": "matrix-hash",
            },
        }
        records = self._records(candidate=True)
        for record in records:
            record["final_context"]["loc"] = "candidate_location_a"
            record["final_context"]["history"][0]["decision"]["selected_loc"] = (
                "candidate_location_a"
            )
        self._replace_records_and_recompute(self.candidate_run, records)

        with patch.object(
            comparator, "_load_bound_quality_contract", return_value=contract
        ):
            report = self._compare()

        self.assertEqual(report["quality_verdict"], "reject")
        self.assertEqual(report["validation_verdict"], "reject")
        self.assertEqual(report["verdict"], "reject")
        self.assertFalse(report["review_ready"])
        self.assertEqual(comparator.comparison_exit_code(report), 1)

    def test_control64_metric_scope_excludes_exploration_only_regression(self):
        self.experiment.update(
            {
                "schema_version": "variation-nonselected-quality-experiment/v2",
                "comparison_authority": "quality_non_selected",
                "surface_kind": "default_fixed_64_16",
                "prompt_selection": "default_unselected",
                "metric_scope": "control64",
            }
        )
        contract = {
            "contract_sha256": "quality-contract-hash",
            "coverage_receipt_sha256": "coverage-receipt-hash",
            "guard_remediation_receipt_sha256": "remediation-receipt-hash",
            "_validated_coverage_eligibility": {
                "candidate_action_pool_locations": 19,
                "candidate_locations": 19,
                "candidate_subjects": 15,
                "extra_seed_count": 0,
                "fixed_seed_count": 80,
                "prompt_schedule_sha256": "schedule-hash",
                "status": "pass",
                "witness_matrix_sha256": "matrix-hash",
            },
        }
        records = self._records(candidate=True)
        for record in records[64:]:
            record["cleaned_prompt"] = (
                "a girl keeps saying softly keeps saying calmly keeps saying slowly"
            )
        self._replace_records_and_recompute(self.candidate_run, records)

        with patch.object(
            comparator, "_load_bound_quality_contract", return_value=contract
        ):
            report = self._compare()

        self.assertEqual(report["metric_scope"], "control64")
        self.assertEqual(report["metric_record_count"], 64)
        self.assertEqual(report["quality_verdict"], "pass")
        self.assertEqual(
            report["metric_comparisons"]["naturalness.repeated_ngram_count"]["delta"],
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
