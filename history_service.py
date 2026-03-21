from __future__ import annotations

from typing import Any

from object_focus_service import extract_object_flags


def recent_history_decisions(ctx: Any, node_name: str, limit: int = 4) -> list[dict]:
    decisions = []
    for entry in reversed(getattr(ctx, "history", [])):
        if entry.node != node_name:
            continue
        decisions.append(entry.decision or {})
        if len(decisions) >= limit:
            break
    return decisions


def recent_template_history(ctx: Any, limit: int = 4) -> list[str]:
    templates = []
    for decision in recent_history_decisions(ctx, "ContextPromptBuilder", limit=limit):
        template_key = str(decision.get("template_key", "")).strip()
        if template_key:
            templates.append(template_key)
    return templates


def recent_template_part_history(ctx: Any, part_name: str, limit: int = 4) -> list[str]:
    keys = []
    field_name = f"{part_name}_key"
    for decision in recent_history_decisions(ctx, "ContextPromptBuilder", limit=limit):
        key = str(decision.get(field_name, "")).strip()
        if key:
            keys.append(key)
    return keys


def recent_clothing_packs(ctx: Any, limit: int = 4) -> list[str]:
    recent = []
    for decision in recent_history_decisions(ctx, "ContextClothingExpander", limit=limit):
        pack_key = str(decision.get("base_pack", "")).strip()
        if pack_key:
            recent.append(pack_key)
    return recent


def recent_clothing_types(ctx: Any, limit: int = 4) -> list[str]:
    recent = []
    for decision in recent_history_decisions(ctx, "ContextClothingExpander", limit=limit):
        chosen_type = str(decision.get("chosen_type", "")).strip()
        if chosen_type:
            recent.append(chosen_type)
    return recent


def recent_outerwear_packs(ctx: Any, limit: int = 4) -> list[str]:
    recent = []
    for decision in recent_history_decisions(ctx, "ContextClothingExpander", limit=limit):
        outerwear_pack = str(decision.get("outerwear_pack", "")).strip()
        if outerwear_pack:
            recent.append(outerwear_pack)
    return recent


def clothing_signature_from_decision(decision: dict | None) -> str:
    chosen_type = str((decision or {}).get("chosen_type", "")).strip() or "none"
    base_pack = str((decision or {}).get("base_pack", "")).strip() or "none"
    base_variant = str((decision or {}).get("base_variant", "")).strip() or "none"
    outerwear_pack = str((decision or {}).get("outerwear_pack", "")).strip() or "none"
    outerwear_variant = str((decision or {}).get("outerwear_variant", "")).strip() or "none"
    return f"{chosen_type}|{base_pack}|{base_variant}|{outerwear_pack}|{outerwear_variant}"


def recent_clothing_signatures(ctx: Any, limit: int = 4) -> list[str]:
    recent = []
    for decision in recent_history_decisions(ctx, "ContextClothingExpander", limit=limit):
        signature = clothing_signature_from_decision(decision)
        if signature and signature != "none|none|none":
            recent.append(signature)
    return recent


def recent_prompt_objects(ctx: Any, limit: int = 4) -> set[str]:
    objects = set()
    for node_name in ("ContextClothingExpander", "ContextLocationExpander", "ContextSceneVariator"):
        for decision in recent_history_decisions(ctx, node_name, limit=limit):
            for value in decision.get("objects", []):
                if value:
                    objects.add(str(value))
            new_action = str(decision.get("new_action", "")).strip()
            objects.update(extract_object_flags(new_action))
    return objects
