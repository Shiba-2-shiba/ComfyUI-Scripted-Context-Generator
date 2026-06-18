from __future__ import annotations

import random
from typing import Any, Dict, List, Sequence

if __package__ and "." in __package__:
    from ..location_service import resolve_location_key
    from ..object_focus_service import (
        OBJECT_TOKENS,
        action_policy_weight,
        classify_object_hotspot,
        extract_action_object_flags,
        slot_object_policy_weight,
        summarize_slot_object_focus,
    )
    from ..core.solo_safety import filter_solo_action_safe_candidates, filter_solo_safe_candidates, is_solo_action_safe_text, is_solo_safe_text
    from .action_profiles import (
        DEFAULT_DAILY_LIFE_TAGS,
        LOCATION_CONTEXT_HINTS,
        LOC_SPECIFIC_DAILY_LIFE_PROFILES,
        TAG_BASED_DAILY_LIFE_PROFILES,
    )
    from .action_semantics import (
        build_action_target_vector,
        rank_action_slot_options,
        semantic_action_debug_payload,
        semantic_descriptor_options_for_slot,
    )
    from .action_relation_binder import apply_object_relation_slots
    from . import action_parser
    from . import action_renderer
    from .semantic_epig import add_semantic_debug, domain_enabled, semantic_mode
else:
    from location_service import resolve_location_key
    from object_focus_service import (
        OBJECT_TOKENS,
        action_policy_weight,
        classify_object_hotspot,
        extract_action_object_flags,
        slot_object_policy_weight,
        summarize_slot_object_focus,
    )
    from core.solo_safety import filter_solo_action_safe_candidates, filter_solo_safe_candidates, is_solo_action_safe_text, is_solo_safe_text
    from pipeline.action_profiles import (
        DEFAULT_DAILY_LIFE_TAGS,
        LOCATION_CONTEXT_HINTS,
        LOC_SPECIFIC_DAILY_LIFE_PROFILES,
        TAG_BASED_DAILY_LIFE_PROFILES,
    )
    from pipeline.action_semantics import (
        build_action_target_vector,
        rank_action_slot_options,
        semantic_action_debug_payload,
        semantic_descriptor_options_for_slot,
    )
    from pipeline.action_relation_binder import apply_object_relation_slots
    from pipeline import action_parser
    from pipeline import action_renderer
    from pipeline.semantic_epig import add_semantic_debug, domain_enabled, semantic_mode

