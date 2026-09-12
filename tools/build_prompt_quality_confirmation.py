"""Build fixed 256-seed holdout confirmations for accepted quality objectives."""

from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.analyze_prompt_quality import analyze_records, load_policy
from tools.prompt_quality_loop import _atomic_write, build_confirmation_cohort, build_source_manifest
from tools.semantic_review_contract import SEMANTIC_COMPARISON_TO_REVIEW
from tools.workflow_prompt_runner import WorkflowValidationError, build_canonical_record, canonical_json_bytes, load_profile
from workflow_widget_validation import load_workflow


WORKFLOW = ROOT / "ComfyUI-workflow-context.json"
PROFILE = ROOT / "verification" / "fixtures" / "prompt_quality_supported_profile.json"
POLICY = ROOT / "vocab" / "data" / "prompt_quality_policy.json"
ABLATION_FEATURE_IDS = ("g004", "g005", "g006")
V150_COMPARISON_SCHEMAS = SEMANTIC_COMPARISON_TO_REVIEW
V150_COMPARISON_SCHEMA = "prompt-quality-comparison/v2"
V150_REVIEW_SCHEMA = "prompt-quality-review/v4"
V150_BUNDLE_SCHEMA = "variation-v150-confirmation-bundle/v1"
EXTRA_RUNTIME_FILES = (
    "prompts.jsonl",
    "mood_map.json",
    "templates.txt",
    "workflow_samples.json",
    "assets/calc_variations.py",
    "assets/compatibility_review.csv",
)


def ablation_contract() -> dict[str, Any]:
    return {
        "adapters": {
            "g004": "disable_location_time_context_filter",
            "g005": "disable_composition_punctuation_normalization",
            "g006": "force_single_sentence_scene_tail",
        },
        "feature_ids": list(ABLATION_FEATURE_IDS),
        "schema_version": "prompt-quality-ablation-contract/v1",
    }


def apply_combined_baseline_ablation(feature_ids: Sequence[str]) -> list[str]:
    selected = list(feature_ids)
    if selected != list(ABLATION_FEATURE_IDS):
        raise ValueError(f"combined ablation features must be exactly {','.join(ABLATION_FEATURE_IDS)} in order")
    return [_apply_baseline_ablation(feature_id) for feature_id in selected]


def _existing_seeds() -> set[int]:
    seeds: set[int] = set()
    result_root = ROOT / "assets" / "results" / "prompt_quality_loop"
    for path in result_root.rglob("records.jsonl") if result_root.exists() else ():
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, Mapping) or "run_seed" not in record or "cohort" not in record:
                    raise ValueError("canonical seed/cohort fields are required")
                seed = int(record["run_seed"])
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise WorkflowValidationError(
                    "invalid_prior_cohort_record",
                    "confirmation holdout discovery found a malformed prior record",
                    path=str(path.relative_to(ROOT)),
                    line=line_number,
                    exception_type=type(exc).__name__,
                ) from exc
            if record.get("cohort") != "confirmation":
                seeds.add(seed)
    return seeds


def _load_or_create_seeds(path: Path) -> dict[str, Any]:
    existing_seeds = _existing_seeds()
    if path.exists():
        cohort = json.loads(path.read_text(encoding="utf-8"))
    else:
        cohort = build_confirmation_cohort(sorted(existing_seeds))
        _atomic_write(path, canonical_json_bytes(cohort))
    seeds = [int(seed) for seed in cohort.get("confirmation_seeds", [])]
    if len(seeds) != 256 or len(seeds) != len(set(seeds)):
        raise ValueError("confirmation cohort must contain exactly 256 unique seeds")
    overlap = existing_seeds & set(seeds)
    if overlap:
        raise ValueError(f"confirmation seeds overlap prior iteration cohorts: {sorted(overlap)[:5]}")
    return cohort


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verification_input_entries(
    root: Path, *, verification_manifest_text: str | None = None,
) -> dict[str, str]:
    """Bind optional snapshot test support without changing legacy snapshot hashes."""
    marker = root / ".verification-inputs.json"
    if verification_manifest_text is None and not marker.exists():
        return {}
    try:
        if marker.is_symlink():
            raise ValueError("verification manifest must not be a symlink")
        if verification_manifest_text is None:
            raw = marker.read_bytes()
        else:
            if not isinstance(verification_manifest_text, str):
                raise ValueError("verification manifest text must be a string")
            raw = verification_manifest_text.encode("utf-8")
            if marker.exists() and marker.read_bytes() != raw:
                raise ValueError("verification manifest differs from the bound promotion context")
        payload = json.loads(raw)
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != "snapshot-verification-inputs/v1"
            or set(payload) != {"schema_version", "files"}
            or not isinstance(payload["files"], list)
        ):
            raise ValueError("unsupported verification input manifest")
        entries = {marker.name: hashlib.sha256(raw).hexdigest()}
        for relative in payload["files"]:
            if not isinstance(relative, str) or not relative:
                raise ValueError("verification input path must be a non-empty string")
            path = root / relative
            if Path(relative).is_absolute() or ".." in Path(relative).parts or relative in entries:
                raise ValueError("verification input path is unsafe or duplicated")
            path.resolve().relative_to(root.resolve())
            if path.is_symlink():
                raise ValueError("verification input must not be a symlink")
            entries[relative] = _sha256(path)
        return entries
    except (OSError, ValueError) as exc:
        raise WorkflowValidationError(
            "invalid_snapshot_verification_inputs", "snapshot verification inputs are missing or invalid",
            path=str(marker), reason=str(exc),
        ) from exc


