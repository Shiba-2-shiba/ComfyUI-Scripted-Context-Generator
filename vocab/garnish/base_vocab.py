"""Garnish vocabulary - Base vocabulary definitions (loaded from JSON)."""

from ..loader import load_json

_data = load_json("garnish_base_vocab.json")

VIEW_ANGLES = _data["VIEW_ANGLES"]
VIEW_FRAMING = _data["VIEW_FRAMING"]
POSE_STANDING = _data["POSE_STANDING"]
POSE_SITTING = _data["POSE_SITTING"]
POSE_LYING = _data["POSE_LYING"]
POSE_DYNAMIC = _data["POSE_DYNAMIC"]
HAND_POSITIONS = _data["HAND_POSITIONS"]
HAND_GESTURES = _data["HAND_GESTURES"]
EYES_BASE = _data["EYES_BASE"]
MOUTH_BASE = _data["MOUTH_BASE"]
MOOD_POOLS = _data["MOOD_POOLS"]
EFFECTS_UNIVERSAL = _data["EFFECTS_UNIVERSAL"]
EFFECTS_BRIGHT = _data["EFFECTS_BRIGHT"]
EFFECTS_DARK = _data["EFFECTS_DARK"]
EFFECTS_DYNAMIC = _data["EFFECTS_DYNAMIC"]
