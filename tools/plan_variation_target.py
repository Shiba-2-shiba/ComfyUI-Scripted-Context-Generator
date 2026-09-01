from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from assets.calc_variations import calc_base_metrics, is_action_pool_location_key
from registry import load_action_pools, load_scene_compatibility, resolve_location_alias_map
from tools.build_compatibility_review import build_generated_rows, resolve_canonical_location
from tools.check_variation_scope import load_variation_scope
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


DEFAULT_MINIMUM_ACTIONS = [12, 16, 20, 24, 32, 35]
L0_BASELINE_MANIFEST_PATH = (
    ROOT / "docs" / "variation_expansion" / "experiments" / "v150-planner-l0" / "manifest.json"
)
L0_POOL_POLICY_PATH = (
    ROOT / "docs" / "variation_expansion" / "experiments" / "v150-planner-l0" / "pool-policy.json"
)
L0_PROTECTED_INPUT_PATHS = (
    "vocab/data/variation_scope.json",
    "vocab/data/scene_compatibility.json",
    "vocab/data/action_pools.json",
    "assets/compatibility_review.csv",
    "vocab/data/prompt_quality_policy.json",
    "rules/consistency_rules.json",
    "tools/prompt_quality_loop.py",
    "docs/prompt_quality/final-review-contract.json",
    ".omx/ultragoal/goals.json",
    ".omx/ultragoal/ledger.jsonl",
)
PROJECTION_MANIFEST_SCHEMA_VERSION = "variation-target-scenarios/v1"
PROJECTION_REPORT_SCHEMA_VERSION = "variation-target-projection-report/v1"
PROJECTION_MODEL_VERSION = "mixed-shape-largest-remainder/v1"
_SCENARIO_FIELDS = frozenset(
    {
        "id",
        "subject_count",
        "location_count",
        "compatibility_density_basis_points",
        "action_depth_row_distribution",
        "proposed_subject_ids",
        "proposed_location_ids",
        "subject_utility_groups",
        "location_utility_groups",
        "notes",
    }
)
_DISTRIBUTION_FIELDS = frozenset({"actions", "row_share_basis_points"})


def _valid_action_pools() -> Dict[str, list]:
    return {
        str(key): value
        for key, value in load_action_pools().items()
        if is_action_pool_location_key(str(key), value)
    }


def _canonical_overrides(scope: dict) -> Dict[str, str]:
    config = scope.get("compatibility_review_generation", {})
    overrides = config.get("canonical_location_overrides", {}) if isinstance(config, dict) else {}
    if not isinstance(overrides, dict):
        return {}
    return {str(key): str(value) for key, value in overrides.items()}


def _compatibility_location_sources(compatibility: dict) -> List[str]:
    locations: List[str] = []
    locations.extend(str(item) for item in compatibility.get("locations", []))
    locations.extend(str(item) for item in compatibility.get("universal_locs", []))
    for tag_locations in compatibility.get("loc_tags", {}).values():
        locations.extend(str(item) for item in tag_locations)
    return locations


def action_backed_compatible_locations(scope: dict | None = None) -> List[str]:
    scope = scope or load_variation_scope()
    compatibility = load_scene_compatibility()
    action_pools = _valid_action_pools()
    action_locations = set(action_pools)
    scope_locations = set(scope.get("variation_locations", []))
    aliases = resolve_location_alias_map()
    canonical_overrides = _canonical_overrides(scope)

    locations = set()
    for location in _compatibility_location_sources(compatibility):
        canonical = resolve_canonical_location(location, aliases, scope_locations, canonical_overrides)
        if canonical not in action_locations:
            canonical = resolve_canonical_location(location, aliases, action_locations, canonical_overrides)
        if canonical in action_locations:
            locations.add(canonical)
    return sorted(locations)


def all_compatible_subjects() -> List[str]:
    return sorted(str(subject) for subject in load_scene_compatibility().get("characters", {}))


def _scenario_scope(base_scope: dict, subjects: Sequence[str], locations: Sequence[str]) -> dict:
    scenario = copy.deepcopy(base_scope)
    scenario["variation_subjects"] = list(subjects)
    scenario["variation_locations"] = list(locations)
    return scenario


