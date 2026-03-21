"""Background vocabulary — auto-built location alias map with legacy fallback."""

try:
    from ...registry import resolve_location_alias_map
except ImportError:
    from registry import resolve_location_alias_map


LOC_TAG_MAP = resolve_location_alias_map()
THEME_CHOICES = ["none"] + sorted(list(LOC_TAG_MAP.keys()))
