import random

if __package__ and "." in __package__:
    from ..clothing_service import resolve_clothing_theme
    from ..core.context_state import generation_state_from_context
    from ..core.context_ops import append_history, ensure_context, patch_context
    from ..core.schema import DebugInfo
    from ..core.semantic_policy import sanitize_text
    from ..history_service import (
        clothing_signature_from_decision,
        extract_object_flags,
        recent_clothing_packs,
        recent_clothing_signatures,
        recent_clothing_types,
        recent_outerwear_packs,
    )
    from ..location_service import resolve_location_key
    from ..vocab.seed_utils import mix_seed
else:
    from clothing_service import resolve_clothing_theme
    from core.context_state import generation_state_from_context
    from core.context_ops import append_history, ensure_context, patch_context
    from core.schema import DebugInfo
    from core.semantic_policy import sanitize_text
    from history_service import (
        clothing_signature_from_decision,
        extract_object_flags,
        recent_clothing_packs,
        recent_clothing_signatures,
        recent_clothing_types,
        recent_outerwear_packs,
    )
    from location_service import resolve_location_key
    from vocab.seed_utils import mix_seed

if __package__ and "." in __package__:
    from .. import clothing_vocab
else:
    import clothing_vocab

VALID_OUTFIT_MODES = ("random", "dresses", "separates", "outerwear_only", "no_outerwear")
CLOTHING_CANDIDATE_ATTEMPTS = 5
OUTERWEAR_BLOCKED_LOCATION_KEYS = {
    "apartment_balcony",
    "bedroom_boudoir",
    "clean_modern_kitchen",
    "cozy_living_room",
    "messy_kitchen",
    "fitness_gym",
    "school_gym_hall",
}


def _normalize_signature_part(value):
    text = str(value or "").strip().lower()
    if not text:
        return ""
    return "_".join(text.replace("-", " ").split())


def _build_variant_signature(parts):
    normalized = [_normalize_signature_part(part) for part in parts if _normalize_signature_part(part)]
    return "~".join(normalized)


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
        if key == "colors" and char_colors and rng.random() < 0.60:
            return rng.choice(char_colors)
        default_prob = clothing_vocab.PALETTE_DEFAULT_PROBABILITIES.get(key, 0.5)
        if key in palette and palette[key] and rng.random() < default_prob:
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
    variant_signature = _build_variant_signature([
        *selected_items,
        color,
        material,
        pattern,
        style,
        *details_list,
    ])
    if details_list:
        return f"{main_part}, with {', '.join(details_list)}", variant_signature
    return main_part, variant_signature


def _weighted_recent_choice(options, rng, recent_values=None):
    values = list(options or [])
    if not values:
        return ""
    recent_values = {str(item) for item in (recent_values or []) if item}
    if len(values) == 1:
        return values[0]
    weights = [0.25 if str(item) in recent_values else 1.0 for item in values]
    return rng.choices(values, weights=weights, k=1)[0]


def _location_blocks_outerwear(loc):
    loc_key = resolve_location_key(loc) or str(loc or "").strip().lower()
    return loc_key in OUTERWEAR_BLOCKED_LOCATION_KEYS


def _candidate_repeat_penalty(decision, recent_packs, recent_types, recent_outerwear, recent_signatures):
    penalty = 0
    signature = str(decision.get("signature", "")).strip()
    base_pack = str(decision.get("base_pack", "")).strip()
    chosen_type = str(decision.get("chosen_type", "")).strip()
    outerwear_pack = str(decision.get("outerwear_pack", "")).strip()
    if signature and signature in recent_signatures:
        penalty += 8
    if base_pack and base_pack in recent_packs:
        penalty += 3
    if chosen_type and chosen_type in recent_types:
        penalty += 2
    if outerwear_pack and outerwear_pack in recent_outerwear:
        penalty += 1
    return penalty


