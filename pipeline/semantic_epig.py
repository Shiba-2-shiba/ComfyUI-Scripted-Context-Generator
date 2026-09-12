"""Config and debug helpers for semantic EPIG-style enrichment."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

try:  # pragma: no cover - import shape depends on package execution mode
    from ..vocab.loader import load_json
except ImportError:  # pragma: no cover
    from vocab.loader import load_json

CONFIG_FILE = "semantic_epig_config.json"
KNOWN_DOMAINS = (
    "action",
    "object_relation",
    "location_scene",
    "clothing_tpo",
    "personality_behavior",
)
VALID_MODES = {"off", "passive", "active"}

DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": "1.0",
    "default_mode": "passive",
    "gamma": 2.0,
    "top_k": 3,
    "top_window": 3,
    "domains": {
        "action": {"mode": "passive"},
        "object_relation": {"mode": "passive"},
        "location_scene": {"mode": "passive"},
        "clothing_tpo": {"mode": "passive"},
        "personality_behavior": {"mode": "passive"},
    },
}


def _normalized_mode(value: Any, fallback: str = "passive") -> str:
    mode = str(value or "").strip().lower()
    if mode in VALID_MODES:
        return mode
    return fallback if fallback in VALID_MODES else "passive"


def _merge_config(payload: Any) -> dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    if not isinstance(payload, dict):
        return config

    for key in ("schema_version", "gamma", "top_k", "top_window"):
        if key in payload:
            config[key] = payload[key]
    config["default_mode"] = _normalized_mode(payload.get("default_mode"), "passive")

    domains = payload.get("domains")
    if isinstance(domains, dict):
        for domain in KNOWN_DOMAINS:
            domain_payload = domains.get(domain)
            if not isinstance(domain_payload, dict):
                continue
            merged_domain = dict(config["domains"].get(domain, {}))
            merged_domain.update(domain_payload)
            merged_domain["mode"] = _normalized_mode(
                domain_payload.get("mode"),
                config["default_mode"],
            )
            config["domains"][domain] = merged_domain

    return config


def load_semantic_epig_config() -> dict[str, Any]:
    try:
        payload = load_json(CONFIG_FILE)
    except (FileNotFoundError, OSError, ValueError):
        payload = {}
    return _merge_config(payload)


def semantic_mode(domain: str) -> str:
    config = load_semantic_epig_config()
    domain_key = str(domain or "").strip()
    if domain_key not in KNOWN_DOMAINS:
        return "off"
    domain_config = config.get("domains", {}).get(domain_key, {})
    return _normalized_mode(domain_config.get("mode"), config.get("default_mode", "passive"))


def domain_enabled(domain: str, *, active_only: bool = False) -> bool:
    mode = semantic_mode(domain)
    if active_only:
        return mode == "active"
    return mode in {"passive", "active"}


def selection_debug_fields(
    *,
    mode: str,
    semantic_scoring_enabled: bool | None = None,
    baseline_candidate: Any = "",
    semantic_candidate: Any = "",
    semantic_top_candidate: Any = "",
    selected_candidate_rank: int | None = None,
    selection_changed_by_semantic: bool | None = None,
) -> dict[str, Any]:
    scoring_enabled = mode in {"passive", "active"} if semantic_scoring_enabled is None else bool(semantic_scoring_enabled)
    if selection_changed_by_semantic is None:
        selection_changed_by_semantic = (
            bool(scoring_enabled)
            and baseline_candidate not in ("", None)
            and semantic_candidate not in ("", None)
            and baseline_candidate != semantic_candidate
        )
    return {
        "semantic_scoring_enabled": bool(scoring_enabled),
        "selection_changed_by_semantic": bool(selection_changed_by_semantic),
        "baseline_candidate": baseline_candidate,
        "semantic_candidate": semantic_candidate,
        "semantic_top_candidate": semantic_top_candidate,
        "selected_candidate_rank": selected_candidate_rank,
    }


def add_semantic_debug(decision: dict[str, Any], domain: str, payload: dict[str, Any]) -> None:
    if not isinstance(decision, dict) or not isinstance(payload, dict):
        return
    domain_key = str(domain or "").strip()
    if not domain_key:
        return
    semantic_debug = decision.setdefault("semantic_epig", {})
    if not isinstance(semantic_debug, dict):
        decision["semantic_epig"] = {}
        semantic_debug = decision["semantic_epig"]
    semantic_debug[domain_key] = dict(payload)
