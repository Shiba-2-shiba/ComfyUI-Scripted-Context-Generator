from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from assets.calc_variations import calc_base_metrics, is_action_pool_location_key
from registry import load_action_pools, load_scene_compatibility, resolve_location_alias_map
from tools.analyze_variation_candidates import analyze_candidate_catalog, load_candidate_catalog
from tools.build_action_pools import expand_source_payload, read_shared_families
from tools.build_compatibility_review import resolve_canonical_location
from tools.check_variation_scope import load_variation_scope
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


REPORT_SCHEMA_VERSION = "variation-candidate-contribution-model/v1"
ADDITION_SCHEMA_VERSION = "variation-location-additions/v1"
ADDITION_REPORT_SCHEMA_VERSION = "variation-location-addition-plan/v1"
_ADDITION_FIELDS = frozenset(
    {"id", "compatibility_tags", "action_count", "utility_group", "distinct_from", "rationale"}
)


def _projection_payload(value: Mapping[str, Any]) -> Mapping[str, Any]:
    projection = value.get("projection") if isinstance(value, Mapping) else None
    return projection if isinstance(projection, Mapping) else value


def _canonical_locations_for_tags(
    tags: set[str],
    *,
    compatibility: Mapping[str, Any],
    aliases: Mapping[str, Any],
    counted_locations: set[str],
    overrides: Mapping[str, str],
) -> set[str]:
    raw_locations = {
        str(location)
        for tag in tags
        for location in compatibility.get("loc_tags", {}).get(tag, [])
    } | {str(location) for location in compatibility.get("universal_locs", [])}
    return {
        canonical
        for raw in raw_locations
        for canonical in [resolve_canonical_location(raw, aliases, counted_locations, overrides)]
        if canonical in counted_locations
    }


def model_candidate_contributions(
    catalog: Mapping[str, Any],
    *,
    scenario_manifest: Mapping[str, Any],
    projection_report: Mapping[str, Any],
) -> dict:
    analysis = analyze_candidate_catalog(
        catalog,
        scenario_manifest=scenario_manifest,
        projection_report=projection_report,
    )
    if analysis.get("structural_status") != "pass":
        raise WorkflowValidationError(
            "candidate_not_contribution_eligible",
            "candidate catalog must pass structural analysis before contribution modeling",
            errors=analysis.get("errors", []),
        )
    projection = _projection_payload(projection_report)
    scenario_id = analysis["scenario_binding"]["scenario_id"]
    selected = next(
        (
            item
            for item in projection.get("hypothetical_scenarios", [])
            if isinstance(item, Mapping) and item.get("id") == scenario_id
        ),
        None,
    )
    if selected is None:
        raise WorkflowValidationError("missing_contribution_scenario", "bound projection scenario is missing")

    scope = load_variation_scope()
    compatibility = load_scene_compatibility()
    aliases = resolve_location_alias_map()
    overrides = scope.get("compatibility_review_generation", {}).get("canonical_location_overrides", {})
    counted_subjects = set(scope.get("variation_subjects", []))
    counted_locations = set(scope.get("variation_locations", []))
    action_pools = {
        str(key): value
        for key, value in load_action_pools().items()
        if is_action_pool_location_key(str(key), value)
    }
    baseline = calc_base_metrics(ROOT)

    new_subject_existing_rows = 0
    new_subject_existing_variations = 0
    subject_breakdown: dict[str, dict[str, int]] = {}
    subject_tags: dict[str, set[str]] = {}
    for subject in catalog["subjects"]:
        subject_id = str(subject["id"])
        tags = set(subject["tags"])
        subject_tags[subject_id] = tags
        compatible = _canonical_locations_for_tags(
            tags,
            compatibility=compatibility,
            aliases=aliases,
            counted_locations=counted_locations,
            overrides=overrides,
        )
        contribution = sum(len(action_pools.get(location, [])) for location in compatible)
        subject_breakdown[subject_id] = {"rows": len(compatible), "base_variations": contribution}
        new_subject_existing_rows += len(compatible)
        new_subject_existing_variations += contribution

    shared_families = read_shared_families()
    existing_profiles = compatibility.get("characters", {})
    existing_subject_new_rows = 0
    new_subject_new_rows = 0
    new_location_variations = 0
    location_breakdown: dict[str, dict[str, int]] = {}
    for location in catalog["locations"]:
        location_id = str(location["id"])
        tags = set(location["compatibility_tags"])
        universal = bool(location.get("universal", False))
        existing_count = sum(
            1
            for subject_id, profile in existing_profiles.items()
            if subject_id in counted_subjects
            and isinstance(profile, Mapping)
            and (universal or bool(tags & set(profile.get("tags", []))))
        )
        proposed_count = sum(
            1
            for subject_id, subject_values in subject_tags.items()
            if universal or bool(tags & subject_values)
        )
        expansion_report = {"ERROR": [], "WARNING": [], "INFO": []}
        actions = expand_source_payload(
            location_id,
            {
                "actions": list(location["action_plan"]["direct_actions"]),
                "families": list(location["action_plan"]["family_refs"]),
            },
            shared_families,
            expansion_report,
        )
        if expansion_report["ERROR"]:
            raise WorkflowValidationError(
                "candidate_action_expansion_failed",
                "candidate action plan failed during contribution modeling",
                location=location_id,
                errors=expansion_report["ERROR"],
            )
        rows = existing_count + proposed_count
        contribution = rows * len(actions)
        location_breakdown[location_id] = {
            "existing_subject_rows": existing_count,
            "proposed_subject_rows": proposed_count,
            "rows": rows,
            "actions": len(actions),
            "base_variations": contribution,
        }
        existing_subject_new_rows += existing_count
        new_subject_new_rows += proposed_count
        new_location_variations += contribution

    estimated_rows = (
        int(baseline["row_count"])
        + new_subject_existing_rows
        + existing_subject_new_rows
        + new_subject_new_rows
    )
    estimated_variations = (
        int(baseline["total_base_variations"])
        + new_subject_existing_variations
        + new_location_variations
    )
    target = int(projection["target"])
    projected_variations = int(selected["projected_base_variations"])
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "catalog_sha256": analysis["catalog_sha256"],
        "scenario_id": scenario_id,
        "baseline": {
            "rows": int(baseline["row_count"]),
            "base_variations": int(baseline["total_base_variations"]),
        },
        "contributions": {
            "new_subject_existing_location": {
                "rows": new_subject_existing_rows,
                "base_variations": new_subject_existing_variations,
            },
            "existing_subject_new_location": {"rows": existing_subject_new_rows},
            "new_subject_new_location": {"rows": new_subject_new_rows},
            "all_new_location_rows": {
                "rows": existing_subject_new_rows + new_subject_new_rows,
                "base_variations": new_location_variations,
            },
        },
        "estimated": {
            "rows": estimated_rows,
            "base_variations": estimated_variations,
            "target": target,
            "target_gap": target - estimated_variations,
            "target_met": estimated_variations >= target,
        },
        "projection_comparison": {
            "projected_rows": int(selected["projected_rows"]),
            "projected_base_variations": projected_variations,
            "row_delta": estimated_rows - int(selected["projected_rows"]),
            "base_variation_delta": estimated_variations - projected_variations,
        },
        "subject_breakdown": dict(sorted(subject_breakdown.items())),
        "location_breakdown": dict(sorted(location_breakdown.items())),
    }


