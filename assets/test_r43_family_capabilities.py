"""Family authorization uses bound producers; fixtures are labelled recombinations."""
import copy
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
from unittest import mock

import pytest

import prompt_renderer
from core.schema import ActionFrame
from history_service import clothing_signature_digest, clothing_signature_from_decision
from pipeline.action_renderer import render_action_slots
from pipeline.action_parser import action_verb
from pipeline.character_profile_pipeline import build_character_profile, load_character_profiles
from pipeline.clothing_candidate_renderer import build_variant_signature
from pipeline.prompt_realizer import build_content_plan, realize_content_plan
from pipeline.realization_evidence import Truth, build_realization_evidence
from object_focus_service import extract_action_object_flags
from vocab.loader import load_json


FAMILIES = (
    'subject_action_scene', 'subject_action__scene_tail', 'scene_lead_subject_action',
    'action_lead_subject_scene', 'subject_scene_action', 'subject_action_scene_insert',
)


def plan_for_inputs(inputs, family='subject_action_scene'):
    selected = inputs['selected_templates']
    _, surface = prompt_renderer._render_action_clause(
        inputs['action'], inputs['garnish'],
        prompt_renderer._derive_action_surface(inputs['action']), selected['body'])
    return build_content_plan(
        seed=inputs['seed'], subject_clause=inputs['template_slots']['subject'],
        action_clause=inputs['template_slots']['adjunct'], scene_clause=inputs['template_slots']['scene'],
        action_frame=inputs['action_frame'],
        template_roles=prompt_renderer._derive_template_roles(
            inputs['action'], inputs['garnish'], inputs['mood'], inputs['scene']),
        template_keys=tuple(selected[section]['key'] for section in ('intro', 'body', 'end')),
        action_surface=surface, syntax_family=family)


def fixture_case(family='subject_action_scene'):
    spec = json.loads((Path(__file__).parent / 'fixtures/r43_family_recombinations.json').read_text())
    assert spec['classification'] == 'RECOMBINATION'
    profile = build_character_profile(0, 'fixed', spec['subject_profile'], load_character_profiles())
    clothing = spec['clothing']
    clothing_text = clothing['color'] + ' ' + clothing['garment']
    decision = {
        'theme': clothing['theme'], 'chosen_type': clothing['type'], 'base_pack': clothing['pack'],
        'base_variant': build_variant_signature([clothing['garment'], clothing['color'], '', '', '']),
        'outerwear_pack': '', 'outerwear_variant': '', 'attempt_index': 0,
    }
    decision['signature'] = clothing_signature_digest(clothing_signature_from_decision(decision))
    action = render_action_slots(spec['action_slots'], activity_first=True)
    frame = ActionFrame.from_slots(spec['action_slots'], legacy_text=action,
        main_verb=spec['main_verb'], primary_object=spec['primary_object']).to_dict()
    scene = spec['scene']
    context = {
        'subj': profile['subj_prompt'], 'costume': clothing['theme'], 'loc': scene['pack'],
        'action': action, 'meta': {'mood': spec['mood']},
        'extras': {
            'character_name': spec['subject_profile'], 'hair_color': profile['hair_color'],
            'eye_color': profile['eye_color'], 'color_palette': profile['color_palette'],
            'character_palette_str': profile['color_palette_str'],
            'clothing_prompt': clothing_text, 'raw_costume_key': clothing['theme'],
            'location_prompt': scene['environment'], 'raw_loc_tag': scene['pack'],
            'garnish': ', '.join(spec['garnish_tags']), 'raw_mood_key': spec['mood_key'],
        },
        'history': [
            {'node': 'ContextClothingExpander', 'seed': spec['seed'], 'decision': decision},
            {'node': 'ContextLocationExpander', 'seed': spec['seed'], 'decision': {
                'pack_key': scene['pack'], 'objects': [], 'selected_props': [], 'template_key': scene['mode']}},
            {'node': 'ContextGarnish', 'seed': spec['seed'], 'decision': {'final_tags': spec['garnish_tags']}},
        ],
    }
    selected = {section: copy.deepcopy(next(entry for entry in prompt_renderer._template_entries(section)
        if entry['key'] == key)) for section, key in spec['templates'].items()}
    inputs = {
        'context': context, 'subject': context['subj'], 'clothing': clothing_text,
        'scene': scene['environment'], 'action': action, 'garnish': context['extras']['garnish'],
        'mood': spec['mood'], 'staging_tags': '', 'action_frame': frame, 'seed': spec['seed'],
        'character_palette': profile['color_palette'], 'selected_templates': selected,
        'template_slots': {slot: selected[section]['text']
            for slot, section in (('subject', 'intro'), ('adjunct', 'body'), ('scene', 'end'))},
    }
    return inputs, plan_for_inputs(inputs, family), build_realization_evidence(inputs)


