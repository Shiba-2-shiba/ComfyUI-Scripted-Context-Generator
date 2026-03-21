from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.action_generator import action_verb, generate_action_for_location  # noqa: E402
from registry import load_action_pools, load_scene_compatibility, load_scene_axes  # noqa: E402


SEED_COUNT_DEFAULT = 32
LOW_DIVERSITY_UNIQUE_RATE = 0.50
LOW_DIVERSITY_SLOT_RATE = 0.40
MIN_AVG_UNIQUE_ACTION_RATE = 0.95
MIN_AVG_UNIQUE_SLOT_RATE = 0.95
MIN_LOCATION_UNIQUE_ACTION_RATE = 0.95
MIN_LOCATION_UNIQUE_SLOT_RATE = 0.93
MAX_LOW_DIVERSITY_LOCATIONS = 0


def _iter_audit_locations(compatibility: Dict[str, Any], scope: str) -> Iterable[str]:
    seen = set()
    if scope in {"daily_life", "all"}:
        for loc in compatibility.get("daily_life_locs", []):
            if loc not in seen:
                seen.add(loc)
                yield str(loc)
    if scope == "all":
        for loc in compatibility.get("universal_locs", []):
            if loc not in seen:
                seen.add(loc)
                yield str(loc)
        for locs in compatibility.get("loc_tags", {}).values():
            for loc in locs:
                if loc not in seen:
                    seen.add(loc)
                    yield str(loc)


def _usable_pool(action_pools: Dict[str, Any], loc: str):
    pool = action_pools.get(loc, [])
    return [item for item in pool if not isinstance(item, str) or not item.startswith("_")]


def _slot_signature(slots: Dict[str, Any]) -> str:
    return "|".join(
        [
            str(slots.get("purpose", "")),
            str(slots.get("progress_state", "")),
            str(slots.get("social_distance", "")),
            str(slots.get("obstacle_or_trigger", "")),
            str(slots.get("posture", "")),
            str(slots.get("hand_action", "")),
            str(slots.get("gaze_target", "")),
        ]
    )


