"""Candidate-only, positively bounded grammar for the direct template triple.

The tables classify reusable clause components, never seeds or whole prompts.
Unknown constructions fail closed. Materialization inserts only grammatical
articles/links; raw evidence is revalidated at each eligibility boundary.
"""
from collections.abc import Mapping
import re

try:
    from ..core.schema import ActionFrame
    from ..core.semantic_policy import find_banned_terms
    from ..core.solo_safety import is_solo_safe_text
    from ..object_focus_service import extract_action_object_flags
    from ..location_service import load_background_packs
except ImportError:
    from core.schema import ActionFrame
    from core.semantic_policy import find_banned_terms
    from core.solo_safety import is_solo_safe_text
    from object_focus_service import extract_action_object_flags
    from location_service import load_background_packs

from .v2_leaf_grammar import background_modifiers, gaze, place_phrase, predicate, simple_clothes, temporal


_STANDALONE_FAMILY = 'subject_action__scene_tail'
_RELOCATED_FAMILIES = frozenset({'scene_lead_subject_action', 'subject_scene_action'})
_TEMPLATES = {'subject': '{subject_clause}', 'adjunct': '{action_clause}', 'scene': '{scene_clause}'}
_COLORS = ('black', 'blonde', 'blue', 'brown', 'copper', 'dark brown', 'ginger', 'pink',
           'platinum blonde', 'purple', 'red', 'silver', 'white')
_EYES = ('amber', 'blue', 'brown', 'cyan', 'dark brown', 'glowing green', 'gold', 'green',
         'grey', 'hazel', 'ice blue', 'neon blue', 'pink', 'purple', 'red', 'sharp black')
_STYLES = {
    'elegant updo': 'an elegant updo', 'short asymmetrical cut': 'a short asymmetrical cut',
    'bob cut': 'a bob cut', 'high ponytail': 'a high ponytail', 'messy bun': 'a messy bun',
    'long curly hair': 'long curly hair', 'long straight hair': 'long straight hair',
    'long flowing hair': 'long flowing hair', 'loose waves': 'loose waves',
    'short messy bob': 'a short messy bob', 'neatly tied hair': 'neatly tied hair',
}
_PRIMARY = frozenset({
    'checking the arrangement before moving to the next section',
    'standing quietly while reviewing what she needs next', 'securing the telescope cover',
})
_SHARED = frozenset({
    'hovering in place while she decides', 'checking what is happening nearby',
    'weighing one choice against another', 'meeting the viewer with a quiet look',
    'looking off for a quiet second', 'taking one more easy breath',
    'leaving room for a quiet exchange with the viewer',
    'taking on an easy unhurried posture', 'letting the pause settle properly',
})
_TEMPORAL = frozenset({'after realizing something is missing', 'after school'})
_GARNISH = {
    'brows knit in concentration': 'with brows knit in concentration',
    'steady gaze': 'with a steady gaze', 'still posture': 'with a still posture',
    'hands kept precise and controlled': 'with hands kept precise and controlled',
}
_ENVIRONMENTS = {
    'antique_shop': {'cluttered dusty antique shop', 'mysterious curio store filled with history'},
    'university_campus_courtyard': {'open university campus courtyard', 'sunny college quad with benches'},
    'observatory_dome': {'hilltop astronomical observatory', 'circular telescope chamber'},
}
# Each value supplies the determiner required by its reviewed noun phrase.
_NOUNS = {
    'old mechanical clocks': 'old mechanical clocks',
    'ornate gold-framed mirrors': 'ornate gold-framed mirrors',
    'vintage curved glass display cabinets': 'vintage curved glass display cabinets',
    'canvas backpacks resting on benches': 'canvas backpacks resting on benches',
    'wide stone path between lawns': 'a wide stone path between lawns',
    'large equatorial telescope': 'a large equatorial telescope',
    'curved rotating dome track': 'a curved rotating dome track',
    'weather monitor': 'a weather monitor',
}
_DETAILS = {'polished finish': 'with a polished finish',
            'layered background depth': 'with layered background depth',
            'quiet timeless atmosphere': 'with a quiet timeless atmosphere'}
