# -*- coding: utf-8 -*-
"""
vocab/seed_utils.py — Salted deterministic RNG utilities
========================================================

Provides ``mix_seed()`` which combines a base seed with a domain-specific
salt to produce an independent sub-seed. This breaks correlation between
nodes that share the same user-provided seed, while preserving full
determinism (same seed + same salt → same output, always).

Usage:
    from vocab.seed_utils import mix_seed

    rng_cloth  = random.Random(mix_seed(seed, "cloth"))
    rng_loc    = random.Random(mix_seed(seed, "loc"))
    rng_garni  = random.Random(mix_seed(seed, "garnish"))
    # All three are deterministic but statistically independent
"""

from __future__ import annotations

import hashlib


def mix_seed(seed: int, salt: str) -> int:
    """
    Mix a base seed with a string salt to produce an independent sub-seed.

    Uses SHA-256 for stable, platform-independent hashing. The output is
    a 32-bit unsigned integer suitable for ``random.Random()``.

    Parameters
    ----------
    seed : int
        The user-provided base seed.
    salt : str
        A domain-specific identifier (e.g. "cloth", "loc", "garnish").

    Returns
    -------
    int
        A mixed seed in the range [0, 2^32).
    """
    h = hashlib.sha256(f"{seed}:{salt}".encode("ascii")).digest()
    return int.from_bytes(h[:4], "big")
