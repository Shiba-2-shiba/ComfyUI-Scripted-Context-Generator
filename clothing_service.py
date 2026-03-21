from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Dict, List


ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "vocab", "data")

_CLOTHING_THEME_ALIASES = {
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
    "street casual": "street_casual",
    "steampunk inventor": "steampunk_inventor",
    "sleek evening gown": "sleek_evening_gown",
    "library girl": "library_girl",
}


def _load_json(filename: str):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_key(value: str) -> str:
    return str(value or "").strip().lower().replace("-", " ")


def _candidate_variants(value: str) -> List[str]:
    raw = _normalize_key(value)
    if not raw:
        return []
    variants = [
        raw,
        raw.replace("_", " "),
        raw.replace(" ", "_"),
    ]
    deduped: List[str] = []
    seen = set()
    for variant in variants:
        if variant not in seen:
            seen.add(variant)
            deduped.append(variant)
    return deduped


@lru_cache(maxsize=1)
def load_clothing_theme_map() -> Dict[str, dict]:
    return _load_json("clothing_theme_map.json")


def resolve_clothing_theme(raw: str) -> str:
    theme_map = load_clothing_theme_map()
    for candidate in _candidate_variants(raw):
        if candidate in theme_map:
            return candidate
        mapped = _CLOTHING_THEME_ALIASES.get(candidate)
        if mapped and mapped in theme_map:
            return mapped
    return ""
