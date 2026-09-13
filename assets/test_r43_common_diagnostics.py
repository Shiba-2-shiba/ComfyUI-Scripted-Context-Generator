"""Common-route diagnostics replay constructors without widening parity claims."""
import copy
import hashlib
import random
from unittest.mock import patch

from assets.test_r43_family_capabilities import plan_for_inputs
from assets.test_r43_reachability_diagnostics import DIRECT_CASES, snapshot_for
from assets.test_r43_runtime_integration import common_snapshot
from pipeline import v2_candidate_bridge as bridge
from pipeline.prompt_realizer import realize_content_plan
import prompt_renderer
from tools import realizer_reachability_diagnostics as diagnostics
from tools.workflow_prompt_runner import canonical_json_bytes


def captured_common(*, standalone=False):
    inputs, plan, text, debug, surface, replacements = common_snapshot()
    if standalone:
        end = copy.deepcopy(next(entry for entry in prompt_renderer._template_entries('end')
                                 if entry['key'] == 'end_scene_room'))
        inputs['selected_templates']['end'] = end
        inputs['template_slots']['scene'] = end['text']
        plan = plan_for_inputs(inputs, 'single-sentence-scene-tail')
        text, debug = realize_content_plan(plan, return_debug=True)
    captures = []
    # Only the old compatibility adapter is unavailable. Common evidence,
    # family proof, constructor, finalizer and cleaner are all real.
    with patch.object(bridge, 'materialize_direct', return_value=None):
        template, _, _ = bridge.render_candidate(
            plan, text, debug, inputs['action_frame'], surface, replacements,
            inputs['seed'], common_inputs=inputs, audit_sink=captures.append)
    assert captures[0]['common_route'] is True
    finalization = {'replacements': replacements, 'staging_tags': '',
                    'action': inputs['action'], 'composition_mode': True}
    return {'bridge': captures[0], 'finalization': finalization,
            'raw_prompt': prompt_renderer._finalize_prompt(template, **finalization)}


def test_common_route_uses_typed_binding_and_same_forced_parity_definition():
    snapshot = captured_common()
    before, state = copy.deepcopy(snapshot), random.getstate()
    result = diagnostics.diagnose_snapshot(snapshot, force_families=True)
    assert snapshot == before and random.getstate() == state
    assert result['route'] == result['trace_mode'] == 'common_evidence'
    assert not result['errors']
    projection = result['capability_projection']
    assert projection['schema_version'] == 'realizer-capability-projection/v1'
    assert projection['status'] == 'AVAILABLE' and projection['capabilities']
    assert result['capability_projection_sha256'] == hashlib.sha256(
        canonical_json_bytes(projection)).hexdigest()
    for component in result['domains'].values():
        assert component['constructor_supported'] and component['grammar_known']
        assert component['binding_success'] and component['runtime_available']
        assert not component['unknown'] and not component['blockers']
        assert component['facts_basis'] == 'common_typed_evidence'
    for family, row in result['families'].items():
        assert row['runtime_eligible'] and row['constructor_v2']
        assert not row['blockers'] and not row['baseline_marker']
        if family == snapshot['bridge']['selected']:
            assert row['executed_v2'] and row['forced_render_v2']
            assert row['semantic_parity'] == 'EXACT_ORDINARY_OUTPUT'
        else:
            assert row['semantic_parity'] == 'NOT_AVAILABLE'
            assert row['forced_render_v2'] is None


def test_forcing_uses_source_plan_and_common_api_without_legacy_arguments():
    snapshot = captured_common()
    expected = diagnostics.diagnose_snapshot(snapshot, force_families=True)
    snapshot['bridge']['concrete_plan']['semantic_slots']['subject'] = 'stale concrete text'
    with patch.object(diagnostics.direct, 'materialize_direct', side_effect=AssertionError('legacy path')):
        with patch.object(diagnostics, 'realize_content_plan', wraps=realize_content_plan) as render:
            actual = diagnostics.diagnose_snapshot(snapshot, force_families=True)
    assert actual == expected
    assert render.call_count == len(bridge.FAMILIES)
    for call in render.call_args_list:
        assert set(call.kwargs) == {'realization_evidence', 'builder_inputs', 'return_debug'}


def test_common_token_equality_does_not_certify_changed_output():
    snapshot = captured_common()
    assert 'long straight hair' in snapshot['raw_prompt']
    snapshot['raw_prompt'] = snapshot['raw_prompt'].replace('long straight hair', 'straight long hair')
    result = diagnostics.diagnose_snapshot(snapshot, force_families=True)
    selected = result['families'][snapshot['bridge']['selected']]
    assert selected['constructor_v2']
    assert selected['forced']['lexical_counter_equal_auxiliary']
    assert selected['forced_render_v2'] is None
    assert selected['semantic_parity'] == 'NOT_AVAILABLE'


def test_changed_current_inputs_cannot_reuse_captured_common_permission():
    snapshot = captured_common()
    snapshot['bridge']['common_inputs']['context']['history'] = []
    result = diagnostics.diagnose_snapshot(snapshot, force_families=True)
    assert result['errors']
    assert not result['domains']['clothing']['runtime_available']
    assert all(row['constructor_v2'] is False for row in result['families'].values())
    assert all(row['semantic_parity'] == 'NOT_AVAILABLE' for row in result['families'].values())


def test_noneligible_common_families_report_actual_proof_blockers():
    snapshot = captured_common(standalone=True)
    assert set(snapshot['bridge']['selectable']) == set(bridge.FAMILIES) - {'action_lead_subject_scene'}
    proofs = {proof['family']: proof for proof in snapshot['bridge']['common_proofs']}
    result = diagnostics.diagnose_snapshot(snapshot, force_families=True)
    assert not result['errors']
    for family, row in result['families'].items():
        assert row['runtime_eligible'] == (family != 'action_lead_subject_scene')
        if not row['runtime_eligible']:
            assert row['blockers'] == sorted(set(proofs[family]['blocker_ids']))
            assert row['forced']['status'] == 'NOT_ELIGIBLE'
            assert 'family.legacy_route_ceiling' not in row['blockers']


def test_unused_common_inputs_do_not_change_legacy_diagnostics():
    snapshot = snapshot_for(DIRECT_CASES[0])
    original = diagnostics.diagnose_snapshot(snapshot, force_families=True)
    snapshot['bridge'].update(common_route=False, common_inputs=common_snapshot()[0], common_proofs=[])
    with patch.object(diagnostics, '_common_evidence', side_effect=AssertionError('legacy priority')):
        actual = diagnostics.diagnose_snapshot(snapshot, force_families=True)
    additive_fields = {
        'coverage_signature', 'coverage_signature_sha256',
        'capability_projection', 'capability_projection_sha256',
    }
    assert {key: value for key, value in actual.items() if key not in additive_fields} == {
        key: value for key, value in original.items() if key not in additive_fields}
    signature = actual['coverage_signature']
    assert signature['proof_basis'] == 'invalid_common_inputs'
    assert signature['eligible_families'] == []
    assert signature['family_blockers']
    assert all('binding.current_input_mismatch' in blockers
               for blockers in signature['family_blockers'].values())
    projection = actual['capability_projection']
    assert projection == {
        'schema_version': 'realizer-capability-projection/v1',
        'status': 'NOT_AVAILABLE',
        'capabilities': [],
    }
    assert actual['capability_projection_sha256'] == hashlib.sha256(
        canonical_json_bytes(projection)).hexdigest()
