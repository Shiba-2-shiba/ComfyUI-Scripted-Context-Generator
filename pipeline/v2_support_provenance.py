"""Bind received support fields separately from the existing closed grammar.

Source reconstruction cannot authorize a clause. Unknown source or grammar
keeps the complete current text and unknown ownership. These adapters neither
sample producers nor infer missing node settings or filtered-away selections.
"""
from collections.abc import Mapping
from dataclasses import replace
import json
from pathlib import Path

from .character_profile_pipeline import build_character_profile
from .realization_evidence import (
    ClauseEvidence, EvidenceComponent, ProducerPart, ProducerTrace, SourceRef, Truth, text_sha256,
)

if __package__ and '.' in __package__:
    from ..character_service import load_character_profiles
else:
    from character_service import load_character_profiles


_MOOD_MAP = json.loads((Path(__file__).resolve().parents[1] / 'mood_map.json').read_text(encoding='utf-8'))


def _received(inputs, domain, section, field):
    context = inputs.get('context')
    if not isinstance(context, Mapping):
        return None, None
    source = context if section is None else context.get(section)
    if not isinstance(source, Mapping):
        return context, None
    raw = source.get(field)
    current = inputs.get(domain, raw)
    return context, raw if isinstance(raw, str) and isinstance(current, str) and current == raw else None


def _atom(domain, text, part_ids=(), *, known=False, subject=None, owner=None,
          form='unknown', attachment='unknown', same_subject=Truth.UNKNOWN, rule_ids=()):
    return ClauseEvidence(
        atom_id=f'{domain}:{part_ids[0] if part_ids else "current"}', source_part_ids=part_ids,
        source_text=text, grammar_known=Truth.TRUE if known else Truth.UNKNOWN,
        grammatical_subject_id=subject if known else None, owner_id=owner if known else None,
        form=form if known else 'unknown', attachment=attachment if known else 'unknown',
        same_subject=same_subject if known else Truth.UNKNOWN,
        # The compatibility grammar did not establish general place/reference facts.
        place_refs=None, antecedent_ids=None, rule_ids=rule_ids if known else (),
    )


def _unbound(inputs, domain, raw=None):
    current = inputs.get(domain, raw)
    atoms = (_atom(domain, current),) if isinstance(current, str) else ()
    return EvidenceComponent(domain, None, atoms, False, (f'{domain}.source_binding_unknown',))


def _bound(domain, raw, fields, atoms, *, input_binding_sha256, source_identity_sha256):
    parts = tuple(ProducerPart(part_id, SourceRef(domain, producer, field, key, text_sha256(text)), text)
                  for part_id, producer, field, key, text in fields)
    trace = ProducerTrace(
        mode='bound_constructor', producer=f'{domain}.received_constructor',
        source_identity_sha256=source_identity_sha256, input_binding_sha256=input_binding_sha256,
        raw_output_sha256=text_sha256(raw), emitted_output_sha256=text_sha256(raw),
        parts=parts, emitted_part_ids=tuple(part.part_id for part in parts), omitted_parts=None,
        constructor_id=f'r43.{domain}.received_source/v1',
    )
    blockers = () if all(atom.grammar_known is Truth.TRUE for atom in atoms) else (f'{domain}.unsupported_constructor',)
    return EvidenceComponent(domain, trace, tuple(atoms), True, blockers)


