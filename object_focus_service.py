from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Any, Dict, Iterable, Sequence


ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "vocab", "data")

_SHARED_OBJECT_PATTERNS = {
    "book": re.compile(r"\bbook\b|\bbooks\b|\bnotebook\b|\btextbook\b", re.IGNORECASE),
    "phone": re.compile(r"\bphone\b|\bsmartphone\b|\bmobile\b", re.IGNORECASE),
    "coffee": re.compile(r"\bcoffee\b|\blatte\b|\bespresso\b|\bcappuccino\b|\bcup\b", re.IGNORECASE),
    "drink": re.compile(r"\bdrink\b|\bbeverage\b|\btea bowl\b|\btea\b", re.IGNORECASE),
    "screen": re.compile(r"\bscreen\b|\bmonitor\b|\bdisplay\b", re.IGNORECASE),
}
ACTION_OBJECT_PATTERNS = {
    "surfboard": re.compile(r"\bsurfboard\b|\bboard\b", re.IGNORECASE),
    "book": re.compile(r"\bbook\b|\bbooks\b|\bnotebook\b|\bnovel\b|\btextbook\b", re.IGNORECASE),
    "phone": re.compile(r"\bphone\b|\bsmartphone\b|\bmobile\b", re.IGNORECASE),
    "coffee": re.compile(r"\bcoffee\b|\blatte\b|\bespresso\b|\bcappuccino\b", re.IGNORECASE),
    "drink": re.compile(r"\bdrink\b|\bdrinks\b|\bbeverage\b|\bsipping\b", re.IGNORECASE),
    "microphone": re.compile(r"\bmicrophone\b|\bmic\b", re.IGNORECASE),
    "screen": re.compile(r"\bscreen\b|\bmonitor\b|\bdisplay\b", re.IGNORECASE),
}
OBJECT_TOKENS = tuple(ACTION_OBJECT_PATTERNS.keys())
_SYMBOLIC_OBJECT_HINTS = (
    "surfboard", " board", "book", "phone", "coffee", "drink", "microphone", "screen",
)


@lru_cache(maxsize=1)
def load_object_concentration_policy() -> Dict[str, Any]:
    path = os.path.join(DATA_DIR, "object_concentration_policy.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def extract_object_flags(text: str) -> set[str]:
    flags = set()
    source = str(text or "")
    for key, pattern in _SHARED_OBJECT_PATTERNS.items():
        if pattern.search(source):
            flags.add(key)
    return flags


def extract_action_object_flags(text: str) -> set[str]:
    flags = set()
    source = str(text or "")
    for key, pattern in ACTION_OBJECT_PATTERNS.items():
        if pattern.search(source):
            flags.add(key)
    return flags


def is_symbolic_object_text(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(token in lowered for token in _SYMBOLIC_OBJECT_HINTS)


def background_object_policy(loc_tag: str) -> Dict[str, Any]:
    policy = load_object_concentration_policy()
    background_policy = policy.get("content_redistribution", {}).get("background", {})
    return background_policy.get(str(loc_tag).lower().strip(), {})


def background_weight_map(loc_tag: str, section_name: str) -> Dict[str, float]:
    return background_object_policy(loc_tag).get(f"{section_name}_weights", {})


def action_policy_weight(loc: str, text: str) -> float:
    policy = load_object_concentration_policy()
    action_policy = policy.get("content_redistribution", {}).get("action", {})
    loc_policy = action_policy.get(str(loc).lower().strip(), {})
    action_weights = loc_policy.get("action_weights", {})
    return max(0.01, float(action_weights.get(str(text), 1.0)))


def classify_object_hotspot(loc: str, object_token: str) -> str:
    policy = load_object_concentration_policy()
    loc_key = str(loc or "").strip()
    token = str(object_token or "").strip()
    if token in policy.get("audit_artifact", {}).get(loc_key, []):
        return "audit_artifact"
    if token in policy.get("true_bias_background", {}).get(loc_key, []):
        return "true_bias_background"
    if token in policy.get("true_bias_action", {}).get(loc_key, []):
        return "true_bias_action"
    if token in policy.get("thematic_anchor", {}).get(loc_key, {}):
        return "thematic_anchor"
    return "general"


def slot_object_policy_weight(loc: str, text: str, selected_objects: Iterable[str] | None = None):
    selected_objects = set(selected_objects or [])
    objects = extract_action_object_flags(text)
    if not objects:
        return 1.0, objects, {}

    weight = 1.0
    classifications = {}
    for object_token in objects:
        classification = classify_object_hotspot(loc, object_token)
        classifications[object_token] = classification
        if classification in {"audit_artifact", "true_bias_action"}:
            weight *= 0.18
        elif classification == "thematic_anchor":
            weight *= 1.10
        if object_token in selected_objects:
            weight *= 0.35
    return max(0.01, weight), objects, classifications


def summarize_slot_object_focus(loc: str, slots: Dict[str, str], slot_keys: Sequence[str]) -> Dict[str, Any]:
    slot_map: Dict[str, list[str]] = {}
    classifications: Dict[str, str] = {}
    for key in slot_keys:
        value = str(slots.get(key, "")).strip()
        if not value:
            continue
        objects = sorted(extract_action_object_flags(value))
        if not objects:
            continue
        slot_map[key] = objects
        for object_token in objects:
            classifications.setdefault(object_token, classify_object_hotspot(loc, object_token))
    return {
        "detected_objects": sorted(classifications.keys()),
        "slot_map": slot_map,
        "classifications": classifications,
    }