def engine():
    from pipeline import family_capabilities
    return family_capabilities


def test_recombination_has_real_bound_known_producers_in_every_domain():
    inputs, _, evidence = fixture_case()
    frame = inputs['action_frame']
    object_flags = sorted(extract_action_object_flags(inputs['action']))
    expected = ActionFrame.from_slots(frame['legacy_slots'], legacy_text=inputs['action'],
        main_verb=action_verb(inputs['action']), primary_object=object_flags[0] if object_flags else '')
    assert frame == expected.to_dict()
    assert {item.domain for item in evidence.components} == {
        'subject', 'clothing', 'action', 'scene', 'garnish', 'mood', 'template'}
    for item in evidence.components:
        assert item.runtime_available and item.trace is not None, (item.domain, item.blockers)
        assert not item.blockers, (item.domain, item.blockers)
        assert all(atom.grammar_known is Truth.TRUE for atom in item.atoms), item.domain


@pytest.mark.parametrize('family', FAMILIES)
def test_each_family_proves_constructs_and_reaches_requested_surface(family):
    inputs, plan, evidence = fixture_case(family)
    before = copy.deepcopy(inputs), plan.to_dict(), evidence
    proof = engine().prove_family(family, plan, evidence, builder_inputs=inputs)
    assert proof.eligible, proof.blocker_ids
    assert not proof.blocker_ids and proof.constructor_id
    assert proof.input_binding_sha256 == evidence.input_binding_sha256
    with pytest.raises(FrozenInstanceError):
        proof.eligible = False
    concrete, transforms = engine().construct_family(plan, evidence, proof, builder_inputs=inputs)
    assert concrete.syntax_family == family and isinstance(transforms, tuple)
    assert all('{' not in value for value in concrete.semantic_slots.values())
    text, debug = realize_content_plan(plan, realization_evidence=evidence,
        builder_inputs=inputs, family_proof=proof, return_debug=True)
    assert text and '{' not in text and 'clipboard' in text and 'opera house' in text
    assert 'long straight hair' in text and 'dark brown eyes' in text
    assert 'cream cozy sweater dress' in text and inputs['mood'] in text
    assert text.lower().count('girl') == 1
    # Check the text itself: a debug label cannot stand in for realizing a family.
    if family == 'scene_lead_subject_action':
        assert text.lower().startswith('in ')
        assert text.index('opera house') < text.index('girl') < text.index('holding')
    elif family == 'action_lead_subject_scene':
        assert text.lower().startswith('holding the clipboard, ')
        assert text.index('clipboard') < text.index('girl') < text.index('opera house')
    elif family == 'subject_scene_action':
        assert text.index('girl') < text.index('opera house') < text.index('holding')
    else:
        assert text.index('girl') < text.index('holding') < text.index('opera house')
    assert text.count('.') == (2 if family == 'subject_action__scene_tail' else 1)
    assert debug['syntax_family'] == family
    assert not debug['syntax_fallback_reason']
    assert (inputs, plan.to_dict(), evidence) == before


def test_all_family_proofs_can_construct_from_their_shared_source_plan():
    inputs, plan, evidence = fixture_case()
    proofs = engine().prove_all_families(plan, evidence, builder_inputs=inputs)
    assert isinstance(proofs, tuple) and {proof.family for proof in proofs} == set(FAMILIES)
    for proof in proofs:
        assert proof.eligible, (proof.family, proof.blocker_ids)
        concrete, _ = engine().construct_family(plan, evidence, proof, builder_inputs=inputs)
        assert concrete.syntax_family == proof.family


