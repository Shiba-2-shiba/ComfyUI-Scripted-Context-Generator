from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.semantic_policy import find_banned_terms, normalize_fragment_text
from registry import load_action_pools, load_scene_compatibility, resolve_location_alias_map
from tools.build_action_pools import (
    MANIFEST_PATH as ACTION_MANIFEST_PATH,
    SOURCE_DIR as ACTION_SOURCE_DIR,
    expand_source_payload,
    read_shared_families,
)
from tools.build_compatibility_review import resolve_canonical_location
from tools.check_variation_scope import load_variation_scope
from tools.plan_variation_target import (
    _load_l0_baseline_manifest,
    L0_POOL_POLICY_PATH,
    build_projection_report,
    validate_locked_input_hashes,
)
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


CATALOG_SCHEMA_VERSION = "variation-quality-candidate-catalog/v1"
ITERATION_SCHEMA_VERSION = "variation-quality-candidate-iteration/v1"
EXTENDED_ITERATION_SCHEMA_VERSION = "variation-quality-candidate-iteration/v2"
ENRICHED_ITERATION_SCHEMA_VERSION = "variation-quality-candidate-iteration/v3"
LOCATION_ADDITIONS_SCHEMA_VERSION = "variation-quality-location-additions/v1"
LOCATION_OVERRIDES_SCHEMA_VERSION = "variation-quality-location-overrides/v1"
REPORT_SCHEMA_VERSION = "variation-quality-candidate-analysis/v1"
_ITERATION_FIELDS = frozenset(
    {
        "schema_version",
        "catalog_id",
        "stage_id",
        "base_catalog_path",
        "base_catalog_sha256",
        "action_overrides_path",
        "action_overrides_sha256",
        "scenario_binding",
        "quality_limits",
        "prompt_quality_receipt",
    }
)
_EXTENDED_ITERATION_FIELDS = frozenset(
    {
        "schema_version",
        "catalog_id",
        "stage_id",
        "base_catalog_path",
        "base_catalog_sha256",
        "location_additions_path",
        "location_additions_sha256",
        "scenario_binding",
        "quality_limits",
        "prompt_quality_receipt",
    }
)
_ENRICHED_ITERATION_FIELDS = frozenset(
    {
        "schema_version",
        "catalog_id",
        "stage_id",
        "base_catalog_path",
        "base_catalog_sha256",
        "location_overrides_path",
        "location_overrides_sha256",
        "scenario_binding",
        "quality_limits",
        "prompt_quality_receipt",
    }
)
_TOP_FIELDS = frozenset(
    {
        "schema_version",
        "catalog_id",
        "stage_id",
        "scenario_binding",
        "subjects",
        "locations",
        "quality_limits",
        "prompt_quality_receipt",
    }
)
_SUBJECT_FIELDS = frozenset({"id", "utility_group", "tags", "default_costume", "utility_claim"})
_LOCATION_FIELDS = frozenset(
    {
        "id",
        "utility_group",
        "compatibility_tags",
        "universal",
        "environment_terms",
        "background_pack",
        "utility_claim",
        "action_plan",
    }
)
_LOCATION_OVERRIDE_FIELDS = frozenset({"id", "background_pack", "action_plan"})
_BACKGROUND_PACK_FIELDS = frozenset(
    {"environment", "core", "texture", "props", "fx", "time", "crowd", "weather", "lighting", "aliases"}
)
_BACKGROUND_PACK_MINIMUM_COUNTS = {
    "environment": 2,
    "core": 4,
    "texture": 2,
    "props": 3,
    "fx": 2,
    "time": 2,
    "crowd": 2,
    "weather": 2,
    "lighting": 2,
}
_CLAIM_FIELDS = frozenset({"category", "prompt_visible_terms", "distinct_from", "rationale"})
_ACTION_PLAN_FIELDS = frozenset({"direct_actions", "family_refs"})
_DIRECT_ACTION_FIELDS = frozenset({"text", "load"})
_FAMILY_REF_FIELDS = frozenset({"name", "offset", "take"})
_BINDING_FIELDS = frozenset(
    {"scenario_manifest_sha256", "projection_report_sha256", "scenario_id", "baseline_manifest_sha256"}
)
_LIMIT_FIELDS = frozenset({"max_exact_duplicate_pressure_basis_points", "max_shared_family_location_reuse"})


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _normalized_text(value: Any) -> str:
    return normalize_fragment_text(str(value or "")).casefold()


def _identity_key(value: Any) -> str:
    return re.sub(r"[ _-]+", " ", _normalized_text(value)).strip()


def _error(code: str, message: str, **details: Any) -> dict:
    return {"code": code, "message": message, "details": dict(sorted(details.items()))}


def _append_unknown_fields(errors: list[dict], payload: Any, allowed: set[str] | frozenset[str], *, path: str) -> None:
    if not isinstance(payload, Mapping):
        errors.append(_error("invalid_catalog_object", "catalog value must be an object", path=path))
        return
    unknown = sorted(set(payload) - allowed)
    if unknown:
        errors.append(_error("unknown_catalog_field", "catalog contains unknown fields", path=path, fields=unknown))


def _valid_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def _duplicate_normalized(values: Sequence[str]) -> list[str]:
    normalized = [_identity_key(value) for value in values]
    counts = Counter(normalized)
    return sorted(value for value, count in counts.items() if value and count > 1)


