"""Common-only reviewed Scene grammar still requires exact producer origins."""
import copy
import json
from pathlib import Path
from unittest import mock

import pytest

from pipeline import v2_scene_provenance as scene
from pipeline.realization_evidence import Truth, build_realization_evidence


def context():
    cases = json.loads((Path(__file__).parent / 'fixtures/r43_real_graph_cases.json').read_text(encoding='utf-8'))
    case = next(case for case in cases['cases'] if case['run_seed'] == 51)
    return json.loads(case['builder_inputs']['context_json'])


def component(ctx, **extra):
    return build_realization_evidence({'context': ctx, **extra}).components[4]


def decision(ctx):
    return next(row['decision'] for row in reversed(ctx['history']) if row['node'] == 'ContextLocationExpander')


def test_actual_observatory_keeps_raw_order_and_default_origins():
    ctx = context()
    value = component(ctx)
    assert value.runtime_available
    assert value.trace.constructor_id == 'scene.reviewed_legacy_constituents/v1'
    assert [(part.source.field, part.source.catalog_key, part.text) for part in value.trace.parts] == [
        ('environment', 'observatory_dome', 'circular telescope chamber'),
        ('texture', 'background_defaults', 'polished finish'),
        ('time', 'observatory_dome', 'deep moonless night'),
        ('details', 'background_defaults', 'layered background depth'),
        ('core', 'observatory_dome', 'large equatorial telescope'),
        ('core', 'observatory_dome', 'curved rotating dome track'),
        ('props', 'observatory_dome', 'weather monitor'),
    ]
    assert all(atom.grammar_known is Truth.TRUE for atom in value.atoms)
    assert all(atom.owner_id == 'scene:0' for atom in value.atoms[1:])
    assert 'temporal_attachment_safe' not in dict(value.facts)
    assert scene.common_scene_parts(ctx['extras']['location_prompt'], ctx['loc']) == (
        'in a circular telescope chamber', (
            'with a polished finish', 'during a deep moonless night', 'with layered background depth',
            'featuring a large equatorial telescope and a curved rotating dome track', 'with a weather monitor'))


@pytest.mark.parametrize('change', ['current', 'location', 'raw', 'frame', 'mode', 'props', 'semantic', 'latest', 'duplicate'])
def test_reviewed_route_rejects_stale_binding_and_duplicate_sections(change):
    ctx = context()
    extra = {}
    if change == 'current':
        extra['scene'] = 'other scene'
    elif change == 'location':
        ctx['loc'] = 'antique_shop'
    elif change == 'raw':
        ctx['extras']['raw_loc_tag'] = 'antique_shop'
    elif change == 'frame':
        extra['action_frame'] = {'legacy_slots': {'location': 'antique_shop'}}
    elif change == 'mode':
        decision(ctx)['template_key'] = 'simple'
    elif change == 'props':
        decision(ctx)['selected_props'] = []
    elif change == 'semantic':
        decision(ctx)['semantic_epig']['location_scene']['section_changes']['core']['semantic'].reverse()
    elif change == 'latest':
        ctx['history'].append({'node': 'ContextLocationExpander', 'decision': {}})
    elif change == 'duplicate':
        ctx['extras']['location_prompt'] += ', polished finish'
    assert component(ctx, **extra).trace is None


@pytest.mark.parametrize('field,raw', [
    ('texture', 'polished finish'), ('weather', '  polished finish  '),
    ('weather', 'with weather monitor'), ('core', '  large equatorial telescope  '),
    ('core', 'large equatorial telescope and curved rotating dome track'),
    ('environment', '  circular telescope chamber  '),
])
def test_reviewed_route_rejects_competing_normalized_and_default_origins(field, raw):
    packs = copy.deepcopy(scene.load_background_packs())
    packs['observatory_dome'].setdefault(field, []).append(raw)
    with mock.patch.object(scene, 'load_background_packs', return_value=packs):
        assert component(context()).trace is None


def test_catalog_membership_does_not_grant_reviewed_grammar():
    ctx = context()
    ctx['extras']['location_prompt'] = 'circular telescope chamber, featuring telescope silently rotating'
    decision(ctx).pop('semantic_epig')
    decision(ctx)['selected_props'] = []
    packs = copy.deepcopy(scene.load_background_packs())
    packs['observatory_dome']['core'].append('telescope silently rotating')
    with mock.patch.object(scene, 'load_background_packs', return_value=packs):
        value = component(ctx)
        assert value.trace is not None and value.runtime_available
        assert [(part.source.field, part.source.catalog_key, part.text) for part in value.trace.parts] == [
            ('environment', 'observatory_dome', 'circular telescope chamber'),
            ('core', 'observatory_dome', 'telescope silently rotating')]
        assert value.atoms[1].grammar_known is Truth.UNKNOWN
        assert value.atoms[1].antecedent_ids is None
        assert 'scene.grammar_unknown' in value.blockers
        assert 'scene.r45_source_only_permission_deferred' in value.blockers
        assert scene.common_scene_parts(ctx['extras']['location_prompt'], ctx['loc']) is None


def test_reviewed_vocabulary_without_catalog_membership_stays_unknown():
    ctx = context()
    packs = copy.deepcopy(scene.load_background_packs())
    packs['observatory_dome']['props'].remove('weather monitor')
    with mock.patch.object(scene, 'load_background_packs', return_value=packs):
        assert component(ctx).trace is None


def test_existing_producer_scene_api_and_modern_owned_restrictions_are_unchanged():
    ctx = context()
    assert scene.producer_scene_parts(ctx['extras']['location_prompt'], ctx['loc']) is None
    assert scene.producer_owned_scene(ctx['extras']['location_prompt'], ctx['loc']) is None
    location = 'small contemporary gallery arranged for a weekday viewing, during quiet evening performance'
    assert scene.common_scene_parts(location, 'art_gallery') == scene.producer_scene_parts(location, 'art_gallery')
    assert scene.producer_owned_scene(location, 'art_gallery') is None