POSTURE_BY_PURPOSE = {
    "study": ["settled at the edge of her seat", "leaning in over what she is doing", "paused in a still working posture"],
    "work": ["keeping an upright working posture", "leaning in with quiet purpose", "holding herself steady while she works"],
    "commute": ["braced to move at any second", "keeping a balanced stance for the crowd", "holding herself ready to continue on"],
    "rest": ["letting her shoulders loosen", "taking on an easy unhurried posture", "settling into a quieter pace"],
    "shop": ["slowing down just enough to compare things", "hovering in place while she decides", "angling herself toward what she is considering"],
    "wait": ["holding still for the moment", "staying near where she needs to be", "lingering without fully relaxing"],
}
HAND_ACTION_BY_PURPOSE = {
    "study": ["fingers keeping her notes in order", "one hand resting near the page she needs", "hands busy with the material in front of her"],
    "work": ["one hand already reaching for the next task", "fingers gathering what she needs next", "hands staying precise and controlled"],
    "commute": ["one hand keeping hold of what matters", "fingers tightening briefly around her things", "hand shifting to keep her balance"],
    "rest": ["hands loosening at her sides", "fingers easing out of their tension", "one hand resting lightly where it lands"],
    "shop": ["one hand hovering over the next option", "fingers checking the item in front of her", "hand moving between two nearby choices"],
    "wait": ["fingers fidgeting for a second", "one hand keeping her place", "hands settling and then shifting again"],
}
GAZE_BY_PURPOSE = {
    "study": ["eyes following the detail she is working through", "looking over the exact thing that needs her attention"],
    "work": ["eyes fixed on what needs to happen next", "looking between the task and the space around it"],
    "commute": ["checking where the next movement will come from", "keeping an eye on the path ahead"],
    "rest": ["looking off for a quiet second", "letting her gaze drift before returning"],
    "shop": ["looking from one option to another", "checking the next thing that catches her eye"],
    "wait": ["watching for the moment to move", "keeping track of what might change nearby"],
}
PROGRESS_STATE_CLAUSES = {
    "preparing": ["before fully getting started", "as she gets herself ready", "while setting up the next step"],
    "midway": ["already in the middle of it", "while keeping the momentum going", "without losing her place"],
    "wrapping_up": ["near the point where she can move on", "while bringing it to a close", "as the last part falls into place"],
}
OBSTACLE_OR_TRIGGER_CLAUSES = {
    "delay": ["while the delay keeps stretching out", "because the timing still is not right"],
    "spill": ["after a small mess interrupts the rhythm", "while handling a minor spill without fuss"],
    "wind": ["while the moving air keeps getting in the way", "as the wind keeps tugging at the moment"],
    "luggage": ["while the extra things she is carrying slow her down", "because she still has too much to juggle"],
    "forgot": ["after realizing something is missing", "while trying to remember what she almost left behind"],
}
SOCIAL_DISTANCE_CLAUSES = {
    "alone": ["keeping to herself", "lost in her own rhythm"],
    "viewer": [
        "meeting the viewer with a quiet look",
        "as if responding directly to the viewer",
        "leaving room for a quiet exchange with the viewer",
    ],
    "acquaintance": ["leaving room for casual conversation", "half-ready to answer someone nearby"],
    "stranger": ["keeping a polite distance", "avoiding getting in anyone's way"],
    "crowd": ["protecting her space in the crowd", "moving carefully around the people nearby"],
}
SOLO_VIEWER_FACING_SOCIAL_DISTANCES = {"acquaintance", "stranger", "crowd"}
SOLO_SAFE_SOCIAL_DISTANCES = ("alone", "viewer")
OPTIONAL_MICRO_ACTIONS = {
    "study": ["quietly marking her place", "rechecking a small detail", "staying with the line she was following"],
    "work": ["mentally lining up the next task", "pausing to reassess one detail", "moving on only after one more check"],
    "commute": ["counting the moment before she has to move", "adjusting to the movement around her", "keeping pace with the space around her"],
    "rest": ["taking one more easy breath", "letting the pause settle properly", "holding onto the quiet for a second longer"],
    "shop": ["weighing one choice against another", "double-checking what stands out", "lingering over the decision a little longer"],
    "wait": ["measuring the pause instead of rushing it", "checking whether anything has changed yet", "holding onto her place a little longer"],
}

def action_text(item: Any) -> str:
    return action_parser.action_text(item)


def action_verb(text: str) -> str:
    return action_parser.action_verb(text)


def action_object_flags(text: str) -> set[str]:
    return extract_action_object_flags(text)


