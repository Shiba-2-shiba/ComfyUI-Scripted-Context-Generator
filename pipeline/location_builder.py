import random

if __package__ and "." in __package__:
    from ..core.context_state import generation_state_from_context
    from ..core.context_ops import append_history, ensure_context, patch_context
    from ..core.schema import DebugInfo
    from ..core.semantic_policy import filter_candidate_strings, sanitize_text
    from ..core.solo_safety import filter_solo_safe_candidates
    from ..location_service import resolve_location_key
    from ..object_focus_service import background_repeat_risk_flags, extract_object_flags
    from ..history_service import recent_prompt_objects
    from ..vocab.seed_utils import mix_seed
    from .location_semantics import build_scene_target_vector, rank_location_segment_options, semantic_location_debug_payload
    from .location_policy import (
        filter_fx_candidates as _filter_fx_candidates,
        filter_off_mode_options as _filter_off_mode_options,
        is_daily_life_loc as _is_daily_life_loc,
        is_symbolic_prop as _is_symbolic_prop,
        prefer_bright_time_options as _prefer_bright_time_options,
        props_sampling_policy as _props_sampling_policy,
        split_weather_options as _split_weather_options,
    )
    from .location_segment_selector import (
        semantic_choice as _semantic_choice,
        weighted_choice as _weighted_choice,
        weighted_sample as _weighted_sample,
        weighted_sample_with_recent_object_guard as _weighted_sample_with_recent_object_guard,
    )
    from .semantic_epig import add_semantic_debug, domain_enabled, semantic_mode
else:
    from core.context_state import generation_state_from_context
    from core.context_ops import append_history, ensure_context, patch_context
    from core.schema import DebugInfo
    from core.semantic_policy import filter_candidate_strings, sanitize_text
    from core.solo_safety import filter_solo_safe_candidates
    from location_service import resolve_location_key
    from object_focus_service import background_repeat_risk_flags, extract_object_flags
    from history_service import recent_prompt_objects
    from vocab.seed_utils import mix_seed
    from pipeline.location_semantics import build_scene_target_vector, rank_location_segment_options, semantic_location_debug_payload
    from pipeline.location_policy import (
        filter_fx_candidates as _filter_fx_candidates,
        filter_off_mode_options as _filter_off_mode_options,
        is_daily_life_loc as _is_daily_life_loc,
        is_symbolic_prop as _is_symbolic_prop,
        prefer_bright_time_options as _prefer_bright_time_options,
        props_sampling_policy as _props_sampling_policy,
        split_weather_options as _split_weather_options,
    )
    from pipeline.location_segment_selector import (
        semantic_choice as _semantic_choice,
        weighted_choice as _weighted_choice,
        weighted_sample as _weighted_sample,
        weighted_sample_with_recent_object_guard as _weighted_sample_with_recent_object_guard,
    )
    from pipeline.semantic_epig import add_semantic_debug, domain_enabled, semantic_mode

if __package__ and "." in __package__:
    from .. import background_vocab
else:
    import background_vocab

TEXTURE_DEFAULT_BLEND_PROB = 0.25
TEXTURE_SEGMENT_SELECT_PROB = 0.55
FX_DEFAULT_BLEND_PROB = 0.10
FX_SEGMENT_SELECT_PROB = 0.20
MAX_FX_SEGMENTS = 1


