"""Isolated N2.7 experiment bridge; never imported by the active checkout."""
from dataclasses import replace
import random

from .prompt_realizer import realize_content_plan
from .syntax_family_selector import candidate_family_safe, eligible_syntax_families
from .v2_direct_provenance import materialize_direct
from .v2_structural_evidence import build_structural_evidence
try:
    from ..vocab.seed_utils import mix_seed
except ImportError:
    from vocab.seed_utils import mix_seed


FAMILIES = (
    "subject_action_scene", "subject_action__scene_tail", "scene_lead_subject_action",
    "action_lead_subject_scene", "subject_scene_action", "subject_action_scene_insert",
)
_FALLBACK = {"single-sentence-scene-tail": "subject_action_scene", "two-sentence-scene-tail": "subject_action__scene_tail"}


def render_candidate(plan, legacy_template, legacy_debug, frame, surface, replacements, seed, *, producer_context=None):
    def resolve(value):
        for token, replacement in replacements:
            value = value.replace(token, str(replacement) if replacement is not None else "")
        return value

    slots = dict(plan.semantic_slots)
    for key in ("subject", "adjunct", "scene"):
        slots[key] = resolve(slots.get(key, ""))
    concrete = replace(plan, semantic_slots=slots)
    actual_surface = {**surface, "rendered_clause": slots["adjunct"]}
    evidence = {'slots': dict(plan.semantic_slots), 'replacements': replacements, 'surface': surface}
    if isinstance(producer_context, dict):
        evidence['character_palette'] = producer_context.get('character_palette', ())
    replay = build_structural_evidence(frame, dict(replacements).get('{action}', ''))
    direct_slots = materialize_direct(evidence, frame)
    structural_evidence = None
    if direct_slots is None:
        structural_evidence = replay
        if structural_evidence is not None:
            direct_slots = materialize_direct(evidence, frame, structural_evidence=structural_evidence)
        if direct_slots is None:
            structural_evidence = None
    provenance = evidence if direct_slots is not None else None
    if direct_slots is not None:
        concrete = replace(plan, semantic_slots=direct_slots)
        actual_surface = {**surface, 'rendered_clause': direct_slots['adjunct']}
    eligible, eligibility = eligible_syntax_families(concrete, frame, actual_surface, return_debug=True,
                                                     direct_provenance=provenance,
                                                     structural_evidence=structural_evidence)
    selectable = sorted(key for key in eligible if not eligibility['direct_provenance_valid']
                        or key in eligibility['direct_supported_families'])
    selectable = [key for key in selectable if candidate_family_safe(key, eligibility, structural_evidence=structural_evidence)]
    if selectable:
        selected = random.Random(mix_seed(seed, "realizer_v2_candidate_family")).choice(selectable)
        # Bind the actual constructor output for the selected family; changing
        # a family label alone must not authorize a different scene surface.
        selected_slots = (materialize_direct(provenance, frame, syntax_family=selected,
                                            structural_evidence=structural_evidence)
                          if eligibility['direct_provenance_valid'] else concrete.semantic_slots)
        requested = replace(concrete, syntax_family=selected, semantic_slots=selected_slots)
        text, debug = realize_content_plan(requested, action_frame=frame, action_surface=actual_surface,
                                          return_debug=True, direct_provenance=provenance,
                                          structural_evidence=structural_evidence)
        if debug["realizer_version"] == "v2":
            actual = replace(requested, syntax_family=debug["syntax_family"], clause_order=tuple(debug["clause_order"]))
            return text, actual, {**debug, "candidate_v2_applied": True, "candidate_eligibility": eligibility}

    # Preserve exact v1 realization, including its preselected sentence structure.
    # Map only its documented structural identity; never claim this executed v2.
    old_family = legacy_debug["syntax_family"]
    selected = _FALLBACK[old_family]
    actual = replace(plan, syntax_family=selected, clause_order=tuple(legacy_debug["clause_order"]))
    debug = {**legacy_debug, "syntax_family": selected,
             "eligible_syntax_families": [_FALLBACK[key] for key in legacy_debug["eligible_syntax_families"]],
             "syntax_fallback_reason": "candidate_ineligible_preserve_v1",
             "fallback_origin_syntax_family": old_family,
             "candidate_v2_applied": False, "candidate_eligibility": eligibility}
    return legacy_template, actual, debug
