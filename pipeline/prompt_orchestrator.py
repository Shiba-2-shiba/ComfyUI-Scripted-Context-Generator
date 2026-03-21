try:
    from .. import prompt_renderer
    from ..core.context_state import generation_state_from_context
    from ..core.context_ops import append_history, ensure_context, patch_context
    from ..core.schema import DebugInfo
    from ..history_service import recent_template_history, recent_template_part_history
except ImportError:
    import prompt_renderer
    from core.context_state import generation_state_from_context
    from core.context_ops import append_history, ensure_context, patch_context
    from core.schema import DebugInfo
    from history_service import recent_template_history, recent_template_part_history

_derive_template_roles = prompt_renderer._derive_template_roles
_template_entries = prompt_renderer._template_entries


def build_prompt_text(
    template,
    composition_mode,
    seed,
    subj="",
    costume="",
    loc="",
    action="",
    garnish="",
    meta_mood="",
    meta_style="",
    staging_tags="",
    recent_templates=None,
    recent_intro_keys=None,
    recent_body_keys=None,
    recent_end_keys=None,
    return_debug=False,
):
    return prompt_renderer.build_prompt_text(
        template=template,
        composition_mode=composition_mode,
        seed=seed,
        subj=subj,
        costume=costume,
        loc=loc,
        action=action,
        garnish=garnish,
        meta_mood=meta_mood,
        meta_style=meta_style,
        staging_tags=staging_tags,
        recent_templates=recent_templates,
        recent_intro_keys=recent_intro_keys,
        recent_body_keys=recent_body_keys,
        recent_end_keys=recent_end_keys,
        return_debug=return_debug,
        template_entries_fn=_template_entries,
    )


def build_prompt_from_context(context, template, composition_mode, seed):
    ctx = ensure_context(context, default_seed=int(seed))
    state = generation_state_from_context(ctx)
    prompt, prompt_debug = build_prompt_text(
        template=template,
        composition_mode=composition_mode,
        seed=seed,
        subj=ctx.subj,
        costume=state.clothing.clothing_prompt or ctx.costume,
        loc=state.location.location_prompt or ctx.loc,
        action=ctx.action,
        garnish=state.fragments.garnish,
        meta_mood=ctx.meta.mood,
        staging_tags=state.fragments.staging_tags,
        recent_templates=recent_template_history(ctx),
        recent_intro_keys=recent_template_part_history(ctx, "intro"),
        recent_body_keys=recent_template_part_history(ctx, "body"),
        recent_end_keys=recent_template_part_history(ctx, "end"),
        return_debug=True,
    )
    updated_ctx = patch_context(ctx, updates={"seed": seed})
    updated_ctx = append_history(
        updated_ctx,
        DebugInfo(
            node="ContextPromptBuilder",
            seed=seed,
            decision={**prompt_debug, "prompt": prompt},
        ),
    )
    return updated_ctx, prompt
