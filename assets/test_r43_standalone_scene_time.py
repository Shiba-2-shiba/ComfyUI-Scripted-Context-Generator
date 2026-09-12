"""A proved time belongs to the standalone Scene, never to a moved Action."""
import copy
from dataclasses import replace

from assets.test_r43_ordinary_application import real_case
from assets.test_r43_family_capabilities import fixture_case, plan_for_inputs
from core.context_codec import context_from_json
from pipeline.prompt_orchestrator import build_prompt_from_context
from pipeline.prompt_realizer import ContentPlan, realize_content_plan
from pipeline.realization_evidence import build_realization_evidence
from pipeline.family_capabilities import prove_all_families
import prompt_renderer


def test_real_owned_bedroom_time_scopes_complete_standalone_scene():
    args = real_case()['builder_inputs']
    snapshots = []
    build_prompt_from_context(context_from_json(args['context_json'], default_seed=args['seed']),
        args['template'], args['composition_mode'], args['seed'], audit_sink=snapshots.append)
    snapshot = snapshots[0]
    inputs = snapshot['common_evidence_inputs']
    plan = ContentPlan(**snapshot['bridge']['input_plan'])
    evidence = build_realization_evidence(inputs)
    proofs = prove_all_families(plan, evidence, builder_inputs=inputs)
    assert {proof.family for proof in proofs if proof.eligible} == {'subject_action__scene_tail'}
    requested = replace(plan, syntax_family='subject_action__scene_tail')
    raw, debug = realize_content_plan(requested, realization_evidence=evidence, builder_inputs=inputs, return_debug=True)
    assert '. During a quiet night, the scene around her stays in a gothic victorian boudoir that features ' in raw
    assert 'a vintage vanity mirror with lights and a wooden wardrobe with open doors' in raw
    assert raw.lower().count('quiet night') == 1
    assert 'scene.standalone_time_scope/v1' in debug['transform_rule_ids']


def test_recombined_scene_time_is_not_global_relocation_permission():
    inputs, _, _ = fixture_case()
    location = 'grand historic opera house interior, during evening performance'
    inputs['scene'] = inputs['context']['extras']['location_prompt'] = location
    for row in inputs['context']['history']:
        if row['node'] == 'ContextLocationExpander':
            row['decision'].update(template_key='detailed')
    entry = copy.deepcopy(next(entry for entry in prompt_renderer._template_entries('end') if entry['key'] == 'end_scene_room'))
    inputs['selected_templates']['end'] = entry
    inputs['template_slots']['scene'] = entry['text']
    plan, evidence = plan_for_inputs(inputs), build_realization_evidence(inputs)
    assert {p.family for p in prove_all_families(plan, evidence, builder_inputs=inputs) if p.eligible} == {'subject_action__scene_tail'}
    bad = copy.deepcopy(inputs)
    next(row for row in bad['context']['history'] if row['node'] == 'ContextLocationExpander')['decision']['pack_key'] = 'art_gallery'
    assert not any(p.eligible for p in prove_all_families(plan, build_realization_evidence(bad), builder_inputs=bad))


def test_time_order_and_extra_unproved_parts_do_not_change_scope_or_disappear():
    args = real_case()['builder_inputs']
    snapshots = []
    build_prompt_from_context(context_from_json(args['context_json'], default_seed=args['seed']),
        args['template'], args['composition_mode'], args['seed'], audit_sink=snapshots.append)
    original = snapshots[0]['common_evidence_inputs']
    parts = original['scene'].split(', ')
    plan = replace(ContentPlan(**snapshots[0]['bridge']['input_plan']), syntax_family='subject_action__scene_tail')
    outputs = []
    # Explicitly recombined shuffle orders; never counted as unchanged real inputs.
    for value in (original['scene'], ', '.join((parts[0], parts[2], parts[1]))):
        inputs = copy.deepcopy(original)
        inputs['scene'] = inputs['context']['extras']['location_prompt'] = value
        text, debug = realize_content_plan(plan, realization_evidence=build_realization_evidence(inputs),
                                           builder_inputs=inputs, return_debug=True)
        assert debug['realizer_version'] == 'v2'
        outputs.append(text)
    assert outputs[0] == outputs[1]
    for extra in (', during quiet night', ', while a stranger enters'):
        inputs = copy.deepcopy(original)
        inputs['scene'] = inputs['context']['extras']['location_prompt'] = original['scene'] + extra
        assert not any(p.eligible for p in prove_all_families(plan, build_realization_evidence(inputs), builder_inputs=inputs))
