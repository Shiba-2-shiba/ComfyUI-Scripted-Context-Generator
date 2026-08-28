if __package__ and "." in __package__:
    from .. import prompt_renderer
    from ..core.context_state import generation_state_from_context
    from ..core.context_ops import append_history, ensure_context, patch_context
    from ..core.schema import ActionFrame, DebugInfo
    from ..history_service import recent_template_history, recent_template_part_history
    from .action_generator import action_object_flags
    from .action_parser import action_verb, parse_pool_action_to_slots
else:
    import prompt_renderer
    from core.context_state import generation_state_from_context
    from core.context_ops import append_history, ensure_context, patch_context
    from core.schema import ActionFrame, DebugInfo
    from history_service import recent_template_history, recent_template_part_history
    from pipeline.action_generator import action_object_flags
    from pipeline.action_parser import action_verb, parse_pool_action_to_slots

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
    action_frame=None,
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
        action_frame=action_frame,
        return_debug=return_debug,
        template_entries_fn=_template_entries,
    )


def build_prompt_from_context(context, template, composition_mode, seed):
    ctx = ensure_context(context, default_seed=int(seed))
    state = generation_state_from_context(ctx)
    if not state.action.has_content() and ctx.action:
        slots = parse_pool_action_to_slots(ctx.action, loc=ctx.loc)
        objects = sorted(action_object_flags(ctx.action))
        state.action = ActionFrame.from_slots(
            slots,
            legacy_text=ctx.action,
            main_verb=action_verb(ctx.action),
            primary_object=objects[0] if objects else "",
        )
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
        action_frame=state.action.to_dict() if state.action.has_content() else None,
        return_debug=True,
    )
    action_slots = state.action.to_slot_dict()
    for entry in reversed(ctx.history):
        if entry.node != "ContextSceneVariator":
            continue
        decision_slots = entry.decision.get("slots", {}) if isinstance(entry.decision, dict) else {}
        if isinstance(decision_slots, dict) and decision_slots:
            action_slots = decision_slots
        break
    prompt_debug.update(
        {
            "action_frame": state.action.to_dict(),
            "action_slots": action_slots,
            "action_frame_matches_debug_slots": state.action.to_slot_dict() == action_slots,
        }
    )
    updated_ctx = patch_context(ctx, updates={"seed": seed}, extras=state.to_extras_patch())
    updated_ctx = append_history(
        updated_ctx,
        DebugInfo(
            node="ContextPromptBuilder",
            seed=seed,
            decision={**prompt_debug, "prompt": prompt},
        ),
    )
    return updated_ctx, prompt
