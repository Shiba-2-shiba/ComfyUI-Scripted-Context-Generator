"""Garnish vocabulary - Micro-action concepts and exclusive tag groups (loaded from JSON)."""

from ..loader import load_json

MICRO_ACTION_CONCEPTS = load_json("garnish_micro_actions.json")
EXCLUSIVE_TAG_GROUPS = load_json("garnish_exclusive_groups.json")
