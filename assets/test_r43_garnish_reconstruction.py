"""Post-policy garnish preserves raw provenance without restoring omitted facts."""
import copy

import pytest

from pipeline.realization_evidence import Truth, text_sha256
from pipeline.v2_support_provenance import adapt_garnish_component


def received(tags, current, *, action='reading a book', subject='A solo girl'):
    return {
        'context': {'action': action, 'subj': subject, 'meta': {'mood': ''},
                    'extras': {'garnish': ', '.join(tags), 'staging_tags': ''},
                    'history': [{'node': 'ContextGarnish', 'decision': {'final_tags': list(tags)}}]},
        'garnish': current, 'action_frame': None, 'composition_mode': True,
    }


def adapt(inputs):
    return adapt_garnish_component(inputs, input_binding_sha256='binding', source_identity_sha256='source')


@pytest.mark.parametrize('tags,current,action,omitted', [
    (('looking ahead', 'brows knit in concentration'), 'brows knit in concentration',
     'walking while looking ahead', (('garnish:0', 'legacy.garnish.exact_redundancy'),)),
    (('steady gaze', 'brows knit in concentration'), 'brows knit in concentration',
     'looking ahead', (('garnish:0', 'legacy.garnish.semantic_family_budget'),)),
    (('hands kept precise and controlled', 'still posture'), 'hands kept precise and controlled',
     'reading a book', (('garnish:1', 'legacy.garnish.solo_support_budget'),)),
    (('someone waves', 'brows knit in concentration'), 'brows knit in concentration',
     'reading a book', (('garnish:0', 'legacy.garnish.solo_support_budget'),)),
])
def test_existing_policies_bind_selected_and_emitted_parts_separately(tags, current, action, omitted):
    inputs = received(tags, current, action=action)
    before = copy.deepcopy(inputs)
    result = adapt(inputs)
    assert result.runtime_available and not result.blockers
    assert inputs == before
    assert tuple(part.text for part in result.trace.parts) == tags
    assert result.trace.raw_output_sha256 == text_sha256(', '.join(tags))
    assert result.trace.emitted_output_sha256 == text_sha256(current)
    assert result.trace.omitted_parts == omitted
    assert tuple(atom.source_text for atom in result.atoms) == (current,)
    assert all(atom.grammar_known is Truth.TRUE for atom in result.atoms)
    assert result.trace.emitted_part_ids == result.atoms[0].source_part_ids


def test_unknown_emitted_grammar_is_preserved_and_all_suppressed_is_empty():
    unknown = adapt(received(('steady gaze', 'composed face'), 'composed face', action='steady gaze'))
    assert unknown.trace is not None
    assert unknown.atoms[0].grammar_known is Truth.UNKNOWN
    assert unknown.atoms[0].owner_id is None
    empty = adapt(received(('looking ahead',), '', action='looking ahead'))
    assert empty.trace is not None and empty.atoms == ()
    assert empty.trace.emitted_part_ids == ()
    assert empty.trace.omitted_parts == (('garnish:0', 'legacy.garnish.exact_redundancy'),)


@pytest.mark.parametrize('section,key', [
    (None, 'composition_mode'), (None, 'action_frame'), ('context', 'action'),
    ('context', 'subj'), ('meta', 'mood'), ('extras', 'staging_tags'),
])
def test_missing_raw_policy_inputs_are_not_inferred(section, key):
    inputs = received(('looking ahead', 'still posture'), 'still posture', action='looking ahead')
    target = inputs if section is None else inputs['context'] if section == 'context' else inputs['context'][section]
    del target[key]
    assert adapt(inputs).trace is None


def test_stale_history_mismatched_current_and_frame_fail_closed():
    inputs = received(('looking ahead', 'still posture'), 'still posture', action='looking ahead')
    cases = []
    stale = copy.deepcopy(inputs)
    stale['context']['history'].append({'node': 'ContextGarnish', 'decision': {'final_tags': ['still posture']}})
    cases.append(stale)
    cases.append({**inputs, 'garnish': 'looking ahead'})
    cases.append({**inputs, 'composition_mode': 'true'})
    mismatched_frame = copy.deepcopy(inputs)
    mismatched_frame['context']['extras']['action_frame'] = {'gaze_target': 'looking ahead'}
    cases.append(mismatched_frame)
    for value in cases:
        assert adapt(value).trace is None


def test_raw_current_equality_keeps_existing_source_binding_contract():
    inputs = received(('steady gaze',), 'steady gaze')
    del inputs['composition_mode']
    del inputs['action_frame']
    inputs['context'].pop('meta')
    result = adapt(inputs)
    assert result.trace is not None and result.trace.omitted_parts is None
    assert result.trace.raw_output_sha256 == result.trace.emitted_output_sha256


def test_composition_setting_and_solo_context_are_used_without_defaults():
    inputs = received(('brows knit in concentration', 'still posture'), 'still posture',
                      action='brows knit in concentration')
    assert adapt(inputs).trace is not None
    assert adapt({**inputs, 'composition_mode': False}).trace is None
    inputs = received(('hands kept precise and controlled', 'still posture'),
                      'hands kept precise and controlled', subject='A woman')
    assert adapt(inputs).trace is None


def test_omission_rules_follow_policy_order_and_preserve_original_source_ids():
    inputs = received(('looking ahead', 'steady gaze', 'hands kept precise and controlled', 'still posture'),
                      'hands kept precise and controlled', action='looking ahead')
    result = adapt(inputs)
    assert result.trace is not None
    assert result.trace.omitted_parts == (
        ('garnish:0', 'legacy.garnish.exact_redundancy'),
        ('garnish:1', 'legacy.garnish.semantic_family_budget'),
        ('garnish:3', 'legacy.garnish.solo_support_budget'),
    )
    assert result.trace.emitted_part_ids == ('garnish:2',)
    assert result.atoms[0].source_part_ids == ('garnish:2',)


def test_reconstruction_has_no_random_draws(monkeypatch):
    import random

    def forbidden(*args, **kwargs):
        raise AssertionError('Garnish source reconstruction must not draw RNG')

    monkeypatch.setattr(random, 'Random', forbidden)
    monkeypatch.setattr(random, 'choice', forbidden)
    monkeypatch.setattr(random, 'choices', forbidden)
    result = adapt(received(('looking ahead', 'still posture'), 'still posture', action='looking ahead'))
    assert result.trace is not None
