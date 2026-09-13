"""Scene binding keeps raw parts, locations, owners and antecedents separate."""
import copy
from dataclasses import replace
from unittest import mock

from pipeline.realization_evidence import Truth, build_realization_evidence, validate_evidence_binding
from pipeline import v2_scene_provenance as scene


GALLERY = 'small contemporary gallery arranged for a weekday viewing'
WORKS = 'framed canvas works spaced along the wall'
PLAQUES = 'small title plaques mounted beside each work'


def context(location=GALLERY + ', featuring ' + WORKS + ' and ' + PLAQUES, *, key='art_gallery', mode='detailed'):
    return {'loc': key, 'extras': {'raw_loc_tag': key, 'location_prompt': location},
            'history': [{'node': 'ContextLocationExpander', 'seed': 17,
                         'decision': {'pack_key': key, 'objects': [], 'selected_props': [], 'template_key': mode}}]}


def component(ctx, **extra):
    return build_realization_evidence({'context': ctx, **extra}).components[4]


def test_gallery_predicates_keep_their_own_subject_and_sibling_reference():
    ctx = context()
    value = component(ctx)
    assert value.runtime_available and value.trace.mode == 'bound_constructor'
    assert value.trace.omitted_parts is None
    environment, works, plaques = value.atoms
    assert environment.source_text == GALLERY and environment.grammatical_subject_id == 'scene:0'
    assert works.source_text == WORKS and works.grammatical_subject_id == works.source_part_ids[0]
    assert works.owner_id == 'scene:0'
    assert plaques.source_text == PLAQUES and plaques.grammatical_subject_id == plaques.source_part_ids[0]
    assert plaques.owner_id == 'scene:0'
    assert plaques.antecedent_ids == works.source_part_ids
    assert all(atom.owner_id != 'protagonist' for atom in value.atoms)
    assert ctx['history'][-1]['decision']['template_key'] == 'detailed'
    assert 'lighting_mode' not in ctx['history'][-1]['decision']


def test_missing_reference_wrong_owner_and_unknown_weather_keep_original_text():
    for text in (GALLERY + ', featuring ' + PLAQUES,
                 GALLERY + ', featuring ' + PLAQUES + ' and ' + WORKS,
                 GALLERY + ', featuring ' + WORKS + ' and small title plaques mounted beside her',
                 GALLERY + ', unrecognized crowd clause'):
        value = component(context(text))
        assert value.trace is None and not value.runtime_available
        assert value.atoms[0].source_text == text
        assert value.atoms[0].grammar_known is Truth.UNKNOWN
        assert value.atoms[0].antecedent_ids is None

    text = GALLERY + ', soft daylight filtered through the front glass'
    value = component(context(text))
    assert value.trace is not None and value.runtime_available
    assert [(part.source.field, part.source.catalog_key, part.text) for part in value.trace.parts] == [
        ('environment', 'art_gallery', GALLERY),
        ('weather', 'art_gallery', 'soft daylight filtered through the front glass')]
    assert value.atoms[1].grammar_known is Truth.UNKNOWN
    assert value.atoms[1].antecedent_ids is None
    assert 'scene.grammar_unknown' in value.blockers
    assert 'scene.r45_source_only_permission_deferred' in value.blockers
    assert scene.common_scene_parts(text, 'art_gallery') is None


def test_latest_history_and_current_raw_frame_locations_must_agree():
    ctx = context()
    for changed in ({**ctx, 'history': []}, {**ctx, 'history': None},
                    {**ctx, 'loc': 'opera_house'},
                    {**ctx, 'extras': {**ctx['extras'], 'raw_loc_tag': 'opera_house'}},
                    {**ctx, 'history': [*ctx['history'], {'node': 'ContextLocationExpander', 'decision': {}}]}):
        assert component(changed).trace is None
    assert component(ctx, action_frame={'legacy_slots': {'location': 'opera_house'}}).trace is None
    assert component(ctx, scene=None).trace is None
    assert component(ctx, scene='other text').trace is None


