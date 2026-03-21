import random
import re

try:
    from ..core.context_state import generation_state_from_context
    from ..core.context_ops import append_history, ensure_context, patch_context
    from ..core.schema import DebugInfo
    from ..core.semantic_policy import filter_candidate_strings, sanitize_text
    from ..location_service import resolve_location_key
    from ..object_focus_service import background_weight_map, extract_object_flags, is_symbolic_object_text
    from ..history_service import recent_prompt_objects
    from ..vocab.seed_utils import mix_seed
except ImportError:
    from core.context_state import generation_state_from_context
    from core.context_ops import append_history, ensure_context, patch_context
    from core.schema import DebugInfo
    from core.semantic_policy import filter_candidate_strings, sanitize_text
    from location_service import resolve_location_key
    from object_focus_service import background_weight_map, extract_object_flags, is_symbolic_object_text
    from history_service import recent_prompt_objects
    from vocab.seed_utils import mix_seed

try:
    from .. import background_vocab
except ImportError:
    try:
        import background_vocab
    except ImportError:
        background_vocab = None

DAILY_LIFE_LOCS = {
    "school_classroom", "school_rooftop", "school_library", "modern_office",
    "boardroom", "office_elevator", "commuter_transport", "street_cafe",
    "cozy_bookstore", "shopping_mall_atrium", "fashion_boutique",
    "bedroom_boudoir", "messy_kitchen", "clean_modern_kitchen",
    "cozy_living_room", "rainy_bus_stop", "suburban_neighborhood",
    "rural_town_street", "picnic_park", "illuminated_park", "winter_street",
    "japanese_garden", "tea_room",
}
TEXTURE_DEFAULT_BLEND_PROB = 0.25
TEXTURE_SEGMENT_SELECT_PROB = 0.55
FX_DEFAULT_BLEND_PROB = 0.10
FX_SEGMENT_SELECT_PROB = 0.20
MAX_FX_SEGMENTS = 1
FX_DENY_PATTERNS = (
    re.compile(r"\bconfetti\b", re.IGNORECASE),
    re.compile(r"\bfloating dust particles?\b", re.IGNORECASE),
    re.compile(r"\bsparkling air\b", re.IGNORECASE),
    re.compile(r"\bsparkles?\b", re.IGNORECASE),
    re.compile(r"\bglittering air\b", re.IGNORECASE),
    re.compile(r"\bbokeh\b", re.IGNORECASE),
    re.compile(r"\blens flares?\b", re.IGNORECASE),
    re.compile(r"\bdust motes?\b", re.IGNORECASE),
    re.compile(r"\bdust particles?\b", re.IGNORECASE),
    re.compile(r"\bfloating dust\b", re.IGNORECASE),
    re.compile(r"\bsparkling(?!\s+eyes\b)\w*\b", re.IGNORECASE),
)
_TIME_DARK_HINTS = ("night", "midnight", "twilight", "dusk", "late night", "stormy", "holiday night")
_WEATHER_RARE_HINTS = ("rain", "snow", "storm", "fog", "acid", "winter")
_LIGHTING_HINTS = ("light", "glow", "fluorescent", "ambient", "sun", "spotlight", "daylight", "hour")

def _is_symbolic_prop(text):
    return is_symbolic_object_text(text)


def _props_sampling_policy(props_opts):
    include_prob = 0.8
    second_prop_prob = 0.45
    if len(props_opts) <= 3:
        include_prob = 0.62
        second_prop_prob = 0.20
    if any(_is_symbolic_prop(prop) for prop in props_opts):
        include_prob = max(0.50, include_prob - 0.12)
        second_prop_prob = max(0.10, second_prop_prob - 0.10)
    return include_prob, second_prop_prob


def _is_disallowed_fx_segment(text):
    low = str(text).lower()
    if "snowflake" in low or "sparkling eyes" in low:
        return False
    return any(pattern.search(low) for pattern in FX_DENY_PATTERNS)


def _filter_fx_candidates(options):
    if not options:
        return []
    filtered = []
    seen = set()
    for item in options:
        if not item:
            continue
        item_text = str(item)
        if _is_disallowed_fx_segment(item_text):
            continue
        if item_text in seen:
            continue
        filtered.append(item_text)
        seen.add(item_text)
    return filtered


def _weighted_choice(options, rng, loc_tag, section_name):
    if not options:
        return ""
    weights_map = background_weight_map(loc_tag, section_name)
    weights = [max(0.01, float(weights_map.get(str(option), 1.0))) for option in options]
    return rng.choices(list(options), weights=weights, k=1)[0]


def _weighted_sample(options, rng, k, loc_tag, section_name):
    available = list(options)
    selected = []
    while available and len(selected) < k:
        weights_map = background_weight_map(loc_tag, section_name)
        weights = [max(0.01, float(weights_map.get(str(option), 1.0))) for option in available]
        chosen = rng.choices(available, weights=weights, k=1)[0]
        selected.append(chosen)
        available.remove(chosen)
    return selected


def _weighted_sample_with_recent_object_guard(options, rng, k, loc_tag, section_name, recent_objects=None):
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
            weights.append(base_weight)
        chosen = rng.choices(available, weights=weights, k=1)[0]
        selected.append(chosen)
        available.remove(chosen)
    return selected


def _is_daily_life_loc(loc_tag):
    return str(loc_tag).lower().strip() in DAILY_LIFE_LOCS


def _prefer_bright_time_options(options):
    if not options:
        return []
    preferred = [
        option for option in options
        if not any(token in str(option).lower() for token in _TIME_DARK_HINTS)
    ]
    return preferred or list(options)


