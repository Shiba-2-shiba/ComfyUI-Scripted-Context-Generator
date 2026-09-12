"""Immutable evidence and current-input validation, never family permission."""
import copy
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import subprocess
import sys
from unittest import mock

import pytest

from pipeline import realization_evidence as evidence
from pipeline.action_renderer import render_action_slots
from core.schema import ActionFrame, PromptContext
from pipeline.prompt_realizer import ContentPlan


def inputs():
    slots = {'purpose_clause': 'holding a clipboard'}
    action = render_action_slots(slots)
    frame = ActionFrame.from_slots(slots, legacy_text=action, main_verb='holding', primary_object='clipboard')
    return {'action': action, 'action_frame': frame.to_dict(), 'seed': 17,
            'selected_templates': {'intro': {'key': 'intro', 'text': '{subject_clause}'},
                                   'body': {'key': 'body', 'text': '{action_clause}'}},
            'context': {'subj': 'a solo girl', 'history': []}}


@pytest.mark.parametrize('fact', list(evidence.Truth))
def test_truth_cannot_silently_enter_a_boolean_gate(fact):
    with pytest.raises(TypeError):
        bool(fact)


@pytest.mark.parametrize('invalid', [1, 0, 'true', [], {}])
def test_legacy_facts_cannot_be_coerced_into_truth(invalid):
    with pytest.raises(TypeError):
        evidence.truth_from_optional(invalid)


def test_missing_inputs_stay_unavailable_and_none_is_not_empty():
    value = evidence.build_realization_evidence({})
    assert all(component.trace is None and component.runtime_available is False for component in value.components)
    assert all(component.blockers for component in value.components)
    assert evidence.validate_evidence_binding(value, {})
    assert not evidence.validate_evidence_binding(value, {'action': None})
    assert evidence.truth_from_optional(None) is evidence.Truth.UNKNOWN


def test_deep_freeze_does_not_keep_caller_owned_mutable_values():
    original = inputs()
    producer = {'character_palette': ['blue', 'white']}
    before = copy.deepcopy((original, producer))
    value = evidence.build_realization_evidence(original, producer_context=producer)
    encoded = evidence.evidence_bytes(value)
    original['action_frame']['legacy_slots']['purpose_clause'] = 'different'
    producer['character_palette'].append('red')
    assert evidence.evidence_bytes(value) == encoded
    assert evidence.validate_evidence_binding(value, before[0], producer_context=before[1])
    assert not evidence.validate_evidence_binding(value, original, producer_context=producer)
    with pytest.raises(FrozenInstanceError):
        value.components = ()
    with pytest.raises(TypeError):
        replace(value, components=list(value.components))
    with pytest.raises(TypeError):
        replace(value.components[0], facts=(('mutable', {}),))


@pytest.mark.parametrize('mutation', ['word', 'space', 'slot', 'frame_version', 'seed', 'template_key', 'template_text', 'history'])
def test_any_bound_input_change_invalidates_previous_evidence(mutation):
    original = inputs()
    value = evidence.build_realization_evidence(original)
    changed = copy.deepcopy(original)
    if mutation == 'word':
        changed['action'] += ' quietly'
    elif mutation == 'space':
        changed['action'] = ' ' + changed['action']
    elif mutation == 'slot':
        changed['action_frame']['legacy_slots']['purpose_clause'] = 'checking a clipboard'
    elif mutation == 'frame_version':
        changed['action_frame']['schema_version'] = 'action-frame/v999'
    elif mutation == 'seed':
        changed['seed'] += 1
    elif mutation == 'template_key':
        changed['selected_templates']['body']['key'] = 'other'
    elif mutation == 'template_text':
        changed['selected_templates']['body']['text'] = 'another {action_clause}'
    else:
        changed['context']['history'].append({'node': 'previous', 'seed': 0})
    assert not evidence.validate_evidence_binding(value, changed)


def test_producer_context_missing_empty_and_changed_palette_are_distinct():
    original = inputs()
    value = evidence.build_realization_evidence(original, producer_context={'character_palette': ['blue']})
    for context in (None, {}, {'character_palette': []}, {'character_palette': ['red']}):
        assert not evidence.validate_evidence_binding(value, original, producer_context=context)


