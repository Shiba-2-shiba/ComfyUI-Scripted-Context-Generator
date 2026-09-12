"""Common-only productive leaves bound to received producer roles and relations.

Legacy proofs run first. New rules consume complete clauses; relation vocabulary
proves origin and ownership only, never the grammar of an object state.
"""
from collections.abc import Mapping
import re

try:
    from ..core.schema import ActionFrame
    from ..object_focus_service import load_object_relation_profiles
except ImportError:
    from core.schema import ActionFrame
    from object_focus_service import load_object_relation_profiles

from .v2_leaf_grammar import (
    ActionGrammarFacts, LeafGrammarFacts, _leaf_predicate, action_part_facts,
    aggregate_action_parts, materialize_proved_action_parts, nominal, predicate,
)
from .v2_structural_evidence import build_structural_evidence


def _field(value, key, default=None):
    return value.get(key, default) if isinstance(value, Mapping) else getattr(value, key, default)


def _bound_frame(structural, frame):
    if isinstance(frame, Mapping):
        if frame.get('schema_version') != 'action-frame/v1':
            return None
        frame = ActionFrame.from_dict(frame)
    if not isinstance(frame, ActionFrame) or frame.schema_version != 'action-frame/v1':
        return None
    if structural is None or build_structural_evidence(frame, frame.legacy_text) != structural:
        return None
    if ', '.join(part.text for part in structural.emitted_parts) != frame.legacy_text:
        return None
    return frame


def _reading_activity(value):
    """Reuse selector nominal parsing, with studied inflection's same valency."""
    from .syntax_family_selector import _action_structure, _nominal_object
    verb, separator, obj = value.partition(' ')
    if verb not in {'reading', 'reviewing', 'studying'} or not separator:
        return None
    # Require an actual known object, not selector-approved adverbs or places.
    if not re.fullmatch(r'(?:a|an|the|her) [a-z]+(?: [a-z]+)*', obj) or not _nominal_object(obj):
        return None
    determiner, _, noun = obj.partition(' ')
    if determiner in {'a', 'an'} and determiner != ('an' if noun[0] in 'aeiou' else 'a'):
        return None
    grammatical = 'reading ' + obj if verb == 'studying' else value
    _, surface, independent = _action_structure(grammatical)
    return (verb, noun) if surface == 'gerund' and independent is False else None


def _stance_activity(part, frame, primary):
    if not primary or part.slot_key != 'primary_action':
        return None
    slots = frame.legacy_slots
    posture, activity = slots.get('posture', ''), slots.get('hand_action', '')
    if not posture or not activity or part.text != posture + ' ' + activity:
        return None
    if frame.posture != posture or frame.hand_action != activity:
        return None
    # Reuse only nonspatial simple poses; richer posture complements are unknown.
    if not re.fullmatch(r'lying down|(?:standing|waiting)(?: quietly| still)?|leaning(?: closer| in)?', posture):
        return None
    head = 'lying' if posture == 'lying down' else _leaf_predicate(posture)
    if head != frame.main_verb or not _reading_activity(activity):
        return None
    return LeafGrammarFacts(True, 'gerund', 'main_predicate', 'protagonist', True, True, head)


def _received_book_relation(frame, context, structural):
    if frame.primary_object != 'book' or _field(context, 'action') != frame.legacy_text:
        return False
    activity = _reading_activity(frame.legacy_slots.get('hand_action', ''))
    primary = structural.emitted_parts[0]
    if not activity or activity[1] != 'book' or not _stance_activity(primary, frame, True):
        return False
    history = _field(context, 'history', ())
    if not isinstance(history, (tuple, list)):
        return False
    latest = next((item for item in reversed(history)
                   if _field(item, 'node') == 'ContextSceneVariator'), None)
    decision = _field(latest, 'decision', {})
    if not isinstance(decision, Mapping):
        return False
    received_frame = decision.get('action_frame')
    if received_frame is not None and received_frame != frame.to_dict():
        return False
    if 'new_action' in decision and decision['new_action'] != frame.legacy_text:
        return False
    if 'slots' in decision and decision['slots'] != frame.legacy_slots:
        return False
    semantic = decision.get('semantic_epig', {})
    relation = semantic.get('object_relation', {}) if isinstance(semantic, Mapping) else {}
    if not isinstance(relation, Mapping) or relation.get('mode') != 'active':
        return False
    relation_key = relation.get('relation_key')
    if not isinstance(relation_key, str):
        return False
    profiles = load_object_relation_profiles().get('relations', {})
    profile = profiles.get(relation_key, {})
    if not isinstance(profile, Mapping) or profile.get('object') != 'book':
        return False
    if activity[0] not in profile.get('verbs', ()):
        return False
    if 'detected_objects' in relation and relation['detected_objects'] != ['book']:
        return False
    roles, applied = relation.get('required_roles'), relation.get('applied_slots')
    if not isinstance(roles, Mapping) or roles != profile.get('required_roles') or not isinstance(applied, Mapping):
        return False
    if applied.get('object_state') != frame.legacy_slots.get('object_state'):
        return False
    return all(role in roles and isinstance(roles[role], list)
               and value in roles[role] and frame.legacy_slots.get(role) == value
               for role, value in applied.items())


