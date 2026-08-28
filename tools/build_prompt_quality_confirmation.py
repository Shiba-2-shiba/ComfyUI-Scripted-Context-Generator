"""Build fixed 256-seed holdout confirmations for accepted quality objectives."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.analyze_prompt_quality import analyze_records, load_policy
from tools.prompt_quality_loop import _atomic_write, build_confirmation_cohort, build_source_manifest
from tools.workflow_prompt_runner import WorkflowValidationError, build_canonical_record, canonical_json_bytes, load_profile
from workflow_widget_validation import load_workflow


WORKFLOW = ROOT / "ComfyUI-workflow-context.json"
PROFILE = ROOT / "verification" / "fixtures" / "prompt_quality_supported_profile.json"
POLICY = ROOT / "vocab" / "data" / "prompt_quality_policy.json"


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
    if path.exists():
        cohort = json.loads(path.read_text(encoding="utf-8"))
    else:
        cohort = build_confirmation_cohort(sorted(_existing_seeds()))
        _atomic_write(path, canonical_json_bytes(cohort))
    seeds = [int(seed) for seed in cohort.get("confirmation_seeds", [])]
    if len(seeds) != 256 or len(seeds) != len(set(seeds)):
        raise ValueError("confirmation cohort must contain exactly 256 unique seeds")
    overlap = _existing_seeds() & set(seeds)
    if overlap:
        raise ValueError(f"confirmation seeds overlap prior iteration cohorts: {sorted(overlap)[:5]}")
    return cohort


def _apply_baseline_ablation(objective: str) -> str:
    if objective == "g004":
        from pipeline import location_builder

        location_builder._filter_time_options_for_context = lambda options, _context: list(options)
        return "disable_location_time_context_filter"
    if objective == "g005":
        import prompt_renderer

        prompt_renderer.normalize_composition_punctuation = prompt_renderer._normalize_prompt
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


def build_confirmation(*, objective: str, output_dir: Path, seed_file: Path) -> dict[str, Any]:
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
        "excluded_seed_set_hash": __import__("hashlib").sha256(canonical_json_bytes(excluded_seeds)).hexdigest(),
        "feature_ablation": _apply_baseline_ablation(objective),
        "objective": objective,
        "record_count": 256,
        "schema_version": "prompt-quality-confirmation/v1",
        "source_tree_hash": build_source_manifest()["source_tree_hash"],
    }
    _atomic_write(output_dir / "confirmation.json", canonical_json_bytes(result))
    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    generate = subparsers.add_parser("_generate")
    generate.add_argument("--objective", required=True)
    generate.add_argument("--side", required=True)
    generate.add_argument("--seed-file", required=True)
    generate.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "_generate":
        _generate_records(args.objective, args.side, Path(args.seed_file), Path(args.output))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
