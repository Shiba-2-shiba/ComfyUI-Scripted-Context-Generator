"""Reconstruct a bounded garment producer before proving its nominal grammar.

These runtime-only proofs cover one garment and its attached clothing details.
Membership proves field ownership, never grammaticality. Ambiguous pack/field
reconstructions and unproved states fail closed.
"""
import re

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
    garment, prefixes, details = proofs[0]
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
