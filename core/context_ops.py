from typing import Any, Dict, Optional

from .context_codec import normalize_context_data
from .schema import DebugInfo, PromptContext, LEGACY_STYLE_NOTE


TOP_LEVEL_TEXT_FIELDS = {"subj", "costume", "loc", "action", "context_version"}
TOP_LEVEL_INT_FIELDS = {"seed"}


def ensure_context(context: Any, default_seed: int = 0) -> PromptContext:
    return normalize_context_data(context, default_seed=default_seed, warn_on_legacy=False)


def patch_context(
    context: Any,
    updates: Optional[Dict[str, Any]] = None,
    extras: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> PromptContext:
    ctx = ensure_context(context)

    for key, value in (updates or {}).items():
        if key in TOP_LEVEL_TEXT_FIELDS:
            setattr(ctx, key, "" if value is None else str(value))
        elif key in TOP_LEVEL_INT_FIELDS:
            try:
                setattr(ctx, key, int(value))
            except Exception:
                setattr(ctx, key, 0)
        elif key == "notes" and isinstance(value, list):
            ctx.notes = [str(item) for item in value]
        elif key == "warnings" and isinstance(value, list):
            ctx.warnings = [str(item) for item in value]

    if isinstance(meta, dict):
        if "mood" in meta:
            ctx.meta.mood = "" if meta["mood"] is None else str(meta["mood"])
        if "style" in meta:
            ctx.meta.style = "" if meta["style"] is None else str(meta["style"])
            if ctx.meta.style and LEGACY_STYLE_NOTE not in ctx.notes:
                ctx.notes.append(LEGACY_STYLE_NOTE)
        if "tags" in meta and isinstance(meta["tags"], dict):
            ctx.meta.tags = dict(meta["tags"])

    if isinstance(extras, dict):
        ctx.extras.update(extras)

    return ctx


def merge_context(base: Any, overlay: Any) -> PromptContext:
    base_ctx = ensure_context(base)
    overlay_ctx = ensure_context(overlay)

    merged = ensure_context(base_ctx)

    for key in ("subj", "costume", "loc", "action"):
        value = getattr(overlay_ctx, key)
        if value:
            setattr(merged, key, value)

    if overlay_ctx.seed:
        merged.seed = overlay_ctx.seed

    if overlay_ctx.context_version:
        merged.context_version = overlay_ctx.context_version

    if overlay_ctx.meta.mood:
        merged.meta.mood = overlay_ctx.meta.mood
    if not merged.meta.style and overlay_ctx.meta.style:
        merged.meta.style = overlay_ctx.meta.style
        if LEGACY_STYLE_NOTE not in merged.notes:
            merged.notes.append(LEGACY_STYLE_NOTE)
    elif merged.meta.style and overlay_ctx.meta.style and merged.meta.style != overlay_ctx.meta.style:
        note = "meta.style is legacy read-only; overlay style is not prioritized"
        if note not in merged.notes:
            merged.notes.append(note)
    if overlay_ctx.meta.tags:
        merged.meta.tags.update(overlay_ctx.meta.tags)

    merged.extras.update(overlay_ctx.extras)
    merged.history.extend(overlay_ctx.history)
    merged.notes.extend(overlay_ctx.notes)
    merged.warnings.extend(overlay_ctx.warnings)
    return merged


def append_history(context: Any, entry: Any) -> PromptContext:
    ctx = ensure_context(context)
    if isinstance(entry, DebugInfo):
        ctx.history.append(DebugInfo.from_dict(entry.to_dict()))
    elif isinstance(entry, dict):
        ctx.history.append(DebugInfo.from_dict(entry))
    return ctx


def add_warning(context: Any, warning: str) -> PromptContext:
    ctx = ensure_context(context)
    if warning:
        ctx.warnings.append(str(warning))
    return ctx


def add_note(context: Any, note: str) -> PromptContext:
    ctx = ensure_context(context)
    if note:
        ctx.notes.append(str(note))
    return ctx
