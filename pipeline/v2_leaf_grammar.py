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


# Reviewed compatibility vocabulary shared with the legacy direct route.
LEGACY_PRIMARY = frozenset({
    'checking the arrangement before moving to the next section',
    'standing quietly while reviewing what she needs next', 'securing the telescope cover',
})
LEGACY_SHARED = frozenset({
    'hovering in place while she decides', 'checking what is happening nearby',
    'weighing one choice against another', 'meeting the viewer with a quiet look',
    'looking off for a quiet second', 'taking one more easy breath',
    'leaving room for a quiet exchange with the viewer',
    'taking on an easy unhurried posture', 'letting the pause settle properly',
})
LEGACY_TEMPORAL = frozenset({'after realizing something is missing', 'after school'})

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


@dataclass(frozen=True)
class LeafGrammarFacts:
    known: bool = False
    surface_kind: str = 'unknown'
    attachment_kind: str = 'unknown'
    owner_kind: str = 'unknown'
    same_subject: bool | None = None
    no_place_reference: bool | None = None
    main_verb: str = ''


@dataclass(frozen=True)
class ActionGrammarFacts:
    parts: tuple[LeafGrammarFacts, ...] = ()
    frame_predicate_safe: bool | None = None
    same_subject_attachment_safe: bool | None = None
    independent_action_subject: bool | None = None
    no_place_reference: bool | None = None
    main_verb: str = ''
    surface_kind: str = 'unknown'


_SUBJECT_SLOTS = frozenset({'primary_action', 'hand_action', 'posture', 'gaze_target',
                          'purpose_clause', 'optional_micro_action', 'progress_clause',
                          'obstacle_clause', 'social_clause', 'time_or_weather'})
# These inflections extend the existing small valency grammar, not a conjugator.
_FINITE_GERUNDS = {'checks': 'checking', 'holds': 'holding', 'keeps': 'keeping',
                   'stands': 'standing', 'waits': 'waiting', 'adjusts': 'adjusting',
                   'tightens': 'tightening', 'walks': 'walking', 'leans': 'leaning',
                   'responds': 'responding'}
_SUBORDINATORS = ('while', 'without', 'after', 'before', 'because', 'as')


def _reviewed_role_leaf(value, slot_key, primary):
    """Reuse reviewed grammar only in the producer's existing slot roles."""
    if primary and slot_key == 'primary_action' and value in LEGACY_PRIMARY:
        return value.partition(' ')[0], 'gerund'
    if value in LEGACY_TEMPORAL and slot_key in {'time_or_weather', 'obstacle_clause'} and not primary:
        # The school expression belongs to the time slot, the other reviewed
        # temporal expression is already consumed by the subordinate grammar.
        if slot_key == 'time_or_weather':
            return '', 'temporal'
    if value not in LEGACY_SHARED:
        return None
    from . import action_generator
    tables = {
        'posture': action_generator.POSTURE_BY_PURPOSE,
        'gaze_target': action_generator.GAZE_BY_PURPOSE,
        'purpose_clause': action_generator.OPTIONAL_MICRO_ACTIONS,
        'optional_micro_action': action_generator.OPTIONAL_MICRO_ACTIONS,
        'social_clause': action_generator.SOCIAL_DISTANCE_CLAUSES,
    }
    table = tables.get(slot_key, {})
    if any(value in options for options in table.values()):
        return value.partition(' ')[0], 'gerund'
    return None


def _role_predicate(value, slot_key):
    """Closed owned-object and viewer valencies, scoped to producer roles."""
    if slot_key in {'purpose_clause', 'optional_micro_action'} and re.fullmatch(
            r'holding onto her place (?:(?:a little|a bit) )?longer', value):
        return 'holding'
    if slot_key == 'social_clause' and re.fullmatch(
            r'responding (?:(?:directly|quietly) )?to the viewer', value):
        return 'responding'
    return None


