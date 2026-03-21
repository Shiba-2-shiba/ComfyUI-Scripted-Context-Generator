from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.semantic_policy import find_banned_terms
from core.context_ops import patch_context
from pipeline.action_generator import generate_action_for_location, parse_pool_action_to_slots
from pipeline.location_builder import expand_location_prompt
from pipeline.prompt_orchestrator import build_prompt_from_context
from pipeline.context_pipeline import can_generate_action_for_location
from registry import (
    load_action_pools,
    load_scene_axes,
    iter_location_candidates,
    load_background_packs,
    load_character_profiles,
    load_clothing_theme_map,
    load_scene_compatibility,
    location_alias_collisions,
    resolve_clothing_theme,
    resolve_location_alias_map,
)
from vocab.garnish.logic import sample_garnish


def _flatten_strings(value):
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, list):
        for item in value:
            yield from _flatten_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _flatten_strings(item)


def build_report() -> Dict[str, List[dict]]:
    report = {"ERROR": [], "WARNING": [], "INFO": []}
    compatibility = load_scene_compatibility()
    backgrounds = load_background_packs()
    clothing = load_clothing_theme_map()
    characters = load_character_profiles()
    action_pools = load_action_pools()
    scene_axes = load_scene_axes()

    for name, profile in characters.items():
        costume = str(profile.get("default_costume", "")).strip()
        resolved = resolve_clothing_theme(costume)
        if costume and not resolved:
            report["ERROR"].append(
                {
                    "code": "unresolved_default_costume",
                    "character": name,
                    "default_costume": costume,
                }
            )

    for loc in compatibility.get("daily_life_locs", []):
        if loc not in backgrounds:
            report["ERROR"].append(
                {
                    "code": "missing_background_pack",
                    "location": loc,
                }
            )

    for loc in iter_location_candidates():
        if not can_generate_action_for_location(loc, compatibility):
            report["ERROR"].append(
                {
                    "code": "missing_action_generation",
                    "location": loc,
                }
            )

    structural_keys = {"posture", "hand_action", "gaze_target", "optional_micro_action", "anchor", "purpose"}
    for loc, pool in action_pools.items():
        if str(loc).startswith("_") or str(loc) == "schema_version" or not isinstance(pool, list):
            continue
        for index, item in enumerate(pool):
            text = str(item.get("text", "")) if isinstance(item, dict) else str(item)
            slots = parse_pool_action_to_slots(text, loc=loc, compat=compatibility)
            if not any(slots.get(key) for key in structural_keys):
                report["ERROR"].append(
                    {
                        "code": "unparseable_action_pool_entry",
                        "location": loc,
                        "index": index,
                        "text": text,
                    }
                )

    for alias, pack_keys in location_alias_collisions().items():
        report["WARNING"].append(
            {
                "code": "alias_collision",
                "alias": alias,
                "candidates": pack_keys,
            }
        )

    alias_map = resolve_location_alias_map()
    report["INFO"].append(
        {
            "code": "location_alias_entries",
            "count": len(alias_map),
        }
    )
    report["INFO"].append(
        {
            "code": "clothing_theme_count",
            "count": len(clothing),
        }
    )

    sample_locs = list(iter_location_candidates())[:16]
    for index, loc in enumerate(sample_locs):
        expanded_loc = expand_location_prompt(loc, seed=100 + index, mode="detailed", lighting_mode="off")
        hits = find_banned_terms(expanded_loc)
        if hits:
            report["ERROR"].append(
                {
                    "code": "banned_domain_location_output",
                    "location": loc,
                    "text": expanded_loc,
                    "domains": hits,
                }
            )

    for index, loc in enumerate(iter_location_candidates()):
        pool = action_pools.get(loc, [])
        usable_pool = [item for item in pool if not isinstance(item, str) or not item.startswith("_")]
        action_text, debug = generate_action_for_location(
            loc,
            compatibility,
            scene_axes,
            random.Random(700 + index),
            pool=usable_pool or None,
        )
        if not action_text:
            report["ERROR"].append(
                {
                    "code": "empty_generated_action",
                    "location": loc,
                }
            )
            continue
        action_hits = find_banned_terms(action_text)
        if action_hits:
            report["ERROR"].append(
                {
                    "code": "banned_domain_action_output",
                    "location": loc,
                    "text": action_text,
                    "domains": action_hits,
                }
            )
        if (
            not debug.get("slots")
            or not debug.get("slot_sources")
            or "object_focus" not in debug
            or debug.get("normalized_action") != action_text
        ):
            report["ERROR"].append(
                {
                    "code": "action_slot_contract_violation",
                    "location": loc,
                    "debug": {
                        "generator_mode": debug.get("generator_mode"),
                        "has_slots": bool(debug.get("slots")),
                        "has_slot_sources": bool(debug.get("slot_sources")),
                        "has_object_focus": "object_focus" in debug,
                        "normalized_action_matches": debug.get("normalized_action") == action_text,
                    },
                }
            )

    garnish_samples = [
        sample_garnish(41, "quiet_focused", "waiting for the next train", include_camera=True, context_loc="train_station_platform"),
        sample_garnish(42, "peaceful_relaxed", "sorting out her study materials", context_loc="school_library"),
        sample_garnish(43, "energetic_joy", "comparing a few items by the counter", context_loc="shopping_arcade"),
    ]
    for tags in garnish_samples:
        for tag in tags:
            hits = find_banned_terms(tag)
            if hits:
                report["ERROR"].append(
                    {
                        "code": "banned_domain_garnish_output",
                        "text": tag,
                        "domains": hits,
                    }
                )

    ctx = patch_context(
        {},
        updates={
            "subj": "A solo girl with black hair",
            "costume": "office_lady",
            "loc": "modern_office",
            "action": "checking what needs to be handled next",
            "seed": 77,
        },
        meta={"mood": "during a lunch break", "style": "anime watercolor"},
        extras={
            "clothing_prompt": "white blouse and navy skirt",
            "location_prompt": expand_location_prompt("modern_office", seed=77, mode="detailed", lighting_mode="off"),
            "garnish": ", ".join(sample_garnish(77, "quiet_focused", "checking what needs to be handled next", context_loc="modern_office")),
        },
    )
    _ctx, prompt = build_prompt_from_context(ctx, "", False, 77)
    prompt_hits = find_banned_terms(prompt)
    if prompt_hits:
        report["ERROR"].append(
            {
                "code": "banned_domain_prompt_output",
                "text": prompt,
                "domains": prompt_hits,
            }
        )

    return report


def main() -> int:
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
