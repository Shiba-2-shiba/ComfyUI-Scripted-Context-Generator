"""Generate and bind current/combined-ablation prompt-quality runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_prompt_quality_confirmation import (
    ABLATION_FEATURE_IDS,
    ablation_contract,
    apply_combined_baseline_ablation,
)
from tools.prompt_quality_loop import _atomic_write, _record_analysis_hashes, generate_run
from tools.analyze_prompt_quality import write_analysis
from tools.workflow_prompt_runner import canonical_json_bytes, load_profile
from workflow_widget_validation import load_workflow


PAIR_SCHEMA_VERSION = "prompt-quality-ablation-pair/v1"
REQUIRED_RUN_ARTIFACTS = ("records.jsonl", "metrics.json", "issues.json", "source-manifest.json", "telemetry.json")


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def _repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        raise ValueError(f"artifact must be beneath repository root: {path}") from None


def _validate_features(feature_ids: Sequence[str]) -> list[str]:
    selected = list(feature_ids)
    if selected != list(ABLATION_FEATURE_IDS):
        raise ValueError(f"features must be exactly {','.join(ABLATION_FEATURE_IDS)} in order")
    return selected


def _behavior_contract(variant: str, contract_hash: str, features: Sequence[str]) -> dict[str, Any]:
    return {
        "ablation_contract_hash": contract_hash,
        "feature_ids": list(features),
        "variant": variant,
    }


def _run_child(
    *,
    variant: str,
    output_dir: Path,
    artifact_root: Path,
    workflow: Path,
    profile: Path,
    control_seeds: Path,
    experiment_seed: int,
    iteration_id: str,
    samples: int,
    features: Sequence[str],
    overrides: Path | None,
    policy: Path,
) -> None:
    command = [
        sys.executable, str(Path(__file__).resolve()), "_generate",
        "--variant", variant,
        "--output-dir", str(output_dir),
        "--artifact-root", str(artifact_root),
        "--workflow", str(workflow),
        "--profile", str(profile),
        "--control-seeds", str(control_seeds),
        "--experiment-seed", str(experiment_seed),
        "--iteration-id", iteration_id,
        "--samples", str(samples),
        "--features", ",".join(features),
        "--policy", str(policy),
    ]
    if overrides is not None:
        command.extend(("--overrides", str(overrides)))
    subprocess.run(command, cwd=ROOT, check=True)


def _record_index(path: Path) -> dict[int, dict[str, Any]]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    result = {int(record["run_seed"]): record for record in records}
    if len(result) != len(records):
        raise ValueError(f"duplicate run seed in {path}")
    return result


def _validated_artifact_hashes(run_dir: Path, manifest: Mapping[str, Any]) -> dict[str, str]:
    declared = manifest.get("artifact_hashes")
    if not isinstance(declared, Mapping) or any(name not in declared for name in REQUIRED_RUN_ARTIFACTS):
        raise ValueError(f"run manifest is missing required artifact hashes: {run_dir}")
    validated: dict[str, str] = {}
    for name in REQUIRED_RUN_ARTIFACTS:
        path = run_dir / name
        if not path.is_file():
            raise ValueError(f"required run artifact is missing: {path}")
        actual = _hash_bytes(path.read_bytes())
        if declared.get(name) != actual:
            raise ValueError(f"run artifact hash drifted: {path}")
        validated[name] = actual
    return validated


def validate_pair(current_dir: Path, baseline_dir: Path, *, contract_hash: str) -> dict[str, Any]:
    current_manifest = _load_object(current_dir / "run-manifest.json")
    baseline_manifest = _load_object(baseline_dir / "run-manifest.json")
    shared_fields = (
        "cohort_hash", "workflow_hash", "effective_workflow_hash", "profile_hash",
        "override_hash", "source_tree_hash", "ablation_contract_hash",
    )
    drift = [field for field in shared_fields if current_manifest.get(field) != baseline_manifest.get(field)]
    if drift:
        raise ValueError(f"paired run contract drift: {','.join(drift)}")
    if current_manifest.get("ablation_contract_hash") != contract_hash:
        raise ValueError("paired runs do not bind the requested ablation contract")
    expected_variants = {
        "current": (current_dir, current_manifest, [], "current"),
        "baseline": (
            baseline_dir,
            baseline_manifest,
            list(ABLATION_FEATURE_IDS),
            "combined_ablation_baseline",
        ),
    }
    for side, (run_dir, manifest, features, variant) in expected_variants.items():
        _validated_artifact_hashes(run_dir, manifest)
        behavior = _behavior_contract(variant, contract_hash, features)
        if (
            manifest.get("behavior_feature_ids") != features
            or manifest.get("behavior_variant") != variant
            or manifest.get("behavior_transform_hash") != _hash_bytes(canonical_json_bytes(behavior))
        ):
            raise ValueError(f"invalid {side} behavior transform identity")
        replay = manifest.get("replay_evidence")
        if (
            not isinstance(replay, Mapping)
            or set(replay) != {"checked", "mismatch_count", "status"}
            or replay.get("status") != "pass"
            or replay.get("mismatch_count") != 0
            or not isinstance(replay.get("checked"), int)
            or isinstance(replay.get("checked"), bool)
            or replay.get("checked") <= 0
        ):
            raise ValueError(f"{side} immutable replay evidence did not pass")
    current_records = _record_index(current_dir / "records.jsonl")
    baseline_records = _record_index(baseline_dir / "records.jsonl")
    if set(current_records) != set(baseline_records):
        raise ValueError("paired record seed sets differ")
    expected_count = len(current_records)
    for side, manifest in (("current", current_manifest), ("baseline", baseline_manifest)):
        if manifest["replay_evidence"]["checked"] != expected_count:
            raise ValueError(f"{side} replay checked count does not match records")
    if any(current_records[seed].get("cohort") != baseline_records[seed].get("cohort") for seed in current_records):
        raise ValueError("paired record cohort labels differ")
    changed_seeds = sorted(
        seed for seed in current_records
        if current_records[seed].get("cleaned_prompt") != baseline_records[seed].get("cleaned_prompt")
    )
    if not changed_seeds:
        raise ValueError("combined ablation produced no sentinel prompt difference")
    sentinel = {
        "changed_seed_count": len(changed_seeds),
        "changed_seeds": changed_seeds,
    }
    sentinel["sentinel_hash"] = _hash_bytes(canonical_json_bytes(sentinel))
    return sentinel


def build_pair(
    *,
    output_dir: Path,
    artifact_root: Path,
    current_run_id: str,
    baseline_run_id: str,
    workflow: Path,
    profile: Path,
    control_seeds: Path,
    experiment_seed: int,
    iteration_id: str,
    samples: int,
    feature_ids: Sequence[str],
    overrides: Path | None = None,
    policy: Path | None = None,
) -> dict[str, Any]:
    features = _validate_features(feature_ids)
    contract = ablation_contract()
    contract_hash = _hash_bytes(canonical_json_bytes(contract))
    if policy is None:
        raise ValueError("paired generation requires an analyzer policy")
    current_dir = output_dir / current_run_id
    baseline_dir = output_dir / baseline_run_id
    _run_child(
        variant="current", output_dir=current_dir, artifact_root=artifact_root,
        workflow=workflow, profile=profile, control_seeds=control_seeds,
        experiment_seed=experiment_seed, iteration_id=iteration_id, samples=samples,
        features=features, overrides=overrides,
        policy=policy,
    )
    _run_child(
        variant="combined_ablation_baseline", output_dir=baseline_dir, artifact_root=artifact_root,
        workflow=workflow, profile=profile, control_seeds=control_seeds,
        experiment_seed=experiment_seed, iteration_id=iteration_id, samples=samples,
        features=features, overrides=overrides,
        policy=policy,
    )
    sentinel = validate_pair(current_dir, baseline_dir, contract_hash=contract_hash)
    sides = {}
    for side, path in (("current", current_dir), ("baseline", baseline_dir)):
        manifest = _load_object(path / "run-manifest.json")
        sides[side] = {
            "artifact_hashes": _validated_artifact_hashes(path, manifest),
            "records_hash": _hash_bytes((path / "records.jsonl").read_bytes()),
            "run_manifest_hash": _hash_bytes((path / "run-manifest.json").read_bytes()),
            "run_manifest_path": _repo_relative(path / "run-manifest.json"),
            "run_path": _repo_relative(path),
        }
    pair = {
        "ablation_contract": contract,
        "ablation_contract_hash": contract_hash,
        "baseline_feature_ids": features,
        "declared_variant_difference": {
            "baseline": "combined_ablation_baseline",
            "current": "current",
        },
        "iteration_id": iteration_id,
        "policy_hash": _hash_bytes(policy.read_bytes()),
        "schema_version": PAIR_SCHEMA_VERSION,
        "sentinel": sentinel,
        "sides": sides,
    }
    _atomic_write(output_dir / "ablation-pair.json", canonical_json_bytes(pair))
    return pair


def _generate(args: argparse.Namespace) -> None:
    features = _validate_features(args.features.split(","))
    contract_hash = _hash_bytes(canonical_json_bytes(ablation_contract()))
    if args.variant == "combined_ablation_baseline":
        apply_combined_baseline_ablation(features)
        behavior_features = features
    else:
        behavior_features = []
    control_value = _load_object(Path(args.control_seeds))
    controls = control_value.get("control_seeds")
    if not isinstance(controls, list):
        raise ValueError("control seed file must contain control_seeds")
    overrides = _load_object(Path(args.overrides)) if args.overrides else None
    generate_run(
        load_workflow(Path(args.workflow)), Path(args.output_dir), artifact_root=Path(args.artifact_root),
        experiment_seed=args.experiment_seed, iteration_id=args.iteration_id,
        control_seeds=[int(seed) for seed in controls], samples=args.samples,
        profile=load_profile(Path(args.profile)), overrides=overrides,
        behavior_transform=_behavior_contract(args.variant, contract_hash, behavior_features),
    )
    output_dir = Path(args.output_dir)
    analysis = write_analysis(
        output_dir / "records.jsonl", output_dir / "metrics.json", output_dir / "issues.json",
        policy_path=Path(args.policy),
    )
    _record_analysis_hashes(output_dir, analysis)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "_generate"):
        command = subparsers.add_parser(name)
        command.add_argument("--artifact-root", required=True)
        command.add_argument("--workflow", required=True)
        command.add_argument("--profile", required=True)
        command.add_argument("--control-seeds", required=True)
        command.add_argument("--experiment-seed", type=int, required=True)
        command.add_argument("--iteration-id", required=True)
        command.add_argument("--samples", type=int, default=80)
        command.add_argument("--features", required=True)
        command.add_argument("--overrides")
        command.add_argument("--policy", required=True)
    build = subparsers.choices["build"]
    build.add_argument("--output-dir", required=True)
    build.add_argument("--current-run-id", required=True)
    build.add_argument("--baseline-run-id", required=True)
    generate = subparsers.choices["_generate"]
    generate.add_argument("--output-dir", required=True)
    generate.add_argument("--variant", choices=("current", "combined_ablation_baseline"), required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "_generate":
            _generate(args)
            return 0
        pair = build_pair(
            output_dir=Path(args.output_dir), artifact_root=Path(args.artifact_root),
            current_run_id=args.current_run_id, baseline_run_id=args.baseline_run_id,
            workflow=Path(args.workflow), profile=Path(args.profile), control_seeds=Path(args.control_seeds),
            experiment_seed=args.experiment_seed, iteration_id=args.iteration_id, samples=args.samples,
            feature_ids=args.features.split(","), overrides=Path(args.overrides) if args.overrides else None,
            policy=Path(args.policy),
        )
        sys.stdout.buffer.write(canonical_json_bytes(pair))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"ablation pair generation failed: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