def adapt_subject_component(inputs, *, input_binding_sha256, source_identity_sha256):
    """Rebuild the existing fixed profile constructor, with no new appearance rules."""
    from .v2_direct_provenance import _subject

    context, raw = _received(inputs, 'subject', None, 'subj')
    if raw is None:
        return _unbound(inputs, 'subject', context.get('subj') if context else None)
    extras = context.get('extras')
    if not isinstance(extras, Mapping):
        return _unbound(inputs, 'subject', raw)
    name = extras.get('character_name')
    profiles = load_character_profiles()
    if not isinstance(name, str) or name not in profiles:
        return _unbound(inputs, 'subject', raw)
    # Fixed mode never draws a profile; reuse the actual constructor, not a
    # second handwritten version of its hair/eye assembly.
    rebuilt = build_character_profile(0, 'fixed', name, profiles)
    if raw != rebuilt['subj_prompt'] or any(
        key in extras and extras[key] != rebuilt[key]
        for key in ('hair_color', 'eye_color', 'color_palette')
    ):
        return _unbound(inputs, 'subject', raw)
    traits = profiles[name].get('visual_traits', {})
    fields = tuple((f'subject:{field}', 'CharacterProfile', f'visual_traits.{field}', name, traits[field])
                   for field in ('hair_style', 'hair_color', 'eye_color') if traits.get(field))
    known = _subject(raw) is not None
    atom = _atom('subject', raw, tuple(field[0] for field in fields), known=known,
                 subject='protagonist', owner='protagonist', form='nominal', attachment='main',
                 same_subject=Truth.TRUE, rule_ids=('legacy.subject.profile_nominal',))
    return _bound('subject', raw, fields, (atom,), input_binding_sha256=input_binding_sha256,
                  source_identity_sha256=source_identity_sha256)


def _reconstruct_garnish_policy(inputs, context, raw, current, tags):
    """Replay only the received Builder inputs through the existing pure policies."""
    if __package__ and '.' in __package__:
        from .. import prompt_renderer as renderer
    else:
        import prompt_renderer as renderer

    extras, meta = context.get('extras'), context.get('meta')
    if (not isinstance(meta, Mapping) or type(inputs.get('composition_mode')) is not bool
            or 'action_frame' not in inputs
            or any(not isinstance(value, str) for value in (
                context.get('action'), context.get('subj'), meta.get('mood'), extras.get('staging_tags')))):
        return None
    frame = inputs['action_frame']
    if (frame is not None and not isinstance(frame, Mapping)
            or 'action_frame' in extras and frame != extras['action_frame']):
        return None
    layers = renderer._arbitrate_prompt_cues(
        action=context['action'], garnish=raw, meta_mood=meta['mood'],
        staging_tags=extras['staging_tags'], action_frame=frame,
        composition_mode=inputs['composition_mode'],
    )
    emitted = layers['garnish']
    subject = renderer.strip_person_demographic_descriptors(
        renderer.normalize_subject_to_girl(context['subj']))
    solo_dropped = []
    if renderer._is_solo_prompt_context(subject, layers['staging_tags']):
        emitted, _, solo_dropped = renderer._compact_solo_support_tags(emitted, layers['staging_tags'])
    if emitted != current:
        return None
    emitted_tags = renderer.split_semantic_tags(emitted)
    # Filtering may omit a selected tag; it cannot invent or rewrite a source part.
    if any(tag not in tags for tag in emitted_tags) or ', '.join(emitted_tags) != current:
        return None
    policies = (
        ('legacy.garnish.exact_redundancy', layers['debug']['exact_redundancy_dropped']),
        ('legacy.garnish.semantic_family_budget', layers['debug']['garnish_dropped_tags']),
        ('legacy.garnish.solo_support_budget', solo_dropped),
    )
    omitted = []
    for index, tag in enumerate(tags):
        if tag in emitted_tags:
            continue
        rule = next((rule for rule, dropped in policies if tag in dropped), None)
        if rule is None:
            return None
        omitted.append((f'garnish:{index}', rule))
    return tuple(emitted_tags), tuple(omitted)


