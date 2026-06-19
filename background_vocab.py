# -*- coding: utf-8 -*-
"""
background_vocab.py — Facade
=============================
All data has been moved to ``vocab/background/``.
This file re-exports every public symbol so that existing imports
(``from . import background_vocab`` / ``import background_vocab``)
continue to work without modification.

Boundary contract:
- New runtime code must import from ``vocab.background`` directly.
- Repo-owned runtime imports of this facade are guarded by
  ``assets/test_compatibility_boundaries.py``.
- Keep this facade only for external/backward-compatible imports.
"""

if __package__:
    from .vocab.background import (  # noqa: F401
        CONCEPT_PACKS,
        GENERAL_DEFAULTS,
        LOC_TAG_MAP,
        THEME_CHOICES,
    )
else:
    from vocab.background import (  # noqa: F401
        CONCEPT_PACKS,
        GENERAL_DEFAULTS,
        LOC_TAG_MAP,
        THEME_CHOICES,
    )

__all__ = [
    "CONCEPT_PACKS",
    "GENERAL_DEFAULTS",
    "LOC_TAG_MAP",
    "THEME_CHOICES",
]