def test_matching_checksum_cannot_authorize_forged_components():
    original = inputs()
    value = evidence.build_realization_evidence(original)
    action = value.components[0]
    assert action.trace is not None
    changed_atom = replace(action.atoms[0], owner_id='another-person')
    forged = replace(value, components=(replace(action, atoms=(changed_atom,)), *value.components[1:]))
    assert forged.input_binding_sha256 == value.input_binding_sha256
    assert not evidence.validate_evidence_binding(forged, original)
    forged_unknown = replace(value, components=(action, replace(value.components[1], runtime_available=True), *value.components[2:]))
    assert not evidence.validate_evidence_binding(forged_unknown, original)
    wrong_type = replace(value, components=(replace(action, runtime_available=1), *value.components[1:]))
    assert not evidence.validate_evidence_binding(wrong_type, original)
    assert not evidence.validate_evidence_binding(replace(value, components=value.components[:-1]), original)


def test_old_schema_and_changed_runtime_source_identity_are_invalid():
    original = inputs()
    value = evidence.build_realization_evidence(original)
    assert not evidence.validate_evidence_binding(replace(value, schema_version='realization-evidence/v0'), original)
    assert not evidence.validate_evidence_binding(replace(value, source_identity_sha256='0' * 64), original)
    with mock.patch.object(evidence, '_SOURCE_IDENTITY_SHA256', '1' * 64):
        assert not evidence.validate_evidence_binding(value, original)


def test_canonical_mapping_order_and_explicit_audit_serializer():
    original = inputs()
    reordered = {key: original[key] for key in reversed(original)}
    first = evidence.build_realization_evidence(original)
    second = evidence.build_realization_evidence(reordered)
    assert evidence.evidence_bytes(first) == evidence.evidence_bytes(second)
    exported = evidence.evidence_to_dict(first)
    assert json.loads(evidence.evidence_bytes(first)) == exported
    assert not evidence.validate_evidence_binding(exported, original)
    assert 'realization_evidence' not in PromptContext().to_dict()
    assert 'realization_evidence' not in ActionFrame().to_dict()
    assert 'realization_evidence' not in ContentPlan({}, (), (), '', '', {}).to_dict()
    assert not hasattr(first, 'eligible')


@pytest.mark.parametrize('invalid', [{1: 'coerced-key'}, {'nan': float('nan')}, {'object': object()}])
def test_noncanonical_inputs_are_rejected_without_coercion(invalid):
    with pytest.raises((TypeError, ValueError)):
        evidence.build_realization_evidence(invalid)
    assert not evidence.validate_evidence_binding(evidence.build_realization_evidence({}), invalid)


def test_build_and_validate_do_not_scan_repository_per_call():
    original = inputs()
    value = evidence.build_realization_evidence(original)
    with mock.patch.object(Path, 'rglob', side_effect=AssertionError('no repo scan')):
        for _ in range(2):
            assert evidence.validate_evidence_binding(value, original)
            assert evidence.runtime_source_identity() == value.source_identity_sha256


def test_fresh_process_hashseeds_and_package_import_produce_identical_bytes(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = '''
import importlib, importlib.util, json, sys
from pathlib import Path
root=Path(sys.argv[1]); mode=sys.argv[2]
if mode=='package':
    spec=importlib.util.spec_from_file_location('scg_evidence_probe', root/'__init__.py', submodule_search_locations=[str(root)])
    pkg=importlib.util.module_from_spec(spec); sys.modules[spec.name]=pkg; spec.loader.exec_module(pkg)
    module=importlib.import_module('scg_evidence_probe.pipeline.realization_evidence')
    assert 'pipeline.realization_evidence' not in sys.modules
else:
    sys.path.insert(0,str(root)); module=importlib.import_module('pipeline.realization_evidence')
value=module.build_realization_evidence(json.load(sys.stdin))
assert module.validate_evidence_binding(value, json.loads(sys.argv[3]))
sys.stdout.buffer.write(module.evidence_bytes(value))
'''
    import os
    payload = json.dumps(inputs())
    results = []
    for mode in ('root', 'package'):
        for seed in ('0', '123'):
            result = subprocess.run([sys.executable, '-B', '-c', script, str(root), mode, payload],
                cwd=tmp_path, env={**os.environ, 'PYTHONHASHSEED': seed, 'PYTHONPATH': ''},
                input=payload.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            assert result.returncode == 0, result.stderr.decode(errors='replace')
            results.append(result.stdout)
    assert all(value == results[0] for value in results)
