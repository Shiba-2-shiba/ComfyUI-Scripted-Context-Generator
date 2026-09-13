"""Canonical diagnostic blocker IDs; never grant runtime permission."""
from __future__ import annotations


FAMILY_PREFIX_ALIASES = {
    'family.required_fact_not_true.': 'family.required_fact_not_true:',
    'family.forbidden_fact_not_false.': 'family.forbidden_fact_not_false:',
    'family.missing_slot.': 'family.missing_slot:',
}

HARD_EXACT = frozenset({
    'policy.conflict', 'binding.frame_current_text_mismatch',
    'binding.replay_mismatch', 'binding.current_input_mismatch',
    'render.proof_constructor_mismatch', 'transport.runtime_inputs_missing',
})

FACT_DOMAIN = {
    'frame_predicate_safe': 'action',
    'independent_action_subject': 'action',
    'same_subject_attachment_safe': 'action',
    # These facts derive from ActionGrammarFacts.no_place_reference in
    # family_capabilities._prepare(), so repair responsibility is Action.
    'scene_action_overlap': 'action',
    'scene_action_nonduplicative': 'action',
    'scene_lead_safe': 'scene',
    'scene_adjunct_safe': 'scene',
    'standalone_scene_safe': 'scene',
}

SLOT_DOMAIN = {'subject': 'subject', 'adjunct': 'action', 'predicate': 'action', 'scene': 'scene'}

FAMILY_EXACT_DOMAIN = {
    # All four are emitted from Action-derived facts in family_capabilities._proof().
    'family.scene_overlap_unknown': 'action',
    'family.action_lead_subject_unknown': 'action',
    'family.frame_unproved': 'action',
    'family.independent_subject': 'action',
}


def canonical_blocker_id(identifier: str) -> str:
    if not isinstance(identifier, str) or not identifier:
        raise ValueError('blocker identifier must be a non-empty string')
    for old, new in FAMILY_PREFIX_ALIASES.items():
        if identifier.startswith(old):
            return new + identifier[len(old):]
    return identifier


def is_hard_excluded(identifier: str) -> bool:
    identifier = canonical_blocker_id(identifier)
    return (
        identifier in HARD_EXACT
        or identifier.startswith(('policy.', 'binding.', 'transport.'))
        or 'stale' in identifier
        or ('mismatch' in identifier and any(part in identifier for part in
                                             ('binding', 'replay', 'current_input', 'constructor')))
    )


def blocker_domain(identifier: str) -> str | None:
    identifier = canonical_blocker_id(identifier)
    if identifier in FAMILY_EXACT_DOMAIN:
        return FAMILY_EXACT_DOMAIN[identifier]
    for domain in ('action', 'scene', 'clothing', 'subject', 'template', 'garnish', 'mood'):
        if identifier.startswith(domain + '.'):
            return domain
    prefix = 'family.required_fact_not_true:'
    if identifier.startswith(prefix):
        return FACT_DOMAIN.get(identifier[len(prefix):])
    prefix = 'family.forbidden_fact_not_false:'
    if identifier.startswith(prefix):
        return FACT_DOMAIN.get(identifier[len(prefix):])
    prefix = 'family.missing_slot:'
    if identifier.startswith(prefix):
        return SLOT_DOMAIN.get(identifier[len(prefix):])
    return None


def is_repairable_blocker(identifier: str) -> bool:
    identifier = canonical_blocker_id(identifier)
    return not is_hard_excluded(identifier) and blocker_domain(identifier) is not None
