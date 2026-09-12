from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import build_prompt_quality_confirmation as confirmation
from tools import build_prompt_quality_verification as verification
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]


class CandidateGateTests(unittest.TestCase):
    def setUp(self) -> None:
        artifact_root = ROOT / "assets/results"
        artifact_root.mkdir(parents=True, exist_ok=True)
        self.temp = Path(tempfile.mkdtemp(prefix="candidate-gates-", dir=artifact_root))
        self.addCleanup(lambda: shutil.rmtree(self.temp, ignore_errors=True))

    def test_confirmation_cohort_is_repeatable_and_rechecks_new_history(self) -> None:
        seed_file = self.temp / "holdout.json"
        with mock.patch.object(confirmation, "_existing_seeds", return_value={1, 2}) as history:
            cohort = confirmation._load_or_create_seeds(seed_file)
            history.assert_called_once_with()
            self.assertEqual(confirmation._load_or_create_seeds(seed_file), cohort)
        seeds = cohort["confirmation_seeds"]
        self.assertEqual(len(set(seeds)), 256)
        self.assertFalse({1, 2} & set(seeds))
        with mock.patch.object(confirmation, "_existing_seeds", return_value={seeds[0]}):
            with self.assertRaisesRegex(ValueError, "overlap"):
                confirmation._load_or_create_seeds(seed_file)

    def test_confirmation_rejects_duplicate_or_short_cohort(self) -> None:
        seed_file = self.temp / "holdout.json"
        for seeds in ([1] * 256, list(range(255))):
            with self.subTest(count=len(set(seeds))):
                seed_file.write_bytes(canonical_json_bytes({"confirmation_seeds": seeds}))
                with mock.patch.object(confirmation, "_existing_seeds", return_value=set()):
                    with self.assertRaisesRegex(ValueError, "256 unique"):
                        confirmation._load_or_create_seeds(seed_file)

    def test_confirmation_retains_result_contract_and_post_generation_history(self) -> None:
        seed_file = self.temp / "holdout.json"
        cohort = confirmation.build_confirmation_cohort([1, 2])
        seed_file.write_bytes(canonical_json_bytes(cohort))
        output = self.temp / "confirmation"
        output.mkdir()
        for side in ("baseline", "candidate"):
            (output / f"{side}-records.jsonl").write_bytes(canonical_json_bytes({"run_seed": 42}))
        metrics = {"fixture": 1}
        with mock.patch.object(confirmation, "_existing_seeds", return_value={1, 2}) as history, \
             mock.patch.object(confirmation.subprocess, "run") as run, \
             mock.patch.object(confirmation, "load_policy", return_value={}), \
             mock.patch.object(confirmation, "analyze_records", return_value={"metrics": metrics}), \
             mock.patch.object(confirmation, "_compare", return_value={"verdict": "pass"}), \
             mock.patch.object(confirmation, "build_source_manifest", return_value={"source_tree_hash": "a" * 64}), \
             mock.patch.object(confirmation, "_apply_baseline_ablation", return_value="disable_composition_punctuation_normalization") as ablate:
            # Keep the later scan: records added while generation runs must be seen.
            run.side_effect = lambda *args, **kwargs: setattr(history, "return_value", {1, 2, 3})
            result = confirmation.build_confirmation(objective="g005", output_dir=output, seed_file=seed_file)
        ablate.assert_not_called()
        self.assertEqual(result, {
            "cohort_hash": cohort["cohort_hash"],
            "comparison": {"verdict": "pass"},
            "excluded_seed_count": 3,
            "excluded_seed_set_hash": hashlib.sha256(canonical_json_bytes([1, 2, 3])).hexdigest(),
            "feature_ablation": "disable_composition_punctuation_normalization",
            "objective": "g005",
            "record_count": 256,
            "schema_version": "prompt-quality-confirmation/v1",
            "source_tree_hash": "a" * 64,
        })
        self.assertEqual(json.loads((output / "confirmation.json").read_text(encoding="utf-8")), result)
        self.assertEqual([call.args[0][6] for call in run.call_args_list], ["baseline", "candidate"])

    def test_candidate_gate_inventory_is_exact_and_candidate_owned(self) -> None:
        candidate = self.temp / "candidate"
        inventory = verification.candidate_gate_inventory(candidate, python="python", pwsh="pwsh")
        self.assertEqual(set(inventory), verification.REQUIRED_GATES)
        self.assertIsNone(inventory["blind_review"])
        self.assertIsNone(inventory["prompt_quality_confirmation"])
        self.assertIsNone(inventory["target_comparison"])
        for gate, command in inventory.items():
            if command is not None and gate != "python_tests":
                self.assertTrue(any(str(candidate) in value for value in command), gate)
        self.assertEqual(inventory["browser"][-2:], ["-CustomNodeRoot", str(candidate.resolve())])
        self.assertEqual(inventory["frontend"][-2:], ["-CustomNodeRoot", str(candidate.resolve())])
        for gate in ("frontend", "browser"):
            command = inventory[gate]
            self.assertEqual(command[command.index("-ActivePluginRoot") + 1], str(ROOT.resolve()))

    def test_environment_is_sanitized_to_candidate_root(self) -> None:
        candidate = self.temp / "candidate"
        with mock.patch.dict(confirmation.os.environ, {"PYTHONPATH": str(ROOT), "PYTHONNOUSERSITE": "0"}):
            environment = confirmation._sanitized_environment(candidate)
        self.assertEqual(environment["PYTHONPATH"], str(candidate.resolve()))
        self.assertEqual(environment["PYTHONNOUSERSITE"], "1")
        self.assertEqual(environment["PYTHONSAFEPATH"], "1")

    def test_import_sentinel_rejects_active_tree_module(self) -> None:
        fake_module = mock.Mock(__file__=str(ROOT / "pipeline/location_builder.py"))
        with mock.patch.dict(confirmation.sys.modules, {"candidate_gate_leak": fake_module}):
            with self.assertRaises(WorkflowValidationError) as caught:
                confirmation._import_sentinel(self.temp / "candidate", ROOT)
        self.assertEqual(caught.exception.code, "active_source_imported")

    def test_candidate_seed_fixture_must_be_outside_both_roots(self) -> None:
        candidate = self.temp / "candidate"
        candidate.mkdir()
        (candidate / "tools").mkdir()
        (candidate / "tools/build_prompt_quality_confirmation.py").write_text("", encoding="utf-8")
        comparison_path = self.temp / "comparison.json"
        review_path = self.temp / "review.json"
        comparison_path.write_bytes(canonical_json_bytes({"schema_version": confirmation.V150_COMPARISON_SCHEMA}))
        review_path.write_bytes(canonical_json_bytes({"schema_version": confirmation.V150_REVIEW_SCHEMA}))
        with mock.patch.object(confirmation, "build_source_manifest", return_value={"entries": [], "source_tree_hash": "a" * 64}), \
             mock.patch.object(confirmation, "_snapshot_content_hash", return_value="b" * 64), \
             mock.patch.object(confirmation, "_load_json_object", side_effect=[{
                 "schema_version": confirmation.V150_COMPARISON_SCHEMA,
                 "experiment_id": "exp", "candidate_source_tree_sha256": "a" * 64,
                 "candidate_snapshot_content_sha256": "b" * 64, "automatic_verdict": "pass",
             }, {
                 "schema_version": confirmation.V150_REVIEW_SCHEMA,
                 "experiment_id": "exp", "candidate_source_tree_sha256": "a" * 64,
                 "comparison_artifact_sha256": hashlib.sha256(comparison_path.read_bytes()).hexdigest(),
                 "status": "pass", "verdict": "pass",
             }]):
            with self.assertRaises(WorkflowValidationError) as caught:
                confirmation.build_candidate_confirmation(
                    candidate_root=candidate, comparison_path=comparison_path, review_path=review_path,
                    output_dir=self.temp / "out", seed_file=candidate / "seeds.json", experiment_id="exp",
                )
        self.assertEqual(caught.exception.code, "seed_fixture_inside_source")

    def test_candidate_confirmation_accepts_v3_v5_and_rejects_mixing(self) -> None:
        candidate = self.temp / "candidate"
        (candidate / "tools").mkdir(parents=True)
        (candidate / "tools/build_prompt_quality_confirmation.py").write_text("", encoding="utf-8")
        comparison_path = self.temp / "comparison-v3.json"
        comparison_path.write_bytes(canonical_json_bytes({
            "schema_version": "prompt-quality-comparison/v3", "experiment_id": "exp",
            "candidate_source_tree_sha256": "a" * 64, "candidate_snapshot_content_sha256": "b" * 64,
            "automatic_comparison_verdict": "pass",
        }))
        review_path = self.temp / "review-v5.json"
        base_review = {
            "schema_version": "prompt-quality-review/v5", "experiment_id": "exp",
            "candidate_source_tree_sha256": "a" * 64,
            "comparison_artifact_hash": hashlib.sha256(comparison_path.read_bytes()).hexdigest(),
            "status": "pass", "verdict": "pass",
        }
        review_path.write_bytes(canonical_json_bytes(base_review))
        with mock.patch.object(confirmation, "build_source_manifest", return_value={"entries": [], "source_tree_hash": "a" * 64}), \
             mock.patch.object(confirmation, "_snapshot_content_hash", return_value="b" * 64):
            with self.assertRaises(WorkflowValidationError) as accepted:
                confirmation.build_candidate_confirmation(
                    candidate_root=candidate, comparison_path=comparison_path, review_path=review_path,
                    output_dir=self.temp / "out", seed_file=candidate / "seeds.json", experiment_id="exp",
                )
            self.assertEqual(accepted.exception.code, "seed_fixture_inside_source")
            base_review["schema_version"] = "prompt-quality-review/v4"
            review_path.write_bytes(canonical_json_bytes(base_review))
            with self.assertRaises(WorkflowValidationError) as mixed:
                confirmation.build_candidate_confirmation(
                    candidate_root=candidate, comparison_path=comparison_path, review_path=review_path,
                    output_dir=self.temp / "out", seed_file=self.temp / "seeds.json", experiment_id="exp",
                )
            self.assertEqual(mixed.exception.code, "mixed_v150_review_generation")

    def test_v6_confirmation_and_verification_schema_dispatch(self) -> None:
        candidate = self.temp / "candidate-v6"
        (candidate / "tools").mkdir(parents=True)
        (candidate / "tools/build_prompt_quality_confirmation.py").write_text("", encoding="utf-8")
        comparison_path = self.temp / "comparison-v4.json"
        comparison_path.write_bytes(canonical_json_bytes({
            "schema_version": "prompt-quality-comparison/v4", "experiment_id": "exp",
            "candidate_source_tree_sha256": "a" * 64, "candidate_snapshot_content_sha256": "b" * 64,
            "automatic_comparison_verdict": "pass",
        }))
        review_path = self.temp / "review-v6.json"
        review_path.write_bytes(canonical_json_bytes({
            "schema_version": "prompt-quality-review/v6", "experiment_id": "exp",
            "candidate_source_tree_sha256": "a" * 64,
            "comparison_artifact_hash": hashlib.sha256(comparison_path.read_bytes()).hexdigest(),
            "status": "pass", "verdict": "pass",
        }))
        with mock.patch.object(confirmation, "build_source_manifest", return_value={"entries": [], "source_tree_hash": "a" * 64}), \
             mock.patch.object(confirmation, "_snapshot_content_hash", return_value="b" * 64):
            with self.assertRaises(WorkflowValidationError) as accepted:
                confirmation.build_candidate_confirmation(
                    candidate_root=candidate, comparison_path=comparison_path, review_path=review_path,
                    output_dir=self.temp / "out-v6", seed_file=candidate / "seeds.json", experiment_id="exp",
                )
            self.assertEqual(accepted.exception.code, "seed_fixture_inside_source")
        with self.assertRaises(WorkflowValidationError) as verification_dispatch:
            verification.build_verification(
                comparison_path=comparison_path, review_path=review_path,
                evidence_dir=self.temp, output_path=self.temp / "verification-v6.json",
            )
        self.assertEqual(verification_dispatch.exception.code, "candidate_root_required")

    def test_verification_schema_dispatch_is_closed(self) -> None:
        evidence = self.temp / "evidence"
        evidence.mkdir()
        review = self.temp / "review.json"
        review.write_text("{}", encoding="utf-8")
        comparison = self.temp / "comparison.json"
        comparison.write_bytes(canonical_json_bytes({"schema_version": "prompt-quality-comparison/v999"}))
        with self.assertRaises(WorkflowValidationError) as caught:
            verification.build_verification(
                comparison_path=comparison, review_path=review, evidence_dir=evidence,
                output_path=self.temp / "receipt.json",
            )
        self.assertEqual(caught.exception.code, "invalid_comparison_artifact")

    def test_v2_requires_explicit_candidate_root(self) -> None:
        evidence = self.temp / "evidence"
        evidence.mkdir()
        review = self.temp / "review.json"
        review.write_text("{}", encoding="utf-8")
        comparison = self.temp / "comparison.json"
        comparison.write_bytes(canonical_json_bytes({"schema_version": verification.V150_COMPARISON_SCHEMA}))
        with self.assertRaises(WorkflowValidationError) as caught:
            verification.build_verification(
                comparison_path=comparison, review_path=review, evidence_dir=evidence,
                output_path=self.temp / "receipt.json",
            )
        self.assertEqual(caught.exception.code, "candidate_root_required")


if __name__ == "__main__":
    unittest.main()
