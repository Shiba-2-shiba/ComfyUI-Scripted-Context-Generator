"""Real producer input locks common-only coverage and clause ownership."""
import copy
import json
from pathlib import Path

from core.context_codec import context_from_json
from nodes_prompt_cleaner import PromptCleaner
from pipeline.family_capabilities import prove_all_families
from pipeline.prompt_orchestrator import build_prompt_from_context
from pipeline.prompt_realizer import ContentPlan
from pipeline.realization_evidence import build_realization_evidence
from tools.realizer_candidate_replay import builder_inputs


def run_case():
    pair = json.loads((Path(__file__).parent / 'fixtures/r43_coverage_as01_pair.json').read_text(encoding='utf-8'))
    args = builder_inputs(pair)
    context = context_from_json(args['context_json'], default_seed=args['seed'])
    before = copy.deepcopy(context.to_dict())
    captured = []
    updated, raw = build_prompt_from_context(context, args['template'], args['composition_mode'], args['seed'],
                                            audit_sink=captured.append)
    assert context.to_dict() == before
    return pair, updated, raw, captured[0]


def test_source_bound_action_scene_ordinary_expansion():
    pair, updated, raw, snapshot = run_case()
    decision = updated.history[-1].decision
    assert decision['realizer_version'] == 'v2'
    assert snapshot['bridge']['common_route']
    assert updated.to_dict()['extras'] == pair['builder_context']['extras']
    assert updated.to_dict()['history'][:-1] == pair['builder_context']['history'][:-1]
    assert decision['action_frame'] == pair['builder_context']['history'][-1]['decision']['action_frame']
    for text in (raw, PromptCleaner().clean(text=raw)[0]):
        for constituent in ('turning toward the center of attention with composure',
                            'leaning in with quiet purpose', 'clicking a pen',
                            'as the session wraps up', 'professional soundproof recording booth',
                            'geometric sound isolation pads on the wall',
                            'quiet focused atmosphere', 'lived-in atmosphere'):
            assert text.count(constituent) == 1
    assert 'family_proof' not in json.dumps(updated.to_dict())


def test_dependent_event_stays_nonhuman_and_cannot_lead_action():
    _, _, _, snapshot = run_case()
    inputs = snapshot['common_evidence_inputs']
    evidence = build_realization_evidence(inputs)
    action = next(component for component in evidence.components if component.domain == 'action')
    event = next(atom for atom in action.atoms if atom.source_text == 'as the session wraps up')
    assert event.grammatical_subject_id.startswith('event:')
    assert event.owner_id is None and event.same_subject.value == 'false'
    assert event.attachment == 'dependent_temporal_event'
    assert any(rule.startswith('v2_common_action_grammar:time_or_weather:') for rule in event.rule_ids)
    plan = ContentPlan(**snapshot['bridge']['input_plan'])
    proofs = prove_all_families(plan, evidence, builder_inputs=inputs)
    assert any(proof.eligible for proof in proofs)
    lead = next(proof for proof in proofs if proof.family == 'action_lead_subject_scene')
    assert not lead.eligible
    for proof in proofs:
        if proof.eligible:
            assert 'action.count_noun_article/v1' in proof.transform_rule_ids