def _audit_location(
    loc: str,
    compatibility: Dict[str, Any],
    action_pools: Dict[str, Any],
    scene_axes: Dict[str, Any],
    seed_count: int,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    pool = _usable_pool(action_pools, loc)
    generator_modes = Counter()
    slot_sources_seen = Counter()
    object_focus_hits = Counter()

    for seed in range(seed_count):
        action_text, debug = generate_action_for_location(
            loc,
            compatibility,
            scene_axes,
            random.Random(seed),
            pool=pool or None,
        )
        slots = debug.get("slots", {}) or {}
        object_focus = debug.get("object_focus", {}) or {}
        rows.append(
            {
                "seed": seed,
                "action": action_text,
                "verb": action_verb(action_text),
                "mode": str(debug.get("generator_mode", "")),
                "slot_signature": _slot_signature(slots),
                "purpose": str(slots.get("purpose", "")),
                "progress_state": str(slots.get("progress_state", "")),
                "social_distance": str(slots.get("social_distance", "")),
                "object_focus": object_focus,
            }
        )
        generator_modes[str(debug.get("generator_mode", ""))] += 1
        for source in (debug.get("slot_sources", {}) or {}).values():
            slot_sources_seen[str(source)] += 1
        for token in (object_focus.get("detected_objects", []) or []):
            object_focus_hits[str(token)] += 1

    action_counter = Counter(row["action"] for row in rows)
    verb_counter = Counter(row["verb"] for row in rows if row["verb"])
    slot_counter = Counter(row["slot_signature"] for row in rows if row["slot_signature"])

    unique_action_count = len(action_counter)
    unique_verb_count = len(verb_counter)
    unique_slot_signature_count = len(slot_counter)

    report = {
        "location": loc,
        "seed_count": seed_count,
        "generator_modes": dict(generator_modes),
        "has_pool": bool(pool),
        "unique_action_count": unique_action_count,
        "unique_action_rate": round(unique_action_count / seed_count, 4),
        "duplicate_action_rate": round(1.0 - (unique_action_count / seed_count), 4),
        "unique_verb_count": unique_verb_count,
        "unique_verb_rate": round(unique_verb_count / seed_count, 4),
        "unique_slot_signature_count": unique_slot_signature_count,
        "unique_slot_signature_rate": round(unique_slot_signature_count / seed_count, 4),
        "top_actions": [{"text": text, "count": count} for text, count in action_counter.most_common(5)],
        "top_verbs": [{"verb": text, "count": count} for text, count in verb_counter.most_common(5)],
        "slot_source_counts": dict(slot_sources_seen),
        "object_focus_counts": dict(object_focus_hits),
        "low_diversity": (unique_action_count / seed_count) < LOW_DIVERSITY_UNIQUE_RATE
        or (unique_slot_signature_count / seed_count) < LOW_DIVERSITY_SLOT_RATE,
        "samples": rows[:5],
    }
    return report


def build_action_diversity_report(scope: str = "daily_life", seed_count: int = SEED_COUNT_DEFAULT) -> Dict[str, Any]:
    compatibility = load_scene_compatibility()
    action_pools = load_action_pools()
    scene_axes = load_scene_axes()

    location_reports = [
        _audit_location(loc, compatibility, action_pools, scene_axes, seed_count)
        for loc in _iter_audit_locations(compatibility, scope)
    ]

    if not location_reports:
        return {
            "scope": scope,
            "seed_count": seed_count,
            "summary": {},
            "locations": [],
        }

    avg_unique_action_rate = sum(item["unique_action_rate"] for item in location_reports) / len(location_reports)
    avg_unique_slot_rate = sum(item["unique_slot_signature_rate"] for item in location_reports) / len(location_reports)
    low_diversity_locations = [item["location"] for item in location_reports if item["low_diversity"]]

    summary = {
        "location_count": len(location_reports),
        "avg_unique_action_rate": round(avg_unique_action_rate, 4),
        "avg_unique_slot_signature_rate": round(avg_unique_slot_rate, 4),
        "min_unique_action_rate": round(min(item["unique_action_rate"] for item in location_reports), 4),
        "min_unique_slot_signature_rate": round(min(item["unique_slot_signature_rate"] for item in location_reports), 4),
        "low_diversity_location_count": len(low_diversity_locations),
        "low_diversity_locations": low_diversity_locations,
    }
    return {
        "scope": scope,
        "seed_count": seed_count,
        "summary": summary,
        "locations": location_reports,
    }


def evaluate_action_diversity_thresholds(
    report: Dict[str, Any],
    min_avg_unique_action_rate: float = MIN_AVG_UNIQUE_ACTION_RATE,
    min_avg_unique_slot_rate: float = MIN_AVG_UNIQUE_SLOT_RATE,
    min_location_unique_action_rate: float = MIN_LOCATION_UNIQUE_ACTION_RATE,
    min_location_unique_slot_rate: float = MIN_LOCATION_UNIQUE_SLOT_RATE,
    max_low_diversity_locations: int = MAX_LOW_DIVERSITY_LOCATIONS,
) -> Dict[str, Any]:
    summary = report.get("summary", {}) or {}
    locations = report.get("locations", []) or []
    failures: List[Dict[str, Any]] = []

    if float(summary.get("avg_unique_action_rate", 0.0)) < float(min_avg_unique_action_rate):
        failures.append(
            {
                "code": "avg_unique_action_rate_below_threshold",
                "expected_gte": float(min_avg_unique_action_rate),
                "actual": float(summary.get("avg_unique_action_rate", 0.0)),
            }
        )
    if float(summary.get("avg_unique_slot_signature_rate", 0.0)) < float(min_avg_unique_slot_rate):
        failures.append(
            {
                "code": "avg_unique_slot_rate_below_threshold",
                "expected_gte": float(min_avg_unique_slot_rate),
                "actual": float(summary.get("avg_unique_slot_signature_rate", 0.0)),
            }
        )
    if float(summary.get("low_diversity_location_count", 0)) > int(max_low_diversity_locations):
        failures.append(
            {
                "code": "too_many_low_diversity_locations",
                "expected_lte": int(max_low_diversity_locations),
                "actual": int(summary.get("low_diversity_location_count", 0)),
            }
        )

    low_action_locations = [
        item["location"]
        for item in locations
        if float(item.get("unique_action_rate", 0.0)) < float(min_location_unique_action_rate)
    ]
    if low_action_locations:
        failures.append(
            {
                "code": "location_unique_action_rate_below_threshold",
                "expected_gte": float(min_location_unique_action_rate),
                "locations": low_action_locations,
            }
        )

    low_slot_locations = [
        item["location"]
        for item in locations
        if float(item.get("unique_slot_signature_rate", 0.0)) < float(min_location_unique_slot_rate)
    ]
    if low_slot_locations:
        failures.append(
            {
                "code": "location_unique_slot_rate_below_threshold",
                "expected_gte": float(min_location_unique_slot_rate),
                "locations": low_slot_locations,
            }
        )

    thresholds = {
        "min_avg_unique_action_rate": float(min_avg_unique_action_rate),
        "min_avg_unique_slot_rate": float(min_avg_unique_slot_rate),
        "min_location_unique_action_rate": float(min_location_unique_action_rate),
        "min_location_unique_slot_rate": float(min_location_unique_slot_rate),
        "max_low_diversity_locations": int(max_low_diversity_locations),
    }
    return {
        "passed": not failures,
        "thresholds": thresholds,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit 32-seed action diversity for Phase 3 quality checks")
    parser.add_argument("--scope", choices=["daily_life", "all"], default="daily_life")
    parser.add_argument("--seed-count", type=int, default=SEED_COUNT_DEFAULT)
    parser.add_argument("--output", default="")
    parser.add_argument("--enforce-thresholds", action="store_true")
    args = parser.parse_args()

    report = build_action_diversity_report(scope=args.scope, seed_count=args.seed_count)
    report["threshold_evaluation"] = evaluate_action_diversity_thresholds(report)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    print(text)
    if args.enforce_thresholds and not report["threshold_evaluation"]["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