_TIMES = {'evening': 'the evening', 'late morning': 'late morning',
          'bright afternoon': 'a bright afternoon', 'deep moonless night': 'a deep moonless night'}
_MOODS = {
    'the moment kept deliberate rather than urgent, with everything else held at the edge',
    'the scene narrowing to one line of thought as the rest of the room falls gently aside',
    'a quiet room holding around her while the task in front of her sets the pace',
}


def _article(value):
    return ('an ' if value[0] in 'aeiou' else 'a ') + value


def _subject(value):
    for color in _COLORS:
        for eyes in _EYES:
            tail = color + ' hair and ' + eyes + ' eyes'
            if value == 'A solo girl with ' + tail:
                return value
            for style, rendered in _STYLES.items():
                if value == 'A solo girl with ' + style + ', ' + tail:
                    return 'A solo girl with ' + rendered + ', ' + tail
    return None


def _clothes(value):
    if value == 'casual layered top and practical trousers':
        return 'a ' + value
    if re.fullmatch(r'(?:silver|beige|cream|dusty rose|soft gray) '
                    r'(?:(?:fair isle|solid|cable-knit) )?'
                    r'(?:(?:wool|cashmere|fleece) )?'
                    r'(?:(?:long-sleeve|knee-length) )?'
                    r'(?:warm turtleneck sweater dress|cozy sweater dress)', value):
        return 'a ' + value
    return simple_clothes(value)


def _scene_modifier(part):
    """Consume one complete, closed modifier; never split the mood clause."""
    if part in _DETAILS:
        return _DETAILS[part]
    if part.startswith('during ') and part[7:] in _TIMES:
        return 'during ' + _TIMES[part[7:]]
    prefix = next((p for p in ('with ', 'featuring ', 'adorned with ') if part.startswith(p)), None)
    if prefix is None:
        return None
    nouns = part[len(prefix):].split(' and ')
    if any(noun not in _NOUNS for noun in nouns):
        return None
    return prefix + ' and '.join(_NOUNS[noun] for noun in nouns)


def _scene_parts(location, mood, location_key):
    """Derive anchor, closed modifiers and with-absolute from raw source text."""
    anchor, *raw_modifiers = location.split(', ')
    if mood not in _MOODS:
        return None
    modifiers = tuple(_scene_modifier(part) for part in raw_modifiers)
    if anchor in _ENVIRONMENTS.get(location_key, set()) and all(part is not None for part in modifiers):
        return 'in ' + _article(anchor), modifiers, 'with ' + mood
    pack = load_background_packs().get(location_key, {})
    parsed_anchor = place_phrase(anchor)
    if anchor not in pack.get('environment', []) or parsed_anchor is None:
        return None
    modifiers = background_modifiers(raw_modifiers, pack)
    if modifiers is None:
        return None
    return parsed_anchor, modifiers, 'with ' + mood


def _relative_scene(parts):
    """Give all location modifiers one explicit owner before moving the scene."""
    anchor, modifiers, absolute = parts
    predicates = []
    for modifier in modifiers:
        if modifier.startswith('during '):
            if not predicates:
                return None  # No proved owner for a leading temporal modifier.
            predicates[-1] += ' ' + modifier
        elif modifier.startswith('with '):
            predicates.append('has ' + modifier[5:])
        elif modifier.startswith('featuring '):
            predicates.append('features ' + modifier[10:])
        elif modifier.startswith('adorned with '):
            predicates.append('is ' + modifier)
        else:
            return None
    if not predicates:
        return anchor + ', ' + absolute
    coordinated = predicates[0] if len(predicates) == 1 else (
        ' and '.join(predicates) if len(predicates) == 2 else
        ', '.join(predicates[:-1]) + ', and ' + predicates[-1])
    return anchor + ', which ' + coordinated + ', ' + absolute


def _scene(location, mood, location_key, syntax_family=None):
    parts = _scene_parts(location, mood, location_key)
    if parts is None:
        return None
    if syntax_family in _RELOCATED_FAMILIES:
        return _relative_scene(parts)
    anchor, modifiers, absolute = parts
    return ', '.join((anchor, *modifiers, absolute))