def _snapshot_content_hash(root: Path, *, verification_manifest_text: str | None = None) -> str:
    entries = {entry["path"]: entry["sha256"] for entry in build_source_manifest(root)["entries"]}
    for relative in EXTRA_RUNTIME_FILES:
        path = root / relative
        if path.is_file():
            entries[relative] = _sha256(path)
    entries.update(_verification_input_entries(root, verification_manifest_text=verification_manifest_text))
    return hashlib.sha256(canonical_json_bytes(dict(sorted(entries.items())))).hexdigest()


def _path_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _import_sentinel(candidate_root: Path, forbidden_root: Path | None) -> dict[str, Any]:
    candidate_root = candidate_root.resolve()
    forbidden_root = forbidden_root.resolve() if forbidden_root else None
    imported: dict[str, str] = {}
    leaked: dict[str, str] = {}
    for name, module in sorted(sys.modules.items()):
        value = getattr(module, "__file__", None)
        if not value:
            continue
        path = Path(value).resolve()
        if _path_within(path, candidate_root):
            imported[name] = str(path)
        elif forbidden_root and _path_within(path, forbidden_root):
            leaked[name] = str(path)
    if leaked:
        raise WorkflowValidationError(
            "active_source_imported",
            "candidate confirmation imported modules from the active source root",
            modules=leaked,
        )
    payload = {
        "candidate_root": str(candidate_root),
        "forbidden_root": str(forbidden_root) if forbidden_root else None,
        "imported_candidate_modules": imported,
    }
    payload["sentinel_sha256"] = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return payload


