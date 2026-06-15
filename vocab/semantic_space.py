"""Generic axis-vector ranking helpers for semantic prompt enrichment."""

from __future__ import annotations

import math
from typing import Any, Iterable, Sequence

Vector = dict[str, float]


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_vector(vector: dict[str, Any] | None, axes: Sequence[str]) -> Vector:
    source = vector if isinstance(vector, dict) else {}
    normalized: Vector = {}
    for axis in axes:
        key = str(axis)
        try:
            normalized[key] = clamp01(float(source.get(key, 0.5)))
        except (TypeError, ValueError):
            normalized[key] = 0.5
    return normalized


def weighted_distance(
    left: Vector,
    right: Vector,
    axis_weights: dict[str, float] | None = None,
) -> float:
    axes = sorted(set(left) | set(right))
    if not axes:
        return 0.0

    weights = axis_weights if isinstance(axis_weights, dict) else {}
    total = 0.0
    weight_total = 0.0
    for axis in axes:
        try:
            weight = max(0.0, float(weights.get(axis, 1.0)))
        except (TypeError, ValueError):
            weight = 1.0
        if weight <= 0.0:
            continue
        delta = float(left.get(axis, 0.5)) - float(right.get(axis, 0.5))
        total += weight * (delta * delta)
        weight_total += weight

    if weight_total <= 0.0:
        return 0.0
    return math.sqrt(total / weight_total)


def relevance_from_distance(distance: float, gamma: float = 2.0) -> float:
    return math.exp(-float(gamma) * max(0.0, float(distance)))


def rank_candidates(
    candidates: Iterable[dict[str, Any]],
    target_vector: Vector,
    axes: Sequence[str],
    *,
    axis_weights: dict[str, float] | None = None,
    gamma: float = 2.0,
    text_key: str = "text",
    vector_key: str = "vector",
) -> list[dict[str, Any]]:
    target = normalize_vector(target_vector, axes)
    ranked: list[dict[str, Any]] = []

    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            continue
        text = str(candidate.get(text_key, "")).strip()
        if not text:
            continue
        vector = normalize_vector(candidate.get(vector_key, {}), axes)
        distance = weighted_distance(vector, target, axis_weights=axis_weights)
        item = dict(candidate)
        item["text"] = text
        item["vector"] = vector
        item["distance"] = distance
        item["score"] = relevance_from_distance(distance, gamma=gamma)
        item.setdefault("source", f"candidate[{index}]")
        ranked.append(item)

    ranked.sort(key=lambda item: (-(item.get("score") or 0.0), item["text"]))
    return ranked


def top_window(ranked: Sequence[dict[str, Any]], window_size: int = 3) -> list[dict[str, Any]]:
    try:
        limit = max(0, int(window_size))
    except (TypeError, ValueError):
        limit = 3
    return list(ranked[:limit])


def _iter_vectors(payload: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    if isinstance(payload, dict):
        if "vector" in payload:
            yield f"{path}.vector", payload.get("vector")
        for key, value in payload.items():
            yield from _iter_vectors(value, f"{path}.{key}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            yield from _iter_vectors(value, f"{path}[{index}]")


def validate_axis_payload(
    payload: dict[str, Any],
    required_axes: Sequence[str] | None = None,
) -> list[str]:
    warnings: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be an object"]

    if not payload.get("schema_version"):
        warnings.append("missing schema_version")

    axes = payload.get("axes")
    if not isinstance(axes, list) or not axes:
        warnings.append("axes must be a non-empty list")
        axes = []

    normalized_axes = [str(axis) for axis in axes if str(axis).strip()]
    if len(normalized_axes) != len(set(normalized_axes)):
        warnings.append("axes contains duplicate entries")

    for required_axis in required_axes or ():
        if str(required_axis) not in normalized_axes:
            warnings.append(f"missing required axis '{required_axis}'")

    axis_set = set(normalized_axes)
    for path, vector in _iter_vectors(payload):
        if not isinstance(vector, dict):
            warnings.append(f"{path} must be an object")
            continue
        for axis, value in vector.items():
            axis_name = str(axis)
            if axis_set and axis_name not in axis_set:
                warnings.append(f"{path}.{axis_name} is not declared in axes")
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                warnings.append(f"{path}.{axis_name} must be numeric")
                continue
            if not 0.0 <= numeric <= 1.0:
                warnings.append(f"{path}.{axis_name} must be between 0.0 and 1.0")
        missing = sorted(axis_set - {str(axis) for axis in vector})
        for axis_name in missing:
            warnings.append(f"{path} missing axis '{axis_name}'")

    return warnings
