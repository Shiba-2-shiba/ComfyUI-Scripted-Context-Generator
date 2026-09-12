"""Valence-arousal helpers for emotion-aware garnish selection."""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .loader import load_json

VAD = Tuple[float, float]
PROFILE_FILE = "emotion_vad_profiles.json"

_LOW_AROUSAL_TERMS = (
    "calm",
    "gentle",
    "soft",
    "relaxed",
    "easy",
    "quiet",
    "settled",
    "still",
    "slow",
    "unhurried",
    "faint",
    "contented",
    "half-lidded",
)

_HIGH_AROUSAL_TERMS = (
    "bright",
    "quick",
    "sharp",
    "hard",
    "tense",
    "rigid",
    "restless",
    "darting",
    "flicking",
    "drumming",
    "pacing",
    "breathing hard",
    "clenched",
    "glaring",
    "furrowed",
    "excited",
    "bouncing",
)

_NEGATIVE_VALENCE_TERMS = (
    "sad",
    "downcast",
    "distant",
    "tired",
    "trembling",
    "small",
    "rigid",
    "hard",
    "clenched",
    "strained",
    "uneasy",
    "impatient",
    "frown",
    "glaring",
)

_POSITIVE_VALENCE_TERMS = (
    "smile",
    "grin",
    "warm",
    "bright",
    "gentle",
    "kind",
    "soft",
    "easy",
    "contented",
    "touched",
    "shining",
)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def load_profiles() -> Dict[str, Any]:
    data = load_json(PROFILE_FILE)
    return data if isinstance(data, dict) else {}


def categories() -> List[str]:
    profile_categories = load_profiles().get("categories", {})
    if not isinstance(profile_categories, dict):
        return []
    return list(profile_categories.keys())


def category_profile(category: str) -> Dict[str, Any]:
    profile_categories = load_profiles().get("categories", {})
    if not isinstance(profile_categories, dict):
        return {}
    profile = profile_categories.get(str(category or ""))
    return profile if isinstance(profile, dict) else {}


def category_vad(category: str) -> Optional[VAD]:
    profile = category_profile(category)
    vad = profile.get("vad")
    if not isinstance(vad, list) or len(vad) < 2:
        return None
    try:
        return (_clamp(float(vad[0])), _clamp(float(vad[1])))
    except (TypeError, ValueError):
        return None


def alias_category(value: str) -> Optional[str]:
    key = str(value or "").strip().lower().replace(" ", "_")
    if not key:
        return None
    if key in categories():
        return key
    for category in categories():
        aliases = category_profile(category).get("aliases", [])
        if isinstance(aliases, list) and key in {str(alias).lower() for alias in aliases}:
            return category
    return None


def nuance_vad(nuance: str) -> Optional[VAD]:
    key = str(nuance or "").strip().lower()
    profiles = load_profiles().get("nuances", {})
    if not isinstance(profiles, dict):
        return None
    vad = profiles.get(key)
    if not isinstance(vad, list) or len(vad) < 2:
        return None
    try:
        return (_clamp(float(vad[0])), _clamp(float(vad[1])))
    except (TypeError, ValueError):
        return None


def apply_load_bias(vad: Optional[VAD], load: str) -> Optional[VAD]:
    if vad is None:
        return None
    biases = load_profiles().get("load_arousal_bias", {})
    bias = 0.0
    if isinstance(biases, dict):
        try:
            bias = float(biases.get(str(load or ""), 0.0))
        except (TypeError, ValueError):
            bias = 0.0
    return (_clamp(vad[0]), _clamp(vad[1] + bias))


def blend_vad(primary: Optional[VAD], secondary: Optional[VAD], secondary_weight: float = 0.35) -> Optional[VAD]:
    if primary is None:
        return secondary
    if secondary is None:
        return primary
    weight = _clamp(secondary_weight)
    return (
        _clamp((primary[0] * (1.0 - weight)) + (secondary[0] * weight)),
        _clamp((primary[1] * (1.0 - weight)) + (secondary[1] * weight)),
    )


def distance(left: VAD, right: VAD) -> float:
    return math.sqrt((left[0] - right[0]) ** 2 + (left[1] - right[1]) ** 2)


def relevance(left: VAD, right: VAD, gamma: Optional[float] = None) -> float:
    if gamma is None:
        try:
            gamma = float(load_profiles().get("gamma", 2.0))
        except (TypeError, ValueError):
            gamma = 2.0
    return math.exp(-float(gamma) * distance(left, right))


def closest_category(target: VAD, allowed: Iterable[str]) -> Optional[str]:
    scored: List[Tuple[float, str]] = []
    for category in allowed:
        vad = category_vad(category)
        if vad is None:
            continue
        scored.append((distance(vad, target), category))
    if not scored:
        return None
    scored.sort(key=lambda item: (item[0], item[1]))
    return scored[0][1]


def descriptor_vad(category: str, descriptor: str, intensity: str = "medium") -> Optional[VAD]:
    base = category_vad(category)
    if base is None:
        return None
    valence, arousal = base
    text = str(descriptor or "").lower()

    if any(term in text for term in _LOW_AROUSAL_TERMS):
        arousal -= 0.12
    if any(term in text for term in _HIGH_AROUSAL_TERMS):
        arousal += 0.12
    if any(term in text for term in _NEGATIVE_VALENCE_TERMS):
        valence -= 0.08
    if any(term in text for term in _POSITIVE_VALENCE_TERMS):
        valence += 0.08

    if intensity == "mild":
        arousal -= 0.06
    elif intensity == "strong":
        arousal += 0.08

    return (_clamp(valence), _clamp(arousal))


def rank_descriptors(
    category: str,
    descriptors: Sequence[str],
    target: Optional[VAD],
    intensity: str = "medium",
) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []
    for descriptor in descriptors:
        descriptor_text = str(descriptor or "").strip()
        if not descriptor_text:
            continue
        vad = descriptor_vad(category, descriptor_text, intensity)
        if vad is None or target is None:
            score = 0.0
            delta = None
        else:
            delta = distance(vad, target)
            score = relevance(vad, target)
        ranked.append(
            {
                "tag": descriptor_text,
                "vad": list(vad) if vad is not None else None,
                "distance": delta,
                "score": score,
            }
        )
    ranked.sort(key=lambda item: (-(item["score"] or 0.0), item["tag"]))
    return ranked


def validate_profiles(expected_categories: Iterable[str]) -> List[str]:
    errors: List[str] = []
    profile_categories = set(categories())
    expected = {str(category) for category in expected_categories}
    missing = sorted(expected - profile_categories)
    extra = sorted(profile_categories - expected)
    if missing:
        errors.append(f"missing categories: {missing}")
    if extra:
        errors.append(f"extra categories: {extra}")
    for category in sorted(expected & profile_categories):
        vad = category_vad(category)
        if vad is None:
            errors.append(f"{category}: invalid vad")
            continue
        if not (0.0 <= vad[0] <= 1.0 and 0.0 <= vad[1] <= 1.0):
            errors.append(f"{category}: vad out of range {vad}")
    return errors