def _solo_safe_social_distance(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in SOLO_VIEWER_FACING_SOCIAL_DISTANCES:
        return "viewer"
    if normalized in SOLO_SAFE_SOCIAL_DISTANCES and is_solo_safe_text(normalized):
        return normalized
    if normalized and not is_solo_safe_text(normalized):
        return "viewer"
    return normalized


def choose_action_with_bias_guard(pool, rng, loc="", recent_verbs=None, recent_objects=None, solo_safety=True):
    if not pool:
        return None, set(), {}
    if solo_safety:
        pool = [item for item in pool if is_solo_action_safe_text(action_text(item))]
        if not pool:
            return None, set(), {}
    recent_verbs = {str(item).lower() for item in (recent_verbs or []) if item}
    recent_objects = set(recent_objects or [])
    parsed = []
    object_hits = {k: 0 for k in OBJECT_TOKENS}
    for item in pool:
        text = action_text(item)
        flags = action_object_flags(text)
        parsed.append((item, flags))
        for flag in flags:
            object_hits[flag] += 1
    pool_size = len(parsed)
    dominant = {key for key, cnt in object_hits.items() if pool_size > 0 and (cnt / pool_size) >= 0.5}
    weights = []
    for item, flags in parsed:
        text = action_text(item)
        verb = action_verb(text)
        base_weight = 0.35 if flags & dominant else 1.0
        if verb and verb in recent_verbs:
            base_weight *= 0.35
        if flags & recent_objects:
            base_weight *= 0.55
        base_weight *= action_policy_weight(loc, text)
        weights.append(base_weight)
    total = sum(weights)
    if total <= 0:
        return rng.choice(pool), dominant, object_hits
    selected = rng.choices(parsed, weights=weights, k=1)[0][0]
    return selected, dominant, object_hits


def merge_profile(base_profile, override_profile):
    merged = {}
    for key in set(base_profile.keys()) | set(override_profile.keys()):
        values = []
        for source in (base_profile.get(key, []), override_profile.get(key, [])):
            for item in source:
                if item not in values:
                    values.append(item)
        merged[key] = values
    return merged


def get_loc_tags(loc, compat):
    tags = []
    for tag, locs in compat.get("loc_tags", {}).items():
        if loc in locs:
            tags.append(tag)
    return tags


def build_daily_life_profile(loc, compat):
    loc_tags = get_loc_tags(loc, compat)
    daily_life_tags = set(compat.get("daily_life_tags", [])) or set(DEFAULT_DAILY_LIFE_TAGS)
    matching_tags = [tag for tag in loc_tags if tag in daily_life_tags]
    profile = {}
    for tag in matching_tags:
        profile = merge_profile(profile, TAG_BASED_DAILY_LIFE_PROFILES.get(tag, {}))
    profile = merge_profile(profile, LOC_SPECIFIC_DAILY_LIFE_PROFILES.get(loc, {}))
    return profile, matching_tags


def is_daily_life_loc(loc, compat):
    explicit = set(compat.get("daily_life_locs", []))
    if loc in explicit:
        return True
    profile, matching_tags = build_daily_life_profile(loc, compat)
    return bool(profile or matching_tags)


def can_generate_action_for_location(loc, compat=None, action_pools=None):
    compat = compat or {}
    action_pools = action_pools or {}
    loc_key = resolve_location_key(loc) or str(loc or "").strip()
    if action_pools.get(loc_key):
        return True
    profile, matching_tags = build_daily_life_profile(loc_key, compat)
    if profile or matching_tags:
        return True
    return loc_key in set(compat.get("daily_life_locs", [])) or loc_key in set(compat.get("universal_locs", []))


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


def _location_context_profile(loc):
    lowered = str(loc or "").lower()
    for keywords, profile in LOCATION_CONTEXT_HINTS:
        if any(keyword in lowered for keyword in keywords):
            return profile
    return {
        "anchors": ["near the part of the scene she is using", "close to where she needs to be"],
        "gaze_target": ["checking what is happening nearby", "looking toward the next thing she needs"],
    }


def _weighted_slot_choice(
    options: Sequence[str],
    rng,
    loc="",
    recent_verbs=None,
    recent_objects=None,
    selected_objects=None,
    semantic_scores=None,
):
    values = [str(item) for item in options if str(item).strip()]
    if not values:
        return ""
    recent_verbs = {str(item).lower() for item in (recent_verbs or []) if item}
    recent_objects = set(recent_objects or [])
    selected_objects = set(selected_objects or [])
    semantic_scores = semantic_scores or {}
    weights = []
    for value in values:
        weight = 1.0
        verb = action_verb(value)
        objects = action_object_flags(value)
        if verb and verb in recent_verbs:
            weight *= 0.35
        if objects & recent_objects:
            weight *= 0.55
        policy_weight, _policy_objects, _classifications = slot_object_policy_weight(loc, value, selected_objects=selected_objects)
        weight *= policy_weight
        if value in semantic_scores:
            weight *= 0.50 + max(0.0, float(semantic_scores.get(value, 0.0) or 0.0))
        weights.append(weight)
    return rng.choices(values, weights=weights, k=1)[0]


def _normalize_action_phrase(text: str) -> str:
    return action_parser.normalize_action_phrase(text)


def parse_pool_action_to_slots(action_text: str, loc: str = "", compat=None) -> Dict[str, str]:
    def resolve_profile(loc_key: str, compatibility: Dict[str, Any]):
        profile, _matching_tags = build_daily_life_profile(loc_key, compatibility)
        return profile

    return action_parser.parse_pool_action_to_slots(
        action_text,
        loc=loc,
        compat=compat or {},
        daily_life_profile_resolver=resolve_profile,
    )


def _slot_sources(slots: Dict[str, str], slot_overrides: Dict[str, str]) -> Dict[str, str]:
    sources = {}
    for key, value in slots.items():
        if key == "daily_life_tags":
            continue
        if not value:
            continue
        sources[key] = "pool" if slot_overrides.get(key) else "generated"
    return sources


def build_action_slots(
    loc,
    compat,
    scene_axes,
    rng,
    recent_verbs=None,
    recent_objects=None,
    slot_overrides=None,
    semantic_debug=None,
    solo_safety=True,
):
    slot_overrides = {
        str(key): _normalize_action_phrase(value)
        for key, value in (slot_overrides or {}).items()
        if _normalize_action_phrase(value)
    }
    solo_safety_suppressed_obstacle = False
    if solo_safety:
        slot_overrides = {
            key: value
            for key, value in slot_overrides.items()
            if key in {"social_distance", "obstacle_or_trigger"} or is_solo_action_safe_text(value)
        }
        if slot_overrides.get("social_distance"):
            slot_overrides["social_distance"] = _solo_safe_social_distance(slot_overrides.get("social_distance", ""))
        if not is_solo_safe_text(slot_overrides.get("obstacle_or_trigger", "")):
            solo_safety_suppressed_obstacle = "obstacle_or_trigger" in slot_overrides
            slot_overrides["obstacle_or_trigger"] = ""
    loc_key = slot_overrides.get("location") or resolve_location_key(loc) or str(loc or "").strip()
    profile, matching_tags = build_daily_life_profile(loc_key, compat)
    context_profile = _location_context_profile(loc_key)

    def pick_axis(name, fallback):
        return _pick_axis_value(list(profile.get(name, []) or fallback), rng)

    purpose = slot_overrides.get("purpose") or pick_axis("purpose", ["wait", "rest", "shop"])
    progress_state = slot_overrides.get("progress_state") or pick_axis("progress", ["midway", "preparing"])
    social_distance = slot_overrides.get("social_distance") or pick_axis("social_distance", ["alone", "acquaintance"])
    if solo_safety:
        social_distance = _solo_safe_social_distance(social_distance)
    obstacle_or_trigger = slot_overrides.get("obstacle_or_trigger", "")
    if not obstacle_or_trigger and not solo_safety_suppressed_obstacle and profile.get("obstacle") and rng.random() < 0.35:
        obstacle_or_trigger = _pick_axis_value(profile.get("obstacle", []), rng)
    if solo_safety and not is_solo_safe_text(obstacle_or_trigger):
        obstacle_or_trigger = ""

    action_semantic_mode = semantic_mode("action")
    action_target_vector = {}
    action_slot_rankings: Dict[str, List[Dict[str, Any]]] = {}
    action_slot_changes: Dict[str, Dict[str, Any]] = {}
    if domain_enabled("action"):
        semantic_action_text = " ".join(str(value) for value in slot_overrides.values())
        action_target_vector = build_action_target_vector(
            purpose,
            progress_state=progress_state,
            social_distance=social_distance,
            obstacle_or_trigger=obstacle_or_trigger,
            loc=loc_key,
            action_text=semantic_action_text,
        )

    selected_objects = set()
    for key in (
        "posture",
        "hand_action",
        "gaze_target",
        "purpose_clause",
        "progress_clause",
        "social_clause",
        "obstacle_clause",
        "optional_micro_action",
        "time_or_weather",
    ):
        selected_objects.update(action_object_flags(slot_overrides.get(key, "")))

    def choose_slot(name: str, options: Sequence[str]):
        semantic_scores = {}
        baseline_value = ""
        semantic_top_candidate = ""
        selected_candidate_rank = None
        option_values = [str(option) for option in options if str(option).strip()]
        if domain_enabled("action"):
            descriptor_options = semantic_descriptor_options_for_slot(
                name,
                purpose=purpose,
                action_verb=action_verb(" ".join(str(value) for value in slot_overrides.values())),
                object_flags=selected_objects,
            )
            for descriptor_option in descriptor_options[:2]:
                if descriptor_option not in option_values:
                    option_values.append(descriptor_option)
        if solo_safety:
            option_values = filter_solo_action_safe_candidates(option_values)
        if domain_enabled("action") and option_values:
            action_slot_rankings[name] = rank_action_slot_options(
                name,
                option_values,
                action_target_vector,
                loc=loc_key,
            )
            if semantic_mode("action") == "active":
                semantic_scores = {
                    str(item.get("text", "")): float(item.get("score", 0.0) or 0.0)
                    for item in action_slot_rankings[name]
                }
                semantic_top_candidate = str(action_slot_rankings[name][0].get("text", "")) if action_slot_rankings[name] else ""
        if slot_overrides.get(name):
            value = slot_overrides.get(name, "")
            baseline_value = value
        else:
            rng_state = rng.getstate()
            baseline_value = _weighted_slot_choice(
                option_values,
                rng,
                loc=loc_key,
                recent_verbs=recent_verbs,
                recent_objects=recent_objects,
                selected_objects=selected_objects,
                semantic_scores={},
            )
            rng.setstate(rng_state)
            value = _weighted_slot_choice(
                option_values,
                rng,
                loc=loc_key,
                recent_verbs=recent_verbs,
                recent_objects=recent_objects,
                selected_objects=selected_objects,
                semantic_scores=semantic_scores,
            )
        if action_slot_rankings.get(name) and value:
            for index, item in enumerate(action_slot_rankings[name], start=1):
                if str(item.get("text", "")) == value:
                    selected_candidate_rank = index
                    break
            semantic_top_candidate = semantic_top_candidate or str(action_slot_rankings[name][0].get("text", ""))
            action_slot_changes[name] = {
                "baseline": baseline_value,
                "semantic": value,
                "changed": bool(semantic_scores) and baseline_value != value,
                "semantic_top_candidate": semantic_top_candidate,
                "selected_candidate_rank": selected_candidate_rank,
            }
        if value:
            selected_objects.update(action_object_flags(value))
        return value

    slots = {
        "location": loc_key,
        "purpose": purpose,
        "progress_state": progress_state,
        "social_distance": social_distance,
        "obstacle_or_trigger": obstacle_or_trigger,
        "daily_life_tags": list(matching_tags),
        "anchor": choose_slot("anchor", context_profile.get("anchors", [])),
        "posture": choose_slot("posture", POSTURE_BY_PURPOSE.get(purpose, [])),
        "hand_action": choose_slot("hand_action", HAND_ACTION_BY_PURPOSE.get(purpose, [])),
        "gaze_target": choose_slot(
            "gaze_target",
            list(GAZE_BY_PURPOSE.get(purpose, [])) + list(context_profile.get("gaze_target", [])),
        ),
        "purpose_clause": choose_slot(
            "purpose_clause",
            list(OPTIONAL_MICRO_ACTIONS.get(purpose, [])) + [
                _pick_axis_micro_action(scene_axes, "purpose", purpose, rng),
            ],
        ),
        "progress_clause": choose_slot(
            "progress_clause",
            PROGRESS_STATE_CLAUSES.get(progress_state, [""]),
        ),
        "social_clause": choose_slot("social_clause", SOCIAL_DISTANCE_CLAUSES.get(social_distance, [])),
        "obstacle_clause": choose_slot(
            "obstacle_clause",
            [
                OBSTACLE_OR_TRIGGER_CLAUSES.get(obstacle_or_trigger, [""])[0],
                _pick_axis_micro_action(scene_axes, "obstacle", obstacle_or_trigger, rng) if obstacle_or_trigger else "",
            ],
        ),
        "optional_micro_action": choose_slot("optional_micro_action", OPTIONAL_MICRO_ACTIONS.get(purpose, [])),
        "time_or_weather": choose_slot(
            "time_or_weather",
            list(profile.get("time", [])) or list(profile.get("weather", [])),
        ),
    }
    if isinstance(semantic_debug, dict) and domain_enabled("action"):
        semantic_debug["action"] = semantic_action_debug_payload(
            mode=action_semantic_mode,
            target_vector=action_target_vector,
            slot_rankings=action_slot_rankings,
            slot_changes=action_slot_changes,
            selected_by_semantic=action_semantic_mode == "active",
        )
    return slots


def render_action_slots(slots: Dict[str, str], activity_first: bool = False) -> str:
    return action_renderer.render_action_slots(slots, activity_first=activity_first)


def generate_action_for_location(
    loc,
    compat,
    scene_axes,
    rng,
    pool=None,
    recent_verbs=None,
    recent_objects=None,
    solo_safety=True,
):
    loc_key = resolve_location_key(loc) or str(loc or "").strip()
    filtered_pool_count = 0
    if solo_safety and pool:
        original_pool_size = len(pool)
        pool = [item for item in pool if is_solo_action_safe_text(action_text(item))]
        filtered_pool_count = original_pool_size - len(pool)
    if pool:
        new_action_item, dominant_objects, object_hits = choose_action_with_bias_guard(
            pool,
            rng,
            loc_key,
            recent_verbs=recent_verbs,
            recent_objects=recent_objects,
            solo_safety=solo_safety,
        )
        if new_action_item is None:
            pool = None
        else:
            if isinstance(new_action_item, dict):
                base_action_text = str(new_action_item.get("text", ""))
                action_load = new_action_item.get("load")
            else:
                base_action_text = str(new_action_item)
                action_load = ""
    if pool:
        pool_slots = parse_pool_action_to_slots(base_action_text, loc=loc_key, compat=compat)
        semantic_debug = {}
        slots = build_action_slots(
            loc_key,
            compat,
            scene_axes,
            rng,
            recent_verbs=recent_verbs,
            recent_objects=recent_objects,
            slot_overrides=pool_slots,
            semantic_debug=semantic_debug,
            solo_safety=solo_safety,
        )
        relation_debug = apply_object_relation_slots(slots, render_action_slots(slots, activity_first=True)) if domain_enabled("object_relation") else None
        normalized_action = render_action_slots(slots, activity_first=True)
        decision = {
            "generator_mode": "pool",
            "action_pool_size": len(pool),
            "action_pool_dominant_objects": sorted(dominant_objects) if dominant_objects else [],
            "action_pool_object_hits": {k: v for k, v in object_hits.items() if v > 0},
            "solo_safety_filtered_pool_count": filtered_pool_count,
            "base_action": base_action_text,
            "normalized_action": normalized_action,
            "action_load": action_load,
            "pool_slots": pool_slots,
            "slot_sources": _slot_sources(slots, pool_slots),
            "object_focus": summarize_slot_object_focus(
                loc_key,
                slots,
                ("posture", "hand_action", "object_relation", "object_state", "gaze_target", "purpose_clause", "optional_micro_action", "obstacle_clause", "time_or_weather"),
            ),
            "slots": slots,
        }
        if semantic_debug.get("action"):
            add_semantic_debug(decision, "action", semantic_debug["action"])
        if relation_debug is not None:
            add_semantic_debug(decision, "object_relation", relation_debug)
        return normalized_action, decision

    semantic_debug = {}
    slots = build_action_slots(
        loc_key,
        compat,
        scene_axes,
        rng,
        recent_verbs=recent_verbs,
        recent_objects=recent_objects,
        semantic_debug=semantic_debug,
        solo_safety=solo_safety,
    )
    relation_debug = apply_object_relation_slots(slots, render_action_slots(slots)) if domain_enabled("object_relation") else None
    normalized_action = render_action_slots(slots)
    decision = {
        "generator_mode": "compositional",
        "normalized_action": normalized_action,
        "pool_slots": {},
        "slot_sources": _slot_sources(slots, {}),
        "solo_safety_filtered_pool_count": filtered_pool_count,
        "object_focus": summarize_slot_object_focus(
            loc_key,
            slots,
            ("posture", "hand_action", "object_relation", "object_state", "gaze_target", "purpose_clause", "optional_micro_action", "obstacle_clause", "time_or_weather"),
        ),
        "slots": slots,
    }
    if semantic_debug.get("action"):
        add_semantic_debug(decision, "action", semantic_debug["action"])
    if relation_debug is not None:
        add_semantic_debug(decision, "object_relation", relation_debug)
    return normalized_action, decision