def _load_bound_catalog_artifact(relative_value: Any, hash_value: Any, *, kind: str) -> tuple[Path, Any]:
    if not isinstance(relative_value, str) or not relative_value.strip():
        raise WorkflowValidationError(f"missing_{kind}_path", f"{kind} path is required")
    candidate_path = (ROOT / relative_value).resolve()
    try:
        candidate_path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise WorkflowValidationError(f"invalid_{kind}_path", f"{kind} path escapes the repository") from exc
    try:
        actual_hash = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
        value = _read_json(candidate_path)
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowValidationError(
            f"{kind}_unreadable",
            f"{kind} could not be read",
            path=str(relative_value),
            exception_type=type(exc).__name__,
        ) from exc
    if not isinstance(hash_value, str) or actual_hash != hash_value:
        raise WorkflowValidationError(
            f"{kind}_hash_mismatch",
            f"{kind} hash does not match the iteration manifest",
            expected=hash_value,
            actual=actual_hash,
        )
    return candidate_path, value


def load_candidate_catalog(path: str | Path, _seen: set[Path] | None = None) -> dict:
    candidate = Path(path).resolve()
    seen = set() if _seen is None else set(_seen)
    if candidate in seen:
        raise WorkflowValidationError("candidate_catalog_cycle", "candidate catalog composition contains a cycle")
    seen.add(candidate)
    try:
        payload = _read_json(candidate)
    except OSError as exc:
        raise WorkflowValidationError(
            "candidate_catalog_unreadable",
            "candidate catalog could not be read",
            path=str(candidate),
            exception_type=type(exc).__name__,
        ) from exc
    except json.JSONDecodeError as exc:
        raise WorkflowValidationError(
            "candidate_catalog_invalid_json",
            "candidate catalog is not valid JSON",
            path=str(candidate),
            line=exc.lineno,
            column=exc.colno,
        ) from exc
    if not isinstance(payload, dict):
        raise WorkflowValidationError("invalid_candidate_catalog", "candidate catalog must be a JSON object")
    if payload.get("schema_version") == ENRICHED_ITERATION_SCHEMA_VERSION:
        unknown = sorted(set(payload) - _ENRICHED_ITERATION_FIELDS)
        if unknown:
            raise WorkflowValidationError(
                "unknown_candidate_iteration_field",
                "enriched candidate iteration contains unknown fields",
                fields=unknown,
            )
        base_path, _base_raw = _load_bound_catalog_artifact(
            payload.get("base_catalog_path"), payload.get("base_catalog_sha256"), kind="base_catalog"
        )
        _override_path, overrides = _load_bound_catalog_artifact(
            payload.get("location_overrides_path"),
            payload.get("location_overrides_sha256"),
            kind="location_overrides",
        )
        base = load_candidate_catalog(base_path, seen)
        if not isinstance(overrides, dict) or overrides.get("schema_version") != LOCATION_OVERRIDES_SCHEMA_VERSION:
            raise WorkflowValidationError(
                "invalid_location_overrides_schema",
                "location overrides must use the supported quality catalog schema",
            )
        if set(overrides) != {"schema_version", "locations"} or not isinstance(overrides.get("locations"), list):
            raise WorkflowValidationError(
                "invalid_location_overrides_catalog",
                "location overrides catalog must contain only a locations array",
            )
        materialized = copy.deepcopy(base)
        location_map = {
            str(item.get("id", "")): item
            for item in materialized.get("locations", [])
            if isinstance(item, dict) and str(item.get("id", ""))
        }
        override_map: dict[str, dict[str, Any]] = {}
        for item in overrides["locations"]:
            if not isinstance(item, dict) or set(item) != _LOCATION_OVERRIDE_FIELDS or not str(item.get("id", "")):
                raise WorkflowValidationError(
                    "invalid_location_override",
                    "each location override must contain only id, background_pack, and action_plan",
                )
            location_id = str(item["id"])
            if location_id in override_map:
                raise WorkflowValidationError("location_override_id_collision", "location override IDs must be unique")
            override_map[location_id] = item
        if set(override_map) != set(location_map):
            raise WorkflowValidationError(
                "location_override_id_mismatch",
                "location overrides must exactly cover base catalog locations",
                missing=sorted(set(location_map) - set(override_map)),
                extra=sorted(set(override_map) - set(location_map)),
            )
        for location_id, item in override_map.items():
            location_map[location_id]["background_pack"] = copy.deepcopy(item["background_pack"])
            location_map[location_id]["action_plan"] = copy.deepcopy(item["action_plan"])
        materialized["catalog_id"] = payload.get("catalog_id")
        materialized["stage_id"] = payload.get("stage_id")
        materialized["scenario_binding"] = copy.deepcopy(payload.get("scenario_binding"))
        materialized["quality_limits"] = copy.deepcopy(payload.get("quality_limits"))
        materialized["prompt_quality_receipt"] = payload.get("prompt_quality_receipt")
        return materialized
    if payload.get("schema_version") == EXTENDED_ITERATION_SCHEMA_VERSION:
        unknown = sorted(set(payload) - _EXTENDED_ITERATION_FIELDS)
        if unknown:
            raise WorkflowValidationError(
                "unknown_candidate_iteration_field",
                "extended candidate iteration contains unknown fields",
                fields=unknown,
            )
        base_path, _base_raw = _load_bound_catalog_artifact(
            payload.get("base_catalog_path"), payload.get("base_catalog_sha256"), kind="base_catalog"
        )
        _addition_path, additions = _load_bound_catalog_artifact(
            payload.get("location_additions_path"),
            payload.get("location_additions_sha256"),
            kind="location_additions",
        )
        base = load_candidate_catalog(base_path, seen)
        if not isinstance(additions, dict) or additions.get("schema_version") != LOCATION_ADDITIONS_SCHEMA_VERSION:
            raise WorkflowValidationError(
                "invalid_location_additions_schema",
                "location additions must use the supported quality catalog schema",
            )
        if set(additions) != {"schema_version", "locations"} or not isinstance(additions.get("locations"), list):
            raise WorkflowValidationError(
                "invalid_location_additions_catalog",
                "location additions catalog must contain only a locations array",
            )
        materialized = copy.deepcopy(base)
        existing_ids = {str(item.get("id", "")) for item in materialized.get("locations", []) if isinstance(item, dict)}
        addition_ids = [
            str(item.get("id", ""))
            for item in additions["locations"]
            if isinstance(item, dict)
        ]
        if len(addition_ids) != len(additions["locations"]) or not all(addition_ids):
            raise WorkflowValidationError("invalid_location_addition", "every location addition must be an object with an ID")
        if len(addition_ids) != len(set(addition_ids)) or existing_ids & set(addition_ids):
            raise WorkflowValidationError(
                "location_addition_id_collision",
                "location additions must be unique and absent from the base catalog",
            )
        materialized["locations"].extend(copy.deepcopy(additions["locations"]))
        materialized["locations"].sort(key=lambda item: str(item.get("id", "")))
        materialized["catalog_id"] = payload.get("catalog_id")
        materialized["stage_id"] = payload.get("stage_id")
        materialized["scenario_binding"] = copy.deepcopy(payload.get("scenario_binding"))
        materialized["quality_limits"] = copy.deepcopy(payload.get("quality_limits"))
        materialized["prompt_quality_receipt"] = payload.get("prompt_quality_receipt")
        return materialized
    if payload.get("schema_version") == ITERATION_SCHEMA_VERSION:
        unknown = sorted(set(payload) - _ITERATION_FIELDS)
        if unknown:
            raise WorkflowValidationError(
                "unknown_candidate_iteration_field",
                "candidate iteration contains unknown fields",
                fields=unknown,
            )

        base_path, _base_raw = _load_bound_catalog_artifact(
            payload.get("base_catalog_path"), payload.get("base_catalog_sha256"), kind="base_catalog"
        )
        _override_path, overrides = _load_bound_catalog_artifact(
            payload.get("action_overrides_path"), payload.get("action_overrides_sha256"), kind="action_overrides"
        )
        base = load_candidate_catalog(base_path, seen)
        if not isinstance(overrides, dict):
            raise WorkflowValidationError("invalid_action_overrides", "action overrides must be an object")
        materialized = copy.deepcopy(base)
        locations = materialized.get("locations", [])
        location_map = {
            str(item.get("id", "")): item
            for item in locations
            if isinstance(item, dict) and str(item.get("id", ""))
        }
        if set(overrides) != set(location_map):
            raise WorkflowValidationError(
                "action_override_id_mismatch",
                "action overrides must exactly cover base catalog locations",
                missing=sorted(set(location_map) - set(overrides)),
                extra=sorted(set(overrides) - set(location_map)),
            )
        for location_id, action_plan in overrides.items():
            if not isinstance(action_plan, dict):
                raise WorkflowValidationError(
                    "invalid_action_override",
                    "each action override must be an object",
                    id=location_id,
                )
            location_map[location_id]["action_plan"] = copy.deepcopy(action_plan)
        materialized["catalog_id"] = payload.get("catalog_id")
        materialized["stage_id"] = payload.get("stage_id")
        materialized["scenario_binding"] = copy.deepcopy(payload.get("scenario_binding"))
        materialized["quality_limits"] = copy.deepcopy(payload.get("quality_limits"))
        materialized["prompt_quality_receipt"] = payload.get("prompt_quality_receipt")
        return materialized
    return payload


