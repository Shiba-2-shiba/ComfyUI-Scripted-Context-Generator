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
from tools.semantic_review_contract import SEMANTIC_COMPARISON_TO_REVIEW, V7_TARGETS, V7_GUARDS, v7_dimension_eligibility


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


def _review_v3_selection(
    experiment_id: str,
    before: Sequence[Mapping[str, Any]],
    after: Sequence[Mapping[str, Any]],
    review_policy: Mapping[str, Any],
    before_issues: Mapping[str, Any],
    after_issues: Mapping[str, Any],
    guard_dimensions: Sequence[str],
) -> dict[str, Any]:
    """Freeze the comparison-bound v3 review sample before any votes exist."""

    before_by_seed = {int(item["run_seed"]): item for item in before}
    after_by_seed = {int(item["run_seed"]): item for item in after}
    prompt_changed = sorted(
        seed for seed in before_by_seed
        if before_by_seed[seed].get("cleaned_prompt") != after_by_seed[seed].get("cleaned_prompt")
    )
    issue_code_mapping = {
        "consistency": ["consistency_rule_conflict", "location_action_object_conflict"],
    }

    def issue_seeds(artifact: Mapping[str, Any], codes: set[str]) -> set[int]:
        if artifact.get("schema_version") != "prompt-quality-issues/v1" or not isinstance(artifact.get("issues"), list):
            raise WorkflowValidationError("invalid_issues_artifact", "v3 review selection requires canonical issues/v1")
        seeds: set[int] = set()
        for issue in artifact["issues"]:
            if not isinstance(issue, Mapping) or issue.get("issue_code") not in codes:
                continue
            affected_seeds = issue.get("affected_seeds")
            if not isinstance(affected_seeds, list):
                raise WorkflowValidationError("invalid_issues_artifact", "issue affected_seeds must be an array")
            seeds.update(int(seed) for seed in affected_seeds)
        return seeds

    consistency_issue_codes = set(issue_code_mapping["consistency"])
    consistency_eligible = sorted(
        issue_seeds(before_issues, consistency_issue_codes)
        | issue_seeds(after_issues, consistency_issue_codes)
    )
    outside_cohort = sorted(set(consistency_eligible) - set(before_by_seed))
    if outside_cohort:
        raise WorkflowValidationError(
            "issue_seed_outside_cohort", "consistency issue seed is outside the paired cohort", seeds=outside_cohort
        )
    if len(consistency_eligible) > 20:
        raise WorkflowValidationError(
            "review_eligible_seed_overflow", "all consistency eligible seeds must fit the 20-pair review",
            actual=len(consistency_eligible),
        )

    def rank(seed: int) -> tuple[str, int]:
        digest = hashlib.sha256(f"{experiment_id}:review-sample:{seed}".encode()).hexdigest()
        return digest, seed

    selected = list(consistency_eligible)
    selected.extend(sorted((seed for seed in prompt_changed if seed not in selected), key=rank)[:20 - len(selected)])
    if len(selected) < 20:
        selected.extend(sorted((seed for seed in before_by_seed if seed not in selected), key=rank)[:20 - len(selected)])
    if len(selected) != 20:
        raise WorkflowValidationError(
            "insufficient_review_cohort", "review-contract/v3 requires 20 paired seeds", actual=len(selected)
        )
    dimension_authority = review_policy.get("dimension_authority", {})
    expected_dimensions = {
        "protagonist_clarity", "consistency", "naturalness",
        "redundancy", "diversity", "image_prompt_suitability",
    }
    if not isinstance(dimension_authority, Mapping) or set(dimension_authority) != expected_dimensions:
        raise WorkflowValidationError(
            "invalid_review_contract", "v3 dimension_authority must cover the complete rubric exactly"
        )
    if (
        dimension_authority.get("consistency") != "affected_seed_pairwise"
        or dimension_authority.get("naturalness") != "selected_pairwise"
        or dimension_authority.get("image_prompt_suitability") != "selected_pairwise"
        or dimension_authority.get("diversity") != "current_source_corpus_confirmation"
    ):
        raise WorkflowValidationError("invalid_review_contract", "v3 target and diversity authorities are fixed")
    lanes = review_policy.get("independent_lanes")
    fraction = review_policy.get("minimum_valid_vote_fraction")
    cap = review_policy.get("minimum_valid_votes_cap")
    codes = review_policy.get("hard_defect_codes")
    if lanes != 2 or not isinstance(fraction, (int, float)) or isinstance(fraction, bool) or not 0 < fraction <= 1:
        raise WorkflowValidationError("invalid_review_contract", "v3 requires two lanes and a valid vote fraction")
    if not isinstance(cap, int) or isinstance(cap, bool) or cap < 1 or cap > 40:
        raise WorkflowValidationError("invalid_review_contract", "v3 minimum vote cap must be an integer from 1 through 40")
    if (
        not isinstance(codes, list) or not codes or len(codes) != len(set(codes))
        or not all(isinstance(code, str) and code.strip() for code in codes)
    ):
        raise WorkflowValidationError("invalid_review_contract", "v3 hard defect codes must be a non-empty closed set")
    prompt_changed_set = set(prompt_changed)
    eligible: dict[str, Any] = {}
    guard_set = set(guard_dimensions)
    for dimension, authority in sorted(dimension_authority.items()):
        if authority == "affected_seed_pairwise":
            seeds = list(consistency_eligible) if dimension == "consistency" else [
                seed for seed in selected if seed in prompt_changed_set
            ]
        elif authority == "selected_pairwise":
            seeds = list(selected)
        elif authority == "current_source_corpus_confirmation":
            eligible[str(dimension)] = {"authority": authority, "minimum_valid_votes": 0, "seeds": []}
            continue
        else:
            raise WorkflowValidationError(
                "invalid_review_contract", "unknown v3 dimension authority", dimension=dimension, authority=authority
            )
        possible_votes = len(seeds) * lanes
        if authority == "selected_pairwise" and dimension in guard_set:
            minimum = int(review_policy.get("guard_dimension_contract", {}).get("minimum_valid_votes", 0))
        else:
            minimum = min(cap, math.ceil(possible_votes * float(fraction)))
        eligible[str(dimension)] = {
            "authority": authority,
            "minimum_valid_votes": minimum,
            "seeds": seeds,
        }
    eligible_seed_hashes = {
        "consistency": hashlib.sha256(canonical_json_bytes(consistency_eligible)).hexdigest(),
    }
    eligible["consistency"]["eligible_seed_hash"] = eligible_seed_hashes["consistency"]
    selection = {
        "affected_seeds": prompt_changed,
        "dimension_issue_code_mapping": issue_code_mapping,
        "dimensions": eligible,
        "eligible_seed_hashes": eligible_seed_hashes,
        "prompt_changed_seeds": prompt_changed,
        "selected_seeds": selected,
        "strategy": "affected_first_deterministic_20",
    }
    selection["selection_hash"] = hashlib.sha256(canonical_json_bytes(selection)).hexdigest()
    return selection


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


