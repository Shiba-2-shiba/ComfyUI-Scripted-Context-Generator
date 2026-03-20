import importlib
import json
import os
import random
import re
from typing import Any

try:
    from ..core.context_ops import add_warning, append_history, ensure_context, patch_context
    from ..core.schema import DebugInfo
    from ..vocab.seed_utils import mix_seed
except ImportError:
    from core.context_ops import add_warning, append_history, ensure_context, patch_context
    from core.schema import DebugInfo
    from vocab.seed_utils import mix_seed


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "vocab", "data")

_compat_cache = None
_action_pools_cache = None
_scene_axis_cache = None
_object_concentration_policy_cache = None
_garnish_vocab_module = None

_OBJECT_PATTERNS = {
    "surfboard": re.compile(r"\bsurfboard\b|\bboard\b", re.IGNORECASE),
    "book": re.compile(r"\bbook\b|\bbooks\b|\bnotebook\b|\bnovel\b|\btextbook\b", re.IGNORECASE),
    "phone": re.compile(r"\bphone\b|\bsmartphone\b|\bmobile\b", re.IGNORECASE),
    "coffee": re.compile(r"\bcoffee\b|\blatte\b|\bespresso\b|\bcappuccino\b", re.IGNORECASE),
    "drink": re.compile(r"\bdrink\b|\bdrinks\b|\bbeverage\b|\bsipping\b", re.IGNORECASE),
    "microphone": re.compile(r"\bmicrophone\b|\bmic\b", re.IGNORECASE),
    "screen": re.compile(r"\bscreen\b|\bmonitor\b|\bdisplay\b", re.IGNORECASE),
}