def materialize_direct(provenance, frame_value, *, syntax_family=None):
    """Reconstruct supported concrete clauses from raw, fully checked evidence."""
    if not isinstance(provenance, Mapping):
        return None
    slots, pairs, surface = (provenance.get(k) for k in ('slots', 'replacements', 'surface'))
    if not isinstance(slots, Mapping) or not isinstance(surface, Mapping) or not isinstance(pairs, (list, tuple)):
        return None
    if any(slots.get(k) != v for k, v in _TEMPLATES.items()):
        return None
    if any(not isinstance(pair, (list, tuple)) or len(pair) != 2
           or not all(isinstance(v, str) for v in pair) for pair in pairs):
        return None
    values = dict(pairs)
    required = {'{subject_clause}', '{action_clause}', '{scene_clause}', '{scene_anchor_clause}',
                '{subj}', '{costume}', '{loc}', '{action}', '{garnish}', '{meta_mood}', '{meta_style}'}
    if len(values) != len(pairs) or set(values) != required or any(re.search(r'[{}.!?;]', v) for v in values.values()):
        return None
    subject, clothes = _subject(values['{subj}']), _clothes(values['{costume}'])
    if subject is None or clothes is None:
        return None
    if values['{subject_clause}'] != values['{subj}'] + ' in ' + values['{costume}']:
        return None
    if (values['{scene_clause}'] != 'in ' + values['{loc}'] + ', ' + values['{meta_mood}']
            or values['{scene_anchor_clause}'] != values['{scene_clause}'][3:]):
        return None
    frame = frame_value if isinstance(frame_value, ActionFrame) else ActionFrame.from_dict(frame_value)
    action, garnish = values['{action}'], values['{garnish}']
    rendered = action + (', ' + garnish if garnish else '')
    if (frame.schema_version != 'action-frame/v1' or frame.legacy_text != action
            or values['{action_clause}'] != rendered or surface.get('rendered_clause') != rendered
            or surface.get('surface') != 'gerund'):
        return None
    pieces = action.split(', ')
    if (pieces[0] not in _PRIMARY and not predicate(pieces[0])
            or any(p not in _SHARED | _TEMPORAL and not predicate(p) and not temporal(p) for p in pieces[1:])):
        return None
    verb = pieces[0].split()[0]
    obj = frame.primary_object
    if (frame.main_verb != verb or slots.get('predicate') != verb or slots.get('object') != obj
            or any(surface.get(key, value) != value for key, value in
                   (('verb', verb), ('first_token', verb), ('input_surface', 'gerund')))
            or (obj and obj not in extract_action_object_flags(action)
                and re.search(r'(?<!\w)' + re.escape(obj) + r'(?!\w)', action) is None)):
        return None
    garnishes = garnish.split(', ') if garnish else []
    if any(g not in _GARNISH and not gaze(g) for g in garnishes):
        return None
    scene = _scene(values['{loc}'], values['{meta_mood}'], frame.legacy_slots.get('location'), syntax_family)
    if scene is None:
        return None
    joined = ' '.join(values[k] for k in _TEMPLATES.values())
    if find_banned_terms(joined) or not is_solo_safe_text(joined):
        return None
    return {**slots, 'subject': subject + ' in ' + clothes,
            'adjunct': ', '.join([action, *(_GARNISH[g] if g in _GARNISH else g for g in garnishes)]), 'scene': scene}


def direct_binding_families(plan, frame, surface, provenance):
    """Recheck family-specific slots and derive support from constructor success."""
    expected = materialize_direct(provenance, frame, syntax_family=plan.syntax_family)
    if not (expected is not None and dict(plan.semantic_slots) == expected
            and plan.lexical_choice == 'gerund'
            and isinstance(surface, Mapping)
            and dict(surface) == {**provenance['surface'], 'rendered_clause': expected['adjunct']}):
        return frozenset()
    supported = {_STANDALONE_FAMILY}
    if materialize_direct(provenance, frame, syntax_family='scene_lead_subject_action') is not None:
        supported.update(_RELOCATED_FAMILIES)
    return frozenset(supported)
