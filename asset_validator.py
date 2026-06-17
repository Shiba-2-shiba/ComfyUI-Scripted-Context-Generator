from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, List, Sequence

from character_service import load_character_profiles
from clothing_service import load_clothing_theme_map, resolve_clothing_theme
from core.semantic_policy import find_banned_term_matches
from location_service import load_background_alias_overrides, load_background_packs
from object_focus_service import OBJECT_TOKENS
from scene_service import load_scene_compatibility
from vocab.semantic_space import validate_axis_payload


def _iter_string_paths(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path or "$", value
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            next_path = f"{path}[{index}]" if path else f"[{index}]"
            yield from _iter_string_paths(item, next_path)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            next_path = f"{path}.{key}" if path else str(key)
            yield from _iter_string_paths(item, next_path)


_TARGETED_BANNED_ASSETS = (
    "background_packs.json",
    "background_defaults.json",
    "clothing_packs.json",
    "garnish_base_vocab.json",
    "garnish_exclusive_groups.json",
    "garnish_micro_actions.json",
    "semantic_epig_config.json",
)
_SEMANTIC_CONFIG_FILE = "semantic_epig_config.json"
_SEMANTIC_DOMAINS = {
    "action",
    "object_relation",
    "location_scene",
    "clothing_tpo",
    "personality_behavior",
}
_SEMANTIC_MODES = {"off", "passive", "active"}
_SEMANTIC_AXIS_ASSETS = (
    "action_semantic_profiles.json",
    "action_slot_descriptors.json",
    "location_axis_profiles.json",
    "staging_axis_descriptors.json",
    "clothing_axis_profiles.json",
    "personality_behavior_profiles.json",
)
_SEMANTIC_BANNED_ASSETS = _SEMANTIC_AXIS_ASSETS + (
    "object_relation_profiles.json",
)
_OBJECT_RELATION_FILE = "object_relation_profiles.json"
ALLOWED_OBJECT_RELATION_ROLES = {
    "posture",
    "hand_action",
    "gaze_target",
    "object_relation",
    "object_state",
    "optional_micro_action",
}
_ALLOWED_UNCONNECTED_PROFILES = {
    "Diana (Noble)",
    "Hana (Idol)",
    "Jasmine (Dancer)",
    "Nina (Tech)",
    "Penelope (Steam)",
    "Rin (Cool)",
    "Violet (Shy)",
    "Zara (Exotic)",
}
_ALIAS_LAYER_FILES = {
    "canonical": "loc_aliases_canonical.json",
    "legacy": "loc_aliases_legacy.json",
    "fallback": "loc_aliases_fallback.json",
}
_DEPRECATED_ALIAS_FILE = "loc_aliases.json"


def _data_dir() -> Path:
    return Path(__file__).resolve().parent / "vocab" / "data"


def _read_json_asset(filename: str) -> Any:
    return json.loads((_data_dir() / filename).read_text(encoding="utf-8"))


def _asset_exists(filename: str) -> bool:
    return (_data_dir() / filename).exists()


def _normalize_alias_targets(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = str(value).strip()
        return [text] if text else []
    return []


def load_alias_layer_asset(layer_name: str) -> dict[str, Any]:
    filename = _ALIAS_LAYER_FILES[layer_name]
    payload = _read_json_asset(filename)
    aliases = payload.get("aliases", {}) if isinstance(payload, dict) else {}
    notes = payload.get("notes", {}) if isinstance(payload, dict) else {}
    return {
        "filename": filename,
        "layer": str(payload.get("layer", "")) if isinstance(payload, dict) else "",
        "schema_version": str(payload.get("schema_version", "")) if isinstance(payload, dict) else "",
        "aliases": {
            str(key).strip().lower(): _normalize_alias_targets(value)
            for key, value in aliases.items()
            if str(key).strip()
        },
        "notes": {
            str(key).strip().lower(): str(value).strip()
            for key, value in notes.items()
            if str(key).strip()
        },
    }


def find_banned_asset_terms(text: str) -> list[tuple[str, str]]:
    return find_banned_term_matches(text, ignore_hyphenated_body_type=True)


def validate_banned_terms_in_asset(asset_name: str, data: Any) -> list[str]:
    warnings: list[str] = []
    for path, text in _iter_string_paths(data):
        for domain, term in find_banned_asset_terms(text):
            warnings.append(
                f"{asset_name}:{path} contains banned {domain} term '{term}' in '{text}'"
            )
    return warnings


def validate_location_aliases(
    background_packs: dict[str, Any],
    alias_overrides: dict[str, Sequence[str]] | None = None,
) -> list[str]:
    warnings: list[str] = []
    alias_overrides = alias_overrides or {}
    alias_owners: dict[str, list[str]] = {}

    for pack_key, pack_data in background_packs.items():
        seen_local = set()
        aliases = list(pack_data.get("aliases", []) or [])
        for index, alias in enumerate(aliases):
            normalized = str(alias).strip().lower()
            if not normalized:
                warnings.append(f"background_packs:{pack_key}.aliases[{index}] is empty")
                continue
            if normalized in seen_local:
                warnings.append(
                    f"background_packs:{pack_key}.aliases has duplicate alias '{normalized}'"
                )
                continue
            seen_local.add(normalized)
            alias_owners.setdefault(normalized, [])
            if pack_key not in alias_owners[normalized]:
                alias_owners[normalized].append(pack_key)

    for alias, owners in alias_owners.items():
        if len(owners) > 1 and alias not in {str(key).strip().lower() for key in alias_overrides}:
            warnings.append(
                f"background_packs alias '{alias}' is shared by multiple packs: {', '.join(sorted(owners))}"
            )

    for alias, targets in alias_overrides.items():
        normalized = str(alias).strip().lower()
        if not normalized:
            warnings.append("background_alias_overrides contains an empty alias key")
        if not targets:
            warnings.append(f"background_alias_overrides:{alias} has no target packs")

    return warnings


def validate_alias_layer_assets(
    background_packs: dict[str, Any],
    layer_assets: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    warnings: list[str] = []
    layer_assets = layer_assets or {
        layer_name: load_alias_layer_asset(layer_name)
        for layer_name in _ALIAS_LAYER_FILES
    }
    pack_keys = {str(key).strip().lower() for key in background_packs}

    for layer_name, asset in layer_assets.items():
        filename = asset["filename"]
        aliases = asset.get("aliases", {})
        notes = asset.get("notes", {})

        if asset.get("layer") != layer_name:
            warnings.append(f"{filename} layer field must be '{layer_name}'")
        if not asset.get("schema_version"):
            warnings.append(f"{filename} missing schema_version")

        for alias, targets in aliases.items():
            if not targets:
                warnings.append(f"{filename}:{alias} has no target locations")
                continue

            for target in targets:
                normalized_target = str(target).strip().lower()
                if normalized_target not in pack_keys:
                    warnings.append(
                        f"{filename}:{alias} targets unknown canonical location '{target}'"
                    )

            if alias not in notes:
                warnings.append(f"{filename}:{alias} is missing migration note")

            if layer_name == "canonical" and alias in pack_keys:
                normalized_target = str(targets[0]).strip().lower()
                if normalized_target != alias:
                    warnings.append(
                        f"{filename}:{alias} must not remap canonical pack key to '{targets[0]}'"
                    )

    deprecated_payload = _read_json_asset(_DEPRECATED_ALIAS_FILE)
    deprecated_aliases = deprecated_payload.get("aliases", {}) if isinstance(deprecated_payload, dict) else {}
    if deprecated_aliases:
        warnings.append(f"{_DEPRECATED_ALIAS_FILE} should be empty after alias-layer migration")

    return warnings


def validate_character_assets(
    character_profiles: dict[str, Any],
    compatibility_characters: dict[str, Any],
    clothing_theme_map: dict[str, Any],
    allow_unconnected_profiles: Sequence[str] | None = None,
) -> list[str]:
    warnings: list[str] = []
    allowed = {str(item) for item in (allow_unconnected_profiles or [])}
    compat_by_costume: dict[str, list[str]] = {}

    for compat_key, compat_info in compatibility_characters.items():
        costume = str(compat_info.get("default_costume", "")).strip()
        if costume:
            compat_by_costume.setdefault(resolve_clothing_theme(costume) or costume, []).append(compat_key)

    for profile_name, profile in character_profiles.items():
        costume = str(profile.get("default_costume", "")).strip()
        resolved_costume = resolve_clothing_theme(costume) or costume
        if costume and resolved_costume not in clothing_theme_map:
            warnings.append(
                f"character_profiles:{profile_name} has unresolved default costume '{costume}'"
            )
        if (
            resolved_costume
            and not compat_by_costume.get(resolved_costume)
            and profile_name not in allowed
        ):
            warnings.append(
                f"character_profiles:{profile_name} is not connected to any scene compatibility archetype for costume '{resolved_costume}'"
            )

    return warnings


def validate_semantic_epig_config(payload: Any | None = None) -> list[str]:
    warnings: list[str] = []
    data = _read_json_asset(_SEMANTIC_CONFIG_FILE) if payload is None else payload
    if not isinstance(data, dict):
        return [f"{_SEMANTIC_CONFIG_FILE} must be a JSON object"]

    if not data.get("schema_version"):
        warnings.append(f"{_SEMANTIC_CONFIG_FILE} missing schema_version")

    default_mode = str(data.get("default_mode", "")).strip().lower()
    if default_mode not in _SEMANTIC_MODES:
        warnings.append(f"{_SEMANTIC_CONFIG_FILE}:default_mode must be one of {sorted(_SEMANTIC_MODES)}")

    domains = data.get("domains")
    if not isinstance(domains, dict):
        warnings.append(f"{_SEMANTIC_CONFIG_FILE}:domains must be an object")
        return warnings

    missing_domains = sorted(_SEMANTIC_DOMAINS - {str(key) for key in domains})
    for domain in missing_domains:
        warnings.append(f"{_SEMANTIC_CONFIG_FILE}:domains missing '{domain}'")

    for domain, domain_payload in domains.items():
        domain_key = str(domain)
        if domain_key not in _SEMANTIC_DOMAINS:
            warnings.append(f"{_SEMANTIC_CONFIG_FILE}:domains has unknown domain '{domain_key}'")
        if not isinstance(domain_payload, dict):
            warnings.append(f"{_SEMANTIC_CONFIG_FILE}:domains.{domain_key} must be an object")
            continue
        mode = str(domain_payload.get("mode", default_mode)).strip().lower()
        if mode not in _SEMANTIC_MODES:
            warnings.append(f"{_SEMANTIC_CONFIG_FILE}:domains.{domain_key}.mode must be one of {sorted(_SEMANTIC_MODES)}")

    return warnings


def validate_semantic_axis_asset(filename: str, payload: Any | None = None) -> list[str]:
    data = _read_json_asset(filename) if payload is None else payload
    warnings = [
        f"{filename}:{warning}"
        for warning in validate_axis_payload(data if isinstance(data, dict) else {})
    ]
    warnings.extend(validate_banned_terms_in_asset(filename, data))
    return warnings


def validate_object_relation_profiles(payload: Any | None = None) -> list[str]:
    data = _read_json_asset(_OBJECT_RELATION_FILE) if payload is None else payload
    warnings: list[str] = []
    if not isinstance(data, dict):
        return [f"{_OBJECT_RELATION_FILE} must be a JSON object"]

    if not data.get("schema_version"):
        warnings.append(f"{_OBJECT_RELATION_FILE} missing schema_version")

    relations = data.get("relations")
    if not isinstance(relations, dict):
        warnings.append(f"{_OBJECT_RELATION_FILE}:relations must be an object")
        warnings.extend(validate_banned_terms_in_asset(_OBJECT_RELATION_FILE, data))
        return warnings

    object_tokens = {str(token) for token in OBJECT_TOKENS}
    for relation_key, relation in relations.items():
        key = str(relation_key or "").strip()
        path = f"{_OBJECT_RELATION_FILE}:relations.{key or '<empty>'}"
        if ":" not in key or key.startswith(":") or key.endswith(":"):
            warnings.append(f"{path} key must use 'object:relation' format")
            key_object = ""
        else:
            key_object = key.split(":", 1)[0]

        if not isinstance(relation, dict):
            warnings.append(f"{path} must be an object")
            continue

        object_token = str(relation.get("object", "")).strip()
        if not object_token:
            warnings.append(f"{path}.object is required")
        elif object_token not in object_tokens:
            warnings.append(f"{path}.object unknown object token '{object_token}'")
        if key_object and object_token and key_object != object_token:
            warnings.append(f"{path}.object must match relation key object '{key_object}'")

        verbs = relation.get("verbs")
        if not isinstance(verbs, list) or not verbs:
            warnings.append(f"{path}.verbs must be a non-empty list")
        elif not all(isinstance(verb, str) and verb.strip() for verb in verbs):
            warnings.append(f"{path}.verbs must contain non-empty strings")

        roles = relation.get("required_roles")
        if not isinstance(roles, dict) or not roles:
            warnings.append(f"{path}.required_roles must be a non-empty object")
        elif isinstance(roles, dict):
            for role, values in roles.items():
                role_key = str(role or "").strip()
                role_path = f"{path}.required_roles.{role_key or '<empty>'}"
                if role_key not in ALLOWED_OBJECT_RELATION_ROLES:
                    warnings.append(f"{role_path} unknown role")
                if not isinstance(values, list) or not values:
                    warnings.append(f"{role_path} must be a non-empty list")
                    continue
                if not all(isinstance(value, str) and value.strip() for value in values):
                    warnings.append(f"{role_path} must contain non-empty strings")

        forbidden = relation.get("forbidden_patterns", [])
        if not isinstance(forbidden, list):
            warnings.append(f"{path}.forbidden_patterns must be a list")
        elif not all(isinstance(value, str) and value.strip() for value in forbidden):
            warnings.append(f"{path}.forbidden_patterns must contain non-empty strings")

    warnings.extend(validate_banned_terms_in_asset(_OBJECT_RELATION_FILE, data))
    return warnings


def validate_semantic_epig_assets() -> list[str]:
    warnings: list[str] = []
    warnings.extend(validate_semantic_epig_config())

    for filename in _SEMANTIC_AXIS_ASSETS:
        if _asset_exists(filename):
            warnings.extend(validate_semantic_axis_asset(filename))

    for filename in _SEMANTIC_BANNED_ASSETS:
        if _asset_exists(filename) and filename not in _SEMANTIC_AXIS_ASSETS:
            warnings.extend(validate_banned_terms_in_asset(filename, _read_json_asset(filename)))

    if _asset_exists(_OBJECT_RELATION_FILE):
        warnings.extend(validate_object_relation_profiles())

    return warnings


def validate_assets() -> list[str]:
    warnings: list[str] = []
    backgrounds = load_background_packs()
    alias_overrides = load_background_alias_overrides()
    clothing_theme_map = load_clothing_theme_map()
    character_profiles = load_character_profiles()
    compatibility = load_scene_compatibility().get("characters", {})

    for filename in _TARGETED_BANNED_ASSETS:
        data = _read_json_asset(filename)
        warnings.extend(validate_banned_terms_in_asset(filename, data))

    warnings.extend(validate_location_aliases(backgrounds, alias_overrides))
    warnings.extend(validate_alias_layer_assets(backgrounds))
    warnings.extend(
        validate_character_assets(
            character_profiles,
            compatibility,
            clothing_theme_map,
            allow_unconnected_profiles=_ALLOWED_UNCONNECTED_PROFILES,
        )
    )
    warnings.extend(validate_semantic_epig_assets())

    return sorted(set(warnings))
