"""Reconstruct producer-owned scene fields and validate their nominal grammar."""
import re

try:
    from ..location_service import load_background_packs
    from ..vocab.loader import load_json
except ImportError:
    from location_service import load_background_packs
    from vocab.loader import load_json


_HEADS = {
    'environment': {'bedroom', 'boudoir'},
    'core': {'bed', 'mirror', 'wardrobe', 'cushions'},
    'texture': {'sheets', 'rug'},
    'details': {'depth'},
    'time': {'morning', 'night'},
    'complement': {'lights', 'doors'},
}
_MODIFIERS = {'cozy', 'romantic', 'gothic', 'victorian', 'vintage', 'canopied',
              'four-poster', 'wooden', 'open', 'scattered', 'soft', 'smooth',
              'fluffy', 'thick', 'layered', 'lazy', 'quiet'}
_COMPOUNDS = {'vanity', 'silk', 'background'}
_PLURAL_OR_MASS = {'cushions', 'sheets', 'lights', 'doors', 'depth'}


def _nominal(value, field):
    # Nested with-phrases belong to this noun, not to the protagonist or action.
    base, separator, complement = value.partition(' with ')
    if not re.fullmatch(r'[a-z]+(?:-[a-z]+)*(?: [a-z]+(?:-[a-z]+)*)*', base):
        return None
    words = base.split()
    if words[-1] not in _HEADS[field]:
        return None
    compound = False
    for word in words[:-1]:
        if word in _COMPOUNDS:
            compound = True
        elif word not in _MODIFIERS or compound:
            return None
    if separator:
        if field != 'core' or words[-1] not in {'mirror', 'wardrobe'}:
            return None
        tail = _nominal(complement, 'complement')
        if tail is None:
            return None
    else:
        tail = None
    rendered = base if words[-1] in _PLURAL_OR_MASS else ('an ' if base[0] in 'aeiou' else 'a ') + base
    return rendered + (' with ' + tail if tail else '')


def producer_scene_parts(location, location_key):
    """Return concrete constituents only after exact field/topology binding.

    The producer selects one environment and at most one segment per section,
    shuffles sections, then deduplicates. We preserve that selected order. Raw
    field membership supplies provenance; a separate closed grammar supplies
    noun/attachment proof. Unsupported weather, people and clauses stay unknown.
    """
    if not isinstance(location, str) or not isinstance(location_key, str):
        return None
    pack = load_background_packs().get(location_key, {})
    anchor, *segments = location.split(', ')
    if anchor not in pack.get('environment', ()):
        return None
    parsed_anchor = _nominal(anchor, 'environment')
    if parsed_anchor is None:
        return None
    defaults = load_json('background_defaults.json')
    seen, modifiers = set(), []
    for segment in segments:
        prefix = next((word for word in ('featuring ', 'adorned with ', 'with ', 'during ')
                       if segment.startswith(word)), '')
        if prefix:
            field = {'featuring ': 'core', 'with ': 'props', 'adorned with ': 'props', 'during ': 'time'}[prefix]
            source = pack.get(field, ())
            raw = segment[len(prefix):].split(' and ')
            if field not in _HEADS or not 1 <= len(raw) <= (1 if field == 'time' else 2):
                return None
        else:
            fields = [field for field, source in (('texture', pack.get('texture', ())),
                                                   ('details', defaults.get('details', ()))) if segment in source]
            if len(fields) != 1:
                return None
            field, raw = fields[0], [segment]
            source = pack.get(field, ()) if field == 'texture' else defaults.get(field, ())
            prefix = 'with '
        if field in seen or len(raw) != len(set(raw)) or any(value not in source for value in raw):
            return None
        nouns = [_nominal(value, field) for value in raw]
        if any(noun is None for noun in nouns):
            return None
        seen.add(field)
        modifiers.append(prefix + ' and '.join(nouns))
    return 'in ' + parsed_anchor, tuple(modifiers)
