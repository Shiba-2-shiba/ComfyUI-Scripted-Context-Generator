import copy
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from tools import materialize_variation_candidate_snapshot as materializer
from tools.materialize_variation_candidate_snapshot import (
    MUTABLE_CANDIDATE_FILES,
    _manifest_entries,
    build_snapshot_plan,
    materialize_candidate_snapshots,
    validate_snapshot_manifest,
)
from tools.prompt_quality_loop import _source_files
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = ROOT / "assets" / "results"
ITERATION_ROOT = ROOT / "docs" / "variation_expansion" / "experiments" / "v150-candidate-l2-iteration-002"
SCHEDULE_ITERATION_ROOT = ROOT / "docs" / "variation_expansion" / "experiments" / "v150-candidate-shape-iteration-004"
SCHEDULE_PATH = ROOT / "docs" / "variation_expansion" / "experiments" / "v150-candidate-shape-iteration-005" / "coverage-plan.json"
FINAL_SCHEDULE_PATH = ROOT / "docs" / "variation_expansion" / "experiments" / "v150-candidate-shape-iteration-006" / "full-workflow-schedule.json"
QUALITY_CONTRACT_PATH = ROOT / "docs" / "variation_expansion" / "experiments" / "v150-candidate-shape-iteration-008" / "nonselected-quality-contract.json"


def _build_plan():
    return build_snapshot_plan(
        candidate_iteration=ITERATION_ROOT / "candidate-iteration.json",
        scenario_manifest=ITERATION_ROOT / "scenario-manifest.json",
        projection_report=ITERATION_ROOT / "projection-report.json",
        analysis_report=ITERATION_ROOT / "analysis-report.json",
        source_root=ROOT,
    )


def _build_scheduled_plan():
    return build_snapshot_plan(
        candidate_iteration=SCHEDULE_ITERATION_ROOT / "candidate-iteration.json",
        scenario_manifest=SCHEDULE_ITERATION_ROOT / "scenario-manifest.json",
        projection_report=SCHEDULE_ITERATION_ROOT / "projection-report.json",
        analysis_report=SCHEDULE_ITERATION_ROOT / "analysis-report.json",
        prompt_schedule=SCHEDULE_PATH,
        source_root=ROOT,
    )


def _build_final_scheduled_plan():
    return build_snapshot_plan(
        candidate_iteration=SCHEDULE_ITERATION_ROOT / "candidate-iteration.json",
        scenario_manifest=SCHEDULE_ITERATION_ROOT / "scenario-manifest.json",
        projection_report=SCHEDULE_ITERATION_ROOT / "projection-report.json",
        analysis_report=SCHEDULE_ITERATION_ROOT / "analysis-report.json",
        prompt_schedule=FINAL_SCHEDULE_PATH,
        source_root=ROOT,
    )


def _build_quality_plan():
    return build_snapshot_plan(
        candidate_iteration=SCHEDULE_ITERATION_ROOT / "candidate-iteration.json",
        scenario_manifest=SCHEDULE_ITERATION_ROOT / "scenario-manifest.json",
        projection_report=SCHEDULE_ITERATION_ROOT / "projection-report.json",
        analysis_report=SCHEDULE_ITERATION_ROOT / "analysis-report.json",
        quality_contract=QUALITY_CONTRACT_PATH,
        source_root=ROOT,
    )


