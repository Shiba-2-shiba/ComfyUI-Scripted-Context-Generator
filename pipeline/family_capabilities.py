"""Common family proof from current producer evidence; no ordinary selection.

Every public entry reconstructs evidence from current inputs. A frozen proof or
matching digest supplied by a caller cannot grant permission by itself.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
import hashlib

from .realization_evidence import (
    DOMAINS, FamilyProof, Truth, _canonical, _json_input, validate_evidence_binding,
)
from .action_parser import action_verb
from .v2_clothing_provenance import _materialize_single_garment, _PREFIX_FIELDS
from .v2_direct_provenance import _subject, _GARNISH, _relative_scene
from .v2_leaf_grammar import derive_action_grammar, materialize_action_parts, verified_primary_verbs
from .v2_scene_provenance import common_scene_parts, producer_owned_scene
from .v2_structural_evidence import build_structural_evidence
from .v2_template_provenance import materialize_scene_template, scene_template_kind

if __package__ and '.' in __package__:
    from ..core.schema import ActionFrame
    from ..core.semantic_policy import find_banned_terms
    from ..core.solo_safety import is_solo_safe_text
    from ..object_focus_service import extract_action_object_flags
    from ..vocab.loader import load_json
    from ..vocab.syntax_families import CATALOG_FILENAME, SAFETY_FACTS, validate_syntax_family_catalog
else:
    from core.schema import ActionFrame
    from core.semantic_policy import find_banned_terms
    from core.solo_safety import is_solo_safe_text
    from object_focus_service import extract_action_object_flags
    from vocab.loader import load_json
    from vocab.syntax_families import CATALOG_FILENAME, SAFETY_FACTS, validate_syntax_family_catalog


_STANDALONE = 'subject_action__scene_tail'
_ACTION_LEAD = 'action_lead_subject_scene'
_ORDERS = {
    'scene_lead_subject_action': ('scene', 'subject', 'action'),
    _ACTION_LEAD: ('action', 'subject', 'scene'),
    'subject_scene_action': ('subject', 'scene', 'action'),
}


def _digest(value):
    return hashlib.sha256(_canonical(_json_input(value))).hexdigest()


def _catalog(value):
    current = load_json(CATALOG_FILENAME)
    catalog = current if value is None else value
    issues = validate_syntax_family_catalog(catalog)
    if issues or _digest(catalog) != _digest(current):
        raise ValueError('Family catalog must match the validated current source catalog')
    return catalog


def _clothing(component):
    # The validated trace already identifies one selected pack and unique fields.
    # Reuse the nominal constructor without searching other packs a second time.
    parts = component.trace.parts
    garment = next(part.text for part in parts if part.part_id == 'clothing:garment')
    prefixes = tuple(next((part.text for part in parts if part.part_id == 'clothing:' + field), '')
                     for field in _PREFIX_FIELDS)
    details = tuple((part.source.field.removeprefix('palette.'), part.text)
                    for part in parts if part.part_id.startswith('clothing:detail:'))
    return _materialize_single_garment(garment, prefixes, details)


def _prepare(plan, evidence, inputs, producer_context):
    """Once-per-call current binding and common materialization, never a cache."""
    from .prompt_realizer import ContentPlan, build_content_plan
    if __package__ and '.' in __package__:
        from ..prompt_renderer import _derive_action_surface, _derive_template_roles, _render_action_clause
    else:
        from prompt_renderer import _derive_action_surface, _derive_template_roles, _render_action_clause

    facts = dict.fromkeys(sorted(SAFETY_FACTS), Truth.UNKNOWN)
    result = {'facts': facts, 'blockers': [], 'inputs': inputs}
    if type(plan) is not ContentPlan or not isinstance(inputs, Mapping):
        result['blockers'].append('binding.plan_or_inputs_missing')
        return result
    if not validate_evidence_binding(evidence, inputs, producer_context=producer_context):
        result['blockers'].append('binding.evidence_mismatch')
        return result
    components = {component.domain: component for component in evidence.components}
    for domain in DOMAINS:
        component = components[domain]
        if not component.runtime_available or component.trace is None:
            result['blockers'].append(domain + '.source_unavailable')
        result['blockers'].extend(component.blockers)
        if any(atom.grammar_known is not Truth.TRUE for atom in component.atoms):
            result['blockers'].append(domain + '.grammar_unknown')
        if not component.atoms and domain != 'garnish':
            result['blockers'].append(domain + '.atoms_missing')
    required = ('subject', 'clothing', 'action', 'scene', 'garnish', 'mood')
    if any(not isinstance(inputs.get(key), str) for key in required) or type(inputs.get('seed')) is not int:
        result['blockers'].append('transport.current_inputs_missing')
    if result['blockers']:
        return result
    slots, selected = inputs['template_slots'], inputs['selected_templates']
    action, garnish, mood, scene = (inputs[key] for key in ('action', 'garnish', 'mood', 'scene'))
    roles = _derive_template_roles(action, garnish, mood, scene)
    _, surface = _render_action_clause(action, garnish, _derive_action_surface(action), selected['body'])
    expected = build_content_plan(
        seed=inputs['seed'], subject_clause=slots['subject'], action_clause=slots['adjunct'],
        scene_clause=slots['scene'], action_frame=inputs['action_frame'], template_roles=roles,
        template_keys=[selected[part]['key'] for part in ('intro', 'body', 'end')],
        action_surface=surface, syntax_family=plan.syntax_family,
    )
    if _digest(expected.to_dict()) != _digest(plan.to_dict()):
        result['blockers'].append('binding.plan_mismatch')
    context = inputs.get('context', {})
    if not isinstance(context, Mapping) or context.get('action') != action:
        result['blockers'].append('binding.received_action_mismatch')
    frame = ActionFrame.from_dict(inputs['action_frame'])
    # This is the producer's semantic projection, not a noun inferred from the
    # rendered English. For example clipboard is intentionally not an object flag.
    objects = sorted(extract_action_object_flags(action))
    projected_frame = ActionFrame.from_slots(
        frame.legacy_slots, legacy_text=action, main_verb=action_verb(action),
        primary_object=objects[0] if objects else '',
    )
    if _digest(inputs['action_frame']) != _digest(projected_frame.to_dict()):
        result['blockers'].append('binding.semantic_frame_projection_mismatch')
    received_frame = context.get('extras', {}).get('action_frame')
    if received_frame is not None and _digest(received_frame) != _digest(inputs['action_frame']):
        result['blockers'].append('binding.received_frame_mismatch')
    structural = build_structural_evidence(frame, action)
    grammar = derive_action_grammar(structural)
    heads = verified_primary_verbs(structural)
    semantic_verb = grammar.main_verb
    if structural is not None and ' and ' in structural.emitted_parts[0].text:
        semantic_verb = action_verb(action) if len(heads) > 1 else None
        if semantic_verb not in heads:
            semantic_verb = None
    frame_safe = (grammar.frame_predicate_safe is True and bool(semantic_verb)
                  and frame.main_verb == semantic_verb
                  and _digest(inputs['action_frame']) == _digest(projected_frame.to_dict())
                  and surface.get('surface') == grammar.surface_kind)
    if not frame_safe:
        result['blockers'].append('binding.semantic_frame_mismatch')
    if 'action_surface' in inputs and _digest(inputs['action_surface']) != _digest(surface):
        result['blockers'].append('binding.surface_mismatch')
    if 'template_roles' in inputs and _digest(inputs['template_roles']) != _digest(roles):
        result['blockers'].append('binding.roles_mismatch')
    joined = ' '.join(inputs[key] for key in required)
    if find_banned_terms(joined) or not is_solo_safe_text(joined):
        result['blockers'].append('policy.conflict')
    subject = _subject(inputs['subject'])
    clothes = _clothing(components['clothing'])
    rendered_action = materialize_action_parts(structural)
    if subject is None or clothes is None or rendered_action is None:
        result['blockers'].append('constructor.common_component_unavailable')
        return result
    garnish_parts = [(_GARNISH[tag] if tag in _GARNISH else tag)
                     for tag in (garnish.split(', ') if garnish else ())]
    action_text = ', '.join((rendered_action, *garnish_parts))
    same_subject = all(atom.same_subject is Truth.TRUE and atom.grammatical_subject_id == 'protagonist'
                       for atom in components['action'].atoms)
    facts.update(
        frame_predicate_safe=Truth.TRUE if frame_safe else Truth.FALSE,
        fragment_subject_action=Truth.FALSE,
        independent_action_subject=(Truth.FALSE if grammar.independent_action_subject is False
                                    else Truth.TRUE if grammar.independent_action_subject is True else Truth.UNKNOWN),
        same_subject_attachment_safe=Truth.TRUE if same_subject and grammar.surface_kind == 'gerund' else Truth.FALSE,
        scene_action_overlap=Truth.FALSE if grammar.no_place_reference is True else Truth.UNKNOWN,
        scene_action_nonduplicative=Truth.TRUE if grammar.no_place_reference is True else Truth.UNKNOWN,
    )
    transforms = ['subject.profile_nominal/v1', 'clothing.selected_nominal/v1']
    transforms.extend('action.with_absolute/v1' for atom in components['action'].atoms if atom.attachment == 'with_absolute')
    if garnish_parts:
        transforms.append('garnish.existing_attachment/v1')
    result.update(components=components, frame=frame, surface=surface, subject=subject + ' in ' + clothes,
                  action=action_text, actor_action=rendered_action, garnish_parts=tuple(garnish_parts),
                  template_kind=scene_template_kind(slots),
                  location_key=components['scene'].trace.parts[0].source.catalog_key,
                  transforms=transforms)
    return result


def _family_construction(family, plan, prepared):
    inputs = prepared['inputs']
    if prepared['template_kind'] == 'owned_finite' and family == _ACTION_LEAD:
        return None, (), 'template.absolute_not_locative_predicate'
    scene = inputs['scene']
    if family == _STANDALONE and prepared['template_kind'] == 'direct':
        parts = common_scene_parts(scene, prepared['location_key'])
        scene_text = ', '.join((*parts[:1], *parts[1], 'with ' + inputs['mood'])) if parts else None
        scene_rule = 'scene.standalone_constituents/v1'
    elif prepared['components']['scene'].trace.constructor_id == 'scene.reviewed_legacy_constituents/v1':
        # Reuse the exact reviewed constructor only on its newly source-bound
        # route. This does not authorize arbitrary temporal/adorned movement.
        parts = common_scene_parts(scene, prepared['location_key'])
        scene_text = _relative_scene((*parts, 'with ' + inputs['mood'])) if parts else None
        scene_rule = 'scene.reviewed_legacy_relative/v1'
    else:
        owned = producer_owned_scene(scene, prepared['location_key'])
        scene_text = owned + ', with ' + inputs['mood'] if owned is not None else None
        scene_rule = 'scene.owner_relative/v1'
    if scene_text is None:
        return None, (), 'scene.placement_constructor_unknown'
    attachment = 'absolute' if prepared['template_kind'] == 'owned_finite' and family != _STANDALONE else 'finite'
    scene_text = materialize_scene_template(inputs['template_slots'], scene_text, attachment=attachment)
    if scene_text is None:
        return None, (), 'template.constructor_unknown'
    slots = {**plan.semantic_slots, 'subject': prepared['subject'], 'adjunct': prepared['action'], 'scene': scene_text}
    garnish_subject = family == _ACTION_LEAD and bool(prepared['garnish_parts'])
    if garnish_subject:
        if any(atom.owner_id != 'protagonist' or atom.attachment not in {'with_absolute', 'with_nominal', 'shared_modifier'}
               for atom in prepared['components']['garnish'].atoms):
            return None, (), 'garnish.subject_attachment_unknown'
        slots['subject'] += ', ' + ', '.join(prepared['garnish_parts'])
        slots['adjunct'] = prepared['actor_action']
    concrete = replace(plan, semantic_slots=slots, syntax_family=family,
                       clause_order=_ORDERS.get(family, ('subject', 'action', 'scene')))
    transforms = [*prepared['transforms'], scene_rule, 'mood.with_absolute/v1']
    if prepared['template_kind'] == 'owned_finite':
        transforms.append('template.owned_absolute/v1' if attachment == 'absolute' else 'template.staying_to_stays/v1')
    if garnish_subject:
        transforms.append('garnish.subject_parenthetical/v1')
    transforms.extend(('family.layout:' + family + '/v1', 'surface.existing_normalization/v1'))
    return concrete, tuple(dict.fromkeys(transforms)), None


def _proof(family, plan, evidence, prepared, catalog):
    entry = next((entry for entry in catalog['families'] if entry['key'] == family), None)
    blockers = list(prepared['blockers'])
    facts = dict(prepared['facts'])
    concrete, transforms = None, ()
    if entry is None:
        blockers.append('family.unknown')
    if not blockers:
        concrete, transforms, blocker = _family_construction(family, plan, prepared)
        if blocker:
            blockers.append(blocker)
        placement = Truth.TRUE if concrete is not None else Truth.UNKNOWN
        facts.update(standalone_scene_safe=placement if family == _STANDALONE else Truth.UNKNOWN,
                     scene_lead_safe=placement if family == 'scene_lead_subject_action' else Truth.UNKNOWN,
                     scene_adjunct_safe=placement if family in {'subject_scene_action', 'subject_action_scene_insert'} else Truth.UNKNOWN)
        if '*' not in entry['roles'] and not set(plan.discourse_roles).intersection(entry['roles']):
            blockers.append('family.role_mismatch')
        surface = prepared['surface']['surface']
        if (('*' not in entry['allowed_action_surfaces'] and surface not in entry['allowed_action_surfaces'])
                or surface in entry['avoid_action_surfaces']):
            blockers.append('family.surface_not_allowed')
        for slot in entry['required_slots']:
            if concrete is None or not concrete.semantic_slots.get(slot):
                blockers.append('family.missing_slot:' + slot)
        for fact in entry['requires']:
            if facts[fact] is not Truth.TRUE:
                blockers.append('family.required_fact_not_true:' + fact)
        for fact in entry['forbids']:
            if facts[fact] is not Truth.FALSE:
                blockers.append('family.forbidden_fact_not_false:' + fact)
        # Baseline metadata is an unconditional fallback marker; actual common
        # v2 always requires the same explicit frame/subject/scene protections.
        if facts['frame_predicate_safe'] is not Truth.TRUE:
            blockers.append('family.frame_unproved')
        if facts['independent_action_subject'] is not Truth.FALSE:
            blockers.append('family.independent_subject')
        if family != _STANDALONE and facts['scene_action_overlap'] is not Truth.FALSE:
            blockers.append('family.scene_overlap_unknown')
        if family == _ACTION_LEAD and facts['same_subject_attachment_safe'] is not Truth.TRUE:
            blockers.append('family.action_lead_subject_unknown')
    eligible = not blockers and concrete is not None
    atom_map = tuple((atom.atom_id, 'subject' if domain in {'subject', 'clothing'}
                      or domain == 'garnish' and 'garnish.subject_parenthetical/v1' in transforms else
                      'adjunct' if domain in {'action', 'garnish'} else 'scene' if domain in {'scene', 'mood'} else atom.attachment)
                     for domain in DOMAINS for atom in prepared['components'][domain].atoms) if 'components' in prepared else ()
    proof = FamilyProof(
        family, getattr(evidence, 'input_binding_sha256', ''),
        _digest(plan.to_dict()) if hasattr(plan, 'to_dict') else '',
        _digest(catalog), _digest(concrete.to_dict()) if eligible else None,
        'common_family:' + family + '/v1' if eligible else None, eligible,
        tuple(sorted(facts.items())), tuple(sorted(set(blockers))), transforms if eligible else (),
        atom_map if eligible else (),
    )
    return proof, concrete


def prove_family(family, plan, evidence, *, builder_inputs, producer_context=None, catalog=None):
    metadata = _catalog(catalog)
    prepared = _prepare(plan, evidence, builder_inputs, producer_context)
    return _proof(family, plan, evidence, prepared, metadata)[0]


def prove_all_families(plan, evidence, *, builder_inputs, producer_context=None, catalog=None):
    metadata = _catalog(catalog)
    prepared = _prepare(plan, evidence, builder_inputs, producer_context)
    return tuple(_proof(entry['key'], plan, evidence, prepared, metadata)[0]
                 for entry in sorted(metadata['families'], key=lambda entry: entry['key']))


def construct_family(plan, evidence, proof, *, builder_inputs, producer_context=None, catalog=None):
    if type(proof) is not FamilyProof:
        raise ValueError('A current FamilyProof is required')
    metadata = _catalog(catalog)
    prepared = _prepare(plan, evidence, builder_inputs, producer_context)
    current, concrete = _proof(proof.family, plan, evidence, prepared, metadata)
    if not current.eligible or not _same_proof(proof, current):
        raise ValueError('Family proof is stale, forged or ineligible')
    return concrete, current.transform_rule_ids


def _same_proof(left, right):
    try:
        return (type(left) is FamilyProof and type(right) is FamilyProof and left == right
                and _canonical(family_proof_to_dict(left)) == _canonical(family_proof_to_dict(right)))
    except (AttributeError, TypeError, ValueError):
        return False


def family_proof_to_dict(proof):
    if type(proof) is not FamilyProof:
        raise TypeError('Expected FamilyProof')
    return {
        'family': proof.family, 'input_binding_sha256': proof.input_binding_sha256,
        'plan_binding_sha256': proof.plan_binding_sha256, 'catalog_binding_sha256': proof.catalog_binding_sha256,
        'construction_binding_sha256': proof.construction_binding_sha256, 'constructor_id': proof.constructor_id,
        'eligible': proof.eligible, 'facts': {key: value.value for key, value in proof.facts},
        'blocker_ids': list(proof.blocker_ids), 'transform_rule_ids': list(proof.transform_rule_ids),
        'source_atom_map': [list(pair) for pair in proof.source_atom_map],
    }


def realize_common_plan(plan, evidence, *, builder_inputs, producer_context=None, catalog=None, proof=None, return_debug=False):
    from .prompt_realizer import _render_family_surface, _realize_content_plan_v1
    proofs = prove_all_families(plan, evidence, builder_inputs=builder_inputs,
                               producer_context=producer_context, catalog=catalog)
    chosen = next((item for item in proofs if item.family == plan.syntax_family), None)
    eligible = [item.family for item in proofs if item.eligible]
    if proof is not None and not _same_proof(proof, chosen):
        chosen = None
    if chosen is not None and chosen.eligible:
        concrete, transforms = construct_family(plan, evidence, chosen, builder_inputs=builder_inputs,
                                               producer_context=producer_context, catalog=catalog)
        surface = {'surface': concrete.lexical_choice}
        finite = scene_template_kind(builder_inputs['template_slots']) == 'owned_finite'
        text = _render_family_surface(concrete, action_surface=surface, scene_is_finite=finite,
            subject_parenthetical='garnish.subject_parenthetical/v1' in transforms)
        debug = {'realizer_version': 'v2', 'requested_syntax_family': plan.syntax_family,
                 'syntax_family': chosen.family, 'eligible_syntax_families': eligible,
                 'syntax_fallback_reason': '', 'clause_order': list(concrete.clause_order),
                 'family_proof': family_proof_to_dict(chosen), 'transform_rule_ids': list(transforms)}
    else:
        fallback = replace(plan, syntax_family='single-sentence-scene-tail', clause_order=('subject', 'action', 'scene'))
        text = _realize_content_plan_v1(fallback)
        debug = {'realizer_version': 'v1', 'requested_syntax_family': plan.syntax_family,
                 'syntax_family': 'subject_action_scene', 'eligible_syntax_families': eligible,
                 'syntax_fallback_reason': 'common_family_unproved', 'clause_order': list(fallback.clause_order)}
    return (text, debug) if return_debug else text
