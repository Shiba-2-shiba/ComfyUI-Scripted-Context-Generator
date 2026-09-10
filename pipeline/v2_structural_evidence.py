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
