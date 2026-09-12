"""Selected history narrows source; membership alone cannot prove clothing."""
import copy
from dataclasses import replace
from pathlib import Path
from unittest import mock

from history_service import clothing_signature_digest, clothing_signature_from_decision
from pipeline.clothing_candidate_renderer import build_variant_signature
from pipeline.realization_evidence import Truth, build_realization_evidence, validate_evidence_binding
from pipeline import v2_clothing_provenance as clothing
from pipeline import realization_evidence


def context(*, color='cream', details=('knit belt',), palette=()):
    garment = 'cozy sweater dress'
    raw = (color + ' ' if color else '') + garment + (', with ' + ', '.join(details) if details else '')
    decision = {'theme': 'street_casual', 'chosen_type': 'dresses', 'base_pack': 'winter_knit_dress',
                'base_variant': build_variant_signature([garment, color, '', '', '', *details]),
                'outerwear_pack': '', 'outerwear_variant': '', 'attempt_index': 0}
    decision['signature'] = clothing_signature_digest(clothing_signature_from_decision(decision))
    return {'costume': 'street_casual', 'extras': {'clothing_prompt': raw, 'raw_costume_key': 'street_casual',
             'character_palette_str': ', '.join(palette), 'color_palette': list(palette)},
            'history': [{'node': 'ContextClothingExpander', 'seed': 17, 'decision': decision}]}


def component(ctx):
    return next(item for item in build_realization_evidence({'context': ctx}).components if item.domain == 'clothing')


def test_latest_selected_pack_binds_without_guessing_past_renderer_settings():
    ctx = context()
    original = copy.deepcopy(ctx)
    value = component(ctx)
    assert value.runtime_available and value.trace.mode == 'bound_constructor'
    assert value.atoms[0].grammar_known is Truth.TRUE
    assert value.atoms[0].owner_id == 'protagonist'
    assert value.trace.omitted_parts is None
    assert all(part.source.catalog_key in ('dresses:winter_knit_dress', None) for part in value.trace.parts)
    assert ctx == original and 'outfit_mode' not in ctx['history'][-1]['decision']
    assert 'outerwear_chance' not in ctx['history'][-1]['decision']


def test_missing_or_stale_latest_history_never_falls_back_to_an_older_match():
    ctx = context()
    for broken in ({**ctx, 'history': []}, {**ctx, 'history': None},
                   {**ctx, 'history': [*ctx['history'], {'node': 'ContextClothingExpander', 'decision': {}}]}):
        assert component(broken).trace is None
    for field in ('base_pack', 'base_variant', 'signature', 'chosen_type'):
        broken = copy.deepcopy(ctx)
        broken['history'][-1]['decision'][field] = 'different'
        assert component(broken).trace is None
    broken = copy.deepcopy(ctx)
    broken['extras']['clothing_prompt'] += ', with fuzzy leg warmers'
    assert component(broken).trace is None


def test_selected_history_does_not_scan_unrelated_or_ambiguous_other_packs():
    packs = copy.deepcopy(clothing.clothing_vocab.CONCEPT_PACKS)
    packs['dresses']['unrelated_duplicate'] = copy.deepcopy(packs['dresses']['winter_knit_dress'])
    class SelectedOnly(dict):
        def values(self):
            raise AssertionError('Do not scan unrelated packs')
        def items(self):
            raise AssertionError('Do not scan unrelated packs')
    narrowed = SelectedOnly({key: SelectedOnly(value) for key, value in packs.items()})
    with mock.patch.object(clothing.clothing_vocab, 'CONCEPT_PACKS', narrowed):
        assert component(context()).trace is not None


def test_duplicate_field_origins_and_unproved_grammar_are_unknown():
    packs = copy.deepcopy(clothing.clothing_vocab.CONCEPT_PACKS)
    pack = packs['dresses']['winter_knit_dress']
    pack['optional_details'].append('knit belt')
    with mock.patch.object(clothing.clothing_vocab, 'CONCEPT_PACKS', packs):
        assert component(context()).trace is None
    packs = copy.deepcopy(clothing.clothing_vocab.CONCEPT_PACKS)
    choices = packs['dresses']['winter_knit_dress']['choices']
    # String and [noun, modifier] origins render/sign identically. Do not pick one.
    next(iter(choices.values())).append('cozy sweater dress')
    with mock.patch.object(clothing.clothing_vocab, 'CONCEPT_PACKS', packs):
        assert component(context()).trace is None
    packs = copy.deepcopy(clothing.clothing_vocab.CONCEPT_PACKS)
    packs['dresses']['winter_knit_dress']['optional_details'].append('the stranger waves')
    with mock.patch.object(clothing.clothing_vocab, 'CONCEPT_PACKS', packs):
        value = component(context(details=('the stranger waves',)))
        assert value.trace is None and value.runtime_available is False


def test_character_palette_is_bound_and_ambiguous_color_origins_fail_closed():
    assert component(context(color='charcoal grey', palette=('charcoal grey',))).trace is not None
    assert component(context(color='charcoal grey', palette=('red',))).trace is None
    assert component(context(color='cream', palette=('cream',))).trace is None
    assert component(context(color='she waves', palette=('she waves',))).trace is None


def test_outerwear_and_multigarment_ownership_are_not_invented():
    for change in ({'outerwear_pack': 'coat', 'outerwear_variant': 'red~coat'}, {'chosen_type': 'separates'}):
        ctx = context()
        ctx['history'][-1]['decision'].update(change)
        decision = ctx['history'][-1]['decision']
        decision['signature'] = clothing_signature_digest(clothing_signature_from_decision(decision))
        assert component(ctx).trace is None


def test_common_validation_rejects_changed_history_palette_and_forged_owner():
    ctx = context()
    inputs = {'context': ctx}
    value = build_realization_evidence(inputs)
    assert validate_evidence_binding(value, inputs)
    for field in ('base_pack', 'attempt_index', 'base_variant'):
        changed = copy.deepcopy(inputs)
        changed['context']['history'][-1]['decision'][field] = 'changed'
        assert not validate_evidence_binding(value, changed)
    clothes = value.components[1]
    forged = replace(value, components=(value.components[0], replace(clothes, atoms=(replace(clothes.atoms[0], owner_id='other'),)), *value.components[2:]))
    assert not validate_evidence_binding(forged, inputs)


def test_explicit_null_current_clothing_does_not_become_context_proof():
    value = build_realization_evidence({'context': context(), 'clothing': None})
    assert value.components[1].trace is None


def test_cached_source_identity_covers_clothing_sanitizer_code():
    original_read = Path.read_bytes
    def changed_policy(path):
        data = original_read(path)
        return data + b'\n# source changed\n' if path.name == 'semantic_policy.py' else data
    before = realization_evidence._source_identity()
    with mock.patch.object(Path, 'read_bytes', changed_policy):
        assert realization_evidence._source_identity() != before
