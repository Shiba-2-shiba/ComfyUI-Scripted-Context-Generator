"""Deterministic, seed-paired prompt-quality comparison and verdicts.

This module is deliberately read-only with respect to product source.  Callers
may write the returned canonical artifact beneath their experiment root, but a
promotion verdict never applies a patch or invokes git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


COMPARISON_SCHEMA_VERSION = "prompt-quality-comparison/v1"
PROMOTION_SCHEMA_VERSION = "prompt-quality-promotion-verdict/v1"
REQUIRED_RECORD_COUNT = 80
REQUIRED_CONTROL_COUNT = 64
REQUIRED_EXPLORATION_COUNT = 16
REQUIRED_VERIFICATION_GATES = {
    "action_pools", "blind_review", "browser", "compatibility_review",
    "data_validation", "frontend", "full_flow", "prompt_quality_confirmation",
    "python_tests", "target_comparison", "widgets",
}
MIN_FULL_REGRESSION_TESTS = 505


def _load_object(value: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    loaded = json.loads(Path(value).read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise WorkflowValidationError("invalid_comparison_input", "comparison input must be a JSON object")
    return loaded


def _load_records(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "records.jsonl"
    try:
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowValidationError(
            "invalid_records_artifact", "could not read canonical records", path=str(path), exception_type=type(exc).__name__
        ) from exc
    if not all(isinstance(record, dict) for record in records):
        raise WorkflowValidationError("invalid_records_artifact", "every record must be a JSON object", path=str(path))
    return records


def _analysis_metrics(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "metrics.json"
    try:
        return _load_object(path)
    except OSError as exc:
        raise WorkflowValidationError("missing_metrics_artifact", "run metrics are missing", path=str(path)) from exc


def _manifest(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "run-manifest.json"
    try:
        return _load_object(path)
    except OSError as exc:
        raise WorkflowValidationError("missing_run_manifest", "run manifest is missing", path=str(path)) from exc


def _numeric_leaves(value: Any, prefix: str = "") -> dict[str, float]:
    leaves: dict[str, float] = {}
    if isinstance(value, Mapping):
        for key, child in sorted(value.items()):
            path = f"{prefix}.{key}" if prefix else str(key)
            leaves.update(_numeric_leaves(child, path))
    elif isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
        leaves[prefix] = float(value)
    return leaves


def _metric_value(metrics: Mapping[str, Any], path: str) -> float:
    current: Any = metrics
    for component in path.split("."):
        if not isinstance(current, Mapping) or component not in current:
            raise WorkflowValidationError("missing_metric", "configured metric is absent", metric=path)
        current = current[component]
    if not isinstance(current, (int, float)) or isinstance(current, bool) or not math.isfinite(float(current)):
        raise WorkflowValidationError("invalid_metric", "configured metric must be finite and numeric", metric=path)
    return float(current)


def _paired_records(before: Sequence[Mapping[str, Any]], after: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    def indexed(records: Sequence[Mapping[str, Any]], side: str) -> dict[int, Mapping[str, Any]]:
        result: dict[int, Mapping[str, Any]] = {}
        for record in records:
            if "run_seed" not in record:
                raise WorkflowValidationError("missing_seed", "record has no run_seed", side=side)
            seed = int(record["run_seed"])
            if seed in result:
                raise WorkflowValidationError("duplicate_seed", "run contains duplicate seeds", seed=seed, side=side)
            result[seed] = record
        return result

    before_by_seed = indexed(before, "before")
    after_by_seed = indexed(after, "after")
    if set(before_by_seed) != set(after_by_seed):
        raise WorkflowValidationError(
            "cohort_mismatch",
            "before and after must contain the same seed cohort",
            before_only=sorted(set(before_by_seed) - set(after_by_seed)),
            after_only=sorted(set(after_by_seed) - set(before_by_seed)),
        )
    if len(before_by_seed) < REQUIRED_RECORD_COUNT:
        raise WorkflowValidationError(
            "insufficient_promotion_cohort",
            "formal comparison requires at least 80 paired records",
            actual=len(before_by_seed),
            required=REQUIRED_RECORD_COUNT,
        )
    cohort_counts = {"control": 0, "exploration": 0}
    for seed in sorted(before_by_seed):
        before_cohort = before_by_seed[seed].get("cohort")
        after_cohort = after_by_seed[seed].get("cohort")
        if before_cohort != after_cohort:
            raise WorkflowValidationError("cohort_mismatch", "paired seed changed cohort", seed=seed)
        if before_cohort in cohort_counts:
            cohort_counts[str(before_cohort)] += 1
    if cohort_counts != {"control": REQUIRED_CONTROL_COUNT, "exploration": REQUIRED_EXPLORATION_COUNT}:
        raise WorkflowValidationError(
            "cohort_drift", "formal paired cohort must contain 64 control and 16 exploration records", **cohort_counts
        )
    return {"paired_count": len(before_by_seed), **{f"{key}_count": value for key, value in cohort_counts.items()}}


def _compatibility(before: Mapping[str, Any], after: Mapping[str, Any], before_metrics: Mapping[str, Any], after_metrics: Mapping[str, Any]) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    for key in ("cohort_hash", "workflow_hash", "effective_workflow_hash", "profile_hash"):
        if key in before or key in after:
            checks[key] = bool(before.get(key)) and before.get(key) == after.get(key)
    for key in ("analyzer_version", "policy_version"):
        if key in before_metrics or key in after_metrics:
            checks[key] = bool(before_metrics.get(key)) and before_metrics.get(key) == after_metrics.get(key)
    failed = sorted(key for key, passed in checks.items() if not passed)
    if failed:
        raise WorkflowValidationError(
            "comparison_contract_mismatch",
            "incumbent and candidate require a shared cohort, workflow, profile, policy and analyzer contract",
            mismatched_fields=failed,
        )
    return {"checks": checks, "status": "pass"}


def _metric_config(policy: Mapping[str, Any], experiment: Mapping[str, Any]) -> tuple[str, list[str], dict[str, Any]]:
    target = str(experiment.get("target_metric", ""))
    if not target:
        raise WorkflowValidationError("missing_target_metric", "experiment must lock exactly one target metric")
    guards = experiment.get("guard_metrics", [])
    if not isinstance(guards, list) or not all(isinstance(item, str) for item in guards):
        raise WorkflowValidationError("invalid_guard_metrics", "guard_metrics must be an array of metric paths")
    catalog = policy.get("metrics", {})
    if catalog and not isinstance(catalog, Mapping):
        raise WorkflowValidationError("invalid_policy", "policy metrics must be an object")
    target_policy = dict(catalog.get(target, {})) if isinstance(catalog, Mapping) else {}
    target_policy.update(experiment.get("target_policy", {}))
    return target, list(guards), target_policy


def compare_runs(
    before_dir: str | Path,
    after_dir: str | Path,
    *,
    policy: Mapping[str, Any] | str | Path,
    experiment: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Compare two analyzer-populated run directories using a locked experiment."""

    before_path = Path(before_dir)
    after_path = Path(after_dir)
    if isinstance(policy, Mapping):
        policy_value = dict(policy)
    else:
        from tools.analyze_prompt_quality import load_policy

        policy_value = load_policy(policy)
    experiment_value = _load_object(experiment)
    qualitative_targets = experiment_value.get("target_qualitative_dimensions")
    qualitative_guards = experiment_value.get("guard_qualitative_dimensions")
    qualitative_dimensions = {
        "protagonist_clarity", "consistency", "naturalness",
        "redundancy", "diversity", "image_prompt_suitability",
    }
    if (
        not isinstance(qualitative_targets, list)
        or not isinstance(qualitative_guards, list)
        or set(qualitative_targets) | set(qualitative_guards) != qualitative_dimensions
        or set(qualitative_targets) & set(qualitative_guards)
    ):
        raise WorkflowValidationError(
            "invalid_qualitative_scope", "experiment must lock a complete disjoint qualitative review scope"
        )
    qualitative_scope_hash = hashlib.sha256(canonical_json_bytes({
        "guard_qualitative_dimensions": qualitative_guards,
        "target_qualitative_dimensions": qualitative_targets,
    })).hexdigest()
    before_manifest, after_manifest = _manifest(before_path), _manifest(after_path)
    artifact_before_metrics, artifact_after_metrics = _analysis_metrics(before_path), _analysis_metrics(after_path)
    before_records, after_records = _load_records(before_path), _load_records(after_path)
    paired = _paired_records(before_records, after_records)
    compatibility = _compatibility(before_manifest, after_manifest, artifact_before_metrics, artifact_after_metrics)
    selected_policy_version = policy_value.get("policy_version", policy_value.get("version"))
    if selected_policy_version and artifact_before_metrics.get("policy_version") != selected_policy_version:
        raise WorkflowValidationError(
            "comparison_contract_mismatch", "run metrics were produced with another policy version",
            expected_policy_version=selected_policy_version,
            actual_policy_version=artifact_before_metrics.get("policy_version"),
        )

    # Formal promotion is decided on the fixed control64 cohort.  The paired80
    # artifacts remain available for issue discovery, but must not dilute the
    # incumbent/candidate target effect with rotating exploration observations.
    scope = str(experiment_value.get("metric_scope", "control64"))
    if scope not in {"control64", "paired80"}:
        raise WorkflowValidationError("unsupported_metric_scope", "comparison supports control64 or paired80", scope=scope)
    selected_before = before_records if scope == "paired80" else [item for item in before_records if item.get("cohort") == "control"]
    selected_after = after_records if scope == "paired80" else [item for item in after_records if item.get("cohort") == "control"]
    can_reanalyze = all("cleaned_prompt" in item and "context" in item for item in selected_before + selected_after)
    if can_reanalyze:
        from tools.analyze_prompt_quality import analyze_records

        before_metrics = analyze_records(selected_before, policy_value)["metrics"]
        after_metrics = analyze_records(selected_after, policy_value)["metrics"]
    else:
        # Synthetic precision fixtures may intentionally contain only paired
        # seed/cohort records and precomputed analyzer metrics.
        before_metrics, after_metrics = artifact_before_metrics, artifact_after_metrics

    target, guards, target_policy = _metric_config(policy_value, experiment_value)
    before_target = _metric_value(before_metrics, target)
    after_target = _metric_value(after_metrics, target)
    target_direction = target_policy.get("direction", experiment_value.get("direction", "decrease"))
    if target_direction not in {"increase", "decrease"}:
        raise WorkflowValidationError("invalid_policy", "metric direction must be increase or decrease", metric=target)
    signed_change = (before_target - after_target) if target_direction == "decrease" else (after_target - before_target)
    relative_change = signed_change / abs(before_target) if before_target else (1.0 if signed_change > 0 else 0.0)
    metric_kind = str(target_policy.get("kind", experiment_value.get("target_kind", "behavior")))
    effects = policy_value.get("comparison", {}).get("effect_sizes", {})
    required_absolute = float(target_policy.get("min_absolute", effects.get("defect_count_min_reduction", 2.0) if metric_kind == "behavior" else 0.0))
    required_relative = float(target_policy.get(
        "min_relative",
        effects.get("diversity_min_relative_improvement", 0.05)
        if metric_kind == "diversity"
        else effects.get("defect_rate_min_relative_improvement", 0.10),
    ))
    absolute_passed = required_absolute > 0 and round(signed_change, 12) >= round(required_absolute, 12)
    relative_passed = required_relative > 0 and round(relative_change, 12) >= round(required_relative, 12)
    target_passed = absolute_passed or relative_passed
    if required_absolute <= 0 and required_relative <= 0:
        target_passed = signed_change > 0

    max_guard_regression = float(policy_value.get(
        "guard_max_absolute_regression",
        policy_value.get("comparison", {}).get("guards", {}).get("max_absolute_rate_regression", 0.02),
    ))
    guard_results = []
    metric_catalog = policy_value.get("metrics", {})
    if not isinstance(metric_catalog, Mapping):
        raise WorkflowValidationError("invalid_policy", "policy metrics must be an object")
    for metric in guards:
        before_value = _metric_value(before_metrics, metric)
        after_value = _metric_value(after_metrics, metric)
        if metric in {"runtime.context_json_bytes_p95", "runtime.context_bytes_p95"}:
            ratio = float(policy_value.get("context_size", {}).get("p95_max_ratio", 1.10))
            limit = before_value * ratio
            guard_results.append({
                "after": after_value,
                "before": before_value,
                "metric": metric,
                "passed": after_value <= limit,
                "regression": round(max(0.0, after_value - before_value), 12),
                "threshold": limit,
            })
            continue
        if metric in {"runtime.context_json_bytes_max", "runtime.context_bytes_max"}:
            ratio = float(policy_value.get("context_size", {}).get("max_max_ratio", 1.25))
            limit = before_value * ratio
            guard_results.append({
                "after": after_value,
                "before": before_value,
                "metric": metric,
                "passed": after_value <= limit,
                "regression": round(max(0.0, after_value - before_value), 12),
                "threshold": limit,
            })
            continue
        config = metric_catalog.get(metric)
        if not isinstance(config, Mapping) or config.get("direction") not in {"increase", "decrease"}:
            raise WorkflowValidationError(
                "missing_metric_policy",
                "every guard metric requires an explicit increase/decrease policy direction",
                metric=metric,
            )
        guard_direction = config.get("direction", "increase")
        regression = (before_value - after_value) if guard_direction == "increase" else (after_value - before_value)
        threshold = float(config.get("max_guard_regression", max_guard_regression))
        policy_floor = config.get("minimum")
        policy_ceiling = config.get("maximum")
        # Analyzer metrics have fixed decimal precision; compare at the same
        # stable precision so an inclusive 2pp boundary is not lost to binary
        # floating-point representation (for example 1.00 - 0.98).
        passed = round(regression, 12) <= round(threshold, 12)
        if policy_floor is not None:
            passed = passed and after_value >= float(policy_floor)
        if policy_ceiling is not None:
            passed = passed and after_value <= float(policy_ceiling)
        guard_results.append({
            "after": after_value,
            "before": before_value,
            "metric": metric,
            "passed": passed,
            "regression": round(regression, 12),
            "threshold": threshold,
        })

    hard_gate_contract = policy_value.get("comparison", {}).get("hard_gates", policy_value.get("hard_gate_metrics", {}))
    if isinstance(hard_gate_contract, list):
        hard_gate_contract = {str(metric): 0 for metric in hard_gate_contract}
    hard_gate_failures = []
    for metric, expected in hard_gate_contract.items():
        value = _metric_value(after_metrics, str(metric))
        if value != float(expected):
            hard_gate_failures.append({"expected": float(expected), "metric": str(metric), "value": value})
    non_regression = policy_value.get("non_regression_metrics", {
        "diversity.exact_unique_ratio": "increase",
        "runtime.fallback_rate": "decrease",
    })
    if isinstance(non_regression, list):
        non_regression = {str(metric): "decrease" for metric in non_regression}
    for metric, metric_direction in non_regression.items():
        try:
            before_value = _metric_value(before_metrics, str(metric))
            after_value = _metric_value(after_metrics, str(metric))
        except WorkflowValidationError as exc:
            if exc.code == "missing_metric":
                continue
            raise
        regressed = after_value < before_value if metric_direction == "increase" else after_value > before_value
        if regressed:
            hard_gate_failures.append({"metric": str(metric), "before": before_value, "after": after_value})

    context_policy = policy_value.get("context_size", {})
    p95_ratio = float(context_policy.get("p95_max_ratio", 1.10))
    max_ratio = float(context_policy.get("max_max_ratio", 1.25))
    p95_path = "runtime.context_json_bytes_p95" if "context_json_bytes_p95" in before_metrics.get("runtime", {}) else "runtime.context_bytes_p95"
    max_path = "runtime.context_json_bytes_max" if "context_json_bytes_max" in before_metrics.get("runtime", {}) else "runtime.context_bytes_max"
    before_p95 = _metric_value(before_metrics, p95_path)
    after_p95 = _metric_value(after_metrics, p95_path)
    before_max = _metric_value(before_metrics, max_path)
    after_max = _metric_value(after_metrics, max_path)
    if before_p95 and after_p95 > before_p95 * p95_ratio:
        hard_gate_failures.append({"metric": p95_path, "limit": before_p95 * p95_ratio, "value": after_p95})
    if before_max and after_max > before_max * max_ratio:
        hard_gate_failures.append({"metric": max_path, "limit": before_max * max_ratio, "value": after_max})

    all_before = _numeric_leaves(before_metrics)
    all_after = _numeric_leaves(after_metrics)
    deltas = {
        key: round(all_after[key] - all_before[key], 12)
        for key in sorted(set(all_before) & set(all_after))
        if all_after[key] != all_before[key]
    }
    automatic_pass = target_passed and not hard_gate_failures and all(item["passed"] for item in guard_results)
    return {
        "automatic_verdict": "pass" if automatic_pass else "reject",
        "compatibility": compatibility,
        "deltas": deltas,
        "experiment_id": experiment_value.get("experiment_id"),
        "guard_metrics": guard_results,
        "hard_gate_failures": hard_gate_failures,
        "paired_cohort": paired,
        "metric_scope": scope,
        "policy_version": policy_value.get("policy_version", policy_value.get("version")),
        "qualitative_scope_hash": qualitative_scope_hash,
        "record_artifact_hashes": {
            "after": __import__("hashlib").sha256((after_path / "records.jsonl").read_bytes()).hexdigest(),
            "before": __import__("hashlib").sha256((before_path / "records.jsonl").read_bytes()).hexdigest(),
        },
        "review_contract_hash": hashlib.sha256(canonical_json_bytes(policy_value.get("review", {}))).hexdigest(),
        "source_tree_hashes": {
            "after": after_manifest.get("source_tree_hash"),
            "before": before_manifest.get("source_tree_hash"),
        },
        "cohort_hashes": {
            "after": after_manifest.get("cohort_hash"),
            "before": before_manifest.get("cohort_hash"),
        },
        "schema_version": COMPARISON_SCHEMA_VERSION,
        "target_metric": {
            "after": after_target,
            "before": before_target,
            "direction": target_direction,
            "kind": metric_kind,
            "metric": target,
            "passed": target_passed,
            "relative_improvement": round(relative_change, 12),
            "signed_improvement": round(signed_change, 12),
        },
    }


