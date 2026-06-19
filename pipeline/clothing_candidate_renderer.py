from __future__ import annotations

import random
from typing import Any

try:
    from ..clothing_service import resolve_clothing_theme
    from ..core.semantic_policy import sanitize_text
    from ..history_service import clothing_signature_from_decision, extract_object_flags
    from ..location_service import resolve_location_key
    from ..vocab import clothing as clothing_vocab
    from ..vocab.seed_utils import mix_seed
except ImportError:
    from clothing_service import resolve_clothing_theme
    from core.semantic_policy import sanitize_text
    from history_service import clothing_signature_from_decision, extract_object_flags
    from location_service import resolve_location_key
    from vocab import clothing as clothing_vocab
    from vocab.seed_utils import mix_seed


OUTERWEAR_BLOCKED_LOCATION_KEYS = {
    "apartment_balcony",
    "bedroom_boudoir",
    "clean_modern_kitchen",
    "cozy_living_room",
    "messy_kitchen",
    "fitness_gym",
    "school_gym_hall",
}
STATE_DETAIL_RULES = (
    {
        "family": "snow",
        "terms": ("snow", "snowy", "snowflake"),
        "allowed_location_keys": ("winter_street",),
        "allowed_location_terms": ("snow", "snowy", "winter", "ski"),
    },
    {
        "family": "wet",
        "terms": ("rain-soaked", "wet"),
        "allowed_location_keys": (
            "enchanted_lake",
            "japanese_bath",
            "luxury_bathroom",
            "poolside_resort",
            "rainy_alley",
            "rainy_bus_stop",
            "riverside_walk",
            "tropical_beach",
            "wave_barrel",
        ),
        "allowed_location_terms": ("rain", "wet", "bath", "onsen", "beach", "pool", "wave", "lake", "riverside"),
    },
    {
        "family": "sun_beach",
        "terms": ("sun-kissed",),
        "allowed_location_keys": ("mountain_resort", "poolside_resort", "tropical_beach", "wave_barrel"),
        "allowed_location_terms": ("beach", "pool", "poolside", "resort", "summer", "sun", "wave"),
    },
    {
        "family": "exertion",
        "terms": ("sweaty",),
        "allowed_location_keys": ("fitness_gym", "school_gym_hall", "stadium_court", "yoga_studio"),
        "allowed_location_terms": ("gym", "yoga", "stadium", "court", "sport", "training", "workout"),
    },
    {
        "family": "battle_damage",
        "terms": ("battle-worn", "blood-stained"),
        "allowed_location_keys": ("burning_battlefield", "castle_hall", "dragon_lair", "dungeon_crypt"),
        "allowed_location_terms": ("battle", "battlefield", "castle", "dragon", "dungeon", "lair"),
    },
    {
        "family": "workshop_dirt",
        "terms": ("grease stained",),
        "allowed_location_keys": ("clockwork_workshop",),
        "allowed_location_terms": ("clockwork", "workshop", "mechanic", "industrial", "machinery"),
    },
)


def normalize_signature_part(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    return "_".join(text.replace("-", " ").split())


def build_variant_signature(parts: list[Any]) -> str:
    normalized = [normalize_signature_part(part) for part in parts if normalize_signature_part(part)]
    return "~".join(normalized)


def state_detail_rule(value: str) -> dict[str, Any] | None:
    text = str(value or "").lower()
    for rule in STATE_DETAIL_RULES:
        if any(term in text for term in rule["terms"]):
            return rule
    return None


def location_allows_state_detail(loc: str, state_detail: str) -> bool:
    rule = state_detail_rule(state_detail)
    if not rule:
        return True
    raw = str(loc or "").strip().lower()
    loc_key = resolve_location_key(loc) or raw
    loc_key = str(loc_key or "").strip().lower()
    if loc_key in rule["allowed_location_keys"]:
        return True
    loc_text = " ".join(part for part in (raw, loc_key) if part)
    return bool(loc_text and any(term in loc_text for term in rule["allowed_location_terms"]))


def build_item_description(rng, concept_data: dict[str, Any], char_colors=None, loc: str = "") -> tuple[str, str]:
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

    def pick_palette(key: str) -> str:
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
        state_detail = rng.choice(states)
        if location_allows_state_detail(loc, state_detail):
            details_list.append(state_detail)

    adjectives = [x for x in [color, pattern, material, style] if x]
    adj_str = " ".join(adjectives)
    items_str = " and ".join(selected_items)
    main_part = f"{adj_str} {items_str}" if adj_str else items_str
    variant_signature = build_variant_signature([
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


def weighted_recent_choice(options, rng, recent_values=None) -> str:
    values = list(options or [])
    if not values:
        return ""
    recent_values = {str(item) for item in (recent_values or []) if item}
    if len(values) == 1:
        return values[0]
    weights = [0.25 if str(item) in recent_values else 1.0 for item in values]
    return rng.choices(values, weights=weights, k=1)[0]


def location_blocks_outerwear(loc: str) -> bool:
    loc_key = resolve_location_key(loc) or str(loc or "").strip().lower()
    return loc_key in OUTERWEAR_BLOCKED_LOCATION_KEYS


def candidate_repeat_penalty(decision, recent_packs, recent_types, recent_outerwear, recent_signatures) -> int:
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


def render_clothing_candidate(
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
                else weighted_recent_choice(available_types, rng, recent_values=recent_types)
            )
        if chosen_type:
            chosen_pack_name = weighted_recent_choice(packs_map[chosen_type], rng, recent_values=recent_packs)
            concept_data = clothing_vocab.CONCEPT_PACKS[chosen_type].get(chosen_pack_name)
            if concept_data:
                item_description, variant_signature = build_item_description(rng, concept_data, char_colors, loc=loc)
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
        elif location_blocks_outerwear(loc):
            should_add_outer = False
        else:
            outerwear_floor = float(getattr(clothing_vocab, "OUTERWEAR_SELECTION_PROBABILITY", 0.25))
            should_add_outer = rng.random() < max(float(outerwear_chance), min(0.45, outerwear_floor + 0.12))

    if should_add_outer:
        outer_name = weighted_recent_choice(packs_map["outerwear"], rng, recent_values=recent_outerwear)
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
            decision["outerwear_variant"] = build_variant_signature([chosen_color, chosen_outer])

    prompt = sanitize_text(", ".join(final_parts))
    decision["objects"] = sorted(extract_object_flags(prompt))
    decision["signature"] = clothing_signature_from_decision(decision)
    if recent_signatures and decision["signature"] in recent_signatures:
        decision["repeat_guard_hit"] = True
    decision["prompt"] = prompt
    decision["repeat_guard_penalty"] = candidate_repeat_penalty(
        decision,
        recent_packs=recent_packs,
        recent_types=recent_types,
        recent_outerwear=recent_outerwear,
        recent_signatures=recent_signatures,
    )
    decision["attempt_index"] = int(attempt_index)
    return prompt, decision
