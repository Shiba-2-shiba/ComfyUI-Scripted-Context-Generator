"""Reconstruct a bounded garment producer before proving its nominal grammar.

These runtime-only proofs cover one garment and its attached clothing details.
Membership proves field ownership, never grammaticality. Ambiguous pack/field
reconstructions and unproved states fail closed.
"""
import re
import json
from collections.abc import Mapping

from .clothing_candidate_renderer import _GARMENT_MATERIAL
from .v2_leaf_grammar import _choice, clothing_vocab


_PREFIX_FIELDS = ('colors', 'patterns', 'materials', 'styles')
_DETAIL_FIELDS = ('embellishments', 'optional_details', 'states')
_ADJECTIVES = frozenset({'cozy', 'warm', 'soft', 'ribbed', 'fuzzy'})
_HEAD_COMPOUNDS = {
    'dress': {('sweater',), ('turtleneck', 'sweater')},
    'texture': {(), ('knit',)}, 'belt': {(), ('knit',)},
    'scarf': {(), ('knit',)}, 'warmers': {('leg',)},
    'silhouette': {('knit',)},
}
_HEADS = {
    'garment': {'dress'}, 'embellishments': {'texture', 'belt'},
    'optional_details': {'scarf', 'warmers'}, 'styles': {'silhouette'},
}


def _noun(value, role):
    """Consume adjective* compound* head, with explicit plural-head ownership."""
    if not isinstance(value, str) or not re.fullmatch(r'[a-z]+(?: [a-z]+)*', value):
        return None
    words = value.split()
    head = words[-1]
    if head not in _HEADS.get(role, set()):
        return None
    index = 0
    while index < len(words) - 1 and words[index] in _ADJECTIVES:
        index += 1
    if tuple(words[index:-1]) not in _HEAD_COMPOUNDS[head]:
        return None
    return value if head == 'warmers' else ('an ' if value[0] in 'aeiou' else 'a ') + value


def _prefix_grammar(value, field):
    if not value:
        return True
    if field == 'colors':
        return bool(re.fullmatch(
            r'(?:(?:charcoal|soft|dark|dusty|moss|emerald) )?'
            r'(?:grey|gray|rose|cream|beige|black|white|silver|blue|green|purple|pink|red|brown|gold)',
            value))
    if field == 'patterns':
        return value in {'fair isle', 'solid', 'cable-knit'}
    if field == 'materials':
        return value in {'wool', 'cashmere', 'fleece'}
    return value in {'long-sleeve', 'knee-length'} or _noun(value, 'styles') is not None


def _prefix_paths(value, palette, fields=_PREFIX_FIELDS):
    """One optional selection per producer field, in emitted order."""
    if not fields:
        return [()] if not value else []
    paths = [(None, *tail) for tail in _prefix_paths(value, palette, fields[1:])]
    for item in set(palette.get(fields[0], [])):
        if not isinstance(item, str) or not item:
            continue
        if value == item or value.startswith(item + ' '):
            rest = value[len(item):].removeprefix(' ')
            paths.extend((item, *tail) for tail in _prefix_paths(rest, palette, fields[1:]))
    return paths


def _detail_paths(details, pack, fields=_DETAIL_FIELDS):
    if not fields:
        return [()] if not details else []
    paths = _detail_paths(details, pack, fields[1:])
    field = fields[0]
    source = pack.get('palette', {}) if field == 'embellishments' else pack
    if details and details[0] in source.get(field, []):
        paths += [((field, details[0]), *tail)
                  for tail in _detail_paths(details[1:], pack, fields[1:])]
    return paths


def _coordinate(values):
    if len(values) < 2:
        return ''.join(values)
    return ', '.join(values[:-1]) + ' and ' + values[-1]


def materialize_clothes(value, *, character_palette=()):
    """Return a garment NP with owned attachments, or None for unproved input.

    character_palette must come from the selected character's existing palette;
    it permits the producer's color override, subject to independent color grammar.
    No palette is inferred from arbitrary words in the clothing string.
    """
    if (not isinstance(value, str) or not value or value != value.strip()
            or re.search(r'[;.!?{}\n\r]', value)
            or not isinstance(character_palette, (tuple, list))
            or any(not isinstance(color, str) for color in character_palette)):
        return None
    main, separator, tail = value.partition(', with ')
    details = tail.split(', ') if separator else []
    if ',' in main or (separator and not tail) or len(details) > 3 or len(set(details)) != len(details):
        return None
    proofs = []
    for groups in clothing_vocab.CONCEPT_PACKS.values():
        for pack in groups.values():
            choices = list(pack.get('choices', {}).values())
            # Multiple garments need an additional proof of detail attachment.
            if len(choices) != 1:
                continue
            for option in choices[0]:
                garment = _choice(option)
                if not garment or not (main == garment or main.endswith(' ' + garment)):
                    continue
                prefix = main[:-len(garment)].removesuffix(' ')
                palette = dict(pack.get('palette', {}))
                palette['colors'] = list(palette.get('colors', [])) + list(character_palette)
                if _GARMENT_MATERIAL.search(garment):
                    palette['materials'] = []
                prefix_paths = _prefix_paths(prefix, palette)
                detail_paths = _detail_paths(details, pack)
                # Reject source ambiguity before using grammar to filter it.
                if len(prefix_paths) != 1 or len(detail_paths) != 1:
                    if prefix_paths and detail_paths:
                        return None
                    continue
                proofs.append((garment, prefix_paths[0], detail_paths[0]))
    if len(proofs) != 1:
        return None
    return _materialize_single_garment(*proofs[0])


