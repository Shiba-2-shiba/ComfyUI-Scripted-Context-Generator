from __future__ import annotations

from typing import Mapping, Sequence

try:
    from ..object_focus_service import background_weight_map, extract_object_flags
except ImportError:
    from object_focus_service import background_weight_map, extract_object_flags


def semantic_score_multiplier(option: str, semantic_scores: Mapping[str, float] | None = None) -> float:
    if not semantic_scores:
        return 1.0
    score = max(0.0, float(semantic_scores.get(str(option), 0.0) or 0.0))
    return 0.50 + score


def weighted_choice(options: Sequence[str], rng, loc_tag: str, section_name: str, semantic_scores=None) -> str:
    if not options:
        return ""
    weights_map = background_weight_map(loc_tag, section_name)
    weights = [
        max(0.01, float(weights_map.get(str(option), 1.0))) * semantic_score_multiplier(option, semantic_scores)
        for option in options
    ]
    return rng.choices(list(options), weights=weights, k=1)[0]


def weighted_sample(options: Sequence[str], rng, k: int, loc_tag: str, section_name: str, semantic_scores=None) -> list[str]:
    available = list(options)
    selected = []
    while available and len(selected) < k:
        weights_map = background_weight_map(loc_tag, section_name)
        weights = [
            max(0.01, float(weights_map.get(str(option), 1.0))) * semantic_score_multiplier(option, semantic_scores)
            for option in available
        ]
        chosen = rng.choices(available, weights=weights, k=1)[0]
        selected.append(chosen)
        available.remove(chosen)
    return selected


def weighted_sample_with_recent_object_guard(
    options: Sequence[str],
    rng,
    k: int,
    loc_tag: str,
    section_name: str,
    recent_objects=None,
    semantic_scores=None,
) -> list[str]:
    available = list(options)
    selected = []
    recent_objects = set(recent_objects or [])
    while available and len(selected) < k:
        weights_map = background_weight_map(loc_tag, section_name)
        weights = []
        for option in available:
            base_weight = max(0.01, float(weights_map.get(str(option), 1.0)))
            if extract_object_flags(option) & recent_objects:
                base_weight *= 0.35
            base_weight *= semantic_score_multiplier(option, semantic_scores)
            weights.append(base_weight)
        chosen = rng.choices(available, weights=weights, k=1)[0]
        selected.append(chosen)
        available.remove(chosen)
    return selected


def semantic_choice(options: Sequence[str], rng, semantic_scores=None) -> str:
    if not options:
        return ""
    values = list(options)
    if not semantic_scores:
        return rng.choice(values)
    weights = [semantic_score_multiplier(option, semantic_scores) for option in values]
    return rng.choices(values, weights=weights, k=1)[0]
