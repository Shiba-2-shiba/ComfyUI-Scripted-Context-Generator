"""Finite productive grammar; source membership alone never proves syntax.

All constructors consume their input. Artifact and place heads are deliberately
disjoint: new action spatial arguments cannot silently repeat a scene anchor.
"""
from dataclasses import dataclass
import re

try:
    from ..vocab import clothing as clothing_vocab
except ImportError:
    from vocab import clothing as clothing_vocab


_HEADS = {
    'artifact': {'bolt', 'nut', 'hood', 'machine', 'lift', 'cabinet', 'board', 'clipboard', 'crate'},
    'place': {'garage', 'workshop', 'road', 'street', 'shop', 'bay', 'station'},
    'event': {'inspection', 'errand', 'shift', 'task'},
    'abstract': {'detail', 'pause', 'thing'},
    'garment': {'top', 'skirt', 'trousers', 'blouse', 'shirt'},
}
_ADJECTIVES = {
    'open', 'next', 'quiet', 'small', 'local', 'narrow', 'paved', 'marked', 'rolling',
    'modern', 'commercial', 'nostalgic', 'rural', 'hydraulic', 'late-afternoon',
    'early', 'steady', 'beige', 'ivory', 'charcoal', 'navy', 'blue', 'belted', 'fitted',
    'high-waist', 'long-sleeve', 'tucked-in', 'pressed', 'tailored', 'solid', 'pinstripe',
    'knee-length', 'structured',
}
_COMPOUNDS = {
    'vehicle', 'repair', 'maintenance', 'countryside', 'village', 'town', 'vegetable',
    'service', 'tool', 'vending', 'knit', 'pencil', 'silk', 'cotton', 'wool',
    'button-down',
}
_DETERMINERS = {'a', 'an', 'the', 'one'}
_PLACE_PREPOSITIONS = {'road': 'on', 'street': 'on', 'garage': 'in', 'workshop': 'in',
                       'shop': 'in', 'bay': 'in', 'station': 'in'}
_SPATIAL = {'beneath', 'beside', 'near', 'by', 'under'}
_TRANSITIVE = {
    'tightening': {'bolt', 'nut'}, 'adjusting': {'bolt', 'nut', 'hood'},
    'holding': {'bolt', 'nut', 'hood', 'clipboard'},
    'checking': {'bolt', 'nut', 'hood', 'machine', 'detail'},
    'measuring': {'pause', 'detail'},
}


@dataclass(frozen=True)
class Nominal:
    text: str
    head: str
    kind: str
    determined: bool

    def with_article(self):
        if self.determined or self.head == 'trousers':
            return self.text
        return ('an ' if self.text[0] in 'aeiou' else 'a ') + self.text


def nominal(value, kinds, *, determined=False):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z]+(?:-[a-z]+)*(?: [a-z]+(?:-[a-z]+)*)*', value):
        return None
    words = value.split()
    has_determiner = words[0] in _DETERMINERS
    determiner = words[0] if has_determiner else ''
    if has_determiner:
        words = words[1:]
    if not words or (determined and not has_determiner):
        return None
    head = words[-1]
    kind = next((kind for kind in kinds if head in _HEADS.get(kind, set())), None)
    if kind is None or (head == 'trousers' and determiner in {'a', 'an', 'one'}):
        return None
    # Every accepted word has a known initial sound in this finite lexicon.
    # A larger lexicon with silent-h/u exceptions needs explicit sound metadata.
    if determiner in {'a', 'an'} and determiner != ('an' if words[0][0] in 'aeiou' else 'a'):
        return None
    compounds_started = False
    for word in words[:-1]:
        if word in _COMPOUNDS:
            compounds_started = True
        elif word not in _ADJECTIVES or compounds_started:
            return None
    return Nominal(value, head, kind, has_determiner)


def _spatial(value):
    preposition, separator, obj = value.partition(' ')
    return bool(separator and preposition in _SPATIAL and nominal(obj, {'artifact'}, determined=True))


def place_phrase(value):
    parsed = nominal(value, {'place'})
    preposition = _PLACE_PREPOSITIONS.get(parsed.head) if parsed else None
    return preposition + ' ' + parsed.with_article() if preposition else None


def _object(value, heads):
    parsed = nominal(value, {'artifact', 'abstract'}, determined=True)
    return bool(parsed and parsed.head in heads)


def gaze(value):
    words = value.split()
    if words[:1] != ['looking']:
        return False
    rest = words[1:]
    if rest[:1] == ['directly']:
        rest = rest[1:]
    if rest in (['ahead'], ['away']):
        return True
    if rest[:1] not in (['toward'], ['at']):
        return False
    obj = ' '.join(rest[1:])
    for finite in ('needs', 'checks'):
        suffix = ' she ' + finite
        if obj.endswith(suffix):
            parsed = nominal(obj[:-len(suffix)], {'abstract'}, determined=True)
            return bool(parsed and parsed.head == 'thing')
    return bool(nominal(obj, {'artifact'}, determined=True))