def _identity_key(value: Any) -> str:
    return re.sub(r"[ _-]+", " ", str(value or "").strip().casefold())


def plan_location_additions(
    catalog: Mapping[str, Any],
    additions: Mapping[str, Any],
    *,
    base_report: Mapping[str, Any],
) -> dict:
    if additions.get("schema_version") != ADDITION_SCHEMA_VERSION:
        raise WorkflowValidationError("unsupported_location_addition_schema", "location addition schema is unsupported")
    rows = additions.get("additions")
    if not isinstance(rows, list) or not rows:
        raise WorkflowValidationError("missing_location_additions", "location additions must be a non-empty array")
    if base_report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise WorkflowValidationError("invalid_base_contribution_report", "base contribution report schema is invalid")
    expected_catalog_hash = hashlib.sha256(canonical_json_bytes(dict(catalog))).hexdigest()
    if expected_catalog_hash != base_report.get("catalog_sha256"):
        raise WorkflowValidationError("addition_catalog_hash_mismatch", "addition catalog does not match base report")

    scope = load_variation_scope()
    compatibility = load_scene_compatibility()
    aliases = resolve_location_alias_map()
    overrides = scope.get("compatibility_review_generation", {}).get("canonical_location_overrides", {})
    current_subjects = set(scope.get("variation_subjects", []))
    current_locations = set(scope.get("variation_locations", []))
    candidate_locations = {str(item["id"]) for item in catalog["locations"]}
    runtime_locations = {
        str(key)
        for key, value in load_action_pools().items()
        if is_action_pool_location_key(str(key), value)
    }
    candidate_subject_tags = [set(item["tags"]) for item in catalog["subjects"]]
    existing_profiles = compatibility.get("characters", {})
    known_tags = set(compatibility.get("loc_tags", {}))
    known_location_refs = {
        _identity_key(item)
        for item in current_locations | candidate_locations | runtime_locations | set(aliases)
    }
    ids: list[str] = []
    modeled = []
    for index, item in enumerate(rows):
        if not isinstance(item, Mapping):
            raise WorkflowValidationError("invalid_location_addition", "location addition must be an object", index=index)
        unknown = sorted(set(item) - _ADDITION_FIELDS)
        if unknown:
            raise WorkflowValidationError(
                "unknown_location_addition_field",
                "location addition contains unknown fields",
                index=index,
                fields=unknown,
            )
        location_id = str(item.get("id", "")).strip()
        if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", location_id):
            raise WorkflowValidationError("invalid_location_addition_id", "location addition ID must be lowercase snake_case", id=location_id)
        if _identity_key(location_id) in known_location_refs:
            raise WorkflowValidationError("location_addition_collision", "location addition collides with current or candidate IDs", id=location_id)
        canonical = resolve_canonical_location(location_id, aliases, current_locations, overrides)
        if canonical != location_id:
            raise WorkflowValidationError("location_addition_collision", "location addition resolves to an existing alias", id=location_id)
        tags = item.get("compatibility_tags")
        if not isinstance(tags, list) or not tags or any(not isinstance(tag, str) or not tag for tag in tags):
            raise WorkflowValidationError("invalid_location_addition_tags", "location addition tags are invalid", id=location_id)
        unknown_tags = sorted(set(tags) - known_tags)
        if unknown_tags:
            raise WorkflowValidationError(
                "unknown_location_addition_tag",
                "location addition uses unknown compatibility tags",
                id=location_id,
                tags=unknown_tags,
            )
        action_count = item.get("action_count")
        if not isinstance(action_count, int) or isinstance(action_count, bool) or not 1 <= action_count <= 20:
            raise WorkflowValidationError(
                "invalid_location_addition_action_count",
                "location addition action_count must be an integer from 1 through 20",
                id=location_id,
            )
        if not isinstance(item.get("utility_group"), str) or not item["utility_group"].strip():
            raise WorkflowValidationError("invalid_location_addition_utility", "location utility group is required", id=location_id)
        comparator = item.get("distinct_from")
        if not isinstance(comparator, str) or _identity_key(comparator) not in known_location_refs:
            raise WorkflowValidationError("unknown_location_addition_comparator", "location comparator is unknown", id=location_id)
        if not isinstance(item.get("rationale"), str) or not item["rationale"].strip():
            raise WorkflowValidationError("invalid_location_addition_rationale", "location rationale is required", id=location_id)
        tag_set = set(tags)
        existing_count = sum(
            1
            for subject_id, profile in existing_profiles.items()
            if subject_id in current_subjects
            and isinstance(profile, Mapping)
            and bool(tag_set & set(profile.get("tags", [])))
        )
        proposed_count = sum(1 for subject_tags in candidate_subject_tags if tag_set & subject_tags)
        compatible_count = existing_count + proposed_count
        contribution = compatible_count * action_count
        ids.append(location_id)
        modeled.append(
            {
                "id": location_id,
                "compatibility_tags": sorted(tags),
                "action_count": action_count,
                "existing_subject_rows": existing_count,
                "proposed_subject_rows": proposed_count,
                "rows": compatible_count,
                "base_variations": contribution,
                "utility_group": item["utility_group"],
                "distinct_from": comparator,
                "rationale": item["rationale"],
            }
        )
    if len(ids) != len(set(ids)):
        raise WorkflowValidationError("duplicate_location_addition_id", "location addition IDs must be unique")
    modeled.sort(key=lambda item: item["id"])
    added_rows = sum(item["rows"] for item in modeled)
    added_variations = sum(item["base_variations"] for item in modeled)
    starting = int(base_report["estimated"]["base_variations"])
    target = int(base_report["estimated"]["target"])
    total = starting + added_variations
    return {
        "schema_version": ADDITION_REPORT_SCHEMA_VERSION,
        "catalog_sha256": base_report["catalog_sha256"],
        "base_report_sha256": hashlib.sha256(canonical_json_bytes(dict(base_report))).hexdigest(),
        "additions_sha256": hashlib.sha256(
            canonical_json_bytes({"schema_version": ADDITION_SCHEMA_VERSION, "additions": modeled})
        ).hexdigest(),
        "starting_base_variations": starting,
        "starting_target_gap": target - starting,
        "additions": modeled,
        "added_rows": added_rows,
        "added_base_variations": added_variations,
        "estimated_total_base_variations": total,
        "target": target,
        "target_gap": target - total,
        "target_met": total >= target,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Model candidate contribution using existing and new location depths separately.")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--scenario-file", required=True)
    parser.add_argument("--projection-report", required=True)
    parser.add_argument("--location-additions")
    args = parser.parse_args()
    try:
        catalog = load_candidate_catalog(args.catalog)
        scenario = json.loads(Path(args.scenario_file).read_text(encoding="utf-8"))
        projection = json.loads(Path(args.projection_report).read_text(encoding="utf-8"))
        report = model_candidate_contributions(
            catalog,
            scenario_manifest=scenario,
            projection_report=projection,
        )
        if args.location_additions:
            additions = json.loads(Path(args.location_additions).read_text(encoding="utf-8"))
            report = plan_location_additions(catalog, additions, base_report=report)
    except (OSError, ValueError, json.JSONDecodeError, WorkflowValidationError) as exc:
        envelope = exc.to_envelope() if isinstance(exc, WorkflowValidationError) else WorkflowValidationError(
            "candidate_contribution_model_failed",
            "candidate contribution model failed",
            exception_type=type(exc).__name__,
        ).to_envelope()
        sys.stderr.buffer.write(canonical_json_bytes(envelope))
        return 2
    sys.stdout.buffer.write(canonical_json_bytes(report))
    target_met = report.get("target_met")
    if target_met is None:
        target_met = report["estimated"]["target_met"]
    return 0 if target_met else 1


if __name__ == "__main__":
    raise SystemExit(main())
