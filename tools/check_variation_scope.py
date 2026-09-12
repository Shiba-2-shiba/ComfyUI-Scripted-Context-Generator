from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from assets.calc_variations import calc_base_metrics
from registry import load_action_pools, load_background_packs, load_scene_compatibility, resolve_location_alias_map


SCOPE_PATH = ROOT / "vocab" / "data" / "variation_scope.json"
CSV_PATH = ROOT / "assets" / "compatibility_review.csv"


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_variation_scope(path: Path = SCOPE_PATH) -> Dict[str, Any]:
    return _load_json(path)


def _csv_subjects_and_locations(path: Path = CSV_PATH) -> tuple[Set[str], Set[str], int]:
    subjects: Set[str] = set()
    locations: Set[str] = set()
    row_count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            row_count += 1
            subject = str(row.get("subj") or "").strip()
            location = str(row.get("canonical_loc") or row.get("loc") or "").strip()
            if subject:
                subjects.add(subject)
            if location:
                locations.add(location)
    return subjects, locations, row_count


def _duplicates(values: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    duplicated: Set[str] = set()
    for value in values:
        if value in seen:
            duplicated.add(value)
        seen.add(value)
    return sorted(duplicated)


def build_scope_report() -> Dict[str, List[dict]]:
    report: Dict[str, List[dict]] = {"ERROR": [], "WARNING": [], "INFO": []}
    scope = load_variation_scope()
    subjects = list(scope.get("variation_subjects", []))
    locations = list(scope.get("variation_locations", []))
    scope_subjects = set(subjects)
    scope_locations = set(locations)
    csv_subjects, csv_locations, csv_row_count = _csv_subjects_and_locations()

    if scope.get("schema_version") != "1.0":
        report["ERROR"].append({"code": "unsupported_variation_scope_schema", "value": scope.get("schema_version")})

    duplicate_subjects = _duplicates(subjects)
    if duplicate_subjects:
        report["ERROR"].append({"code": "duplicate_variation_subjects", "subjects": duplicate_subjects})

    duplicate_locations = _duplicates(locations)
    if duplicate_locations:
        report["ERROR"].append({"code": "duplicate_variation_locations", "locations": duplicate_locations})

    compatibility = load_scene_compatibility()
    compat_subjects = set(compatibility.get("characters", {}))
    missing_compat_subjects = sorted(scope_subjects - compat_subjects)
    if missing_compat_subjects:
        report["ERROR"].append({"code": "scope_subject_missing_from_scene_compatibility", "subjects": missing_compat_subjects})

    compatibility_locations = set(compatibility.get("locations", []))
    action_pools = load_action_pools()
    background_packs = load_background_packs()
    alias_map = resolve_location_alias_map()
    location_sources = compatibility_locations | set(action_pools) | set(background_packs) | set(alias_map)
    missing_location_sources = sorted(scope_locations - location_sources)
    if missing_location_sources:
        report["ERROR"].append({"code": "scope_location_missing_from_known_sources", "locations": missing_location_sources})

    missing_background_packs = sorted(scope_locations - set(background_packs) - set(alias_map))
    if missing_background_packs:
        report["WARNING"].append({"code": "scope_location_missing_background_pack", "locations": missing_background_packs})

    csv_subject_extras = sorted(csv_subjects - scope_subjects)
    if csv_subject_extras:
        report["ERROR"].append({"code": "compatibility_review_subject_outside_scope", "subjects": csv_subject_extras})

    csv_location_extras = sorted(csv_locations - scope_locations)
    if csv_location_extras:
        report["ERROR"].append({"code": "compatibility_review_location_outside_scope", "locations": csv_location_extras})

    missing_csv_subjects = sorted(scope_subjects - csv_subjects)
    if missing_csv_subjects:
        report["ERROR"].append({"code": "scope_subject_missing_from_compatibility_review", "subjects": missing_csv_subjects})

    missing_csv_locations = sorted(scope_locations - csv_locations)
    if missing_csv_locations:
        report["ERROR"].append({"code": "scope_location_missing_from_compatibility_review", "locations": missing_csv_locations})

    metrics = calc_base_metrics(ROOT)
    expected = scope.get("expected_metrics", {})
    metric_key_map = {
        "unique_subjects": "unique_subjects",
        "unique_locations": "unique_locations",
        "row_count": "row_count",
        "total_base_variations": "total_base_variations",
    }
    for scope_key, metric_key in metric_key_map.items():
        if scope_key in expected and expected[scope_key] != metrics.get(metric_key):
            report["ERROR"].append(
                {
                    "code": "variation_scope_metric_mismatch",
                    "metric": scope_key,
                    "expected": expected[scope_key],
                    "actual": metrics.get(metric_key),
                }
            )

    report["INFO"].append(
        {
            "code": "variation_scope_summary",
            "scope_subject_count": len(scope_subjects),
            "scope_location_count": len(scope_locations),
            "compatibility_review_subject_count": len(csv_subjects),
            "compatibility_review_location_count": len(csv_locations),
            "compatibility_review_row_count": csv_row_count,
            "total_base_variations": metrics["total_base_variations"],
        }
    )
    return report


def main() -> int:
    report = build_scope_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