def _leaf_predicate(value):
    """Consume one predicate using closed valencies and small motion forms."""
    if predicate(value):
        return value.partition(' ')[0]
    # A seat is a spatial argument, not evidence that the scene is distinct.
    if re.fullmatch(r'sitting in the (?:audience )?seats', value):
        return 'sitting'
    # This purpose infinitive owns a concrete reading object; free pronouns,
    # destinations and trailing adjuncts are deliberately outside its valency.
    if re.fullmatch(r'leaning (?:in|closer) to read (?:a|the) (?:(?:tiny|small) )?label', value):
        return 'leaning'
    if re.fullmatch(r'(?:walking|moving)(?: slowly| carefully)?|leaning(?: closer| in)?|'
                    r'(?:standing|waiting)(?: quietly| still)?|sleeping|returning|'
                    r'(?:fully )?getting started', value):
        return value.split()[1] if value.startswith('fully ') else value.split()[0]
    if re.fullmatch(r'(?:keeping|holding) herself (?:steady|still|ready)', value):
        return value.split()[0]
    # Aspectual complements stay attached to the same explicit protagonist.
    if re.fullmatch(r'keeping (?:her place|the momentum) going|bringing it to a close|'
                    r'losing her place|heading to bed|(?:finally )?coming home|'
                    r'getting ready to leave', value):
        return value.split()[1] if value.startswith('finally ') else value.split()[0]
    verb, _, rest = value.partition(' ')
    if verb in {'checking', 'rechecking'} and re.fullmatch(
            r'what (?:still )?needs (?:doing|checking|adjusting)', rest):
        return verb
    if verb == 'adjusting' and re.fullmatch(r'something (?:out of place|nearby)', rest):
        return verb
    if verb == 'keeping' and re.fullmatch(r'her (?:movements|posture) (?:composed|steady|still)', rest):
        return verb
    if verb == 'tidying' and re.fullmatch(
            r'the (?:(?:small|quiet|narrow) )?(?:area|space)(?: around her| in front of her)?', rest):
        return verb
    if verb == 'following' and nominal(rest, {'abstract'}, determined=True):
        return verb
    if verb == 'realizing' and re.fullmatch(r'something is (?:missing|ready)', rest):
        return verb
    return None


def _protagonist_clause(value, slot_key=None):
    if value.startswith('she '):
        finite, _, rest = value[4:].partition(' ')
        if re.fullmatch(r'(?:works|waits|decides)', value[4:]):
            return {'works': 'working', 'waits': 'waiting', 'decides': 'deciding'}[finite], 'finite'
        if finite == 'gets' and re.fullmatch(r'herself (?:ready|steady)', rest):
            return 'getting', 'finite'
        gerund = _FINITE_GERUNDS.get(finite)
        if gerund and (_leaf_predicate(gerund + (' ' + rest if rest else ''))
                       or _role_predicate(gerund + (' ' + rest if rest else ''), slot_key)):
            return gerund, 'finite'
        return None
    finite, _, rest = value.partition(' ')
    gerund = _FINITE_GERUNDS.get(finite)
    if gerund and (_leaf_predicate(gerund + (' ' + rest if rest else ''))
                   or _role_predicate(gerund + (' ' + rest if rest else ''), slot_key)):
        return gerund, 'clause'
    for prefix in ('not ', 'never '):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    verb = _leaf_predicate(value) or _role_predicate(value, slot_key)
    return (verb, 'gerund') if verb else None


def _external_clause(value):
    # A small event-subject grammar; no free noun phrase or free finite tail.
    match = re.fullmatch(r'(.+) (ends|begins|starts|change|keeps stretching out)', value)
    if not match:
        return False
    subject, verb = match.groups()
    if subject == 'the lights':
        return verb == 'change'
    if subject == 'the delay':
        return verb == 'keeps stretching out'
    return bool(nominal(subject, {'event'}, determined=True) and verb in {'ends', 'begins', 'starts'})


def _body_clause(value):
    match = re.fullmatch(r'(?:her )?(eyes|hands|fingers|shoulders) (.+)', value)
    if not match:
        return False
    body, rest = match.groups()
    verb, _, obj = rest.partition(' ')
    # The grammatical subject is plural body parts: protagonist reflexives are
    # not valid objects here, even though the protagonist owns those body parts.
    return bool(body == 'eyes' and verb == 'following'
                and nominal(obj, {'abstract'}, determined=True)
                or body in {'hands', 'fingers'} and verb == 'holding'
                and _object(obj, _TRANSITIVE['holding']))


