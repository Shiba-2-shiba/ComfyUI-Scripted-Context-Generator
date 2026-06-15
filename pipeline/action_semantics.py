"""Semantic ranking helpers for action slot enrichment."""

from __future__ import annotations

from typing import Any, Sequence

try:  # pragma: no cover - package mode varies in tests and ComfyUI
    from ..vocab.loader import load_json
    from ..vocab.semantic_space import Vector, normalize_vector, rank_candidates
    from .semantic_epig import load_semantic_epig_config, semantic_mode
except ImportError:  # pragma: no cover
    from vocab.loader import load_json
    from vocab.semantic_space import Vector, normalize_vector, rank_candidates
    from pipeline.semantic_epig import load_semantic_epig_config, semantic_mode

PROFILE_FILE = "action_semantic_profiles.json"
DESCRIPTOR_FILE = "action_slot_descriptors.json"
ACTION_AXES = (
    "motion_energy",
    "body_openness",
    "precision",
    "object_coupling",
    "social_intensity",
    "time_pressure",
)


def _load_json_dict(filename: str) -> dict[str, Any]:
    try:
        payload = load_json(filename)
    except (FileNotFoundError, OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_action_semantic_profiles() -> dict[str, Any]:
    return _load_json_dict(PROFILE_FILE)


def load_action_slot_descriptors() -> dict[str, Any]:
    return _load_json_dict(DESCRIPTOR_FILE)


def _profile_vector(purpose: str) -> Vector:
    payload = load_action_semantic_profiles()
    profiles = payload.get("profiles", {})
    if not isinstance(profiles, dict):
        return normalize_vector({}, ACTION_AXES)
    profile = profiles.get(str(purpose or "").strip().lower(), {})
    if not isinstance(profile, dict):
        return normalize_vector({}, ACTION_AXES)
    return normalize_vector(profile.get("vector", {}), ACTION_AXES)


def _nudge(vector: Vector, axis: str, amount: float) -> None:
    vector[axis] = max(0.0, min(1.0, float(vector.get(axis, 0.5)) + amount))


def build_action_target_vector(
    purpose: str,
    progress_state: str = "",
    social_distance: str = "",
    obstacle_or_trigger: str = "",
    loc: str = "",
    action_text: str = "",
    selected_objects: set[str] | None = None,
) -> Vector:
    vector = _profile_vector(purpose)
    progress = str(progress_state or "").strip().lower()
    social = str(social_distance or "").strip().lower()
    obstacle = str(obstacle_or_trigger or "").strip().lower()
    text = f"{loc} {action_text}".lower()
    objects = set(selected_objects or set())

    if progress == "preparing":
        _nudge(vector, "time_pressure", 0.08)
    elif progress == "wrapping_up":
        _nudge(vector, "precision", 0.05)
    if social == "crowd":
        _nudge(vector, "social_intensity", 0.12)
        _nudge(vector, "time_pressure", 0.08)
    elif social == "alone":
        _nudge(vector, "social_intensity", -0.10)
    if obstacle in {"delay", "luggage", "forgot"}:
        _nudge(vector, "time_pressure", 0.12)
    if obstacle in {"spill", "wind"}:
        _nudge(vector, "motion_energy", 0.08)
    if objects or any(term in text for term in ("book", "phone", "coffee", "screen", "bag")):
        _nudge(vector, "object_coupling", 0.08)
    if any(term in text for term in ("station", "commute", "train", "bus", "platform")):
        _nudge(vector, "time_pressure", 0.05)
        _nudge(vector, "motion_energy", 0.05)

    return normalize_vector(vector, ACTION_AXES)


def _descriptor_lookup(slot_name: str) -> dict[str, dict[str, Any]]:
    payload = load_action_slot_descriptors()
    slots = payload.get("slots", {})
    if not isinstance(slots, dict):
        return {}
    descriptors = slots.get(str(slot_name or ""), [])
    if not isinstance(descriptors, list):
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for index, descriptor in enumerate(descriptors):
        if not isinstance(descriptor, dict):
            continue
        text = str(descriptor.get("text", "")).strip()
        if not text:
            continue
        item = dict(descriptor)
        item.setdefault("source", f"action_slot_descriptors:{slot_name}[{index}]")
        item.setdefault("role", slot_name)
        lookup[text] = item
    return lookup


def rank_action_slot_options(
    slot_name: str,
    options: Sequence[str],
    target_vector: dict[str, float],
    loc: str = "",
) -> list[dict[str, Any]]:
    payload = load_action_slot_descriptors()
    axis_weights = payload.get("axis_weights", {}) if isinstance(payload, dict) else {}
    lookup = _descriptor_lookup(slot_name)
    candidates: list[dict[str, Any]] = []
    for index, option in enumerate(options):
        text = str(option or "").strip()
        if not text:
            continue
        descriptor = dict(lookup.get(text, {}))
        descriptor.setdefault("text", text)
        descriptor.setdefault("vector", {})
        descriptor.setdefault("source", f"runtime:{slot_name}[{index}]")
        descriptor.setdefault("role", slot_name)
        candidates.append(descriptor)

    return rank_candidates(
        candidates,
        normalize_vector(target_vector, ACTION_AXES),
        ACTION_AXES,
        axis_weights=axis_weights if isinstance(axis_weights, dict) else None,
        gamma=float(load_semantic_epig_config().get("gamma", 2.0) or 2.0),
    )


def semantic_slot_weights(slot_name: str, options: Sequence[str], target_vector: dict[str, float]) -> dict[str, float]:
    ranked = rank_action_slot_options(slot_name, options, target_vector)
    return {str(item["text"]): float(item.get("score", 0.0) or 0.0) for item in ranked}


def semantic_action_debug_payload(
    *,
    mode: str | None = None,
    target_vector: dict[str, float] | None = None,
    slot_rankings: dict[str, list[dict[str, Any]]] | None = None,
    selected_by_semantic: bool = False,
) -> dict[str, Any]:
    compact_rankings: dict[str, list[dict[str, Any]]] = {}
    for slot_name, ranking in (slot_rankings or {}).items():
        compact_rankings[slot_name] = [
            {
                "text": str(item.get("text", "")),
                "score": round(float(item.get("score", 0.0) or 0.0), 4),
                "distance": round(float(item.get("distance", 0.0) or 0.0), 4),
                "source": str(item.get("source", "")),
                "role": str(item.get("role", slot_name)),
            }
            for item in ranking[:5]
        ]
    return {
        "mode": mode or semantic_mode("action"),
        "target_vector": normalize_vector(target_vector or {}, ACTION_AXES),
        "slot_rankings": compact_rankings,
        "selected_by_semantic": bool(selected_by_semantic),
    }