def predicate(value):
    """Known valencies plus fully consumed nominal/spatial complements."""
    verb, separator, tail = value.partition(' ')
    if not separator:
        return False
    if gaze(value):
        return True
    if verb in {'standing', 'waiting'}:
        return _spatial(tail)
    if verb in {'holding', 'keeping'} and re.fullmatch(r'herself (?:steady|still)(?: while she (?:works|waits))?', tail):
        return True
    if verb == 'keeping' and tail == 'to herself':
        return True
    if verb == 'pausing':
        match = re.fullmatch(r'to (?:reassess|inspect|check) (.+)', tail)
        return bool(match and nominal(match[1], {'artifact', 'abstract'}, determined=True))
    heads = _TRANSITIVE.get(verb)
    if heads is None:
        return False
    if _object(tail, heads):
        return True
    if verb == 'measuring' and tail.endswith(' instead of rushing it'):
        return _object(tail[:-len(' instead of rushing it')], heads)
    for preposition in _SPATIAL:
        obj, sep, anchor = tail.partition(' ' + preposition + ' ')
        if sep:
            return _object(obj, heads) and bool(nominal(anchor, {'artifact'}, determined=True))
    return False


def temporal(value):
    connector, separator, event = value.partition(' ')
    return bool(separator and connector in {'before', 'after', 'during'}
                and nominal(event, {'event'}, determined=True))


def _background_field(value):
    return next((field for prefix, field in (('during ', 'time'), ('featuring ', 'core'),
                                             ('with ', 'props'), ('adorned with ', 'props'))
                 if value.startswith(prefix)), None)


def background_modifiers(values, pack):
    """The producer emits at most one segment per field, then shuffles them."""
    fields = [_background_field(value) for value in values]
    if None in fields or len(set(fields)) != len(fields) or len(set(values)) != len(values):
        return None
    result = tuple(_background_modifier(value, pack) for value in values)
    return result if all(value is not None for value in result) else None


def _background_modifier(value, pack):
    """Bind connector to the exact producer field before parsing its nouns."""
    if value.startswith('during '):
        raw = value[7:]
        parsed = nominal(raw, {'event'})
        return 'during ' + parsed.with_article() if raw in pack.get('time', []) and parsed else None
    prefix = next((p for p in ('featuring ', 'with ', 'adorned with ') if value.startswith(p)), None)
    if prefix is None:
        return None
    field = _background_field(value)
    raw = value[len(prefix):].split(' and ')
    if not 1 <= len(raw) <= 2 or len(set(raw)) != len(raw):
        return None
    nouns = [nominal(part, {'artifact', 'place'}) for part in raw]
    if any(part not in pack.get(field, []) for part in raw) or any(item is None for item in nouns):
        return None
    return prefix + ' and '.join(item.with_article() for item in nouns)


def _choice(option):
    if isinstance(option, str):
        return option
    if isinstance(option, list) and option and all(isinstance(item, str) for item in option):
        return option[1] + ' ' + option[0] if len(option) > 1 else option[0]
    return ''


def _palette_prefix(value, palette, fields):
    if not fields:
        return value == ''
    if _palette_prefix(value, palette, fields[1:]):
        return True
    return any(value == item and _palette_prefix('', palette, fields[1:])
               or value.startswith(item + ' ') and _palette_prefix(value[len(item) + 1:], palette, fields[1:])
               for item in palette.get(fields[0], []) if isinstance(item, str) and item)


def simple_clothes(value):
    """Prove exact producer choices and optional-prefix order, then nominal form."""
    pieces = value.split(' and ')
    nouns = [nominal(piece, {'garment'}) for piece in pieces]
    if not pieces or any(item is None or item.determined for item in nouns):
        return None
    for packs in clothing_vocab.CONCEPT_PACKS.values():
        for pack in packs.values():
            choices = list(pack.get('choices', {}).values())
            if len(choices) != len(pieces):
                continue
            if any(piece not in {_choice(option) for option in options}
                   for piece, options in zip(pieces[1:], choices[1:])):
                continue
            for option in choices[0]:
                first = _choice(option)
                if not first or not (pieces[0] == first or pieces[0].endswith(' ' + first)):
                    continue
                prefix = pieces[0][:-len(first)].rstrip()
                selected = [first, *pieces[1:]]
                palette = dict(pack.get('palette', {}))
                materials = {material for groups in clothing_vocab.CONCEPT_PACKS.values()
                             for source in groups.values() for material in source.get('palette', {}).get('materials', [])}
                if any(re.search(r'\b' + re.escape(material) + r'\b', item)
                       for material in materials for item in selected):
                    palette['materials'] = []  # Same suppression as the producer.
                if _palette_prefix(prefix, palette, ('colors', 'patterns', 'materials', 'styles')):
                    return ' and '.join(item.with_article() for item in nouns)
    return None