def _gaze_body_state(value):
    """An eyes-state complement with an owned body subject, not actor control."""
    return bool(re.fullmatch(r'(?:her )?eyes fixed on what needs to happen next', value))


def _shared_leaf(value, depth=0, *, slot_key=None):
    """At most two subordinate levels inside one producer-owned leaf."""
    if depth > 2:
        return None
    if value.startswith('as if '):
        if slot_key != 'social_clause':
            return None
        inner = value[len('as if '):]
        parsed = _protagonist_clause(inner, slot_key)
        return parsed if parsed and (parsed[1] == 'gerund' or inner.startswith('she ')) else None
    direct = _protagonist_clause(value, slot_key)
    if direct:
        return direct
    left, sep, right = value.partition(' and ')
    if sep:
        first, second = _protagonist_clause(left, slot_key), _protagonist_clause(right, slot_key)
        if first and second and first[1] == second[1] == 'gerund':
            return first
        return None
    for connector in _SUBORDINATORS:
        prefix = connector + ' '
        if value.startswith(prefix):
            # Causal conjunctions require an explicit finite subject.
            inner = value[len(prefix):]
            if connector in {'because', 'as'}:
                return _protagonist_clause(inner, slot_key) if inner.startswith('she ') else None
            parsed = _protagonist_clause(inner, slot_key)
            if connector == 'without':
                return parsed if parsed and parsed[1] == 'gerund' else None
            # One connector introduces one predicate, never another connector.
            return parsed if parsed and (parsed[1] == 'gerund' or inner.startswith('she ')) else None
        left, sep, right = value.partition(' ' + connector + ' ')
        if sep and _protagonist_clause(left, slot_key) and _shared_leaf(prefix + right, depth + 1, slot_key=slot_key):
            return _protagonist_clause(left, slot_key)
    return None


def action_part_facts(part, *, primary=False):
    """Only a known producer role plus fully consumed leaf grammar proves facts."""
    if (getattr(part, 'slot_key', None) not in _SUBJECT_SLOTS
            or not isinstance(getattr(part, 'text', None), str)):
        return LeafGrammarFacts()
    value = part.text
    if not value or value != value.strip() or re.search(r'[,;.!?{}\n]', value):
        return LeafGrammarFacts()
    if primary and value.startswith(('she ', 'not ', 'never ')):
        return LeafGrammarFacts()  # Main realization already supplies its subject.
    if _gaze_body_state(value):
        if primary or part.slot_key != 'gaze_target':
            return LeafGrammarFacts()
        return LeafGrammarFacts(True, 'body_state', 'with_absolute',
                                'protagonist_body_part', False, True)
    if _body_clause(value):
        if primary or part.slot_key not in {'gaze_target', 'hand_action', 'posture'}:
            return LeafGrammarFacts()
        return LeafGrammarFacts(True, 'body_part', 'independent_clause',
                                'protagonist_body_part', False, True)
    connector, _, rest = value.partition(' ')
    if connector in {'while', 'after', 'before', 'because', 'as'} and _external_clause(rest):
        if primary:
            return LeafGrammarFacts()
        attachment = 'subordinate_causal' if connector in {'because', 'as'} else 'subordinate_temporal'
        return LeafGrammarFacts(True, 'finite', attachment, 'scene_event', False, True)
    if temporal(value) and not primary:
        return LeafGrammarFacts(True, 'temporal', 'subordinate_temporal', 'protagonist', True, True)
    parsed = _reviewed_role_leaf(value, part.slot_key, primary) or _shared_leaf(value, slot_key=part.slot_key)
    if parsed is None:
        return LeafGrammarFacts()
    verb, surface = parsed
    if not primary and surface in {'finite', 'clause'} and connector not in _SUBORDINATORS:
        return LeafGrammarFacts()  # Shared referent alone cannot license a comma splice.
    # A leading temporal/causal clause is never an action predicate.
    if primary and connector in _SUBORDINATORS:
        return LeafGrammarFacts()
    attachment = ('main_predicate' if primary else
                  'subordinate_comparative' if value.startswith('as if ') else
                  'subordinate_causal' if connector in {'because', 'as'} else
                  'subordinate_temporal' if connector in {'while', 'after', 'before'} else
                  'shared_subject_modifier')
    # Known destination constructions still carry a spatial reference; they do
    # not establish scene non-overlap merely because their grammar is understood.
    no_place = None if re.search(r'\b(?:home|bed|area|space|place|nearby|school|section|seats)\b', value) else True
    return LeafGrammarFacts(True, surface, attachment, 'protagonist', True, no_place, verb)