def _analysis_issues(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "issues.json"
    try:
        return _load_object(path)
    except OSError as exc:
        raise WorkflowValidationError("missing_issues_artifact", "run issues are missing", path=str(path)) from exc


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
    ablation_pair: str | Path | None = None,
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
    review_policy = policy_value.get("review", {})
    is_v3 = isinstance(review_policy, Mapping) and review_policy.get("schema_version") == "prompt-quality-review-contract/v3"
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
    ablation_binding: dict[str, Any] | None = None
    if is_v3:
        if not isinstance(ablation_pair, (str, Path)):
            raise WorkflowValidationError(
                "ablation_pair_required", "review-contract/v3 comparison requires a bound ablation pair artifact"
            )
        pair_path = Path(ablation_pair)
        pair = _load_object(pair_path)
        if pair.get("schema_version") != "prompt-quality-ablation-pair/v1":
            raise WorkflowValidationError("invalid_ablation_pair", "ablation pair schema is invalid")
        from tools.build_prompt_quality_ablation_pair import validate_pair
        from tools.build_prompt_quality_confirmation import ABLATION_FEATURE_IDS, ablation_contract

        expected_contract = ablation_contract()
        expected_contract_hash = hashlib.sha256(canonical_json_bytes(expected_contract)).hexdigest()
        if (
            pair.get("ablation_contract") != expected_contract
            or pair.get("ablation_contract_hash") != expected_contract_hash
            or pair.get("baseline_feature_ids") != list(ABLATION_FEATURE_IDS)
        ):
            raise WorkflowValidationError("ablation_pair_contract_mismatch", "ablation pair contract drifted")
        sides = pair.get("sides", {})
        if not isinstance(sides, Mapping) or set(sides) != {"baseline", "current"}:
            raise WorkflowValidationError("invalid_ablation_pair", "ablation pair sides are invalid")
        expected = {"baseline": before_path.resolve(), "current": after_path.resolve()}
        for side, run_path in expected.items():
            side_value = sides.get(side, {})
            declared = (ROOT / str(side_value.get("run_path", ""))).resolve()
            if declared != run_path:
                raise WorkflowValidationError("ablation_pair_run_mismatch", "comparison run is not bound by pair", side=side)
            manifest_path = run_path / "run-manifest.json"
            records_path = run_path / "records.jsonl"
            if (
                side_value.get("run_manifest_hash") != hashlib.sha256(manifest_path.read_bytes()).hexdigest()
                or side_value.get("records_hash") != hashlib.sha256(records_path.read_bytes()).hexdigest()
            ):
                raise WorkflowValidationError("ablation_pair_hash_mismatch", "paired run artifact hash drifted", side=side)
            manifest_value = _load_object(manifest_path)
            if side_value.get("artifact_hashes") != manifest_value.get("artifact_hashes"):
                raise WorkflowValidationError(
                    "ablation_pair_consumed_artifact_mismatch", "pair does not bind the run artifact inventory", side=side
                )
        contract_hash = pair.get("ablation_contract_hash")
        if (
            contract_hash != before_manifest.get("ablation_contract_hash")
            or contract_hash != after_manifest.get("ablation_contract_hash")
            or before_manifest.get("behavior_feature_ids") != list(ABLATION_FEATURE_IDS)
            or before_manifest.get("behavior_variant") != "combined_ablation_baseline"
            or after_manifest.get("behavior_feature_ids") != []
            or after_manifest.get("behavior_variant") != "current"
            or before_manifest.get("behavior_transform_hash") == after_manifest.get("behavior_transform_hash")
        ):
            raise WorkflowValidationError("ablation_pair_variant_mismatch", "paired behavior variants are not declared exactly")
        try:
            recomputed_sentinel = validate_pair(after_path, before_path, contract_hash=str(contract_hash))
        except ValueError as exc:
            raise WorkflowValidationError(
                "invalid_ablation_pair", "ablation pair validation failed", reason=str(exc)
            ) from exc
        if pair.get("sentinel") != recomputed_sentinel:
            raise WorkflowValidationError("ablation_pair_sentinel_mismatch", "ablation pair sentinel drifted")
        ablation_binding = {
            "artifact_hash": hashlib.sha256(pair_path.read_bytes()).hexdigest(),
            "artifact_path": pair_path.resolve().relative_to(ROOT.resolve()).as_posix(),
            "contract_hash": contract_hash,
            "consumed_artifact_hashes": {
                "after": dict(sides["current"]["artifact_hashes"]),
                "before": dict(sides["baseline"]["artifact_hashes"]),
            },
        }
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
    result = {
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
            "after": hashlib.sha256((after_path / "records.jsonl").read_bytes()).hexdigest(),
            "before": hashlib.sha256((before_path / "records.jsonl").read_bytes()).hexdigest(),
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
    if ablation_binding is not None:
        result["ablation_pair"] = ablation_binding
    if is_v3:
        result["review_selection"] = _review_v3_selection(
            str(experiment_value.get("experiment_id", "")), before_records, after_records, review_policy,
            _analysis_issues(before_path), _analysis_issues(after_path),
            qualitative_guards,
        )
    return result


def _review_failures(
    review: Mapping[str, Any],
    expected_record_hashes: Mapping[str, Any] | None = None,
    expected_source_hashes: Mapping[str, Any] | None = None,
    expected_cohort_hashes: Mapping[str, Any] | None = None,
    expected_review_contract_hash: str | None = None,
    expected_qualitative_scope_hash: str | None = None,
    expected_experiment_id: str | None = None,
    expected_comparison_hash: str | None = None,
    expected_review_selection: Mapping[str, Any] | None = None,
    expected_review_schema: str | None = None,
) -> list[str]:
    if not review:
        return ["review_missing"]
    failures: list[str] = []
    is_v3 = review.get("schema_version") == "prompt-quality-review/v3"
    is_v4 = review.get("schema_version") == "prompt-quality-review/v4"
    is_v5 = review.get("schema_version") == "prompt-quality-review/v5"
    is_v6 = review.get("schema_version") == "prompt-quality-review/v6"
    is_v7 = review.get("schema_version") == "prompt-quality-review/v7"
    is_semantic = is_v4 or is_v5 or is_v6 or is_v7
    uses_non_abstain = is_v5 or is_v6 or is_v7
    if review.get("schema_version") not in {"prompt-quality-review/v1", "prompt-quality-review/v3", *SEMANTIC_COMPARISON_TO_REVIEW.values()}:
        failures.append("review_schema_invalid")
    if expected_review_schema is not None and review.get("schema_version") != expected_review_schema:
        failures.append("review_schema_invalid")
    if expected_review_selection is not None:
        if not is_v3 and not is_semantic:
            failures.append("review_bound_schema_required")
        if review.get("comparison_artifact_hash") != expected_comparison_hash:
            failures.append("review_comparison_hash_mismatch")
        if review.get("selection_hash") != expected_review_selection.get("selection_hash"):
            failures.append("review_selection_hash_mismatch")
    if review.get("pair_count_per_lane") != 20:
        failures.append("review_pair_count_invalid")
    reviewers = review.get("reviewers", [])
    reviewer_ids = [item.get("reviewer_id") for item in reviewers if isinstance(item, Mapping)] if isinstance(reviewers, list) else []
    if len(reviewer_ids) != 2 or None in reviewer_ids or len(set(reviewer_ids)) != 2:
        failures.append("reviewer_identity_not_independent")
    if is_semantic:
        session_ids = [item.get("review_session_id") for item in reviewers if isinstance(item, Mapping)] if isinstance(reviewers, list) else []
        if len(session_ids) != 2 or None in session_ids or len(set(session_ids)) != 2 or set(session_ids) & set(reviewer_ids):
            failures.append("review_session_not_independent")
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
    if is_semantic:
        if provenance != {}:
            failures.append("reviewed_run_provenance_invalid")
    elif not isinstance(provenance, Mapping) or set(provenance) != {"before", "after"}:
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
        if is_v7:
            if targets != set(V7_TARGETS) or guards != set(V7_GUARDS):
                failures.append("review_scope_invalid")
            if expected_review_selection is None or expected_review_selection.get("dimensions") != v7_dimension_eligibility(
                [pair["pair_id"] for pair in expected_review_selection.get("pairs", [])]
            ):
                failures.append("review_vote_thresholds_invalid")
        for dimension, result in dimensions.items():
            if not isinstance(result, Mapping) or result.get("passed") is not True:
                failures.append(f"review_dimension_failed:{dimension}")
            if expected_review_selection is not None:
                eligibility = expected_review_selection.get("dimensions", {}).get(dimension, {})
                if dimension in targets:
                    if result.get("authority") != eligibility.get("authority"):
                        failures.append(f"review_authority_mismatch:{dimension}")
                required = int(eligibility.get("minimum_non_abstain_votes" if uses_non_abstain else "minimum_valid_votes", 0))
                enforce_minimum = eligibility.get("authority") in {"affected_seed_pairwise", "selected_pairwise", "semantic_pairwise"}
            elif dimension in targets:
                required = 36
                enforce_minimum = True
            else:
                required = 0
                enforce_minimum = False
            if enforce_minimum:
                observed = int(result.get("non_abstain_votes" if uses_non_abstain else "valid_votes", 0))
                if observed < required:
                    failures.append(f"review_votes_insufficient:{dimension}")
                if uses_non_abstain and int(result.get("directional_votes", 0)) < int(eligibility.get("minimum_directional_votes", 0)):
                    failures.append(f"review_directional_votes_insufficient:{dimension}")
        if expected_review_selection is not None:
            diversity = dimensions.get("diversity", {})
            diversity_votes = diversity.get("non_abstain_votes" if uses_non_abstain else "valid_votes")
            if diversity.get("authority") != "current_source_corpus_confirmation" or diversity_votes != 0:
                failures.append("review_diversity_authority_invalid")
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
    key_is_v3 = key.get("schema_version") == "prompt-quality-review-assignment-key/v3"
    key_is_v4 = key.get("schema_version") == "prompt-quality-review-assignment-key/v4"
    key_is_v5 = key.get("schema_version") == "prompt-quality-review-assignment-key/v5"
    key_is_v6 = key.get("schema_version") == "prompt-quality-review-assignment-key/v6"
    key_is_v7 = key.get("schema_version") == "prompt-quality-review-assignment-key/v7"
    key_is_semantic = key_is_v4 or key_is_v5 or key_is_v6 or key_is_v7
    if key.get("schema_version") not in {
        "prompt-quality-review-assignment-key/v1", "prompt-quality-review-assignment-key/v3",
        "prompt-quality-review-assignment-key/v4", "prompt-quality-review-assignment-key/v5",
        "prompt-quality-review-assignment-key/v6",
        "prompt-quality-review-assignment-key/v7",
    } or {
        str(item.get("lane_id", "")) for item in key_lanes if isinstance(item, Mapping)
    } != {"lane-1", "lane-2"} or len(key_lanes) != 2:
        failures.append("review_assignment_lane_set_invalid")
    if key_is_v3 or key_is_semantic:
        comparison_relative = Path(str(key.get("comparison_artifact_path", "")))
        if comparison_relative.is_absolute() or ".." in comparison_relative.parts:
            failures.append("review_comparison_path_invalid")
        else:
            comparison_path = (ROOT / comparison_relative).resolve()
            try:
                comparison_path.relative_to(ROOT.resolve())
            except ValueError:
                failures.append("review_comparison_path_invalid")
            else:
                if not comparison_path.is_file() or hashlib.sha256(comparison_path.read_bytes()).hexdigest() != key.get("comparison_artifact_hash"):
                    failures.append("review_comparison_hash_mismatch")
                elif key_is_semantic:
                    try:
                        bound_comparison = _load_object(comparison_path)
                        if (
                            bound_comparison.get("schema_version") != ("prompt-quality-comparison/v5" if key_is_v7 else "prompt-quality-comparison/v4" if key_is_v6 else "prompt-quality-comparison/v3" if key_is_v5 else "prompt-quality-comparison/v2")
                            or review.get("candidate_source_tree_sha256") != bound_comparison.get("candidate_source_tree_sha256")
                            or review.get("candidate_snapshot_content_sha256") != bound_comparison.get("candidate_snapshot_content_sha256")
                        ):
                            failures.append("review_candidate_binding_mismatch")
                    except (OSError, ValueError, TypeError, json.JSONDecodeError):
                        failures.append("review_comparison_recursive_validation_failed")
        selection = dict(key.get("selection", {}))
        selection["dimensions"] = key.get("dimension_eligibility")
        if hashlib.sha256(canonical_json_bytes(selection)).hexdigest() != key.get("selection_hash"):
            failures.append("review_selection_hash_mismatch")
        contract = key.get("review_contract")
        if not isinstance(contract, Mapping) or hashlib.sha256(canonical_json_bytes(dict(contract))).hexdigest() != key.get("review_contract_hash"):
            failures.append("review_contract_hash_mismatch")
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
        pairs = (
            {str(item.get("pair_id")): True for item in lane.get("pairs", [])}
            if key_is_semantic else
            {str(item.get("pair_id")): int(item.get("run_seed")) for item in lane.get("pairs", [])}
        )
        assignments = lane_key.get("assignments", []) if isinstance(lane_key.get("assignments"), list) else []
        for assignment in assignments:
            pair_id = str(assignment.get("pair_id", ""))
            seed = int(assignment.get("run_seed", -1)) if not key_is_semantic else None
            material = (
                f"{key.get('comparison_artifact_hash')}:{lane_id}:{pair_id}"
                if key_is_semantic else f"{experiment_id}:{lane_id}:{seed}"
            )
            digest = hashlib.sha256(material.encode()).digest()
            expected_candidate = "A" if int.from_bytes(digest[:8], "big") % 2 == 0 else "B"
            if (
                (pairs.get(pair_id) is not True if key_is_semantic else pairs.get(pair_id) != seed)
                or assignment.get("candidate_side") != expected_candidate
                or assignment.get("incumbent_side") != ("B" if expected_candidate == "A" else "A")
            ):
                failures.append(f"review_assignment_drift:{lane_id}:{pair_id}")
    paths = key.get("reviewed_record_paths")
    hashes = key.get("reviewed_record_hashes")
    provenance = key.get("reviewed_run_provenance")
    bound_records: dict[str, dict[int, str]] = {}
    provenance_valid = provenance == {} if key_is_semantic else isinstance(provenance, Mapping) and set(provenance) == {"before", "after"}
    if not all(isinstance(value, Mapping) and set(value) == {"before", "after"} for value in (paths, hashes)) or not provenance_valid:
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
                        (str(item["pair_id"]) if key_is_semantic else int(item["run_seed"])): str(item["cleaned_prompt"])
                        for item in records
                    }
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    failures.append(f"review_record_content_invalid:{side}")
            if review.get("reviewed_record_hashes", {}).get(side) != hashes[side]:
                failures.append(f"review_aggregate_record_hash_mismatch:{side}")
            if key_is_semantic:
                continue
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
        if key_is_semantic:
            selected_pair_ids = {
                str(item["pair_id"]) for item in selection.get("pairs", [])
            } if isinstance(selection, Mapping) and isinstance(selection.get("pairs"), list) else set()
            selected_seeds = set()
        elif key_is_v3:
            selected_seeds = {
                int(seed) for seed in selection.get("selected_seeds", [])
            } if isinstance(selection, Mapping) and isinstance(selection.get("selected_seeds"), list) else set()
        else:
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
            if key_is_semantic:
                lane_pair_ids = set(pairs)
                if lane_pair_ids != selected_pair_ids or len(lane_pair_ids) != 20:
                    failures.append(f"review_selected_pair_set_mismatch:{lane_id}")
            else:
                lane_seeds = {int(item["run_seed"]) for item in pairs.values()}
                if lane_seeds != selected_seeds or len(lane_seeds) != 20:
                    failures.append(f"review_selected_seed_set_mismatch:{lane_id}")
            for pair_id, assignment in assignments.items():
                pair = pairs.get(pair_id, {})
                record_key = pair_id if key_is_semantic else int(assignment.get("run_seed", -1))
                prompts = pair.get("prompts", {}) if isinstance(pair.get("prompts"), Mapping) else {}
                candidate_side = str(assignment.get("candidate_side", ""))
                incumbent_side = str(assignment.get("incumbent_side", ""))
                if (
                    prompts.get(candidate_side) != bound_records["after"].get(record_key)
                    or prompts.get(incumbent_side) != bound_records["before"].get(record_key)
                ):
                    failures.append(f"review_prompt_record_mismatch:{lane_id}:{pair_id}")
    try:
        from tools.aggregate_blind_prompt_review import aggregate_review

        recomputed = aggregate_review(
            review_dir,
            None,
            experiment={
                "target_qualitative_dimensions": review.get("target_qualitative_dimensions", []),
                "guard_qualitative_dimensions": review.get("guard_qualitative_dimensions", []),
            } if key_is_semantic else {},
            policy={},
        )
        if key_is_semantic:
            recomputed.update({
                "candidate_source_tree_sha256": review.get("candidate_source_tree_sha256"),
                "candidate_snapshot_content_sha256": review.get("candidate_snapshot_content_sha256"),
            })
        if canonical_json_bytes(recomputed) != canonical_json_bytes(review):
            failures.append("review_aggregate_recomputation_mismatch")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        failures.append("review_aggregate_recomputation_failed")
    return sorted(set(failures))


def _v150_verification_failures(
    verification_path: Path, verified: Mapping[str, Any], compared: Mapping[str, Any],
    comparison_path: Path, review_path: Path,
) -> list[str]:
    failures: list[str] = []
    expected_fields = {
        "schema_version", "status", "experiment_id", "candidate_root", "candidate_root_identity_sha256",
        "candidate_source_tree_sha256", "candidate_snapshot_content_sha256", "comparison_artifact_sha256",
        "review_artifact_sha256", "quality_gates",
    }
    if set(verified) != expected_fields or verified.get("schema_version") != "variation-v150-verification-receipt/v1" or verified.get("status") != "pass":
        return ["verification_schema_or_status_invalid"]
    if (
        verified.get("experiment_id") != compared.get("experiment_id")
        or verified.get("candidate_source_tree_sha256") != compared.get("candidate_source_tree_sha256")
        or verified.get("candidate_snapshot_content_sha256") != compared.get("candidate_snapshot_content_sha256")
        or verified.get("comparison_artifact_sha256") != hashlib.sha256(comparison_path.read_bytes()).hexdigest()
        or verified.get("review_artifact_sha256") != hashlib.sha256(review_path.read_bytes()).hexdigest()
    ):
        failures.append("verification_artifacts_invalid")
    gates = verified.get("quality_gates")
    if not isinstance(gates, Mapping) or set(gates) != REQUIRED_VERIFICATION_GATES:
        return failures + ["verification_gate_inventory_invalid"]
    for gate_name, gate in gates.items():
        if not isinstance(gate, Mapping) or set(gate) != {"evidence_path", "evidence_sha256", "result_path", "result_sha256", "status"} or gate.get("status") != "pass":
            failures.append(f"verification_gate_invalid:{gate_name}")
            continue
        for kind in ("evidence", "result"):
            path = Path(str(gate.get(f"{kind}_path", ""))).resolve()
            try:
                path.relative_to(ROOT.resolve())
            except ValueError:
                failures.append(f"verification_{kind}_path_invalid:{gate_name}")
                continue
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != gate.get(f"{kind}_sha256"):
                failures.append(f"verification_{kind}_hash_mismatch:{gate_name}")
        expected = comparison_path.resolve() if gate_name == "target_comparison" else review_path.resolve() if gate_name == "blind_review" else None
        if expected is not None and Path(str(gate.get("result_path", ""))).resolve() != expected:
            failures.append(f"verification_{'comparison' if gate_name == 'target_comparison' else 'review'}_binding_mismatch")
    return sorted(set(failures))


def _v150_promote_failures(
    compared: Mapping[str, Any], comparison_path: Path, review: Mapping[str, Any], review_path: Path,
    verified: Mapping[str, Any], verification_path: Path,
) -> list[str]:
    failures: list[str] = []
    required_hashes = {
        "automatic_comparison_hash", "candidate_source_tree_sha256", "candidate_snapshot_content_sha256",
        "semantic_pair_contract_sha256", "pair_generation_receipt_sha256", "pair_validation_sha256",
        "selection_salt_sha256", "compatibility_graph_sha256", "baseline_records_sha256",
        "candidate_records_sha256", "review_contract_hash", "qualitative_scope_hash",
    }
    if compared.get("automatic_comparison_verdict") != "pass" or compared.get("uses_output_metrics_for_selection") is not False:
        failures.append("automatic_comparison_failed")
    if any(not isinstance(compared.get(field), str) or len(compared[field]) != 64 for field in required_hashes):
        failures.append("comparison_binding_invalid")
    automatic_reference = Path(str(compared.get("automatic_comparison_path", "")))
    if ".." in automatic_reference.parts:
        failures.append("automatic_comparison_path_invalid")
    else:
        automatic_path = (ROOT / automatic_reference).resolve()
        if not automatic_path.is_relative_to(ROOT.resolve()):
            failures.append("automatic_comparison_path_invalid")
        elif not automatic_path.is_file() or hashlib.sha256(automatic_path.read_bytes()).hexdigest() != compared.get("automatic_comparison_hash"):
            failures.append("automatic_comparison_hash_mismatch")
    expected_records = {"before": compared.get("baseline_records_sha256"), "after": compared.get("candidate_records_sha256")}
    failures.extend(_review_failures(
        review, expected_records, None, None, compared.get("review_contract_hash"),
        compared.get("qualitative_scope_hash"), compared.get("experiment_id"),
        hashlib.sha256(comparison_path.read_bytes()).hexdigest(), compared.get("review_selection"),
        expected_review_schema=SEMANTIC_COMPARISON_TO_REVIEW[compared["schema_version"]],
    ))
    if review.get("candidate_source_tree_sha256") != compared.get("candidate_source_tree_sha256") or review.get("candidate_snapshot_content_sha256") != compared.get("candidate_snapshot_content_sha256"):
        failures.append("review_candidate_binding_mismatch")
    failures.extend(_review_artifact_binding_failures(review_path, review))
    failures.extend(_v150_verification_failures(verification_path, verified, compared, comparison_path, review_path))
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
    comparison_schema = compared.get("schema_version")
    if comparison_schema not in {COMPARISON_SCHEMA_VERSION, *SEMANTIC_COMPARISON_TO_REVIEW}:
        failures.append("invalid_comparison_schema")
        comparison_hash = hashlib.sha256(canonical_json_bytes(compared)).hexdigest()
        return {
            "comparison_hash": comparison_hash, "failures": failures,
            "schema_version": PROMOTION_SCHEMA_VERSION, "source_mutated": False, "verdict": "reject",
        }
    if comparison_schema in SEMANTIC_COMPARISON_TO_REVIEW:
        if not all(isinstance(value, (str, Path)) for value in (comparison, review, verification)):
            missing = [
                name for name, value in (("comparison", comparison), ("review", review), ("verification", verification))
                if not isinstance(value, (str, Path))
            ]
            failures.extend(f"{name}_artifact_path_required" for name in missing)
            comparison_hash = hashlib.sha256(canonical_json_bytes(compared)).hexdigest()
        else:
            comparison_path, review_path, verification_path = Path(comparison), Path(review), Path(verification)
            comparison_hash = hashlib.sha256(comparison_path.read_bytes()).hexdigest()
            review_value, verified = _load_object(review_path), _load_object(verification_path)
            failures.extend(_v150_promote_failures(compared, comparison_path, review_value, review_path, verified, verification_path))
        return {
            "comparison_hash": comparison_hash, "failures": sorted(set(failures)),
            "schema_version": PROMOTION_SCHEMA_VERSION, "source_mutated": False,
            "verdict": "promote" if not failures else "reject",
        }
    if compared.get("automatic_verdict") != "pass":
        failures.append("automatic_comparison_failed")
    binding = compared.get("ablation_pair")
    if compared.get("review_selection") is not None:
        if not isinstance(binding, Mapping):
            failures.append("ablation_pair_binding_missing")
        else:
            relative = Path(str(binding.get("artifact_path", "")))
            if relative.is_absolute() or ".." in relative.parts:
                failures.append("ablation_pair_path_invalid")
            else:
                pair_path = (ROOT / relative).resolve()
                try:
                    pair_path.relative_to(ROOT.resolve())
                except ValueError:
                    failures.append("ablation_pair_path_invalid")
                else:
                    if not pair_path.is_file() or hashlib.sha256(pair_path.read_bytes()).hexdigest() != binding.get("artifact_hash"):
                        failures.append("ablation_pair_hash_mismatch")
                    else:
                        try:
                            from tools.build_prompt_quality_ablation_pair import validate_pair

                            pair = _load_object(pair_path)
                            if (
                                pair.get("schema_version") != "prompt-quality-ablation-pair/v1"
                                or pair.get("ablation_contract_hash") != binding.get("contract_hash")
                            ):
                                raise ValueError("ablation pair contract binding drifted")
                            sides = pair.get("sides", {})
                            current_dir = (ROOT / str(sides["current"]["run_path"])).resolve()
                            baseline_dir = (ROOT / str(sides["baseline"]["run_path"])).resolve()
                            current_dir.relative_to(ROOT.resolve())
                            baseline_dir.relative_to(ROOT.resolve())
                            for side_name, run_dir in (("current", current_dir), ("baseline", baseline_dir)):
                                side = sides[side_name]
                                if (
                                    hashlib.sha256((run_dir / "run-manifest.json").read_bytes()).hexdigest()
                                    != side.get("run_manifest_hash")
                                    or hashlib.sha256((run_dir / "records.jsonl").read_bytes()).hexdigest()
                                    != side.get("records_hash")
                                ):
                                    raise ValueError("paired run binding hash drifted")
                            validate_pair(current_dir, baseline_dir, contract_hash=str(binding.get("contract_hash", "")))
                            consumed = {
                                "after": sides["current"]["artifact_hashes"],
                                "before": sides["baseline"]["artifact_hashes"],
                            }
                            if binding.get("consumed_artifact_hashes") != consumed:
                                failures.append("ablation_pair_consumed_artifact_mismatch")
                        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                            failures.append("ablation_pair_recursive_validation_failed")
    if not isinstance(comparison, (str, Path)):
        failures.append("comparison_artifact_path_required")
    review_value = _load_object(review) if review is not None else {}
    comparison_hash = (
        hashlib.sha256(Path(comparison).read_bytes()).hexdigest()
        if isinstance(comparison, (str, Path)) and Path(comparison).is_file()
        else hashlib.sha256(canonical_json_bytes(compared)).hexdigest()
    )
    failures.extend(_review_failures(
        review_value,
        compared.get("record_artifact_hashes") if isinstance(compared.get("record_artifact_hashes"), Mapping) else None,
        compared.get("source_tree_hashes") if isinstance(compared.get("source_tree_hashes"), Mapping) else None,
        compared.get("cohort_hashes") if isinstance(compared.get("cohort_hashes"), Mapping) else None,
        compared.get("review_contract_hash") if isinstance(compared.get("review_contract_hash"), str) else None,
        compared.get("qualitative_scope_hash") if isinstance(compared.get("qualitative_scope_hash"), str) else None,
        compared.get("experiment_id") if isinstance(compared.get("experiment_id"), str) else None,
        comparison_hash,
        compared.get("review_selection") if isinstance(compared.get("review_selection"), Mapping) else None,
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
        "comparison_hash": comparison_hash,
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
    parser.add_argument("--ablation-pair")
    parser.add_argument("--output")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = compare_runs(
            args.before, args.after, policy=args.policy, experiment=args.experiment,
            ablation_pair=args.ablation_pair,
        )
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
