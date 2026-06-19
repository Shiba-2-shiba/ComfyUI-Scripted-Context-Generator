"""Compatibility facade for callers that still import `pipeline.content_pipeline`.

This module intentionally re-exports the extracted builders/orchestrator so older
imports keep working while the real implementation lives in narrower modules.
Repo-owned runtime code should import those narrower modules directly; the only
intentional repo-owned caller left is `assets/test_deprecated_behavior.py`,
which guards this compatibility surface.

Boundary contract:
- New runtime code must import `pipeline.clothing_builder`,
  `pipeline.location_builder`, `pipeline.mood_builder`, or
  `pipeline.prompt_orchestrator` directly.
- `assets/test_compatibility_boundaries.py` guards against repo-owned runtime
  imports of this facade.
- Keep this facade until external workflow or extension compatibility no longer
  needs the old import path.
"""

from .clothing_builder import apply_clothing_expansion, expand_clothing_prompt
from .location_builder import apply_location_expansion, expand_location_prompt
from .mood_builder import apply_mood_expansion, expand_dictionary_value
from .prompt_orchestrator import (
    _derive_template_roles,
    _template_entries,
    build_prompt_from_context,
    build_prompt_text,
)

__all__ = [
    "apply_clothing_expansion",
    "expand_clothing_prompt",
    "apply_location_expansion",
    "expand_location_prompt",
    "apply_mood_expansion",
    "expand_dictionary_value",
    "_derive_template_roles",
    "_template_entries",
    "build_prompt_from_context",
    "build_prompt_text",
]
