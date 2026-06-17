if __package__ and "." in __package__:
    from ..clothing_service import resolve_clothing_theme
    from ..core.context_state import generation_state_from_context
    from ..core.context_ops import append_history, ensure_context, patch_context
    from ..core.schema import DebugInfo
    from ..history_service import (
        recent_clothing_packs,
        recent_clothing_signatures,
        recent_clothing_types,
        recent_outerwear_packs,
    )
    from ..location_service import resolve_location_key
    from .clothing_candidate_selector import select_clothing_candidate
    from .clothing_semantics import (
        build_clothing_target_vector,
        clothing_semantic_debug_payload,
    )
    from .semantic_epig import add_semantic_debug, domain_enabled, semantic_mode
else:
    from clothing_service import resolve_clothing_theme
    from core.context_state import generation_state_from_context
    from core.context_ops import append_history, ensure_context, patch_context
    from core.schema import DebugInfo
    from history_service import (
        recent_clothing_packs,
        recent_clothing_signatures,
        recent_clothing_types,
        recent_outerwear_packs,
    )
    from location_service import resolve_location_key
    from pipeline.clothing_candidate_selector import select_clothing_candidate
    from pipeline.clothing_semantics import (
        build_clothing_target_vector,
        clothing_semantic_debug_payload,
    )
    from pipeline.semantic_epig import add_semantic_debug, domain_enabled, semantic_mode

VALID_OUTFIT_MODES = ("random", "dresses", "separates", "outerwear_only", "no_outerwear")


def expand_clothing_prompt(
    theme_key,
    seed,
    outfit_mode,
    outerwear_chance,
    character_palette="",
    loc="",
    recent_packs=None,
    recent_types=None,
    recent_outerwear=None,
    recent_signatures=None,
    return_debug=False,
    action_text="",
):
    try:
        seed = int(seed)
    except Exception:
        seed = 0
    if outfit_mode not in VALID_OUTFIT_MODES:
        outfit_mode = "random"
    recent_packs = {str(item) for item in (recent_packs or []) if item}
    recent_types = {str(item) for item in (recent_types or []) if item}
    recent_outerwear = {str(item) for item in (recent_outerwear or []) if item}
    recent_signatures = {str(item) for item in (recent_signatures or []) if item}
    clothing_tpo_enabled = domain_enabled("clothing_tpo")
    clothing_tpo_mode = semantic_mode("clothing_tpo")
    clothing_tpo_active = clothing_tpo_enabled and clothing_tpo_mode == "active"
    clothing_target_vector = {}
    if clothing_tpo_enabled:
        clothing_target_vector = build_clothing_target_vector(
            resolve_location_key(loc) or loc,
            action_text=action_text,
            theme_key=resolve_clothing_theme(theme_key) or theme_key,
        )

    prompt, decision, candidate_scores, baseline_selected_attempt_index = select_clothing_candidate(
        theme_key,
        seed,
        outfit_mode,
        outerwear_chance,
        character_palette,
        recent_packs=recent_packs,
        recent_types=recent_types,
        recent_outerwear=recent_outerwear,
        recent_signatures=recent_signatures,
        clothing_tpo_enabled=clothing_tpo_enabled,
        clothing_tpo_active=clothing_tpo_active,
        clothing_target_vector=clothing_target_vector,
        loc=loc,
    )
    if clothing_tpo_enabled:
        add_semantic_debug(
            decision,
            "clothing_tpo",
            clothing_semantic_debug_payload(
                mode=clothing_tpo_mode,
                target_vector=clothing_target_vector,
                candidate_scores=candidate_scores,
                selected_attempt_index=decision.get("attempt_index", 0),
                baseline_selected_attempt_index=baseline_selected_attempt_index,
                semantic_selected_attempt_index=decision.get("attempt_index", 0),
                selected_by_semantic=clothing_tpo_active,
            ),
        )
    return (prompt, decision) if return_debug else prompt


def apply_clothing_expansion(context, seed, outfit_mode, outerwear_chance, character_palette=""):
    ctx = ensure_context(context, default_seed=int(seed))
    state = generation_state_from_context(ctx)
    raw_theme_key = state.clothing.raw_costume_key or ctx.costume
    theme_key = resolve_clothing_theme(raw_theme_key) or raw_theme_key
    raw_loc_key = state.location.raw_loc_tag or ctx.loc
    palette_value = character_palette or state.character.palette_text
    clothing_prompt, decision = expand_clothing_prompt(
        theme_key,
        seed,
        outfit_mode,
        outerwear_chance,
        palette_value,
        loc=raw_loc_key,
        recent_packs=recent_clothing_packs(ctx),
        recent_types=recent_clothing_types(ctx),
        recent_outerwear=recent_outerwear_packs(ctx),
        recent_signatures=recent_clothing_signatures(ctx),
        return_debug=True,
        action_text=ctx.action,
    )
    state.character.palette_text = palette_value
    state.character.palette = [item.strip() for item in palette_value.split(",") if item.strip()] if palette_value else []
    state.clothing.raw_costume_key = raw_theme_key
    state.clothing.resolved_theme = theme_key
    state.clothing.clothing_prompt = clothing_prompt
    ctx = patch_context(
        ctx,
        updates={"seed": seed, "costume": theme_key},
        extras=state.to_extras_patch(),
    )
    ctx = append_history(
        ctx,
        DebugInfo(
            node="ContextClothingExpander",
            seed=seed,
            decision=decision,
        ),
    )
    return ctx, clothing_prompt