class TestVariationCandidateSnapshotPlan(unittest.TestCase):
    def test_plan_binds_exact_l2_inputs_and_declared_delta(self):
        plan = _build_plan()

        self.assertEqual(plan["schema_version"], "variation-candidate-snapshot-plan/v1")
        self.assertEqual(plan["snapshot_id"], "v150-candidate-002")
        self.assertEqual(plan["declared_delta"], {
            "subjects": 15,
            "locations": 15,
            "action_pools": 15,
            "actions_per_location": [20],
        })
        self.assertEqual(len(plan["candidate_ids"]["subjects"]), 15)
        self.assertEqual(len(plan["candidate_ids"]["locations"]), 15)
        self.assertEqual(plan["candidate_ids"]["subjects"], sorted(plan["candidate_ids"]["subjects"]))
        self.assertEqual(plan["candidate_ids"]["locations"], sorted(plan["candidate_ids"]["locations"]))
        self.assertEqual(set(plan["mutable_candidate_files"]), set(MUTABLE_CANDIDATE_FILES))

    def test_plan_is_canonical_and_deterministic(self):
        first = _build_plan()
        second = _build_plan()

        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))

    def test_plan_rejects_input_outside_source_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outside = Path(temp_dir) / "scenario.json"
            outside.write_bytes((ITERATION_ROOT / "scenario-manifest.json").read_bytes())
            with self.assertRaises(WorkflowValidationError) as raised:
                build_snapshot_plan(
                    candidate_iteration=ITERATION_ROOT / "candidate-iteration.json",
                    scenario_manifest=outside,
                    projection_report=ITERATION_ROOT / "projection-report.json",
                    analysis_report=ITERATION_ROOT / "analysis-report.json",
                    source_root=ROOT,
                )

        self.assertEqual(raised.exception.code, "snapshot_input_outside_repo")

    def test_optional_prompt_schedule_is_hash_bound(self):
        plan = _build_scheduled_plan()
        schedule = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))

        self.assertIn("prompt_schedule", plan["inputs"])
        self.assertEqual(plan["prompt_schedule_sha256"], schedule["schedule_sha256"])
        self.assertEqual(plan["candidate_ids"]["subjects"], schedule["expected_subjects"])
        self.assertEqual(plan["candidate_ids"]["locations"], schedule["expected_locations"])

    def test_nonselected_quality_contract_is_bound_without_prompt_schedule(self):
        plan = _build_quality_plan()
        contract = json.loads(QUALITY_CONTRACT_PATH.read_text(encoding="utf-8"))

        self.assertIn("quality_contract", plan["inputs"])
        self.assertNotIn("prompt_schedule", plan["inputs"])
        self.assertIsNone(plan["prompt_schedule_sha256"])
        self.assertEqual(plan["quality_contract_sha256"], contract["contract_sha256"])

    def test_quality_contract_and_prompt_schedule_are_mutually_exclusive(self):
        with self.assertRaises(WorkflowValidationError) as raised:
            build_snapshot_plan(
                candidate_iteration=SCHEDULE_ITERATION_ROOT / "candidate-iteration.json",
                scenario_manifest=SCHEDULE_ITERATION_ROOT / "scenario-manifest.json",
                projection_report=SCHEDULE_ITERATION_ROOT / "projection-report.json",
                analysis_report=SCHEDULE_ITERATION_ROOT / "analysis-report.json",
                prompt_schedule=FINAL_SCHEDULE_PATH,
                quality_contract=QUALITY_CONTRACT_PATH,
                source_root=ROOT,
            )

        self.assertEqual(raised.exception.code, "snapshot_quality_surface_conflict")


