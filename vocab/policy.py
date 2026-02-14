# -*- coding: utf-8 -*-
"""
vocab/policy.py — Vocabulary Policy Framework
==============================================

Provides a pluggable policy layer for filtering and weighting
vocabulary candidates during prompt generation.

The default policy is a no-op pass-through (backward compatible).
Custom policies can be created by subclassing ``VocabPolicy`` or
by configuring the ``DefaultPolicy`` with rules.

Usage:
    # Default (no-op): backward-compatible with existing behavior
    policy = VocabPolicy()
    filtered = policy.apply(candidates, context)
    # → returns candidates unchanged

    # Context-aware policy (matches existing _is_out_of_context logic)
    policy = ContextAwarePolicy()
    filtered = policy.apply(candidates, context={"loc_tag": "fantasy_forest"})
    # → filters out modern tech items in fantasy contexts

    # Custom policy with hard bans
    policy = VocabPolicy(hard_ban=["phone", "smartphone"])
    filtered = policy.apply(candidates, context)
    # → removes any candidate containing banned words
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set


class VocabPolicy:
    """
    Base vocabulary policy — configurable candidate filtering.

    By default, acts as a no-op pass-through. Can be configured with:
    - ``hard_ban``: list of substrings to completely exclude
    - ``soft_cap``: dict mapping category names to max count
    - ``weight_overrides``: dict mapping substrings to weight multipliers

    Subclass and override ``apply()`` for custom behavior.
    """

    def __init__(
        self,
        hard_ban: Optional[List[str]] = None,
        soft_cap: Optional[Dict[str, int]] = None,
        weight_overrides: Optional[Dict[str, float]] = None,
    ):
        self.hard_ban: List[str] = hard_ban or []
        self.soft_cap: Dict[str, int] = soft_cap or {}
        self.weight_overrides: Dict[str, float] = weight_overrides or {}

    def apply(self, candidates: List[str], context: Optional[dict] = None) -> List[str]:
        """
        Apply policy to a list of candidate strings.

        Parameters
        ----------
        candidates : list of str
            Raw candidate tags/items to filter.
        context : dict, optional
            Context information (e.g. loc_tag, costume_key, mood).

        Returns
        -------
        list of str
            Filtered candidates.
        """
        if not self.hard_ban:
            return candidates

        result = []
        for c in candidates:
            c_lower = c.lower()
            if any(ban in c_lower for ban in self.hard_ban):
                continue
            result.append(c)
        return result

    def get_weight(self, item: str) -> float:
        """
        Return the weight multiplier for a candidate item.

        Used by sampling logic to bias selection toward/away from
        certain items. Default weight is 1.0.
        """
        if not self.weight_overrides:
            return 1.0

        item_lower = item.lower()
        for pattern, weight in self.weight_overrides.items():
            if pattern in item_lower:
                return weight
        return 1.0


class ContextAwarePolicy(VocabPolicy):
    """
    Context-aware policy that suppresses modern tech in
    fantasy/historical/nature settings.

    This replicates the logic of ``_is_out_of_context()`` as a
    policy object, making it composable and testable.
    """

    # Modern tech items to suppress
    MODERN_TECH = [
        "phone", "smartphone", "cellphone", "mobile",
        "laptop", "tablet", "computer", "headphone", "earphone",
    ]

    # Context keywords that trigger tech suppression
    ANACHRONISM_TRIGGERS = [
        "fantasy", "ancient", "medieval", "shrine", "temple", "dungeon",
        "gladiator", "knight", "elf", "wizard", "witch",
        "kimono", "yukata", "samurai", "ninja",
        "forest", "nature", "beach", "ocean", "mountain", "cave",
    ]

    # Contexts where tech is acceptable even with anachronism keywords
    TECH_EXEMPTIONS = ["cyberpunk", "scifi", "modern", "office"]

    # Low-weight items for micro-action guaranteed selection
    LOW_WEIGHT_ITEMS = ["phone", "book"]

    def __init__(
        self,
        hard_ban: Optional[List[str]] = None,
        soft_cap: Optional[Dict[str, int]] = None,
        weight_overrides: Optional[Dict[str, float]] = None,
        low_weight_factor: float = 0.1,
    ):
        super().__init__(hard_ban, soft_cap, weight_overrides)
        self.low_weight_factor = low_weight_factor

    def apply(self, candidates: List[str], context: Optional[dict] = None) -> List[str]:
        """
        Apply context-aware filtering:
        1. Hard bans (from parent)
        2. Modern tech suppression in anachronistic contexts
        """
        # Apply parent's hard ban first
        result = super().apply(candidates, context)

        if not context:
            return result

        loc_tag = (context.get("loc_tag", "") or "").lower()
        costume_key = (context.get("costume_key", "") or "").lower()
        context_str = loc_tag + " " + costume_key

        # Check if we're in a tech-exempt context
        if any(ex in context_str for ex in self.TECH_EXEMPTIONS):
            return result

        # Check if we're in an anachronistic context
        is_anachronistic = any(k in context_str for k in self.ANACHRONISM_TRIGGERS)
        if not is_anachronistic:
            return result

        # Filter out modern tech
        filtered = []
        for item in result:
            item_lower = item.lower()
            if any(t in item_lower for t in self.MODERN_TECH):
                continue
            filtered.append(item)

        return filtered

    def get_weight(self, item: str) -> float:
        """
        Returns low weight for phone/book items (for micro-action
        guaranteed selection bias), full weight otherwise.
        """
        # Check parent overrides first
        parent_weight = super().get_weight(item)
        if parent_weight != 1.0:
            return parent_weight

        item_lower = item.lower()
        if any(lw in item_lower for lw in self.LOW_WEIGHT_ITEMS):
            return self.low_weight_factor
        return 1.0


# Pre-built policy instances for convenience
POLICY_NOOP = VocabPolicy()
POLICY_CONTEXT_AWARE = ContextAwarePolicy()
