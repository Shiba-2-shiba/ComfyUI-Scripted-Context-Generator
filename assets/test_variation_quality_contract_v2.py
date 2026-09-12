"""Unit tests for prospective evidence bindings; these files are not run receipts."""
from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.prompt_quality_loop import build_cohort
from tools.variation_quality_contract import _hash_path, _hash_value, validate_variation_quality_contract
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


class TestProspectiveQualityContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.snapshot = self.root / "coverage"
        self.snapshot.mkdir()
        self.catalog = {"subjects": [{"id": f"s{i:02}"} for i in range(15)],
                        "locations": [{"id": f"l{i:02}"} for i in range(19)]}
        ids = {key: [row["id"] for row in rows] for key, rows in self.catalog.items()}
        cohort = build_cohort(9472026, "v150-i4q2", list(range(64)), 80)
        self.write("iteration.json", {})
        certificate = {"status": "pass", "verified_location_count": 19,
                       "verified_subject_count": 15, "fixed_seed_count": 80,
                       "extra_seed_count": 0, "schedule_sha256": "s" * 64,
                       "witness_matrix_sha256": "w" * 64, "cohort_hash": cohort["cohort_hash"],
                       "coverage_is_quality_evidence": False, "promotion_ready": False}
        certificate["verification_sha256"] = _hash_value(certificate)
        self.schedule = {"schema_version": "variation-prompt-final-coverage-schedule/v2",
                         "schedule_sha256": "s" * 64, "witness_matrix_sha256": "w" * 64,
                         "cohort": cohort, "run_contract": {}, "effective_catalog_sha256": _hash_value(self.catalog),
                         "expected_subjects": ids["subjects"], "expected_locations": ids["locations"]}
        self.write("schedule.json", self.schedule)
        self.plan = {"baseline_prompt_mode": "active", "inputs": {"candidate_iteration": {"path": "iteration.json", "sha256": _hash_path(self.root / "iteration.json")},
                                "prompt_schedule": {"path": "schedule.json", "sha256": _hash_path(self.root / "schedule.json")}},
                     "quality_contract_sha256": None, "effective_catalog_sha256": _hash_value(self.catalog)}
        self.write("coverage/snapshot-plan.json", self.plan)
        self.manifest = {"state": "SNAPSHOT_READY", "prompt_generation_allowed": True,
                         "candidate_source_tree_sha256": "a" * 64,
                         "candidate_snapshot_content_sha256": "b" * 64,
                         "candidate_ids": ids, "quality_contract_sha256": None,
                         "prompt_schedule_sha256": self.schedule["schedule_sha256"],
                         "prompt_schedule_verification": certificate}
        self.write("coverage/snapshot-manifest.json", self.manifest)
        self.contract = {"schema_version": "variation-nonselected-quality-contract/v2", "contract_id": "unit-only",
                         "coverage_snapshot_manifest_path": "coverage/snapshot-manifest.json",
                         "coverage_snapshot_manifest_sha256": _hash_path(self.snapshot / "snapshot-manifest.json"),
                         "coverage_snapshot_content_sha256": "b" * 64,
                         "coverage_schedule_path": "schedule.json",
                         "coverage_schedule_sha256": _hash_path(self.root / "schedule.json"),
                         "candidate_iteration_path": "iteration.json", "candidate_iteration_sha256": _hash_path(self.root / "iteration.json"),
                         "effective_catalog_sha256": _hash_value(self.catalog), "candidate_source_tree_sha256": "a" * 64,
                         "candidate_ids": ids, "cohort": cohort, "run_contract": {},
                         "coverage_eligibility": {"candidate_action_pool_locations": 19, "candidate_locations": 19,
                             "candidate_subjects": 15, "extra_seed_count": 0, "fixed_seed_count": 80,
                             "prompt_schedule_sha256": "s" * 64, "witness_matrix_sha256": "w" * 64,
                             "certificate_verification_sha256": certificate["verification_sha256"], "status": "pass"},
                         "surface": {"baseline_rows": 80, "candidate_rows": 80, "kind": "default_fixed_64_16",
                                     "prompt_selection": "default_unselected", "uses_output_metrics_for_selection": False},
                         "authority": {"coverage_is_quality_evidence": False, "quality_evidence": True, "promotion_ready": False}}
        self.rehash()
        self.validation = self.enterContext(patch("tools.materialize_variation_candidate_snapshot.validate_snapshot_manifest", return_value={"status": "pass"}))
        self.enterContext(patch("tools.variation_quality_contract.load_candidate_catalog", return_value=self.catalog))

    def write(self, relative, value):
        (self.root / relative).write_bytes(canonical_json_bytes(value))

    def rehash(self):
        self.contract.pop("contract_sha256", None)
        self.contract["contract_sha256"] = _hash_value(self.contract)

    def validate(self):
        return validate_variation_quality_contract(self.contract, repository_root=self.root)

    def test_fresh_binding_requires_real_snapshot_validator(self):
        self.assertEqual(self.validate()["status"], "pass")
        self.validation.assert_called_once_with(self.snapshot, self.manifest, source_root=self.root)

    def test_real_snapshot_replay_failure_propagates(self):
        self.validation.side_effect = WorkflowValidationError("final_coverage_witness_replay_mismatch", "unit replay failure")
        with self.assertRaisesRegex(WorkflowValidationError, "unit replay failure"):
            self.validate()

    def test_rebound_contract_cannot_hide_source_content_or_schedule_drift(self):
        original = copy.deepcopy(self.contract)
        for field in ("candidate_source_tree_sha256", "coverage_snapshot_content_sha256", "coverage_schedule_sha256", "coverage_snapshot_manifest_sha256"):
            with self.subTest(field=field):
                self.contract = copy.deepcopy(original)
                self.contract[field] = "0" * 64
                self.rehash()
                with self.assertRaises(WorkflowValidationError):
                    self.validate()

    def test_coverage_cannot_depend_on_quality_contract(self):
        self.plan["inputs"]["quality_contract"] = {"path": "recursive.json", "sha256": "0" * 64}
        self.write("coverage/snapshot-plan.json", self.plan)
        with self.assertRaises(WorkflowValidationError):
            self.validate()
        self.validation.assert_not_called()

    def test_cohort_and_run_contract_must_match_coverage(self):
        for field, value in (("cohort", build_cohort(1, "different", list(range(64)), 80)), ("run_contract", {"overrides": {"1": {"seed": 9}}})):
            original = copy.deepcopy(self.contract)
            with self.subTest(field=field):
                self.contract[field] = value
                self.rehash()
                with self.assertRaises(WorkflowValidationError):
                    self.validate()
            self.contract = original

    def test_false_coverage_count_and_authority_are_rejected(self):
        for field in ("coverage_eligibility", "authority", "surface"):
            original = copy.deepcopy(self.contract)
            self.contract[field] = {}
            self.rehash()
            with self.subTest(field=field), self.assertRaises(WorkflowValidationError):
                self.validate()
            self.contract = original

    def test_unknown_fields_and_escaping_paths_are_rejected(self):
        self.contract["historical_rejection"] = "pretend"
        self.rehash()
        with self.assertRaises(WorkflowValidationError):
            self.validate()
        self.contract.pop("historical_rejection")
        self.contract["coverage_snapshot_manifest_path"] = "../outside.json"
        self.rehash()
        with self.assertRaises(WorkflowValidationError):
            self.validate()

    def test_synthetic_baseline_is_not_prospective_evidence(self):
        self.plan.pop("baseline_prompt_mode")
        self.write("coverage/snapshot-plan.json", self.plan)
        with self.assertRaises(WorkflowValidationError):
            self.validate()

    def test_comparison_accepts_active_corpus_but_keeps_candidate80(self):
        from tools import compare_variation_prompt_pair as comparison

        self.write("quality-contract.json", self.contract)
        (self.root / "prompts.jsonl").write_text("active\ncorpus\nrows\n", encoding="utf-8")
        quality = self.root / "quality"
        (quality / "candidate-root").mkdir(parents=True)
        (quality / "baseline-root").mkdir()
        (quality / "baseline-root/prompts.jsonl").write_bytes((self.root / "prompts.jsonl").read_bytes())
        (quality / "candidate-root/prompts.jsonl").write_text("candidate\n" * 80, encoding="utf-8")
        manifest = {**self.manifest, "prompt_rows": {"baseline": 3, "candidate": 80},
                    "quality_contract_sha256": self.contract["contract_sha256"], "prompt_schedule_sha256": None}
        plan = {"baseline_prompt_mode": "active", "quality_contract_sha256": self.contract["contract_sha256"],
                "inputs": {"quality_contract": {"path": "quality-contract.json", "sha256": _hash_path(self.root / "quality-contract.json")}}}
        self.write("quality/snapshot-plan.json", plan)
        experiment = {"schema_version": comparison.QUALITY_EXPERIMENT_SCHEMA_VERSION,
                      "quality_contract_sha256": self.contract["contract_sha256"], "comparison_authority": "quality_non_selected",
                      "surface_kind": "default_fixed_64_16", "prompt_selection": "default_unselected", "run_contract": {},
                      "default_candidate_prompts_sha256": _hash_path(quality / "candidate-root/prompts.jsonl")}
        fixed = self.contract["cohort"]
        experiment["cohort"] = {"cohort_hash": fixed["cohort_hash"], "experiment_seed": fixed["experiment_seed"],
                                "iteration_id": fixed["iteration_id"], "control_count": 64, "exploration_count": 16, "samples": 80}
        with patch.object(comparison, "ROOT", self.root), patch.object(comparison, "validate_variation_quality_contract", return_value={"coverage_eligibility": self.contract["coverage_eligibility"]}):
            self.assertIsNotNone(comparison._load_bound_quality_contract(quality, manifest, experiment))
            experiment["cohort"]["cohort_hash"] = build_cohort(1, "alternate", list(range(64)), 80)["cohort_hash"]
            with self.assertRaises(WorkflowValidationError):
                comparison._load_bound_quality_contract(quality, manifest, experiment)
            experiment["cohort"]["cohort_hash"] = fixed["cohort_hash"]
            manifest["prompt_rows"]["candidate"] = 79
            with self.assertRaises(WorkflowValidationError):
                comparison._load_bound_quality_contract(quality, manifest, experiment)

    def test_coherent_alternate_seed_membership_is_rejected(self):
        from tools.compare_variation_prompt_pair import _validate_quality_cohort_records

        fixed = self.contract["cohort"]
        records = [{"run_seed": seed, "cohort": name} for name in ("control", "exploration") for seed in fixed[name + "_seeds"]]
        _validate_quality_cohort_records(self.contract, records, fixed["cohort_hash"])
        alternate = build_cohort(1, "alternate", list(range(64)), 80)
        wrong = [{"run_seed": seed, "cohort": name} for name in ("control", "exploration") for seed in alternate[name + "_seeds"]]
        for cohort_hash in (fixed["cohort_hash"], alternate["cohort_hash"]):
            with self.subTest(cohort_hash=cohort_hash), self.assertRaises(WorkflowValidationError):
                _validate_quality_cohort_records(self.contract, wrong, cohort_hash)

    def test_same_source_valid_run_requires_the_snapshot_prompt_corpus(self):
        from tools.analyze_prompt_quality import analyze_records, load_policy
        from tools.compare_variation_prompt_pair import REQUIRED_RUN_ARTIFACTS, _validate_run
        from tools.prompt_quality_loop import build_source_manifest

        source, run = self.root / "source", self.root / "run"
        source.mkdir()
        run.mkdir()
        corpus = source / "prompts.jsonl"
        corpus.write_bytes(b"unselected corpus\n")
        source_manifest = build_source_manifest(source)
        policy = load_policy(Path(__file__).resolve().parents[1] / "vocab/data/prompt_quality_policy.json")
        records = [{"run_seed": i, "cohort": "control" if i < 64 else "exploration",
                    "cleaned_prompt": f"a girl reviews route notes at a station number {i}", "final_context": {}} for i in range(80)]
        (run / "records.jsonl").write_bytes(b"".join(canonical_json_bytes(row) for row in records))
        analyzed = analyze_records(records, policy)
        for name, value in (("metrics.json", analyzed["metrics"]), ("issues.json", analyzed["issues"]),
                            ("source-manifest.json", source_manifest), ("telemetry.json", {})):
            self.write("run/" + name, value)
        manifest = {"source_tree_hash": source_manifest["source_tree_hash"], "prompt_corpus_sha256": _hash_path(corpus),
                    "replay_evidence": {"checked": 80, "mismatch_count": 0, "status": "pass"},
                    "artifact_hashes": {name: _hash_path(run / name) for name in REQUIRED_RUN_ARTIFACTS}}
        self.write("run/run-manifest.json", manifest)
        args = {"expected_source_hash": source_manifest["source_tree_hash"], "snapshot_source_root": source, "policy": policy}
        _validate_run(run, **args, require_prompt_corpus=True)
        corpus.write_bytes(b"scheduled corpus\n")
        self.assertEqual(build_source_manifest(source), source_manifest)
        _validate_run(run, **args)  # Legacy comparisons retain their original contract.
        with self.assertRaises(WorkflowValidationError):
            _validate_run(run, **args, require_prompt_corpus=True)
        manifest.pop("prompt_corpus_sha256")
        self.write("run/run-manifest.json", manifest)
        with self.assertRaises(WorkflowValidationError):
            _validate_run(run, **args, require_prompt_corpus=True)

    def test_preparation_subprocess_does_not_inherit_active_pythonpath(self):
        from tools.prepare_variation_quality_evaluation import _run
        with patch.dict(os.environ, {"PYTHONPATH": "active-plugin", "PYTHONNOUSERSITE": "0"}), patch(
            "tools.prepare_variation_quality_evaluation.subprocess.run",
        ) as execute:
            execute.return_value.returncode = 0
            _run(self.root, self.root, "unit-command", "test.py")
        env = execute.call_args.kwargs["env"]
        self.assertEqual(env["PYTHONPATH"], str(self.root.resolve()))
        self.assertEqual(env["PYTHONNOUSERSITE"], "1")
        self.assertEqual(env["PYTHONSAFEPATH"], "1")
if __name__ == "__main__":
    unittest.main()
