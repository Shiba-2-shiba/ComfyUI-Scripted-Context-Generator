from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from assets.calc_variations import calc_base_metrics, is_action_pool_location_key
from registry import load_action_pools, load_scene_compatibility, resolve_location_alias_map
from tools.build_compatibility_review import build_generated_rows, resolve_canonical_location
from tools.check_variation_scope import load_variation_scope


DEFAULT_MINIMUM_ACTIONS = [12, 16, 20, 24, 32, 35]


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


def _parse_minimum_actions(values: str) -> List[int]:
    actions = []
    for value in values.split(","):
        value = value.strip()
        if value:
            actions.append(int(value))
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
    args = parser.parse_args()

    report = build_target_report(
        target=args.target,
        minimum_actions=_parse_minimum_actions(args.minimum_actions),
        top=args.top,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