def expand_location_prompt(
    loc_tag,
    seed,
    mode,
    lighting_mode="auto",
    recent_objects=None,
    return_debug=False,
    action_text="",
    mood_text="",
):
    try:
        seed = int(seed)
    except Exception:
        seed = 0
    if mode not in ["detailed", "simple"]:
        mode = "detailed"
    if not background_vocab:
        return "[ERR: background_vocab.py not found]"

    rng = random.Random(mix_seed(seed, "loc"))
    raw_tag = str(loc_tag).lower().strip()
    cleaned_tag = resolve_location_key(raw_tag) or raw_tag
    pack_data = background_vocab.CONCEPT_PACKS.get(cleaned_tag)
    if not pack_data:
        debug = {"pack_key": cleaned_tag, "objects": [], "selected_props": [], "template_key": ""}
        return (str(loc_tag), debug) if return_debug else str(loc_tag)

    location_semantic_mode = semantic_mode("location_scene")
    location_target_vector = {}
    location_segment_rankings = {}
    location_section_changes = {}
    if domain_enabled("location_scene"):
        location_target_vector = build_scene_target_vector(
            cleaned_tag,
            action_text=action_text,
            mood_text=mood_text,
        )

    def record_segment_ranking(section_name, options):
        if domain_enabled("location_scene") and options:
            location_segment_rankings[section_name] = rank_location_segment_options(
                section_name,
                [str(option) for option in options if str(option).strip()],
                location_target_vector,
                loc_key=cleaned_tag,
            )

    def semantic_scores_for(section_name):
        if semantic_mode("location_scene") != "active":
            return {}
        return {
            str(item.get("text", "")): float(item.get("score", 0.0) or 0.0)
            for item in location_segment_rankings.get(section_name, [])
        }

    def record_section_change(section_name, baseline, semantic):
        if not domain_enabled("location_scene"):
            return
        ranking = location_segment_rankings.get(section_name, [])
        semantic_text = semantic[0] if isinstance(semantic, list) and semantic else semantic
        selected_rank = None
        for index, item in enumerate(ranking, start=1):
            if str(item.get("text", "")) == str(semantic_text):
                selected_rank = index
                break
        location_section_changes[section_name] = {
            "baseline": baseline,
            "semantic": semantic,
            "changed": semantic_mode("location_scene") == "active" and baseline != semantic,
            "semantic_top_candidate": str(ranking[0].get("text", "")) if ranking else "",
            "selected_candidate_rank": selected_rank,
        }

    env_options = filter_solo_safe_candidates(filter_candidate_strings(pack_data.get("environment", [])))
    record_segment_ranking("environment", env_options)
    if env_options:
        rng_state = rng.getstate()
        baseline_env_part = _weighted_choice(env_options, rng, cleaned_tag, "environment", semantic_scores={})
        rng.setstate(rng_state)
        env_part = _weighted_choice(env_options, rng, cleaned_tag, "environment", semantic_scores=semantic_scores_for("environment"))
        record_section_change("environment", baseline_env_part, env_part)
    else:
        env_part = cleaned_tag
    if mode == "simple":
        prompt = sanitize_text(env_part)
        debug = {"pack_key": cleaned_tag, "objects": sorted(extract_object_flags(prompt)), "selected_props": [], "template_key": "simple"}
        if domain_enabled("location_scene"):
            add_semantic_debug(
                debug,
                "location_scene",
                semantic_location_debug_payload(
                    mode=location_semantic_mode,
                    target_vector=location_target_vector,
                    segment_rankings=location_segment_rankings,
                    section_changes=location_section_changes,
                    selected_by_semantic=location_semantic_mode == "active",
                ),
            )
        return (prompt, debug) if return_debug else prompt

    segments = []
    selected_repeat_risk_objects = set()
    decision = {"pack_key": cleaned_tag, "objects": [], "selected_props": [], "template_key": "detailed"}

    def keep_repeat_risk_budget(options):
        kept = []
        for option in options:
            if background_repeat_risk_flags(option) and selected_repeat_risk_objects:
                continue
            kept.append(option)
        return kept

    def remember_repeat_risk(options):
        for option in options:
            selected_repeat_risk_objects.update(background_repeat_risk_flags(option))

    def enforce_repeat_risk_budget(options):
        accepted = []
        local_repeat_risk_objects = set(selected_repeat_risk_objects)
        for option in options:
            flags = background_repeat_risk_flags(option)
            if flags and local_repeat_risk_objects:
                continue
            accepted.append(option)
            local_repeat_risk_objects.update(flags)
        return accepted

    core_opts = filter_solo_safe_candidates(filter_candidate_strings(pack_data.get("core", [])))
    record_segment_ranking("core", core_opts)
    if core_opts and rng.random() < 0.95:
        num_core = 2 if len(core_opts) > 1 and rng.random() < 0.50 else 1
        rng_state = rng.getstate()
        baseline_core = _weighted_sample(core_opts, rng, min(num_core, len(core_opts)), cleaned_tag, "core", semantic_scores={})
        rng.setstate(rng_state)
        chosen_core = _weighted_sample(core_opts, rng, min(num_core, len(core_opts)), cleaned_tag, "core", semantic_scores=semantic_scores_for("core"))
        chosen_core = enforce_repeat_risk_budget(chosen_core)
        record_section_change("core", baseline_core, chosen_core)
        remember_repeat_risk(chosen_core)
        if len(chosen_core) == 1:
            segments.append(f"featuring {chosen_core[0]}")
        else:
            segments.append(f"featuring {chosen_core[0]} and {chosen_core[1]}")

    props_opts = filter_solo_safe_candidates(filter_candidate_strings(pack_data.get("props", [])))
    props_opts = keep_repeat_risk_budget(props_opts)
    record_segment_ranking("props", props_opts)
    include_prob, second_prop_prob = _props_sampling_policy(props_opts)
    if props_opts and rng.random() < include_prob:
        num_props = 2 if len(props_opts) > 1 and rng.random() < second_prop_prob else 1
        if num_props == 2 and all(_is_symbolic_prop(prop) for prop in props_opts):
            num_props = 1
        rng_state = rng.getstate()
        baseline_props = _weighted_sample_with_recent_object_guard(
            props_opts,
            rng,
            min(num_props, len(props_opts)),
            cleaned_tag,
            "props",
            recent_objects=recent_objects,
            semantic_scores={},
        )
        rng.setstate(rng_state)
        chosen_props = _weighted_sample_with_recent_object_guard(
            props_opts,
            rng,
            min(num_props, len(props_opts)),
            cleaned_tag,
            "props",
            recent_objects=recent_objects,
            semantic_scores=semantic_scores_for("props"),
        )
        record_section_change("props", baseline_props, chosen_props)
        remember_repeat_risk(chosen_props)
        connector_word = rng.choice(["with", "adorned with"])
        if len(chosen_props) == 1:
            segments.append(f"{connector_word} {chosen_props[0]}")
        else:
            segments.append(f"{connector_word} {chosen_props[0]} and {chosen_props[1]}")
        decision["selected_props"] = list(chosen_props)

    texture_candidates = filter_solo_safe_candidates(filter_candidate_strings(pack_data.get("texture", []) or []))
    general_defaults = getattr(background_vocab, "GENERAL_DEFAULTS", {})
    if rng.random() < TEXTURE_DEFAULT_BLEND_PROB:
        texture_candidates.extend(filter_solo_safe_candidates(filter_candidate_strings(general_defaults.get("texture", []))))
    if lighting_mode == "off":
        texture_candidates = _filter_off_mode_options(texture_candidates, fallback_all=False)
    record_segment_ranking("texture", texture_candidates)
    if texture_candidates and rng.random() < TEXTURE_SEGMENT_SELECT_PROB:
        rng_state = rng.getstate()
        baseline_texture = _semantic_choice(texture_candidates, rng, {})
        rng.setstate(rng_state)
        texture = _semantic_choice(texture_candidates, rng, semantic_scores_for("texture"))
        record_section_change("texture", baseline_texture, texture)
        segments.append(texture)

    if rng.random() < 0.35:
        details_defaults = filter_solo_safe_candidates(filter_candidate_strings(general_defaults.get("details", [])))
        if lighting_mode == "off":
            details_defaults = _filter_off_mode_options(details_defaults, fallback_all=False)
        record_segment_ranking("details", details_defaults)
        if details_defaults:
            rng_state = rng.getstate()
            baseline_details = _semantic_choice(details_defaults, rng, {})
            rng.setstate(rng_state)
            details = _semantic_choice(details_defaults, rng, semantic_scores_for("details"))
            record_section_change("details", baseline_details, details)
            segments.append(details)

    is_daily_life = _is_daily_life_loc(cleaned_tag)
    time_opts = filter_solo_safe_candidates(filter_candidate_strings(pack_data.get("time", [])))
    if lighting_mode == "off":
        time_opts = _filter_off_mode_options(time_opts, fallback_all=False)
    record_segment_ranking("time", time_opts)
    if time_opts and rng.random() < (0.72 if is_daily_life else 0.5):
        bright_time_options = _prefer_bright_time_options(time_opts)
        rng_state = rng.getstate()
        baseline_time = _semantic_choice(bright_time_options, rng, {})
        rng.setstate(rng_state)
        time_choice = _semantic_choice(bright_time_options, rng, semantic_scores_for("time"))
        record_section_change("time", baseline_time, time_choice)
        segments.append(f"during {time_choice}")
    weather_opts = filter_solo_safe_candidates(filter_candidate_strings(pack_data.get("weather", [])))
    record_segment_ranking("weather", weather_opts)
    preferred_weather, rare_weather = _split_weather_options(weather_opts)
    weather_probability = 0.18 if is_daily_life else 0.12
    if preferred_weather and rng.random() < weather_probability:
        rng_state = rng.getstate()
        baseline_weather = _semantic_choice(preferred_weather, rng, {})
        rng.setstate(rng_state)
        weather = _semantic_choice(preferred_weather, rng, semantic_scores_for("weather"))
        record_section_change("weather", baseline_weather, weather)
        segments.append(weather)
    elif rare_weather and rng.random() < 0.03:
        rng_state = rng.getstate()
        baseline_weather = _semantic_choice(rare_weather, rng, {})
        rng.setstate(rng_state)
        weather = _semantic_choice(rare_weather, rng, semantic_scores_for("weather"))
        record_section_change("weather", baseline_weather, weather)
        segments.append(weather)
    crowd_opts = filter_solo_safe_candidates(filter_candidate_strings(pack_data.get("crowd", [])))
    record_segment_ranking("crowd", crowd_opts)
    if crowd_opts and rng.random() < (0.58 if is_daily_life else 0.30):
        rng_state = rng.getstate()
        baseline_crowd = _semantic_choice(crowd_opts, rng, {})
        rng.setstate(rng_state)
        crowd = _semantic_choice(crowd_opts, rng, semantic_scores_for("crowd"))
        record_section_change("crowd", baseline_crowd, crowd)
        segments.append(crowd)

    fx_candidates = _filter_fx_candidates(filter_solo_safe_candidates(filter_candidate_strings(pack_data.get("fx", []) or [])))
    if lighting_mode == "off":
        fx_candidates = _filter_off_mode_options(fx_candidates, fallback_all=False)
    if rng.random() < FX_DEFAULT_BLEND_PROB:
        fx_candidates.extend(_filter_fx_candidates(filter_solo_safe_candidates(filter_candidate_strings(general_defaults.get("fx", [])))))
    if lighting_mode == "off":
        fx_candidates = _filter_off_mode_options(fx_candidates, fallback_all=False)
    record_segment_ranking("fx", fx_candidates)
    fx_segments_added = 0
    if fx_candidates and fx_segments_added < MAX_FX_SEGMENTS and rng.random() < FX_SEGMENT_SELECT_PROB:
        rng_state = rng.getstate()
        baseline_fx = _weighted_choice(fx_candidates, rng, cleaned_tag, "fx", semantic_scores={})
        rng.setstate(rng_state)
        fx = _weighted_choice(fx_candidates, rng, cleaned_tag, "fx", semantic_scores=semantic_scores_for("fx"))
        record_section_change("fx", baseline_fx, fx)
        segments.append(fx)
        fx_segments_added += 1

    rng.shuffle(segments)
    deduped_segments = []
    seen_segments = set()
    for segment in segments:
        if segment not in seen_segments:
            deduped_segments.append(segment)
            seen_segments.add(segment)

    prompt = sanitize_text(", ".join([env_part] + deduped_segments) if deduped_segments else env_part)
    decision["objects"] = sorted(extract_object_flags(prompt))
    if domain_enabled("location_scene"):
        add_semantic_debug(
            decision,
            "location_scene",
            semantic_location_debug_payload(
                mode=location_semantic_mode,
                target_vector=location_target_vector,
                segment_rankings=location_segment_rankings,
                section_changes=location_section_changes,
                selected_by_semantic=location_semantic_mode == "active",
            ),
        )
    return (prompt, decision) if return_debug else prompt


def apply_location_expansion(context, seed, mode, lighting_mode="auto"):
    ctx = ensure_context(context, default_seed=int(seed))
    state = generation_state_from_context(ctx)
    raw_loc_tag = state.location.raw_loc_tag or ctx.loc
    loc_tag = resolve_location_key(raw_loc_tag) or raw_loc_tag
    location_prompt, decision = expand_location_prompt(
        loc_tag,
        seed,
        mode,
        lighting_mode,
        recent_objects=recent_prompt_objects(ctx),
        return_debug=True,
        action_text=ctx.action,
        mood_text=ctx.meta.mood,
    )
    state.location.raw_loc_tag = raw_loc_tag
    state.location.resolved_location_key = loc_tag
    state.location.location_prompt = location_prompt
    ctx = patch_context(
        ctx,
        updates={"seed": seed, "loc": loc_tag},
        extras=state.to_extras_patch(),
    )
    ctx = append_history(
        ctx,
        DebugInfo(
            node="ContextLocationExpander",
            seed=seed,
            decision=decision,
        ),
    )
    return ctx, location_prompt
