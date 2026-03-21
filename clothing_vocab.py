# -*- coding: utf-8 -*-
"""
clothing_vocab.py — Facade
===========================
All data has been moved to ``vocab/clothing/``.
This file re-exports every public symbol for backward compatibility.
"""

if __package__:
    from .vocab.clothing import (  # noqa: F401
        CONCEPT_PACKS,
        THEME_TO_PACKS,
        THEME_CHOICES,
        STATE_TAGS,
        PALETTE_DEFAULT_PROBABILITIES,
        OPTIONAL_DETAIL_PROBABILITY,
        STATE_DETAIL_PROBABILITY,
        OUTERWEAR_SELECTION_PROBABILITY,
        EMBELLISHMENT_DETAIL_PROBABILITY,
    )
else:
    from vocab.clothing import (  # noqa: F401
        CONCEPT_PACKS,
        THEME_TO_PACKS,
        THEME_CHOICES,
        STATE_TAGS,
        PALETTE_DEFAULT_PROBABILITIES,
        OPTIONAL_DETAIL_PROBABILITY,
        STATE_DETAIL_PROBABILITY,
        OUTERWEAR_SELECTION_PROBABILITY,
        EMBELLISHMENT_DETAIL_PROBABILITY,
    )

__all__ = [
    "CONCEPT_PACKS",
    "THEME_TO_PACKS",
    "THEME_CHOICES",
    "STATE_TAGS",
    "PALETTE_DEFAULT_PROBABILITIES",
    "OPTIONAL_DETAIL_PROBABILITY",
    "STATE_DETAIL_PROBABILITY",
    "OUTERWEAR_SELECTION_PROBABILITY",
    "EMBELLISHMENT_DETAIL_PROBABILITY",
]
