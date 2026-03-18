import json
import logging
import os
import random
import re

try:
    from ..core.context_ops import patch_context, ensure_context
    from ..vocab.seed_utils import mix_seed
except ImportError:
    from core.context_ops import patch_context, ensure_context
    from vocab.seed_utils import mix_seed

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "vocab", "data")

logger = logging.getLogger("PromptAssembly")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(os.path.join(ROOT_DIR, "simple_template_debug.log"), encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

DEFAULT_GENERATION_MODE = "scene_emotion_priority"
DEFAULT_TEMPLATE = "{subject_clause}, {action_clause}, {scene_clause}."
DEFAULT_END_TEMPLATE = "{scene_clause}"

try:
    from .. import clothing_vocab
except ImportError:
    try:
        import clothing_vocab
    except ImportError:
        clothing_vocab = None

try:
    from .. import background_vocab
except ImportError:
    try:
        import background_vocab
    except ImportError:
        background_vocab = None

_object_concentration_policy_cache = None

CLOTHING_ALIAS_MAP = {
    "business girl": "office_lady",
    "ceo": "office_lady",
    "student": "school_uniform",
    "runner": "gym_workout",
    "fitness model": "gym_workout",
    "vacationer": "beach_resort",
    "winter traveler": "winter_date",
    "japanese shrine maiden": "traditional_japanese",
    "geisha": "traditional_japanese",
    "spy agent": "secret_agent",
    "detective": "secret_agent",
    "rock star": "rock_concert",
    "guitarist": "rock_concert",
    "gothic girl": "gothic_lolita",
    "doll-like girl": "gothic_lolita",
    "sorceress": "fantasy_battle",
    "blonde elf archer": "fantasy_battle",
    "cyberpunk warrior": "cyberpunk_night",
    "street dancer": "cyberpunk_night",
}

DAILY_LIFE_LOCS = {
    "school_classroom", "school_rooftop", "school_library", "modern_office",
    "boardroom", "office_elevator", "commuter_transport", "street_cafe",
    "cozy_bookstore", "shopping_mall_atrium", "fashion_boutique",
    "bedroom_boudoir", "messy_kitchen", "clean_modern_kitchen",
    "cozy_living_room", "rainy_bus_stop", "suburban_neighborhood",
    "rural_town_street", "picnic_park", "illuminated_park", "winter_street",
    "japanese_garden", "tea_room",
}
BIAS_OBJECT_HINTS = (
    "surfboard", " board", "book", "phone", "coffee", "drink", "microphone", "screen",
)
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


def _resolve_json_path(json_path: str) -> str:
    if not json_path or str(json_path).strip() == "":
        json_path = "mood_map.json"
    if not os.path.isabs(json_path):
        json_path = os.path.join(ROOT_DIR, json_path)
    return json_path


def expand_dictionary_value(key, json_path, default_value, seed):
    try:
        seed = int(seed)
    except Exception:
        seed = 0

    json_path = _resolve_json_path(json_path)
    data = {}
    if os.path.exists(json_path) and os.path.isfile(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"\033[93m[MoodExpand] Error loading JSON: {e}\033[0m")
    else:
        print(f"\033[93m[MoodExpand] File not found: {json_path}\033[0m")

    key_lower = str(key).lower().strip()
    data_lower = {k.lower(): v for k, v in data.items()}
    result = data_lower.get(key_lower, default_value)
    staging_text = ""

    if isinstance(result, dict):
        rng = random.Random(seed)
        desc_list = result.get("description", [])
        if isinstance(desc_list, list) and desc_list:
            description_text = rng.choice(desc_list)
        else:
            description_text = str(result.get("description", default_value))
        staging_list = result.get("staging_tags", [])
        if isinstance(staging_list, list):
            staging_text = ", ".join(staging_list)
        return str(description_text), staging_text

    if isinstance(result, list):
        rng = random.Random(seed)
        result = rng.choice(result) if result else default_value

    return str(result), staging_text


def apply_mood_expansion(context, seed, json_path, default_value):
    ctx = ensure_context(context, default_seed=int(seed))
    key = ctx.meta.mood
    expanded_text, staging_text = expand_dictionary_value(key, json_path, default_value, seed)
    extras = {}
    if staging_text:
        extras["staging_tags"] = staging_text
    ctx = patch_context(ctx, updates={"seed": seed}, meta={"mood": expanded_text}, extras=extras)
    return ctx, expanded_text, staging_text


def _build_item_description(rng, concept_data, char_colors=None):
    selected_items = []
    choices_dict = concept_data.get("choices", {})
    for _, options in choices_dict.items():
        choice = rng.choice(options)
        if isinstance(choice, list):
            if len(choice) > 1:
                item_str = f"{choice[1]} {choice[0]}"
            elif len(choice) == 1:
                item_str = choice[0]
            else:
                item_str = ""
        else:
            item_str = choice
        if item_str:
            selected_items.append(item_str)

    palette = concept_data.get("palette", {})

    def pick_palette(key):
        if key == "colors" and char_colors:
            if rng.random() < 0.60:
                return rng.choice(char_colors)
        default_prob = clothing_vocab.PALETTE_DEFAULT_PROBABILITIES.get(key, 0.5)
        if key in palette and palette[key]:
            if rng.random() < default_prob:
                return rng.choice(palette[key])
        return ""

    color = pick_palette("colors")
    material = pick_palette("materials")
    pattern = pick_palette("patterns")
    style = pick_palette("styles")
    embellishments = palette.get("embellishments", [])
    opt_details = concept_data.get("optional_details", [])
    details_list = []
    embellishment_prob = max(0.70, float(getattr(clothing_vocab, "EMBELLISHMENT_DETAIL_PROBABILITY", 0.55)))
    optional_detail_prob = max(0.60, float(getattr(clothing_vocab, "OPTIONAL_DETAIL_PROBABILITY", 0.45)))
    state_detail_prob = max(0.38, float(getattr(clothing_vocab, "STATE_DETAIL_PROBABILITY", 0.30)))
    if embellishments and rng.random() < embellishment_prob:
        details_list.append(rng.choice(embellishments))
    if opt_details and rng.random() < optional_detail_prob:
        details_list.append(rng.choice(opt_details))
    states = concept_data.get("states", [])
    if states and rng.random() < state_detail_prob:
        details_list.append(rng.choice(states))

    adjectives = [x for x in [color, pattern, material, style] if x]
    adj_str = " ".join(adjectives)
    items_str = " and ".join(selected_items)
    main_part = f"{adj_str} {items_str}" if adj_str else items_str
    if details_list:
        return f"{main_part}, with {', '.join(details_list)}"
    return main_part


def expand_clothing_prompt(theme_key, seed, outfit_mode, outerwear_chance, character_palette=""):
    try:
        seed = int(seed)
    except Exception:
        seed = 0
    if outfit_mode not in ["random", "dresses", "separates", "outerwear_only", "no_outerwear"]:
        outfit_mode = "random"
    if not clothing_vocab:
        return "[ERR: clothing_vocab.py not found]"

    rng = random.Random(mix_seed(seed, "cloth"))
    raw_key = str(theme_key).lower().strip()
    char_colors = [c.strip() for c in str(character_palette).split(",") if c.strip()] if character_palette else []
    theme = CLOTHING_ALIAS_MAP.get(raw_key, raw_key)
    packs_map = clothing_vocab.THEME_TO_PACKS.get(theme)
    if not packs_map:
        return f"{theme_key}, (generic outfit)"

    final_parts = []
    if outfit_mode != "outerwear_only":
        available_types = [k for k in packs_map.keys() if k in ["dresses", "separates"]]
        chosen_type = None
        if available_types:
            chosen_type = outfit_mode if outfit_mode in available_types else rng.choice(available_types)
        if chosen_type:
            chosen_pack_name = rng.choice(packs_map[chosen_type])
            concept_data = clothing_vocab.CONCEPT_PACKS[chosen_type].get(chosen_pack_name)
            if concept_data:
                final_parts.append(_build_item_description(rng, concept_data, char_colors))

    has_outer = "outerwear" in packs_map and packs_map["outerwear"]
    should_add_outer = False
    if has_outer:
        if outfit_mode == "outerwear_only":
            should_add_outer = True
        elif outfit_mode == "no_outerwear":
            should_add_outer = False
        else:
            outerwear_floor = float(getattr(clothing_vocab, "OUTERWEAR_SELECTION_PROBABILITY", 0.25))
            should_add_outer = rng.random() < max(float(outerwear_chance), min(0.45, outerwear_floor + 0.12))

    if should_add_outer:
        outer_name = rng.choice(packs_map["outerwear"])
        outer_data = clothing_vocab.CONCEPT_PACKS["outerwear"].get(outer_name)
        if outer_data:
            o_palette = outer_data.get("palette", {})
            o_colors = o_palette.get("colors", [])
            o_choices = outer_data.get("choices", {}).get("outerwear", [])
            o_desc = ""
            chosen_color = ""
            if char_colors and rng.random() < 0.7:
                chosen_color = rng.choice(char_colors)
            elif o_colors:
                chosen_color = rng.choice(o_colors)
            if chosen_color:
                o_desc += f"{chosen_color} "
            if o_choices:
                o_desc += f"{rng.choice(o_choices)}"
            if outfit_mode == "outerwear_only":
                final_parts.append(o_desc)
            else:
                final_parts.append(f"wearing a {o_desc} over it")

    return ", ".join(final_parts)


def apply_clothing_expansion(context, seed, outfit_mode, outerwear_chance, character_palette=""):
    ctx = ensure_context(context, default_seed=int(seed))
    theme_key = str(ctx.extras.get("raw_costume_key", "") or ctx.costume)
    palette_value = character_palette or str(ctx.extras.get("character_palette_str", ""))
    clothing_prompt = expand_clothing_prompt(theme_key, seed, outfit_mode, outerwear_chance, palette_value)
    ctx = patch_context(
        ctx,
        updates={"seed": seed},
        extras={"clothing_prompt": clothing_prompt, "raw_costume_key": theme_key, "character_palette_str": palette_value},
    )
    return ctx, clothing_prompt


def _is_symbolic_prop(text):
    low = str(text).lower()
    return any(token in low for token in BIAS_OBJECT_HINTS)


def _props_sampling_policy(props_opts):
    include_prob = 0.8
    second_prop_prob = 0.45
    if len(props_opts) <= 3:
        include_prob = 0.62
        second_prop_prob = 0.20
    if any(_is_symbolic_prop(p) for p in props_opts):
        include_prob = max(0.50, include_prob - 0.12)
        second_prop_prob = max(0.10, second_prop_prob - 0.10)
    return include_prob, second_prop_prob


def _is_disallowed_fx_segment(text):
    low = str(text).lower()
    if "snowflake" in low or "sparkling eyes" in low:
        return False
    return any(p.search(low) for p in FX_DENY_PATTERNS)


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


def _object_policy_for_loc(loc_tag):
    policy = _load_object_concentration_policy()
    background_policy = policy.get("content_redistribution", {}).get("background", {})
    return background_policy.get(str(loc_tag).lower().strip(), {})


def _segment_weight_map(loc_tag, section_name):
    return _object_policy_for_loc(loc_tag).get(f"{section_name}_weights", {})


def _weighted_choice(options, rng, loc_tag, section_name):
    if not options:
        return ""
    weights_map = _segment_weight_map(loc_tag, section_name)
    weights = [max(0.01, float(weights_map.get(str(option), 1.0))) for option in options]
    return rng.choices(list(options), weights=weights, k=1)[0]


def _weighted_sample(options, rng, k, loc_tag, section_name):
    available = list(options)
    selected = []
    while available and len(selected) < k:
        weights_map = _segment_weight_map(loc_tag, section_name)
        weights = [max(0.01, float(weights_map.get(str(option), 1.0))) for option in available]
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


def expand_location_prompt(loc_tag, seed, mode, lighting_mode="auto"):
    try:
        seed = int(seed)
    except Exception:
        seed = 0
    if mode not in ["detailed", "simple"]:
        mode = "detailed"
    if not background_vocab:
        return "[ERR: background_vocab.py not found]"

    rng = random.Random(mix_seed(seed, "loc"))
    cleaned_tag = str(loc_tag).lower().strip()
    pack_candidates = background_vocab.LOC_TAG_MAP.get(cleaned_tag)
    if not pack_candidates:
        return str(loc_tag)
    selected_pack_key = rng.choice(pack_candidates)
    pack_data = background_vocab.CONCEPT_PACKS.get(selected_pack_key)
    if not pack_data:
        return str(loc_tag)

    env_options = pack_data.get("environment", [])
    env_part = _weighted_choice(env_options, rng, selected_pack_key, "environment") if env_options else cleaned_tag
    if mode == "simple":
        return env_part

    segments = []
    core_opts = pack_data.get("core", [])
    if core_opts and rng.random() < 0.95:
        num_core = 2 if len(core_opts) > 1 and rng.random() < 0.50 else 1
        chosen_core = _weighted_sample(core_opts, rng, min(num_core, len(core_opts)), selected_pack_key, "core")
        if len(chosen_core) == 1:
            segments.append(f"featuring {chosen_core[0]}")
        else:
            connector = rng.choice(["and", "plus", "featuring"])
            segments.append(f"featuring {chosen_core[0]} {connector} {chosen_core[1]}")

    props_opts = pack_data.get("props", [])
    include_prob, second_prop_prob = _props_sampling_policy(props_opts)
    if props_opts and rng.random() < include_prob:
        num_props = 2 if len(props_opts) > 1 and rng.random() < second_prop_prob else 1
        if num_props == 2 and all(_is_symbolic_prop(p) for p in props_opts):
            num_props = 1
        chosen_props = _weighted_sample(props_opts, rng, min(num_props, len(props_opts)), selected_pack_key, "props")
        connector_word = rng.choice(["with", "scattered with", "filled with", "adorned with"])
        if len(chosen_props) == 1:
            segments.append(f"{connector_word} {chosen_props[0]}")
        else:
            joiner = rng.choice(["and", "plus", "as well as"])
            segments.append(f"{connector_word} {chosen_props[0]} {joiner} {chosen_props[1]}")

    texture_candidates = list(pack_data.get("texture", []) or [])
    general_defaults = getattr(background_vocab, "GENERAL_DEFAULTS", {})
    if rng.random() < TEXTURE_DEFAULT_BLEND_PROB:
        texture_candidates.extend(general_defaults.get("texture", []))
    if lighting_mode == "off":
        texture_candidates = _filter_off_mode_options(texture_candidates, fallback_all=False)
    if texture_candidates and rng.random() < TEXTURE_SEGMENT_SELECT_PROB:
        segments.append(rng.choice(texture_candidates))

    if rng.random() < 0.35:
        details_defaults = general_defaults.get("details", [])
        if lighting_mode == "off":
            details_defaults = _filter_off_mode_options(details_defaults, fallback_all=False)
        if details_defaults:
            segments.append(rng.choice(details_defaults))

    is_daily_life = _is_daily_life_loc(cleaned_tag)
    time_opts = pack_data.get("time", [])
    if lighting_mode == "off":
        time_opts = _filter_off_mode_options(time_opts, fallback_all=False)
    if time_opts and rng.random() < (0.72 if is_daily_life else 0.5):
        segments.append(f"during {rng.choice(_prefer_bright_time_options(time_opts))}")
    weather_opts = pack_data.get("weather", [])
    preferred_weather, rare_weather = _split_weather_options(weather_opts)
    weather_probability = 0.18 if is_daily_life else 0.12
    if preferred_weather and rng.random() < weather_probability:
        segments.append(rng.choice(preferred_weather))
    elif rare_weather and rng.random() < 0.03:
        segments.append(rng.choice(rare_weather))
    crowd_opts = pack_data.get("crowd", [])
    if crowd_opts and rng.random() < (0.58 if is_daily_life else 0.30):
        segments.append(rng.choice(crowd_opts))

    fx_candidates = _filter_fx_candidates(pack_data.get("fx", []) or [])
    if lighting_mode == "off":
        fx_candidates = _filter_off_mode_options(fx_candidates, fallback_all=False)
    if rng.random() < FX_DEFAULT_BLEND_PROB:
        fx_candidates.extend(_filter_fx_candidates(general_defaults.get("fx", [])))
    if lighting_mode == "off":
        fx_candidates = _filter_off_mode_options(fx_candidates, fallback_all=False)
    fx_segments_added = 0
    if fx_candidates and fx_segments_added < MAX_FX_SEGMENTS and rng.random() < FX_SEGMENT_SELECT_PROB:
        segments.append(_weighted_choice(fx_candidates, rng, selected_pack_key, "fx"))
        fx_segments_added += 1

    rng.shuffle(segments)
    deduped_segments = []
    seen_segments = set()
    for seg in segments:
        if seg not in seen_segments:
            deduped_segments.append(seg)
            seen_segments.add(seg)

    if lighting_mode == "auto":
        lighting_opts = pack_data.get("lighting", [])
        if lighting_opts:
            chosen_lighting = rng.choice(lighting_opts)
            if not any(_contains_lighting_hint(segment) for segment in deduped_segments):
                deduped_segments.append(chosen_lighting)

    return ", ".join([env_part] + deduped_segments) if deduped_segments else env_part


def apply_location_expansion(context, seed, mode, lighting_mode="auto"):
    ctx = ensure_context(context, default_seed=int(seed))
    loc_tag = str(ctx.extras.get("raw_loc_tag", "") or ctx.loc)
    location_prompt = expand_location_prompt(loc_tag, seed, mode, lighting_mode)
    ctx = patch_context(ctx, updates={"seed": seed}, extras={"location_prompt": location_prompt, "raw_loc_tag": loc_tag})
    return ctx, location_prompt


def _load_lines(filename):
    path = os.path.join(ROOT_DIR, filename)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                logger.debug(f"Loaded {len(lines)} lines from {filename}")
                return lines
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            print(f"\033[93m[PromptAssembly] Error loading {filename}: {e}\033[0m")
    else:
        logger.warning(f"File not found: {filename}")
    return []


def _load_rules():
    rule_path = os.path.join(ROOT_DIR, "rules", "consistency_rules.json")
    if os.path.exists(rule_path):
        try:
            with open(rule_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                rules = data.get("conflicts", [])
                logger.debug(f"Loaded {len(rules)} consistency rules.")
                return rules
        except Exception as e:
            logger.error(f"Error loading consistency_rules.json: {e}")
            print(f"\033[93m[PromptAssembly] Error loading consistency_rules.json: {e}\033[0m")
    else:
        logger.warning("consistency_rules.json not found.")
    return []


def _join_nonempty(parts, sep=", "):
    cleaned = []
    for part in parts:
        if part is None:
            continue
        text = str(part).strip().strip(",")
        if text:
            cleaned.append(text)
    return sep.join(cleaned)


def _strip_clause_punctuation(text):
    if text is None:
        return ""
    return re.sub(r"[\s,.;:]+$", "", str(text).strip())


def _compose_visual_sentence(*parts):
    clauses = []
    for part in parts:
        clean = _strip_clause_punctuation(part)
        if clean:
            clauses.append(clean)
    if not clauses:
        return ""
    return ", ".join(clauses) + "."


def _normalize_prompt(text):
    if text is None:
        return ""
    text = str(text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r",\s*,+", ", ", text)
    text = re.sub(r"\.\s*\.+", ".", text)
    text = re.sub(r",\s*\.", ".", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _make_consistency_checker(rules, context_values):
    def is_consistent(template_part):
        for rule in rules:
            input_term = rule.get("input_term", "").lower()
            template_term = rule.get("template_term", "").lower()
            if not input_term or not template_term:
                continue
            triggered = False
            for val in context_values:
                if val and input_term in str(val).lower():
                    triggered = True
                    break
            if triggered and template_term in str(template_part).lower():
                logger.debug(f"Conflict detected: input '{input_term}' conflicts with template '{template_term}' in part '{template_part}'")
                return False
        return True
    return is_consistent


def _expand_location_key_for_builder(loc, rng, context_values, is_consistent):
    bg_packs_path = os.path.join(DATA_DIR, "background_packs.json")
    if not loc or not isinstance(loc, str) or not os.path.exists(bg_packs_path):
        return loc
    try:
        with open(bg_packs_path, "r", encoding="utf-8") as f:
            bg_packs = json.load(f)
        if loc not in bg_packs:
            return loc
        logger.info(f"Expanding location: {loc}")
        pack = bg_packs[loc]
        parts = []

        def pick_consistent(candidates):
            if not candidates:
                return None
            for _ in range(10):
                candidate = rng.choice(candidates)
                if is_consistent(str(candidate)):
                    return candidate
            logger.debug("Failed to find consistent candidate after 10 attempts.")
            return None

        envs = pack.get("environment", [])
        if envs:
            e = pick_consistent(envs)
            parts.append(e if e else pack.get("label", loc))
        else:
            parts.append(pack.get("label", loc))

        times = pack.get("time", [])
        if times:
            t = pick_consistent(times)
            if t:
                parts.append(f"during {t}")
        weathers = pack.get("weather", [])
        if weathers:
            w = pick_consistent(weathers)
            if w:
                parts.append(w)
        crowds = pack.get("crowd", [])
        if crowds:
            c = pick_consistent(crowds)
            if c:
                parts.append(c)
        new_loc = ", ".join(parts)
        logger.debug(f"Expanded loc '{loc}' to '{new_loc}'")
        return new_loc
    except Exception as e:
        logger.error(f"Error expanding location: {e}")
        print(f"[PromptAssembly] Error expanding location: {e}")
        return loc


def build_prompt_text(template, composition_mode, seed, subj="", costume="", loc="", action="", garnish="", meta_mood="", meta_style="", staging_tags=""):
    logger.info(f"--- PromptAssembly Build Start (Seed: {seed}) ---")
    logger.debug(f"Generation Mode: {DEFAULT_GENERATION_MODE}")
    logger.debug(f"Inputs - Subj: {subj}, Costume: {costume}, Loc: {loc}, Action: {action}, Garnish: {garnish}, Mood: {meta_mood}, Style: {meta_style}, Staging: {staging_tags}")
    logger.debug(f"Composition Mode: {composition_mode}")

    rng = random.Random(seed)
    subject_clause = _join_nonempty([subj, f"in {costume}" if costume else ""], " ")
    action_clause = _join_nonempty([action, garnish])
    scene_clause = _join_nonempty([f"in {loc}" if loc else "", meta_mood])
    rules = _load_rules()
    context_vals = [subj, costume, loc, action, garnish, meta_mood, meta_style, staging_tags]
    is_consistent = _make_consistency_checker(rules, context_vals)

    loc = _expand_location_key_for_builder(loc, rng, context_vals, is_consistent)
    context_vals = [subj, costume, loc, action, garnish, meta_mood, meta_style, staging_tags]
    is_consistent = _make_consistency_checker(rules, context_vals)
    scene_clause = _join_nonempty([f"in {loc}" if loc else "", meta_mood])

    if composition_mode:
        logger.info("Using Composition Mode")
        intros = _load_lines("vocab/templates_intro.txt")
        bodies = _load_lines("vocab/templates_body.txt")
        ends = _load_lines("vocab/templates_end.txt")

        def select_part(candidates, default):
            if not candidates:
                return default
            for _ in range(10):
                candidate = rng.choice(candidates)
                if is_consistent(candidate):
                    return candidate
            return rng.choice(candidates)

        p_intro = select_part(intros, "{subject_clause}")
        p_body = select_part(bodies, "{action_clause}")
        p_end = select_part(ends, DEFAULT_END_TEMPLATE)
        template = _compose_visual_sentence(p_intro, p_body, p_end)
        logger.debug(f"Composed Template: {template}")
    else:
        logger.info("Using Legacy/Single Template Mode")
        if not template or str(template).strip() == "" or template == DEFAULT_TEMPLATE:
            lines = _load_lines("templates.txt")
            if lines:
                template = rng.choice(lines)

    result = template
    result = result.replace("{subject_clause}", subject_clause)
    result = result.replace("{action_clause}", action_clause)
    result = result.replace("{scene_clause}", scene_clause)
    result = result.replace("{subj}", str(subj) if subj is not None else "")
    result = result.replace("{costume}", str(costume) if costume is not None else "")
    result = result.replace("{loc}", str(loc) if loc is not None else "")
    result = result.replace("{action}", str(action) if action is not None else "")
    result = result.replace("{garnish}", str(garnish) if garnish is not None else "")
    result = result.replace("{meta_mood}", str(meta_mood) if meta_mood is not None else "")
    result = result.replace("{meta_style}", str(meta_style) if meta_style is not None else "")

    if staging_tags and isinstance(staging_tags, str) and staging_tags.strip():
        if "{staging_tags}" in result:
            result = result.replace("{staging_tags}", staging_tags)
        else:
            result = f"{result}, {staging_tags}"
    else:
        result = result.replace("{staging_tags}", "")

    result = _normalize_prompt(result)
    logger.info(f"Final Prompt: {result}")
    return result


def build_prompt_from_context(context, template, composition_mode, seed):
    ctx = ensure_context(context, default_seed=int(seed))
    prompt = build_prompt_text(
        template=template,
        composition_mode=composition_mode,
        seed=seed,
        subj=ctx.subj,
        costume=str(ctx.extras.get("clothing_prompt", "") or ctx.costume),
        loc=str(ctx.extras.get("location_prompt", "") or ctx.loc),
        action=ctx.action,
        garnish=str(ctx.extras.get("garnish", "")),
        meta_mood=ctx.meta.mood,
        meta_style=ctx.meta.style,
        staging_tags=str(ctx.extras.get("staging_tags", "")),
    )
    return patch_context(ctx, updates={"seed": seed}), prompt
