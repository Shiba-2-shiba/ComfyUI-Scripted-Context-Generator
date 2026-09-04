"""TPO scoring helpers for clothing prompt expansion."""

from __future__ import annotations

from typing import Any

try:  # pragma: no cover - package mode varies in tests and ComfyUI
    from ..vocab.loader import load_json
    from ..vocab.semantic_space import Vector, normalize_vector, relevance_from_distance, weighted_distance
    from .semantic_epig import selection_debug_fields, semantic_mode
except ImportError:  # pragma: no cover
    from vocab.loader import load_json
    from vocab.semantic_space import Vector, normalize_vector, relevance_from_distance, weighted_distance
    from pipeline.semantic_epig import selection_debug_fields, semantic_mode

PROFILE_FILE = "clothing_axis_profiles.json"
CLOTHING_AXES = (
    "formality",
    "warmth",
    "movement_freedom",
    "softness",
    "weather_fit",
    "activity_fit",
    "visual_prominence",
)
CONTEXTUAL_THEME_FALLBACKS = (
    {
        "locations": {"vehicle_repair_garage", "maker_space", "clockwork_workshop"},
        "action_terms": ("repair", "tightening a bolt", "open hood", "maintenance", "tool"),
        "theme": "casual",
    },
    {
        "locations": {"bedroom_boudoir", "bedroom", "luxury_hotel_room"},
        "action_terms": ("waking up", "stretching arms", "before sleeping", "getting ready for bed"),
        "theme": "casual",
    },
    {
        "locations": {"forest_cabin", "mountain_resort"},
        "action_terms": ("long walk", "water container", "hiking", "trail"),
        "theme": "casual",
    },
)
NON_FORMAL_OFFICE_THEME_FALLBACK_LOCATIONS = {
    "clean_modern_kitchen",
    "karaoke_bar",
    "shopping_mall_atrium",
    "street_cafe",
    "university_campus_courtyard",
}
OPERATIONAL_NON_FORMAL_LOCATIONS = {
    "community_garden",
    "fire_station",
    "greenhouse_nursery",
    "maker_space",
    "vehicle_repair_garage",
}