def _base_from_rows(rows: Sequence[dict], action_pools: Dict[str, list], minimum_actions: int | None = None) -> dict:
    rows_by_location: Dict[str, int] = defaultdict(int)
    subjects = set()
    locations = set()
    missing_pools = set()

    for row in rows:
        subject = str(row.get("subj", "")).strip()
        location = str(row.get("canonical_loc") or row.get("loc") or "").strip()
        if subject:
            subjects.add(subject)
        if not location:
            continue
        locations.add(location)
        rows_by_location[location] += 1
        if location not in action_pools:
            missing_pools.add(location)

    total = 0
    location_stats = []
    for location, row_count in rows_by_location.items():
        action_count = len(action_pools.get(location, []))
        effective_action_count = max(action_count, minimum_actions or 0) if action_count else 0
        contribution = row_count * effective_action_count
        total += contribution
        location_stats.append(
            {
                "location": location,
                "rows": row_count,
                "actions": action_count,
                "effective_actions": effective_action_count,
                "base_variations": contribution,
            }
        )

    return {
        "unique_subjects": len(subjects),
        "unique_locations": len(locations),
        "row_count": len(rows),
        "total_base_variations": total,
        "missing_pools_count": len(missing_pools),
        "missing_pools": sorted(missing_pools),
        "location_stats": sorted(location_stats, key=lambda item: item["base_variations"], reverse=True),
    }


def scenario_metrics(
    subjects: Sequence[str],
    locations: Sequence[str],
    *,
    scope: dict | None = None,
    minimum_actions: int | None = None,
) -> dict:
    scope = scope or load_variation_scope()
    action_pools = _valid_action_pools()
    rows = build_generated_rows(_scenario_scope(scope, subjects, locations))
    return _base_from_rows(rows, action_pools, minimum_actions)


def _delta_row(name: str, metric: dict, baseline: dict) -> dict:
    return {
        "name": name,
        "unique_subjects": metric["unique_subjects"],
        "unique_locations": metric["unique_locations"],
        "row_count": metric["row_count"],
        "total_base_variations": metric["total_base_variations"],
        "delta_base_variations": metric["total_base_variations"] - baseline["total_base_variations"],
    }


def subject_candidate_deltas(scope: dict | None = None, limit: int | None = None) -> List[dict]:
    scope = scope or load_variation_scope()
    current_subjects = list(scope.get("variation_subjects", []))
    current_locations = list(scope.get("variation_locations", []))
    current_subject_set = set(current_subjects)
    baseline = scenario_metrics(current_subjects, current_locations, scope=scope)

    rows = []
    for subject in all_compatible_subjects():
        if subject in current_subject_set:
            continue
        metric = scenario_metrics(current_subjects + [subject], current_locations, scope=scope)
        rows.append(
            {
                "subject": subject,
                "row_delta": metric["row_count"] - baseline["row_count"],
                "base_variation_delta": metric["total_base_variations"] - baseline["total_base_variations"],
            }
        )

    rows.sort(key=lambda item: (-item["base_variation_delta"], item["subject"]))
    return rows if limit is None else rows[:limit]


def location_candidate_deltas(scope: dict | None = None, limit: int | None = None) -> List[dict]:
    scope = scope or load_variation_scope()
    current_subjects = list(scope.get("variation_subjects", []))
    current_locations = list(scope.get("variation_locations", []))
    current_location_set = set(current_locations)
    action_pools = _valid_action_pools()
    baseline = scenario_metrics(current_subjects, current_locations, scope=scope)

    rows = []
    for location in action_backed_compatible_locations(scope):
        if location in current_location_set:
            continue
        metric = scenario_metrics(current_subjects, current_locations + [location], scope=scope)
        base_variation_delta = metric["total_base_variations"] - baseline["total_base_variations"]
        if base_variation_delta <= 0:
            continue
        rows.append(
            {
                "location": location,
                "row_delta": metric["row_count"] - baseline["row_count"],
                "action_count": len(action_pools.get(location, [])),
                "base_variation_delta": base_variation_delta,
            }
        )

    rows.sort(key=lambda item: (-item["base_variation_delta"], item["location"]))
    return rows if limit is None else rows[:limit]


