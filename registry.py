"""Compatibility facade for legacy data-loading and resolver imports.

Repo-owned runtime code should prefer the narrower service modules directly:
- `location_service.py`
- `clothing_service.py`
- `character_service.py`
- `scene_service.py`

This module remains as a stable forwarding surface for compatibility callers.
"""

from __future__ import annotations

if __package__:
    from .character_service import (
        load_character_profiles,
        resolve_character_key,
        unresolved_character_costumes,
    )
    from .clothing_service import load_clothing_theme_map, resolve_clothing_theme
    from .location_service import (
        build_location_alias_layers,
        build_location_alias_map,
        load_background_alias_overrides,
        load_background_packs,
        load_fallback_location_alias_map,
        load_legacy_location_alias_map,
        location_alias_collisions,
        resolve_location,
        resolve_location_key,
    )
    from .scene_service import (
        iter_location_candidates,
        load_action_pools,
        load_scene_axes,
        load_scene_compatibility,
    )
else:
    from character_service import (
        load_character_profiles,
        resolve_character_key,
        unresolved_character_costumes,
    )
    from clothing_service import load_clothing_theme_map, resolve_clothing_theme
    from location_service import (
        build_location_alias_layers,
        build_location_alias_map,
        load_background_alias_overrides,
        load_background_packs,
        load_fallback_location_alias_map,
        load_legacy_location_alias_map,
        location_alias_collisions,
        resolve_location,
        resolve_location_key,
    )
    from scene_service import (
        iter_location_candidates,
        load_action_pools,
        load_scene_axes,
        load_scene_compatibility,
    )


def resolve_location_alias_map():
    return build_location_alias_map()


__all__ = [
    "build_location_alias_layers",
    "build_location_alias_map",
    "iter_location_candidates",
    "load_action_pools",
    "load_background_alias_overrides",
    "load_background_packs",
    "load_character_profiles",
    "load_clothing_theme_map",
    "load_fallback_location_alias_map",
    "load_legacy_location_alias_map",
    "load_scene_axes",
    "load_scene_compatibility",
    "location_alias_collisions",
    "resolve_character_key",
    "resolve_clothing_theme",
    "resolve_location",
    "resolve_location_alias_map",
    "resolve_location_key",
    "unresolved_character_costumes",
]
