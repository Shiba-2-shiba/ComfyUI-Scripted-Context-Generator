"""Common Scene coverage retains producer fields and noun-owned attachments."""
import copy
import json
from pathlib import Path
from unittest import mock

import pytest

from pipeline import v2_scene_provenance as scene
from pipeline.realization_evidence import Truth, build_realization_evidence


def context():
    pair = json.loads((Path(__file__).parent / 'fixtures/r43_coverage_as01_pair.json').read_text(encoding='utf-8'))
    return pair['builder_context']


def component(ctx):
    return build_realization_evidence({'context': ctx}).components[4]


def decision(ctx):
    return next(row['decision'] for row in reversed(ctx['history']) if row['node'] == 'ContextLocationExpander')


def selected(ctx, field):
    value = decision(ctx)['semantic_epig']['location_scene']['section_changes'][field]['semantic']
    return value[0] if field == 'core' else value


def test_actual_booth_preserves_every_raw_field_and_pads_owned_wall():
    ctx = context()
    value = component(ctx)
    assert value.runtime_available
    assert [(part.source.field, part.source.catalog_key, part.text) for part in value.trace.parts] == [
        ('environment', 'recording_studio', 'professional soundproof recording booth'),
        ('core', 'recording_studio', 'geometric sound isolation pads on wall'),
        ('fx', 'recording_studio', 'quiet focused atmosphere'),
        ('details', 'background_defaults', 'lived-in atmosphere'),
    ]
    assert all(atom.grammar_known is Truth.TRUE for atom in value.atoms)
    pads = value.atoms[1]
    assert pads.grammatical_subject_id == pads.source_part_ids[0]
    assert pads.owner_id == 'scene:0' and pads.antecedent_ids == ()
    assert pads.rule_ids == ('v2_scene_provenance.common_nominal:core/v1', 'scene.pads_wall_article/v1')
    assert all(atom.owner_id == 'scene:0' for atom in value.atoms[1:])
    assert scene.common_scene_parts(ctx['extras']['location_prompt'], ctx['loc']) == (
        'in a professional soundproof recording booth', (
            'featuring geometric sound isolation pads on the wall',
            'with a quiet focused atmosphere', 'with a lived-in atmosphere'))
    assert scene.common_standalone_scene_parts(ctx['extras']['location_prompt'], ctx['loc']) == (
        'in a professional soundproof recording booth that features geometric sound isolation pads on the wall'
        ' and that has a quiet focused atmosphere and that has a lived-in atmosphere', '')


def test_legacy_scene_grammar_is_unchanged():
    ctx = context()
    assert scene.producer_scene_parts(ctx['extras']['location_prompt'], ctx['loc']) is None
    assert scene.producer_owned_scene(ctx['extras']['location_prompt'], ctx['loc']) is None
    for raw, field in [('professional soundproof recording booth', 'environment'),
                       ('geometric sound isolation pads on wall', 'core'),
                       ('quiet focused atmosphere', 'fx'), ('lived-in atmosphere', 'details')]:
        assert scene._scene_nominal(raw, field) is None
        assert scene._nominal(raw, field) is None


@pytest.mark.parametrize('change', ['history', 'location', 'frame', 'simple', 'duplicate', 'missing', 'order'])
def test_booth_rejects_stale_history_locations_and_topology(change):
    ctx = context()
    if change == 'history':
        decision(ctx)['semantic_epig']['location_scene']['section_changes']['core']['semantic'] = []
    elif change == 'location':
        ctx['loc'] = 'opera_house'
    elif change == 'frame':
        ctx['extras']['action_frame']['legacy_slots']['location'] = 'opera_house'
    elif change == 'simple':
        decision(ctx)['template_key'] = 'simple'
    elif change == 'duplicate':
        ctx['extras']['location_prompt'] += ', quiet focused atmosphere'
    elif change == 'missing':
        ctx['extras']['location_prompt'] = ctx['extras']['location_prompt'].replace(', lived-in atmosphere', '')
    elif change == 'order':
        pieces = ctx['extras']['location_prompt'].split(', ')
        ctx['extras']['location_prompt'] = ', '.join((*pieces[1:], pieces[0]))
    assert component(ctx).trace is None