def adapt_garnish_component(inputs, *, input_binding_sha256, source_identity_sha256):
    """Bind latest raw tags, then prove any omissions through existing Builder policy."""
    from .v2_direct_provenance import _GARNISH
    from .v2_leaf_grammar import gaze

    context = inputs.get('context')
    extras = context.get('extras') if isinstance(context, Mapping) else None
    raw = extras.get('garnish') if isinstance(extras, Mapping) else None
    current = inputs.get('garnish', raw)
    if not isinstance(raw, str) or not isinstance(current, str):
        return _unbound(inputs, 'garnish', raw)
    history = context.get('history')
    if not isinstance(history, (tuple, list)):
        return _unbound(inputs, 'garnish', raw)
    latest = next((entry for entry in reversed(history)
                   if isinstance(entry, Mapping) and entry.get('node') == 'ContextGarnish'), None)
    decision = latest.get('decision') if latest else None
    tags = decision.get('final_tags') if isinstance(decision, Mapping) else None
    if (not isinstance(tags, (tuple, list)) or any(not isinstance(tag, str) or not tag for tag in tags)
            or len(set(tags)) != len(tags) or ', '.join(tags) != raw):
        return _unbound(inputs, 'garnish', raw)
    emitted_tags, omitted = tags, None
    if current != raw:
        reconstruction = _reconstruct_garnish_policy(inputs, context, raw, current, tags)
        if reconstruction is None:
            return _unbound(inputs, 'garnish', raw)
        emitted_tags, omitted = reconstruction
    fields = []
    atoms = []
    for index, tag in enumerate(tags):
        part_id = f'garnish:{index}'
        fields.append((part_id, 'ContextGarnish', f'decision.final_tags[{index}]', None, tag))
        if tag not in emitted_tags:
            continue
        is_gaze = gaze(tag)
        known = tag in _GARNISH or is_gaze
        subject = 'protagonist' if is_gaze else {
            'brows knit in concentration': 'body:brows', 'steady gaze': 'body:gaze',
            'still posture': 'body:posture', 'hands kept precise and controlled': 'body:hands',
        }.get(tag)
        atoms.append(_atom('garnish', tag, (part_id,), known=known, subject=subject,
                           owner='protagonist', form='gerund' if is_gaze else 'with_attachment',
                           attachment=('shared_modifier' if is_gaze else 'with_nominal'
                                       if tag in {'steady gaze', 'still posture'} else 'with_absolute'),
                           same_subject=Truth.TRUE if is_gaze else Truth.FALSE,
                           rule_ids=('legacy.garnish.gaze' if is_gaze else 'legacy.garnish.with_attachment',)))
    result = _bound('garnish', raw, fields, atoms, input_binding_sha256=input_binding_sha256,
                    source_identity_sha256=source_identity_sha256)
    if omitted is not None:
        result = replace(result, trace=replace(result.trace,
            emitted_output_sha256=text_sha256(current),
            emitted_part_ids=tuple(atom.source_part_ids[0] for atom in atoms), omitted_parts=omitted,
            constructor_id='r43.garnish.received_policy/v1'))
    return result


def adapt_mood_component(inputs, *, input_binding_sha256, source_identity_sha256):
    """Bind the recorded mood key to its existing descriptions, without seed replay."""
    from .v2_direct_provenance import _MOODS

    context, raw = _received(inputs, 'mood', 'meta', 'mood')
    if raw is None:
        meta = context.get('meta') if context else None
        return _unbound(inputs, 'mood', meta.get('mood') if isinstance(meta, Mapping) else None)
    extras = context.get('extras')
    key = extras.get('raw_mood_key') if isinstance(extras, Mapping) else None
    if not isinstance(key, str) or not key.strip():
        return _unbound(inputs, 'mood', raw)
    key = key.lower().strip()
    source = _MOOD_MAP.get(key)
    descriptions = source.get('description') if isinstance(source, Mapping) else None
    if not isinstance(descriptions, list) or raw not in descriptions:
        return _unbound(inputs, 'mood', raw)
    fields = (('mood:description', 'ContextMoodExpander', 'description', key, raw),)
    atom = _atom('mood', raw, ('mood:description',), known=raw in _MOODS,
                 subject='mood:0', owner='scene:0', form='with_absolute',
                 attachment='with_absolute', same_subject=Truth.FALSE,
                 rule_ids=('legacy.mood.with_absolute',))
    return _bound('mood', raw, fields, (atom,), input_binding_sha256=input_binding_sha256,
                  source_identity_sha256=source_identity_sha256)
