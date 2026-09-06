"""Read-only semantic projections for the effective-diversity audit.

Resolver-backed extraction stays separate from the pure metric helpers. Builder
replay and workflow execution belong to the CLI; no final prose is parsed here.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping
import json
from pathlib import Path
import re
from typing import Any
import unicodedata

from character_service import resolve_character
from clothing_service import resolve_clothing_theme
from core.context_ops import ensure_context
from core.context_state import generation_state_from_context
from core.schema import ActionFrame, PromptContext
from core.semantic_families import semantic_families_for_tags, semantic_families_for_text, split_semantic_tags
from location_service import resolve_location_key
from object_focus_service import extract_action_object_flags
from pipeline.action_parser import STANCE_STARTERS, action_verb
from scene_service import load_scene_axes


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = " ".join(unicodedata.normalize("NFC", value).lower().split())
    return value if value and value != "unknown" else None


def _latest_decision(ctx: PromptContext, node: str) -> Mapping[str, Any] | None:
    for entry in reversed(ctx.history):
        if entry.node == node:
            return entry.decision
    return None


def _valid_frame(raw: Any, ctx: PromptContext) -> ActionFrame | None:
    if not isinstance(raw, Mapping):
        return None
    # Reuse the runtime's supported-version, has-content and legacy-text checks.
    frame = generation_state_from_context({"action": ctx.action, "extras": {"action_frame": dict(raw)}}).action
    return frame if frame.has_content() else None


def _selected_frame(
    ctx: PromptContext, builder: Mapping[str, Any], rejected: list[str],
) -> tuple[ActionFrame | None, str, Mapping[str, Any]]:
    for source, raw in (("builder.action_frame", builder.get("action_frame")),
                        ("extras.action_frame", ctx.extras.get("action_frame"))):
        if raw is not None:
            frame = _valid_frame(raw, ctx)
            if frame is not None:
                return frame, source, raw
            rejected.append(source)

    decision = _latest_decision(ctx, "ContextSceneVariator")
    if decision is None:
        return None, "missing", {}
    # action is the incoming value; new_action is authoritative even when empty.
    selected_action = decision.get("new_action") if "new_action" in decision else decision.get("action")
    selected_loc = _text(decision.get("selected_loc"))
    current_loc = _text(ctx.loc)
    matches = (
        isinstance(selected_action, str) and selected_action.strip() == ctx.action.strip()
        and not (decision.get("action_updated") and "new_action" not in decision)
        and selected_loc is not None and current_loc is not None
        and (resolve_location_key(selected_loc) or selected_loc) == (resolve_location_key(current_loc) or current_loc)
    )
    if not matches:
        rejected.append("scene.decision")
        return None, "missing", {}
    if "action_frame" in decision:
        frame = _valid_frame(decision["action_frame"], ctx)
        if frame is not None:
            return frame, "scene.action_frame", decision["action_frame"]
        rejected.append("scene.action_frame")
    slots = decision.get("slots")
    if isinstance(slots, Mapping) and slots:
        return ActionFrame.from_slots(slots, legacy_text=ctx.action.strip()), "scene.slots", slots
    return None, "missing", {}


def _families(value: Any, classifier: Callable[[str], Collection[str]]) -> list[str] | None:
    if not isinstance(value, str):
        return None
    if not value.strip():
        return []
    return sorted(classifier(value)) or None


def _enum(value: Any, keys: Collection[str]) -> str | None:
    value = _text(value)
    return value if value in keys else None


def build_semantic_signatures(
    record_or_context: Mapping[str, Any] | PromptContext,
    *,
    builder_decision: Mapping[str, Any] | None = None,
    mood_keys: Collection[str] | None = None,
) -> dict[str, Any]:
    """Return fixed core/frame fields, validity, axes and extraction diagnostics.

    Pass core/frame to metric helpers only when ``valid`` is true; otherwise pass
    None. A supplied builder decision must come from CLI replay, and its stored
    prompt must equal this record's raw_prompt. ``mood_keys`` lets a batch reuse
    its source-bound mood dictionary; the default reads repository mood_map.json.
    """
    record = record_or_context
    data = record.get("final_context", record) if isinstance(record, Mapping) else record
    if isinstance(data, PromptContext):
        data = data.to_dict()
    if not isinstance(data, Mapping):
        raise ValueError("a context mapping or record with final_context is required")
    ctx = ensure_context(dict(data))
    raw_extras = data.get("extras")
    raw_extras = raw_extras if isinstance(raw_extras, Mapping) else {}
    builder: Mapping[str, Any] = {}
    if builder_decision is not None:
        raw_prompt = record.get("raw_prompt") if isinstance(record, Mapping) else None
        if (not isinstance(builder_decision, Mapping) or not isinstance(raw_prompt, str)
                or not raw_prompt.strip() or builder_decision.get("prompt") != raw_prompt):
            raise ValueError("builder decision requires exact raw_prompt parity")
        builder = builder_decision
    plan = builder.get("content_plan")
    plan = plan if isinstance(plan, Mapping) else {}
    syntax, plan_syntax = _text(builder.get("syntax_family")), _text(plan.get("syntax_family"))
    if syntax and plan_syntax and syntax != plan_syntax:
        raise ValueError("builder and content-plan syntax families disagree")
    syntax = syntax or plan_syntax

    rejected: list[str] = []
    action, action_source, raw_action = _selected_frame(ctx, builder, rejected)
    slots = action.legacy_slots if action is not None else {}
    sources: dict[str, str] = {}

    def choose(field: str, *candidates: tuple[Any, str]) -> Any:
        for value, source in candidates:
            if value is not None:
                sources[field] = source
                return value
        sources[field] = "missing"
        return None

    resolved = resolve_character(
        raw=_text(ctx.subj) or "", source_subj_key=_text(ctx.extras.get("source_subj_key")) or "",
        character_name=_text(ctx.extras.get("character_name")) or "",
    )
    axes = load_scene_axes()
    verb = _text(action.main_verb) if action is not None else None
    fallback_verb = _text(action_verb(ctx.action))
    purpose = _enum(slots.get("purpose"), axes.get("purpose", {}))
    object_text = _text(slots.get("primary_action")) or ctx.action
    object_flags = extract_action_object_flags(object_text)
    core = {
        "canonical_subject": choose("canonical_subject",
            (_text(resolved.get("profile_key")), "character.profile_key"),
            (_text(resolved.get("compatibility_key")), "character.compatibility_key")),
        "canonical_location": choose("canonical_location",
            (_text(resolve_location_key(_text(ctx.loc) or "")), "context.loc"),
            (_text(resolve_location_key(_text(ctx.extras.get("raw_loc_tag")) or "")), "extras.raw_loc_tag")),
        "action_family_or_main_verb": choose("action_family_or_main_verb",
            (f"verb:{verb}" if verb else None, action_source + ".main_verb"),
            (f"verb:{fallback_verb}" if fallback_verb else None, "context.action"),
            (f"purpose:{purpose}" if purpose else None, action_source + ".slots.purpose")),
        "primary_object_or_object_family": choose("primary_object_or_object_family",
            (_text(action.primary_object) if action is not None else None, action_source + ".primary_object"),
            (next(iter(object_flags)) if len(object_flags) == 1 else None,
             action_source + ".slots.primary_action" if _text(slots.get("primary_action")) else "context.action")),
    }

    posture = _text(action.posture) if action is not None else None
    stance = next((key for key in STANCE_STARTERS if posture and re.match(rf"{re.escape(key)}\b", posture)), None)
    frame = {**core,
        "posture": choose("posture", (stance, action_source + ".posture")),
        "hand_action_family": choose("hand_action_family",
            (_families(raw_action.get("hand_action"), semantic_families_for_text), action_source + ".hand_action")),
        "gaze_target_family": choose("gaze_target_family",
            (_families(raw_action.get("gaze_target"), extract_action_object_flags), action_source + ".gaze_target")),
    }
    for field, slot, domain in (("progress", "progress_state", "progress"),
                                ("stimulus_or_obstacle", "obstacle_or_trigger", "obstacle"),
                                ("social_relation", "social_distance", "social_distance")):
        allowed = set(axes.get(domain, {})) | ({"viewer"} if field == "social_relation" else set())
        frame[field] = choose(field,
            (_enum(getattr(action, field), allowed) if action is not None else None, action_source + "." + field),
            (_enum(slots.get(slot), allowed), action_source + ".slots." + slot))

    if mood_keys is None:
        mood_keys = json.loads((Path(__file__).resolve().parents[1] / "mood_map.json").read_text(encoding="utf-8"))
    frame["mood"] = choose("mood",
        (_enum(ctx.extras.get("raw_mood_key"), mood_keys), "extras.raw_mood_key"),
        (_enum(ctx.meta.mood, mood_keys), "context.meta.mood"))
    clothing = _latest_decision(ctx, "ContextClothingExpander") or {}
    frame["clothing_family"] = choose("clothing_family",
        (_text(clothing.get("chosen_type")), "clothing.chosen_type"),
        (_text(resolve_clothing_theme(_text(clothing.get("theme")) or "")), "clothing.theme"),
        (_text(resolve_clothing_theme(_text(ctx.costume) or "")), "context.costume"))
    garnish = _latest_decision(ctx, "ContextGarnish")
    tags = garnish.get("final_tags") if garnish is not None else None
    if garnish is None and isinstance(raw_extras.get("garnish"), str):
        tags = split_semantic_tags(raw_extras["garnish"])
    families = None
    if isinstance(tags, list) and all(isinstance(tag, str) and tag.strip() for tag in tags):
        families = sorted(semantic_families_for_tags(tags)) or (None if tags else [])
    frame["garnish_family"] = choose("garnish_family",
        (families, "garnish.final_tags" if garnish is not None else "extras.garnish"))
    sources["syntax_family"] = "builder.syntax_family" if _text(builder.get("syntax_family")) else (
        "builder.content_plan.syntax_family" if plan_syntax else "missing")
    return {
        "core": core, "frame": frame,
        "valid": all(core[field] is not None for field in ("canonical_subject", "canonical_location", "action_family_or_main_verb")),
        "axes": {
            "subject": core["canonical_subject"], "location": core["canonical_location"],
            "action_family": core["action_family_or_main_verb"], "primary_object_family": core["primary_object_or_object_family"],
            "mood": frame["mood"], "clothing_family": frame["clothing_family"],
            "garnish_family": frame["garnish_family"], "syntax_family": syntax,
        },
        "diagnostics": {
            "missing_fields": {"core": sorted(key for key, value in core.items() if value is None),
                               "frame": sorted(key for key, value in frame.items() if value is None)},
            "extraction_sources": sources, "rejected_sources": sorted(rejected),
        },
    }
