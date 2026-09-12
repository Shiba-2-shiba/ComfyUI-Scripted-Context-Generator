"""Isolated N2.7 experiment bridge; never imported by the active checkout."""
from dataclasses import replace
from copy import deepcopy
import json
import random

from .prompt_realizer import coerce_action_frame, realize_content_plan
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


def render_candidate(plan, legacy_template, legacy_debug, frame, surface, replacements, seed, *,
                     producer_context=None, common_inputs=None, audit_sink=None):
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
    selected = None
    common_route = False
    common_proofs = ()

    def emit_snapshot(text, debug):
        if audit_sink is not None:
            # Diagnostic objects never share mutable state with inputs or results.
            # JSON round-trip also turns internal tuples into plain JSON arrays.
            audit_sink(json.loads(json.dumps(deepcopy({
                'input_plan': plan.to_dict(),
                'concrete_plan': concrete.to_dict(),
                'frame': coerce_action_frame(frame).to_dict(),
                'source_surface': surface,
                'surface': actual_surface,
                'replacements': replacements,
                'producer_context': producer_context,
                'eligibility': eligibility,
                'selectable': selectable,
                'selected': selected,
                'direct_provenance': provenance,
                'structural_evidence_used': structural_evidence is not None,
                'output_debug': debug,
                'output_template': text,
                'common_route': common_route,
                'common_inputs': common_inputs,
                'common_proofs': common_proofs,
            }))))

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
            debug = {**debug, "candidate_v2_applied": True, "candidate_eligibility": eligibility}
            emit_snapshot(text, debug)
            return text, actual, debug

    # Preserve every accepted compatibility output. New proofs are considered
    # only after that path actually falls back, never via a seed allowlist.
    values = dict(replacements)
    current_fields = {'subject': '{subj}', 'clothing': '{costume}', 'scene': '{loc}',
                      'action': '{action}', 'garnish': '{garnish}', 'mood': '{meta_mood}'}
    if (isinstance(common_inputs, dict) and common_inputs.get('composition_mode') is True
            and common_inputs.get('seed') == seed
            and common_inputs.get('action_frame') == coerce_action_frame(frame).to_dict()
            and all(common_inputs.get(field) == values.get(token) for field, token in current_fields.items())):
        from .realization_evidence import build_realization_evidence
        from .family_capabilities import prove_all_families, construct_family, family_proof_to_dict
        try:
            common_evidence = build_realization_evidence(common_inputs)
        except (TypeError, ValueError):
            # Optional legacy context fields can be noncanonical JSON values.
            # They supply no common proof; preserve the existing fallback.
            common_evidence = None
        proofs = (prove_all_families(plan, common_evidence, builder_inputs=common_inputs)
                  if common_evidence is not None else ())
        common_selectable = sorted(proof.family for proof in proofs if proof.eligible)
        if common_selectable:
            common_selected = random.Random(mix_seed(seed, 'realizer_v2_candidate_family')).choice(common_selectable)
            requested = replace(plan, syntax_family=common_selected)
            text, common_debug = realize_content_plan(
                requested, realization_evidence=common_evidence, builder_inputs=common_inputs, return_debug=True)
            if common_debug['realizer_version'] != 'v2' or common_debug['syntax_family'] != common_selected:
                raise ValueError('Common family proof/constructor mismatch')
            selected_proof = next(proof for proof in proofs if proof.family == common_selected)
            actual, _ = construct_family(plan, common_evidence, selected_proof, builder_inputs=common_inputs)
            # Full proof and transform receipts stay in the audit snapshot only.
            debug = {key: value for key, value in common_debug.items()
                     if key not in {'family_proof', 'transform_rule_ids'}}
            debug['candidate_v2_applied'] = True
            common_route, selected, selectable, concrete = True, common_selected, common_selectable, actual
            if audit_sink is not None:
                common_proofs = [family_proof_to_dict(proof) for proof in proofs]
            emit_snapshot(text, debug)
            return text, actual, debug

    # Preserve exact v1 realization, including its preselected sentence structure.
    # Map only its documented structural identity; never claim this executed v2.
    old_family = legacy_debug["syntax_family"]
    fallback_family = _FALLBACK[old_family]
    actual = replace(plan, syntax_family=fallback_family, clause_order=tuple(legacy_debug["clause_order"]))
    debug = {**legacy_debug, "syntax_family": fallback_family,
             "eligible_syntax_families": [_FALLBACK[key] for key in legacy_debug["eligible_syntax_families"]],
             "syntax_fallback_reason": "candidate_ineligible_preserve_v1",
             "fallback_origin_syntax_family": old_family,
             "candidate_v2_applied": False, "candidate_eligibility": eligibility}
    emit_snapshot(legacy_template, debug)
    return legacy_template, actual, debug