_DEFAULT_DAILY_LIFE_TAGS = {"school", "office", "urban", "domestic", "suburban", "resort", "japanese"}
_TAG_BASED_DAILY_LIFE_PROFILES = {
    "school": {
        "purpose": ["study", "wait", "rest"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["before class starts", "during a lunch break", "after school"],
        "weather": ["sunlight reaching the windows", "rain tapping against the glass"],
        "obstacle": ["forgot", "delay"],
    },
    "office": {
        "purpose": ["work", "wait", "commute"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "acquaintance", "stranger"],
        "time": ["before the meeting begins", "during a short break", "near the end of the workday"],
        "weather": ["the city light reflecting through the glass", "rain streaks showing on the windows"],
        "obstacle": ["delay", "forgot", "luggage"],
    },
    "urban": {
        "purpose": ["shop", "wait", "commute", "rest"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "stranger", "crowd", "acquaintance"],
        "time": ["in the late afternoon", "during the evening rush", "on the way home"],
        "weather": ["a cool breeze moving through the street", "light rain lingering in the air"],
        "obstacle": ["delay", "luggage", "spill"],
    },
    "domestic": {
        "purpose": ["rest", "work", "wait"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["in the quiet part of the morning", "late in the evening", "before heading to bed"],
        "weather": ["soft daylight coming through the window", "the room holding onto the rainy weather outside"],
        "obstacle": ["spill", "forgot"],
    },
    "suburban": {
        "purpose": ["commute", "shop", "rest", "wait"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "stranger", "acquaintance"],
        "time": ["before the next errand", "on the way back home", "as the neighborhood quiets down"],
        "weather": ["wind moving past the houses", "the road still damp from rain"],
        "obstacle": ["delay", "luggage", "forgot"],
    },
    "resort": {
        "purpose": ["rest", "wait", "shop"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "acquaintance", "crowd"],
        "time": ["during a slow afternoon", "just before sunset", "after a long walk"],
        "weather": ["warm air drifting through the space", "sea light reflecting nearby"],
        "obstacle": ["luggage", "delay"],
    },
    "japanese": {
        "purpose": ["rest", "wait", "work"],
        "progress": ["preparing", "midway", "wrapping_up"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["in the stillness of the morning", "late in the afternoon", "as the day starts winding down"],
        "weather": ["soft wind moving through the garden", "rain settling over the eaves"],
        "obstacle": ["wind", "forgot"],
    },
}
_LOC_SPECIFIC_DAILY_LIFE_PROFILES = {
    "commuter_transport": {
        "purpose": ["commute", "wait"],
        "social_distance": ["stranger", "crowd", "alone"],
        "time": ["during the morning rush", "between train stops", "on the ride home"],
        "weather": ["the windows fogged from the weather outside", "rainwater shaking loose at each stop"],
        "obstacle": ["delay", "luggage"],
    },
    "street_cafe": {
        "purpose": ["rest", "wait", "shop"],
        "social_distance": ["alone", "acquaintance", "stranger"],
        "time": ["while the afternoon slows down", "before meeting someone", "between errands"],
        "weather": ["a light breeze stirring the parasol", "sunlight shifting across the table"],
        "obstacle": ["spill", "delay"],
    },
    "cozy_bookstore": {
        "purpose": ["shop", "rest", "wait"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["before the shop closes", "during a rainy afternoon", "while the store stays hushed"],
        "weather": ["rain muttering beyond the front window", "dusty sunlight slipping between the shelves"],
    },
    "shopping_mall_atrium": {
        "purpose": ["shop", "wait", "rest"],
        "social_distance": ["crowd", "stranger", "acquaintance"],
        "time": ["during the weekend rush", "between store visits", "after finishing most of the shopping"],
        "weather": ["light from the skylight shifting overhead", "the glass roof holding back the gray sky"],
        "obstacle": ["luggage", "delay"],
    },
    "fashion_boutique": {
        "purpose": ["shop", "wait"],
        "social_distance": ["alone", "acquaintance", "stranger"],
        "time": ["while deciding on one last item", "between trips to the fitting room", "before checking out"],
        "obstacle": ["delay", "luggage"],
    },
    "school_library": {
        "purpose": ["study", "rest", "wait"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["during the last quiet hour", "between classes", "after the rain drives everyone indoors"],
        "weather": ["soft rain dimming the windows", "late daylight stretching over the tables"],
    },
    "office_elevator": {
        "purpose": ["commute", "wait", "work"],
        "social_distance": ["stranger", "acquaintance"],
        "time": ["between floors on a busy morning", "after a long meeting", "on the way back down"],
        "obstacle": ["delay", "forgot", "luggage"],
    },
    "modern_office": {
        "purpose": ["work", "wait", "rest"],
        "social_distance": ["alone", "acquaintance", "crowd"],
        "time": ["before the inbox fills up", "in the middle of the afternoon slump", "after most people have left"],
        "obstacle": ["delay", "forgot"],
    },
    "boardroom": {
        "purpose": ["work", "wait"],
        "social_distance": ["acquaintance", "stranger"],
        "time": ["before the agenda starts", "while the discussion drags on", "as the meeting wraps up"],
        "obstacle": ["delay", "forgot"],
    },
    "bedroom_boudoir": {
        "purpose": ["rest", "wait"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["before getting ready to leave", "after finally coming home", "before sleeping"],
        "weather": ["rain-muted light on the curtains", "soft sunlight at the edge of the room"],
    },
    "messy_kitchen": {
        "purpose": ["work", "rest", "wait"],
        "social_distance": ["alone", "acquaintance"],
        "time": ["while getting breakfast ready", "between chores", "after dinner is over"],
        "obstacle": ["spill", "forgot"],
    },
    "rainy_bus_stop": {
        "purpose": ["wait", "commute"],
        "social_distance": ["alone", "stranger"],
        "time": ["before the next bus arrives", "on the way home after dark", "during a long delay"],
        "weather": ["rain drumming on the shelter roof", "cold wind slipping under the awning"],
        "obstacle": ["delay", "wind"],
    },
    "suburban_neighborhood": {
        "purpose": ["commute", "rest", "shop"],
        "social_distance": ["alone", "acquaintance", "stranger"],
        "time": ["between errands", "on the walk back home", "as the sunset spreads over the houses"],
        "weather": ["wind moving along the hedges", "warm evening light over the street"],
    },
}


def _load_garnish_vocab_module():
    global _garnish_vocab_module
    if _garnish_vocab_module is not None:
        return _garnish_vocab_module
    try:
        from .. import improved_pose_emotion_vocab as vocab_module  # type: ignore
        importlib.reload(vocab_module)
        _garnish_vocab_module = vocab_module
    except ImportError:
        try:
            import improved_pose_emotion_vocab as vocab_module  # type: ignore
            importlib.reload(vocab_module)
            _garnish_vocab_module = vocab_module
        except ImportError:
            _garnish_vocab_module = None
    return _garnish_vocab_module


def _load_compatibility():
    global _compat_cache
    if _compat_cache is None:
        with open(os.path.join(DATA_DIR, "scene_compatibility.json"), "r", encoding="utf-8") as f:
            _compat_cache = json.load(f)
    return _compat_cache


def _load_action_pools():
    global _action_pools_cache
    if _action_pools_cache is None:
        with open(os.path.join(DATA_DIR, "action_pools.json"), "r", encoding="utf-8") as f:
            _action_pools_cache = json.load(f)
    return _action_pools_cache


def _load_scene_axes():
    global _scene_axis_cache
    if _scene_axis_cache is None:
        with open(os.path.join(DATA_DIR, "scene_axis.json"), "r", encoding="utf-8") as f:
            _scene_axis_cache = json.load(f)
    return _scene_axis_cache


def _load_object_concentration_policy():
    global _object_concentration_policy_cache
    if _object_concentration_policy_cache is None:
        path = os.path.join(DATA_DIR, "object_concentration_policy.json")
        if not os.path.exists(path):
            _object_concentration_policy_cache = {}
        else:
            with open(path, "r", encoding="utf-8") as f:
                _object_concentration_policy_cache = json.load(f)
    return _object_concentration_policy_cache


def _build_exclusion_set(compat):
    excluded = set()
    for rule in compat.get("exclusions", []):
        for char in rule["characters"]:
            for loc in rule["denied_locs"]:
                excluded.add((char, loc))
    return excluded


def _get_compatible_locs(subj, compat, excluded, mode="full"):
    char_info = compat.get("characters", {}).get(subj)
    if not char_info:
        return []
    result = []
    seen = set()
    for tag in char_info.get("tags", []):
        for loc in compat.get("loc_tags", {}).get(tag, []):
            if (subj, loc) not in excluded and loc not in seen:
                result.append((loc, f"tag:{tag}"))
                seen.add(loc)
    if mode == "full":
        for loc in compat.get("universal_locs", []):
            if (subj, loc) not in excluded and loc not in seen:
                result.append((loc, "universal"))
                seen.add(loc)
    return result


def _normalize_compat_subject_key(value):
    return str(value or "").strip()


def _resolve_compat_subject_key(ctx, compat):
    characters = compat.get("characters", {})
    normalized_characters = {
        key.casefold(): key
        for key in characters.keys()
    }
    candidates = [
        ctx.extras.get("source_subj_key", ""),
        ctx.extras.get("character_name", ""),
        ctx.subj,
    ]
    for candidate in candidates:
        normalized = _normalize_compat_subject_key(candidate)
        if not normalized:
            continue
        if normalized in characters:
            return normalized
        matched = normalized_characters.get(normalized.casefold())
        if matched:
            return matched
    return _normalize_compat_subject_key(candidates[0] if candidates else "")


def _scene_candidate_family(source):
    source = str(source)
    if source.startswith("tag:"):
        return "tag"
    return source


def _build_scene_candidate_weights(
    candidates,
    existing_weight,
    tag_weight,
    universal_weight,
    daily_life_weight,
    seed,
    compat,
):
    family_totals = {
        "existing": float(existing_weight),
        "tag": float(tag_weight),
        "universal": float(universal_weight),
        "daily_life": float(daily_life_weight),
    }
    grouped = {"existing": [], "tag": [], "universal": [], "daily_life": []}
    for index, (source, loc) in enumerate(candidates):
        family = _scene_candidate_family(source)
        grouped.setdefault(family, []).append((index, source, loc))

    allocated = [0.0] * len(candidates)
    for family, items in grouped.items():
        if not items:
            continue
        base_weights = []
        for _index, _source, loc in items:
            jitter_rng = random.Random(mix_seed(seed, f"scene_candidate:{family}:{loc}"))
            jitter = 0.92 + (jitter_rng.random() * 0.16)
            base_weights.append(jitter)
        base_total = sum(base_weights) or 1.0
        family_total = family_totals.get(family, 1.0)
        for item, base_weight in zip(items, base_weights):
            index = item[0]
            allocated[index] = family_total * (base_weight / base_total)
    return allocated


def _get_daily_life_bonus_locs(compat_subject_key, compat, excluded, existing_locs):
    bonus = []
    seen = set(existing_locs)
    for loc in compat.get("daily_life_locs", []):
        loc_name = str(loc)
        lowered = loc_name.lower()
        if loc_name in seen:
            continue
        if (compat_subject_key, loc_name) in excluded:
            continue
        if "rainy" in lowered or "winter" in lowered:
            continue
        bonus.append((loc_name, "daily_life"))
        seen.add(loc_name)
    return bonus


def _action_text(item):
    if isinstance(item, dict):
        return str(item.get("text", ""))
    return str(item)


def _action_object_flags(text):
    flags = set()
    for key, pat in _OBJECT_PATTERNS.items():
        if pat.search(text):
            flags.add(key)
    return flags


def _get_action_policy_weight(loc, text):
    policy = _load_object_concentration_policy()
    action_policy = policy.get("content_redistribution", {}).get("action", {})
    loc_policy = action_policy.get(str(loc).lower().strip(), {})
    action_weights = loc_policy.get("action_weights", {})
    return max(0.01, float(action_weights.get(str(text), 1.0)))


def _choose_action_with_bias_guard(pool, rng, loc=""):
    if not pool:
        return None, set(), {}
    parsed = []
    object_hits = {k: 0 for k in _OBJECT_PATTERNS.keys()}
    for item in pool:
        text = _action_text(item)
        flags = _action_object_flags(text)
        parsed.append((item, flags))
        for flag in flags:
            object_hits[flag] += 1
    pool_size = len(parsed)
    dominant = {key for key, cnt in object_hits.items() if pool_size > 0 and (cnt / pool_size) >= 0.5}
    weights = []
    for item, flags in parsed:
        text = _action_text(item)
        base_weight = 0.35 if flags & dominant else 1.0
        base_weight *= _get_action_policy_weight(loc, text)
        weights.append(base_weight)
    total = sum(weights)
    if total <= 0:
        return rng.choice(pool), dominant, object_hits
    selected = rng.choices(parsed, weights=weights, k=1)[0][0]
    return selected, dominant, object_hits


def _merge_profile(base_profile, override_profile):
    merged = {}
    for key in set(base_profile.keys()) | set(override_profile.keys()):
        values = []
        for source in (base_profile.get(key, []), override_profile.get(key, [])):
            for item in source:
                if item not in values:
                    values.append(item)
        merged[key] = values
    return merged


def _get_loc_tags(loc, compat):
    tags = []
    for tag, locs in compat.get("loc_tags", {}).items():
        if loc in locs:
            tags.append(tag)
    return tags


def _build_daily_life_profile(loc, compat):
    loc_tags = _get_loc_tags(loc, compat)
    daily_life_tags = set(compat.get("daily_life_tags", [])) or set(_DEFAULT_DAILY_LIFE_TAGS)
    matching_tags = [tag for tag in loc_tags if tag in daily_life_tags]
    profile = {}
    for tag in matching_tags:
        profile = _merge_profile(profile, _TAG_BASED_DAILY_LIFE_PROFILES.get(tag, {}))
    profile = _merge_profile(profile, _LOC_SPECIFIC_DAILY_LIFE_PROFILES.get(loc, {}))
    return profile, matching_tags


def _is_daily_life_loc(loc, compat):
    explicit = set(compat.get("daily_life_locs", []))
    if loc in explicit:
        return True
    profile, matching_tags = _build_daily_life_profile(loc, compat)
    return bool(profile or matching_tags)


def _pick_axis_value(options, rng):
    if not options:
        return ""
    return rng.choice(options)


def _pick_axis_micro_action(scene_axes, axis_name, axis_value, rng):
    axis_info = scene_axes.get(axis_name, {}).get(axis_value, {})
    micro_actions = axis_info.get("micro_actions", [])
    if not micro_actions:
        return ""
    return rng.choice(micro_actions)


def _append_clause(action_text, clause):
    if not clause:
        return action_text
    clean_action = str(action_text).strip().rstrip(".")
    clean_clause = str(clause).strip().rstrip(".")
    if not clean_action:
        return clean_clause
    if clean_clause.lower() in clean_action.lower():
        return clean_action
    return f"{clean_action}, {clean_clause}"


def _enrich_daily_life_action(action_text, loc, compat, scene_axes, rng, decision_log):
    if not _is_daily_life_loc(loc, compat):
        return action_text
    profile, matching_tags = _build_daily_life_profile(loc, compat)
    if not profile:
        return action_text
    selected_axes = {}
    for axis_name in ("purpose", "progress", "social_distance"):
        axis_value = _pick_axis_value(profile.get(axis_name, []), rng)
        if axis_value:
            selected_axes[axis_name] = axis_value
    if profile.get("obstacle") and rng.random() < 0.35:
        selected_axes["obstacle"] = _pick_axis_value(profile.get("obstacle", []), rng)
    action_with_axes = action_text
    axis_details = []
    for axis_name in ("purpose", "progress", "social_distance", "obstacle"):
        axis_value = selected_axes.get(axis_name, "")
        if not axis_value:
            continue
        detail = _pick_axis_micro_action(scene_axes, axis_name, axis_value, rng)
        if detail:
            axis_details.append(detail)
    if axis_details:
        action_with_axes = _append_clause(action_with_axes, rng.choice(axis_details))
    time_clause = _pick_axis_value(profile.get("time", []), rng)
    weather_clause = _pick_axis_value(profile.get("weather", []), rng)
    if time_clause and rng.random() < 0.75:
        action_with_axes = _append_clause(action_with_axes, time_clause)
    elif weather_clause and rng.random() < 0.55:
        action_with_axes = _append_clause(action_with_axes, weather_clause)
    decision_log["scene_axes"] = selected_axes
    if matching_tags:
        decision_log["daily_life_tags"] = matching_tags
    return action_with_axes


def apply_scene_variation(context: Any, seed: int, variation_mode: str):
    ctx = ensure_context(context, default_seed=int(seed))
    ctx.seed = int(seed)
    decision_log = {
        "mode": variation_mode,
        "candidates_count": 0,
        "selected_source": "original",
        "selected_loc": ctx.loc,
    }
    if variation_mode == "original":
        debug_info = DebugInfo(node="ContextSceneVariator", seed=seed, decision=decision_log)
        ctx = append_history(ctx, debug_info)
        return ctx, debug_info

    compat = _load_compatibility()
    action_pools = _load_action_pools()
    scene_axes = _load_scene_axes()
    excluded = _build_exclusion_set(compat)
    rng = random.Random(mix_seed(seed, "scene_var"))

    compat_subject_key = _resolve_compat_subject_key(ctx, compat)
    decision_log["compat_subject_key"] = compat_subject_key
    compatible = _get_compatible_locs(compat_subject_key, compat, excluded, mode=variation_mode)
    decision_log["compatible_unique_count"] = len(compatible)
    if not compatible:
        decision_log["warnings"] = ["No compatible locations found"]
        debug_info = DebugInfo(node="ContextSceneVariator", seed=seed, decision=decision_log)
        ctx = add_warning(ctx, "No compatible locations found")
        ctx = append_history(ctx, debug_info)
        return ctx, debug_info

    weights = compat.get("priority_weights", {})
    existing_weight = float(weights.get("existing", 50))
    tag_weight = float(weights.get("genre_gated", 35))
    universal_weight = float(weights.get("universal", 15))
    daily_life_weight = 0.0
    if variation_mode == "full":
        # Full mode prioritizes scene diversity over keeping the original location.
        existing_weight = max(4.0, existing_weight * 0.22)
        tag_weight = max(tag_weight * 1.05, existing_weight * 3.0)
        universal_weight = max(universal_weight * 3.40, tag_weight * 1.35)
        daily_life_weight = max(universal_weight * 0.90, tag_weight * 1.15)

    candidates = [("existing", ctx.loc)]
    for compat_loc, source in compatible:
        if compat_loc == ctx.loc:
            continue
        candidates.append((source, compat_loc))
    if variation_mode == "full":
        extra_daily_life = _get_daily_life_bonus_locs(
            compat_subject_key,
            compat,
            excluded,
            {loc for _source, loc in candidates},
        )
        for compat_loc, source in extra_daily_life:
            candidates.append((source, compat_loc))
    candidate_weights = _build_scene_candidate_weights(
        candidates,
        existing_weight,
        tag_weight,
        universal_weight,
        daily_life_weight,
        seed,
        compat,
    )

    decision_log["candidates_count"] = len(candidates)
    decision_log["candidates_preview"] = [f"{c[1]} ({c[0]})" for c in candidates]
    decision_log["candidate_source_counts"] = {
        "existing": sum(1 for source, _loc in candidates if _scene_candidate_family(source) == "existing"),
        "tag": sum(1 for source, _loc in candidates if _scene_candidate_family(source) == "tag"),
        "universal": sum(1 for source, _loc in candidates if _scene_candidate_family(source) == "universal"),
        "daily_life": sum(1 for source, _loc in candidates if _scene_candidate_family(source) == "daily_life"),
    }
    decision_log["candidate_weight_profile"] = {
        "existing": existing_weight,
        "tag": tag_weight,
        "universal": universal_weight,
        "daily_life": daily_life_weight,
    }
    chosen_source, chosen_loc = rng.choices(candidates, weights=candidate_weights, k=1)[0]
    decision_log["selected_source"] = chosen_source
    decision_log["selected_loc"] = chosen_loc

    new_action = ctx.action
    should_refresh_action = chosen_loc != ctx.loc or (
        variation_mode == "full" and chosen_loc == ctx.loc and rng.random() < 0.55
    )
    if should_refresh_action:
        pool = [a for a in action_pools.get(chosen_loc, []) if not isinstance(a, str) or not a.startswith("_")]
        if pool:
            new_action_item, dominant_objects, object_hits = _choose_action_with_bias_guard(pool, rng, chosen_loc)
            if isinstance(new_action_item, dict):
                new_action = new_action_item.get("text", "")
                decision_log["action_load"] = new_action_item.get("load")
            else:
                new_action = str(new_action_item)
            decision_log["action_pool_size"] = len(pool)
            if dominant_objects:
                decision_log["action_pool_dominant_objects"] = sorted(dominant_objects)
            decision_log["action_pool_object_hits"] = {k: v for k, v in object_hits.items() if v > 0}
            decision_log["action_updated"] = True
            decision_log["action_refresh_reason"] = "location_changed" if chosen_loc != ctx.loc else "same_location_diversity"
            decision_log["new_action"] = new_action

    enriched_action = _enrich_daily_life_action(new_action, chosen_loc, compat, scene_axes, rng, decision_log)
    if enriched_action != new_action:
        new_action = enriched_action
        decision_log["scene_axis_enriched"] = True
        decision_log["new_action"] = new_action

    ctx = patch_context(ctx, updates={"loc": chosen_loc, "action": new_action, "seed": seed})
    debug_info = DebugInfo(node="ContextSceneVariator", seed=seed, decision=decision_log)
    ctx = append_history(ctx, debug_info)
    return ctx, debug_info


def sample_garnish_fields(
    action_text: str,
    meta_mood_key: str,
    seed: int,
    max_items: int,
    include_camera: bool,
    emotion_nuance: str = "random",
    context_loc: str = "",
    context_costume: str = "",
    scene_tags: Any = "{}",
    personality: str = "",
):
    parsed_tags = {}
    if isinstance(scene_tags, dict):
        parsed_tags = scene_tags
    elif scene_tags:
        try:
            parsed_tags = json.loads(scene_tags)
            if not isinstance(parsed_tags, dict):
                parsed_tags = {}
        except (TypeError, ValueError):
            parsed_tags = {}

    ctx = patch_context(
        {},
        updates={
            "action": action_text,
            "loc": context_loc,
            "costume": context_costume,
            "seed": seed,
        },
        meta={
            "mood": meta_mood_key,
            "tags": parsed_tags,
        },
        extras={
            "personality": personality,
        },
    )
    _updated_ctx, garnish_text, debug_info = apply_garnish(
        ctx,
        int(seed),
        int(max_items),
        bool(include_camera),
        emotion_nuance=emotion_nuance,
        personality=personality,
    )
    return garnish_text, debug_info


def apply_garnish(context: Any, seed: int, max_items: int, include_camera: bool, emotion_nuance: str = "random", personality: str = ""):
    ctx = ensure_context(context, default_seed=int(seed))
    ctx.seed = int(seed)
    vocab_module = _load_garnish_vocab_module()
    if not vocab_module:
        warning = "improved_pose_emotion_vocab.py not found"
        ctx = add_warning(ctx, warning)
        return ctx, "", {"error": warning}

    scene_tags = ctx.meta.tags if isinstance(ctx.meta.tags, dict) else {}
    personality_value = personality or str(ctx.extras.get("personality", ""))
    local_debug = {}
    try:
        normalized_nuance = emotion_nuance
        if not normalized_nuance or str(normalized_nuance).strip().lower() in {"random", "none"}:
            normalized_nuance = ""
        tags = vocab_module.sample_garnish(
            seed=seed,
            meta_mood=ctx.meta.mood,
            action_text=ctx.action,
            max_items=max_items,
            include_camera=include_camera,
            context_loc=ctx.loc,
            context_costume=ctx.costume,
            scene_tags=scene_tags,
            personality=personality_value,
            emotion_nuance=normalized_nuance,
            debug_log=local_debug,
        )
        garnish_text = ", ".join(tags)
        debug_info = DebugInfo(node="ContextGarnish", seed=seed, decision=local_debug)
        ctx = patch_context(ctx, updates={"seed": seed}, extras={"garnish": garnish_text, "personality": personality_value})
        ctx = append_history(ctx, debug_info)
        return ctx, garnish_text, debug_info.to_dict()
    except TypeError:
        try:
            tags = vocab_module.sample_garnish(
                seed=seed,
                meta_mood=ctx.meta.mood,
                action_text=ctx.action,
                max_items=max_items,
            )
            garnish_text = ", ".join(tags)
            ctx = patch_context(ctx, updates={"seed": seed}, extras={"garnish": garnish_text, "personality": personality_value})
            return ctx, garnish_text, {}
        except Exception as exc:
            warning = str(exc)
            ctx = add_warning(ctx, warning)
            return ctx, "", {"error": warning}
    except Exception as exc:
        warning = str(exc)
        ctx = add_warning(ctx, warning)
        return ctx, "", {"error": warning}
