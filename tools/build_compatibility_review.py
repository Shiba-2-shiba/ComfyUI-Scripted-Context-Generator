from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from registry import load_scene_compatibility, resolve_location_alias_map
from tools.check_variation_scope import CSV_PATH, load_variation_scope


FIELDNAMES = ["subj", "loc", "canonical_loc", "source", "source_tag", "is_tag", "is_universal", "is_existing", "is_alias", "costume"]
DEFAULT_OUTPUT_PATH = ROOT / "assets" / "compatibility_review.generated.csv"
PROMPTS_PATH = ROOT / "prompts.jsonl"


def _normal_key(value: str) -> str:
    return str(value or "").strip().lower()


def _generation_config(scope: dict) -> dict:
    return scope.get("compatibility_review_generation", {}) if isinstance(scope, dict) else {}


def _canonical_overrides(scope: dict) -> Dict[str, str]:
    overrides = _generation_config(scope).get("canonical_location_overrides", {})
    if not isinstance(overrides, dict):
        return {}
    return {str(key): str(value) for key, value in overrides.items()}


def _excluded_pairs(scope: dict) -> set[Tuple[str, str]]:
    pairs = _generation_config(scope).get("excluded_pairs", [])
    excluded: set[Tuple[str, str]] = set()
    if not isinstance(pairs, list):
        return excluded
    for pair in pairs:
        if not isinstance(pair, dict):
            continue
        subject = str(pair.get("subj", "")).strip()
        location = str(pair.get("canonical_loc", "")).strip()
        if subject and location:
            excluded.add((subject, location))
    return excluded


def resolve_canonical_location(
    location: str,
    aliases: Dict[str, List[str]],
    canonical_locations: set[str] | None = None,
    canonical_overrides: Dict[str, str] | None = None,
) -> str:
    raw = str(location or "").strip()
    if canonical_overrides and raw in canonical_overrides:
        return canonical_overrides[raw]
    if canonical_locations and raw in canonical_locations:
        return raw
    targets = aliases.get(_normal_key(raw))
    if targets:
        return str(targets[0]).strip()
    return raw


def _load_prompt_rows(path: Path = PROMPTS_PATH) -> List[dict]:
    if not path.exists():
        return []
    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


def _row_key(row: dict) -> Tuple[str, ...]:
    return tuple(str(row.get(field, "")) for field in FIELDNAMES)


def _pair_key(row: dict) -> Tuple[str, str]:
    return (str(row.get("subj", "")), str(row.get("canonical_loc", "")))


def _normalize_rows(rows: Iterable[dict]) -> List[dict]:
    return [{field: str(row.get(field, "")) for field in FIELDNAMES} for row in rows]


def _sort_rows(rows: Iterable[dict]) -> List[dict]:
    return sorted(_normalize_rows(rows), key=lambda row: (row["subj"], row["canonical_loc"], row["source"], row["loc"]))


def build_exclusion_set(compatibility: dict, aliases: Dict[str, List[str]]) -> set[Tuple[str, str]]:
    excluded: set[Tuple[str, str]] = set()
    for rule in compatibility.get("exclusions", []):
        for subject in rule.get("characters", []):
            for location in rule.get("denied_locs", []):
                excluded.add((str(subject), resolve_canonical_location(str(location), aliases)))
    return excluded


def build_existing_prompt_map(scope: dict, aliases: Dict[str, List[str]]) -> Tuple[Dict[Tuple[str, str], dict], List[dict]]:
    scope_subjects = set(scope.get("variation_subjects", []))
    scope_locations = set(scope.get("variation_locations", []))
    existing: Dict[Tuple[str, str], dict] = {}
    skipped: List[dict] = []

    for prompt in _load_prompt_rows():
        subject = str(prompt.get("subj", "")).strip()
        original_location = str(prompt.get("loc", "")).strip()
        canonical_location = resolve_canonical_location(original_location, aliases, scope_locations)
        if subject not in scope_subjects or canonical_location not in scope_locations:
            skipped.append({"subj": subject, "loc": original_location, "canonical_loc": canonical_location})
            continue
        existing[(subject, canonical_location)] = {
            "subj": subject,
            "loc": original_location,
            "canonical_loc": canonical_location,
            "source": "existing",
            "source_tag": "",
            "is_tag": "0",
            "is_universal": "0",
            "is_existing": "1",
            "is_alias": "1" if canonical_location != original_location else "0",
            "costume": str(prompt.get("costume", "")).strip(),
        }

    return existing, skipped


