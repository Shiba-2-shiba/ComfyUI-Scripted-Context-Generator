"""Source-bound new ordinary application; no seed gates in production code."""
import copy
import json
from pathlib import Path

from core.context_codec import context_from_json
from pipeline.prompt_orchestrator import build_prompt_from_context
from pipeline.realization_evidence import Truth
from nodes_prompt_cleaner import PromptCleaner


def real_case():
    receipt = json.loads((Path(__file__).parent / 'fixtures/r43_ordinary_real_cases.json').read_text(encoding='utf-8'))
    assert receipt['classification'] == 'REAL_GRAPH'
    return receipt['cases'][0]


def test_new_ordinary_real_graph_application_preserves_actors_objects_and_every_action_leaf():
    case = real_case()
    args = case['builder_inputs']
    context = context_from_json(args['context_json'], default_seed=args['seed'])
    before = copy.deepcopy(context.to_dict())
    snapshots = []
    updated, raw = build_prompt_from_context(context, args['template'], args['composition_mode'], args['seed'],
                                            audit_sink=snapshots.append)
    decision = updated.history[-1].decision
    assert decision['realizer_version'] == 'v2' and decision['candidate_v2_applied']
    assert snapshots[0]['bridge']['common_route']
    cleaned = PromptCleaner().clean(text=raw)[0]
    assert raw != case['baseline_raw'] and cleaned != case['baseline_cleaned']
    assert context.to_dict() == before
    assert updated.to_dict()['extras'] == case['baseline_builder_context']['extras']
    assert updated.to_dict()['history'][:-1] == case['baseline_builder_context']['history'][:-1]
    assert decision['action_frame'] == case['baseline_builder_context']['history'][-1]['decision']['action_frame']
    for text in (raw, cleaned):
        assert 'is lying down reading a book' in text
        assert 'with open pages visible' in text
        assert 'with eyes following the detail she is working through' in text
        assert 'rechecking a small detail' in text
        assert text.lower().count('girl') == 1
    action = next(item for item in snapshots[0]['common_evidence']['components'] if item['domain'] == 'action')
    for part in action['trace']['parts']:
        assert raw.lower().count(part['text'].lower()) == 1
        assert cleaned.lower().count(part['text'].lower()) == 1
    pages = next(atom for atom in action['atoms'] if atom['source_text'] == 'open pages visible')
    assert pages['grammatical_subject_id'] == 'object:book:pages'
    assert pages['owner_id'] == 'object:book' and pages['same_subject'] == Truth.FALSE.value
    eyes = next(atom for atom in action['atoms'] if atom['source_text'].startswith('eyes following'))
    assert eyes['grammatical_subject_id'] == 'body:eyes' and eyes['owner_id'] == 'protagonist'
    assert 'family_proof' not in json.dumps(updated.to_dict())


def test_missing_or_stale_artifact_relation_keeps_prior_fallback():
    case = real_case()
    args = case['builder_inputs']
    for corrupt in ('missing', 'wrong_object'):
        context = context_from_json(args['context_json'], default_seed=args['seed'])
        history = next(row for row in context.history if row.node == 'ContextSceneVariator')
        relation = history.decision['semantic_epig']['object_relation']
        if corrupt == 'missing':
            history.decision['semantic_epig'].pop('object_relation')
        else:
            relation['relation_key'] = 'phone:checking'
        updated, raw = build_prompt_from_context(context, args['template'], args['composition_mode'], args['seed'])
        assert updated.history[-1].decision['realizer_version'] == 'v1'
        assert raw == case['baseline_raw']