class TestVariationCandidateSnapshotMaterialization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="vs-", dir=RESULTS_ROOT)
        cls.addClassCleanup(cls.temp_dir.cleanup)
        cls.destination = Path(cls.temp_dir.name) / "s"
        cls.plan = _build_plan()
        cls.active_before = hashlib.sha256(canonical_json_bytes(_manifest_entries(ROOT))).hexdigest()
        cls.manifest = materialize_candidate_snapshots(
            cls.plan,
            source_root=ROOT,
            destination_root=cls.destination,
        )
        cls.active_after = hashlib.sha256(canonical_json_bytes(_manifest_entries(ROOT))).hexdigest()
        cls.baseline_root = cls.destination / "baseline-root"
        cls.candidate_root = cls.destination / "candidate-root"

    def test_active_source_is_unchanged(self):
        self.assertEqual(self.active_after, self.active_before)
        self.assertTrue(self.manifest["active_source_unchanged"])
        self.assertEqual(self.manifest["active_source_before_sha256"], self.active_before)
        self.assertEqual(self.manifest["active_source_after_sha256"], self.active_before)

    def test_baseline_is_a_byte_exact_filtered_source_copy(self):
        for source in _source_files(ROOT):
            relative = source.relative_to(ROOT)
            with self.subTest(path=relative.as_posix()):
                copied = self.baseline_root / relative
                self.assertTrue(copied.is_file())
                self.assertEqual(copied.read_bytes(), source.read_bytes())

    def test_candidate_delta_is_allowlist_only(self):
        allowed = set(MUTABLE_CANDIDATE_FILES) | {
            f"vocab/source/action_pools/{location}.json"
            for location in self.plan["candidate_ids"]["locations"]
        }

        self.assertTrue(set(self.manifest["changed_files"]).issubset(allowed))
        self.assertEqual(
            set(self.manifest["changed_files"]) - set(MUTABLE_CANDIDATE_FILES),
            {f"vocab/source/action_pools/{location}.json" for location in self.plan["candidate_ids"]["locations"]},
        )

    def test_candidate_materializes_exact_subject_location_and_action_counts(self):
        scope = json.loads((self.candidate_root / "vocab/data/variation_scope.json").read_text(encoding="utf-8"))
        action_pools = json.loads((self.candidate_root / "vocab/data/action_pools.json").read_text(encoding="utf-8"))

        self.assertEqual(len(scope["variation_subjects"]), 135)
        self.assertEqual(len(scope["variation_locations"]), 105)
        for location in self.plan["candidate_ids"]["locations"]:
            with self.subTest(location=location):
                self.assertEqual(len(action_pools[location]), 20)
                self.assertTrue((self.candidate_root / f"vocab/source/action_pools/{location}.json").is_file())

    def test_candidate_rebuild_and_compatibility_metrics_are_reproducible(self):
        action_check = subprocess.run(
            [sys.executable, "tools/build_action_pools.py", "--check"],
            cwd=self.candidate_root,
            capture_output=True,
            text=True,
            check=False,
        )
        metrics_run = subprocess.run(
            [sys.executable, "assets/calc_variations.py", "--json"],
            cwd=self.candidate_root,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(action_check.returncode, 0, action_check.stdout + action_check.stderr)
        self.assertEqual(metrics_run.returncode, 0, metrics_run.stdout + metrics_run.stderr)
        metrics = json.loads(metrics_run.stdout)["base"]
        self.assertEqual(metrics["unique_subjects"], 135)
        self.assertEqual(metrics["unique_locations"], 105)
        self.assertEqual(metrics["row_count"], 7817)
        self.assertEqual(metrics["total_base_variations"], 141984)
        self.assertEqual(self.manifest["candidate_metrics"], metrics)

    def test_compatibility_keeps_active_prompt_pairs_before_candidate_prompts_are_installed(self):
        candidate_prompts = [
            json.loads(line)
            for line in (self.candidate_root / "prompts.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        with (self.candidate_root / "assets/compatibility_review.csv").open(
            encoding="utf-8-sig", newline=""
        ) as handle:
            compatibility_rows = list(csv.DictReader(handle))
        with (self.baseline_root / "assets/compatibility_review.csv").open(
            encoding="utf-8-sig", newline=""
        ) as handle:
            baseline_rows = list(csv.DictReader(handle))

        existing_pairs = {
            (row["subj"], row["loc"])
            for row in compatibility_rows
            if row["is_existing"] == "1"
        } | {
            (row["subj"], row["canonical_loc"])
            for row in compatibility_rows
            if row["is_existing"] == "1"
        }
        baseline_existing_pairs = {
            (row["subj"], row["loc"])
            for row in baseline_rows
            if row["is_existing"] == "1"
        } | {
            (row["subj"], row["canonical_loc"])
            for row in baseline_rows
            if row["is_existing"] == "1"
        }
        self.assertTrue(baseline_existing_pairs.issubset(existing_pairs))
        self.assertEqual(len(candidate_prompts), 80)
        self.assertTrue(
            {row["subj"] for row in candidate_prompts}.issubset(
                set(self.plan["candidate_ids"]["subjects"])
            )
        )
        self.assertTrue(
            {row["loc"] for row in candidate_prompts}.issubset(
                set(self.plan["candidate_ids"]["locations"])
            )
        )
        self.assertTrue(
            {(row["subj"], row["loc"]) for row in candidate_prompts}.isdisjoint(existing_pairs)
        )

    def test_manifest_is_canonical_and_validates_snapshot_hashes(self):
        tracked = json.loads((self.destination / "snapshot-manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(canonical_json_bytes(tracked), canonical_json_bytes(self.manifest))
        validation = validate_snapshot_manifest(self.destination, self.manifest)
        self.assertEqual(validation["status"], "pass")
        self.assertEqual(validation["baseline_source_tree_sha256"], self.manifest["baseline_source_tree_sha256"])
        self.assertEqual(validation["candidate_source_tree_sha256"], self.manifest["candidate_source_tree_sha256"])

    def test_manifest_validation_rejects_candidate_hash_drift(self):
        target = self.candidate_root / "vocab/data/scene_compatibility.json"
        original = target.read_bytes()
        try:
            target.write_bytes(original + b"\n")
            with self.assertRaises(WorkflowValidationError) as raised:
                validate_snapshot_manifest(self.destination, self.manifest)
        finally:
            target.write_bytes(original)

        self.assertEqual(raised.exception.code, "candidate_snapshot_hash_mismatch")

    def test_manifest_validation_rejects_decision_field_tampering(self):
        cases = [
            ("state", "SNAPSHOT_READY"),
            ("prompt_generation_allowed", True),
            ("quantitative_gate", {**self.manifest["quantitative_gate"], "target": 1, "target_met": True}),
        ]
        for field, value in cases:
            with self.subTest(field=field):
                tampered = copy.deepcopy(self.manifest)
                tampered[field] = value
                with self.assertRaises(WorkflowValidationError) as raised:
                    validate_snapshot_manifest(self.destination, tampered)
                self.assertEqual(raised.exception.code, "snapshot_decision_field_mismatch")

    def test_materializer_rejects_bound_input_hash_drift_and_path_escape(self):
        current_plan = _build_plan()
        drifted = copy.deepcopy(current_plan)
        drifted["inputs"]["analysis_report"]["sha256"] = "0" * 64
        escaped = copy.deepcopy(current_plan)
        escaped["inputs"]["analysis_report"]["path"] = "../outside.json"
        for plan, expected in (
            (drifted, "snapshot_input_hash_mismatch"),
            (escaped, "snapshot_input_outside_repo"),
        ):
            with self.subTest(expected=expected):
                destination = Path(self.temp_dir.name) / f"rejected-{expected}"
                with self.assertRaises(WorkflowValidationError) as raised:
                    materialize_candidate_snapshots(plan, source_root=ROOT, destination_root=destination)
                self.assertEqual(raised.exception.code, expected)
                self.assertFalse(destination.exists())

    def test_materializer_rejects_derived_plan_tampering(self):
        cases = [
            ("projection_target", 1),
            ("projected_base_variations", 0),
            ("candidate_ids", {**self.plan["candidate_ids"], "subjects": self.plan["candidate_ids"]["subjects"][:-1]}),
            ("mutable_candidate_files", self.plan["mutable_candidate_files"][:-1]),
        ]
        for field, value in cases:
            with self.subTest(field=field):
                tampered = copy.deepcopy(self.plan)
                tampered[field] = value
                destination = Path(self.temp_dir.name) / f"tampered-{field}"
                with self.assertRaises(WorkflowValidationError) as raised:
                    materialize_candidate_snapshots(tampered, source_root=ROOT, destination_root=destination)
                self.assertEqual(raised.exception.code, "snapshot_plan_derived_field_mismatch")
                self.assertFalse(destination.exists())

    def test_materializer_rejects_runtime_extra_drift_after_planning(self):
        current_plan = _build_plan()
        original_entries = materializer._manifest_entries

        def drifted_entries(root):
            entries = original_entries(root)
            if Path(root).resolve() == ROOT.resolve():
                entries = dict(entries)
                entries["prompts.jsonl"] = "0" * 64
            return entries

        destination = Path(self.temp_dir.name) / "runtime-extra-drift"
        with patch.object(materializer, "_manifest_entries", side_effect=drifted_entries):
            with self.assertRaises(WorkflowValidationError) as raised:
                materialize_candidate_snapshots(current_plan, source_root=ROOT, destination_root=destination)

        self.assertEqual(raised.exception.code, "snapshot_plan_derived_field_mismatch")
        self.assertFalse(destination.exists())

    def test_materializer_rejects_existing_destination(self):
        existing = Path(self.temp_dir.name) / "existing"
        existing.mkdir()
        current_plan = _build_plan()

        with self.assertRaises(WorkflowValidationError) as raised:
            materialize_candidate_snapshots(current_plan, source_root=ROOT, destination_root=existing)

        self.assertEqual(raised.exception.code, "snapshot_destination_exists")


class TestScheduledVariationCandidateSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="vs-schedule-", dir=RESULTS_ROOT)
        cls.addClassCleanup(cls.temp_dir.cleanup)
        cls.destination = Path(cls.temp_dir.name) / "s"
        cls.plan = _build_scheduled_plan()
        cls.manifest = materialize_candidate_snapshots(
            cls.plan,
            source_root=ROOT,
            destination_root=cls.destination,
        )

    def test_schedule_materializes_exact_nineteen_candidate_rows(self):
        schedule = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))
        rows = [
            json.loads(line)
            for line in (self.destination / "candidate-root/prompts.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        self.assertEqual(rows, schedule["candidate_rows"])
        self.assertEqual(
            hashlib.sha256((self.destination / "candidate-root/prompts.jsonl").read_bytes()).hexdigest(),
            schedule["candidate_prompts_jsonl_sha256"],
        )
        self.assertEqual(self.manifest["prompt_rows"], {"baseline": 80, "candidate": 19})
        self.assertEqual(self.manifest["prompt_schedule_sha256"], schedule["schedule_sha256"])

    def test_scheduled_snapshot_revalidates_all_hashes_and_decisions(self):
        validation = validate_snapshot_manifest(self.destination, self.manifest)

        self.assertEqual(validation["status"], "pass")
        self.assertTrue(self.manifest["prompt_generation_allowed"])
        self.assertEqual(self.manifest["candidate_metrics"]["total_base_variations"], 150184)

    def test_materializer_rejects_corrupted_scheduled_prompt_write(self):
        destination = Path(self.temp_dir.name) / "corrupt-write"
        original_write = materializer._write_jsonl

        def corrupt_candidate(path, rows):
            original_write(path, rows)
            if path.parent.name == "candidate-root":
                path.write_bytes(path.read_bytes() + b"\n")

        with patch.object(materializer, "_write_jsonl", side_effect=corrupt_candidate):
            with self.assertRaises(WorkflowValidationError) as raised:
                materialize_candidate_snapshots(
                    _build_scheduled_plan(),
                    source_root=ROOT,
                    destination_root=destination,
                )

        self.assertEqual(raised.exception.code, "coverage_schedule_prompt_hash_mismatch")
        self.assertFalse(destination.exists())


class TestFinalCoverageVariationCandidateSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="vs-final-", dir=RESULTS_ROOT)
        cls.addClassCleanup(cls.temp_dir.cleanup)
        cls.destination = Path(cls.temp_dir.name) / "s"
        cls.manifest = materialize_candidate_snapshots(
            _build_final_scheduled_plan(),
            source_root=ROOT,
            destination_root=cls.destination,
        )

    def test_full_workflow_witness_certificate_replays_during_materialization(self):
        verification = self.manifest["prompt_schedule_verification"]

        self.assertEqual(verification["status"], "pass")
        self.assertEqual(verification["fixed_seed_count"], 80)
        self.assertEqual(verification["extra_seed_count"], 0)
        self.assertEqual(verification["verified_location_count"], 19)
        self.assertEqual(verification["verified_subject_count"], 15)
        self.assertFalse(verification["coverage_is_quality_evidence"])
        self.assertEqual(verification["fixed_verdict"], "reject")
        self.assertFalse(verification["promotion_ready"])

    def test_final_coverage_snapshot_revalidates_certificate(self):
        self.assertEqual(
            validate_snapshot_manifest(self.destination, self.manifest)["status"],
            "pass",
        )


class TestNonSelectedQualityCandidateSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="vs-quality-", dir=RESULTS_ROOT)
        cls.addClassCleanup(cls.temp_dir.cleanup)
        cls.destination = Path(cls.temp_dir.name) / "s"
        cls.manifest = materialize_candidate_snapshots(
            _build_quality_plan(),
            source_root=ROOT,
            destination_root=cls.destination,
        )

    def test_quality_surface_uses_default_eighty_rows_without_schedule(self):
        self.assertEqual(self.manifest["prompt_rows"], {"baseline": 80, "candidate": 80})
        self.assertIsNone(self.manifest["prompt_schedule_sha256"])
        self.assertIsNone(self.manifest["prompt_schedule_verification"])
        self.assertIsNotNone(self.manifest["quality_contract_sha256"])

    def test_quality_snapshot_revalidates_contract_and_hashes(self):
        self.assertEqual(
            validate_snapshot_manifest(self.destination, self.manifest)["status"],
            "pass",
        )


if __name__ == "__main__":
    unittest.main()