def _sanitized_environment(candidate_root: Path) -> dict[str, str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(candidate_root.resolve())
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONSAFEPATH"] = "1"
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


def _apply_baseline_ablation(objective: str) -> str:
    if objective == "g004":
        from pipeline import location_builder

        location_builder._filter_time_options_for_context = lambda options, _context: list(options)
        return "disable_location_time_context_filter"
    if objective == "g005":
        import prompt_renderer

        prompt_renderer.normalize_composition_punctuation = prompt_renderer._normalize_prompt
        prompt_renderer._append_staging_tags = lambda result, staging_tags: (
            result.replace("{staging_tags}", staging_tags)
            if "{staging_tags}" in result
            else f"{result}, {prompt_renderer.sanitize_text(staging_tags)}"
        )
        return "disable_composition_punctuation_normalization"
    if objective == "g006":
        import prompt_renderer

        prompt_renderer.select_syntax_family = lambda _seed: "single-sentence-scene-tail"
        return "force_single_sentence_scene_tail"
    raise ValueError(f"unsupported objective: {objective}")


def _generate_records(objective: str, side: str, seed_file: Path, output: Path) -> None:
    cohort = json.loads(seed_file.read_text(encoding="utf-8"))
    if side == "baseline":
        _apply_baseline_ablation(objective)
    workflow = load_workflow(WORKFLOW)
    profile = load_profile(PROFILE)
    records = [
        build_canonical_record(
            workflow,
            int(seed),
            profile=profile,
            overrides={8: {"composition_mode": True}},
            cohort="confirmation",
        )
        for seed in cohort["confirmation_seeds"]
    ]
    _atomic_write(output, b"".join(canonical_json_bytes(record) for record in records))


def _metric(metrics: Mapping[str, Any], path: str) -> float:
    value: Any = metrics
    for component in path.split("."):
        value = value[component]
    return float(value)


def _compare(
    objective: str,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    target_config = {
        "g004": ("consistency.domains.location_action_object.hard_conflict_count", "decrease"),
        "g005": ("naturalness.punctuation_anomaly_count", "decrease"),
        "g006": ("diversity.syntax_entropy", "increase"),
    }
    target, direction = target_config[objective]
    before_target, after_target = _metric(before, target), _metric(after, target)
    signed = before_target - after_target if direction == "decrease" else after_target - before_target
    relative = signed / abs(before_target) if before_target else (1.0 if signed > 0 else 0.0)
    target_passed = relative >= 0.05 or signed >= 2
    rare_deterministic = objective == "g004" and before_target < 5 and after_target == 0
    hard_gates = policy.get("comparison", {}).get("hard_gates", {})
    if not isinstance(hard_gates, Mapping) or not hard_gates:
        raise WorkflowValidationError("invalid_policy", "confirmation requires a non-empty hard-gate mapping")
    guards = {
        f"candidate_hard_gate:{path}": _metric(after, str(path)) == float(expected)
        for path, expected in hard_gates.items()
    }
    guards.update({
        "exact_unique_non_regression": _metric(after, "diversity.exact_unique_ratio") >= _metric(before, "diversity.exact_unique_ratio"),
        "fallback_non_regression": _metric(after, "runtime.fallback_rate") <= _metric(before, "runtime.fallback_rate"),
        "context_p95_guard": _metric(after, "runtime.context_json_bytes_p95") <= _metric(before, "runtime.context_json_bytes_p95") * 1.10,
        "context_max_guard": _metric(after, "runtime.context_json_bytes_max") <= _metric(before, "runtime.context_json_bytes_max") * 1.25,
    })
    if objective == "g006":
        guards["repeated_ngram_non_regression"] = _metric(after, "naturalness.repeated_ngram_count") <= _metric(before, "naturalness.repeated_ngram_count")
    verdict = "pass" if (target_passed or rare_deterministic) and all(guards.values()) else "fail"
    return {
        "direction": direction,
        "guards": guards,
        "rare_deterministic": rare_deterministic,
        "relative_improvement": round(relative, 6),
        "signed_improvement": round(signed, 6),
        "target_after": after_target,
        "target_before": before_target,
        "target_metric": target,
        "verdict": verdict,
    }


def build_confirmation(
    *, objective: str, output_dir: Path, seed_file: Path,
    forbidden_root: Path | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cohort = _load_or_create_seeds(seed_file)
    for side in ("baseline", "candidate"):
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "_generate",
                "--objective",
                objective,
                "--side",
                side,
                "--seed-file",
                str(seed_file),
                "--output",
                str(output_dir / f"{side}-records.jsonl"),
            ],
            cwd=ROOT,
            env=_sanitized_environment(ROOT),
            check=True,
        )
    policy = load_policy(POLICY)
    sides: dict[str, Any] = {}
    for side in ("baseline", "candidate"):
        records = [
            json.loads(line)
            for line in (output_dir / f"{side}-records.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        sides[side] = analyze_records(records, policy)["metrics"]
        _atomic_write(output_dir / f"{side}-metrics.json", canonical_json_bytes(sides[side]))
    excluded_seeds = sorted(_existing_seeds())
    result = {
        "cohort_hash": cohort["cohort_hash"],
        "comparison": _compare(objective, sides["baseline"], sides["candidate"], policy),
        "excluded_seed_count": len(excluded_seeds),
        "excluded_seed_set_hash": hashlib.sha256(canonical_json_bytes(excluded_seeds)).hexdigest(),
        "feature_ablation": ablation_contract()["adapters"][objective],
        "objective": objective,
        "record_count": 256,
        "schema_version": "prompt-quality-confirmation/v1",
        "source_tree_hash": build_source_manifest()["source_tree_hash"],
    }
    if forbidden_root is not None:
        result.update({
            "candidate_snapshot_content_sha256": _snapshot_content_hash(ROOT),
            "process_isolation": _import_sentinel(ROOT, forbidden_root),
            "entrypoint": str(Path(__file__).resolve()),
            "cwd": str(ROOT.resolve()),
        })
    _atomic_write(output_dir / "confirmation.json", canonical_json_bytes(result))
    return result


def _load_json_object(path: Path, schema: str | set[str], code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowValidationError(code, "could not read bound JSON artifact", path=str(path)) from exc
    schemas = {schema} if isinstance(schema, str) else schema
    if not isinstance(value, dict) or value.get("schema_version") not in schemas:
        raise WorkflowValidationError(code, "bound artifact schema is unsupported", path=str(path))
    return value


def build_candidate_confirmation(
    *,
    candidate_root: Path,
    comparison_path: Path,
    review_path: Path,
    output_dir: Path,
    seed_file: Path,
    experiment_id: str,
    candidate_content_hash: str | None = None,
) -> dict[str, Any]:
    """Run G004/G005/G006 in isolated candidate-owned processes and bind them."""

    candidate_root = candidate_root.resolve()
    active_root = ROOT.resolve()
    if candidate_root == active_root or not (candidate_root / "tools/build_prompt_quality_confirmation.py").is_file():
        raise WorkflowValidationError("invalid_candidate_root", "candidate root must be a separate complete source tree")
    for bound in (comparison_path, review_path):
        if not bound.resolve().is_file():
            raise WorkflowValidationError("missing_confirmation_input", "bound confirmation input is missing", path=str(bound))
    comparison = _load_json_object(comparison_path, set(V150_COMPARISON_SCHEMAS), "invalid_v150_comparison")
    review = _load_json_object(review_path, set(V150_COMPARISON_SCHEMAS.values()), "invalid_v150_review")
    if review.get("schema_version") != V150_COMPARISON_SCHEMAS[comparison["schema_version"]]:
        raise WorkflowValidationError("mixed_v150_review_generation", "comparison and review schemas must belong to one generation")
    source_hash = build_source_manifest(candidate_root)["source_tree_hash"]
    content_hash = _snapshot_content_hash(candidate_root)
    expected_content_hash = candidate_content_hash or comparison.get("candidate_snapshot_content_sha256")
    comparison_hash = _sha256(comparison_path)
    review_comparison_hash = review.get("comparison_artifact_sha256", review.get("comparison_artifact_hash"))
    if (
        comparison.get("experiment_id") != experiment_id
        or comparison.get("candidate_source_tree_sha256") != source_hash
        or comparison.get("candidate_snapshot_content_sha256") != content_hash
        or expected_content_hash != content_hash
        or comparison.get("automatic_comparison_verdict", comparison.get("automatic_verdict")) != "pass"
    ):
        raise WorkflowValidationError("stale_v150_comparison", "comparison does not bind the candidate root")
    if (
        review.get("experiment_id") != experiment_id
        or review.get("candidate_source_tree_sha256") != source_hash
        or review_comparison_hash != comparison_hash
        or review.get("status", review.get("verdict")) != "pass"
        or review.get("verdict", "pass") != "pass"
    ):
        raise WorkflowValidationError("stale_v150_review", "review does not authorize candidate confirmation")

    seed_file = seed_file.resolve()
    if _path_within(seed_file, active_root) or _path_within(seed_file, candidate_root):
        raise WorkflowValidationError("seed_fixture_inside_source", "confirmation seed fixture must be outside both source roots")
    seed_file.parent.mkdir(parents=True, exist_ok=True)
    # Create the cohort once before any objective starts, then make it read-only.
    if not seed_file.exists():
        cohort = build_confirmation_cohort([])
        _atomic_write(seed_file, canonical_json_bytes(cohort))
        seed_file.chmod(0o444)
    cohort = json.loads(seed_file.read_text(encoding="utf-8"))
    seeds = cohort.get("confirmation_seeds", [])
    if len(seeds) != 256 or len(set(seeds)) != 256:
        raise WorkflowValidationError("invalid_confirmation_cohort", "shared cohort must contain 256 unique seeds")
    cohort_file_hash = _sha256(seed_file)

    output_dir.mkdir(parents=True, exist_ok=True)
    objective_bindings: dict[str, Any] = {}
    entrypoint = candidate_root / "tools/build_prompt_quality_confirmation.py"
    for objective in ABLATION_FEATURE_IDS:
        objective_dir = output_dir / objective
        command = [
            sys.executable, str(entrypoint), "candidate-objective",
            "--objective", objective,
            "--output-dir", str(objective_dir),
            "--seed-file", str(seed_file),
            "--forbidden-root", str(active_root),
        ]
        completed = subprocess.run(
            command,
            cwd=candidate_root,
            env=_sanitized_environment(candidate_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if completed.returncode != 0:
            raise WorkflowValidationError(
                "candidate_confirmation_failed", "candidate objective process failed",
                objective=objective, exit_code=completed.returncode, stderr=completed.stderr[-4000:],
            )
        artifact_path = objective_dir / "confirmation.json"
        artifact = _load_json_object(artifact_path, "prompt-quality-confirmation/v1", "invalid_confirmation_artifact")
        isolation = artifact.get("process_isolation")
        if (
            artifact.get("objective") != objective
            or artifact.get("record_count") != 256
            or artifact.get("cohort_hash") != cohort.get("cohort_hash")
            or artifact.get("source_tree_hash") != source_hash
            or artifact.get("candidate_snapshot_content_sha256") != content_hash
            or artifact.get("cwd") != str(candidate_root)
            or artifact.get("entrypoint") != str(entrypoint)
            or not isinstance(isolation, Mapping)
            or isolation.get("candidate_root") != str(candidate_root)
            or artifact.get("comparison", {}).get("verdict") != "pass"
        ):
            raise WorkflowValidationError("invalid_candidate_confirmation", "objective evidence is stale or mixed", objective=objective)
        objective_bindings[objective] = {
            "artifact_path": str(artifact_path.resolve()),
            "artifact_sha256": _sha256(artifact_path),
            "records": {
                side: _sha256(objective_dir / f"{side}-records.jsonl") for side in ("baseline", "candidate")
            },
            "metrics": {
                side: _sha256(objective_dir / f"{side}-metrics.json") for side in ("baseline", "candidate")
            },
            "entrypoint": str(entrypoint),
            "cwd": str(candidate_root),
            "exit_code": completed.returncode,
            "import_sentinel_sha256": isolation.get("sentinel_sha256"),
            "verdict": "pass",
        }
        if _sha256(seed_file) != cohort_file_hash:
            raise WorkflowValidationError("confirmation_cohort_mutated", "seed fixture changed during confirmation")
        if build_source_manifest(candidate_root)["source_tree_hash"] != source_hash or _snapshot_content_hash(candidate_root) != content_hash:
            raise WorkflowValidationError("candidate_changed_during_confirmation", "candidate root changed during confirmation")

    bundle = {
        "schema_version": V150_BUNDLE_SCHEMA,
        "status": "pass",
        "experiment_id": experiment_id,
        "candidate_root": str(candidate_root),
        "candidate_root_identity_sha256": hashlib.sha256(str(candidate_root).encode("utf-8")).hexdigest(),
        "candidate_source_tree_sha256": source_hash,
        "candidate_snapshot_content_sha256": content_hash,
        "comparison_artifact_path": str(comparison_path.resolve()),
        "comparison_artifact_sha256": comparison_hash,
        "review_artifact_path": str(review_path.resolve()),
        "review_artifact_sha256": _sha256(review_path),
        "cohort_path": str(seed_file),
        "cohort_file_sha256": cohort_file_hash,
        "cohort_hash": cohort.get("cohort_hash"),
        "record_count": 256,
        "objectives": objective_bindings,
    }
    _atomic_write(output_dir / "confirmation-bundle.json", canonical_json_bytes(bundle))
    return bundle


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    generate = subparsers.add_parser("_generate")
    generate.add_argument("--objective", required=True)
    generate.add_argument("--side", required=True)
    generate.add_argument("--seed-file", required=True)
    generate.add_argument("--output", required=True)
    candidate = subparsers.add_parser("candidate-objective")
    candidate.add_argument("--objective", choices=ABLATION_FEATURE_IDS, required=True)
    candidate.add_argument("--output-dir", type=Path, required=True)
    candidate.add_argument("--seed-file", type=Path, required=True)
    candidate.add_argument("--forbidden-root", type=Path, required=True)
    bundle = subparsers.add_parser("candidate-bundle")
    bundle.add_argument("--candidate-root", type=Path, required=True)
    bundle.add_argument("--comparison", type=Path, required=True)
    bundle.add_argument("--review", type=Path, required=True)
    bundle.add_argument("--output-dir", type=Path, required=True)
    bundle.add_argument("--seed-file", type=Path, required=True)
    bundle.add_argument("--experiment-id", required=True)
    bundle.add_argument("--candidate-content-hash")
    args = parser.parse_args()
    if args.command == "_generate":
        _generate_records(args.objective, args.side, Path(args.seed_file), Path(args.output))
        return 0
    if args.command == "candidate-objective":
        result = build_confirmation(
            objective=args.objective,
            output_dir=args.output_dir,
            seed_file=args.seed_file,
            forbidden_root=args.forbidden_root,
        )
        sys.stdout.buffer.write(canonical_json_bytes(result))
        return 0
    if args.command == "candidate-bundle":
        result = build_candidate_confirmation(
            candidate_root=args.candidate_root,
            comparison_path=args.comparison,
            review_path=args.review,
            output_dir=args.output_dir,
            seed_file=args.seed_file,
            experiment_id=args.experiment_id,
            candidate_content_hash=args.candidate_content_hash,
        )
        sys.stdout.buffer.write(canonical_json_bytes(result))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
