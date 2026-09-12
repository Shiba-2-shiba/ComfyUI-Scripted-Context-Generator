"""Reconstruct producer-owned scene fields and validate their nominal grammar."""
import re
from collections.abc import Mapping

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
    parsed = _producer_scene_components(location, location_key)
    return parsed[:2] if parsed is not None else None


def common_scene_parts(location, location_key):
    """Render exact source-bound Scene parts for the common evidence route."""
    parsed = _producer_scene_components(location, location_key, bind_sources=True)
    if parsed is None:
        parsed = _producer_scene_components(location, location_key, bind_sources=True, reviewed=True)
    return parsed[:2] if parsed is not None else None


def _producer_scene_components(location, location_key, *, bind_sources=False, reviewed=False):
    """Retain raw fields alongside unchanged nominal constructors for adapters."""
    if not isinstance(location, str) or not isinstance(location_key, str):
        return None
    pack = load_background_packs().get(location_key, {})
    anchor, *segments = location.split(', ')
    if anchor not in pack.get('environment', ()):
        return None
    if bind_sources:
        if __package__ and '.' in __package__:
            from ..core.semantic_policy import sanitize_text
        else:
            from core.semantic_policy import sanitize_text
        def matching_raw(value, source):
            return {raw for raw in source if isinstance(raw, str) and sanitize_text(raw) == value}
        if matching_raw(anchor, pack.get('environment', ())) != {anchor}:
            return None
        # A catalog environment containing commas must not be reinterpreted as
        # an easier environment plus separate selected segments.
        if any(sanitize_text(raw) != anchor and (location == sanitize_text(raw)
               or location.startswith(sanitize_text(raw) + ', '))
               for raw in pack.get('environment', ()) if isinstance(raw, str)):
            return None
    if reviewed:
        # The direct adapter imports this module; resolve its reviewed grammar
        # only while binding a common Scene, after module initialization.
        from .v2_direct_provenance import _ENVIRONMENTS, _article, _scene_modifier
        parsed_anchor = _article(anchor) if anchor in _ENVIRONMENTS.get(location_key, ()) else None
    else:
        parsed_anchor = _nominal(anchor, 'environment')
    if parsed_anchor is None:
        return None
    defaults = load_json('background_defaults.json')
    bare_sources = [('texture', pack.get('texture', ()), location_key),
                    ('details', defaults.get('details', ()), 'background_defaults'),
                    ('fx', pack.get('fx', ()), location_key)]
    if bind_sources:
        bare_sources += [('texture', defaults.get('texture', ()), 'background_defaults'),
                         ('fx', defaults.get('fx', ()), 'background_defaults'),
                         ('weather', pack.get('weather', ()), location_key),
                         ('crowd', pack.get('crowd', ()), location_key)]
    seen, modifiers = set(), []
    components = [('environment', anchor, location_key, _scene_nominal(anchor, 'environment'))]
    for segment in segments:
        reviewed_modifier = _scene_modifier(segment) if reviewed else None
        if reviewed and reviewed_modifier is None:
            return None
        prefix = next((word for word in ('featuring ', 'adorned with ', 'with ', 'during ')
                       if segment.startswith(word)), '')
        if prefix:
            field = {'featuring ': 'core', 'with ': 'props', 'adorned with ': 'props', 'during ': 'time'}[prefix]
            source = pack.get(field, ())
            raw = segment[len(prefix):].split(' and ')
            if (field not in _HEADS and not (reviewed and field == 'props')
                    or not 1 <= len(raw) <= (1 if field == 'time' else 2)):
                return None
            source_key = location_key
            if bind_sources:
                if any(matching_raw(segment, values) for _, values, _ in bare_sources):
                    return None
                if any(matching_raw(value, source) != {value} for value in raw):
                    return None
                if len(raw) > 1 and matching_raw(' and '.join(raw), source):
                    return None
        else:
            if bind_sources:
                origins = {(field, source_key, raw) for field, source, source_key in bare_sources
                           for raw in matching_raw(segment, source)}
                if len(origins) != 1 or next(iter(origins))[2] != segment:
                    return None
                fields = [(field, source_key) for field, source_key, _ in origins]
            else:
                fields = [(field, source_key) for field, source, source_key in bare_sources if segment in source]
            if len(fields) != 1:
                return None
            (field, source_key), raw = fields[0], [segment]
            source = defaults.get(field, ()) if source_key == 'background_defaults' else pack.get(field, ())
            prefix = 'with '
        if field in seen or len(raw) != len(set(raw)) or any(value not in source for value in raw):
            return None
        if not reviewed:
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
        modifiers.append(reviewed_modifier if reviewed else prefix + ' and '.join(nouns))
        components.extend((field, value, source_key, _scene_nominal(value, field)) for value in raw)
    return 'in ' + parsed_anchor, tuple(modifiers), tuple(components)


