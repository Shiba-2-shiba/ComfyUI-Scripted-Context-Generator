"""Support source binding and grammar recognition remain independent."""
import copy

import pytest

from pipeline.character_profile_pipeline import build_character_profile, load_character_profiles
from pipeline.realization_evidence import Truth
from pipeline.v2_support_provenance import (
    adapt_garnish_component, adapt_mood_component, adapt_subject_component,
)


def adapt(fn, ctx, **current):
    return fn({'context': ctx, **current}, input_binding_sha256='binding',
              source_identity_sha256='source')


def subject_context(name='Aiko (Quiet)'):
    profile = build_character_profile(0, 'fixed', name, load_character_profiles())
    return {'subj': profile['subj_prompt'], 'extras': {
        'character_name': name, 'hair_color': profile['hair_color'],
        'eye_color': profile['eye_color'], 'color_palette': profile['color_palette']}}


def garnish_context(tags=('steady gaze',)):
    return {'extras': {'garnish': ', '.join(tags)}, 'history': [
        {'node': 'ContextGarnish', 'decision': {'final_tags': list(tags)}}]}


def mood_context(text='the moment kept deliberate rather than urgent, with everything else held at the edge'):
    return {'meta': {'mood': text}, 'extras': {'raw_mood_key': 'quiet_focused'}}


def test_subject_binds_profile_and_preserves_its_raw_appearance_parts():
    ctx = subject_context()
    value = adapt(adapt_subject_component, ctx, subject=ctx['subj'])
    assert value.runtime_available and not value.blockers
    assert value.trace.input_binding_sha256 == 'binding'
    assert value.trace.source_identity_sha256 == 'source'
    assert value.atoms[0].source_text == ctx['subj']
    assert value.atoms[0].grammar_known is Truth.TRUE
    assert value.atoms[0].grammatical_subject_id == 'protagonist'
    assert value.atoms[0].attachment == 'main'
    assert value.atoms[0].owner_id == 'protagonist'
    assert {part.source.field for part in value.trace.parts} == {
        'visual_traits.hair_color', 'visual_traits.hair_style', 'visual_traits.eye_color'}


def test_unknown_subject_grammar_does_not_erase_profile_source():
    value = adapt(adapt_subject_component, subject_context('Aiko (Gothic)'))
    assert value.trace is not None and value.runtime_available
    assert value.atoms[0].grammar_known is Truth.UNKNOWN
    assert 'hime cut' in value.atoms[0].source_text
    assert 'subject.unsupported_constructor' in value.blockers


def test_stale_subject_profile_and_second_person_fail_closed():
    ctx = subject_context()
    cases = [({**ctx, 'subj': ctx['subj'] + ' and another girl'}, {}),
             (ctx, {'subject': ctx['subj'] + ' smiling'}),
             ({**ctx, 'extras': {**ctx['extras'], 'character_name': 'Aiko (Confident)'}}, {}),
             ({**ctx, 'extras': {**ctx['extras'], 'hair_color': 'blue'}}, {})]
    for changed, current in cases:
        assert adapt(adapt_subject_component, changed, **current).trace is None


def test_garnish_binds_latest_selection_and_preserves_body_owner():
    value = adapt(adapt_garnish_component, garnish_context(('brows knit in concentration', 'looking ahead')))
    assert value.runtime_available and not value.blockers
    brows, gaze = value.atoms
    assert brows.grammatical_subject_id == 'body:brows'
    assert brows.owner_id == 'protagonist' and brows.same_subject is Truth.FALSE
    assert brows.attachment == 'with_absolute'
    assert gaze.grammatical_subject_id == 'protagonist'
    assert gaze.attachment == 'shared_modifier'
    assert gaze.same_subject is Truth.TRUE


def test_garnish_unknown_source_text_is_retained_without_grammar_promotion():
    value = adapt(adapt_garnish_component, garnish_context(('another girl waves',)))
    assert value.trace is not None
    assert value.atoms[0].source_text == 'another girl waves'
    assert value.atoms[0].grammar_known is Truth.UNKNOWN
    assert value.atoms[0].owner_id is None


def test_garnish_latest_history_and_current_text_must_match():
    ctx = garnish_context()
    changed = copy.deepcopy(ctx)
    changed['history'].append({'node': 'ContextGarnish', 'decision': {}})
    assert adapt(adapt_garnish_component, changed).trace is None
    assert adapt(adapt_garnish_component, ctx, garnish='').trace is None
    assert adapt(adapt_garnish_component, {'extras': ctx['extras']}).trace is None


def test_empty_garnish_requires_explicit_empty_selection():
    empty = adapt(adapt_garnish_component, garnish_context(()), garnish='')
    assert empty.runtime_available and empty.trace is not None and not empty.blockers
    assert empty.trace.parts == () and empty.atoms == ()
    assert adapt(adapt_garnish_component, {}).trace is None


def test_mood_grammar_is_separate_from_current_raw_key_membership():
    value = adapt(adapt_mood_component, mood_context())
    assert value.runtime_available and not value.blockers
    assert value.atoms[0].grammar_known is Truth.TRUE
    assert value.atoms[0].same_subject is Truth.FALSE
    assert value.atoms[0].attachment == 'with_absolute'
    assert value.atoms[0].owner_id == 'scene:0'
    unknown = adapt(adapt_mood_component, mood_context(
        'the air staying calm while her attention stays with what still needs finishing'))
    assert unknown.trace is not None and unknown.atoms[0].grammar_known is Truth.UNKNOWN
    assert 'mood.unsupported_constructor' in unknown.blockers


def test_stale_mood_and_raw_key_fail_closed():
    ctx = mood_context()
    assert adapt(adapt_mood_component, ctx, mood='a different mood').trace is None
    assert adapt(adapt_mood_component, {**ctx, 'extras': {'raw_mood_key': 'energetic_joy'}}).trace is None
    assert adapt(adapt_mood_component, {'meta': ctx['meta']}).trace is None


@pytest.mark.parametrize('fn,key,ctx', [
    (adapt_subject_component, 'subject', subject_context()),
    (adapt_garnish_component, 'garnish', garnish_context()),
    (adapt_mood_component, 'mood', mood_context()),
])
def test_malformed_current_values_are_not_coerced(fn, key, ctx):
    for value in (None, 1, [], {}):
        assert adapt(fn, ctx, **{key: value}).trace is None
    assert fn({}, input_binding_sha256='binding', source_identity_sha256='source').trace is None
