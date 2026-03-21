from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Dict, Iterable


ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "vocab", "data")


def _load_json(filename: str):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_scene_compatibility() -> Dict[str, dict]:
    return _load_json("scene_compatibility.json")


@lru_cache(maxsize=1)
def load_action_pools() -> Dict[str, dict]:
    return _load_json("action_pools.json")


@lru_cache(maxsize=1)
def load_scene_axes() -> Dict[str, dict]:
    return _load_json("scene_axis.json")


def iter_location_candidates() -> Iterable[str]:
    compatibility = load_scene_compatibility()
    yielded = set()
    for key in compatibility.get("daily_life_locs", []):
        if key not in yielded:
            yielded.add(key)
            yield key
    for key in compatibility.get("universal_locs", []):
        if key not in yielded:
            yielded.add(key)
            yield key
    for locs in compatibility.get("loc_tags", {}).values():
        for key in locs:
            if key not in yielded:
                yielded.add(key)
                yield key