def _load_profiles() -> dict[str, Any]:
    try:
        payload = load_json(PROFILE_FILE)
    except (FileNotFoundError, OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _vector_from(section: str, key: str) -> Vector | None:
    payload = _load_profiles()
    entries = payload.get(section, {}) if isinstance(payload, dict) else {}
    if not isinstance(entries, dict):
        return None
    entry = entries.get(str(key or "").strip().lower())
    if not isinstance(entry, dict):
        return None
    return normalize_vector(entry.get("vector", {}), CLOTHING_AXES)


def _average_vectors(vectors: list[Vector]) -> Vector:
    if not vectors:
        return normalize_vector({}, CLOTHING_AXES)
    averaged: Vector = {}
    for axis in CLOTHING_AXES:
        averaged[axis] = sum(vector.get(axis, 0.5) for vector in vectors) / len(vectors)
    return normalize_vector(averaged, CLOTHING_AXES)


def _action_key(action_text: str) -> str:
    text = str(action_text or "").lower()
    if any(token in text for token in ("commute", "train", "bus", "walking", "waiting")):
        return "commute"
    if any(token in text for token in ("study", "reading", "writing", "reviewing")):
        return "study"
    if any(token in text for token in ("work", "typing", "meeting", "document")):
        return "work"
    if any(token in text for token in ("rest", "relax", "sitting quietly", "dozing")):
        return "rest"
    if any(token in text for token in ("shop", "browsing", "checking out")):
        return "shop"
    return ""


def resolve_contextual_clothing_theme(loc: str, action_text: str, theme_key: str) -> str:
    requested = str(theme_key or "").strip().lower()
    if requested != "office_lady":
        return requested
    location = str(loc or "").strip().lower()
    action = str(action_text or "").strip().lower()
    if location in OPERATIONAL_NON_FORMAL_LOCATIONS:
        return "casual"
    for fallback in CONTEXTUAL_THEME_FALLBACKS:
        if location in fallback["locations"] and any(term in action for term in fallback["action_terms"]):
            return str(fallback["theme"])
    if location in NON_FORMAL_OFFICE_THEME_FALLBACK_LOCATIONS and _action_key(action) != "work":
        return "casual"
    return requested


def build_clothing_target_vector(loc: str, action_text: str = "", theme_key: str = "") -> Vector:
    vectors: list[Vector] = []
    for section, key in (
        ("location_targets", loc),
        ("action_targets", _action_key(action_text)),
        ("theme_profiles", theme_key),
    ):
        vector = _vector_from(section, key)
        if vector is not None:
            vectors.append(vector)
    return _average_vectors(vectors)


def _candidate_vector(decision: dict[str, Any]) -> Vector:
    vectors: list[Vector] = []
    for section, key in (
        ("theme_profiles", decision.get("theme", "")),
        ("pack_profiles", decision.get("base_pack", "")),
        ("pack_profiles", decision.get("outerwear_pack", "")),
    ):
        vector = _vector_from(section, str(key))
        if vector is not None:
            vectors.append(vector)
    return _average_vectors(vectors)


def score_clothing_decision(decision: dict[str, Any], prompt: str, target_vector: dict[str, float]) -> dict[str, Any]:
    candidate = _candidate_vector(decision)
    target = normalize_vector(target_vector, CLOTHING_AXES)
    distance = weighted_distance(candidate, target)
    score = relevance_from_distance(distance)
    return {
        "candidate_vector": candidate,
        "score": score,
        "distance": distance,
        "semantic_penalty": semantic_clothing_penalty(score),
    }


def semantic_clothing_penalty(score: float, max_penalty: int = 4) -> int:
    numeric = max(0.0, min(1.0, float(score)))
    if numeric >= 0.75:
        return 0
    if numeric >= 0.55:
        return 1
    if numeric >= 0.35:
        return max(1, min(max_penalty, 2))
    return max_penalty


def clothing_semantic_debug_payload(
    *,
    target_vector: dict[str, float],
    candidate_scores: list[dict[str, Any]],
    selected_attempt_index: int,
    baseline_selected_attempt_index: int | None = None,
    semantic_selected_attempt_index: int | None = None,
    mode: str | None = None,
    selected_by_semantic: bool = False,
) -> dict[str, Any]:
    resolved_mode = mode or semantic_mode("clothing_tpo")
    normalized_target = {
        axis: round(float(value), 4)
        for axis, value in normalize_vector(target_vector, CLOTHING_AXES).items()
    }
    baseline_index = selected_attempt_index if baseline_selected_attempt_index is None else int(baseline_selected_attempt_index)
    semantic_index = selected_attempt_index if semantic_selected_attempt_index is None else int(semantic_selected_attempt_index)
    detailed_indices = {int(selected_attempt_index), baseline_index, semantic_index}
    normalized_scores = []
    for item in candidate_scores:
        attempt_index = int(item.get("attempt_index", 0))
        compact = {
            "attempt_index": attempt_index,
            "score": round(float(item.get("score", 0.0) or 0.0), 4),
        }
        if attempt_index in detailed_indices:
            compact.update(
                {
                    "distance": round(float(item.get("distance", 0.0) or 0.0), 4),
                    "semantic_penalty": int(item.get("semantic_penalty", 0) or 0),
                    "repeat_penalty": int(item.get("repeat_penalty", 0) or 0),
                    "final_penalty": int(
                        item.get("final_penalty", item.get("repeat_penalty", 0)) or 0
                    ),
                }
            )
        normalized_scores.append(compact)
    return {
        "mode": resolved_mode,
        "target_vector": normalized_target,
        "candidate_score_count": len(candidate_scores),
        "candidate_scores": normalized_scores,
        "selected_attempt_index": int(selected_attempt_index),
        "baseline_selected_attempt_index": baseline_index,
        "semantic_selected_attempt_index": semantic_index,
        "selected_by_semantic": bool(selected_by_semantic),
        **selection_debug_fields(
            mode=resolved_mode,
            semantic_scoring_enabled=bool(candidate_scores),
            baseline_candidate=baseline_index,
            semantic_candidate=semantic_index,
            semantic_top_candidate=semantic_index,
            selected_candidate_rank=semantic_index,
            selection_changed_by_semantic=baseline_index != semantic_index,
        ),
    }
