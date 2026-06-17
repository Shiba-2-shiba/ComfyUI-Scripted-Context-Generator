"""Data-driven personality behavior ranking helpers."""

from __future__ import annotations

from typing import Any, Sequence

from .loader import load_json
from .semantic_space import Vector, normalize_vector, rank_candidates

PROFILE_FILE = "personality_behavior_profiles.json"
PERSONALITY_AXES = (
    "sociability",
    "restraint",
    "confidence",
    "curiosity",
    "meticulousness",
    "warmth",
)


def load_personality_profiles() -> dict[str, Any]:
    try:
        payload = load_json(PROFILE_FILE)
    except (FileNotFoundError, OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _profile(personality: str) -> dict[str, Any]:
    payload = load_personality_profiles()
    profiles = payload.get("profiles", {}) if isinstance(payload, dict) else {}
    if not isinstance(profiles, dict):
        return {}
    profile = profiles.get(str(personality or "").strip().lower(), {})
    return profile if isinstance(profile, dict) else {}


def personality_vector(personality: str) -> Vector | None:
    profile = _profile(personality)
    if not profile:
        return None
    return normalize_vector(profile.get("vector", {}), PERSONALITY_AXES)


def prefer_category_for_personality(personality: str) -> str | None:
    category = str(_profile(personality).get("prefer_category", "") or "").strip()
    return category or None


def _descriptor_lookup(slot: str) -> dict[str, dict[str, Any]]:
    payload = load_personality_profiles()
    descriptors = payload.get("descriptors", {}) if isinstance(payload, dict) else {}
    slot_descriptors = descriptors.get(str(slot or ""), []) if isinstance(descriptors, dict) else []
    if not isinstance(slot_descriptors, list):
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for index, descriptor in enumerate(slot_descriptors):
        if not isinstance(descriptor, dict):
            continue
        text = str(descriptor.get("text", "")).strip()
        if not text:
            continue
        item = dict(descriptor)
        item.setdefault("source", f"personality_behavior_profiles:{slot}[{index}]")
        item.setdefault("role", slot)
        lookup[text] = item
    return lookup


def rank_personality_descriptors(personality: str, slot: str, candidates: Sequence[str] | None = None) -> list[dict[str, Any]]:
    target = personality_vector(personality)
    if target is None:
        return []
    lookup = _descriptor_lookup(slot)
    source_candidates = list(candidates or lookup.keys())
    ranked_candidates: list[dict[str, Any]] = []
    for index, candidate in enumerate(source_candidates):
        text = str(candidate or "").strip()
        if not text:
            continue
        descriptor = dict(lookup.get(text, {}))
        descriptor.setdefault("text", text)
        descriptor.setdefault("vector", {})
        descriptor.setdefault("source", f"runtime:{slot}[{index}]")
        descriptor.setdefault("role", slot)
        ranked_candidates.append(descriptor)
    return rank_candidates(ranked_candidates, target, PERSONALITY_AXES)


def ranked_personality_candidate_stream(personality: str) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for slot in ("gaze", "posture", "hands"):
        for slot_rank, item in enumerate(rank_personality_descriptors(personality, slot), start=1):
            candidate = dict(item)
            candidate["role"] = str(candidate.get("role", slot))
            candidate["slot_rank"] = slot_rank
            merged.append(candidate)
    merged.sort(key=lambda item: (-(float(item.get("score", 0.0) or 0.0)), str(item.get("role", "")), str(item.get("text", ""))))
    for index, item in enumerate(merged, start=1):
        item["rank"] = index
    return merged


def pick_personality_descriptor(
    personality: str,
    rng,
    context_loc: str = "",
    context_costume: str = "",
    action_text: str = "",
    existing_tags: list[str] | None = None,
    reject_fn=None,
    debug: dict[str, Any] | None = None,
) -> str:
    del context_loc, context_costume, action_text, existing_tags
    if reject_fn is not None:
        rejected_candidates = []
        for candidate in ranked_personality_candidate_stream(personality):
            text = str(candidate.get("text", "")).strip()
            if not text:
                continue
            reject_reason = reject_fn(text)
            if reject_reason:
                rejected_candidates.append({"text": text, "reason": str(reject_reason), "rank": candidate.get("rank")})
                continue
            if debug is not None:
                debug["selected_candidate_rank"] = candidate.get("rank")
                debug["selected_candidate_role"] = candidate.get("role")
                debug["rejected_candidates"] = rejected_candidates
                debug["candidate_stream"] = ranked_personality_candidate_stream(personality)[:5]
            return text
        if debug is not None:
            debug["selected_candidate_rank"] = None
            debug["rejected_candidates"] = rejected_candidates
            debug["candidate_stream"] = ranked_personality_candidate_stream(personality)[:5]
        return ""

    rankings = {
        slot: rank_personality_descriptors(personality, slot)
        for slot in ("gaze", "posture", "hands")
    }
    if debug is not None:
        debug["slot_rankings"] = rankings
    choices = [ranking[0]["text"] for ranking in rankings.values() if ranking]
    if not choices:
        if debug is not None:
            debug["candidate_options"] = []
            debug["selected_candidate_rank"] = None
        return ""
    selected = rng.choice(choices)
    if debug is not None:
        debug["candidate_options"] = choices
        debug["selected_candidate_rank"] = choices.index(selected) + 1 if selected in choices else None
    return selected


def personality_behavior_debug_payload(
    personality: str,
    *,
    mode: str = "passive",
    selected: str = "",
    selected_by_semantic: bool = False,
    fallback_used: bool = False,
    rejected_candidates: list[dict[str, Any]] | None = None,
    selected_candidate_rank: int | None = None,
) -> dict[str, Any]:
    target = personality_vector(personality)
    slot_rankings = {
        slot: rank_personality_descriptors(personality, slot)
        for slot in ("gaze", "posture", "hands")
    }
    compact_rankings: dict[str, list[dict[str, Any]]] = {}
    for slot, ranking in slot_rankings.items():
        compact_rankings[slot] = [
            {
                "text": str(item.get("text", "")),
                "score": round(float(item.get("score", 0.0) or 0.0), 4),
                "distance": round(float(item.get("distance", 0.0) or 0.0), 4),
                "source": str(item.get("source", "")),
                "role": str(item.get("role", slot)),
            }
            for item in ranking[:5]
        ]
    return {
        "mode": mode,
        "personality": str(personality or "").strip().lower(),
        "target_vector": normalize_vector(target or {}, PERSONALITY_AXES) if target is not None else {},
        "prefer_category": prefer_category_for_personality(personality),
        "slot_rankings": compact_rankings,
        "selected": selected,
        "selected_by_semantic": bool(selected_by_semantic),
        "semantic_scoring_enabled": mode in {"passive", "active"},
        "selection_changed_by_semantic": bool(selected_by_semantic),
        "baseline_candidate": "",
        "semantic_candidate": selected if selected_by_semantic else "",
        "semantic_top_candidate": "",
        "selected_candidate_rank": selected_candidate_rank,
        "fallback_used": bool(fallback_used),
        "rejected_candidates": list(rejected_candidates or []),
    }