def _compatible_locations_for_subject(
    subject: str,
    subject_info: dict,
    compatibility: dict,
    aliases: Dict[str, List[str]],
    excluded: set[Tuple[str, str]],
    canonical_locations: set[str],
    canonical_overrides: Dict[str, str],
) -> Dict[str, dict]:
    compatible: Dict[str, dict] = {}

    for location in compatibility.get("universal_locs", []):
        canonical_location = resolve_canonical_location(str(location), aliases, canonical_locations, canonical_overrides)
        if (subject, canonical_location) not in excluded:
            compatible.setdefault(
                canonical_location,
                {"type": "universal", "tag": "", "original": str(location)},
            )

    for tag in subject_info.get("tags", []):
        tag_text = str(tag)
        for location in compatibility.get("loc_tags", {}).get(tag_text, []):
            canonical_location = resolve_canonical_location(str(location), aliases, canonical_locations, canonical_overrides)
            if (subject, canonical_location) not in excluded:
                compatible[canonical_location] = {"type": "tag", "tag": tag_text, "original": str(location)}

    return compatible


def build_generated_rows(scope: dict | None = None) -> List[dict]:
    scope = scope or load_variation_scope()
    scope_subjects = set(scope.get("variation_subjects", []))
    scope_locations = set(scope.get("variation_locations", []))
    compatibility = load_scene_compatibility()
    aliases = resolve_location_alias_map()
    excluded = build_exclusion_set(compatibility, aliases)
    excluded.update(_excluded_pairs(scope))
    canonical_overrides = _canonical_overrides(scope)
    existing_prompts, _skipped = build_existing_prompt_map(scope, aliases)

    rows: List[dict] = []
    for subject in scope.get("variation_subjects", []):
        if subject not in scope_subjects:
            continue
        subject_info = compatibility.get("characters", {}).get(subject)
        if not subject_info:
            continue

        compatible = _compatible_locations_for_subject(
            subject,
            subject_info,
            compatibility,
            aliases,
            excluded,
            scope_locations,
            canonical_overrides,
        )
        for canonical_location, meta in compatible.items():
            if canonical_location not in scope_locations:
                continue
            if (subject, canonical_location) in excluded:
                continue
            existing_row = existing_prompts.get((subject, canonical_location))
            if existing_row:
                rows.append(existing_row)
                continue
            source_type = str(meta["type"])
            source_tag = str(meta.get("tag", ""))
            original_location = str(meta["original"])
            rows.append(
                {
                    "subj": subject,
                    "loc": original_location,
                    "canonical_loc": canonical_location,
                    "source": f"{source_type}:{source_tag}" if source_tag else source_type,
                    "source_tag": source_tag,
                    "is_tag": "1" if source_type == "tag" else "0",
                    "is_universal": "1" if source_type == "universal" else "0",
                    "is_existing": "0",
                    "is_alias": "1" if canonical_location != original_location else "0",
                    "costume": str(subject_info.get("default_costume", "")).strip(),
                }
            )

        for (existing_subject, canonical_location), existing_row in existing_prompts.items():
            if (
                existing_subject == subject
                and canonical_location not in compatible
                and (existing_subject, canonical_location) not in excluded
            ):
                rows.append(existing_row)

    return _sort_rows(rows)


