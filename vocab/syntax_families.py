"""Validation of candidate syntax metadata, independent of runtime selection."""

from __future__ import annotations

import math
from typing import Any


CATALOG_FILENAME = "natural_language_realizer_v2.json"
BASELINE_FAMILY = "subject_action_scene"
SCHEMA_VERSION = "syntax-family-catalog/v1"
DISCOURSE_ROLES = frozenset({"neutral", "focused", "quiet", "transition", "social"})
ACTION_SURFACES = frozenset({"clause", "gerund", "fragment", "framed"})
CONTENT_SLOTS = frozenset({"subject", "predicate", "object", "adjunct", "scene"})
SAFETY_FACTS = frozenset({
    "standalone_scene_safe", "scene_lead_safe", "same_subject_attachment_safe",
    "frame_predicate_safe", "scene_adjunct_safe", "scene_action_nonduplicative",
    "fragment_subject_action", "independent_action_subject", "scene_action_overlap",
})
# These are nominal eligible layouts, not templates or vocabulary. An
# unconditional baseline with missing slots may emit fewer clauses or no text.
_LAYOUTS = {
    BASELINE_FAMILY: (1, ["subject", "action", "scene"]),
    "subject_action__scene_tail": (2, ["subject", "action", "scene"]),
    "scene_lead_subject_action": (1, ["scene", "subject", "action"]),
    "action_lead_subject_scene": (1, ["action", "subject", "scene"]),
    "subject_scene_action": (1, ["subject", "scene", "action"]),
    "subject_action_scene_insert": (1, ["subject", "action", "scene"]),
}
_REQUIRED_SAFETY = {
    "subject_action__scene_tail": {"standalone_scene_safe"},
    "scene_lead_subject_action": {"scene_lead_safe"},
    "action_lead_subject_scene": {"same_subject_attachment_safe"},
    "subject_scene_action": {"frame_predicate_safe", "scene_adjunct_safe"},
    "subject_action_scene_insert": {"frame_predicate_safe", "scene_adjunct_safe", "scene_action_nonduplicative"},
}
_FAMILY_FIELDS = {
    "key", "roles", "required_slots", "allowed_action_surfaces", "avoid_action_surfaces",
    "requires", "forbids", "sentence_count", "clause_order", "fallback_family", "weight",
}


def validate_syntax_family_catalog(payload: Any) -> list[str]:
    """Return deterministic diagnostics; do not load files or mutate the payload.

    A future selector must treat the baseline as unconditional. For other families,
    every required safety fact must be True and every forbidden fact must be
    explicitly False. Missing/None facts are unknown and exclude that family.
    Action-surface checks apply to the rendered surface, not the original verb.
    Optional families beyond these six need an explicit schema/validation update.
    """
    if not isinstance(payload, dict):
        return ["catalog must be an object"]
    issues: list[str] = []
    if set(payload) != {"schema_version", "baseline_family", "families"}:
        issues.append("catalog fields must be schema_version, baseline_family, families")
    if payload.get("schema_version") != SCHEMA_VERSION:
        issues.append("unsupported schema_version")
    if payload.get("baseline_family") != BASELINE_FAMILY:
        issues.append("baseline_family must be subject_action_scene")
    families = payload.get("families")
    if not isinstance(families, list):
        return sorted(issues + ["families must be a list"])
    seen: set[str] = set()

    for index, family in enumerate(families):
        path = f"families[{index}]"
        if not isinstance(family, dict):
            issues.append(f"{path} must be an object")
            continue
        if set(family) != _FAMILY_FIELDS:
            issues.append(f"{path} has missing or unknown fields")
        key = family.get("key")
        if not isinstance(key, str) or key not in _LAYOUTS:
            issues.append(f"{path}.key must name a supported family")
            continue
        if key in seen:
            issues.append(f"{path}.key duplicate: {key}")
        seen.add(key)
        baseline = key == BASELINE_FAMILY

        def members(field: str, allowed: frozenset[str], *, nonempty: bool = False) -> set[str]:
            values = family.get(field)
            if (not isinstance(values, list) or not all(isinstance(value, str) for value in values)
                    or (nonempty and not values)):
                issues.append(f"{path}.{field} must be a {'nonempty ' if nonempty else ''}string list")
                return set()
            result = set(values)
            if len(result) != len(values) or not result <= allowed:
                issues.append(f"{path}.{field} has duplicate or unknown values")
            return result

        roles = members("roles", DISCOURSE_ROLES | ({"*"} if baseline else set()), nonempty=True)
        slots = members("required_slots", CONTENT_SLOTS)
        allowed = members("allowed_action_surfaces", ACTION_SURFACES | ({"*"} if baseline else set()), nonempty=True)
        avoided = members("avoid_action_surfaces", ACTION_SURFACES)
        required = members("requires", SAFETY_FACTS)
        forbidden = members("forbids", SAFETY_FACTS)
        if allowed & avoided or required & forbidden:
            issues.append(f"{path} has contradictory constraints")
        sentences, order = _LAYOUTS[key]
        if type(family.get("sentence_count")) is not int or family["sentence_count"] != sentences:
            issues.append(f"{path}.sentence_count does not match family layout")
        if family.get("clause_order") != order:
            issues.append(f"{path}.clause_order does not match family layout")
        weight = family.get("weight")
        try:
            valid_weight = type(weight) in (int, float) and weight > 0 and math.isfinite(weight)
        except OverflowError:
            valid_weight = False
        if not valid_weight:
            issues.append(f"{path}.weight must be positive and finite (not bool)")

        if baseline:
            if roles != {"*"} or allowed != {"*"} or any((slots, required, forbidden, avoided)):
                issues.append(f"{path} baseline must be unconditional")
            if family.get("fallback_family") is not None:
                issues.append(f"{path} baseline must terminate fallback with null")
            continue
        if family.get("fallback_family") != BASELINE_FAMILY:
            issues.append(f"{path}.fallback_family must directly name the baseline")
        minimum_slots = {"subject", "adjunct", "scene"}
        if "frame_predicate_safe" in _REQUIRED_SAFETY[key]:
            minimum_slots.add("predicate")
        if not minimum_slots <= slots or not _REQUIRED_SAFETY[key] <= required:
            issues.append(f"{path} is missing required slots or positive safety facts")
        minimum_forbids = {"independent_action_subject"}
        safe_surfaces = {"gerund", "clause"}
        if key == "action_lead_subject_scene":
            minimum_forbids.add("fragment_subject_action")
            safe_surfaces = {"gerund"}
        if key == "subject_action_scene_insert":
            minimum_forbids.add("scene_action_overlap")
        if not minimum_forbids <= forbidden or not allowed <= safe_surfaces:
            issues.append(f"{path} permits an unsafe action surface or subject/scene attachment")

    if seen != set(_LAYOUTS):
        issues.append("catalog must contain all six required families")
    return sorted(set(issues))