def _review_failures(
    review: Mapping[str, Any],
    expected_record_hashes: Mapping[str, Any] | None = None,
    expected_source_hashes: Mapping[str, Any] | None = None,
    expected_cohort_hashes: Mapping[str, Any] | None = None,
    expected_review_contract_hash: str | None = None,
    expected_qualitative_scope_hash: str | None = None,
    expected_experiment_id: str | None = None,
) -> list[str]:
    if not review:
        return ["review_missing"]
    failures: list[str] = []
    if review.get("schema_version") != "prompt-quality-review/v1":
        failures.append("review_schema_invalid")
    if review.get("pair_count_per_lane") != 20:
        failures.append("review_pair_count_invalid")
    reviewers = review.get("reviewers", [])
    reviewer_ids = [item.get("reviewer_id") for item in reviewers if isinstance(item, Mapping)] if isinstance(reviewers, list) else []
    if len(reviewer_ids) != 2 or None in reviewer_ids or len(set(reviewer_ids)) != 2:
        failures.append("reviewer_identity_not_independent")
    for key in ("assignment_key_hash",):
        value = review.get(key)
        if not isinstance(value, str) or len(value) != 64:
            failures.append(f"{key}_invalid")
    for key in ("lane_input_hashes", "lane_result_hashes"):
        values = review.get(key)
        if not isinstance(values, Mapping) or set(values) != {"lane-1", "lane-2"} or not all(
            isinstance(value, str) and len(value) == 64 for value in values.values()
        ):
            failures.append(f"{key}_invalid")
    if review.get("hash_validation") != "pass":
        failures.append("review_hash_validation_failed")
    if review.get("review_contract_hash") != expected_review_contract_hash:
        failures.append("review_contract_hash_mismatch")
    if review.get("qualitative_scope_hash") != expected_qualitative_scope_hash:
        failures.append("review_qualitative_scope_mismatch")
    if not expected_experiment_id or review.get("experiment_id") != expected_experiment_id:
        failures.append("review_experiment_id_mismatch")
    record_hashes = review.get("reviewed_record_hashes")
    if not isinstance(record_hashes, Mapping) or set(record_hashes) != {"before", "after"} or not all(
        isinstance(value, str) and len(value) == 64 for value in record_hashes.values()
    ):
        failures.append("reviewed_record_hashes_invalid")
    elif expected_record_hashes is None or dict(record_hashes) != dict(expected_record_hashes):
        failures.append("reviewed_record_hashes_mismatch")
    provenance = review.get("reviewed_run_provenance")
    if not isinstance(provenance, Mapping) or set(provenance) != {"before", "after"}:
        failures.append("reviewed_run_provenance_invalid")
    else:
        source_hashes = {side: provenance.get(side, {}).get("source_tree_hash") for side in ("before", "after")}
        cohort_hashes = {side: provenance.get(side, {}).get("cohort_hash") for side in ("before", "after")}
        if expected_source_hashes is None or source_hashes != dict(expected_source_hashes):
            failures.append("reviewed_source_hashes_mismatch")
        if expected_cohort_hashes is None or cohort_hashes != dict(expected_cohort_hashes):
            failures.append("reviewed_cohort_hashes_mismatch")
    if review.get("candidate_hard_defect_count") != 0:
        failures.append("candidate_hard_defect")
    dimensions = review.get("dimensions", {})
    required_dimensions = {
        "protagonist_clarity", "consistency", "naturalness",
        "redundancy", "diversity", "image_prompt_suitability",
    }
    if not isinstance(dimensions, Mapping) or set(dimensions) != required_dimensions:
        failures.append("review_dimensions_invalid")
    else:
        targets = set(review.get("target_qualitative_dimensions", []))
        guards = set(review.get("guard_qualitative_dimensions", []))
        if targets | guards != required_dimensions or targets & guards:
            failures.append("review_scope_invalid")
        for dimension, result in dimensions.items():
            if not isinstance(result, Mapping) or result.get("passed") is not True:
                failures.append(f"review_dimension_failed:{dimension}")
            if dimension in targets and int(result.get("valid_votes", 0)) < 36:
                failures.append(f"review_votes_insufficient:{dimension}")
    raw_failures = review.get("failures", [])
    if raw_failures:
        failures.append("qualitative_review_failed")
    if failures:
        return sorted(set(failures))
    if review.get("status") == "pass" and review.get("verdict") == "pass":
        return []
    return ["qualitative_review_failed"]


