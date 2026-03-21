# -*- coding: utf-8 -*-
"""
improved_pose_emotion_vocab.py — Facade
========================================
All data and logic has been moved to ``vocab/garnish/``.
This file re-exports every public symbol for backward compatibility.
"""

if __package__:
    from .vocab.garnish import (  # noqa: F401
        sample_garnish,
        normalize,
        # Data structures used by nodes & tests
        VIEW_ANGLES,
        VIEW_FRAMING,
        POSE_STANDING,
        POSE_DYNAMIC,
        HAND_POSITIONS,
        HAND_GESTURES,
        EYES_BASE,
        MOUTH_BASE,
        MOOD_POOLS,
        MICRO_ACTION_CONCEPTS,
        EXCLUSIVE_TAG_GROUPS,
        EFFECTS_UNIVERSAL,
        EFFECTS_BRIGHT,
        EFFECTS_DARK,
        EFFECTS_DYNAMIC,
        # Internal helpers (re-exported for compat)
        _get_action_anchors,
        _resolve_micro_actions,
        _is_out_of_context,
    )
else:
    from vocab.garnish import (  # noqa: F401
        sample_garnish,
        normalize,
        # Data structures used by nodes & tests
        VIEW_ANGLES,
        VIEW_FRAMING,
        POSE_STANDING,
        POSE_DYNAMIC,
        HAND_POSITIONS,
        HAND_GESTURES,
        EYES_BASE,
        MOUTH_BASE,
        MOOD_POOLS,
        MICRO_ACTION_CONCEPTS,
        EXCLUSIVE_TAG_GROUPS,
        EFFECTS_UNIVERSAL,
        EFFECTS_BRIGHT,
        EFFECTS_DARK,
        EFFECTS_DYNAMIC,
        # Internal helpers (re-exported for compat)
        _get_action_anchors,
        _resolve_micro_actions,
        _is_out_of_context,
    )

__all__ = [
    "sample_garnish", "normalize",
]