def derive_action_grammar(evidence):
    """Aggregate positive leaf proofs. Unknown never becomes False or True."""
    from .v2_structural_evidence import ActionStructuralEvidence
    if not isinstance(evidence, ActionStructuralEvidence) or not evidence.exact_replay or not evidence.emitted_parts:
        return ActionGrammarFacts()
    parts = tuple(action_part_facts(part, primary=index == 0)
                  for index, part in enumerate(evidence.emitted_parts))
    return aggregate_action_parts(parts)


def _dependent_temporal_event(part):
    return (part.known and part.attachment_kind == 'dependent_temporal_event'
            and part.surface_kind == 'finite' and part.owner_kind == 'scene_event'
            and part.same_subject is False and part.no_place_reference is True
            and not part.main_verb)


def aggregate_action_parts(parts, *, allow_dependent_events=False):
    """Aggregate already derived leaf facts for either bounded grammar route."""
    if not parts:
        return ActionGrammarFacts()
    primary = parts[0]
    known = all(part.known for part in parts)
    shared = all(part.same_subject is True for part in parts) if known else None
    independent = any(part.same_subject is False and part.attachment_kind != 'with_absolute'
                      and not (allow_dependent_events and _dependent_temporal_event(part))
                      for part in parts) if known else None
    no_place = True if known and all(part.no_place_reference is True for part in parts) else None
    return ActionGrammarFacts(parts, True if known and primary.attachment_kind == 'main_predicate' else None,
                              shared, independent, no_place, primary.main_verb, primary.surface_kind)


def materialize_action_parts(evidence):
    """Preserve every actor leaf and license only proved body states with 'with'."""
    facts = derive_action_grammar(evidence)
    return materialize_proved_action_parts(evidence, facts)


def materialize_proved_action_parts(evidence, facts, *, allow_common_parts=False):
    """Shared rendering for fresh leaf proofs; callers own source binding."""
    if (facts.frame_predicate_safe is not True
            or len(evidence.emitted_parts) != len(facts.parts)):
        return None
    result = []
    for part, leaf in zip(evidence.emitted_parts, facts.parts):
        if leaf.attachment_kind == 'with_absolute':
            # Facts were freshly derived from the exact source text and role.
            result.append('with ' + part.text)
        elif allow_common_parts and _dependent_temporal_event(leaf):
            result.append(part.text)
        elif leaf.surface_kind == 'count_noun_gerund':
            if (not allow_common_parts or part.text != 'clicking pen'
                    or leaf.main_verb != 'clicking' or leaf.owner_kind != 'protagonist'
                    or leaf.same_subject is not True):
                return None
            result.append('clicking a pen')
        elif leaf.same_subject is True:
            result.append(part.text)
        else:
            return None
    return ', '.join(result)


def verified_primary_verbs(evidence):
    """Surface heads in a completely known primary predicate, in textual order.

    These grammatical heads do not overwrite the producer's semantic main verb.
    Callers must separately bind that semantic fact to its original parser replay.
    """
    from .v2_structural_evidence import ActionStructuralEvidence
    if not isinstance(evidence, ActionStructuralEvidence) or not evidence.exact_replay or not evidence.emitted_parts:
        return ()
    primary = evidence.emitted_parts[0]
    facts = action_part_facts(primary, primary=True)
    if not facts.known or facts.attachment_kind != 'main_predicate':
        return ()
    if ' and ' not in primary.text:
        return (facts.main_verb,) if facts.main_verb else ()
    heads = []
    for value in primary.text.split(' and '):
        if value.startswith(('not ', 'never ', 'she ')):
            return ()
        parsed = _protagonist_clause(value, primary.slot_key)
        if parsed is None or parsed[1] != 'gerund':
            return ()
        heads.append(parsed[0])
    return tuple(heads)
