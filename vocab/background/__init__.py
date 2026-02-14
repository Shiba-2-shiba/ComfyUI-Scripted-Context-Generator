"""
Background vocabulary package — re-exports all public symbols.

This package provides the same public API as the original monolithic
``background_vocab.py`` so that ``from background_vocab import *`` and
attribute-level access both work unchanged.
"""

from .concept_packs import CONCEPT_PACKS
from .defaults import GENERAL_DEFAULTS
from .loc_tag_map import LOC_TAG_MAP, THEME_CHOICES

__all__ = [
    "CONCEPT_PACKS",
    "GENERAL_DEFAULTS",
    "LOC_TAG_MAP",
    "THEME_CHOICES",
]