def _projection_payload(value: Mapping[str, Any]) -> Mapping[str, Any]:
    projection = value.get("projection") if isinstance(value, Mapping) else None
    return projection if isinstance(projection, Mapping) else value


def _existing_family_reuse_counts() -> Counter[str]:
    counts: Counter[str] = Counter()
    manifest = _read_json(ACTION_MANIFEST_PATH)
    locations = manifest.get("location_order", []) if isinstance(manifest, dict) else []
    for location in locations if isinstance(locations, list) else []:
        path = ACTION_SOURCE_DIR / f"{location}.json"
        if not path.exists():
            continue
        payload = _read_json(path)
        refs = payload.get("families", []) if isinstance(payload, dict) else []
        for ref in refs if isinstance(refs, list) else []:
            if isinstance(ref, str):
                name = ref
            elif isinstance(ref, Mapping):
                name = str(ref.get("name") or ref.get("family") or "")
            else:
                name = ""
            if name:
                counts[name] += 1
    return counts


def _action_text(action: Any) -> str:
    return str(action.get("text", "")).strip() if isinstance(action, Mapping) else str(action).strip()


def _validate_claim(
    claim: Any,
    *,
    path: str,
    known_ids: set[str],
    visible_surface: str,
    errors: list[dict],
) -> tuple[str, ...]:
    _append_unknown_fields(errors, claim, _CLAIM_FIELDS, path=path)
    if not isinstance(claim, Mapping):
        return ()
    category = claim.get("category")
    terms = claim.get("prompt_visible_terms")
    distinct_from = claim.get("distinct_from")
    rationale = claim.get("rationale")
    if not isinstance(category, str) or not category.strip() or not _valid_string_list(terms) or not _valid_string_list(distinct_from):
        errors.append(_error("invalid_utility_claim", "utility claim is incomplete", path=path))
        return ()
    if not isinstance(rationale, str) or not rationale.strip():
        errors.append(_error("invalid_utility_claim", "utility claim rationale is required", path=path))
    unknown = sorted(item for item in distinct_from if _identity_key(item) not in known_ids)
    if unknown:
        errors.append(_error("unknown_distinct_from", "utility comparator is unknown", path=path, ids=unknown))
    normalized_surface = _normalized_text(visible_surface)
    missing_terms = sorted(term for term in terms if _normalized_text(term) not in normalized_surface)
    if missing_terms:
        errors.append(
            _error(
                "utility_term_not_visible",
                "prompt-visible utility terms are absent from the candidate surface",
                path=path,
                terms=missing_terms,
            )
        )
    return tuple(sorted(_normalized_text(term) for term in terms))


