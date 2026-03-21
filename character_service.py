from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Dict, List

if __package__:
    from .clothing_service import resolve_clothing_theme
    from .scene_service import load_scene_compatibility
else:
    from clothing_service import resolve_clothing_theme
    from scene_service import load_scene_compatibility


ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "vocab", "data")

_PREFERRED_ARCHETYPE_BY_COSTUME = {
    "school_uniform": "student",
    "office_lady": "business girl",
    "gothic_lolita": "gothic girl",
    "gym_workout": "gym girl",
    "fantasy_battle": "fantasy warrior",
    "mori_natural": "mori girl",
    "cozy_cafe": "cafe customer",
    "traditional_japanese": "shrine maiden",
    "rock_concert": "rock singer",
    "cyberpunk_night": "cyberpunk girl",
    "beach_resort": "vacation girl",
    "scifi_space": "space pilot",
    "steampunk": "inventor girl",
    "steampunk_inventor": "inventor girl",
    "library_girl": "library girl",
}


def _load_json(filename: str):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_text(value: str) -> str:
    return str(value or "").strip()


def _canonical_lookup(value: str) -> str:
    return _normalize_text(value).casefold()


def _character_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", _canonical_lookup(value))
    return normalized.strip("_")


def _tokenize(value: str) -> List[str]:
    return [token for token in re.findall(r"[a-z0-9]+", _canonical_lookup(value)) if token]


def _normalize_costume(value: str) -> str:
    raw = _normalize_text(value)
    return resolve_clothing_theme(raw) or raw


@lru_cache(maxsize=1)
def load_character_profiles() -> Dict[str, dict]:
    data = _load_json("character_profiles.json")
    return data.get("characters", {})


def _compatibility_characters() -> Dict[str, dict]:
    return load_scene_compatibility().get("characters", {})


def _resolve_profile_key(raw: str) -> str:
    profiles = load_character_profiles()
    lookup = {_canonical_lookup(key): key for key in profiles}
    return lookup.get(_canonical_lookup(raw), "")


def _resolve_compatibility_key(raw: str) -> str:
    characters = _compatibility_characters()
    lookup = {_canonical_lookup(key): key for key in characters}
    return lookup.get(_canonical_lookup(raw), "")


def _compatibility_candidates_for_profile(profile_key: str) -> List[str]:
    profiles = load_character_profiles()
    characters = _compatibility_characters()
    profile = profiles.get(profile_key, {})
    if not profile:
        return []

    costume = _normalize_costume(profile.get("default_costume", ""))
    profile_tokens = set(_tokenize(profile_key))
    profile_tokens.update(_tokenize(profile.get("personality", "")))

    candidates: List[tuple[int, str]] = []
    for compat_key, compat_info in characters.items():
        compat_costume = _normalize_costume(compat_info.get("default_costume", ""))
        if costume and compat_costume != costume:
            continue
        score = 1
        compat_tokens = set(_tokenize(compat_key))
        score += len(profile_tokens & compat_tokens) * 10
        if compat_key == _PREFERRED_ARCHETYPE_BY_COSTUME.get(costume, ""):
            score += 100
        candidates.append((score, compat_key))

    candidates.sort(key=lambda item: (-item[0], len(item[1]), item[1]))
    return [key for _score, key in candidates]


def resolve_character(raw: str = "", source_subj_key: str = "", character_name: str = "") -> Dict[str, object]:
    profiles = load_character_profiles()
    compatibility = _compatibility_characters()

    resolved_profile_key = ""
    resolved_compatibility_key = ""
    warnings: List[str] = []

    for candidate in (character_name, raw):
        resolved_profile_key = _resolve_profile_key(candidate)
        if resolved_profile_key:
            break

    for candidate in (source_subj_key, raw, character_name):
        resolved_compatibility_key = _resolve_compatibility_key(candidate)
        if resolved_compatibility_key:
            break

    profile = profiles.get(resolved_profile_key, {})
    compatibility_info = compatibility.get(resolved_compatibility_key, {})
    compatibility_keys: List[str] = []

    if resolved_profile_key:
        compatibility_keys = _compatibility_candidates_for_profile(resolved_profile_key)
        if not resolved_compatibility_key and compatibility_keys:
            resolved_compatibility_key = compatibility_keys[0]
            compatibility_info = compatibility.get(resolved_compatibility_key, {})
        elif not resolved_compatibility_key:
            warnings.append(f"No compatibility archetype found for profile '{resolved_profile_key}'")

    visuals = profile.get("visual_traits", {}) if isinstance(profile, dict) else {}
    profile_costume = _normalize_text(profile.get("default_costume", "")) if isinstance(profile, dict) else ""
    compatibility_costume = _normalize_text(compatibility_info.get("default_costume", "")) if isinstance(compatibility_info, dict) else ""
    default_costume = profile_costume or compatibility_costume
    resolved_default_costume = _normalize_costume(default_costume)
    if default_costume and not resolved_default_costume:
        warnings.append(f"Unresolved default costume '{default_costume}'")

    display_name = resolved_profile_key or resolved_compatibility_key or _normalize_text(raw) or _normalize_text(character_name)
    personality = _normalize_text(profile.get("personality", "")) if isinstance(profile, dict) else ""
    palette = profile.get("color_palette", []) if isinstance(profile, dict) else []
    if not isinstance(palette, list):
        palette = []
    palette = [str(item) for item in palette]
    compatibility_tags = compatibility_info.get("tags", []) if isinstance(compatibility_info, dict) else []
    if not isinstance(compatibility_tags, list):
        compatibility_tags = []
    compatibility_tags = [str(item) for item in compatibility_tags]

    return {
        "character_id": _character_id(display_name),
        "display_name": display_name,
        "profile_key": resolved_profile_key,
        "compatibility_key": resolved_compatibility_key,
        "compatibility_keys": compatibility_keys or ([resolved_compatibility_key] if resolved_compatibility_key else []),
        "default_costume": resolved_default_costume or default_costume,
        "personality": personality,
        "hair_color": _normalize_text(visuals.get("hair_color", "")),
        "hair_style": _normalize_text(visuals.get("hair_style", "")),
        "eye_color": _normalize_text(visuals.get("eye_color", "")),
        "palette": palette,
        "visual_traits": visuals if isinstance(visuals, dict) else {},
        "compatibility_tags": compatibility_tags,
        "warnings": warnings,
    }


def resolve_character_key(raw: str) -> str:
    resolved = resolve_character(raw=raw, character_name=raw)
    if resolved.get("profile_key"):
        return str(resolved["profile_key"])
    return str(resolved.get("compatibility_key", ""))


def unresolved_character_costumes() -> List[str]:
    unresolved = []
    for profile in load_character_profiles().values():
        costume = str(profile.get("default_costume", "")).strip()
        if costume and not resolve_clothing_theme(costume):
            unresolved.append(costume)
    return sorted(set(unresolved))
