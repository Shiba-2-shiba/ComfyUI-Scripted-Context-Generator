from __future__ import annotations

from typing import Any, Dict, MutableMapping

try:
    from ..object_focus_service import extract_action_object_flags, summarize_object_relation_focus
    from .semantic_epig import semantic_mode
except ImportError:
    from object_focus_service import extract_action_object_flags, summarize_object_relation_focus
    from pipeline.semantic_epig import semantic_mode


def apply_object_relation_slots(slots: MutableMapping[str, str], action_text: str) -> Dict[str, Any]:
    relation_debug = summarize_object_relation_focus(
        action_text,
        extract_action_object_flags(action_text),
    )
    relation_debug["mode"] = semantic_mode("object_relation")
    relation_debug["applied_slots"] = {}
    relation_debug["skipped_slots"] = {}

    if semantic_mode("object_relation") != "active":
        relation_debug["skipped_slots"] = {
            role: "passive mode"
            for role in relation_debug.get("required_roles", {})
        }
        return relation_debug

    role_slots = relation_debug.get("required_roles", {})
    if not isinstance(role_slots, dict):
        return relation_debug
    for role, candidates in role_slots.items():
        if not isinstance(candidates, list) or not candidates:
            continue
        chosen = str(candidates[0]).strip()
        if not chosen:
            continue
        role_key = str(role)
        existing = str(slots.get(role_key, "")).strip()
        if existing:
            relation_debug["skipped_slots"][role_key] = "existing slot already set"
            continue
        slots[role_key] = chosen
        relation_debug["applied_slots"][role_key] = chosen
    return relation_debug
