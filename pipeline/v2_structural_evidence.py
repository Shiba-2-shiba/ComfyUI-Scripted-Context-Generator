"""Ephemeral producer trace; equality binds evidence to this exact action."""
from collections.abc import Mapping
from dataclasses import dataclass

try:
    from ..core.schema import ActionFrame
except ImportError:
    from core.schema import ActionFrame

from .action_renderer import RenderedActionPart, trace_action_slots


@dataclass(frozen=True)
class ActionStructuralEvidence:
    exact_replay: bool
    activity_first: bool | None
    primary_slot: str
    emitted_slots: tuple[str, ...]
    emitted_parts: tuple[RenderedActionPart, ...]


def _normalized(value):
    # Normalize spacing only. Case, punctuation, ownership and polarity matter.
    return ' '.join(value.split()) if isinstance(value, str) else None


def build_structural_evidence(frame_value, current_action):
    """Accept one provenance trace, including identical traces from both modes."""
    if isinstance(frame_value, Mapping):
        if frame_value.get('schema_version') != 'action-frame/v1':
            return None
        frame_value = ActionFrame.from_dict(frame_value)
    if not isinstance(frame_value, ActionFrame) or frame_value.schema_version != 'action-frame/v1':
        return None
    slots = frame_value.legacy_slots
    current = _normalized(current_action)
    if not isinstance(slots, Mapping) or not slots or not current or _normalized(frame_value.legacy_text) != current:
        return None
    # Renderer accepts coercible legacy values; coercion is not source evidence.
    source_keys = {'anchor', 'primary_action', 'posture', 'hand_action', 'purpose_clause',
                   'object_relation', 'object_state', 'gaze_target', 'obstacle_clause',
                   'progress_clause', 'optional_micro_action', 'social_clause', 'time_or_weather'}
    if any(key in slots and not isinstance(slots[key], str) for key in source_keys):
        return None
    matches = []
    for mode in (False, True):
        parts = trace_action_slots(slots, activity_first=mode)
        if parts and _normalized(', '.join(part.text for part in parts)) == current:
            matches.append((mode, parts))
    if not matches:
        return None
    signature = lambda parts: tuple((p.slot_key, _normalized(p.text)) for p in parts)
    if any(signature(parts) != signature(matches[0][1]) for _, parts in matches[1:]):
        return None
    parts = matches[0][1]
    # Composite/default renderer labels are useful diagnostics, not a known leaf.
    if any(part.slot_key not in source_keys or not slots.get(part.slot_key)
           or _normalized(slots[part.slot_key]) != _normalized(part.text) for part in parts):
        return None
    return ActionStructuralEvidence(True, matches[0][0] if len(matches) == 1 else None,
                                    parts[0].slot_key, tuple(p.slot_key for p in parts), parts)


