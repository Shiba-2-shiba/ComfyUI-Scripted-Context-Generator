from __future__ import annotations

import random
import re
import hashlib
import json
from typing import Any

try:
    from ..clothing_service import resolve_clothing_theme
    from ..core.semantic_policy import sanitize_text
    from ..history_service import clothing_signature_digest, clothing_signature_from_decision, extract_object_flags
    from ..location_service import resolve_location_key
    from ..vocab import clothing as clothing_vocab
    from ..vocab.seed_utils import mix_seed
except ImportError:
    from clothing_service import resolve_clothing_theme
    from core.semantic_policy import sanitize_text
    from history_service import clothing_signature_digest, clothing_signature_from_decision, extract_object_flags
    from location_service import resolve_location_key
    from vocab import clothing as clothing_vocab
    from vocab.seed_utils import mix_seed


_GARMENT_MATERIAL = re.compile(
    r"\b(?:" + "|".join(re.escape(material) for material in sorted({
        material for packs in clothing_vocab.CONCEPT_PACKS.values() for pack in packs.values()
        for material in pack.get("palette", {}).get("materials", []) if material
    })) + r")\b", re.IGNORECASE,
)


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


def _trace_binding(inputs) -> str:
    from .realization_evidence import _canonical, _json_input
    return hashlib.sha256(_canonical(_json_input(inputs))).hexdigest()


def _trace_part(part_id, field, selected, text, catalog_key, producer):
    from .realization_evidence import ProducerPart, SourceRef, text_sha256
    raw = selected if isinstance(selected, str) else json.dumps(selected, ensure_ascii=False, separators=(",", ":"))
    if field == "character_palette.colors":
        catalog_key = None
    return ProducerPart(part_id, SourceRef("clothing", producer, field, catalog_key, text_sha256(raw)), text)


def _make_trace(producer, binding, raw, emitted, parts, emitted_ids, omitted, constructor_id):
    from .realization_evidence import ProducerTrace, runtime_source_identity, text_sha256
    return ProducerTrace("exact_renderer_replay", producer, runtime_source_identity(), binding,
                         text_sha256(raw), text_sha256(emitted), tuple(parts), tuple(emitted_ids),
                         tuple(omitted), constructor_id)


def _assemble_item_description(selected_items, *, color="", material="", pattern="", style="", details_list=()):
    adjectives = [x for x in [color, pattern, material, style] if x]
    adj_str = " ".join(adjectives)
    items_str = " and ".join(selected_items)
    main_part = f"{adj_str} {items_str}" if adj_str else items_str
    variant_signature = build_variant_signature([
        *selected_items, color, material, pattern, style, *details_list,
    ])
    if details_list:
        return f"{main_part}, with {', '.join(details_list)}", variant_signature
    return main_part, variant_signature


