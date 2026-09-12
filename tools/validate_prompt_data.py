from __future__ import annotations

import json
import random
import sys
import csv
from pathlib import Path
from typing import Any, Dict, List

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


def build_variation_source_summary() -> Dict[str, Any]:
    csv_path = ROOT / "assets" / "compatibility_review.csv"
    if not csv_path.exists():
        return {
            "variation_subject_count": 0,
            "variation_location_count": 0,
            "variation_row_count": 0,
        }

    subjects = set()
    locations = set()
    row_count = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            row_count += 1
            subject = str(row.get("subj") or "").strip()
            location = str(row.get("canonical_loc") or row.get("loc") or "").strip()
            if subject:
                subjects.add(subject)
            if location:
                locations.add(location)

    return {
        "variation_subject_count": len(subjects),
        "variation_location_count": len(locations),
        "variation_row_count": row_count,
    }


def build_expansion_summary(
    compatibility: dict,
    backgrounds: dict,
    clothing: dict,
    characters: dict,
    action_pools: dict,
    alias_map: dict,
) -> Dict[str, Any]:
    location_candidates = list(iter_location_candidates())
    action_pool_locations = sorted(
        str(key)
        for key, value in action_pools.items()
        if isinstance(key, str)
        and key.strip()
        and not key.startswith("_")
        and key != "schema_version"
        and isinstance(value, list)
    )
    action_generatable = sorted(
        loc
        for loc in location_candidates
        if can_generate_action_for_location(loc, compatibility)
    )
    dedicated_pool_missing = sorted(set(location_candidates) - set(action_pool_locations))

    return {
        "subject_count": len(characters),
        **build_variation_source_summary(),
        "compat_character_count": len(compatibility.get("characters", {})),
        "clothing_theme_count": len(clothing),
        "background_pack_count": len(backgrounds),
        "location_candidate_count": len(location_candidates),
        "daily_life_location_count": len(compatibility.get("daily_life_locs", [])),
        "universal_location_count": len(compatibility.get("universal_locs", [])),
        "action_pool_count": len(action_pool_locations),
        "action_generatable_count": len(action_generatable),
        "dedicated_action_pool_missing_count": len(dedicated_pool_missing),
        "dedicated_action_pool_missing_preview": dedicated_pool_missing[:12],
        "alias_entry_count": len(alias_map),
    }


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
    report["INFO"].append(
        {
            "code": "expansion_summary",
            **build_expansion_summary(
                compatibility,
                backgrounds,
                clothing,
                characters,
                action_pools,
                alias_map,
            ),
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
