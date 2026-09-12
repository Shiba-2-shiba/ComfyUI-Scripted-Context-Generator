"""Bind source template topology before preserving a scene wrapper as finite.

These functions prove the wrapper only. The caller must independently prove the
locative scene's constituents before materialization; source membership cannot
establish their grammar or attachment.
"""
from collections.abc import Mapping
import json
import re

try:
    from ..vocab.loader import load_json
except ImportError:
    from vocab.loader import load_json


_OWNED_SCENE = re.compile(
    r'(?:and|with) (?P<owner>the (?:room|scene) around her) staying in '
    r'\{scene_anchor_clause\}'
)


def scene_template_kind(slots):
    """Classify an exact catalog triple with independently known slot grammar."""
    if not isinstance(slots, Mapping):
        return None
    if slots.get('subject') != '{subject_clause}' or slots.get('adjunct') != '{action_clause}':
        return None
    scene = slots.get('scene')
    if not isinstance(scene, str):
        return None
    if scene == '{scene_clause}':
        kind = 'direct'
    elif _OWNED_SCENE.fullmatch(scene):
        kind = 'owned_finite'
    else:
        return None
    catalog = load_json('template_catalog.json')
    if not isinstance(catalog, Mapping):
        return None
    for slot, field in (('subject', 'intro'), ('adjunct', 'body'), ('scene', 'end')):
        entries = catalog.get(field)
        if not isinstance(entries, (list, tuple)) or not any(
            isinstance(entry, Mapping) and entry.get('text') == slots[slot]
            for entry in entries
        ):
            return None
    return kind


def materialize_scene_template(slots, locative_scene, *, attachment='finite'):
    """Preserve proved scene text, changing only a link and staying's inflection."""
    kind = scene_template_kind(slots)
    if (attachment not in {'finite', 'absolute'} or kind is None or not isinstance(locative_scene, str)
            or not locative_scene or locative_scene.strip() != locative_scene
            or re.search(r'[{}.!?;\r\n]', locative_scene)):
        return None
    if kind == 'direct':
        # Existing direct constructors also produce 'on' for road/street.
        # This checks the wrapper boundary only; noun proof remains upstream.
        return locative_scene if re.fullmatch(r'(?:in|on) [^\s].*', locative_scene) else None
    if not locative_scene.startswith('in ') or not locative_scene[3:] or locative_scene[3:].strip() != locative_scene[3:]:
        return None
    owner = _OWNED_SCENE.fullmatch(slots['scene']).group('owner')
    if attachment == 'absolute':
        return 'with ' + owner + ' staying ' + locative_scene
    return owner + ' stays ' + locative_scene


