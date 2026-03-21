import importlib
import json
import os
import random
from typing import Any

if __package__ and "." in __package__:
    from ..character_service import resolve_character
    from ..core.context_state import generation_state_from_context
    from ..core.context_ops import add_warning, append_history, ensure_context, patch_context
    from ..core.schema import DebugInfo
    from ..location_service import resolve_location_key
    from ..pipeline.action_generator import (
        action_object_flags as generator_action_object_flags,
        action_verb as generator_action_verb,
        can_generate_action_for_location as generator_can_generate_action_for_location,
        choose_action_with_bias_guard as generator_choose_action_with_bias_guard,
        generate_action_for_location,
    )
    from ..vocab.seed_utils import mix_seed
else:
    from character_service import resolve_character
    from core.context_state import generation_state_from_context
    from core.context_ops import add_warning, append_history, ensure_context, patch_context
    from core.schema import DebugInfo
    from location_service import resolve_location_key
    from pipeline.action_generator import (
        action_object_flags as generator_action_object_flags,
        action_verb as generator_action_verb,
        can_generate_action_for_location as generator_can_generate_action_for_location,
        choose_action_with_bias_guard as generator_choose_action_with_bias_guard,
        generate_action_for_location,
    )
    from vocab.seed_utils import mix_seed


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "vocab", "data")

_compat_cache = None
_action_pools_cache = None
_scene_axis_cache = None
_garnish_vocab_module = None


def _load_garnish_vocab_module():
    global _garnish_vocab_module
    if _garnish_vocab_module is not None:
        return _garnish_vocab_module
    if __package__ and "." in __package__:
        from .. import improved_pose_emotion_vocab as vocab_module  # type: ignore
        importlib.reload(vocab_module)
        _garnish_vocab_module = vocab_module
    else:
        import improved_pose_emotion_vocab as vocab_module  # type: ignore
        importlib.reload(vocab_module)
        _garnish_vocab_module = vocab_module
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
    state = generation_state_from_context(ctx)
    resolved = resolve_character(
        raw=ctx.subj,
        source_subj_key=state.character.source_subj_key,
        character_name=state.character.character_name,
    )
    if resolved.get("compatibility_key"):
        return _normalize_compat_subject_key(resolved["compatibility_key"])
    candidates = [state.character.source_subj_key, state.character.character_name, ctx.subj]
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


def _action_verb(text):
    return generator_action_verb(text)


def _action_object_flags(text):
    return generator_action_object_flags(text)


def _recent_scene_decisions(ctx, limit=4):
    decisions = []
    for entry in reversed(ctx.history):
        if entry.node != "ContextSceneVariator":
            continue
        decisions.append(entry.decision or {})
        if len(decisions) >= limit:
            break
    return decisions


def _recent_location_history(ctx, limit=4):
    locations = []
    for decision in _recent_scene_decisions(ctx, limit=limit):
        loc = str(decision.get("selected_loc", "")).strip()
        if loc:
            locations.append(loc)
    return locations


def _recent_action_verb_history(ctx, limit=4):
    verbs = []
    for decision in _recent_scene_decisions(ctx, limit=limit):
        action_text = str(decision.get("new_action", "") or decision.get("action", "")).strip()
        verb = _action_verb(action_text)
        if verb:
            verbs.append(verb)
    return verbs


def _recent_action_object_history(ctx, limit=4):
    objects = set()
    for decision in _recent_scene_decisions(ctx, limit=limit):
        action_text = str(decision.get("new_action", "") or decision.get("action", "")).strip()
        objects.update(_action_object_flags(action_text))
    return objects


def _choose_action_with_bias_guard(pool, rng, loc="", recent_verbs=None, recent_objects=None):
    return generator_choose_action_with_bias_guard(
        pool,
        rng,
        loc,
        recent_verbs=recent_verbs,
        recent_objects=recent_objects,
    )

def can_generate_action_for_location(loc, compat=None):
    compat = compat or _load_compatibility()
    action_pools = _load_action_pools()
    return generator_can_generate_action_for_location(loc, compat=compat, action_pools=action_pools)


def _compose_fallback_action(loc, compat, scene_axes, rng, decision_log, recent_verbs=None, recent_objects=None):
    action_text, generated = generate_action_for_location(
        loc,
        compat,
        scene_axes,
        rng,
        recent_verbs=recent_verbs,
        recent_objects=recent_objects,
    )
    decision_log["action_fallback"] = generated
    decision_log.update(generated)
    return action_text, generated