def _review_artifact_binding_failures(review_path: Path, review: Mapping[str, Any]) -> list[str]:
    review_dir = review_path.resolve().parent
    key_path = review_dir / "assignment-key.json"
    if not key_path.is_file():
        return ["review_assignment_key_missing"]
    try:
        key = json.loads(key_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ["review_assignment_key_invalid"]
    failures: list[str] = []
    if hashlib.sha256(key_path.read_bytes()).hexdigest() != review.get("assignment_key_hash"):
        failures.append("review_assignment_key_hash_mismatch")
    experiment_id = str(key.get("experiment_id", ""))
    key_lanes = key.get("lanes", []) if isinstance(key.get("lanes"), list) else []
    if key.get("schema_version") != "prompt-quality-review-assignment-key/v1" or {
        str(item.get("lane_id", "")) for item in key_lanes if isinstance(item, Mapping)
    } != {"lane-1", "lane-2"} or len(key_lanes) != 2:
        failures.append("review_assignment_lane_set_invalid")
    for lane_key in key_lanes:
        lane_id = str(lane_key.get("lane_id", ""))
        lane_path = review_dir / f"{lane_id}.json"
        result_path = review_dir / f"{lane_id}-result.json"
        if not lane_path.is_file() or not result_path.is_file():
            failures.append(f"review_lane_artifact_missing:{lane_id}")
            continue
        lane_hash = hashlib.sha256(lane_path.read_bytes()).hexdigest()
        result_hash = hashlib.sha256(result_path.read_bytes()).hexdigest()
        if lane_key.get("lane_artifact_hash") != lane_hash or review.get("lane_input_hashes", {}).get(lane_id) != lane_hash:
            failures.append(f"review_lane_hash_mismatch:{lane_id}")
        if review.get("lane_result_hashes", {}).get(lane_id) != result_hash:
            failures.append(f"review_lane_result_hash_mismatch:{lane_id}")
        try:
            lane = json.loads(lane_path.read_text(encoding="utf-8"))
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            failures.append(f"review_lane_json_invalid:{lane_id}")
            continue
        if result.get("input_hash") != lane_hash:
            failures.append(f"review_result_input_hash_mismatch:{lane_id}")
        pairs = {str(item.get("pair_id")): int(item.get("run_seed")) for item in lane.get("pairs", [])}
        assignments = lane_key.get("assignments", []) if isinstance(lane_key.get("assignments"), list) else []
        for assignment in assignments:
            pair_id = str(assignment.get("pair_id", ""))
            seed = int(assignment.get("run_seed", -1))
            digest = hashlib.sha256(f"{experiment_id}:{lane_id}:{seed}".encode()).digest()
            expected_candidate = "A" if int.from_bytes(digest[:8], "big") % 2 == 0 else "B"
            if (
                pairs.get(pair_id) != seed
                or assignment.get("candidate_side") != expected_candidate
                or assignment.get("incumbent_side") != ("B" if expected_candidate == "A" else "A")
            ):
                failures.append(f"review_assignment_drift:{lane_id}:{pair_id}")
    paths = key.get("reviewed_record_paths")
    hashes = key.get("reviewed_record_hashes")
    provenance = key.get("reviewed_run_provenance")
    bound_records: dict[str, dict[int, str]] = {}
    if not all(isinstance(value, Mapping) and set(value) == {"before", "after"} for value in (paths, hashes, provenance)):
        failures.append("review_record_binding_invalid")
    else:
        for side in ("before", "after"):
            relative = Path(str(paths[side]))
            if relative.is_absolute() or ".." in relative.parts:
                failures.append(f"review_record_path_invalid:{side}")
                continue
            record_path = (ROOT / relative).resolve()
            try:
                record_path.relative_to(ROOT.resolve())
            except ValueError:
                failures.append(f"review_record_path_invalid:{side}")
                continue
            if not record_path.is_file() or hashlib.sha256(record_path.read_bytes()).hexdigest() != hashes[side]:
                failures.append(f"review_record_hash_mismatch:{side}")
            else:
                try:
                    records = [json.loads(line) for line in record_path.read_text(encoding="utf-8").splitlines() if line.strip()]
                    bound_records[side] = {
                        int(item["run_seed"]): str(item["cleaned_prompt"])
                        for item in records
                    }
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    failures.append(f"review_record_content_invalid:{side}")
            if review.get("reviewed_record_hashes", {}).get(side) != hashes[side]:
                failures.append(f"review_aggregate_record_hash_mismatch:{side}")
            manifest = None
            for name in ("run-manifest.json", "confirmation.json"):
                candidate = record_path.parent / name
                if candidate.is_file():
                    manifest = json.loads(candidate.read_text(encoding="utf-8"))
                    break
            expected = provenance[side]
            if manifest is None or any(manifest.get(field) != expected.get(field) for field in ("source_tree_hash", "cohort_hash")):
                failures.append(f"review_record_provenance_mismatch:{side}")
            if review.get("reviewed_run_provenance", {}).get(side) != expected:
                failures.append(f"review_aggregate_provenance_mismatch:{side}")
    if set(bound_records) == {"before", "after"}:
        selection = key.get("selection", {})
        selected_seeds = {
            int(seed)
            for values in selection.values()
            if isinstance(values, list)
            for seed in values
        } if isinstance(selection, Mapping) else set()
        for lane_key in key_lanes:
            lane_id = str(lane_key.get("lane_id", ""))
            lane_path = review_dir / f"{lane_id}.json"
            if not lane_path.is_file():
                continue
            lane = json.loads(lane_path.read_text(encoding="utf-8"))
            pairs = {str(item["pair_id"]): item for item in lane.get("pairs", [])}
            assignments = {str(item["pair_id"]): item for item in lane_key.get("assignments", [])}
            lane_seeds = {int(item["run_seed"]) for item in pairs.values()}
            if lane_seeds != selected_seeds or len(lane_seeds) != 20:
                failures.append(f"review_selected_seed_set_mismatch:{lane_id}")
            for pair_id, assignment in assignments.items():
                pair = pairs.get(pair_id, {})
                seed = int(assignment.get("run_seed", -1))
                prompts = pair.get("prompts", {}) if isinstance(pair.get("prompts"), Mapping) else {}
                candidate_side = str(assignment.get("candidate_side", ""))
                incumbent_side = str(assignment.get("incumbent_side", ""))
                if (
                    prompts.get(candidate_side) != bound_records["after"].get(seed)
                    or prompts.get(incumbent_side) != bound_records["before"].get(seed)
                ):
                    failures.append(f"review_prompt_record_mismatch:{lane_id}:{pair_id}")
    try:
        from tools.aggregate_blind_prompt_review import aggregate_review

        recomputed = aggregate_review(review_dir, None, experiment={}, policy={})
        if canonical_json_bytes(recomputed) != canonical_json_bytes(review):
            failures.append("review_aggregate_recomputation_mismatch")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        failures.append("review_aggregate_recomputation_failed")
    return sorted(set(failures))


def _verification_artifact_failures(
    verification_path: Path,
    verified: Mapping[str, Any],
    compared: Mapping[str, Any],
    comparison_path: Path,
    review_path: Path,
) -> list[str]:
    failures: list[str] = []
    if (
        set(verified) != {"artifacts", "quality_gates", "schema_version", "status"}
        or verified.get("schema_version") != "prompt-quality-verification/v2"
        or verified.get("status") != "pass"
    ):
        failures.append("verification_schema_or_status_invalid")
    artifacts = verified.get("artifacts")
    if (
        not isinstance(artifacts, Mapping)
        or artifacts.get("comparison_hash") != hashlib.sha256(canonical_json_bytes(compared)).hexdigest()
        or artifacts.get("source_tree_hash") != compared.get("source_tree_hashes", {}).get("after")
    ):
        failures.append("verification_artifacts_invalid")
    gates = verified.get("quality_gates")
    if not isinstance(gates, Mapping) or set(gates) != REQUIRED_VERIFICATION_GATES:
        failures.append("verification_gate_inventory_invalid")
        return failures
    for gate_name, gate in gates.items():
        if not isinstance(gate, Mapping) or set(gate) != {"status", "evidence_path", "evidence_hash"} or gate.get("status") != "pass":
            failures.append(f"verification_gate_invalid:{gate_name}")
            continue
        relative = Path(str(gate.get("evidence_path", "")))
        if relative.is_absolute() or ".." in relative.parts:
            failures.append(f"verification_evidence_path_invalid:{gate_name}")
            continue
        evidence_path = (ROOT / relative).resolve()
        try:
            evidence_path.relative_to(ROOT.resolve())
        except ValueError:
            failures.append(f"verification_evidence_path_invalid:{gate_name}")
            continue
        if not evidence_path.is_file() or hashlib.sha256(evidence_path.read_bytes()).hexdigest() != gate.get("evidence_hash"):
            failures.append(f"verification_evidence_hash_mismatch:{gate_name}")
            continue
        try:
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            failures.append(f"verification_evidence_invalid:{gate_name}")
            continue
        if (
            not isinstance(evidence, Mapping)
            or evidence.get("schema_version") != "prompt-quality-verification-evidence/v1"
            or evidence.get("gate_name") != gate_name
            or evidence.get("source_tree_hash") != compared.get("source_tree_hashes", {}).get("after")
            or evidence.get("status") != "pass"
            or evidence.get("exit_code") != 0
            or not isinstance(evidence.get("command"), str)
            or not evidence["command"].strip()
        ):
            failures.append(f"verification_evidence_invalid:{gate_name}")
            continue
        result_relative = Path(str(evidence.get("result_path", "")))
        if result_relative.is_absolute() or ".." in result_relative.parts:
            failures.append(f"verification_result_path_invalid:{gate_name}")
            continue
        result_path = (ROOT / result_relative).resolve()
        if not result_path.is_file() or hashlib.sha256(result_path.read_bytes()).hexdigest() != evidence.get("result_hash"):
            failures.append(f"verification_result_hash_mismatch:{gate_name}")
            continue
        if gate_name == "target_comparison":
            if result_path != comparison_path.resolve():
                failures.append("verification_comparison_binding_mismatch")
            continue
        if gate_name == "blind_review":
            if result_path != review_path.resolve():
                failures.append("verification_review_binding_mismatch")
            continue
        try:
            gate_result = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            failures.append(f"verification_result_invalid:{gate_name}")
            continue
        if (
            not isinstance(gate_result, Mapping)
            or gate_result.get("schema_version") != "prompt-quality-gate-result/v1"
            or gate_result.get("gate_name") != gate_name
            or gate_result.get("source_tree_hash") != compared.get("source_tree_hashes", {}).get("after")
            or gate_result.get("status") != "pass"
            or gate_result.get("exit_code") != 0
            or not isinstance(gate_result.get("summary"), Mapping)
        ):
            failures.append(f"verification_result_invalid:{gate_name}")
            continue
        summary = gate_result["summary"]

        def number(name: str) -> int | None:
            value = summary.get(name)
            return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None

        invalid_summary = False
        if gate_name == "python_tests":
            tests_run, tests_passed = number("tests_run"), number("tests_passed")
            invalid_summary = (
                tests_run is None or tests_passed != tests_run or tests_run < MIN_FULL_REGRESSION_TESTS
                or number("failures") != 0 or number("errors") != 0 or number("skipped") != 0
            )
        elif gate_name == "data_validation":
            invalid_summary = number("errors") != 0 or number("warnings") != 0
        elif gate_name == "frontend":
            invalid_summary = (number("tests_passed") or 0) < 4 or number("failures") != 0
        elif gate_name == "browser":
            invalid_summary = (number("tests_passed") or 0) < 2 or number("failures") != 0
        elif gate_name == "prompt_quality_confirmation":
            invalid_summary = number("objectives_passed") != 3 or number("hard_gate_failures") != 0
        elif gate_name == "full_flow":
            invalid_summary = number("checks_passed") is None or number("failures") != 0
        elif gate_name == "widgets":
            invalid_summary = number("issues") != 0
        elif gate_name == "compatibility_review":
            invalid_summary = any(number(field) != 0 for field in ("errors", "missing_rows", "extra_rows"))
        elif gate_name == "action_pools":
            invalid_summary = number("errors") != 0 or number("missing_pools") != 0
        if invalid_summary:
            failures.append(f"verification_result_invalid:{gate_name}")
    return sorted(set(failures))


def promote_check(
    comparison: Mapping[str, Any] | str | Path,
    *,
    review: Mapping[str, Any] | str | Path | None = None,
    verification: Mapping[str, Any] | str | Path | None = None,
) -> dict[str, Any]:
    """Return a non-mutating promotion verdict artifact."""

    compared = _load_object(comparison)
    failures: list[str] = []
    if compared.get("schema_version") != COMPARISON_SCHEMA_VERSION:
        failures.append("invalid_comparison_schema")
    if compared.get("automatic_verdict") != "pass":
        failures.append("automatic_comparison_failed")
    if not isinstance(comparison, (str, Path)):
        failures.append("comparison_artifact_path_required")
    review_value = _load_object(review) if review is not None else {}
    failures.extend(_review_failures(
        review_value,
        compared.get("record_artifact_hashes") if isinstance(compared.get("record_artifact_hashes"), Mapping) else None,
        compared.get("source_tree_hashes") if isinstance(compared.get("source_tree_hashes"), Mapping) else None,
        compared.get("cohort_hashes") if isinstance(compared.get("cohort_hashes"), Mapping) else None,
        compared.get("review_contract_hash") if isinstance(compared.get("review_contract_hash"), str) else None,
        compared.get("qualitative_scope_hash") if isinstance(compared.get("qualitative_scope_hash"), str) else None,
        compared.get("experiment_id") if isinstance(compared.get("experiment_id"), str) else None,
    ))
    if isinstance(review, (str, Path)):
        failures.extend(_review_artifact_binding_failures(Path(review), review_value))
    else:
        failures.append("review_artifact_path_required")
    if verification is None:
        failures.append("verification_missing")
    else:
        verified = _load_object(verification)
        if isinstance(verification, (str, Path)) and isinstance(comparison, (str, Path)) and isinstance(review, (str, Path)):
            failures.extend(_verification_artifact_failures(
                Path(verification), verified, compared, Path(comparison), Path(review)
            ))
        else:
            failures.append("verification_artifact_path_required")
    return {
        "comparison_hash": __import__("hashlib").sha256(canonical_json_bytes(compared)).hexdigest(),
        "failures": sorted(set(failures)),
        "schema_version": PROMOTION_SCHEMA_VERSION,
        "source_mutated": False,
        "verdict": "promote" if not failures else "reject",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare paired prompt-quality runs without mutating source.")
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--output")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = compare_runs(args.before, args.after, policy=args.policy, experiment=args.experiment)
        content = canonical_json_bytes(result)
        if args.output:
            Path(args.output).write_bytes(content)
        else:
            sys.stdout.buffer.write(content)
        return 0
    except (OSError, json.JSONDecodeError, WorkflowValidationError) as exc:
        envelope = exc.to_envelope() if isinstance(exc, WorkflowValidationError) else WorkflowValidationError(
            "comparison_error", "could not compare prompt-quality runs", exception_type=type(exc).__name__
        ).to_envelope()
        sys.stderr.buffer.write(canonical_json_bytes(envelope))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