@pytest.mark.parametrize('field,raw', [
    ('weather', 'quiet focused atmosphere'), ('texture', 'lived-in atmosphere'),
    ('fx', '  quiet focused atmosphere  '), ('core', '  geometric sound isolation pads on wall  '),
    ('weather', 'featuring geometric sound isolation pads on wall'),
    ('environment', '  professional soundproof recording booth  '),
])
def test_booth_rejects_competing_catalog_origins(field, raw):
    packs = copy.deepcopy(scene.load_background_packs())
    packs['recording_studio'].setdefault(field, []).append(raw)
    with mock.patch.object(scene, 'load_background_packs', return_value=packs):
        assert component(context()).trace is None


@pytest.mark.parametrize('field,raw', [
    ('environment', 'soundproof professional booth'),
    ('core', 'sound isolation pads on the wall'),
    ('core', 'geometric pads'),
    ('fx', 'focused quiet atmosphere'),
    ('details', 'quiet lived-in atmosphere'),
])
def test_productive_grammar_still_requires_selected_field_membership(field, raw):
    ctx = context()
    original = selected(ctx, field)
    ctx['extras']['location_prompt'] = ctx['extras']['location_prompt'].replace(original, raw)
    decision(ctx)['semantic_epig']['location_scene']['section_changes'][field]['semantic'] = [raw] if field == 'core' else raw
    assert component(ctx).trace is None
    packs = copy.deepcopy(scene.load_background_packs())
    defaults = copy.deepcopy(scene.load_json('background_defaults.json'))
    source = defaults if field == 'details' else packs['recording_studio']
    source.setdefault(field, []).append(raw)
    with mock.patch.object(scene, 'load_background_packs', return_value=packs), mock.patch.object(scene, 'load_json', return_value=defaults):
        assert component(ctx).runtime_available


@pytest.mark.parametrize('field,raw', [
    ('environment', 'professional booth on wall'),
    ('core', 'geometric sound isolation pads on her'),
    ('core', 'geometric sound isolation pads on wall beside her'),
    ('core', 'geometric sound isolation pads on wall on wall'),
    ('core', 'geometric sound isolation pads while she waits'),
    ('core', 'geometric geometric pads'),
    ('core', 'sound geometric isolation pads'),
    ('core', 'lived-in atmosphere'),
    ('fx', 'quiet atmosphere follows her'),
    ('details', 'quiet quietly atmosphere'),
])
def test_catalog_membership_cannot_authorize_unknown_grammar_or_wrong_fields(field, raw):
    ctx = context()
    old = selected(ctx, field)
    ctx['extras']['location_prompt'] = ctx['extras']['location_prompt'].replace(old, raw)
    decision(ctx)['semantic_epig']['location_scene']['section_changes'][field]['semantic'] = [raw] if field == 'core' else raw
    packs = copy.deepcopy(scene.load_background_packs())
    defaults = copy.deepcopy(scene.load_json('background_defaults.json'))
    source = defaults if field == 'details' else packs['recording_studio']
    source.setdefault(field, []).append(raw)
    with mock.patch.object(scene, 'load_background_packs', return_value=packs), mock.patch.object(scene, 'load_json', return_value=defaults):
        assert component(ctx).trace is None


def test_section_shuffle_preserves_both_atmosphere_sources_without_deduplication():
    ctx = context()
    pieces = ctx['extras']['location_prompt'].split(', ')
    ctx['extras']['location_prompt'] = ', '.join((pieces[0], pieces[3], pieces[1], pieces[2]))
    value = component(ctx)
    assert value.runtime_available
    assert [part.source.field for part in value.trace.parts] == ['environment', 'details', 'core', 'fx']
    assert [atom.source_text for atom in value.atoms][-3:] == [
        'lived-in atmosphere', 'geometric sound isolation pads on wall', 'quiet focused atmosphere']
    rendered, time = scene.common_standalone_scene_parts(ctx['extras']['location_prompt'], ctx['loc'])
    assert rendered.endswith('that has a lived-in atmosphere and that features geometric sound isolation pads on the wall'
                             ' and that has a quiet focused atmosphere')
    assert not time