def _split_weather_options(options):
    if not options:
        return [], []
    normal = []
    rare = []
    for option in options:
        option_text = str(option).lower()
        if any(token in option_text for token in _WEATHER_RARE_HINTS):
            rare.append(option)
        else:
            normal.append(option)
    return normal, rare


def _contains_lighting_hint(text):
    lowered = str(text).lower()
    return any(token in lowered for token in _LIGHTING_HINTS)


def _filter_off_mode_options(options, fallback_all=True):
    if not options:
        return []
    filtered = [option for option in options if not _contains_lighting_hint(option)]
    if filtered:
        return filtered
    return list(options) if fallback_all else []


def expand_location_prompt(loc_tag, seed, mode, lighting_mode="auto", recent_objects=None, return_debug=False):
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

    env_options = filter_candidate_strings(pack_data.get("environment", []))
    env_part = _weighted_choice(env_options, rng, cleaned_tag, "environment") if env_options else cleaned_tag
    if mode == "simple":
        prompt = sanitize_text(env_part)
        debug = {"pack_key": cleaned_tag, "objects": sorted(extract_object_flags(prompt)), "selected_props": [], "template_key": "simple"}
        return (prompt, debug) if return_debug else prompt

    segments = []
    decision = {"pack_key": cleaned_tag, "objects": [], "selected_props": [], "template_key": "detailed"}
    core_opts = filter_candidate_strings(pack_data.get("core", []))
    if core_opts and rng.random() < 0.95:
        num_core = 2 if len(core_opts) > 1 and rng.random() < 0.50 else 1
        chosen_core = _weighted_sample(core_opts, rng, min(num_core, len(core_opts)), cleaned_tag, "core")
        if len(chosen_core) == 1:
            segments.append(f"featuring {chosen_core[0]}")
        else:
            connector = rng.choice(["and", "plus", "featuring"])
            segments.append(f"featuring {chosen_core[0]} {connector} {chosen_core[1]}")

    props_opts = filter_candidate_strings(pack_data.get("props", []))
    include_prob, second_prop_prob = _props_sampling_policy(props_opts)
    if props_opts and rng.random() < include_prob:
        num_props = 2 if len(props_opts) > 1 and rng.random() < second_prop_prob else 1
        if num_props == 2 and all(_is_symbolic_prop(prop) for prop in props_opts):
            num_props = 1
        chosen_props = _weighted_sample_with_recent_object_guard(
            props_opts,
            rng,
            min(num_props, len(props_opts)),
            cleaned_tag,
            "props",
            recent_objects=recent_objects,
        )
        connector_word = rng.choice(["with", "scattered with", "filled with", "adorned with"])
        if len(chosen_props) == 1:
            segments.append(f"{connector_word} {chosen_props[0]}")
        else:
            joiner = rng.choice(["and", "plus", "as well as"])
            segments.append(f"{connector_word} {chosen_props[0]} {joiner} {chosen_props[1]}")
        decision["selected_props"] = list(chosen_props)

    texture_candidates = list(filter_candidate_strings(pack_data.get("texture", []) or []))
    general_defaults = getattr(background_vocab, "GENERAL_DEFAULTS", {})
    if rng.random() < TEXTURE_DEFAULT_BLEND_PROB:
        texture_candidates.extend(filter_candidate_strings(general_defaults.get("texture", [])))
    if lighting_mode == "off":
        texture_candidates = _filter_off_mode_options(texture_candidates, fallback_all=False)
    if texture_candidates and rng.random() < TEXTURE_SEGMENT_SELECT_PROB:
        segments.append(rng.choice(texture_candidates))

    if rng.random() < 0.35:
        details_defaults = filter_candidate_strings(general_defaults.get("details", []))
        if lighting_mode == "off":
            details_defaults = _filter_off_mode_options(details_defaults, fallback_all=False)
        if details_defaults:
            segments.append(rng.choice(details_defaults))

    is_daily_life = _is_daily_life_loc(cleaned_tag)
    time_opts = filter_candidate_strings(pack_data.get("time", []))
    if lighting_mode == "off":
        time_opts = _filter_off_mode_options(time_opts, fallback_all=False)
    if time_opts and rng.random() < (0.72 if is_daily_life else 0.5):
        segments.append(f"during {rng.choice(_prefer_bright_time_options(time_opts))}")
    weather_opts = filter_candidate_strings(pack_data.get("weather", []))
    preferred_weather, rare_weather = _split_weather_options(weather_opts)
    weather_probability = 0.18 if is_daily_life else 0.12
    if preferred_weather and rng.random() < weather_probability:
        segments.append(rng.choice(preferred_weather))
    elif rare_weather and rng.random() < 0.03:
        segments.append(rng.choice(rare_weather))
    crowd_opts = filter_candidate_strings(pack_data.get("crowd", []))
    if crowd_opts and rng.random() < (0.58 if is_daily_life else 0.30):
        segments.append(rng.choice(crowd_opts))

    fx_candidates = _filter_fx_candidates(filter_candidate_strings(pack_data.get("fx", []) or []))
    if lighting_mode == "off":
        fx_candidates = _filter_off_mode_options(fx_candidates, fallback_all=False)
    if rng.random() < FX_DEFAULT_BLEND_PROB:
        fx_candidates.extend(_filter_fx_candidates(filter_candidate_strings(general_defaults.get("fx", []))))
    if lighting_mode == "off":
        fx_candidates = _filter_off_mode_options(fx_candidates, fallback_all=False)
    fx_segments_added = 0
    if fx_candidates and fx_segments_added < MAX_FX_SEGMENTS and rng.random() < FX_SEGMENT_SELECT_PROB:
        segments.append(_weighted_choice(fx_candidates, rng, cleaned_tag, "fx"))
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