def _build_item_description(rng, concept_data, char_colors, loc, *, with_trace=False, catalog_key=None):
    producer = "build_item_description"
    binding = None
    parts, omitted = [], []
    emitted = set()
    rng_state = None
    if with_trace and callable(getattr(rng, "getstate", None)):
        try:
            rng_state = rng.getstate()
        except NotImplementedError:
            pass
    if rng_state is not None:
        binding = _trace_binding({"concept_data": concept_data,
            "choice_field_order": list(concept_data.get("choices", {})),
            "char_colors": char_colors, "loc": loc, "catalog_key": catalog_key,
            "rng_type": f"{type(rng).__module__}.{type(rng).__qualname__}", "rng_state": rng_state})

    def record(part_id, field, selected, text):
        if binding is not None:
            parts.append(_trace_part(part_id, field, selected, text, catalog_key, producer))
            if text:
                emitted.add(part_id)
            else:
                omitted.append((part_id, "clothing.empty_selected_part"))

    selected_items = []
    choices_dict = concept_data.get("choices", {})
    for index, (field, options) in enumerate(choices_dict.items()):
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
        record(f"choice.{index}", f"choices.{field}", choice, item_str)

    palette = concept_data.get("palette", {})

    def pick_palette(key: str) -> str:
        if key == "colors" and char_colors and rng.random() < 0.60:
            selected = rng.choice(char_colors)
            record("color", "character_palette.colors", selected, selected)
            return selected
        default_prob = clothing_vocab.PALETTE_DEFAULT_PROBABILITIES.get(key, 0.5)
        if key in palette and palette[key] and rng.random() < default_prob:
            selected = rng.choice(palette[key])
            record({"colors": "color", "materials": "material", "patterns": "pattern", "styles": "style"}[key],
                   f"palette.{key}", selected, selected)
            return selected
        return ""

    color = pick_palette("colors")
    material = pick_palette("materials")
    # Garment wording owns its material; a shared optional prefix must not
    # contradict it. Consume the draw first so all later choices remain stable.
    if material and any(_GARMENT_MATERIAL.search(item) for item in selected_items):
        material = ""
        emitted.discard("material")
        if binding is not None:
            omitted.append(("material", "clothing.material_owned_by_garment"))
    pattern = pick_palette("patterns")
    style = pick_palette("styles")
    embellishments = palette.get("embellishments", [])
    opt_details = concept_data.get("optional_details", [])
    details_list = []
    embellishment_prob = max(0.70, float(getattr(clothing_vocab, "EMBELLISHMENT_DETAIL_PROBABILITY", 0.55)))
    optional_detail_prob = max(0.60, float(getattr(clothing_vocab, "OPTIONAL_DETAIL_PROBABILITY", 0.45)))
    state_detail_prob = max(0.38, float(getattr(clothing_vocab, "STATE_DETAIL_PROBABILITY", 0.30)))
    if embellishments and rng.random() < embellishment_prob:
        detail = rng.choice(embellishments)
        details_list.append(detail)
        record("embellishment", "palette.embellishments", detail, detail)
    if opt_details and rng.random() < optional_detail_prob:
        detail = rng.choice(opt_details)
        details_list.append(detail)
        record("optional_detail", "optional_details", detail, detail)
    states = concept_data.get("states", [])
    if states and rng.random() < state_detail_prob:
        state_detail = rng.choice(states)
        record("state", "states", state_detail, state_detail)
        if location_allows_state_detail(loc, state_detail):
            details_list.append(state_detail)
        elif binding is not None:
            emitted.discard("state")
            omitted.append(("state", "clothing.state_location_disallowed:" + state_detail_rule(state_detail)["family"]))

    text, signature = _assemble_item_description(selected_items, color=color, material=material,
        pattern=pattern, style=style, details_list=details_list)
    trace = None
    if binding is not None:
        order = ["color", "pattern", "material", "style",
                 *(f"choice.{index}" for index in range(len(choices_dict))), "embellishment", "optional_detail", "state"]
        trace = _make_trace(producer, binding, text, text, parts,
                            [part_id for part_id in order if part_id in emitted], omitted, "clothing.item/v1")
    return text, signature, trace


def build_item_description(rng, concept_data: dict[str, Any], char_colors=None, loc: str = "") -> tuple[str, str]:
    return _build_item_description(rng, concept_data, char_colors, loc)[:2]