@pytest.mark.parametrize('family', FAMILIES)
def test_current_input_changes_and_forged_grammar_cannot_reuse_a_proof(family):
    inputs, plan, evidence = fixture_case(family)
    proof = engine().prove_family(family, plan, evidence, builder_inputs=inputs)
    assert proof.eligible
    changed = copy.deepcopy(inputs)
    changed['context']['extras']['hair_color'] = 'blue'
    atom = evidence.components[0].atoms[0]
    forged_component = replace(evidence.components[0], atoms=(replace(atom, owner_id='other'),))
    forged_evidence = replace(evidence, components=(forged_component, *evidence.components[1:]))
    for stale_inputs, stale_evidence in ((changed, evidence), (inputs, forged_evidence)):
        rejected = engine().prove_family(family, plan, stale_evidence, builder_inputs=stale_inputs)
        assert not rejected.eligible and rejected.blocker_ids
        with pytest.raises(ValueError):
            engine().construct_family(plan, stale_evidence, proof, builder_inputs=stale_inputs)


def test_family_label_constructor_and_plan_bindings_are_not_transferable():
    inputs, plan, evidence = fixture_case()
    proof = engine().prove_family(FAMILIES[0], plan, evidence, builder_inputs=inputs)
    for forged in (replace(proof, family=FAMILIES[1]), replace(proof, constructor_id='unbound')):
        with pytest.raises(ValueError):
            engine().construct_family(plan, evidence, forged, builder_inputs=inputs)
    for changed in (
        replace(plan, semantic_slots={**plan.semantic_slots, 'predicate': 'destroying'}),
        replace(plan, semantic_slots={**plan.semantic_slots, 'object': 'book'}),
        replace(plan, semantic_slots={**plan.semantic_slots, 'subject': 'someone else'}),
        replace(plan, discourse_roles=('social',)),
        replace(plan, clause_order=('action', 'subject', 'scene')),
        replace(plan, lexical_choice='framed'),
        replace(plan, named_seed_streams={**plan.named_seed_streams, 'syntax': -1}),
    ):
        rejected = engine().prove_family(FAMILIES[0], changed, evidence, builder_inputs=inputs)
        assert not rejected.eligible and rejected.blocker_ids
        with pytest.raises(ValueError):
            engine().construct_family(changed, evidence, proof, builder_inputs=inputs)


def test_changed_frame_metadata_and_catalog_cannot_reuse_bound_construction():
    inputs, plan, evidence = fixture_case()
    proof = engine().prove_family(FAMILIES[0], plan, evidence, builder_inputs=inputs)
    for field, value in (('main_verb', 'destroying'), ('primary_object', 'book')):
        changed = copy.deepcopy(inputs)
        changed['action_frame'][field] = value
        with pytest.raises(ValueError):
            engine().construct_family(plan, evidence, proof, builder_inputs=changed)
        # Rebinding changed metadata must not turn it into a truthful predicate/object.
        rebound = build_realization_evidence(changed)
        rebuilt_plan = plan_for_inputs(changed)
        rejected = engine().prove_family(FAMILIES[0], rebuilt_plan, rebound, builder_inputs=changed)
        assert not rejected.eligible and rejected.blocker_ids
    catalog = copy.deepcopy(load_json('natural_language_realizer_v2.json'))
    catalog['families'][0]['weight'] = 2.0
    with pytest.raises(ValueError):
        engine().construct_family(plan, evidence, proof, builder_inputs=inputs, catalog=catalog)
    with pytest.raises(ValueError):
        engine().construct_family(plan, evidence, proof, builder_inputs=inputs,
            producer_context={'character_palette': ['different']})


@pytest.mark.parametrize('domain', ('subject', 'clothing', 'scene', 'template', 'garnish', 'mood', 'action'))
def test_missing_source_domain_prevents_every_family(domain):
    inputs, _, _ = fixture_case()
    if domain == 'action':
        inputs.pop('action_frame')
    elif domain == 'template':
        inputs.pop('selected_templates')
    elif domain in ('clothing', 'scene', 'garnish'):
        node = {'clothing': 'ContextClothingExpander', 'scene': 'ContextLocationExpander', 'garnish': 'ContextGarnish'}[domain]
        inputs['context']['history'] = [item for item in inputs['context']['history'] if item['node'] != node]
    else:
        inputs['context']['extras'].pop('character_name' if domain == 'subject' else 'raw_mood_key')
    # Preserve a normally constructed source plan even when its evidence is absent.
    _, plan, _ = fixture_case()
    evidence = build_realization_evidence(inputs)
    proofs = engine().prove_all_families(plan, evidence, builder_inputs=inputs)
    assert all(not proof.eligible and proof.blocker_ids for proof in proofs)


def replace_action(inputs, slots, *, verb='holding', object_name=''):
    action = render_action_slots(slots, activity_first=True)
    inputs['action'] = inputs['context']['action'] = action
    inputs['action_frame'] = ActionFrame.from_slots(slots, legacy_text=action,
        main_verb=verb, primary_object=object_name).to_dict()
    return plan_for_inputs(inputs), build_realization_evidence(inputs)


