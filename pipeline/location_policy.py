from __future__ import annotations

import re
from typing import Sequence

try:
    from ..object_focus_service import is_symbolic_object_text
except ImportError:
    from object_focus_service import is_symbolic_object_text


DAILY_LIFE_LOCS = {
    "school_classroom", "school_rooftop", "school_library", "modern_office",
    "boardroom", "office_elevator", "commuter_transport", "street_cafe",
    "cozy_bookstore", "shopping_mall_atrium", "fashion_boutique",
    "bedroom_boudoir", "clean_modern_kitchen",
    "cozy_living_room", "rainy_bus_stop", "suburban_neighborhood",
    "rural_town_street", "picnic_park", "illuminated_park", "winter_street",
    "japanese_garden", "tea_room",
}
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
TIME_DARK_HINTS = ("night", "midnight", "twilight", "dusk", "late night", "stormy", "holiday night")
TIME_BRIGHT_HINTS = (
    "morning", "midday", "noon", "daytime", "daylight", "sunrise",
    "sunlight", "sunlit", "lunch break",
)
TIME_BEDTIME_HINTS = ("before sleeping", "before heading to bed", "before bed", "getting ready for bed")
TIME_LATE_HINTS = TIME_DARK_HINTS + ("evening",) + TIME_BEDTIME_HINTS
TIME_MORNING_HINTS = ("morning", "sunrise", "breakfast")
TIME_AFTERNOON_HINTS = ("afternoon",)
WEATHER_RARE_HINTS = ("rain", "snow", "storm", "fog", "acid", "winter")
LIGHTING_HINTS = ("light", "glow", "fluorescent", "ambient", "sun", "spotlight", "daylight", "hour")
FX_ENERGY_FAMILY_PATTERNS = (
    re.compile(r"\benergy\b", re.IGNORECASE),
    re.compile(r"\benergetic\b", re.IGNORECASE),
    re.compile(r"\bexcitement\b", re.IGNORECASE),
    re.compile(r"\bexcited\b", re.IGNORECASE),
    re.compile(r"\bquick\s+motion\b", re.IGNORECASE),
    re.compile(r"\bparty\s+vibe\b", re.IGNORECASE),
)
LOCATION_CORE_DENY_TERMS = {
    "recording_studio": ("mixing console",),
}


def is_symbolic_prop(text: str) -> bool:
    return is_symbolic_object_text(text)


def props_sampling_policy(props_opts: Sequence[str]) -> tuple[float, float]:
    include_prob = 0.8
    second_prop_prob = 0.45
    if len(props_opts) <= 3:
        include_prob = 0.62
        second_prop_prob = 0.20
    if any(is_symbolic_prop(prop) for prop in props_opts):
        include_prob = max(0.50, include_prob - 0.12)
        second_prop_prob = max(0.10, second_prop_prob - 0.10)
    return include_prob, second_prop_prob


def is_disallowed_fx_segment(text: str) -> bool:
    low = str(text).lower()
    if "snowflake" in low or "sparkling eyes" in low:
        return False
    return any(pattern.search(low) for pattern in FX_DENY_PATTERNS)


def filter_fx_candidates(options: Sequence[str]) -> list[str]:
    if not options:
        return []
    filtered = []
    seen = set()
    for item in options:
        if not item:
            continue
        item_text = str(item)
        if is_disallowed_fx_segment(item_text):
            continue
        if item_text in seen:
            continue
        filtered.append(item_text)
        seen.add(item_text)
    return filtered


def filter_semantic_redundant_fx(options: Sequence[str], context_text: str) -> list[str]:
    def has_energy_excitement_family(text: str) -> bool:
        normalized = re.sub(r"[_-]+", " ", str(text or ""))
        return any(pattern.search(normalized) for pattern in FX_ENERGY_FAMILY_PATTERNS)

    if not has_energy_excitement_family(context_text):
        return list(options)
    return [option for option in options if not has_energy_excitement_family(option)]


def filter_location_core_options(loc_tag: str, options: Sequence[str]) -> list[str]:
    denied = LOCATION_CORE_DENY_TERMS.get(str(loc_tag or "").strip().lower(), ())
    if not denied:
        return list(options)
    return [
        option for option in options
        if not any(term in str(option).lower() for term in denied)
    ]


def is_daily_life_loc(loc_tag: str) -> bool:
    return str(loc_tag).lower().strip() in DAILY_LIFE_LOCS


def prefer_bright_time_options(options: Sequence[str]) -> list[str]:
    if not options:
        return []
    preferred = [
        option for option in options
        if not any(token in str(option).lower() for token in TIME_DARK_HINTS)
    ]
    return preferred or list(options)


def filter_time_options_for_context(options: Sequence[str], context_text: str) -> list[str]:
    if not options:
        return []
    lowered_context = str(context_text).lower()
    filtered = list(options)
    context_is_morning = any(token in lowered_context for token in TIME_MORNING_HINTS)
    context_is_afternoon = any(token in lowered_context for token in TIME_AFTERNOON_HINTS)
    if context_is_morning != context_is_afternoon:
        conflicting_phase = TIME_AFTERNOON_HINTS if context_is_morning else TIME_MORNING_HINTS
        phase_filtered = [
            option for option in filtered
            if not any(token in str(option).lower() for token in conflicting_phase)
        ]
        if phase_filtered:
            filtered = phase_filtered
    context_is_late = any(token in lowered_context for token in TIME_LATE_HINTS)
    context_is_bright = any(token in lowered_context for token in TIME_BRIGHT_HINTS)
    if context_is_late == context_is_bright:
        return filtered

    conflicting_hints = TIME_BRIGHT_HINTS if context_is_late else TIME_LATE_HINTS
    return [
        option for option in filtered
        if not any(token in str(option).lower() for token in conflicting_hints)
    ]


def split_weather_options(options: Sequence[str]) -> tuple[list[str], list[str]]:
    if not options:
        return [], []
    normal = []
    rare = []
    for option in options:
        option_text = str(option).lower()
        if any(token in option_text for token in WEATHER_RARE_HINTS):
            rare.append(option)
        else:
            normal.append(option)
    return normal, rare


def contains_lighting_hint(text: str) -> bool:
    lowered = str(text).lower()
    return any(token in lowered for token in LIGHTING_HINTS)


def filter_off_mode_options(options: Sequence[str], fallback_all: bool = True) -> list[str]:
    if not options:
        return []
    filtered = [option for option in options if not contains_lighting_hint(option)]
    if filtered:
        return filtered
    return list(options) if fallback_all else []
