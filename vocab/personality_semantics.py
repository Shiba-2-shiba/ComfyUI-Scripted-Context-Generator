"""Data-driven personality behavior ranking helpers."""

from __future__ import annotations

from typing import Any, Sequence

from .loader import load_json
from .semantic_space import Vector, normalize_vector, rank_candidates

PROFILE_FILE = "personality_behavior_profiles.json"
SUBJECT_CENTRIC_DESCRIPTOR_FILE = "subject_centric_descriptor_overrides.json"
SEMANTIC_CONFIG_FILE = "semantic_epig_config.json"
VALID_SUBJECT_CENTRIC_MODES = {"off", "passive", "active"}
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


def load_subject_centric_descriptor_overrides() -> dict[str, Any]:
    try:
        payload = load_json(SUBJECT_CENTRIC_DESCRIPTOR_FILE)
    except (FileNotFoundError, OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_semantic_config() -> dict[str, Any]:
    try:
        payload = load_json(SEMANTIC_CONFIG_FILE)
    except (FileNotFoundError, OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _subject_centric_override_config() -> dict[str, Any]:
    config = _load_semantic_config()
    domains = config.get("domains", {}) if isinstance(config, dict) else {}
    personality_config = domains.get("personality_behavior", {}) if isinstance(domains, dict) else {}
    override_config = personality_config.get("subject_centric_overrides", {}) if isinstance(personality_config, dict) else {}
    return override_config if isinstance(override_config, dict) else {}


def subject_centric_override_mode() -> str:
    mode = str(_subject_centric_override_config().get("mode", "off") or "off").strip().lower()
    return mode if mode in VALID_SUBJECT_CENTRIC_MODES else "off"


def subject_centric_override_max_candidates_per_slot() -> int:
    value = _subject_centric_override_config().get("max_candidates_per_slot", 1)
    if not isinstance(value, int):
        return 1
    return max(0, value)


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


def subject_centric_descriptor_options(
    personality: str = "",
    slot: str = "",
    *,
    modes: set[str] | None = None,
    mood_key: str = "",
) -> list[dict[str, Any]]:
    """Return repo-authored subject-centric override candidates.

    These candidates are intentionally loaded separately from the reference
    overlay so runtime code never depends on raw EPIG/NRC source rows or
    score-bearing generated files.
    """

    if modes is None:
        mode = subject_centric_override_mode()
        if mode == "off":
            return []
        modes = {mode}
    payload = load_subject_centric_descriptor_overrides()
    descriptors = payload.get("descriptors", []) if isinstance(payload, dict) else []
    if not isinstance(descriptors, list):
        return []
    personality_key = str(personality or "").strip().lower()
    slot_key = str(slot or "").strip().lower()
    mood_key = str(mood_key or "").strip().lower().replace(" ", "_")
    allowed_modes = {str(mode).strip().lower() for mode in modes}
    options: list[dict[str, Any]] = []
    max_per_slot = subject_centric_override_max_candidates_per_slot()
    slot_counts: dict[str, int] = {}
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            continue
        text = str(descriptor.get("text", "")).strip()
        descriptor_slot = str(descriptor.get("slot", "")).strip().lower()
        descriptor_mode = str(descriptor.get("mode", "")).strip().lower()
        if not text or descriptor_mode not in allowed_modes:
            continue
        if slot_key and descriptor_slot != slot_key:
            continue
        if max_per_slot == 0:
            continue
        if slot_counts.get(descriptor_slot, 0) >= max_per_slot:
            continue
        personalities = descriptor.get("personality", [])
        if personality_key and isinstance(personalities, list) and personalities:
            normalized_personalities = {str(item).strip().lower() for item in personalities if str(item).strip()}
            if personality_key not in normalized_personalities:
                continue
        mood_keys = descriptor.get("mood_keys", [])
        if mood_key and isinstance(mood_keys, list) and mood_keys:
            normalized_mood_keys = {str(item).strip().lower().replace(" ", "_") for item in mood_keys if str(item).strip()}
            if mood_key not in normalized_mood_keys:
                continue
        options.append(
            {
                "id": str(descriptor.get("id", "")).strip(),
                "slot": descriptor_slot,
                "text": text,
                "mode": descriptor_mode,
                "source": SUBJECT_CENTRIC_DESCRIPTOR_FILE,
                "source_hint": list(descriptor.get("source_hint", []) or []),
                "mood_keys": list(descriptor.get("mood_keys", []) or []),
                "reject_context_terms": list(descriptor.get("reject_context_terms", []) or []),
                "debug_tags": list(descriptor.get("debug_tags", []) or []),
            }
        )
        slot_counts[descriptor_slot] = slot_counts.get(descriptor_slot, 0) + 1
    return options


def subject_centric_descriptor_debug_payload(personality: str = "", mood_key: str = "") -> dict[str, Any]:
    options = subject_centric_descriptor_options(personality, mood_key=mood_key)
    by_slot: dict[str, int] = {}
    mode_counts: dict[str, int] = {}
    for option in options:
        slot = str(option.get("slot", ""))
        mode = str(option.get("mode", ""))
        by_slot[slot] = by_slot.get(slot, 0) + 1
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
    mode = subject_centric_override_mode()
    return {
        "source": SUBJECT_CENTRIC_DESCRIPTOR_FILE,
        "adoption_state": "active_candidate_selection" if mode == "active" else "passive_debug_only",
        "mode": mode,
        "max_candidates_per_slot": subject_centric_override_max_candidates_per_slot(),
        "available_count": len(options),
        "by_slot": dict(sorted(by_slot.items())),
        "mode_counts": dict(sorted(mode_counts.items())),
        "candidates": [
            {
                "id": option.get("id", ""),
                "slot": option.get("slot", ""),
                "text": option.get("text", ""),
                "mode": option.get("mode", ""),
                "debug_tags": option.get("debug_tags", []),
            }
            for option in options[:8]
        ],
    }


def pick_subject_centric_override_descriptor(
    personality: str,
    *,
    slot_order: Sequence[str] = ("gaze", "expression", "posture", "hands"),
    mood_key: str = "",
    context_terms: Sequence[str] | None = None,
    reject_fn=None,
    debug: dict[str, Any] | None = None,
) -> str:
    if subject_centric_override_mode() != "active":
        if debug is not None:
            debug["subject_centric_override_active"] = False
        return ""
    rejected: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for slot in slot_order:
        candidates.extend(subject_centric_descriptor_options(personality, slot, modes={"active"}, mood_key=mood_key))
    if str(mood_key or "").strip():
        candidates.sort(
            key=lambda candidate: (
                not bool(candidate.get("mood_keys")),
                slot_order.index(str(candidate.get("slot", "")))
                if str(candidate.get("slot", "")) in slot_order
                else len(slot_order),
            )
        )
    context_text = " ".join(str(item or "").lower() for item in context_terms or [] if str(item or "").strip())
    for candidate in candidates:
        text = str(candidate.get("text", "")).strip()
        if not text:
            continue
        reject_terms = [
            str(term).strip().lower()
            for term in candidate.get("reject_context_terms", [])
            if str(term).strip()
        ]
        matched_reject_term = next((term for term in reject_terms if term in context_text), "")
        if matched_reject_term:
            rejected.append(
                {
                    "text": text,
                    "reason": f"reject_context_term:{matched_reject_term}",
                    "id": candidate.get("id", ""),
                }
            )
            continue
        reject_reason = reject_fn(text) if reject_fn is not None else ""
        if reject_reason:
            rejected.append({"text": text, "reason": str(reject_reason), "id": candidate.get("id", "")})
            continue
        if debug is not None:
            debug["subject_centric_override_active"] = True
            debug["subject_centric_override_selected"] = {
                "id": candidate.get("id", ""),
                "slot": candidate.get("slot", ""),
                "text": text,
            }
            debug["subject_centric_override_rejected"] = rejected
        return text
    if debug is not None:
        debug["subject_centric_override_active"] = True
        debug["subject_centric_override_selected"] = {}
        debug["subject_centric_override_rejected"] = rejected
    return ""


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
    mood_key: str = "",
    reject_fn=None,
    debug: dict[str, Any] | None = None,
) -> str:
    if reject_fn is not None:
        rejected_candidates = []
        override_candidate = pick_subject_centric_override_descriptor(
            personality,
            mood_key=mood_key,
            context_terms=[context_loc, context_costume, action_text, *(existing_tags or [])],
            reject_fn=reject_fn,
            debug=debug,
        )
        if override_candidate:
            if debug is not None:
                debug["selected_candidate_rank"] = 0
                debug["selected_candidate_role"] = "subject_centric_override"
                debug["rejected_candidates"] = []
                debug["candidate_stream"] = ranked_personality_candidate_stream(personality)[:5]
            return override_candidate
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
    mood_key: str = "",
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
        "subject_centric_overrides": subject_centric_descriptor_debug_payload(personality, mood_key=mood_key),
    }