def _common_part(part, frame, structural, context, primary):
    value = part.text
    if not value or value != value.strip() or not re.fullmatch(r'[a-z]+(?:[- ]?[a-z]+)*', value):
        return LeafGrammarFacts()
    stance = _stance_activity(part, frame, primary)
    if stance:
        return stance
    attachment = 'main_predicate' if primary else 'shared_subject_modifier'
    manner = r'(?:composure|(?:quiet|steady) purpose)'
    if part.slot_key in {'primary_action', 'hand_action'} and re.fullmatch(
            r'turning toward the center of attention with ' + manner, value):
        # Attention is an abstract target; this rule never licenses a place.
        return LeafGrammarFacts(True, 'gerund', attachment, 'protagonist', True, True, 'turning')
    if part.slot_key in {'primary_action', 'posture'} and re.fullmatch(
            r'leaning (?:in|closer) with ' + manner, value):
        return LeafGrammarFacts(True, 'gerund', attachment, 'protagonist', True, True, 'leaning')
    if not primary and part.slot_key in {'purpose_clause', 'optional_micro_action'} and re.fullmatch(
            r'clicking pen', value):
        # The source's bare singular count noun licenses exactly one article.
        return LeafGrammarFacts(True, 'count_noun_gerund', attachment,
                                'protagonist', True, True, 'clicking')
    if not primary and part.slot_key == 'time_or_weather' and re.fullmatch(
            r'as the (?:session|task) wraps up', value):
        # A temporal event remains its own subject, never protagonist control.
        return LeafGrammarFacts(True, 'finite', 'dependent_temporal_event',
                                'scene_event', False, True)
    if part.slot_key in {'primary_action', 'purpose_clause', 'optional_micro_action'}:
        if value.startswith('rechecking ') and predicate('checking ' + value[len('rechecking '):]):
            return LeafGrammarFacts(True, 'gerund', 'main_predicate' if primary else 'shared_subject_modifier',
                                    'protagonist', True, True, 'rechecking')
    if not primary and part.slot_key == 'gaze_target':
        match = re.fullmatch(r'(?:her )?eyes following (.+) she is working through', value)
        if match and nominal(match[1], {'abstract'}, determined=True):
            return LeafGrammarFacts(True, 'body_part', 'with_absolute',
                                    'protagonist_body_part', False, True)
    if (not primary and part.slot_key == 'object_state'
            and re.fullmatch(r'(?:open|closed) pages visible', value)
            and _received_book_relation(frame, context, structural)):
        return LeafGrammarFacts(True, 'object_part_state', 'with_absolute',
                                'primary_object_part', False, True)
    return LeafGrammarFacts()


def derive_common_action_grammar(structural, frame, context=None):
    """Keep legacy leaf proofs and derive bounded missing facts from this input."""
    frame = _bound_frame(structural, frame)
    if frame is None:
        return ActionGrammarFacts()
    parts = []
    for index, part in enumerate(structural.emitted_parts):
        leaf = action_part_facts(part, primary=index == 0)
        parts.append(leaf if leaf.known else _common_part(part, frame, structural, context, index == 0))
    return aggregate_action_parts(tuple(parts), allow_dependent_events=True)


def materialize_common_action_parts(structural, frame, context=None):
    """Preserve source words, inserting only proved articles/absolute connectors."""
    return materialize_proved_action_parts(
        structural, derive_common_action_grammar(structural, frame, context),
        allow_common_parts=True)