def _render_clothing_candidate(
    theme_key,
    seed,
    outfit_mode,
    outerwear_chance,
    character_palette,
    recent_packs,
    recent_types,
    recent_outerwear,
    recent_signatures,
    attempt_index=0,
    loc="",
):
    rng = random.Random(mix_seed(seed, "cloth" if attempt_index == 0 else f"cloth:{attempt_index}"))
    raw_key = str(theme_key).lower().strip()
    char_colors = [c.strip() for c in str(character_palette).split(",") if c.strip()] if character_palette else []
    theme = resolve_clothing_theme(raw_key) or raw_key
    packs_map = clothing_vocab.THEME_TO_PACKS.get(theme)
    if not packs_map:
        prompt = sanitize_text(f"{theme_key}, generic outfit")
        debug = {"theme": theme, "base_pack": "", "chosen_type": "", "outerwear_pack": "", "objects": []}
        return prompt, debug

    final_parts = []
    decision = {
        "theme": theme,
        "chosen_type": "",
        "base_pack": "",
        "base_variant": "",
        "outerwear_pack": "",
        "outerwear_variant": "",
        "signature": "",
        "objects": [],
    }
    if outfit_mode != "outerwear_only":
        available_types = [key for key in packs_map.keys() if key in ["dresses", "separates"]]
        chosen_type = None
        if available_types:
            chosen_type = (
                outfit_mode
                if outfit_mode in available_types
                else _weighted_recent_choice(available_types, rng, recent_values=recent_types)
            )
        if chosen_type:
            chosen_pack_name = _weighted_recent_choice(packs_map[chosen_type], rng, recent_values=recent_packs)
            concept_data = clothing_vocab.CONCEPT_PACKS[chosen_type].get(chosen_pack_name)
            if concept_data:
                item_description, variant_signature = _build_item_description(rng, concept_data, char_colors)
                final_parts.append(item_description)
                decision["chosen_type"] = chosen_type
                decision["base_pack"] = chosen_pack_name
                decision["base_variant"] = variant_signature

    has_outer = "outerwear" in packs_map and packs_map["outerwear"]
    should_add_outer = False
    if has_outer:
        if outfit_mode == "outerwear_only":
            should_add_outer = True
        elif outfit_mode == "no_outerwear":
            should_add_outer = False
        elif _location_blocks_outerwear(loc):
            should_add_outer = False
        else:
            outerwear_floor = float(getattr(clothing_vocab, "OUTERWEAR_SELECTION_PROBABILITY", 0.25))
            should_add_outer = rng.random() < max(float(outerwear_chance), min(0.45, outerwear_floor + 0.12))

    if should_add_outer:
        outer_name = _weighted_recent_choice(packs_map["outerwear"], rng, recent_values=recent_outerwear)
        outer_data = clothing_vocab.CONCEPT_PACKS["outerwear"].get(outer_name)
        if outer_data:
            outer_palette = outer_data.get("palette", {})
            outer_colors = outer_palette.get("colors", [])
            outer_choices = outer_data.get("choices", {}).get("outerwear", [])
            outer_description = ""
            chosen_color = ""
            chosen_outer = ""
            if char_colors and rng.random() < 0.7:
                chosen_color = rng.choice(char_colors)
            elif outer_colors:
                chosen_color = rng.choice(outer_colors)
            if chosen_color:
                outer_description += f"{chosen_color} "
            if outer_choices:
                chosen_outer = rng.choice(outer_choices)
                outer_description += f"{chosen_outer}"
            if outfit_mode == "outerwear_only":
                final_parts.append(outer_description)
            else:
                final_parts.append(f"wearing a {outer_description} over it")
            decision["outerwear_pack"] = outer_name
            decision["outerwear_variant"] = _build_variant_signature([chosen_color, chosen_outer])

    prompt = sanitize_text(", ".join(final_parts))
    decision["objects"] = sorted(extract_object_flags(prompt))
    decision["signature"] = clothing_signature_from_decision(decision)
    if recent_signatures and decision["signature"] in recent_signatures:
        decision["repeat_guard_hit"] = True
    decision["prompt"] = prompt
    decision["repeat_guard_penalty"] = _candidate_repeat_penalty(
        decision,
        recent_packs=recent_packs,
        recent_types=recent_types,
        recent_outerwear=recent_outerwear,
        recent_signatures=recent_signatures,
    )
    decision["attempt_index"] = int(attempt_index)
    return prompt, decision