def adapt_template_component(inputs, *, input_binding_sha256, source_identity_sha256):
    """Bind the selected normalized catalog triple without widening its grammar.

    Slots are the renderer's current template fragments, before substitution.
    A recognized attention suffix omission is diagnostic only: proving the
    renderer's pruning condition and authorizing that topology remain separate.
    """
    from .realization_evidence import (
        ClauseEvidence, EvidenceComponent, ProducerPart, ProducerTrace, SourceRef,
        Truth, text_sha256,
    )
    if __package__ and '.' in __package__:
        from ..prompt_renderer import _load_template_catalog, _template_entries
    else:
        from prompt_renderer import _load_template_catalog, _template_entries

    fields = (('subject', 'intro'), ('adjunct', 'body'), ('scene', 'end'))
    selected = inputs.get('selected_templates') if isinstance(inputs, Mapping) else None
    slots = inputs.get('template_slots') if isinstance(inputs, Mapping) else None

    def unavailable(blocker):
        # Retain both received fragments and differing source text for diagnosis;
        # missing source identity must never erase unsupported input.
        atoms = []
        for slot, section in fields:
            current = slots.get(slot) if isinstance(slots, Mapping) else None
            entry = selected.get(section) if isinstance(selected, Mapping) else None
            original = entry.get('text') if isinstance(entry, Mapping) else None
            for label, text in (('current', current), ('selected', original)):
                if not isinstance(text, str) or (label == 'selected' and text == current):
                    continue
                atoms.append(ClauseEvidence(
                    atom_id=f'template:{section}:{label}:unbound', source_part_ids=(), source_text=text,
                    grammar_known=Truth.UNKNOWN, grammatical_subject_id=None, owner_id=None,
                    form='template_wrapper', attachment=slot, same_subject=Truth.UNKNOWN,
                    place_refs=None, antecedent_ids=None, rule_ids=(),
                ))
        return EvidenceComponent('template', None, tuple(atoms), False, (blocker,))

    if not isinstance(inputs, Mapping):
        return unavailable('transport.runtime_inputs_missing')
    if (not isinstance(selected, Mapping) or set(selected) != {'intro', 'body', 'end'}
            or not isinstance(slots, Mapping) or set(slots) != {'subject', 'adjunct', 'scene'}):
        return unavailable('transport.runtime_inputs_missing')
    catalog = _load_template_catalog()
    producer = 'prompt_renderer'
    parts, omitted = [], []
    suffix = ', her attention fixed on it'
    for slot, section in fields:
        entry, text = selected[section], slots[slot]
        if (not isinstance(entry, Mapping) or not isinstance(text, str)
                or not isinstance(catalog, Mapping)
                or not isinstance(catalog.get(section), (list, tuple))):
            return unavailable('binding.template_entry_mismatch')
        # Match the whole normalized entry, including roles and selection
        # metadata. JSON equality also distinguishes injected 0 from False.
        try:
            matches = [candidate for candidate in _template_entries(section)
                       if candidate['key'] == entry.get('key')]
            if len(matches) != 1 or json.dumps(dict(entry), sort_keys=True, allow_nan=False) != json.dumps(
                    matches[0], sort_keys=True, allow_nan=False):
                return unavailable('binding.template_entry_mismatch')
        except (TypeError, ValueError):
            return unavailable('binding.template_entry_mismatch')
        original = entry['text']
        part_id = 'template:' + section
        source = SourceRef('template', producer, section, entry['key'], text_sha256(original))
        parts.append(ProducerPart(part_id, source, text))
        if text != original:
            if section != 'body' or not original.endswith(suffix) or text != original[:-len(suffix)]:
                return unavailable('binding.current_text_mismatch')
            omitted.append(ProducerPart(part_id + ':attention_suffix', source, suffix))
    # Reuse only the existing direct and owned-finite wrapper proof. Source
    # membership and a recognized omission cannot authorize a new topology.
    kind = scene_template_kind(slots) if not omitted else None
    emitted_ids = tuple(part.part_id for part in parts)
    trace = ProducerTrace(
        mode='bound_constructor', producer=producer,
        source_identity_sha256=source_identity_sha256, input_binding_sha256=input_binding_sha256,
        raw_output_sha256=text_sha256('\n'.join(selected[section]['text'] for _, section in fields)),
        emitted_output_sha256=text_sha256('\n'.join(slots[slot] for slot, _ in fields)),
        parts=tuple(parts + omitted), emitted_part_ids=emitted_ids,
        omitted_parts=tuple((part.part_id, 'template.recognized_attention_suffix_omission') for part in omitted),
        constructor_id='template_topology:' + (kind or 'unknown'),
    )
    known = Truth.TRUE if kind else Truth.UNKNOWN
    scene_subject = ('template:' + _OWNED_SCENE.fullmatch(slots['scene']).group('owner').split()[1]
                     if kind == 'owned_finite' else None)
    atoms = tuple(ClauseEvidence(
        atom_id=part.part_id + ':topology', source_part_ids=(part.part_id,), source_text=part.text,
        grammar_known=known, grammatical_subject_id=scene_subject if slot == 'scene' else None, owner_id=None,
        form='template_wrapper', attachment=slot, same_subject=Truth.UNKNOWN,
        # "around her" references the protagonist spatially; it does not prove
        # that she owns the room or makes the room the grammatical protagonist.
        place_refs=None, antecedent_ids=('protagonist',) if slot == 'scene' and scene_subject else None,
        rule_ids=('v2_template_provenance.scene_template_kind:' + kind,) if kind else (),
    ) for part, (slot, _) in zip(parts, fields))
    blockers = () if kind else ('template.topology_unknown',)
    if omitted:
        blockers += ('template.pruning_condition_unknown',)
    return EvidenceComponent('template', trace, atoms, True,
                             blockers,
                             (('template_topology_known', known),))