def _pool_policy_locations() -> set[str]:
    payload = _read_json(L0_POOL_POLICY_PATH)
    rows = payload.get("non_counted_runtime_pools", []) if isinstance(payload, dict) else []
    return {
        str(row.get("location", "")).strip()
        for row in rows
        if isinstance(row, Mapping) and str(row.get("location", "")).strip()
    }


def _derive_prompt_quality_state(receipt: Any, *, catalog_sha256: str) -> tuple[dict, list[dict]]:
    if receipt is None:
        return {"status": "not_evaluated", "receipt_sha256": None}, []
    return {"status": "not_evaluated", "receipt_sha256": None}, [
        _error(
            "prompt_quality_receipt_not_supported_in_l2",
            "L2 accepts only an unevaluated null receipt; authenticated terminal receipt handling belongs to L3",
            catalog_sha256=catalog_sha256,
        )
    ]


def _evaluate_catalog(
    catalog: Mapping[str, Any],
    *,
    scenario_manifest: Mapping[str, Any],
    projection_report: Mapping[str, Any],
    baseline_manifest_path: Path | None = None,
) -> dict:
    errors: list[dict] = []
    policy_findings: list[dict] = []
    _append_unknown_fields(errors, catalog, _TOP_FIELDS, path="catalog")
    if catalog.get("schema_version") != CATALOG_SCHEMA_VERSION:
        errors.append(_error("unsupported_candidate_catalog_schema", "candidate catalog schema is unsupported"))
    if catalog.get("stage_id") != "V150":
        errors.append(_error("unsupported_candidate_stage", "candidate analyzer currently supports only V150"))
    if not isinstance(catalog.get("catalog_id"), str) or not str(catalog.get("catalog_id")).strip():
        errors.append(_error("missing_catalog_id", "catalog_id is required"))

    validate_locked_input_hashes(_load_l0_baseline_manifest(baseline_manifest_path))
    projection = _projection_payload(projection_report)
    binding = catalog.get("scenario_binding")
    _append_unknown_fields(errors, binding, _BINDING_FIELDS, path="scenario_binding")
    if not isinstance(binding, Mapping):
        binding = {}
    try:
        recomputed_projection = build_projection_report(
            scenario_manifest,
            target=int(projection.get("target", 0)),
            baseline=projection.get("baseline_metrics") if isinstance(projection.get("baseline_metrics"), Mapping) else None,
            baseline_manifest_path=baseline_manifest_path,
        )
        if canonical_json_bytes(recomputed_projection) != canonical_json_bytes(dict(projection)):
            errors.append(_error("projection_report_mismatch", "projection report does not match the scenario manifest"))
    except WorkflowValidationError as exc:
        errors.append(_error(exc.code, exc.message, **exc.details))
    projection_sha = _hash_value(dict(projection)) if isinstance(projection, Mapping) else ""
    for field, actual in (
        ("scenario_manifest_sha256", projection.get("scenario_manifest_sha256")),
        ("projection_report_sha256", projection_sha),
        ("baseline_manifest_sha256", projection.get("baseline_manifest_sha256")),
    ):
        if binding.get(field) != actual:
            errors.append(_error("scenario_binding_mismatch", "catalog scenario binding drifted", field=field))
    scenario_id = binding.get("scenario_id")
    scenarios = projection.get("hypothetical_scenarios", []) if isinstance(projection, Mapping) else []
    selected = next((row for row in scenarios if isinstance(row, Mapping) and row.get("id") == scenario_id), None)
    if selected is None:
        errors.append(_error("unknown_bound_scenario", "catalog scenario_id is absent from projection report"))
        selected = {}

    scope = load_variation_scope()
    compatibility = load_scene_compatibility()
    aliases = resolve_location_alias_map()
    overrides = scope.get("compatibility_review_generation", {}).get("canonical_location_overrides", {})
    current_subjects = {str(item) for item in scope.get("variation_subjects", [])}
    known_subjects = set(current_subjects) | {str(item) for item in compatibility.get("characters", {})}
    current_locations = {str(item) for item in scope.get("variation_locations", [])}
    known_locations = current_locations | set(aliases) | _pool_policy_locations()
    known_tags = set(compatibility.get("loc_tags", {}))

    subjects = catalog.get("subjects")
    locations = catalog.get("locations")
    if not isinstance(subjects, list):
        errors.append(_error("invalid_subject_candidates", "subjects must be an array"))
        subjects = []
    if not isinstance(locations, list):
        errors.append(_error("invalid_location_candidates", "locations must be an array"))
        locations = []
    subject_ids = [str(item.get("id", "")).strip() for item in subjects if isinstance(item, Mapping)]
    location_ids = [str(item.get("id", "")).strip() for item in locations if isinstance(item, Mapping)]
    if _duplicate_normalized(subject_ids) or _duplicate_normalized(location_ids):
        errors.append(_error("duplicate_candidate_id", "candidate IDs must be unique after normalization"))
    expected_subject_ids = set(selected.get("proposed_subject_ids", [])) if isinstance(selected, Mapping) else set()
    expected_location_ids = set(selected.get("proposed_location_ids", [])) if isinstance(selected, Mapping) else set()
    if set(subject_ids) != expected_subject_ids:
        errors.append(_error("proposal_id_mismatch", "subject catalog IDs do not match the bound scenario"))
    if set(location_ids) != expected_location_ids:
        errors.append(_error("proposal_id_mismatch", "location catalog IDs do not match the bound scenario"))

    normalized_current_subjects = {_identity_key(item) for item in known_subjects}
    normalized_current_locations = {_identity_key(item) for item in known_locations}
    all_subject_refs = normalized_current_subjects | {_identity_key(item) for item in subject_ids}
    all_location_refs = normalized_current_locations | {_identity_key(item) for item in location_ids}
    subject_signatures: Counter[tuple[str, ...]] = Counter()
    location_signatures: Counter[tuple[str, ...]] = Counter()
    subject_tags: dict[str, set[str]] = {}
    location_tags: dict[str, set[str]] = {}
    location_universal: dict[str, bool] = {}
    expanded_actions: dict[str, list[Any]] = {}
    candidate_action_depths: dict[str, int] = {}
    direct_action_texts: list[str] = []
    family_action_texts: list[str] = []
    candidate_family_counts: Counter[str] = Counter()
    shared_families = read_shared_families()

    for index, item in enumerate(subjects):
        path = f"subjects[{index}]"
        _append_unknown_fields(errors, item, _SUBJECT_FIELDS, path=path)
        if not isinstance(item, Mapping):
            continue
        subject_id = str(item.get("id", "")).strip()
        if not subject_id:
            errors.append(_error("invalid_subject_id", "subject candidate ID is required", path=path))
        if not re.fullmatch(r"[a-z0-9]+(?:[ _-][a-z0-9]+)*", subject_id):
            errors.append(_error("invalid_candidate_id_format", "subject ID must use canonical lowercase words or snake_case", id=subject_id))
        if _identity_key(subject_id) in normalized_current_subjects:
            errors.append(_error("subject_scope_collision", "subject candidate already exists", id=subject_id))
        tags = item.get("tags")
        if not _valid_string_list(tags):
            errors.append(_error("invalid_compatibility_tags", "subject tags must be non-empty strings", path=path))
            tags = []
        unknown_tags = sorted(set(tags) - known_tags)
        if unknown_tags:
            errors.append(_error("unknown_compatibility_tag", "subject uses unknown compatibility tags", id=subject_id, tags=unknown_tags))
        subject_tags[subject_id] = set(tags)
        if item.get("utility_group") not in set(selected.get("subject_utility_groups", [])):
            errors.append(_error("utility_group_mismatch", "subject utility group is absent from the scenario", id=subject_id))
        signature = _validate_claim(
            item.get("utility_claim"),
            path=f"{path}.utility_claim",
            known_ids=all_subject_refs,
            visible_surface=subject_id,
            errors=errors,
        )
        if signature:
            subject_signatures[signature] += 1
        hits = find_banned_terms(subject_id)
        if hits:
            policy_findings.append({"path": f"{path}.id", "terms": hits})

    canonical_candidate_locations: list[str] = []
    for index, item in enumerate(locations):
        path = f"locations[{index}]"
        _append_unknown_fields(errors, item, _LOCATION_FIELDS, path=path)
        if not isinstance(item, Mapping):
            continue
        location_id = str(item.get("id", "")).strip()
        if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", location_id):
            errors.append(_error("invalid_candidate_id_format", "location ID must use canonical lowercase snake_case", id=location_id))
        canonical = resolve_canonical_location(location_id, aliases, current_locations, overrides)
        canonical_candidate_locations.append(canonical)
        if (
            _identity_key(location_id) in normalized_current_locations
            or canonical != location_id
            or location_id in _pool_policy_locations()
        ):
            errors.append(
                _error(
                    "location_canonical_collision",
                    "location candidate collides with current, alias, legacy, or excluded location identity",
                    id=location_id,
                    canonical=canonical,
                )
            )
        tags = item.get("compatibility_tags")
        if not _valid_string_list(tags):
            errors.append(_error("invalid_compatibility_tags", "location tags must be non-empty strings", path=path))
            tags = []
        unknown_tags = sorted(set(tags) - known_tags)
        if unknown_tags:
            errors.append(_error("unknown_compatibility_tag", "location uses unknown compatibility tags", id=location_id, tags=unknown_tags))
        location_tags[location_id] = set(tags)
        universal_value = item.get("universal")
        if type(universal_value) is not bool:
            errors.append(_error("invalid_universal_flag", "location universal must be a JSON boolean", id=location_id))
            universal_value = False
        location_universal[location_id] = universal_value
        if item.get("utility_group") not in set(selected.get("location_utility_groups", [])):
            errors.append(_error("utility_group_mismatch", "location utility group is absent from the scenario", id=location_id))
        environment_terms = item.get("environment_terms")
        if not _valid_string_list(environment_terms):
            errors.append(_error("invalid_environment_terms", "environment terms must be non-empty strings", id=location_id))
            environment_terms = []
        background_pack = item.get("background_pack")
        if background_pack is not None:
            if not isinstance(background_pack, Mapping) or set(background_pack) != _BACKGROUND_PACK_FIELDS:
                errors.append(_error("invalid_background_pack", "background pack fields are not closed", id=location_id))
            else:
                for field in sorted(_BACKGROUND_PACK_FIELDS):
                    values = background_pack.get(field)
                    if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
                        errors.append(_error("invalid_background_pack_values", "background pack values must be strings", id=location_id, field=field))
                        continue
                    minimum = _BACKGROUND_PACK_MINIMUM_COUNTS.get(field, 0)
                    if len(values) < minimum:
                        errors.append(_error("background_pack_density_below_minimum", "background pack field is too sparse", id=location_id, field=field, expected=minimum, actual=len(values)))
        action_plan = item.get("action_plan")
        _append_unknown_fields(errors, action_plan, _ACTION_PLAN_FIELDS, path=f"{path}.action_plan")
        direct_actions = action_plan.get("direct_actions", []) if isinstance(action_plan, Mapping) else []
        family_refs = action_plan.get("family_refs", []) if isinstance(action_plan, Mapping) else []
        if not isinstance(direct_actions, list) or not isinstance(family_refs, list):
            errors.append(_error("invalid_action_plan", "action plan arrays are required", id=location_id))
            direct_actions, family_refs = [], []
        for action_index, action in enumerate(direct_actions):
            _append_unknown_fields(errors, action, _DIRECT_ACTION_FIELDS, path=f"{path}.action_plan.direct_actions[{action_index}]")
            text = _action_text(action)
            if not text or not isinstance(action, Mapping) or action.get("load") not in {"calm", "active"}:
                errors.append(_error("invalid_direct_action", "direct action requires text and calm/active load", id=location_id))
            else:
                direct_action_texts.append(text)
        for ref_index, ref in enumerate(family_refs):
            if not isinstance(ref, Mapping):
                errors.append(_error("invalid_action_family_ref", "family ref must be an object", id=location_id))
                continue
            _append_unknown_fields(errors, ref, _FAMILY_REF_FIELDS, path=f"{path}.action_plan.family_refs[{ref_index}]")
            name = str(ref.get("name", ""))
            offset = ref.get("offset", 0)
            take = ref.get("take")
            if name not in shared_families:
                errors.append(_error("missing_action_family", "action family does not exist", id=location_id, family=name))
                continue
            if not isinstance(offset, int) or isinstance(offset, bool) or not isinstance(take, int) or isinstance(take, bool):
                errors.append(_error("invalid_action_family_slice", "family offset/take must be integers", id=location_id, family=name))
                continue
            if offset < 0 or take <= 0 or offset + take > len(shared_families[name]):
                errors.append(_error("invalid_action_family_slice", "family slice is outside available actions", id=location_id, family=name))
                continue
            candidate_family_counts[name] += 1
            family_action_texts.extend(_action_text(action) for action in shared_families[name][offset : offset + take])
        expansion_report = {"ERROR": [], "WARNING": [], "INFO": []}
        expanded = expand_source_payload(
            location_id,
            {"actions": direct_actions, "families": family_refs},
            shared_families,
            expansion_report,
        )
        expanded_actions[location_id] = expanded
        candidate_action_depths[location_id] = len(expanded)
        allowed_action_depths = {
            int(bucket.get("actions"))
            for bucket in selected.get("action_depth_allocation", [])
            if isinstance(bucket, Mapping) and isinstance(bucket.get("actions"), int)
        }
        if allowed_action_depths and len(expanded) not in allowed_action_depths:
            errors.append(
                _error(
                    "action_depth_not_in_projection",
                    "candidate expanded action count is absent from the bound projection distribution",
                    id=location_id,
                    actual=len(expanded),
                    allowed=sorted(allowed_action_depths),
                )
            )
        for issue in expansion_report["ERROR"]:
            code = "duplicate_candidate_action" if issue.get("code") == "action_pool_source_duplicate_actions" else str(issue.get("code"))
            errors.append(_error(code, "candidate action plan expansion failed", id=location_id, issue=issue))
        action_surface = " ".join(_action_text(action) for action in expanded)
        visible_surface = " ".join([location_id, *environment_terms, action_surface])
        signature = _validate_claim(
            item.get("utility_claim"),
            path=f"{path}.utility_claim",
            known_ids=all_location_refs,
            visible_surface=visible_surface,
            errors=errors,
        )
        if signature:
            location_signatures[signature] += 1
        for term_index, text in enumerate([*environment_terms, *(_action_text(action) for action in expanded)]):
            hits = find_banned_terms(text)
            if hits:
                policy_findings.append({"path": f"{path}.prompt_surface[{term_index}]", "terms": hits})

    if len(canonical_candidate_locations) != len(set(canonical_candidate_locations)):
        errors.append(_error("location_canonical_collision", "candidate locations resolve to duplicate canonical IDs"))
    if any(count > 1 for count in subject_signatures.values()) or any(count > 1 for count in location_signatures.values()):
        errors.append(_error("duplicate_utility_signature", "candidate utility signatures must be distinct"))
    if policy_findings:
        errors.append(_error("banned_candidate_term", "candidate prompt surface contains banned policy terms"))

    loc_tags = compatibility.get("loc_tags", {})
    universal_locations = set(compatibility.get("universal_locs", []))
    existing_compat_subjects = compatibility.get("characters", {})
    proposed_subject_existing_pairs = 0
    subject_coverage: dict[str, int] = {}
    for subject_id, tags in subject_tags.items():
        compatible = {
            resolve_canonical_location(str(location), aliases, current_locations, overrides)
            for tag in tags
            for location in loc_tags.get(tag, [])
        }
        compatible |= {
            resolve_canonical_location(str(location), aliases, current_locations, overrides)
            for location in universal_locations
        }
        compatible &= current_locations
        subject_coverage[subject_id] = len(compatible)
        proposed_subject_existing_pairs += len(compatible)
        if not compatible:
            errors.append(_error("uncovered_subject_candidate", "subject candidate has no compatible current location", id=subject_id))
    existing_subject_proposed_pairs = 0
    location_coverage: dict[str, int] = {}
    for location_id, tags in location_tags.items():
        compatible_subjects = {
            str(subject_id)
            for subject_id, profile in existing_compat_subjects.items()
            if isinstance(profile, Mapping) and (location_universal[location_id] or bool(tags & set(profile.get("tags", []))))
        }
        compatible_subjects &= current_subjects
        location_coverage[location_id] = len(compatible_subjects)
        existing_subject_proposed_pairs += len(compatible_subjects)
        if not compatible_subjects:
            errors.append(_error("uncovered_location_candidate", "location candidate has no compatible current subject", id=location_id))
    proposed_cross_pairs = sum(
        1
        for subject_id, tags in subject_tags.items()
        for location_id, loc_values in location_tags.items()
        if location_universal[location_id] or bool(tags & loc_values)
    )
    baseline_rows = int(projection.get("baseline_metrics", {}).get("row_count", 0) or 0)
    estimated_covered_pairs = baseline_rows + proposed_subject_existing_pairs + existing_subject_proposed_pairs + proposed_cross_pairs
    projected_rows = int(selected.get("projected_rows", 0) or 0) if isinstance(selected, Mapping) else 0
    if estimated_covered_pairs < projected_rows:
        errors.append(
            _error(
                "insufficient_candidate_coverage",
                "candidate compatibility coverage cannot support projected rows",
                estimated=estimated_covered_pairs,
                projected=projected_rows,
            )
        )

    all_candidate_actions = [_normalized_text(_action_text(action)) for rows in expanded_actions.values() for action in rows]
    candidate_counts = Counter(text for text in all_candidate_actions if text)
    candidate_duplicate_occurrences = sum(count - 1 for count in candidate_counts.values() if count > 1)
    candidate_duplicate_pressure = (
        candidate_duplicate_occurrences * 10000 // len(all_candidate_actions) if all_candidate_actions else 0
    )
    existing_actions = {
        _normalized_text(_action_text(action))
        for actions in load_action_pools().values()
        if isinstance(actions, list)
        for action in actions
        if _action_text(action)
    }
    direct_normalized = [_normalized_text(text) for text in direct_action_texts if text]
    direct_existing_duplicates = sum(1 for text in direct_normalized if text in existing_actions)
    shared_normalized = [_normalized_text(text) for text in family_action_texts if text]
    shared_existing_reuse = sum(1 for text in shared_normalized if text in existing_actions)
    shared_text_set = set(shared_normalized)
    direct_duplicate_occurrences = sum(
        1 for text in direct_normalized if text in existing_actions or text in shared_text_set
    ) + sum(count - 1 for count in Counter(direct_normalized).values() if count > 1)
    direct_duplicate_pressure = (
        direct_duplicate_occurrences * 10000 // len(direct_normalized) if direct_normalized else 0
    )

    limits = catalog.get("quality_limits")
    _append_unknown_fields(errors, limits, _LIMIT_FIELDS, path="quality_limits")
    if not isinstance(limits, Mapping):
        limits = {}
    max_duplicate_pressure = limits.get("max_exact_duplicate_pressure_basis_points")
    max_family_reuse = limits.get("max_shared_family_location_reuse")
    if not isinstance(max_duplicate_pressure, int) or isinstance(max_duplicate_pressure, bool) or not 0 <= max_duplicate_pressure <= 10000:
        errors.append(_error("invalid_quality_limit", "duplicate pressure limit must be basis points"))
        max_duplicate_pressure = 0
    if not isinstance(max_family_reuse, int) or isinstance(max_family_reuse, bool) or max_family_reuse <= 0:
        errors.append(_error("invalid_quality_limit", "family reuse limit must be positive"))
        max_family_reuse = 0
    if candidate_duplicate_pressure > max_duplicate_pressure:
        errors.append(
            _error(
                "duplicate_pressure_exceeded",
                "total exact duplicate pressure exceeds the catalog limit",
                actual=candidate_duplicate_pressure,
                limit=max_duplicate_pressure,
            )
        )
    existing_family_counts = _existing_family_reuse_counts()
    resulting_family_counts = {
        family: existing_family_counts[family] + candidate_family_counts[family]
        for family in sorted(set(existing_family_counts) | set(candidate_family_counts))
    }
    over_reused = {family: count for family, count in resulting_family_counts.items() if count > max_family_reuse}
    if over_reused:
        errors.append(_error("action_family_reuse_exceeded", "shared family reuse exceeds the catalog limit", families=over_reused))

    catalog_sha = _hash_value(dict(catalog))
    prompt_quality, receipt_errors = _derive_prompt_quality_state(
        catalog.get("prompt_quality_receipt"),
        catalog_sha256=catalog_sha,
    )
    errors.extend(receipt_errors)
    structural_status = "pass" if not errors else "fail"
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "catalog_sha256": catalog_sha,
        "scenario_binding": {
            "scenario_id": scenario_id,
            "scenario_manifest_sha256": projection.get("scenario_manifest_sha256"),
            "projection_report_sha256": projection_sha,
            "baseline_manifest_sha256": projection.get("baseline_manifest_sha256"),
        },
        "structural_status": structural_status,
        "eligible_for_prompt_evaluation": structural_status == "pass",
        "promotion_ready": structural_status == "pass" and prompt_quality["status"] == "pass",
        "prompt_quality": prompt_quality,
        "identity_analysis": {
            "subject_count": len(subject_ids),
            "location_count": len(location_ids),
            "subject_ids": sorted(subject_ids),
            "location_ids": sorted(location_ids),
        },
        "utility_analysis": {
            "subject_signature_count": len(subject_signatures),
            "location_signature_count": len(location_signatures),
            "human_semantic_review_required": True,
        },
        "compatibility_coverage": {
            "proposed_subject_existing_location_pairs": proposed_subject_existing_pairs,
            "existing_subject_proposed_location_pairs": existing_subject_proposed_pairs,
            "proposed_cross_pairs": proposed_cross_pairs,
            "estimated_total_rows": estimated_covered_pairs,
            "projected_rows": projected_rows,
            "coverage_margin": estimated_covered_pairs - projected_rows,
            "subject_pair_counts": dict(sorted(subject_coverage.items())),
            "location_pair_counts": dict(sorted(location_coverage.items())),
        },
        "action_family_analysis": {
            "candidate_family_refs": dict(sorted(candidate_family_counts.items())),
            "resulting_existing_plus_candidate_reuse": resulting_family_counts,
            "candidate_location_action_depths": dict(sorted(candidate_action_depths.items())),
            "candidate_action_depth_histogram": dict(sorted(Counter(candidate_action_depths.values()).items())),
            "shared_family_action_occurrences": len(shared_normalized),
            "shared_family_existing_reuse_occurrences": shared_existing_reuse,
        },
        "duplicate_pressure": {
            "candidate_total_actions": len(all_candidate_actions),
            "candidate_duplicate_occurrences": candidate_duplicate_occurrences,
            "candidate_duplicate_pressure_basis_points": candidate_duplicate_pressure,
            "direct_action_count": len(direct_normalized),
            "direct_existing_duplicate_occurrences": direct_existing_duplicates,
            "direct_duplicate_pressure_basis_points": direct_duplicate_pressure,
            "intentional_shared_family_existing_reuse_occurrences": shared_existing_reuse,
        },
        "policy_findings": policy_findings,
        "errors": errors,
    }