def _materialize_single_garment(garment, prefixes, details):
    """Shared existing nominal/ownership rules; no new source search or grammar."""
    if (_noun(garment, 'garment') is None
            or any(not _prefix_grammar(word, field) for word, field in zip(prefixes, _PREFIX_FIELDS))):
        return None
    attached = []
    prenominal = []
    for word, field in zip(prefixes, _PREFIX_FIELDS):
        if not word:
            continue
        style_np = _noun(word, 'styles') if field == 'styles' else None
        if style_np:
            attached.append(style_np)
        else:
            prenominal.append(word)
    for field, detail in details:
        rendered = _noun(detail, field)
        if rendered is None:
            return None
        attached.append(rendered)
    noun = ' '.join((*prenominal, garment))
    noun = ('an ' if noun[0] in 'aeiou' else 'a ') + noun
    return noun + (' with ' + _coordinate(attached) if attached else '')


def adapt_clothing_component(context, current_clothing=None, *, input_binding_sha256, source_identity_sha256):
    """Bind one selected garment from received history, never replay guessed settings.

    History removes the prompt and retains normalized variants. A variant alone
    is not reversible: exact current text must uniquely match the selected pack's
    parts, the shared producer assembly/signature, and existing nominal grammar.
    """
    from .clothing_candidate_renderer import _assemble_item_description
    from .clothing_candidate_selector import CLOTHING_CANDIDATE_ATTEMPTS
    from .realization_evidence import (
        ClauseEvidence, EvidenceComponent, ProducerPart, ProducerTrace, SourceRef, Truth, text_sha256,
    )
    if __package__ and '.' in __package__:
        from ..clothing_service import resolve_clothing_theme
        from ..core.semantic_policy import sanitize_text
        from ..history_service import clothing_signature_digest, clothing_signature_from_decision
    else:
        from clothing_service import resolve_clothing_theme
        from core.semantic_policy import sanitize_text
        from history_service import clothing_signature_digest, clothing_signature_from_decision

    def unavailable(blocker):
        return EvidenceComponent('clothing', None, (), False, (blocker,))

    if not isinstance(context, Mapping) or not isinstance(context.get('extras'), Mapping):
        return unavailable('transport.runtime_inputs_missing')
    extras, history = context['extras'], context.get('history')
    value = extras.get('clothing_prompt')
    if current_clothing is not None and current_clothing != value:
        return unavailable('binding.current_text_mismatch')
    if not isinstance(value, str) or not value or value != value.strip() or re.search(r'[;.!?{}\n\r]', value):
        return unavailable('binding.current_text_mismatch')
    if not isinstance(history, (list, tuple)):
        return unavailable('binding.history_missing')
    entry = next((item for item in reversed(history) if isinstance(item, Mapping)
                  and item.get('node') == 'ContextClothingExpander'), None)
    if entry is None:
        return unavailable('binding.history_missing')
    decision = entry.get('decision')
    required = ('theme', 'chosen_type', 'base_pack', 'base_variant', 'outerwear_pack', 'outerwear_variant', 'signature')
    if (not isinstance(decision, Mapping) or any(not isinstance(decision.get(key), str) for key in required)
            or type(entry.get('seed')) is not int or type(decision.get('attempt_index')) is not int
            or not 0 <= decision['attempt_index'] < CLOTHING_CANDIDATE_ATTEMPTS):
        return unavailable('binding.history_stale')
    if decision['signature'] != clothing_signature_digest(clothing_signature_from_decision(decision)):
        return unavailable('binding.history_stale')
    theme = context.get('costume')
    raw_theme = extras.get('raw_costume_key', theme)
    if not isinstance(theme, str) or not isinstance(raw_theme, str):
        return unavailable('binding.history_stale')
    requested = resolve_clothing_theme(theme) or theme
    if (resolve_clothing_theme(raw_theme) or raw_theme) != requested:
        return unavailable('binding.history_stale')
    if decision['theme'] != requested:
        fallback = decision.get('contextual_theme_fallback')
        if (decision.get('requested_theme') != requested or not isinstance(fallback, str)
                or (resolve_clothing_theme(fallback) or fallback) != decision['theme']):
            return unavailable('binding.history_stale')
    if decision['outerwear_pack'] or decision['outerwear_variant']:
        return unavailable('clothing.outerwear_attachment_unknown')
    chosen_type, pack_key = decision['chosen_type'], decision['base_pack']
    theme_packs = clothing_vocab.THEME_TO_PACKS.get(decision['theme'], {})
    if chosen_type not in ('dresses', 'separates') or pack_key not in theme_packs.get(chosen_type, ()):
        return unavailable('binding.history_stale')
    pack = clothing_vocab.CONCEPT_PACKS.get(chosen_type, {}).get(pack_key)
    if not isinstance(pack, Mapping) or not isinstance(pack.get('choices'), Mapping):
        return unavailable('binding.history_stale')
    if len(pack['choices']) != 1:
        return unavailable('clothing.multigarment_owner_unknown')
    palette_text = extras.get('character_palette_str', '')
    palette_values = extras.get('color_palette', [])
    if (not isinstance(palette_text, str) or not isinstance(palette_values, (list, tuple))
            or any(not isinstance(item, str) for item in palette_values)):
        return unavailable('transport.runtime_inputs_missing')
    character_palette = [item.strip() for item in palette_text.split(',') if item.strip()] if palette_text else list(palette_values)
    main, separator, tail = value.partition(', with ')
    details = tail.split(', ') if separator else []
    if ',' in main or (separator and not tail) or len(details) > 3 or len(set(details)) != len(details):
        return unavailable('clothing.owner_unknown')
    field, options = next(iter(pack['choices'].items()))
    matches = []
    for option in options:
        garment = _choice(option)
        if not garment or not (main == garment or main.endswith(' ' + garment)):
            continue
        prefix = main[:-len(garment)].removesuffix(' ')
        source_palette = pack.get('palette', {})
        palette = dict(source_palette)
        palette['colors'] = list(source_palette.get('colors', [])) + character_palette
        if _GARMENT_MATERIAL.search(garment):
            palette['materials'] = []
        prefix_paths, detail_paths = _prefix_paths(prefix, palette), _detail_paths(details, pack)
        # Do not filter away source ambiguity by selecting a grammatically easy path.
        if len(prefix_paths) != 1 or len(detail_paths) != 1:
            if prefix_paths and detail_paths:
                return unavailable('binding.source_ambiguity')
            continue
        prefixes, selected_details = prefix_paths[0], detail_paths[0]
        color, pattern, material, style = (item or '' for item in prefixes)
        if color and color in source_palette.get('colors', []) and color in character_palette:
            return unavailable('binding.source_ambiguity')
        assembled, variant = _assemble_item_description([garment], color=color, material=material,
            pattern=pattern, style=style, details_list=[text for _, text in selected_details])
        if sanitize_text(assembled) != value or variant != decision['base_variant']:
            continue
        source_text = option if isinstance(option, str) else json.dumps(option, ensure_ascii=False, separators=(',', ':'))
        candidate = (source_text, garment, prefixes, selected_details, assembled)
        if candidate not in matches:
            matches.append(candidate)
    if len(matches) != 1:
        return unavailable('binding.source_ambiguity' if matches else 'binding.current_text_mismatch')
    source_text, garment, prefixes, selected_details, assembled = matches[0]
    if _materialize_single_garment(garment, prefixes, selected_details) is None:
        return unavailable('clothing.nominal_grammar_unknown')
    producer, catalog = 'pipeline.clothing_candidate_renderer', chosen_type + ':' + pack_key
    part = ProducerPart('clothing:garment', SourceRef('clothing', producer, 'choices.' + field,
                       catalog, text_sha256(source_text)), garment)
    selected, emitted = [part], []
    for word, palette_field in zip(prefixes, _PREFIX_FIELDS):
        if word:
            override = palette_field == 'colors' and word in character_palette
            item = ProducerPart('clothing:' + palette_field, SourceRef('clothing', producer,
                'character_palette.colors' if override else 'palette.' + palette_field,
                None if override else catalog, text_sha256(word)), word)
            selected.append(item)
            emitted.append(item.part_id)
    emitted.append(part.part_id)
    for index, (detail_field, detail_text) in enumerate(selected_details):
        item = ProducerPart('clothing:detail:' + str(index), SourceRef('clothing', producer,
            'palette.embellishments' if detail_field == 'embellishments' else detail_field,
            catalog, text_sha256(detail_text)), detail_text)
        selected.append(item)
        emitted.append(item.part_id)
    trace = ProducerTrace('bound_constructor', producer, source_identity_sha256, input_binding_sha256,
        text_sha256(assembled), text_sha256(value), tuple(selected), tuple(emitted), None,
        'clothing.selected_pack_single_garment/v1')
    atom = ClauseEvidence('clothing:owned_np', tuple(emitted), value, Truth.TRUE, None, 'protagonist',
        'noun_phrase', 'owned_clothing', Truth.UNKNOWN, (), None,
        ('v2_clothing_provenance.single_garment_nominal/v1',), None)
    return EvidenceComponent('clothing', trace, (atom,), True, (),
        (('nominal_grammar_known', Truth.TRUE), ('single_garment_owner', Truth.TRUE), ('garment_number_singular', Truth.TRUE)))