def apply_scene_variation(context: Any, seed: int, variation_mode: str):
    ctx = ensure_context(context, default_seed=int(seed))
    ctx.seed = int(seed)
    resolved_current_loc = resolve_location_key(ctx.loc) or ctx.loc
    if resolved_current_loc and resolved_current_loc != ctx.loc:
        ctx = patch_context(ctx, updates={"loc": resolved_current_loc})
    decision_log = {
        "mode": variation_mode,
        "candidates_count": 0,
        "selected_source": "original",
        "selected_loc": ctx.loc,
        "action": ctx.action,
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
    recent_locs = _recent_location_history(ctx)
    if recent_locs:
        adjusted_weights = []
        for (source, loc_name), weight in zip(candidates, candidate_weights):
            if loc_name in recent_locs and len(set(loc for _source, loc in candidates)) > 1:
                weight *= 0.25
            adjusted_weights.append(weight)
        candidate_weights = adjusted_weights
        decision_log["recent_loc_penalty"] = recent_locs
    chosen_source, chosen_loc = rng.choices(candidates, weights=candidate_weights, k=1)[0]
    decision_log["selected_source"] = chosen_source
    decision_log["selected_loc"] = chosen_loc

    new_action = ctx.action
    recent_verbs = _recent_action_verb_history(ctx)
    recent_objects = _recent_action_object_history(ctx)
    should_refresh_action = chosen_loc != ctx.loc or (
        variation_mode == "full" and chosen_loc == ctx.loc and rng.random() < 0.55
    )
    generated_mode = ""
    if should_refresh_action:
        pool = [a for a in action_pools.get(chosen_loc, []) if not isinstance(a, str) or not a.startswith("_")]
        if pool:
            new_action, generated = generate_action_for_location(
                chosen_loc,
                compat,
                scene_axes,
                rng,
                pool=pool,
                recent_verbs=recent_verbs,
                recent_objects=recent_objects,
            )
            decision_log.update(generated)
            generated_mode = str(generated.get("generator_mode", ""))
            decision_log["action_updated"] = True
            decision_log["action_refresh_reason"] = "location_changed" if chosen_loc != ctx.loc else "same_location_diversity"
            decision_log["new_action"] = new_action
        else:
            new_action, generated = _compose_fallback_action(
                chosen_loc,
                compat,
                scene_axes,
                rng,
                decision_log,
                recent_verbs=recent_verbs,
                recent_objects=recent_objects,
            )
            generated_mode = str(generated.get("generator_mode", ""))
            decision_log["action_updated"] = True
            decision_log["action_refresh_reason"] = "compositional_fallback"
            decision_log["new_action"] = new_action

    if should_refresh_action and not new_action:
        new_action, generated = _compose_fallback_action(
            chosen_loc,
            compat,
            scene_axes,
            rng,
            decision_log,
            recent_verbs=recent_verbs,
            recent_objects=recent_objects,
        )
        generated_mode = str(generated.get("generator_mode", ""))
        decision_log["new_action"] = new_action

    state = generation_state_from_context(ctx)
    state.location.raw_loc_tag = chosen_loc
    state.location.resolved_location_key = chosen_loc
    ctx = patch_context(
        ctx,
        updates={"loc": chosen_loc, "action": new_action, "seed": seed},
        extras=state.to_extras_patch(),
    )
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
    if include_camera:
        ctx = add_warning(ctx, "include_camera is deprecated and ignored by semantic-only garnish generation")
    vocab_module = _load_garnish_vocab_module()
    if not vocab_module:
        warning = "improved_pose_emotion_vocab.py not found"
        ctx = add_warning(ctx, warning)
        return ctx, "", {"error": warning}

    scene_tags = ctx.meta.tags if isinstance(ctx.meta.tags, dict) else {}
    state = generation_state_from_context(ctx)
    personality_value = personality or state.character.personality
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
            include_camera=False,
            context_loc=ctx.loc,
            context_costume=ctx.costume,
            scene_tags=scene_tags,
            personality=personality_value,
            emotion_nuance=normalized_nuance,
            debug_log=local_debug,
        )
        garnish_text = ", ".join(tags)
        debug_info = DebugInfo(node="ContextGarnish", seed=seed, decision=local_debug)
        state.character.personality = personality_value
        state.fragments.garnish = garnish_text
        ctx = patch_context(ctx, updates={"seed": seed}, extras=state.to_extras_patch())
        ctx = append_history(ctx, debug_info)
        return ctx, garnish_text, debug_info.to_dict()
    except Exception as exc:
        warning = str(exc)
        ctx = add_warning(ctx, warning)
        return ctx, "", {"error": warning}
