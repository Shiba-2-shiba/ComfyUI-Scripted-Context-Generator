import json
from typing import Any, Dict, Optional

from .schema import CONTEXT_VERSION, PromptContext


def make_empty_context(seed: int = 0) -> PromptContext:
    return PromptContext(seed=seed)


def normalize_context_data(
    data: Any,
    default_seed: int = 0,
    warn_on_legacy: bool = True,
) -> PromptContext:
    if isinstance(data, PromptContext):
        ctx = PromptContext.from_dict(data.to_dict())
        if ctx.seed == 0 and default_seed:
            ctx.seed = default_seed
        return ctx

    if not isinstance(data, dict):
        return PromptContext(
            seed=default_seed,
            warnings=["Non-dict context payload; falling back to empty context"],
        )

    normalized = PromptContext.from_dict(data)
    if normalized.seed == 0 and default_seed:
        normalized.seed = default_seed

    if warn_on_legacy and "context_version" not in data:
        normalized.context_version = CONTEXT_VERSION
        normalized.warnings.append("Legacy context payload normalized to v2")

    return normalized


def context_from_json(json_str: Optional[str], default_seed: int = 0) -> PromptContext:
    if json_str is None:
        return make_empty_context(seed=default_seed)

    text = str(json_str).strip()
    if text == "":
        return make_empty_context(seed=default_seed)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return PromptContext(
            seed=default_seed,
            warnings=["Invalid context JSON; falling back to empty context"],
        )

    return normalize_context_data(payload, default_seed=default_seed, warn_on_legacy=True)


def context_to_json(context: Any) -> str:
    if isinstance(context, PromptContext):
        ctx = context
    else:
        ctx = normalize_context_data(context)
    return ctx.to_json()


def context_to_dict(context: Any) -> Dict[str, Any]:
    if isinstance(context, PromptContext):
        return context.to_dict()
    return normalize_context_data(context).to_dict()


def append_warning(context: PromptContext, warning: str) -> PromptContext:
    ctx = PromptContext.from_dict(context.to_dict())
    if warning:
        ctx.warnings.append(str(warning))
    return ctx
