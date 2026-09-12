"""Selected template source identity does not independently prove topology."""
import copy
from unittest import mock

import prompt_renderer
from pipeline import v2_template_provenance as template
from pipeline.realization_evidence import Truth


def inputs(*, intro='intro_plain_subject', body='body_direct_clause', end='end_scene_direct'):
    selected = {
        section: copy.deepcopy(next(entry for entry in prompt_renderer._template_entries(section)
                                    if entry['key'] == key))
        for section, key in (('intro', intro), ('body', body), ('end', end))
    }
    return {'selected_templates': selected, 'template_slots': {
        slot: selected[section]['text']
        for slot, section in (('subject', 'intro'), ('adjunct', 'body'), ('scene', 'end'))}}


def adapt(value):
    return template.adapt_template_component(value, input_binding_sha256='input-digest',
                                             source_identity_sha256='source-digest')


def test_direct_and_owned_finite_keep_source_parts_and_exact_entry_keys():
    for end, kind in (('end_scene_direct', 'direct'), ('end_scene_room', 'owned_finite'),
                      ('end_scene_holding', 'owned_finite')):
        value = inputs(end=end)
        before = copy.deepcopy(value)
        component = adapt(value)
        assert component.runtime_available and not component.blockers
        assert component.trace.mode == 'bound_constructor'
        assert component.trace.constructor_id == 'template_topology:' + kind
        assert component.trace.input_binding_sha256 == 'input-digest'
        assert component.trace.source_identity_sha256 == 'source-digest'
        assert [part.text for part in component.trace.parts] == list(value['template_slots'].values())
        assert [part.source.catalog_key for part in component.trace.parts] == [
            entry['key'] for entry in value['selected_templates'].values()]
        assert all(atom.grammar_known is Truth.TRUE for atom in component.atoms)
        if kind == 'owned_finite':
            assert component.atoms[-1].grammatical_subject_id == (
                'template:room' if end == 'end_scene_room' else 'template:scene')
            assert component.atoms[-1].antecedent_ids == ('protagonist',)
        assert value == before


def test_key_text_roles_and_all_metadata_must_match_current_catalog_exactly():
    for field, replacement in (('key', 'injected'), ('text', '{unknown_placeholder}'),
                               ('roles', ['social']), ('needs_loc', True),
                               ('needs_loc', 0), ('max_action_words', 100),
                               ('preferred_surfaces', ['clause']), ('extra', 'injected')):
        value = inputs()
        value['selected_templates']['intro'][field] = replacement
        if field == 'text':
            value['template_slots']['subject'] = replacement
        component = adapt(value)
        assert not component.runtime_available and component.trace is None, field
        assert component.atoms and all(atom.grammar_known is Truth.UNKNOWN for atom in component.atoms)
        if field == 'text':
            assert replacement in [atom.source_text for atom in component.atoms]
    value = inputs()
    value['selected_templates']['body'].pop('roles')
    assert adapt(value).trace is None


def test_missing_malformed_free_form_and_stale_slots_fail_closed():
    for value in (None, {}, {'selected_templates': {}}, {'selected_templates': 'free text'},
                  {**inputs(), 'template_slots': None}):
        assert adapt(value).trace is None
    for slot in ('subject', 'adjunct', 'scene'):
        value = inputs()
        value['template_slots'][slot] += ' stale'
        component = adapt(value)
        assert component.trace is None
        assert value['template_slots'][slot] in [atom.source_text for atom in component.atoms]


def test_catalog_membership_with_unknown_topology_retains_unknown_grammar():
    component = adapt(inputs(intro='intro_pause_subject'))
    assert component.runtime_available and component.trace is not None
    assert component.blockers == ('template.topology_unknown',)
    assert all(atom.grammar_known is Truth.UNKNOWN for atom in component.atoms)


def test_pruned_attention_suffix_is_traced_without_new_topology_authorization():
    value = inputs(body='body_attention_on_action')
    value['template_slots']['adjunct'] = '{action_clause}'
    component = adapt(value)
    assert component.runtime_available
    assert component.blockers == ('template.topology_unknown', 'template.pruning_condition_unknown')
    assert component.trace.omitted_parts == ((
        'template:body:attention_suffix', 'template.recognized_attention_suffix_omission'),)
    assert component.trace.parts[-1].text == ', her attention fixed on it'
    assert component.trace.parts[-1].part_id not in component.trace.emitted_part_ids


def test_stale_or_ambiguous_current_catalog_does_not_reuse_selected_entry():
    value = inputs()
    catalog = copy.deepcopy(prompt_renderer._load_template_catalog())
    catalog['intro'][0]['roles'] = ['changed']
    with mock.patch.object(prompt_renderer, '_template_catalog_cache', catalog):
        assert adapt(value).trace is None
    catalog = copy.deepcopy(prompt_renderer._load_template_catalog())
    catalog['intro'].append(copy.deepcopy(catalog['intro'][0]))
    with mock.patch.object(prompt_renderer, '_template_catalog_cache', catalog):
        assert adapt(value).trace is None
