from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _get_number(payload: Dict[str, Any], *path: str) -> int | float:
    value: Any = payload
    for key in path:
        if not isinstance(value, dict):
            return 0
        value = value.get(key, 0)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    return 0


def _delta_row(before: Dict[str, Any], after: Dict[str, Any], label: str, *path: str) -> Dict[str, Any]:
    before_value = _get_number(before, *path)
    after_value = _get_number(after, *path)
    return {
        "metric": label,
        "before": before_value,
        "after": after_value,
        "delta": after_value - before_value,
    }


def build_expansion_delta(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    rows = [
        _delta_row(before, after, "unique_subjects", "base", "unique_subjects"),
        _delta_row(before, after, "unique_locations", "base", "unique_locations"),
        _delta_row(before, after, "base_variations", "base", "total_base_variations"),
        _delta_row(before, after, "missing_pools_count", "base", "missing_pools_count"),
        _delta_row(before, after, "mood_keys", "garnish", "mood_keys"),
        _delta_row(before, after, "mood_tags_unique", "garnish", "mood_tags_unique"),
        _delta_row(before, after, "micro_actions_unique", "garnish", "micro_actions_unique"),
        _delta_row(before, after, "background_context_tags_unique", "garnish", "background_context_tags_unique"),
        _delta_row(before, after, "semantic_units_unique", "garnish", "semantic_units_unique"),
        _delta_row(before, after, "garnish_universe_size", "combined", "garnish_universe_size"),
        _delta_row(before, after, "theoretical_upper_bound", "combined", "theoretical_upper_bound"),
    ]
    regressions = [
        row
        for row in rows
        if row["metric"] != "missing_pools_count" and row["delta"] < 0
    ]
    missing_pool_delta = next((row for row in rows if row["metric"] == "missing_pools_count"), None)
    if missing_pool_delta and missing_pool_delta["delta"] > 0:
        regressions.append(missing_pool_delta)

    return {
        "summary": {
            "passed": not regressions,
            "regression_count": len(regressions),
        },
        "metrics": rows,
        "regressions": regressions,
    }


def format_delta_report(delta: Dict[str, Any]) -> str:
    lines = ["Expansion delta report", "======================", ""]
    for row in delta.get("metrics", []):
        lines.append(
            f"- {row['metric']}: {row['before']} -> {row['after']} "
            f"(delta {row['delta']:+})"
        )
    regressions = delta.get("regressions", [])
    lines.append("")
    lines.append(f"Status: {'PASS' if not regressions else 'WARN'}")
    if regressions:
        lines.append("Regressions:")
        for row in regressions:
            lines.append(f"- {row['metric']}: delta {row['delta']:+}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two calc_variations.py JSON reports")
    parser.add_argument("before", help="Path to baseline JSON from assets/calc_variations.py --json")
    parser.add_argument("after", help="Path to current JSON from assets/calc_variations.py --json")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--enforce", action="store_true", help="Return nonzero when expansion metrics regress")
    args = parser.parse_args()

    delta = build_expansion_delta(_read_json(Path(args.before)), _read_json(Path(args.after)))
    if args.json:
        print(json.dumps(delta, ensure_ascii=False, indent=2))
    else:
        print(format_delta_report(delta))
    return 1 if args.enforce and not delta["summary"]["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
