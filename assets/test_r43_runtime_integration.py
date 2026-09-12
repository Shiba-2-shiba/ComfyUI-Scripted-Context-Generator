"""Compatibility-first runtime integration; synthetic and real graphs stay separate."""
import copy
from dataclasses import replace
import json
from pathlib import Path
from unittest.mock import patch

from assets.test_r43_family_capabilities import fixture_case
from core.context_codec import context_from_json
from core.schema import PromptContext
from pipeline import v2_candidate_bridge as bridge
from pipeline.prompt_orchestrator import build_prompt_from_context
from pipeline.prompt_realizer import realize_content_plan
from pipeline import realization_evidence
import prompt_renderer


def common_snapshot():
    inputs, plan, _ = fixture_case()
    inputs['composition_mode'] = True
    legacy = replace(plan, syntax_family='single-sentence-scene-tail')
    text, debug = realize_content_plan(legacy, return_debug=True)
    _, surface = prompt_renderer._render_action_clause(inputs['action'], inputs['garnish'],
        prompt_renderer._derive_action_surface(inputs['action']), inputs['selected_templates']['body'])
    replacements = [
        ('{subject_clause}', inputs['subject'] + ' in ' + inputs['clothing']),
        ('{action_clause}', inputs['action']), ('{scene_clause}', 'in ' + inputs['scene'] + ', ' + inputs['mood']),
        ('{scene_anchor_clause}', inputs['scene'] + ', ' + inputs['mood']),
        ('{subj}', inputs['subject']), ('{costume}', inputs['clothing']), ('{loc}', inputs['scene']),
        ('{action}', inputs['action']), ('{garnish}', inputs['garnish']), ('{meta_mood}', inputs['mood']), ('{meta_style}', ''),
    ]
    return inputs, legacy, text, debug, surface, replacements


def test_compatibility_fallback_can_use_actual_common_proof_without_serializing_it():
    inputs, plan, text, debug, surface, replacements = common_snapshot()
    captures = []
    # Simulate a compatibility adapter without this source construction; the
    # actual common source/proof/constructor are exercised without safety mocks.
    with patch.object(bridge, 'materialize_direct', return_value=None):
        actual, concrete, observed = bridge.render_candidate(plan, text, debug, inputs['action_frame'],
            surface, replacements, inputs['seed'], common_inputs=inputs, audit_sink=captures.append)
    assert actual != text and '{' not in actual and concrete.syntax_family in bridge.FAMILIES
    assert observed['realizer_version'] == 'v2' and observed['candidate_v2_applied']
    assert 'family_proof' not in observed and 'input_binding_sha256' not in json.dumps(observed)
    assert captures[0]['common_route'] is True
    assert captures[0]['selected'] == observed['syntax_family']
    assert len(captures[0]['common_proofs']) == 6


def test_ineligible_common_inputs_keep_exact_compatibility_fallback():
    inputs, plan, text, debug, surface, replacements = common_snapshot()
    inputs['context']['history'] = []
    with patch.object(bridge, 'materialize_direct', return_value=None):
        old = bridge.render_candidate(plan, text, debug, inputs['action_frame'], surface, replacements, inputs['seed'])
        new = bridge.render_candidate(plan, text, debug, inputs['action_frame'], surface, replacements, inputs['seed'],
                                      common_inputs=inputs)
    assert new == old


def test_nine_real_graph_successes_and_public_debug_are_preserved_before_common_route():
    fixture = json.loads((Path(__file__).parent / 'fixtures/r43_real_graph_cases.json').read_text(encoding='utf-8'))
    assert len(fixture['cases']) == 9
    for case in fixture['cases']:
        assert case['classification'] == 'REAL_GRAPH'
        args = case['builder_inputs']
        context = context_from_json(args['context_json'], default_seed=args['seed'])
        before = copy.deepcopy(context.to_dict())
        # Legacy success must not depend on new common proof or its construction.
        with patch.object(realization_evidence, 'build_realization_evidence', side_effect=AssertionError('legacy priority')):
            updated, raw = build_prompt_from_context(context, args['template'], args['composition_mode'], args['seed'])
        assert raw == case['raw'] and updated.to_dict() == case['builder_context'], case['run_seed']
        assert context.to_dict() == before


def test_noncanonical_optional_context_keeps_existing_fallback_with_or_without_sink():
    context = PromptContext.from_dict({'subj': 'a solo girl', 'action': 'reading a book',
                                      'extras': {'custom_score': float('nan')}})
    expected = 'a solo girl, reading a book, and the room around her staying in'
    plain, raw = build_prompt_from_context(context, '', True, 7)
    captured = []
    observed, traced = build_prompt_from_context(context, '', True, 7, audit_sink=captured.append)
    assert raw == traced == expected
    assert json.dumps(plain.to_dict(), sort_keys=True) == json.dumps(observed.to_dict(), sort_keys=True)
    assert captured[0]['common_evidence'] is None
    assert captured[0]['common_evidence_error'] == 'invalid_inputs'