def adapt_action_component(frame_value, current_action, *, input_binding_sha256,
                           source_identity_sha256, context=None):
    """Adapt legacy proofs without widening replay or grammatical acceptance.

    Runtime availability means a byte-exact producer trace exists; individual
    grammar/reference facts can still be unknown. The legacy API above retains
    its whitespace-normalized contract. No family authorization happens here.
    """
    from .realization_evidence import (
        ClauseEvidence, EvidenceComponent, ProducerPart, ProducerTrace, SourceRef,
        Truth, text_sha256, truth_from_optional,
    )
    from .v2_leaf_grammar import action_part_facts
    from .v2_common_action_grammar import derive_common_action_grammar

    def unavailable(blocker):
        return EvidenceComponent('action', None, (), False, (blocker,))

    if isinstance(frame_value, Mapping):
        if frame_value.get('schema_version') != 'action-frame/v1':
            return unavailable('binding.version_mismatch')
        # Inspect original values before the compatibility parser can coerce them.
        if (not isinstance(frame_value.get('legacy_text'), str)
                or not isinstance(frame_value.get('legacy_slots'), Mapping)):
            return unavailable('binding.replay_mismatch')
        frame_value = ActionFrame.from_dict(frame_value)
    if not isinstance(frame_value, ActionFrame):
        return unavailable('binding.replay_mismatch')
    if frame_value.schema_version != 'action-frame/v1':
        return unavailable('binding.version_mismatch')
    if (not isinstance(current_action, str) or not isinstance(frame_value.legacy_text, str)
            or frame_value.legacy_text != current_action):
        return unavailable('binding.frame_current_text_mismatch')
    structural = build_structural_evidence(frame_value, current_action)
    if structural is None:
        return unavailable('binding.replay_mismatch')
    rendered = ', '.join(part.text for part in structural.emitted_parts)
    if rendered != current_action:
        return unavailable('binding.replay_mismatch')

    producer = 'pipeline.action_renderer'
    parts = tuple(
        ProducerPart(
            f'action:{part.slot_key}:{index}',
            SourceRef('action', producer, part.slot_key, None,
                      text_sha256(frame_value.legacy_slots[part.slot_key])),
            part.text,
        )
        for index, part in enumerate(structural.emitted_parts)
    )
    mode = ('same_trace' if structural.activity_first is None else
            'true' if structural.activity_first else 'false')
    trace = ProducerTrace(
        mode='exact_renderer_replay', producer=producer,
        source_identity_sha256=source_identity_sha256,
        input_binding_sha256=input_binding_sha256,
        raw_output_sha256=text_sha256(rendered),
        emitted_output_sha256=text_sha256(current_action), parts=parts,
        emitted_part_ids=tuple(part.part_id for part in parts),
        # The old trace exposes emitted parts only, not suppression rule proofs.
        omitted_parts=None, constructor_id='action_slots:activity_first:' + mode,
    )
    grammar = derive_common_action_grammar(structural, frame_value, context)
    atoms = []
    for index, (part, leaf) in enumerate(zip(parts, grammar.parts)):
        subject = owner = None
        antecedents = None
        legacy_known = action_part_facts(structural.emitted_parts[index], primary=index == 0).known
        if leaf.known and leaf.owner_kind == 'protagonist':
            subject = owner = 'protagonist'
        elif leaf.known and leaf.owner_kind == 'protagonist_body_part':
            # Identity extraction is guarded by the unchanged closed body rule.
            body = part.text.removeprefix('her ').partition(' ')[0]
            subject, owner = 'body:' + body, 'protagonist'
        elif leaf.known and leaf.owner_kind == 'scene_event':
            subject = 'event:' + part.part_id
        elif leaf.known and leaf.owner_kind == 'primary_object_part':
            owner = 'object:' + frame_value.primary_object
            subject = owner + ':pages'
            antecedents = (parts[0].part_id,)
        if leaf.known and not legacy_known and leaf.owner_kind == 'protagonist_body_part':
            antecedents = ('protagonist',)
        atoms.append(ClauseEvidence(
            atom_id=part.part_id + ':clause', source_part_ids=(part.part_id,),
            source_text=part.text,
            grammar_known=Truth.TRUE if leaf.known else Truth.UNKNOWN,
            grammatical_subject_id=subject, owner_id=owner,
            form=leaf.surface_kind, attachment=leaf.attachment_kind,
            same_subject=truth_from_optional(leaf.same_subject),
            place_refs=() if leaf.no_place_reference is True else None,
            antecedent_ids=antecedents,
            rule_ids=((('v2_leaf_grammar.action_part_facts:' if legacy_known else
                        'v2_common_action_grammar:' + part.source.field + ':') + leaf.attachment_kind),)
            if leaf.known else (),
            grammatical_head=leaf.main_verb or None,
        ))
    facts = tuple(
        (name, truth_from_optional(getattr(grammar, name)))
        for name in ('frame_predicate_safe', 'same_subject_attachment_safe',
                     'independent_action_subject', 'no_place_reference')
    )
    blockers = ('action.leaf_grammar_unknown',) if any(
        atom.grammar_known is Truth.UNKNOWN for atom in atoms) else ()
    return EvidenceComponent('action', trace, tuple(atoms), True, blockers, facts)