@pytest.mark.parametrize('extra', (
    {'gaze_target': 'her eyes following the detail'},
    {'obstacle_clause': 'while the inspection ends'},
))
def test_action_leading_rejects_body_or_external_grammatical_subjects(extra):
    inputs, _, _ = fixture_case()
    plan, evidence = replace_action(inputs,
        {'primary_action': 'holding the clipboard', 'location': 'opera_house', **extra})
    action = next(item for item in evidence.components if item.domain == 'action')
    assert all(atom.grammar_known is Truth.TRUE for atom in action.atoms)
    assert any(atom.same_subject is Truth.FALSE for atom in action.atoms)
    proof = engine().prove_family('action_lead_subject_scene', plan, evidence, builder_inputs=inputs)
    assert not proof.eligible and proof.blocker_ids


def test_scene_insert_does_not_treat_unknown_place_overlap_as_absence():
    inputs, _, _ = fixture_case()
    plan, evidence = replace_action(inputs,
        {'primary_action': 'sitting in the audience seats', 'location': 'opera_house'},
        verb='sitting', object_name='')
    action = next(item for item in evidence.components if item.domain == 'action')
    assert action.atoms[0].grammar_known is Truth.TRUE
    assert action.atoms[0].place_refs is None
    proof = engine().prove_family('subject_action_scene_insert', plan, evidence, builder_inputs=inputs)
    assert not proof.eligible and proof.blocker_ids


def test_unknown_action_grammar_cannot_become_a_family_capability():
    inputs, _, _ = fixture_case()
    plan, evidence = replace_action(inputs,
        {'primary_action': 'contemplating the unsaid', 'location': 'opera_house'}, verb='contemplating', object_name='')
    action = next(item for item in evidence.components if item.domain == 'action')
    assert any(atom.grammar_known is Truth.UNKNOWN for atom in action.atoms)
    assert all(not proof.eligible for proof in engine().prove_all_families(plan, evidence, builder_inputs=inputs))


def test_ordinary_realizer_remains_unchanged_without_explicit_common_evidence():
    _, plan, _ = fixture_case()
    legacy = replace(plan, syntax_family='single-sentence-scene-tail')
    text, debug = realize_content_plan(legacy, return_debug=True)
    assert text == '{subject_clause}, {action_clause}, {scene_clause}.'
    assert debug['realizer_version'] == 'v1'
    assert debug['syntax_family'] == 'single-sentence-scene-tail'


def test_owned_template_retains_room_owner_with_proved_absolute_alternatives():
    inputs, _, _ = fixture_case()
    end = copy.deepcopy(next(entry for entry in prompt_renderer._template_entries('end')
        if entry['key'] == 'end_scene_room'))
    inputs['selected_templates']['end'] = end
    inputs['template_slots']['scene'] = end['text']
    plan = plan_for_inputs(inputs, 'subject_action__scene_tail')
    evidence = build_realization_evidence(inputs)
    proofs = engine().prove_all_families(plan, evidence, builder_inputs=inputs)
    assert {proof.family for proof in proofs if proof.eligible} == set(FAMILIES) - {'action_lead_subject_scene'}
    text, debug = realize_content_plan(plan, realization_evidence=evidence,
        builder_inputs=inputs, return_debug=True)
    assert '. The room around her stays in a grand historic opera house interior' in text
    assert debug['syntax_family'] == 'subject_action__scene_tail'
    assert not debug['syntax_fallback_reason']