def adapt_scene_component(context, current_scene=None, frame_value=None, *, input_binding_sha256, source_identity_sha256):
    """Bind current Scene constituents; absent historical settings are not replayed."""
    from .realization_evidence import (
        ClauseEvidence, EvidenceComponent, ProducerPart, ProducerTrace, SourceRef, Truth, text_sha256,
    )
    from .location_builder import _assemble_location_prompt
    if __package__ and '.' in __package__:
        from ..location_service import resolve_location_key
    else:
        from location_service import resolve_location_key

    value = context.get('extras', {}).get('location_prompt') if isinstance(context, Mapping) and isinstance(context.get('extras'), Mapping) else None
    def unavailable(blocker):
        atoms = (ClauseEvidence('scene:unproved', (), value, Truth.UNKNOWN, None, None, 'unknown', 'unknown',
                 Truth.UNKNOWN, None, None, ()),) if isinstance(value, str) and value else ()
        return EvidenceComponent('scene', None, atoms, False, (blocker,))

    if (not isinstance(value, str) or not value or value != value.strip()
            or re.search(r'[;.!?{}\n\r]', value) or current_scene is not None and current_scene != value):
        return unavailable('binding.current_text_mismatch')
    extras, history = context['extras'], context.get('history')
    if not isinstance(history, (list, tuple)):
        return unavailable('binding.history_missing')
    entry = next((row for row in reversed(history) if isinstance(row, Mapping) and row.get('node') == 'ContextLocationExpander'), None)
    if entry is None:
        return unavailable('binding.history_missing')
    decision = entry.get('decision')
    if (not isinstance(decision, Mapping) or type(entry.get('seed')) is not int
            or not isinstance(decision.get('pack_key'), str)
            or decision.get('template_key') not in ('simple', 'detailed')
            or not isinstance(decision.get('selected_props'), (list, tuple))):
        return unavailable('binding.history_stale')
    key = decision['pack_key']
    for location in (context.get('loc'), extras.get('raw_loc_tag', context.get('loc'))):
        if not isinstance(location, str) or (resolve_location_key(location) or location) != key:
            return unavailable('binding.location_mismatch')
    frame_known = False
    for frame in (frame_value, extras.get('action_frame')):
        if frame is None:
            continue
        if not isinstance(frame, Mapping) or not isinstance(frame.get('legacy_slots', {}), Mapping):
            return unavailable('binding.frame_location_mismatch')
        frame_location = frame.get('legacy_slots', {}).get('location')
        if frame_location is not None:
            if not isinstance(frame_location, str) or (resolve_location_key(frame_location) or frame_location) != key:
                return unavailable('binding.frame_location_mismatch')
            frame_known = True
    parsed = _producer_scene_components(value, key, bind_sources=True)
    reviewed = parsed is None
    if reviewed:
        parsed = _producer_scene_components(value, key, bind_sources=True, reviewed=True)
    if parsed is None:
        return unavailable('scene.source_or_grammar_unknown')
    _, _, components = parsed
    if decision['template_key'] == 'simple' and len(components) != 1:
        return unavailable('binding.history_stale')
    selected = {}
    for field, raw, _, _ in components:
        selected.setdefault(field, []).append(raw)
    if list(decision['selected_props']) != selected.get('props', []):
        return unavailable('binding.history_stale')
    semantic = decision.get('semantic_epig', {})
    if not isinstance(semantic, Mapping) or not isinstance(semantic.get('location_scene', {}), Mapping):
        return unavailable('binding.history_stale')
    changes = semantic.get('location_scene', {}).get('section_changes', {})
    if not isinstance(changes, Mapping):
        return unavailable('binding.history_stale')
    for field, change in changes.items():
        if not isinstance(change, Mapping) or 'semantic' not in change:
            return unavailable('binding.history_stale')
        expected = selected.get(field)
        chosen = change['semantic']
        if expected is None:
            if chosen not in ('', []):
                return unavailable('binding.history_stale')
        elif chosen != (expected if field in ('core', 'props') else expected[0]):
            return unavailable('binding.history_stale')
    anchor, *segments = value.split(', ')
    raw_output, emitted = _assemble_location_prompt(anchor, segments)
    if emitted != value:
        return unavailable('binding.current_text_mismatch')
    parts, ids_by_head = [], {}
    for index, (field, raw, source_key, structured) in enumerate(components):
        part = ProducerPart(f'scene:{field}:{index}', SourceRef('scene', 'pipeline.location_builder',
            field, source_key, text_sha256(raw)), raw)
        parts.append(part)
        if structured:
            ids_by_head.setdefault(structured[1], []).append(part.part_id)
    atoms = []
    positions = {part.part_id: index for index, part in enumerate(parts)}
    for index, (part, (field, raw, _, structured)) in enumerate(zip(parts, components)):
        reference = structured[2] if structured else None
        antecedents = tuple(ids_by_head.get(reference, ())) if reference else ()
        if reference and (len(antecedents) != 1 or positions[antecedents[0]] >= index):
            return unavailable('scene.antecedent_unknown')
        attached = structured is not None and any(' ' + word in raw for word in ('arranged ', 'spaced ', 'mounted '))
        subject = ('scene:0' if field == 'environment' else part.part_id) if attached else None
        atoms.append(ClauseEvidence(part.part_id + ':clause', (part.part_id,), raw, Truth.TRUE,
            subject, None if field == 'environment' else 'scene:0', 'noun_phrase',
            'scene_anchor' if field == 'environment' else 'scene_owned_nominal', Truth.UNKNOWN,
            ('scene:0',) if field == 'environment' else None, antecedents,
            (('v2_direct_provenance.reviewed_scene:' if reviewed else 'v2_scene_provenance.nominal:')
             + field + '/v1',) + (('scene.sibling_reference.works/v1',) if reference else ()),
            structured[1] if structured else None))
    trace = ProducerTrace('bound_constructor', 'pipeline.location_builder', source_identity_sha256, input_binding_sha256,
        text_sha256(raw_output), text_sha256(emitted), tuple(parts), tuple(part.part_id for part in parts), None,
        'scene.reviewed_legacy_constituents/v1' if reviewed else 'scene.selected_pack_constituents/v1')
    return EvidenceComponent('scene', trace, tuple(atoms), True, (),
        (('source_order_known', Truth.TRUE), ('ownership_known', Truth.TRUE),
         ('frame_location_matches', Truth.TRUE if frame_known else Truth.UNKNOWN)))


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
    return _owned_scene_locative(anchor, parts[1])


def _owned_scene_locative(anchor, modifiers):
    """Keep every property attached immediately to the environment head."""
    base, separator, event = anchor.partition(' arranged for ')
    predicates = ['is arranged for ' + event] if separator else []
    for modifier in modifiers:
        if modifier.startswith('featuring '):
            predicates.append('features ' + modifier[len('featuring '):])
        elif modifier.startswith('with '):
            predicates.append('has ' + modifier[len('with '):])
        else:
            return None  # Temporal/adorned scope needs its own constructor proof.
    return 'in ' + base + (' that ' + ' and that '.join(predicates) if predicates else '')


def common_standalone_scene_parts(location, location_key):
    """Bind a finite Scene's time separately; this grants no relocation permission."""
    parsed = _producer_scene_components(location, location_key, bind_sources=True)
    if parsed is None:
        return None
    anchor = _nominal(location.split(', ', 1)[0], 'environment')
    if anchor is None:
        return None
    times = tuple(modifier for modifier in parsed[1] if modifier.startswith('during '))
    if len(times) > 1:
        return None
    other = tuple(modifier for modifier in parsed[1] if not modifier.startswith('during '))
    owned = _owned_scene_locative(anchor, other)
    return (owned, times[0] if times else '') if owned is not None else None
