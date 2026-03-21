from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Dict, List

from vocab.loc_tag_builder import build_loc_tag_map


ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "vocab", "data")


def _load_json(filename: str):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_alias_targets(value) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        target = str(value).strip()
        return [target] if target else []
    return []


def _load_alias_layer_json(filename: str) -> Dict[str, List[str]]:
    data = _load_json(filename)
    aliases = data.get("aliases", data) if isinstance(data, dict) else {}
    if not isinstance(aliases, dict):
        return {}
    return {
        str(key).strip().lower(): _normalize_alias_targets(value)
        for key, value in aliases.items()
        if str(key).strip()
    }


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
def load_background_packs() -> Dict[str, dict]:
    return _load_json("background_packs.json")


@lru_cache(maxsize=1)
def load_background_alias_overrides() -> Dict[str, List[str]]:
    data = _load_json("background_alias_overrides.json")
    return {str(key).strip().lower(): [str(item) for item in value] for key, value in data.items()}


@lru_cache(maxsize=1)
def load_legacy_fallback_location_alias_map() -> Dict[str, List[str]]:
    data = _load_json("background_loc_tag_map.json")
    return {str(key).strip().lower(): [str(item) for item in value] for key, value in data.items()}


@lru_cache(maxsize=1)
def build_primary_location_alias_map() -> Dict[str, List[str]]:
    auto_map = build_loc_tag_map(load_background_packs(), load_background_alias_overrides())
    return {
        str(key).strip().lower(): [str(item) for item in value]
        for key, value in auto_map.items()
    }


@lru_cache(maxsize=1)
def load_canonical_location_alias_map() -> Dict[str, List[str]]:
    alias_map = dict(build_primary_location_alias_map())
    alias_map.update(_load_alias_layer_json("loc_aliases_canonical.json"))
    return alias_map


@lru_cache(maxsize=1)
def load_legacy_location_alias_map() -> Dict[str, List[str]]:
    return _load_alias_layer_json("loc_aliases_legacy.json")


@lru_cache(maxsize=1)
def load_fallback_location_alias_map() -> Dict[str, List[str]]:
    alias_map = dict(load_legacy_fallback_location_alias_map())
    alias_map.update(_load_alias_layer_json("loc_aliases_fallback.json"))
    return alias_map


@lru_cache(maxsize=1)
def build_location_alias_layers() -> Dict[str, Dict[str, List[str]]]:
    return {
        "canonical": load_canonical_location_alias_map(),
        "legacy": load_legacy_location_alias_map(),
        "fallback": load_fallback_location_alias_map(),
    }


@lru_cache(maxsize=1)
def build_location_alias_map() -> Dict[str, List[str]]:
    alias_map = dict(load_canonical_location_alias_map())
    for key, value in load_legacy_location_alias_map().items():
        alias_map.setdefault(key, list(value))
    for key, value in load_fallback_location_alias_map().items():
        alias_map.setdefault(key, list(value))
    return alias_map


def resolve_location(raw: str) -> Dict[str, str]:
    packs = load_background_packs()
    alias_layers = build_location_alias_layers()
    canonical_alias_map = alias_layers["canonical"]
    legacy_alias_map = alias_layers["legacy"]
    fallback_alias_map = alias_layers["fallback"]
    canonical_file_alias_map = _load_alias_layer_json("loc_aliases_canonical.json")
    legacy_file_alias_map = _load_alias_layer_json("loc_aliases_legacy.json")
    fallback_file_alias_map = _load_alias_layer_json("loc_aliases_fallback.json")

    # Resolution order is explicit:
    # 1. exact canonical pack key
    # 2. canonical normalization aliases
    # 3. legacy compatibility aliases
    # 4. semantic fallback aliases
    for candidate in _candidate_variants(raw):
        if candidate in packs:
            return {
                "input_key": str(raw or ""),
                "canonical_key": candidate,
                "matched_alias": candidate,
                "source": "pack_key",
                "layer": "canonical",
            }

        if candidate in canonical_alias_map:
            matches = canonical_alias_map[candidate]
            if matches:
                if candidate in canonical_file_alias_map:
                    source = "canonical_alias"
                else:
                    source = "override" if candidate in load_background_alias_overrides() else "pack_alias"
                return {
                    "input_key": str(raw or ""),
                    "canonical_key": str(matches[0]),
                    "matched_alias": candidate,
                    "source": source,
                    "layer": "canonical",
                }

        if candidate in legacy_alias_map:
            matches = legacy_alias_map[candidate]
            if matches:
                return {
                    "input_key": str(raw or ""),
                    "canonical_key": str(matches[0]),
                    "matched_alias": candidate,
                    "source": "legacy_alias",
                    "layer": "legacy",
                }

        if candidate in fallback_alias_map:
            matches = fallback_alias_map[candidate]
            if matches:
                source = "fallback_alias" if candidate in fallback_file_alias_map else "legacy_fallback"
                return {
                    "input_key": str(raw or ""),
                    "canonical_key": str(matches[0]),
                    "matched_alias": candidate,
                    "source": source,
                    "layer": "fallback",
                }

    return {
        "input_key": str(raw or ""),
        "canonical_key": "",
        "matched_alias": "",
        "source": "",
        "layer": "",
    }


def resolve_location_key(raw: str) -> str:
    return resolve_location(raw).get("canonical_key", "")


def location_alias_collisions() -> Dict[str, List[str]]:
    collisions: Dict[str, List[str]] = {}
    alias_sources: Dict[str, List[str]] = {}
    for pack_key, pack_data in load_background_packs().items():
        for alias in [pack_key, *(pack_data.get("aliases", []) or [])]:
            normalized = str(alias).strip().lower()
            alias_sources.setdefault(normalized, [])
            if pack_key not in alias_sources[normalized]:
                alias_sources[normalized].append(pack_key)
    overrides = load_background_alias_overrides()
    for alias, pack_keys in alias_sources.items():
        if len(pack_keys) > 1 and alias not in overrides:
            collisions[alias] = pack_keys
    return collisions
