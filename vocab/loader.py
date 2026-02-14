# -*- coding: utf-8 -*-
"""
vocab/loader.py — JSON file loader with caching
================================================

Loads vocabulary data from JSON files with module-level caching.
In development mode (``PROMPT_BUILDER_DEV=1``), checks file mtime
on each access to auto-invalidate stale caches.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Cache: filename → (mtime, data)
_cache: Dict[str, tuple] = {}

# Dev mode: automatically reload when file changes
_DEV_MODE = os.environ.get("PROMPT_BUILDER_DEV", "0") == "1"


def load_json(filename: str) -> Any:
    """
    Load a JSON file from ``vocab/data/`` with caching.

    In production (default): caches forever after first load.
    In dev mode (``PROMPT_BUILDER_DEV=1``): checks mtime on each call,
    reloading only if the file has been modified.

    Parameters
    ----------
    filename : str
        Basename of the JSON file (e.g. ``"background_packs.json"``).

    Returns
    -------
    Any
        Parsed JSON data (typically a dict or list).
    """
    filepath = os.path.join(_DATA_DIR, filename)

    if filename in _cache:
        cached_mtime, cached_data = _cache[filename]
        if not _DEV_MODE:
            return cached_data
        # Dev mode: check if file has been modified
        current_mtime = os.path.getmtime(filepath)
        if current_mtime == cached_mtime:
            return cached_data

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    mtime = os.path.getmtime(filepath)
    _cache[filename] = (mtime, data)
    return data


def clear_cache() -> None:
    """Clear all cached data. Useful for testing."""
    _cache.clear()