def read_compatibility_rows(path: Path = CSV_PATH) -> List[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return _sort_rows(csv.DictReader(handle))


def compare_rows(generated_rows: Sequence[dict], current_rows: Sequence[dict]) -> dict:
    generated_keys = {_row_key(row) for row in generated_rows}
    current_keys = {_row_key(row) for row in current_rows}
    generated_pairs = {_pair_key(row) for row in generated_rows}
    current_pairs = {_pair_key(row) for row in current_rows}
    missing_from_generated = sorted(current_keys - generated_keys)
    extra_generated = sorted(generated_keys - current_keys)
    missing_pairs = sorted(current_pairs - generated_pairs)
    extra_pairs = sorted(generated_pairs - current_pairs)
    return {
        "missing_from_generated": missing_from_generated,
        "extra_generated": extra_generated,
        "missing_pairs": missing_pairs,
        "extra_pairs": extra_pairs,
        "order_matches": [_row_key(row) for row in generated_rows] == [_row_key(row) for row in current_rows],
    }


def _sample_tuples(rows: Sequence[Tuple[str, ...]], limit: int = 12) -> List[dict]:
    return [dict(zip(FIELDNAMES, row)) for row in rows[:limit]]


def _sample_pairs(rows: Sequence[Tuple[str, str]], limit: int = 12) -> List[dict]:
    return [{"subj": subject, "canonical_loc": location} for subject, location in rows[:limit]]


def build_check_report() -> Dict[str, List[dict]]:
    report: Dict[str, List[dict]] = {"ERROR": [], "WARNING": [], "INFO": []}
    scope = load_variation_scope()
    aliases = resolve_location_alias_map()
    generated_rows = build_generated_rows(scope)
    current_rows = read_compatibility_rows()
    diff = compare_rows(generated_rows, current_rows)
    _existing_prompts, skipped_prompts = build_existing_prompt_map(scope, aliases)

    scope_subjects = set(scope.get("variation_subjects", []))
    scope_locations = set(scope.get("variation_locations", []))
    generated_subject_extras = sorted({row["subj"] for row in generated_rows} - scope_subjects)
    generated_location_extras = sorted({row["canonical_loc"] for row in generated_rows} - scope_locations)
    if generated_subject_extras or generated_location_extras:
        report["ERROR"].append(
            {
                "code": "generated_rows_outside_variation_scope",
                "subjects": generated_subject_extras,
                "locations": generated_location_extras,
            }
        )

    missing_count = len(diff["missing_from_generated"])
    extra_count = len(diff["extra_generated"])
    missing_pair_count = len(diff["missing_pairs"])
    extra_pair_count = len(diff["extra_pairs"])
    drift_payload = {
        "missing_current_rows": missing_count,
        "extra_generated_rows": extra_count,
        "missing_current_pairs": missing_pair_count,
        "extra_generated_pairs": extra_pair_count,
        "order_matches": diff["order_matches"],
        "missing_current_row_sample": _sample_tuples(diff["missing_from_generated"]),
        "extra_generated_row_sample": _sample_tuples(diff["extra_generated"]),
        "missing_current_pair_sample": _sample_pairs(diff["missing_pairs"]),
        "extra_generated_pair_sample": _sample_pairs(diff["extra_pairs"]),
    }
    if missing_pair_count or extra_pair_count:
        report["ERROR"].append({"code": "compatibility_review_pair_drift", **drift_payload})
    elif missing_count or extra_count or not diff["order_matches"]:
        report["WARNING"].append({"code": "compatibility_review_metadata_drift", **drift_payload})

    if skipped_prompts:
        report["WARNING"].append(
            {
                "code": "prompt_rows_outside_variation_scope",
                "count": len(skipped_prompts),
                "sample": skipped_prompts[:12],
            }
        )

    report["INFO"].append(
        {
            "code": "compatibility_review_generation_summary",
            "scope_subject_count": len(scope_subjects),
            "scope_location_count": len(scope_locations),
            "generated_row_count": len(generated_rows),
            "current_row_count": len(current_rows),
            "missing_current_rows": missing_count,
            "extra_generated_rows": extra_count,
            "missing_current_pairs": missing_pair_count,
            "extra_generated_pairs": extra_pair_count,
        }
    )
    return report


def write_rows(rows: Sequence[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or check scoped compatibility_review.csv rows.")
    parser.add_argument("--check", action="store_true", help="Compare generated rows with assets/compatibility_review.csv.")
    parser.add_argument("--write", action="store_true", help="Write generated rows to --output.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Output path for --write.")
    parser.add_argument("--allow-drift", action="store_true", help="Allow writing even when --check reports drift.")
    args = parser.parse_args()

    report = build_check_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.write:
        output_path = Path(args.output)
        if report["ERROR"] and not args.allow_drift:
            return 1
        if output_path.resolve() == CSV_PATH.resolve() and report["ERROR"] and not args.allow_drift:
            return 1
        write_rows(build_generated_rows(), output_path)
        return 0

    return 1 if report["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