def build_item_description_with_trace(rng, concept_data: dict[str, Any], char_colors=None, loc: str = "", *, catalog_key=None):
    """Preserve the two legacy values and add immutable evidence when RNG state exists."""
    return _build_item_description(rng, concept_data, char_colors, loc, with_trace=True, catalog_key=catalog_key)


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
    *,
    trace_sink=None,
):
    rng = random.Random(mix_seed(seed, "cloth" if attempt_index == 0 else f"cloth:{attempt_index}"))
    parts, emitted_ids, omitted = [], [], []
    binding = None
    if trace_sink is not None:
        binding = _trace_binding({"theme_key": theme_key, "seed": seed, "outfit_mode": outfit_mode,
            "outerwear_chance": outerwear_chance, "character_palette": character_palette,
            "recent_packs": sorted(recent_packs or []), "recent_types": sorted(recent_types or []),
            "recent_outerwear": sorted(recent_outerwear or []), "recent_signatures": sorted(recent_signatures or []),
            "attempt_index": attempt_index, "loc": loc, "rng_state": rng.getstate()})

    def record(part_id, field, selected, text, catalog_key, *, emit=True):
        if binding is not None:
            parts.append(_trace_part(part_id, field, selected, text, catalog_key, "render_clothing_candidate"))
            if emit and text:
                emitted_ids.append(part_id)

    raw_key = str(theme_key).lower().strip()
    char_colors = [c.strip() for c in str(character_palette).split(",") if c.strip()] if character_palette else []
    theme = resolve_clothing_theme(raw_key) or raw_key
    packs_map = clothing_vocab.THEME_TO_PACKS.get(theme)
    if not packs_map:
        raw = f"{theme_key} layered top and practical trousers"
        prompt = sanitize_text(raw)
        debug = {"theme": theme, "base_pack": "", "chosen_type": "", "outerwear_pack": "", "objects": []}
        if trace_sink is not None:
            record("fallback", "fallback.template", raw, raw, None)
            trace_sink(_make_trace("render_clothing_candidate", binding, raw, prompt, parts,
                                  emitted_ids, omitted, "clothing.candidate.fallback/v1"))
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
                if trace_sink is None:
                    item_description, variant_signature = build_item_description(rng, concept_data, char_colors, loc=loc)
                else:
                    item_description, variant_signature, item_trace = build_item_description_with_trace(
                        rng, concept_data, char_colors, loc=loc, catalog_key=f"{chosen_type}:{chosen_pack_name}")
                    record("base.selection", f"THEME_TO_PACKS.{theme}.{chosen_type}", chosen_pack_name,
                           chosen_pack_name, f"{chosen_type}:{chosen_pack_name}", emit=False)
                    omitted.append(("base.selection", "clothing.selection_metadata"))
                    from dataclasses import replace
                    parts.extend(replace(part, part_id="base." + part.part_id) for part in item_trace.parts)
                    emitted_ids.extend("base." + part_id for part_id in item_trace.emitted_part_ids)
                    omitted.extend(("base." + part_id, rule) for part_id, rule in item_trace.omitted_parts)
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
            record("outer.selection", f"THEME_TO_PACKS.{theme}.outerwear", outer_name,
                   outer_name, f"outerwear:{outer_name}", emit=False)
            if binding is not None:
                omitted.append(("outer.selection", "clothing.selection_metadata"))
            outer_palette = outer_data.get("palette", {})
            outer_colors = outer_palette.get("colors", [])
            outer_choices = outer_data.get("choices", {}).get("outerwear", [])
            outer_description = ""
            chosen_color = ""
            chosen_outer = ""
            if char_colors and rng.random() < 0.7:
                chosen_color = rng.choice(char_colors)
                record("outer.color", "character_palette.colors", chosen_color, chosen_color, f"outerwear:{outer_name}")
            elif outer_colors:
                chosen_color = rng.choice(outer_colors)
                record("outer.color", "palette.colors", chosen_color, chosen_color, f"outerwear:{outer_name}")
            if chosen_color:
                outer_description += f"{chosen_color} "
            if outer_choices:
                chosen_outer = rng.choice(outer_choices)
                outer_description += f"{chosen_outer}"
                record("outer.choice", "choices.outerwear", chosen_outer, chosen_outer, f"outerwear:{outer_name}")
            if outfit_mode == "outerwear_only":
                final_parts.append(outer_description)
            else:
                final_parts.append(f"wearing a {outer_description} over it")
            decision["outerwear_pack"] = outer_name
            decision["outerwear_variant"] = build_variant_signature([chosen_color, chosen_outer])

    raw_prompt = ", ".join(final_parts)
    prompt = sanitize_text(raw_prompt)
    decision["objects"] = sorted(extract_object_flags(prompt))
    decision["signature"] = clothing_signature_digest(clothing_signature_from_decision(decision))
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
    if trace_sink is not None:
        trace_sink(_make_trace("render_clothing_candidate", binding, raw_prompt, prompt, parts,
                              emitted_ids, omitted, "clothing.candidate/v1"))
    return prompt, decision
