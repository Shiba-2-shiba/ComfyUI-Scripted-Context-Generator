"""Clothing vocabulary - Theme to Pack mapping (loaded from JSON)."""

from ..loader import load_json

THEME_TO_PACKS = load_json("clothing_theme_map.json")
THEME_CHOICES = ["none"] + sorted(list(THEME_TO_PACKS.keys()))
