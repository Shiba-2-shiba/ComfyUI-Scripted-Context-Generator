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


# These lexical categories prove grammar independently of catalog membership.
# Compounds are noun-owned; e.g. "viewing room" cannot modify "gallery".
_SCENE_HEADS = {
    'environment': {'interior', 'gallery'}, 'core': {'works', 'plaques'},
    'texture': {'detailing'}, 'details': {'perspective'},
    'time': {'performance'}, 'fx': {'atmosphere'},
    'event': {'viewing'}, 'surface': {'wall'}, 'reference': {'work'},
}
_NOUN_PARTS = {
    'interior': ({'grand', 'historic', 'small'}, ('opera', 'house')),
    'gallery': ({'small', 'contemporary', 'historic', 'grand'}, ()),
    'works': ({'framed', 'small'}, ('canvas',)),
    'plaques': ({'small'}, ('title',)),
    'detailing': (set(), ('gold', 'leaf')),
    'perspective': ({'atmospheric'}, ()),
    'performance': ({'quiet'}, ('evening',)),
    'atmosphere': ({'hushed', 'quiet'}, ('viewing', 'room')),
    'viewing': ({'quiet'}, ('weekday',)),
    'wall': (set(), ()), 'work': (set(), ()),
}
_ATTACHMENTS = {
    'gallery': ('arranged for ', 'event'),
    'works': ('spaced along ', 'surface'),
    'plaques': ('mounted beside ', 'reference'),
}


def _scene_nominal(value, field):
    """Return rendered nominal, head, and any required sibling antecedent."""
    base, *attachment = re.split(r' (?=arranged |spaced |mounted )', value)
    if len(attachment) > 1 or not re.fullmatch(r'[a-z]+(?: [a-z]+)*', base):
        return None
    words = base.split()
    head = words[-1]
    if head not in _SCENE_HEADS.get(field, ()):
        return None
    adjectives, compound = _NOUN_PARTS[head]
    modifiers = words[:-1]
    if compound and tuple(modifiers[-len(compound):]) == compound:
        modifiers = modifiers[:-len(compound)]
    if len(modifiers) != len(set(modifiers)) or any(word not in adjectives for word in modifiers):
        return None
    determiner = {'surface': 'the ', 'reference': 'each '}.get(field)
    if determiner is None:
        determiner = '' if head in {'works', 'plaques', 'detailing', 'perspective'} else (
            'an ' if base[0] in 'aeiou' else 'a ')
    rendered, reference = determiner + base, None
    if attachment:
        prefix, target_field = _ATTACHMENTS.get(head, ('', ''))
        if not prefix or not attachment[0].startswith(prefix):
            return None
        tail = attachment[0][len(prefix):]
        # The source already owns this determiner. Re-render to prove agreement
        # exactly, without dropping or changing any attached source words.
        article, separator, nominal = tail.partition(' ')
        if not separator or article not in {'a', 'an', 'the', 'each'}:
            return None
        parsed = _scene_nominal(nominal, target_field)
        if parsed is None or parsed[0] != tail:
            return None
        rendered += ' ' + prefix + tail
        if target_field == 'reference':
            reference = 'works'
    return rendered, head, reference


def _nominal(value, field):
    structured = _scene_nominal(value, field)
    if structured is not None:
        return structured[0]
    # Nested with-phrases belong to this noun, not to the protagonist or action.
    base, separator, complement = value.partition(' with ')
    if not re.fullmatch(r'[a-z]+(?:-[a-z]+)*(?: [a-z]+(?:-[a-z]+)*)*', base):
        return None
    words = base.split()
    if words[-1] not in _HEADS.get(field, ()):
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
                                                   ('details', defaults.get('details', ())),
                                                   ('fx', pack.get('fx', ()))) if segment in source]
            if len(fields) != 1:
                return None
            field, raw = fields[0], [segment]
            source = defaults.get(field, ()) if field == 'details' else pack.get(field, ())
            prefix = 'with '
        if field in seen or len(raw) != len(set(raw)) or any(value not in source for value in raw):
            return None
        nouns = [_nominal(value, field) for value in raw]
        if any(noun is None for noun in nouns):
            return None
        if field == 'core':
            structures = [_scene_nominal(value, field) for value in raw]
            heads = {parsed[1] for parsed in structures if parsed is not None}
            if any(parsed is not None and parsed[2] is not None and parsed[2] not in heads
                   for parsed in structures):
                return None
        seen.add(field)
        modifiers.append(prefix + ' and '.join(nouns))
    return 'in ' + parsed_anchor, tuple(modifiers)


def producer_owned_scene(location, location_key):
    """Attach every scene predicate to the head before an outer finite owner.

    A flat ', featuring ...' following 'the room stays in a gallery' could
    describe the room. Start the relative clause immediately after gallery,
    before its event complement introduces another possible antecedent.
    """
    parts = producer_scene_parts(location, location_key)
    if parts is None:
        return None
    raw_anchor = location.split(', ', 1)[0]
    structured = _scene_nominal(raw_anchor, 'environment')
    if structured is None:
        return None
    anchor, _, _ = structured
    base, separator, event = anchor.partition(' arranged for ')
    predicates = ['is arranged for ' + event] if separator else []
    for modifier in parts[1]:
        if modifier.startswith('featuring '):
            predicates.append('features ' + modifier[len('featuring '):])
        elif modifier.startswith('with '):
            predicates.append('has ' + modifier[len('with '):])
        else:
            return None  # Temporal/adorned scope needs its own constructor proof.
    return 'in ' + base + (' that ' + ' and that '.join(predicates) if predicates else '')
