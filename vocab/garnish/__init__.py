"""
Garnish (pose/emotion) vocabulary package — re-exports all public symbols.

Public API:
- ``sample_garnish()``: main garnish generation function
- ``normalize()``: tag normalization utility
- Data structures accessible for advanced use / testing
"""

from .utils import normalize, _dedupe, _merge_unique
from .base_vocab import (
    VIEW_ANGLES,
    VIEW_FRAMING,
    POSE_STANDING,
    POSE_DYNAMIC,
    HAND_POSITIONS,
    HAND_GESTURES,
    EYES_BASE,
    MOUTH_BASE,
    MOOD_POOLS,
    EFFECTS_UNIVERSAL,
    EFFECTS_BRIGHT,
    EFFECTS_DARK,
    EFFECTS_DYNAMIC,
)
from .micro_actions import MICRO_ACTION_CONCEPTS, EXCLUSIVE_TAG_GROUPS
from .logic import (
    sample_garnish,
    _get_action_anchors,
    _resolve_micro_actions,
    _is_out_of_context,
)

__all__ = [
    "sample_garnish",
    "normalize",
    # Data structures (for testing / advanced use)
    "VIEW_ANGLES",
    "VIEW_FRAMING",
    "POSE_STANDING",
    "POSE_DYNAMIC",
    "HAND_POSITIONS",
    "HAND_GESTURES",
    "EYES_BASE",
    "MOUTH_BASE",
    "MOOD_POOLS",
    "MICRO_ACTION_CONCEPTS",
    "EXCLUSIVE_TAG_GROUPS",
    "EFFECTS_UNIVERSAL",
    "EFFECTS_BRIGHT",
    "EFFECTS_DARK",
    "EFFECTS_DYNAMIC",
]
