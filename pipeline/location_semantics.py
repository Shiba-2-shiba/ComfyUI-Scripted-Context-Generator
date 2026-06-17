"""Scene-axis ranking helpers for location prompt expansion."""

from __future__ import annotations

from typing import Any, Sequence

try:  # pragma: no cover - package mode varies in tests and ComfyUI
    from ..vocab.loader import load_json
    from ..vocab.semantic_space import Vector, normalize_vector, rank_candidates
    from .semantic_epig import load_semantic_epig_config, selection_debug_fields, semantic_mode
except ImportError:  # pragma: no cover
    from vocab.loader import load_json
    from vocab.semantic_space import Vector, normalize_vector, rank_candidates
    from pipeline.semantic_epig import load_semantic_epig_config, selection_debug_fields, semantic_mode

PROFILE_FILE = "location_axis_profiles.json"
DESCRIPTOR_FILE = "staging_axis_descriptors.json"
SCENE_AXES = (
    "crowd_density",
    "activity_level",
    "openness",
    "orderliness",
    "weather_intensity",
    "light_softness",
    "intimacy",
    "time_pressure",
)


def _load_json_dict(filename: str) -> dict[str, Any]:
    try:
        payload = load_json(filename)
    except (FileNotFoundError, OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_location_axis_profiles() -> dict[str, Any]:
    return _load_json_dict(PROFILE_FILE)


def load_staging_axis_descriptors() -> dict[str, Any]:
    return _load_json_dict(DESCRIPTOR_FILE)


def _nudge(vector: Vector, axis: str, amount: float) -> None:
    vector[axis] = max(0.0, min(1.0, float(vector.get(axis, 0.5)) + amount))


def build_scene_target_vector(loc_key: str, action_text: str = "", mood_text: str = "") -> Vector:
    payload = load_location_axis_profiles()
    profiles = payload.get("profiles", {}) if isinstance(payload, dict) else {}
    profile = profiles.get(str(loc_key or "").strip().lower(), {}) if isinstance(profiles, dict) else {}
    vector = normalize_vector(profile.get("vector", {}) if isinstance(profile, dict) else {}, SCENE_AXES)

    action = str(action_text or "").lower()
    mood = str(mood_text or "").lower()
    if any(token in action for token in ("commute", "waiting", "delay", "train", "bus")):
        _nudge(vector, "time_pressure", 0.15)
        _nudge(vector, "crowd_density", 0.1)
        _nudge(vector, "activity_level", 0.05)
    if any(token in action for token in ("study", "reading", "writing", "reviewing")):
        _nudge(vector, "orderliness", 0.1)
        _nudge(vector, "activity_level", -0.1)
    if any(token in action for token in ("rest", "relax", "dozing", "sitting quietly")):
        _nudge(vector, "activity_level", -0.15)
        _nudge(vector, "light_softness", 0.1)
    if any(token in action for token in ("running", "dancing", "playing")):
        _nudge(vector, "activity_level", 0.15)
    if any(token in mood for token in ("tense", "urgent", "impatient")):
        _nudge(vector, "time_pressure", 0.05)
    if any(token in mood for token in ("calm", "quiet", "peaceful")):
        _nudge(vector, "activity_level", -0.05)
        _nudge(vector, "light_softness", 0.05)

    return normalize_vector(vector, SCENE_AXES)


def _descriptor_lookup(section_name: str) -> dict[str, dict[str, Any]]:
    payload = load_staging_axis_descriptors()
    descriptors = payload.get("descriptors", {}) if isinstance(payload, dict) else {}
    section_descriptors = descriptors.get(str(section_name or ""), []) if isinstance(descriptors, dict) else []
    if not isinstance(section_descriptors, list):
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for index, descriptor in enumerate(section_descriptors):
        if not isinstance(descriptor, dict):
            continue
        text = str(descriptor.get("text", "")).strip()
        if not text:
            continue
        item = dict(descriptor)
        item.setdefault("source", f"staging_axis_descriptors:{section_name}[{index}]")
        item.setdefault("role", section_name)
        lookup[text] = item
    return lookup


def rank_location_segment_options(
    section_name: str,
    options: Sequence[str],
    target_vector: dict[str, float],
    loc_key: str = "",
) -> list[dict[str, Any]]:
    payload = load_staging_axis_descriptors()
    axis_weights = payload.get("axis_weights", {}) if isinstance(payload, dict) else {}
    lookup = _descriptor_lookup(section_name)
    candidates: list[dict[str, Any]] = []
    for index, option in enumerate(options):
        text = str(option or "").strip()
        if not text:
            continue
        descriptor = dict(lookup.get(text, {}))
        descriptor.setdefault("text", text)
        descriptor.setdefault("vector", {})
        descriptor.setdefault("source", f"runtime:{section_name}[{index}]")
        descriptor.setdefault("role", section_name)
        candidates.append(descriptor)

    return rank_candidates(
        candidates,
        normalize_vector(target_vector, SCENE_AXES),
        SCENE_AXES,
        axis_weights=axis_weights if isinstance(axis_weights, dict) else None,
        gamma=float(load_semantic_epig_config().get("gamma", 2.0) or 2.0),
    )


def semantic_location_weights(section_name: str, options: Sequence[str], target_vector: dict[str, float]) -> dict[str, float]:
    ranked = rank_location_segment_options(section_name, options, target_vector)
    return {str(item["text"]): float(item.get("score", 0.0) or 0.0) for item in ranked}


def semantic_location_debug_payload(
    *,
    mode: str | None = None,
    target_vector: dict[str, float] | None = None,
    segment_rankings: dict[str, list[dict[str, Any]]] | None = None,
    section_changes: dict[str, dict[str, Any]] | None = None,
    selected_by_semantic: bool = False,
) -> dict[str, Any]:
    resolved_mode = mode or semantic_mode("location_scene")
    compact_rankings: dict[str, list[dict[str, Any]]] = {}
    for section_name, ranking in (segment_rankings or {}).items():
        compact_rankings[section_name] = [
            {
                "text": str(item.get("text", "")),
                "score": round(float(item.get("score", 0.0) or 0.0), 4),
                "distance": round(float(item.get("distance", 0.0) or 0.0), 4),
                "source": str(item.get("source", "")),
                "role": str(item.get("role", section_name)),
            }
            for item in ranking[:5]
        ]
    compact_changes: dict[str, dict[str, Any]] = {}
    for section_name, change in (section_changes or {}).items():
        if not isinstance(change, dict):
            continue
        compact_changes[section_name] = {
            "baseline": change.get("baseline", ""),
            "semantic": change.get("semantic", ""),
            "changed": bool(change.get("changed", False)),
            "semantic_top_candidate": change.get("semantic_top_candidate", ""),
            "selected_candidate_rank": change.get("selected_candidate_rank"),
        }
    changed_sections = [section for section, change in compact_changes.items() if change.get("changed")]
    return {
        "mode": resolved_mode,
        "target_vector": normalize_vector(target_vector or {}, SCENE_AXES),
        "segment_rankings": compact_rankings,
        "section_changes": compact_changes,
        "changed_sections": changed_sections,
        "selected_by_semantic": bool(selected_by_semantic),
        **selection_debug_fields(
            mode=resolved_mode,
            semantic_scoring_enabled=bool(segment_rankings),
            selection_changed_by_semantic=bool(changed_sections),
        ),
    }