def minimum_action_scenarios(
    subjects: Sequence[str],
    locations: Sequence[str],
    minimum_actions: Iterable[int],
    *,
    scope: dict | None = None,
    target: int = 100000,
) -> List[dict]:
    rows = []
    for minimum in minimum_actions:
        metric = scenario_metrics(subjects, locations, scope=scope, minimum_actions=int(minimum))
        rows.append(
            {
                "minimum_actions": int(minimum),
                "total_base_variations": metric["total_base_variations"],
                "target_gap": target - metric["total_base_variations"],
                "target_met": metric["total_base_variations"] >= target,
            }
        )
    return rows


def build_target_report(
    *,
    target: int = 100000,
    minimum_actions: Sequence[int] = DEFAULT_MINIMUM_ACTIONS,
    top: int = 20,
) -> dict:
    scope = load_variation_scope()
    current_subjects = list(scope.get("variation_subjects", []))
    current_locations = list(scope.get("variation_locations", []))
    known_subjects = all_compatible_subjects()
    action_locations = sorted(set(current_locations) | set(action_backed_compatible_locations(scope)))
    current_metrics = calc_base_metrics(ROOT)

    scenarios = []
    current_scenario = scenario_metrics(current_subjects, current_locations, scope=scope)
    scenarios.append(_delta_row("current_scope", current_scenario, current_scenario))
    scenarios.append(
        _delta_row(
            "all_known_subjects_current_locations",
            scenario_metrics(known_subjects, current_locations, scope=scope),
            current_scenario,
        )
    )
    scenarios.append(
        _delta_row(
            "current_subjects_all_action_backed_compatible_locations",
            scenario_metrics(current_subjects, action_locations, scope=scope),
            current_scenario,
        )
    )
    full_surface = scenario_metrics(known_subjects, action_locations, scope=scope)
    scenarios.append(_delta_row("all_known_subjects_all_action_backed_compatible_locations", full_surface, current_scenario))

    action_scenarios = minimum_action_scenarios(
        known_subjects,
        action_locations,
        minimum_actions,
        scope=scope,
        target=target,
    )
    first_target_met = next((row for row in action_scenarios if row["target_met"]), None)

    return {
        "target": target,
        "current_metrics": {
            "unique_subjects": current_metrics["unique_subjects"],
            "unique_locations": current_metrics["unique_locations"],
            "row_count": current_metrics["row_count"],
            "total_base_variations": current_metrics["total_base_variations"],
            "missing_pools_count": current_metrics["missing_pools_count"],
            "action_count_summary": current_metrics["action_count_summary"],
        },
        "candidate_pool": {
            "known_subjects": len(known_subjects),
            "current_subjects": len(current_subjects),
            "subject_candidates": len(set(known_subjects) - set(current_subjects)),
            "action_backed_compatible_locations": len(action_locations),
            "current_locations": len(current_locations),
            "location_candidates": len(set(action_locations) - set(current_locations)),
        },
        "scenarios": scenarios,
        "minimum_action_scenarios": action_scenarios,
        "first_minimum_action_target_met": first_target_met,
        "top_subject_candidates": subject_candidate_deltas(scope, top),
        "top_location_candidates": location_candidate_deltas(scope, top),
    }


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validation_error(code: str, message: str, **details: Any) -> dict:
    return {"code": code, "message": message, "details": dict(sorted(details.items()))}


def _validate_unique_strings(value: Any, field: str) -> list[dict]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        return [_validation_error("invalid_utility_groups", f"{field} must be an array of non-empty strings", field=field)]
    normalized = [item.strip() for item in value]
    if len(normalized) != len(set(normalized)):
        return [_validation_error("duplicate_utility_group", f"{field} contains duplicates", field=field)]
    return []


