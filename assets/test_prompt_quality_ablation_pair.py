import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


from tools.build_prompt_quality_ablation_pair import (
    _behavior_contract,
    _hash_bytes,
    _run_child,
    _validate_features,
    validate_pair,
)
from tools.compare_prompt_quality import promote_check
from tools.prompt_quality_loop import _normalize_behavior_transform
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
FEATURES = ["g004", "g005", "g006"]


class TestPromptQualityAblationPair(unittest.TestCase):
    def setUp(self):
        results = ROOT / "assets" / "results"
        results.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="ablation-pair-", dir=results))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.contract_hash = "a" * 64

    def write_side(self, name, *, features, variant, prompt):
        side = self.root / name
        side.mkdir()
        behavior = _behavior_contract(variant, self.contract_hash, features)
        artifacts = {
            "records.jsonl": canonical_json_bytes({
                "cleaned_prompt": prompt, "cohort": "control", "run_seed": 0,
            }),
            "metrics.json": canonical_json_bytes({"record_count": 1}),
            "issues.json": canonical_json_bytes({"issues": []}),
            "source-manifest.json": canonical_json_bytes({"source_tree_hash": "f" * 64}),
            "telemetry.json": canonical_json_bytes({"runs": []}),
        }
        for filename, content in artifacts.items():
            (side / filename).write_bytes(content)
        manifest = {
            "ablation_contract_hash": self.contract_hash,
            "behavior_feature_ids": features,
            "behavior_transform_hash": _hash_bytes(canonical_json_bytes(behavior)),
            "behavior_variant": variant,
            "artifact_hashes": {name: _hash_bytes(content) for name, content in artifacts.items()},
            "cohort_hash": "b" * 64,
            "effective_workflow_hash": "c" * 64,
            "override_hash": "d" * 64,
            "profile_hash": "e" * 64,
            "replay_evidence": {"checked": 1, "mismatch_count": 0, "status": "pass"},
            "source_tree_hash": "f" * 64,
            "workflow_hash": "0" * 64,
        }
        (side / "run-manifest.json").write_bytes(canonical_json_bytes(manifest))
        return side

    def valid_dirs(self):
        current = self.write_side("current", features=[], variant="current", prompt="clean prompt")
        baseline = self.write_side(
            "baseline", features=FEATURES, variant="combined_ablation_baseline", prompt="legacy prompt.,"
        )
        return current, baseline

    def write_pair_artifact(self, current, baseline):
        sides = {}
        for name, path in (("current", current), ("baseline", baseline)):
            manifest_path = path / "run-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            sides[name] = {
                "artifact_hashes": manifest["artifact_hashes"],
                "records_hash": _hash_bytes((path / "records.jsonl").read_bytes()),
                "run_manifest_hash": _hash_bytes(manifest_path.read_bytes()),
                "run_manifest_path": manifest_path.relative_to(ROOT).as_posix(),
                "run_path": path.relative_to(ROOT).as_posix(),
            }
        pair_path = self.root / "ablation-pair.json"
        pair_path.write_bytes(canonical_json_bytes({
            "ablation_contract_hash": self.contract_hash,
            "schema_version": "prompt-quality-ablation-pair/v1", "sides": sides,
        }))
        return pair_path, sides

    def test_closed_feature_order_rejects_unknown_duplicate_and_reordering(self):
        self.assertEqual(_validate_features(FEATURES), FEATURES)
        for invalid in (
            ["g004", "g005", "unknown"],
            ["g004", "g005", "g005", "g006"],
            ["g006", "g005", "g004"],
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                _validate_features(invalid)

    def test_behavior_transform_none_defaults_but_explicit_empty_fails_closed(self):
        default = _normalize_behavior_transform(None)
        self.assertEqual(default["feature_ids"], [])
        self.assertEqual(default["variant"], "current")
        with self.assertRaises(WorkflowValidationError) as caught:
            _normalize_behavior_transform({})
        self.assertEqual(caught.exception.code, "invalid_behavior_transform")

    def test_declared_current_and_baseline_behavior_transforms_are_preserved(self):
        current = _behavior_contract("current", self.contract_hash, [])
        baseline = _behavior_contract("combined_ablation_baseline", self.contract_hash, FEATURES)
        self.assertEqual(_normalize_behavior_transform(current), current)
        self.assertEqual(_normalize_behavior_transform(baseline), baseline)

    def test_child_commands_are_process_isolated_and_baseline_only_declares_ablation(self):
        calls = []

        def capture(command, **kwargs):
            calls.append(command)

        shared = dict(
            output_dir=self.root / "run", artifact_root=self.root,
            workflow=ROOT / "ComfyUI-workflow-context.json",
            profile=ROOT / "verification/fixtures/prompt_quality_supported_profile.json",
            control_seeds=ROOT / "assets/fixtures/prompt_quality_control_seeds.json",
            experiment_seed=1, iteration_id="test", samples=80, features=FEATURES, overrides=None,
            policy=ROOT / "vocab/data/prompt_quality_policy.json",
        )
        with patch("tools.build_prompt_quality_ablation_pair.subprocess.run", side_effect=capture):
            _run_child(variant="current", **shared)
            _run_child(variant="combined_ablation_baseline", **shared)
        self.assertEqual(len(calls), 2)
        self.assertIn("current", calls[0])
        self.assertIn("combined_ablation_baseline", calls[1])
        self.assertEqual(calls[0][0], calls[1][0])

    def test_valid_pair_freezes_sentinel_and_replay(self):
        current, baseline = self.valid_dirs()
        result = validate_pair(current, baseline, contract_hash=self.contract_hash)
        self.assertEqual(result["changed_seeds"], [0])
        self.assertRegex(result["sentinel_hash"], r"^[0-9a-f]{64}$")

    def test_source_cohort_workflow_profile_override_and_contract_drift_fail_closed(self):
        fields = (
            "source_tree_hash", "cohort_hash", "workflow_hash", "effective_workflow_hash",
            "profile_hash", "override_hash", "ablation_contract_hash",
        )
        for field in fields:
            with self.subTest(field=field):
                current, baseline = self.valid_dirs()
                path = baseline / "run-manifest.json"
                manifest = json.loads(path.read_text(encoding="utf-8"))
                manifest[field] = "9" * 64
                path.write_bytes(canonical_json_bytes(manifest))
                with self.assertRaises(ValueError):
                    validate_pair(current, baseline, contract_hash=self.contract_hash)
                shutil.rmtree(current)
                shutil.rmtree(baseline)

    def test_behavior_hash_replay_and_sentinel_tamper_fail_closed(self):
        for mutation in ("behavior_hash", "replay", "replay_missing", "replay_count", "sentinel"):
            with self.subTest(mutation=mutation):
                current, baseline = self.valid_dirs()
                if mutation == "behavior_hash":
                    path = baseline / "run-manifest.json"
                    value = json.loads(path.read_text(encoding="utf-8"))
                    value["behavior_transform_hash"] = "9" * 64
                    path.write_bytes(canonical_json_bytes(value))
                elif mutation == "replay":
                    path = current / "run-manifest.json"
                    value = json.loads(path.read_text(encoding="utf-8"))
                    value["replay_evidence"] = {"checked": 0, "mismatch_count": 0, "status": "not_run"}
                    path.write_bytes(canonical_json_bytes(value))
                elif mutation == "replay_missing":
                    path = current / "run-manifest.json"
                    value = json.loads(path.read_text(encoding="utf-8"))
                    value.pop("replay_evidence")
                    path.write_bytes(canonical_json_bytes(value))
                elif mutation == "replay_count":
                    path = current / "run-manifest.json"
                    value = json.loads(path.read_text(encoding="utf-8"))
                    value["replay_evidence"]["checked"] = 2
                    path.write_bytes(canonical_json_bytes(value))
                else:
                    (baseline / "records.jsonl").write_bytes((current / "records.jsonl").read_bytes())
                with self.assertRaises(ValueError):
                    validate_pair(current, baseline, contract_hash=self.contract_hash)
                shutil.rmtree(current)
                shutil.rmtree(baseline)

    def test_each_bound_run_artifact_is_required_and_hash_validated(self):
        for filename in ("records.jsonl", "metrics.json", "issues.json", "source-manifest.json", "telemetry.json"):
            for mutation in ("tamper", "missing"):
                with self.subTest(filename=filename, mutation=mutation):
                    current, baseline = self.valid_dirs()
                    path = baseline / filename
                    if mutation == "tamper":
                        path.write_bytes(path.read_bytes() + b"tampered")
                    else:
                        path.unlink()
                    with self.assertRaises(ValueError):
                        validate_pair(current, baseline, contract_hash=self.contract_hash)
                    shutil.rmtree(current)
                    shutil.rmtree(baseline)

    def test_missing_run_manifest_is_rejected(self):
        current, baseline = self.valid_dirs()
        (baseline / "run-manifest.json").unlink()
        with self.assertRaises((OSError, ValueError)):
            validate_pair(current, baseline, contract_hash=self.contract_hash)

    def test_promotion_recursively_rejects_tampered_consumed_artifacts(self):
        for filename in ("records.jsonl", "metrics.json", "issues.json", "run-manifest.json"):
            with self.subTest(filename=filename):
                current, baseline = self.valid_dirs()
                pair_path, sides = self.write_pair_artifact(current, baseline)
                comparison = {
                    "ablation_pair": {
                        "artifact_hash": _hash_bytes(pair_path.read_bytes()),
                        "artifact_path": pair_path.relative_to(ROOT).as_posix(),
                        "consumed_artifact_hashes": {
                            "after": sides["current"]["artifact_hashes"],
                            "before": sides["baseline"]["artifact_hashes"],
                        },
                        "contract_hash": self.contract_hash,
                    },
                    "automatic_verdict": "pass", "review_selection": {},
                    "schema_version": "prompt-quality-comparison/v1",
                }
                comparison_path = self.root / "comparison.json"
                comparison_path.write_bytes(canonical_json_bytes(comparison))
                (baseline / filename).write_bytes((baseline / filename).read_bytes() + b"tampered")
                result = promote_check(comparison_path)
                self.assertIn("ablation_pair_recursive_validation_failed", result["failures"])
                shutil.rmtree(current)
                shutil.rmtree(baseline)

    def test_v3_promotion_recomputes_ablation_pair_hash(self):
        pair_path = self.root / "ablation-pair.json"
        pair_path.write_bytes(canonical_json_bytes({"schema_version": "prompt-quality-ablation-pair/v1"}))
        comparison = {
            "ablation_pair": {
                "artifact_hash": "0" * 64,
                "artifact_path": pair_path.relative_to(ROOT).as_posix(),
            },
            "automatic_verdict": "pass",
            "review_selection": {},
            "schema_version": "prompt-quality-comparison/v1",
        }
        comparison_path = self.root / "comparison.json"
        comparison_path.write_bytes(canonical_json_bytes(comparison))
        result = promote_check(comparison_path)
        self.assertEqual(result["verdict"], "reject")
        self.assertIn("ablation_pair_hash_mismatch", result["failures"])


if __name__ == "__main__":
    unittest.main()
