"""Current Builder inputs authorize diagnostics without changing public output."""
import copy
from unittest.mock import patch

from core.schema import PromptContext
from pipeline.prompt_orchestrator import build_prompt_from_context
from pipeline import realization_evidence


def test_builder_captures_selected_entries_and_post_policy_values_in_same_call():
    context = PromptContext.from_dict({
        'subj': 'A solo girl with black hair and blue eyes', 'seed': 17,
        'action': 'reading a book', 'loc': 'tea room',
        'extras': {'garnish': 'steady gaze'}, 'meta': {'mood': ''},
    })
    before = copy.deepcopy(context.to_dict())
    snapshots = []
    observed, raw = build_prompt_from_context(context, '', True, 17, audit_sink=snapshots.append)
    plain, expected = build_prompt_from_context(context, '', True, 17)
    assert (raw, observed.to_dict()) == (expected, plain.to_dict())
    assert context.to_dict() == before
    snapshot = snapshots[0]
    inputs = snapshot['common_evidence_inputs']
    assert inputs['context'] == before
    values = dict(snapshot['finalization']['replacements'])
    assert inputs['subject'] == values['{subj}']
    assert inputs['garnish'] == values['{garnish}']
    assert inputs['mood'] == values['{meta_mood}']
    keys = [inputs['selected_templates'][part]['key'] for part in ('intro', 'body', 'end')]
    assert keys == [observed.history[-1].decision[part + '_key'] for part in ('intro', 'body', 'end')]
    evidence = realization_evidence.build_realization_evidence(inputs)
    assert snapshot['common_evidence'] == realization_evidence.evidence_to_dict(evidence)
    assert {c.domain for c in evidence.components} == set(realization_evidence.DOMAINS)
    assert not any('adapter_not_implemented' in b for c in evidence.components for b in c.blockers)
    assert 'common_evidence' not in str(observed.to_dict())


def test_runtime_fallback_uses_common_evidence_but_rollback_does_not():
    context = PromptContext.from_dict({'subj': 'a solo girl', 'action': 'reading a book'})
    with patch.object(realization_evidence, 'build_realization_evidence',
                      wraps=realization_evidence.build_realization_evidence) as build:
        build_prompt_from_context(context, '', True, 7)
        assert build.called
    with patch.object(realization_evidence, 'build_realization_evidence', side_effect=AssertionError('unexpected evidence')):
        captured = []
        build_prompt_from_context(context, '', False, 7, audit_sink=captured.append)
    assert captured[0]['common_evidence'] is None
    assert captured[0]['common_evidence_inputs'] is None


def test_detached_receipt_mutation_does_not_change_context_or_following_builder():
    context = PromptContext.from_dict({'subj': 'a solo girl', 'action': 'reading a book'})
    expected, raw = build_prompt_from_context(context, '', True, 7)
    def mutate(snapshot):
        snapshot['common_evidence_inputs']['context'].clear()
        snapshot['common_evidence']['components'].clear()
    observed, actual = build_prompt_from_context(context, '', True, 7, audit_sink=mutate)
    assert (observed.to_dict(), actual) == (expected.to_dict(), raw)
    repeated, text = build_prompt_from_context(context, '', True, 7)
    assert (repeated.to_dict(), text) == (expected.to_dict(), raw)