def _non_countable_location_pools() -> set[str]:
    try:
        baseline_manifest = _load_l0_baseline_manifest()
        payload = json.loads(L0_POOL_POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowValidationError(
            "pool_policy_unavailable",
            "locked variation location pool policy is unavailable",
            path=str(L0_POOL_POLICY_PATH),
            exception_type=type(exc).__name__,
        ) from exc
    expected_policy_hash = (
        baseline_manifest.get("artifact_hashes", {}).get("pool-policy.json")
        if isinstance(baseline_manifest, dict)
        else None
    )
    actual_policy_hash = hashlib.sha256(L0_POOL_POLICY_PATH.read_bytes()).hexdigest()
    if expected_policy_hash != actual_policy_hash:
        raise WorkflowValidationError(
            "pool_policy_hash_mismatch",
            "locked variation location pool policy hash does not match the L0 baseline manifest",
            expected=expected_policy_hash,
            actual=actual_policy_hash,
        )
    rows = payload.get("non_counted_runtime_pools", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        raise WorkflowValidationError("invalid_pool_policy", "locked pool policy entries must be an array")
    return {
        str(row.get("location", "")).strip()
        for row in rows
        if isinstance(row, dict) and str(row.get("location", "")).strip()
    }


def _load_l0_baseline_manifest() -> dict:
    try:
        payload = json.loads(L0_BASELINE_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowValidationError(
            "baseline_manifest_unavailable",
            "locked V150 baseline manifest is unavailable",
            path=str(L0_BASELINE_MANIFEST_PATH),
            exception_type=type(exc).__name__,
        ) from exc
    if not isinstance(payload, dict):
        raise WorkflowValidationError("invalid_baseline_manifest", "locked V150 baseline manifest must be an object")
    return payload


def validate_locked_input_hashes(
    manifest: Mapping[str, Any] | None = None,
    *,
    root: Path = ROOT,
    protected_paths: Sequence[str] = L0_PROTECTED_INPUT_PATHS,
) -> None:
    """Fail closed when protected L0 data/policy inputs drift."""

    manifest = dict(_load_l0_baseline_manifest() if manifest is None else manifest)
    expected_hashes = manifest.get("input_hashes", {})
    if not isinstance(expected_hashes, Mapping):
        raise WorkflowValidationError("invalid_baseline_input_hashes", "baseline input_hashes must be an object")
    for relative_path in protected_paths:
        expected = expected_hashes.get(relative_path)
        if not isinstance(expected, str):
            raise WorkflowValidationError(
                "missing_baseline_input_hash",
                "protected input is not bound by the baseline manifest",
                path=relative_path,
            )
        path = root / relative_path
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise WorkflowValidationError(
                "baseline_input_unavailable",
                "protected baseline input is unavailable",
                path=relative_path,
                exception_type=type(exc).__name__,
            ) from exc
        if actual != expected:
            raise WorkflowValidationError(
                "baseline_input_hash_mismatch",
                "protected baseline input drifted",
                path=relative_path,
                expected=expected,
                actual=actual,
            )


def validate_projection_scenario(
    payload: Mapping[str, Any],
    baseline: Mapping[str, Any] | None = None,
) -> list[dict]:
    """Return stable validation errors for one hypothetical scenario."""

    if not isinstance(payload, Mapping):
        return [_validation_error("invalid_projection_scenario", "scenario must be a JSON object")]

    errors: list[dict] = []
    unknown = sorted(set(payload) - _SCENARIO_FIELDS)
    if unknown:
        errors.append(_validation_error("unknown_projection_field", "scenario contains unknown fields", fields=unknown))

    scenario_id = payload.get("id")
    if not isinstance(scenario_id, str) or not scenario_id.strip():
        errors.append(_validation_error("missing_scenario_id", "scenario id must be a non-empty string"))

    baseline_subjects = int((baseline or {}).get("unique_subjects", 0) or 0)
    baseline_locations = int((baseline or {}).get("unique_locations", 0) or 0)
    for field, minimum in (("subject_count", baseline_subjects), ("location_count", baseline_locations)):
        value = payload.get(field)
        if not _is_int(value) or value <= 0:
            errors.append(_validation_error("invalid_projection_count", f"{field} must be a positive integer", field=field))
        elif value < minimum:
            errors.append(
                _validation_error(
                    "projection_below_baseline",
                    f"{field} cannot be below the locked baseline",
                    field=field,
                    minimum=minimum,
                    actual=value,
                )
            )

    density = payload.get("compatibility_density_basis_points")
    if not _is_int(density) or density < 1 or density > 10000:
        errors.append(
            _validation_error(
                "invalid_compatibility_density",
                "compatibility density must be integer basis points from 1 through 10000",
            )
        )

    distribution = payload.get("action_depth_row_distribution")
    if not isinstance(distribution, list) or not distribution:
        errors.append(_validation_error("invalid_action_distribution", "action depth distribution must be non-empty"))
    else:
        depths: list[int] = []
        share_total = 0
        for index, bucket in enumerate(distribution):
            if not isinstance(bucket, Mapping):
                errors.append(
                    _validation_error("invalid_action_bucket", "action distribution bucket must be an object", index=index)
                )
                continue
            unknown_bucket = sorted(set(bucket) - _DISTRIBUTION_FIELDS)
            if unknown_bucket:
                errors.append(
                    _validation_error(
                        "unknown_action_bucket_field",
                        "action distribution bucket contains unknown fields",
                        index=index,
                        fields=unknown_bucket,
                    )
                )
            actions = bucket.get("actions")
            share = bucket.get("row_share_basis_points")
            if not _is_int(actions) or actions <= 0:
                errors.append(_validation_error("invalid_action_depth", "actions must be a positive integer", index=index))
            else:
                depths.append(actions)
            if not _is_int(share) or share <= 0 or share > 10000:
                errors.append(
                    _validation_error(
                        "invalid_action_share",
                        "row share must be integer basis points from 1 through 10000",
                        index=index,
                    )
                )
            else:
                share_total += share
        if len(depths) != len(set(depths)):
            errors.append(_validation_error("duplicate_action_depth", "action depth buckets must be unique"))
        if share_total != 10000:
            errors.append(
                _validation_error(
                    "invalid_action_share_total",
                    "action depth row shares must sum to exactly 10000 basis points",
                    actual=share_total,
                )
            )

    for field in ("subject_utility_groups", "location_utility_groups"):
        errors.extend(_validate_unique_strings(payload.get(field), field))

    for field in ("proposed_subject_ids", "proposed_location_ids"):
        errors.extend(_validate_unique_strings(payload.get(field), field))

    proposed_subject_ids = payload.get("proposed_subject_ids")
    proposed_location_ids = payload.get("proposed_location_ids")
    if isinstance(proposed_subject_ids, list) and _is_int(payload.get("subject_count")):
        expected = int(payload["subject_count"]) - baseline_subjects
        if len(proposed_subject_ids) != expected:
            errors.append(
                _validation_error(
                    "proposed_subject_count_mismatch",
                    "proposed_subject_ids must enumerate the complete subject-count increase",
                    expected=expected,
                    actual=len(proposed_subject_ids),
                )
            )
    if isinstance(proposed_location_ids, list) and _is_int(payload.get("location_count")):
        expected = int(payload["location_count"]) - baseline_locations
        if len(proposed_location_ids) != expected:
            errors.append(
                _validation_error(
                    "proposed_location_count_mismatch",
                    "proposed_location_ids must enumerate the complete location-count increase",
                    expected=expected,
                    actual=len(proposed_location_ids),
                )
            )

    scope = load_variation_scope()
    current_subjects = {str(item) for item in scope.get("variation_subjects", [])}
    current_locations = {str(item) for item in scope.get("variation_locations", [])}
    if isinstance(proposed_subject_ids, list):
        existing = sorted({str(item).strip() for item in proposed_subject_ids} & current_subjects)
        if existing:
            errors.append(
                _validation_error(
                    "proposed_subject_already_counted",
                    "proposed subjects must not already exist in the counted scope",
                    subjects=existing,
                )
            )
    if isinstance(proposed_location_ids, list):
        proposed_locations = {str(item).strip() for item in proposed_location_ids}
        existing = sorted(proposed_locations & current_locations)
        if existing:
            errors.append(
                _validation_error(
                    "proposed_location_already_counted",
                    "proposed locations must not already exist in the counted scope",
                    locations=existing,
                )
            )
        blocked = sorted(
            proposed_locations & _non_countable_location_pools()
        )
        if blocked:
            errors.append(
                _validation_error(
                    "non_countable_location_pool",
                    "scenario cannot count alias-compatible, legacy-only, or quality-excluded pools as distinct utilities",
                    locations=blocked,
                )
            )

    notes = payload.get("notes", "")
    if not isinstance(notes, str):
        errors.append(_validation_error("invalid_scenario_notes", "notes must be a string"))
    return errors


def _raise_projection_errors(errors: Sequence[Mapping[str, Any]]) -> None:
    if not errors:
        return
    first = errors[0]
    raise WorkflowValidationError(
        str(first.get("code", "invalid_projection")),
        str(first.get("message", "projection validation failed")),
        errors=list(errors),
    )


def _normalized_projection_scenario(payload: Mapping[str, Any]) -> dict:
    return {
        "id": str(payload["id"]).strip(),
        "subject_count": int(payload["subject_count"]),
        "location_count": int(payload["location_count"]),
        "compatibility_density_basis_points": int(payload["compatibility_density_basis_points"]),
        "action_depth_row_distribution": sorted(
            (
                {
                    "actions": int(bucket["actions"]),
                    "row_share_basis_points": int(bucket["row_share_basis_points"]),
                }
                for bucket in payload["action_depth_row_distribution"]
            ),
            key=lambda item: item["actions"],
        ),
        "proposed_subject_ids": sorted(str(item).strip() for item in payload["proposed_subject_ids"]),
        "proposed_location_ids": sorted(str(item).strip() for item in payload["proposed_location_ids"]),
        "subject_utility_groups": sorted(str(item).strip() for item in payload["subject_utility_groups"]),
        "location_utility_groups": sorted(str(item).strip() for item in payload["location_utility_groups"]),
        "notes": str(payload.get("notes", "")),
    }


def _normalize_projection_manifest(payload: Mapping[str, Any]) -> dict:
    return {
        "schema_version": str(payload["schema_version"]),
        "stage_id": str(payload["stage_id"]).strip(),
        "baseline_manifest_sha256": str(payload["baseline_manifest_sha256"]),
        "scenarios": sorted(
            (_normalized_projection_scenario(item) for item in payload["scenarios"]),
            key=lambda item: item["id"],
        ),
    }


def load_projection_manifest(path: str | Path) -> dict:
    """Load one versioned projection manifest without mutating repository data."""

    candidate = Path(path)
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except OSError as exc:
        raise WorkflowValidationError(
            "projection_manifest_unreadable",
            "projection manifest could not be read",
            path=str(candidate),
            exception_type=type(exc).__name__,
        ) from exc
    except json.JSONDecodeError as exc:
        raise WorkflowValidationError(
            "projection_manifest_invalid_json",
            "projection manifest is not valid JSON",
            path=str(candidate),
            line=exc.lineno,
            column=exc.colno,
        ) from exc
    if not isinstance(payload, dict):
        raise WorkflowValidationError("invalid_projection_manifest", "projection manifest must be a JSON object")
    return payload


def _validate_projection_manifest(payload: Mapping[str, Any], baseline: Mapping[str, Any]) -> dict:
    if not isinstance(payload, Mapping):
        raise WorkflowValidationError("invalid_projection_manifest", "projection manifest must be a JSON object")
    allowed = {"schema_version", "stage_id", "baseline_manifest_sha256", "scenarios"}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise WorkflowValidationError(
            "unknown_projection_manifest_field",
            "projection manifest contains unknown fields",
            fields=unknown,
        )
    if payload.get("schema_version") != PROJECTION_MANIFEST_SCHEMA_VERSION:
        raise WorkflowValidationError(
            "unsupported_projection_schema",
            "projection manifest schema is unsupported",
            actual=payload.get("schema_version"),
            expected=PROJECTION_MANIFEST_SCHEMA_VERSION,
        )
    stage_id = payload.get("stage_id")
    if not isinstance(stage_id, str) or not stage_id.strip():
        raise WorkflowValidationError("missing_projection_stage", "projection stage_id must be a non-empty string")
    if stage_id.strip() != "V150":
        raise WorkflowValidationError(
            "unsupported_projection_stage",
            "L1 projection manifests currently support only the locked V150 stage",
            actual=stage_id.strip(),
            supported=["V150"],
        )
    baseline_hash = payload.get("baseline_manifest_sha256")
    if (
        not isinstance(baseline_hash, str)
        or len(baseline_hash) != 64
        or any(character not in "0123456789abcdef" for character in baseline_hash)
    ):
        raise WorkflowValidationError(
            "invalid_baseline_manifest_hash",
            "baseline_manifest_sha256 must be a lowercase SHA-256 value",
        )
    expected_baseline_hash = baseline.get("baseline_manifest_sha256")
    if expected_baseline_hash is None and str(stage_id).strip() == "V150":
        try:
            expected_baseline_hash = hashlib.sha256(L0_BASELINE_MANIFEST_PATH.read_bytes()).hexdigest()
        except OSError as exc:
            raise WorkflowValidationError(
                "baseline_manifest_unavailable",
                "locked V150 baseline manifest is unavailable",
                path=str(L0_BASELINE_MANIFEST_PATH),
                exception_type=type(exc).__name__,
            ) from exc
    if expected_baseline_hash is not None and baseline_hash != str(expected_baseline_hash):
        raise WorkflowValidationError(
            "baseline_manifest_hash_mismatch",
            "projection baseline manifest hash does not match the locked baseline",
            expected=str(expected_baseline_hash),
            actual=baseline_hash,
        )
    if stage_id.strip() == "V150":
        validate_locked_input_hashes()
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise WorkflowValidationError("missing_projection_scenarios", "projection manifest must contain scenarios")
    errors: list[dict] = []
    ids: list[str] = []
    for index, scenario in enumerate(scenarios):
        scenario_errors = validate_projection_scenario(scenario, baseline)
        for error in scenario_errors:
            error = dict(error)
            error["scenario_index"] = index
            errors.append(error)
        if isinstance(scenario, Mapping) and isinstance(scenario.get("id"), str):
            ids.append(str(scenario["id"]).strip())
    if len(ids) != len(set(ids)):
        errors.append(_validation_error("duplicate_scenario_id", "scenario ids must be unique"))
    _raise_projection_errors(errors)
    return _normalize_projection_manifest(payload)


def _allocate_action_depth_rows(projected_rows: int, distribution: Sequence[Mapping[str, Any]]) -> list[dict]:
    allocation = []
    allocated_rows = 0
    for bucket in sorted(distribution, key=lambda item: int(item["actions"])):
        numerator = projected_rows * int(bucket["row_share_basis_points"])
        rows = numerator // 10000
        allocated_rows += rows
        allocation.append(
            {
                "actions": int(bucket["actions"]),
                "row_share_basis_points": int(bucket["row_share_basis_points"]),
                "rows": rows,
                "remainder": numerator % 10000,
            }
        )
    remaining = projected_rows - allocated_rows
    remainder_order = sorted(
        range(len(allocation)),
        key=lambda index: (-allocation[index]["remainder"], allocation[index]["actions"]),
    )
    for index in remainder_order[:remaining]:
        allocation[index]["rows"] += 1
    for bucket in allocation:
        bucket["base_variations"] = bucket["rows"] * bucket["actions"]
        bucket.pop("remainder", None)
    return allocation


def project_hypothetical_scenario(
    payload: Mapping[str, Any],
    *,
    baseline: Mapping[str, Any],
    target: int = 100000,
) -> dict:
    """Project one validated mixed scenario using integer-only deterministic math."""

    if not _is_int(target) or target <= 0:
        raise WorkflowValidationError("invalid_projection_target", "projection target must be a positive integer")
    _raise_projection_errors(validate_projection_scenario(payload, baseline))
    scenario = _normalized_projection_scenario(payload)
    eligible_pairs = scenario["subject_count"] * scenario["location_count"]
    projected_rows = eligible_pairs * scenario["compatibility_density_basis_points"] // 10000
    allocation = _allocate_action_depth_rows(projected_rows, scenario["action_depth_row_distribution"])
    projected_base_variations = sum(bucket["base_variations"] for bucket in allocation)
    baseline_variations = int(baseline.get("total_base_variations", 0) or 0)
    return {
        "id": scenario["id"],
        "subject_count": scenario["subject_count"],
        "location_count": scenario["location_count"],
        "eligible_pairs": eligible_pairs,
        "projected_rows": projected_rows,
        "realized_density_basis_points": projected_rows * 10000 // eligible_pairs,
        "action_depth_allocation": allocation,
        "projected_base_variations": projected_base_variations,
        "delta_base_variations": projected_base_variations - baseline_variations,
        "target_gap": target - projected_base_variations,
        "target_met": projected_base_variations >= target,
        "proposed_subject_ids": scenario["proposed_subject_ids"],
        "proposed_location_ids": scenario["proposed_location_ids"],
        "subject_utility_groups": scenario["subject_utility_groups"],
        "location_utility_groups": scenario["location_utility_groups"],
        "notes": scenario["notes"],
    }


def build_projection_report(
    manifest: Mapping[str, Any],
    *,
    target: int,
    baseline: Mapping[str, Any] | None = None,
) -> dict:
    """Build an order-stable, content-addressed hypothetical projection report."""

    if not _is_int(target) or target <= 0:
        raise WorkflowValidationError("invalid_projection_target", "projection target must be a positive integer")
    if baseline is None:
        baseline = build_target_report(target=target)["current_metrics"]
    normalized = _validate_projection_manifest(manifest, baseline)
    if normalized["stage_id"] == "V150" and target != 150000:
        raise WorkflowValidationError(
            "projection_stage_target_mismatch",
            "V150 projection manifests require target 150000",
            expected=150000,
            actual=target,
        )
    scenarios = [
        project_hypothetical_scenario(item, baseline=baseline, target=target)
        for item in normalized["scenarios"]
    ]
    return {
        "schema_version": PROJECTION_REPORT_SCHEMA_VERSION,
        "stage_id": normalized["stage_id"],
        "target": target,
        "baseline_manifest_sha256": normalized["baseline_manifest_sha256"],
        "scenario_manifest_sha256": hashlib.sha256(canonical_json_bytes(normalized)).hexdigest(),
        "planner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "projection_model_version": PROJECTION_MODEL_VERSION,
        "baseline_metrics": {
            "unique_subjects": int(baseline.get("unique_subjects", 0) or 0),
            "unique_locations": int(baseline.get("unique_locations", 0) or 0),
            "row_count": int(baseline.get("row_count", 0) or 0),
            "total_base_variations": int(baseline.get("total_base_variations", 0) or 0),
        },
        "hypothetical_scenarios": scenarios,
    }


def _parse_minimum_actions(values: str) -> List[int]:
    actions = []
    for value in values.split(","):
        value = value.strip()
        if value:
            actions.append(int(value))
    if not actions:
        raise WorkflowValidationError("missing_minimum_actions", "minimum-actions must contain at least one value")
    if any(value <= 0 for value in actions):
        raise WorkflowValidationError("invalid_minimum_action", "minimum action counts must be positive integers")
    if len(actions) != len(set(actions)):
        raise WorkflowValidationError("duplicate_minimum_action", "minimum action counts must be unique")
    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan variation expansion scenarios without writing data files.")
    parser.add_argument("--target", type=int, default=100000, help="Target base variation count.")
    parser.add_argument("--top", type=int, default=20, help="Number of candidate delta rows to include.")
    parser.add_argument(
        "--minimum-actions",
        default=",".join(str(value) for value in DEFAULT_MINIMUM_ACTIONS),
        help="Comma-separated minimum action counts to simulate.",
    )
    parser.add_argument(
        "--scenario-file",
        help="Optional versioned JSON manifest for pure hypothetical projection scenarios.",
    )
    args = parser.parse_args()

    try:
        if args.target <= 0:
            raise WorkflowValidationError("invalid_target", "target must be a positive integer")
        if args.top < 0:
            raise WorkflowValidationError("invalid_top_limit", "top must be zero or greater")
        report = build_target_report(
            target=args.target,
            minimum_actions=_parse_minimum_actions(args.minimum_actions),
            top=args.top,
        )
        if args.scenario_file:
            report["projection"] = build_projection_report(
                load_projection_manifest(args.scenario_file),
                target=args.target,
                baseline=report["current_metrics"],
            )
    except (ValueError, WorkflowValidationError) as exc:
        envelope = (
            exc.to_envelope()
            if isinstance(exc, WorkflowValidationError)
            else WorkflowValidationError(
                "invalid_cli_value",
                "planner CLI value is invalid",
                exception_type=type(exc).__name__,
            ).to_envelope()
        )
        sys.stderr.buffer.write(canonical_json_bytes(envelope))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
