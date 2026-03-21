"""Background vocabulary — auto-built location alias map with legacy fallback."""

if __package__ and __package__.count(".") >= 2:
    from ...registry import resolve_location_alias_map
else:
    from registry import resolve_location_alias_map


LOC_TAG_MAP = resolve_location_alias_map()
THEME_CHOICES = ["none"] + sorted(list(LOC_TAG_MAP.keys()))