def test_simple_mode_does_not_require_absent_semantic_diagnostics():
    value = component(context(GALLERY, mode='simple'))
    assert value.trace is not None and len(value.atoms) == 1
    assert component(context(GALLERY + ', atmospheric perspective', mode='simple')).trace is None


def test_available_selected_section_history_rejects_stale_and_hidden_parts():
    ctx = context()
    history = ctx['history'][-1]['decision']
    history['semantic_epig'] = {'location_scene': {'mode': 'active', 'section_changes': {
        'environment': {'semantic': GALLERY}, 'core': {'semantic': [WORKS, PLAQUES]}}}}
    assert component(ctx).trace is not None
    changed = copy.deepcopy(ctx)
    changes = changed['history'][-1]['decision']['semantic_epig']['location_scene']['section_changes']
    changes['core']['semantic'] = [PLAQUES, WORKS]
    assert component(changed).trace is None
    changes['core']['semantic'] = [WORKS, PLAQUES]
    changes['weather'] = {'semantic': 'hidden weather must not be discarded'}
    assert component(changed).trace is None
    changed = copy.deepcopy(ctx)
    changed['history'][-1]['decision']['selected_props'] = ['missing prop']
    assert component(changed).trace is None


def test_default_sources_and_ambiguous_origins_are_distinct():
    value = component(context(GALLERY + ', atmospheric perspective'))
    assert value.trace.parts[-1].source.catalog_key == 'background_defaults'
    assert value.trace.parts[-1].source.field == 'details'
    packs = copy.deepcopy(scene.load_background_packs())
    packs['art_gallery']['weather'].append('atmospheric perspective')
    with mock.patch.object(scene, 'load_background_packs', return_value=packs):
        assert component(context(GALLERY + ', atmospheric perspective')).trace is None


def test_prefix_and_normalization_cannot_hide_competing_bare_origins():
    for raw, text in (('featuring ' + WORKS, GALLERY + ', featuring ' + WORKS),
                      ('  atmospheric perspective  ', GALLERY + ', atmospheric perspective')):
        packs = copy.deepcopy(scene.load_background_packs())
        packs['art_gallery']['weather'].append(raw)
        with mock.patch.object(scene, 'load_background_packs', return_value=packs):
            assert component(context(text)).trace is None


def test_normalized_atom_and_joined_source_ambiguity_remain_unknown():
    for field, raw in (('environment', '  ' + GALLERY + '  '),
                       ('environment', GALLERY + ', featuring ' + WORKS + ' and ' + PLAQUES),
                       ('core', '  ' + WORKS + '  '), ('core', WORKS + ' and ' + PLAQUES)):
        packs = copy.deepcopy(scene.load_background_packs())
        packs['art_gallery'][field].append(raw)
        with mock.patch.object(scene, 'load_background_packs', return_value=packs):
            assert component(context()).trace is None


def test_current_order_and_reference_cannot_be_forged_with_matching_checksum():
    ctx = context(GALLERY + ', atmospheric perspective, featuring ' + WORKS + ' and ' + PLAQUES)
    value = build_realization_evidence({'context': ctx})
    common = value.components[4]
    assert common.trace is not None
    assert [part.source.field for part in common.trace.parts] == ['environment', 'details', 'core', 'core']
    assert validate_evidence_binding(value, {'context': ctx})
    forged = replace(common, atoms=(*common.atoms[:-1], replace(common.atoms[-1], antecedent_ids=())))
    altered = replace(value, components=(*value.components[:4], forged, *value.components[5:]))
    assert not validate_evidence_binding(altered, {'context': ctx})
    changed = copy.deepcopy(ctx)
    changed['extras']['location_prompt'] = GALLERY + ', featuring ' + WORKS + ' and ' + PLAQUES + ', atmospheric perspective'
    assert not validate_evidence_binding(value, {'context': changed})
