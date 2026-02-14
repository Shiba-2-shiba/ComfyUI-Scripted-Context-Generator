# -*- coding: utf-8 -*-
"""
vocab/loc_tag_builder.py — LOC_TAG_MAP auto-generation utility
==============================================================

Provides ``build_loc_tag_map()`` which generates a LOC_TAG_MAP
from concept pack data that includes ``aliases`` fields.

This enables keeping location-tag aliases close to their pack definition
instead of in a separate hand-maintained mapping.

Usage:
    from vocab.loc_tag_builder import build_loc_tag_map
    
    auto_map = build_loc_tag_map(concept_packs)
    # auto_map["classroom"] → ["school_classroom"]

The generated map can be compared against the hand-written one
for equivalence testing during migration.
"""

from __future__ import annotations

from typing import Dict, List


def build_loc_tag_map(
    concept_packs: Dict[str, dict],
    alias_overrides: Dict[str, List[str]] | None = None,
) -> Dict[str, List[str]]:
    """
    Build a LOC_TAG_MAP from concept packs with ``aliases`` fields.

    Each pack can define an ``aliases`` list of strings. The builder
    creates one map entry per alias, pointing to the pack key.
    The pack key itself is also auto-registered as an alias.

    Multi-pack aliases (e.g. "giant tree library" → ["school_library", "fantasy_forest"])
    need to be specified in ``alias_overrides`` since they cannot be
    inferred from single-pack alias fields.

    Parameters
    ----------
    concept_packs : dict
        The full CONCEPT_PACKS dictionary. Each pack may have an
        ``aliases`` key with a list of tag strings.
    alias_overrides : dict, optional
        Additional or overriding entries to merge into the result.
        These take precedence over auto-generated entries.

    Returns
    -------
    dict
        Mapping of location tags to lists of concept pack keys.
    """
    result: Dict[str, List[str]] = {}

    for pack_key, pack_data in concept_packs.items():
        # Auto-register the pack key itself
        if pack_key not in result:
            result[pack_key] = [pack_key]

        # Process aliases
        aliases = pack_data.get("aliases", [])
        for alias in aliases:
            alias_lower = alias.lower().strip()
            if alias_lower in result:
                # Append pack if not already present
                if pack_key not in result[alias_lower]:
                    result[alias_lower].append(pack_key)
            else:
                result[alias_lower] = [pack_key]

    # Apply overrides (merge or replace)
    if alias_overrides:
        for tag, packs in alias_overrides.items():
            result[tag] = packs

    return result
