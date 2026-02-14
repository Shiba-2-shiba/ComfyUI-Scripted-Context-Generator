"""Background vocabulary — Location Tag Map & Theme Choices (loaded from JSON)."""

from ..loader import load_json

LOC_TAG_MAP = load_json("background_loc_tag_map.json")
THEME_CHOICES = ["none"] + sorted(list(LOC_TAG_MAP.keys()))
