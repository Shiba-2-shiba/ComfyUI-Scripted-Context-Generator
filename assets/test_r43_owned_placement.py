"""Owned wrappers and garnish keep their owners when family placement changes."""
import copy
from dataclasses import replace

import pytest

from assets.test_r43_family_capabilities import fixture_case, plan_for_inputs, replace_action, FAMILIES
from pipeline.family_capabilities import prove_family, construct_family
from pipeline.realization_evidence import build_realization_evidence, Truth
from pipeline.prompt_realizer import realize_content_plan
from nodes_prompt_cleaner import PromptCleaner
import prompt_renderer


def with_garnish(inputs, tags):
    inputs['garnish'] = inputs['context']['extras']['garnish'] = ', '.join(tags)
    next(item for item in inputs['context']['history'] if item['node'] == 'ContextGarnish')['decision']['final_tags'] = list(tags)


@pytest.mark.parametrize('tag', ['brows knit in concentration', 'steady gaze', 'looking ahead'])
def test_action_lead_fronts_only_actor_action_and_keeps_owned_garnish_with_subject(tag):
    inputs, _, _ = fixture_case()
    with_garnish(inputs, [tag])
    plan = plan_for_inputs(inputs, 'action_lead_subject_scene')
    evidence = build_realization_evidence(inputs)
    garnish = next(component for component in evidence.components if component.domain == 'garnish').atoms[0]
    proof = prove_family(plan.syntax_family, plan, evidence, builder_inputs=inputs)
    assert proof.eligible, proof.blocker_ids
    concrete, _ = construct_family(plan, evidence, proof, builder_inputs=inputs)
    assert tag not in concrete.semantic_slots['adjunct']
    assert tag in concrete.semantic_slots['subject']
    assert (garnish.atom_id, 'subject') in proof.source_atom_map
    text, debug = realize_content_plan(plan, realization_evidence=evidence, builder_inputs=inputs, return_debug=True)
    cleaned = PromptCleaner().clean(text=text)[0]
    for rendered in (text, cleaned):
        assert rendered.startswith('Holding the clipboard, ')
        expected = 'with a steady gaze' if tag == 'steady gaze' else ('with ' + tag if tag.startswith('brows') else tag)
        assert expected + ', is in a grand historic opera house interior' in rendered
        assert rendered.count(expected) == 1
    assert garnish.owner_id == 'protagonist'
    if tag != 'looking ahead':
        assert garnish.same_subject is Truth.FALSE and garnish.grammatical_subject_id.startswith('body:')
    assert debug['realizer_version'] == 'v2'


def test_body_action_and_forged_garnish_owner_still_cannot_front():
    inputs, _, _ = fixture_case()
    with_garnish(inputs, ['brows knit in concentration'])
    plan, evidence = replace_action(inputs, {'primary_action': 'holding the clipboard',
        'gaze_target': 'eyes fixed on what needs to happen next', 'location': 'opera_house'})
    assert not prove_family('action_lead_subject_scene', plan, evidence, builder_inputs=inputs).eligible
    inputs, _, _ = fixture_case()
    with_garnish(inputs, ['brows knit in concentration'])
    plan, evidence = plan_for_inputs(inputs), build_realization_evidence(inputs)
    components = list(evidence.components)
    garnish = components[2]
    components[2] = replace(garnish, atoms=(replace(garnish.atoms[0], owner_id='another-person'),))
    assert not prove_family('action_lead_subject_scene', plan, replace(evidence, components=tuple(components)),
                            builder_inputs=inputs).eligible


@pytest.mark.parametrize('family', [family for family in FAMILIES if family != 'action_lead_subject_scene'])
def test_owned_scene_wrapper_has_explicit_finite_or_absolute_placement(family):
    inputs, _, _ = fixture_case()
    entry = copy.deepcopy(next(item for item in prompt_renderer._template_entries('end') if item['key'] == 'end_scene_room'))
    inputs['selected_templates']['end'], inputs['template_slots']['scene'] = entry, entry['text']
    plan, evidence = plan_for_inputs(inputs, family), build_realization_evidence(inputs)
    proof = prove_family(family, plan, evidence, builder_inputs=inputs)
    assert proof.eligible, proof.blocker_ids
    text, debug = realize_content_plan(plan, realization_evidence=evidence, builder_inputs=inputs, return_debug=True)
    expected = 'The room around her stays in' if family == 'subject_action__scene_tail' else 'with the room around her staying in'
    assert expected.lower() in text.lower()
    assert text.lower().count('room around her') == 1
    assert text.lower().count('grand historic opera house interior') == 1
    assert debug['realizer_version'] == 'v2'
    if family == 'scene_lead_subject_action':
        assert text.startswith('With the room around her staying in ')
    rejected = prove_family('action_lead_subject_scene', plan, evidence, builder_inputs=inputs)
    assert not rejected.eligible and 'template.absolute_not_locative_predicate' in rejected.blocker_ids
