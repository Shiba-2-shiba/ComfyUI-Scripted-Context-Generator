from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


POLICY_FILENAME = "prompt_risk_families.json"


def _data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "vocab" / "data"


def _policy_path() -> Path:
    return _data_dir() / POLICY_FILENAME


def _normalize_patterns(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


@lru_cache(maxsize=1)
def load_prompt_risk_policy() -> dict[str, Any]:
    payload = json.loads(_policy_path().read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def validate_prompt_risk_policy(payload: Any | None = None) -> list[str]:
    data = load_prompt_risk_policy() if payload is None else payload
    warnings: list[str] = []
    if not isinstance(data, dict):
        return [f"{POLICY_FILENAME} must be a JSON object"]
    if not str(data.get("schema_version", "")).strip():
        warnings.append(f"{POLICY_FILENAME}:schema_version is required")

    families = data.get("families")
    if not isinstance(families, dict) or not families:
        warnings.append(f"{POLICY_FILENAME}:families must be a non-empty object")
        return warnings

    seen_patterns: dict[str, str] = {}
    for family_name, family in families.items():
        family_key = str(family_name).strip()
        path = f"{POLICY_FILENAME}:families.{family_key or '<empty>'}"
        if not family_key:
            warnings.append(f"{path} family name is empty")
        if not isinstance(family, dict):
            warnings.append(f"{path} must be an object")
            continue

        patterns = _normalize_patterns(family.get("patterns"))
        if not patterns:
            warnings.append(f"{path}.patterns must be a non-empty list")
        if "solo_flags" in family and not isinstance(family.get("solo_flags"), list):
            warnings.append(f"{path}.solo_flags must be a list when present")

        for pattern in patterns:
            normalized = pattern.lower()
            if normalized in seen_patterns:
                warnings.append(
                    f"{path}.patterns duplicate pattern '{pattern}' also used by {seen_patterns[normalized]}"
                )
            else:
                seen_patterns[normalized] = family_key
            try:
                re.compile(pattern)
            except re.error as exc:
                warnings.append(f"{path}.patterns invalid regex '{pattern}': {exc}")

    return warnings


@lru_cache(maxsize=1)
def _compiled_families() -> tuple[tuple[str, tuple[re.Pattern[str], ...], tuple[str, ...]], ...]:
    policy = load_prompt_risk_policy()
    families = policy.get("families", {}) if isinstance(policy, dict) else {}
    compiled = []
    for family_name, family in sorted(families.items()):
        if not isinstance(family, dict):
            continue
        patterns = []
        for pattern in _normalize_patterns(family.get("patterns")):
            patterns.append(re.compile(pattern, re.IGNORECASE))
        if patterns:
            compiled.append(
                (
                    str(family_name),
                    tuple(patterns),
                    tuple(_normalize_patterns(family.get("solo_flags"))),
                )
            )
    return tuple(compiled)


def classify_risk_families(text: str) -> set[str]:
    source = str(text or "")
    families: set[str] = set()
    for family_name, patterns, _flags in _compiled_families():
        if any(pattern.search(source) for pattern in patterns):
            families.add(family_name)
    return families


def solo_flags_for_risk_families(families: Iterable[str]) -> set[str]:
    wanted = {str(family) for family in families or []}
    flags: set[str] = set()
    for family_name, _patterns, solo_flags in _compiled_families():
        if family_name in wanted:
            flags.update(solo_flags)
    return flags


def risk_family_matches(text: str) -> dict[str, list[str]]:
    source = str(text or "")
    matches: dict[str, list[str]] = {}
    for family_name, patterns, _flags in _compiled_families():
        hits = sorted({pattern.pattern for pattern in patterns if pattern.search(source)})
        if hits:
            matches[family_name] = hits
    return matches