def validate_candidate_catalog(
    catalog: Mapping[str, Any],
    *,
    scenario_manifest: Mapping[str, Any],
    projection_report: Mapping[str, Any],
) -> list[dict]:
    return _evaluate_catalog(
        catalog,
        scenario_manifest=scenario_manifest,
        projection_report=projection_report,
    )["errors"]


def analyze_candidate_catalog(
    catalog: Mapping[str, Any],
    *,
    scenario_manifest: Mapping[str, Any],
    projection_report: Mapping[str, Any],
    baseline_manifest_path: Path | None = None,
) -> dict:
    return _evaluate_catalog(
        catalog, scenario_manifest=scenario_manifest, projection_report=projection_report,
        baseline_manifest_path=baseline_manifest_path,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze a V150 variation candidate catalog without mutating data.")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--scenario-file", required=True)
    parser.add_argument("--projection-report", required=True)
    parser.add_argument("--baseline-manifest", type=Path)
    args = parser.parse_args()
    try:
        catalog = load_candidate_catalog(args.catalog)
        scenario = load_candidate_catalog(args.scenario_file)
        projection = load_candidate_catalog(args.projection_report)
        report = analyze_candidate_catalog(
            catalog, scenario_manifest=scenario, projection_report=projection,
            baseline_manifest_path=args.baseline_manifest,
        )
    except (OSError, json.JSONDecodeError, WorkflowValidationError) as exc:
        if isinstance(exc, WorkflowValidationError):
            envelope = exc.to_envelope()
        else:
            envelope = WorkflowValidationError(
                "candidate_analysis_failed",
                "candidate analysis input could not be processed",
                exception_type=type(exc).__name__,
            ).to_envelope()
        sys.stderr.buffer.write(canonical_json_bytes(envelope))
        return 2
    sys.stdout.buffer.write(canonical_json_bytes(report))
    return 0 if report["structural_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