def expand_clothing_prompt(
    theme_key,
    seed,
    outfit_mode,
    outerwear_chance,
    character_palette="",
    loc="",
    recent_packs=None,
    recent_types=None,
    recent_outerwear=None,
    recent_signatures=None,
    return_debug=False,
):
    try:
        seed = int(seed)
    except Exception:
        seed = 0
    if outfit_mode not in VALID_OUTFIT_MODES:
        outfit_mode = "random"
    if not clothing_vocab:
        return "[ERR: clothing_vocab.py not found]"
    recent_packs = {str(item) for item in (recent_packs or []) if item}
    recent_types = {str(item) for item in (recent_types or []) if item}
    recent_outerwear = {str(item) for item in (recent_outerwear or []) if item}
    recent_signatures = {str(item) for item in (recent_signatures or []) if item}

    prompt, decision = _render_clothing_candidate(
        theme_key,
        seed,
        outfit_mode,
        outerwear_chance,
        character_palette,
        loc=loc,
        recent_packs=recent_packs,
        recent_types=recent_types,
        recent_outerwear=recent_outerwear,
        recent_signatures=recent_signatures,
        attempt_index=0,
    )
    best_score = int(decision.get("repeat_guard_penalty", 0))
    for attempt_index in range(1, CLOTHING_CANDIDATE_ATTEMPTS):
        candidate_prompt, candidate_decision = _render_clothing_candidate(
            theme_key,
            seed,
            outfit_mode,
            outerwear_chance,
            character_palette,
            loc=loc,
            recent_packs=recent_packs,
            recent_types=recent_types,
            recent_outerwear=recent_outerwear,
            recent_signatures=recent_signatures,
            attempt_index=attempt_index,
        )
        candidate_score = int(candidate_decision.get("repeat_guard_penalty", 0))
        if candidate_score < best_score:
            prompt, decision = candidate_prompt, candidate_decision
            best_score = candidate_score
            if best_score == 0:
                break
    return (prompt, decision) if return_debug else prompt


def apply_clothing_expansion(context, seed, outfit_mode, outerwear_chance, character_palette=""):
    ctx = ensure_context(context, default_seed=int(seed))
    state = generation_state_from_context(ctx)
    raw_theme_key = state.clothing.raw_costume_key or ctx.costume
    theme_key = resolve_clothing_theme(raw_theme_key) or raw_theme_key
    raw_loc_key = state.location.raw_loc_tag or ctx.loc
    palette_value = character_palette or state.character.palette_text
    clothing_prompt, decision = expand_clothing_prompt(
        theme_key,
        seed,
        outfit_mode,
        outerwear_chance,
        palette_value,
        loc=raw_loc_key,
        recent_packs=recent_clothing_packs(ctx),
        recent_types=recent_clothing_types(ctx),
        recent_outerwear=recent_outerwear_packs(ctx),
        recent_signatures=recent_clothing_signatures(ctx),
        return_debug=True,
    )
    state.character.palette_text = palette_value
    state.character.palette = [item.strip() for item in palette_value.split(",") if item.strip()] if palette_value else []
    state.clothing.raw_costume_key = raw_theme_key
    state.clothing.resolved_theme = theme_key
    state.clothing.clothing_prompt = clothing_prompt
    ctx = patch_context(
        ctx,
        updates={"seed": seed, "costume": theme_key},
        extras=state.to_extras_patch(),
    )
    ctx = append_history(
        ctx,
        DebugInfo(
            node="ContextClothingExpander",
            seed=seed,
            decision=decision,
        ),
    )
    return ctx, clothing_prompt