@pytest.mark.parametrize('family', FAMILIES)
def test_gallery_keeps_scene_predicates_and_sibling_reference_under_every_layout(family):
    inputs, _, _ = fixture_case()
    scene = ('small contemporary gallery arranged for a weekday viewing, featuring '
        'framed canvas works spaced along the wall and small title plaques mounted beside each work')
    inputs['scene'] = inputs['context']['extras']['location_prompt'] = scene
    inputs['context']['loc'] = inputs['context']['extras']['raw_loc_tag'] = 'art_gallery'
    history = next(item for item in inputs['context']['history'] if item['node'] == 'ContextLocationExpander')
    history['decision'].update(pack_key='art_gallery', template_key='detailed')
    replace_action(inputs, {'primary_action': 'holding the clipboard', 'location': 'art_gallery'})
    plan, evidence = plan_for_inputs(inputs, family), build_realization_evidence(inputs)
    scene_component = next(item for item in evidence.components if item.domain == 'scene')
    works, plaques = scene_component.atoms[1:]
    assert plaques.antecedent_ids == works.source_part_ids
    proof = engine().prove_family(family, plan, evidence, builder_inputs=inputs)
    assert proof.eligible, proof.blocker_ids
    concrete, _ = engine().construct_family(plan, evidence, proof, builder_inputs=inputs)
    text, debug = realize_content_plan(plan, realization_evidence=evidence,
        builder_inputs=inputs, family_proof=proof, return_debug=True)
    assert 'framed canvas works spaced along the wall' in text
    assert 'small title plaques mounted beside each work' in text
    assert 'weekday viewing' in text and 'holding the clipboard' in text.lower()
    assert debug['syntax_family'] == family and not debug['syntax_fallback_reason']
    assert works.owner_id == plaques.owner_id == 'scene:0'
    assert all(atom.owner_id != 'protagonist' for atom in scene_component.atoms)
    assert {atom.atom_id for atom in scene_component.atoms} <= {
        atom_id for atom_id, slot in proof.source_atom_map if slot == 'scene'}
    if family != 'subject_action__scene_tail':
        assert 'gallery that is arranged for a weekday viewing and that features' in concrete.semantic_slots['scene']


def test_serialized_integer_truth_and_malformed_producer_context_cannot_authorize():
    inputs, plan, evidence = fixture_case()
    proof = engine().prove_family(FAMILIES[0], plan, evidence, builder_inputs=inputs)
    forged = replace(proof, eligible=1)
    assert forged == proof  # Python equality alone cannot distinguish this forgery.
    serialized = engine().family_proof_to_dict(forged)
    assert type(serialized['eligible']) is int
    for value in (forged, serialized):
        with pytest.raises(ValueError):
            engine().construct_family(plan, evidence, value, builder_inputs=inputs)
    for producer_context in ({'unexpected': 'stale'}, object()):
        with pytest.raises(ValueError):
            engine().construct_family(plan, evidence, proof, builder_inputs=inputs,
                producer_context=producer_context)


def test_ambiguous_selected_catalog_origin_invalidates_existing_proof():
    from pipeline import v2_clothing_provenance as clothing
    inputs, plan, evidence = fixture_case()
    proof = engine().prove_family(FAMILIES[0], plan, evidence, builder_inputs=inputs)
    packs = copy.deepcopy(clothing.clothing_vocab.CONCEPT_PACKS)
    # The selected pack already has a structured choice with these exact bytes.
    # A competing bare choice loses the unique source origin despite equal text.
    choices = packs['dresses']['winter_knit_dress']['choices']
    next(iter(choices.values())).append('cozy sweater dress')
    with mock.patch.object(clothing.clothing_vocab, 'CONCEPT_PACKS', packs):
        with pytest.raises(ValueError):
            engine().construct_family(plan, evidence, proof, builder_inputs=inputs)


def test_failed_opt_in_uses_the_same_template_surface_as_ordinary_v1():
    inputs, plan, evidence = fixture_case('scene_lead_subject_action')
    proof = engine().prove_family(plan.syntax_family, plan, evidence, builder_inputs=inputs)
    altered = replace(proof, constructor_id='not-authorized')
    expected = realize_content_plan(replace(plan, syntax_family='single-sentence-scene-tail'))
    text, debug = realize_content_plan(plan, realization_evidence=evidence,
        builder_inputs=inputs, family_proof=altered, return_debug=True)
    assert text == expected
    assert debug['realizer_version'] == 'v1' and debug['syntax_fallback_reason']


@pytest.mark.parametrize('field,value', (
    ('primary_object', 'holding'),
    ('primary_object', 'the'),
    ('primary_object', 'clipboard'),
    ('primary_object', 'book'),
    ('posture', 'standing'),
    ('gaze_target', 'looking ahead'),
))
def test_rebinding_noncanonical_frame_projection_does_not_authorize(field, value):
    inputs, _, _ = fixture_case()
    inputs['action_frame'][field] = value
    plan, evidence = plan_for_inputs(inputs), build_realization_evidence(inputs)
    # A digest can faithfully bind fabricated metadata; permission needs producer replay.
    proofs = engine().prove_all_families(plan, evidence, builder_inputs=inputs)
    assert all(not proof.eligible and proof.blocker_ids for proof in proofs), (field, value)
