# -*- coding: utf-8 -*-
"""
verify_refactoring.py — Prompt Builder リファクタリング回帰テスト

各フェーズ後に実行し、以下を検証する:
  1) 公開APIスナップショット（型・キー数・必須フィールド）
  2) LOC_TAG_MAP 整合性（重複・未参照・欠損）
  3) Seed 決定性（同seed→同出力）
  4) Import 時間・メモリ簡易計測

Usage:
    python verify_refactoring.py          # 全チェック
    python verify_refactoring.py --quick  # seed決定性のみ高速チェック
"""

from __future__ import annotations

# Fix Windows cp932 stdout encoding
import io
sys_module = __import__("sys")
if hasattr(sys_module.stdout, "reconfigure"):
    sys_module.stdout.reconfigure(encoding="utf-8")
elif hasattr(sys_module.stdout, "buffer"):
    sys_module.stdout = io.TextIOWrapper(sys_module.stdout.buffer, encoding="utf-8")

import argparse
import gc
import json
import os
import sys
import time
import traceback
import tracemalloc
from typing import Any, Dict, List, Set, Tuple

# ---------------------------------------------------------------------------
# Ensure we run from repo root
# ---------------------------------------------------------------------------
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_passed = 0
_failed = 0
_warned = 0


def _ok(msg: str) -> None:
    global _passed
    _passed += 1
    print(f"  [PASS] {msg}")


def _fail(msg: str) -> None:
    global _failed
    _failed += 1
    print(f"  [FAIL] {msg}")


def _warn(msg: str) -> None:
    global _warned
    _warned += 1
    print(f"  [WARN] {msg}")


# =========================================================================
# 1. API Snapshot Verification
# =========================================================================
def check_api_snapshot() -> None:
    """公開 API シンボルの型・キー数・必須フィールドを検証"""
    print("\n=== 1. API Snapshot Verification ===")

    # --- background_vocab ---
    import background_vocab as bg

    expected_bg_exports = {"CONCEPT_PACKS", "GENERAL_DEFAULTS", "LOC_TAG_MAP", "THEME_CHOICES"}
    actual_bg_exports = set(bg.__all__) if hasattr(bg, "__all__") else set()
    if expected_bg_exports <= actual_bg_exports:
        _ok(f"background_vocab.__all__ contains expected symbols: {sorted(expected_bg_exports)}")
    else:
        _fail(f"background_vocab.__all__ missing: {expected_bg_exports - actual_bg_exports}")

    if isinstance(bg.CONCEPT_PACKS, dict):
        _ok(f"background_vocab.CONCEPT_PACKS is dict, {len(bg.CONCEPT_PACKS)} packs")
    else:
        _fail("background_vocab.CONCEPT_PACKS is not a dict")

    # Check required fields per pack
    bg_required_fields = {"environment", "core", "texture", "props", "fx", "time"}
    bg_missing_fields: List[str] = []
    for pack_name, pack_data in bg.CONCEPT_PACKS.items():
        for field in bg_required_fields:
            if field not in pack_data:
                bg_missing_fields.append(f"{pack_name}.{field}")
    if not bg_missing_fields:
        _ok(f"All {len(bg.CONCEPT_PACKS)} background packs have required fields: {sorted(bg_required_fields)}")
    else:
        _fail(f"Background packs missing fields: {bg_missing_fields[:10]}")

    if isinstance(bg.GENERAL_DEFAULTS, dict):
        _ok(f"background_vocab.GENERAL_DEFAULTS is dict, keys={sorted(bg.GENERAL_DEFAULTS.keys())}")
    else:
        _fail("background_vocab.GENERAL_DEFAULTS is not a dict")

    if isinstance(bg.LOC_TAG_MAP, dict):
        _ok(f"background_vocab.LOC_TAG_MAP is dict, {len(bg.LOC_TAG_MAP)} entries")
    else:
        _fail("background_vocab.LOC_TAG_MAP is not a dict")

    if isinstance(bg.THEME_CHOICES, list):
        _ok(f"background_vocab.THEME_CHOICES is list, {len(bg.THEME_CHOICES)} items")
    else:
        _fail("background_vocab.THEME_CHOICES is not a list")

    # --- clothing_vocab ---
    import clothing_vocab as cl

    expected_cl_exports = {
        "CONCEPT_PACKS", "THEME_TO_PACKS", "THEME_CHOICES",
        "STATE_TAGS", "PALETTE_DEFAULT_PROBABILITIES",
        "OPTIONAL_DETAIL_PROBABILITY", "STATE_DETAIL_PROBABILITY",
        "OUTERWEAR_SELECTION_PROBABILITY", "EMBELLISHMENT_DETAIL_PROBABILITY",
    }
    actual_cl_exports = set(cl.__all__) if hasattr(cl, "__all__") else set()
    if expected_cl_exports <= actual_cl_exports:
        _ok(f"clothing_vocab.__all__ contains expected symbols: {len(expected_cl_exports)} items")
    else:
        _fail(f"clothing_vocab.__all__ missing: {expected_cl_exports - actual_cl_exports}")

    if isinstance(cl.CONCEPT_PACKS, dict):
        total_clothing = sum(len(v) for v in cl.CONCEPT_PACKS.values())
        _ok(f"clothing_vocab.CONCEPT_PACKS is dict, {len(cl.CONCEPT_PACKS)} categories, {total_clothing} total packs")
    else:
        _fail("clothing_vocab.CONCEPT_PACKS is not a dict")

    if isinstance(cl.THEME_TO_PACKS, dict):
        _ok(f"clothing_vocab.THEME_TO_PACKS is dict, {len(cl.THEME_TO_PACKS)} themes")
    else:
        _fail("clothing_vocab.THEME_TO_PACKS is not a dict")

    # Check clothing pack required fields
    cl_required_fields = {"core", "choices", "palette"}
    cl_missing: List[str] = []
    for category, packs in cl.CONCEPT_PACKS.items():
        for pack_name, pack_data in packs.items():
            for field in cl_required_fields:
                if field not in pack_data:
                    cl_missing.append(f"{category}.{pack_name}.{field}")
    if not cl_missing:
        _ok(f"All clothing packs have required fields: {sorted(cl_required_fields)}")
    else:
        _fail(f"Clothing packs missing fields: {cl_missing[:10]}")

    # Probability constants type check
    for const_name in ["PALETTE_DEFAULT_PROBABILITIES", "OPTIONAL_DETAIL_PROBABILITY",
                        "STATE_DETAIL_PROBABILITY", "OUTERWEAR_SELECTION_PROBABILITY",
                        "EMBELLISHMENT_DETAIL_PROBABILITY"]:
        val = getattr(cl, const_name, None)
        if val is not None:
            _ok(f"clothing_vocab.{const_name} exists, type={type(val).__name__}")
        else:
            _fail(f"clothing_vocab.{const_name} is missing")

    # --- improved_pose_emotion_vocab ---
    import improved_pose_emotion_vocab as pv

    expected_pv_exports = {"sample_garnish", "normalize"}
    actual_pv_exports = set(pv.__all__) if hasattr(pv, "__all__") else set()
    if expected_pv_exports <= actual_pv_exports:
        _ok(f"improved_pose_emotion_vocab.__all__ contains expected symbols")
    else:
        _fail(f"improved_pose_emotion_vocab.__all__ missing: {expected_pv_exports - actual_pv_exports}")

    if callable(getattr(pv, "sample_garnish", None)):
        _ok("improved_pose_emotion_vocab.sample_garnish is callable")
    else:
        _fail("improved_pose_emotion_vocab.sample_garnish is not callable")

    if callable(getattr(pv, "normalize", None)):
        _ok("improved_pose_emotion_vocab.normalize is callable")
    else:
        _fail("improved_pose_emotion_vocab.normalize is not callable")

    # Check internal data structures are present
    for attr_name in ["MOOD_POOLS", "MICRO_ACTION_CONCEPTS", "VIEW_ANGLES",
                       "VIEW_FRAMING", "EXCLUSIVE_TAG_GROUPS"]:
        if hasattr(pv, attr_name):
            obj = getattr(pv, attr_name)
            _ok(f"improved_pose_emotion_vocab.{attr_name} exists, type={type(obj).__name__}, "
                f"len={len(obj) if hasattr(obj, '__len__') else 'N/A'}")
        else:
            _warn(f"improved_pose_emotion_vocab.{attr_name} not found (may be internal)")


# =========================================================================
# 2. LOC_TAG_MAP Integrity
# =========================================================================
def check_loc_tag_map_integrity() -> None:
    """LOC_TAG_MAP の整合性チェック"""
    print("\n=== 2. LOC_TAG_MAP Integrity ===")

    import background_vocab as bg

    loc_map = bg.LOC_TAG_MAP
    concept_packs = bg.CONCEPT_PACKS

    # 2a. Check for pack references pointing to non-existent packs
    missing_packs: List[Tuple[str, str]] = []
    for loc_tag, pack_list in loc_map.items():
        for pack_key in pack_list:
            if pack_key not in concept_packs:
                missing_packs.append((loc_tag, pack_key))

    if not missing_packs:
        _ok("All LOC_TAG_MAP values reference existing CONCEPT_PACKS")
    else:
        _fail(f"LOC_TAG_MAP references {len(missing_packs)} non-existent packs: {missing_packs[:5]}")

    # 2b. Check for CONCEPT_PACKS not referenced by any LOC_TAG_MAP entry
    referenced_packs: Set[str] = set()
    for pack_list in loc_map.values():
        referenced_packs.update(pack_list)

    unreferenced = set(concept_packs.keys()) - referenced_packs
    if not unreferenced:
        _ok("All CONCEPT_PACKS are referenced by at least one LOC_TAG_MAP entry")
    else:
        _warn(f"CONCEPT_PACKS not referenced by LOC_TAG_MAP: {sorted(unreferenced)}")

    # 2c. Detect duplicate keys (Python silently uses last definition)
    # We need to parse the source file to find literal duplicates
    source_path = os.path.join(REPO_DIR, "background_vocab.py")
    if os.path.exists(source_path):
        _detect_duplicate_dict_keys(source_path, "LOC_TAG_MAP")
    else:
        # Try to find it in vocab submodule
        alt_path = os.path.join(REPO_DIR, "vocab", "background", "loc_tag_map.py")
        if os.path.exists(alt_path):
            _detect_duplicate_dict_keys(alt_path, "LOC_TAG_MAP")
        else:
            # Might be in JSON now
            json_path = os.path.join(REPO_DIR, "vocab", "data", "background_loc_tag_map.json")
            if os.path.exists(json_path):
                _ok("LOC_TAG_MAP is now in JSON (no Python duplicate key issue)")
            else:
                _warn("Could not locate LOC_TAG_MAP source for duplicate key analysis")

    # 2d. Check THEME_TO_PACKS references (clothing)
    import clothing_vocab as cl
    cl_missing: List[Tuple[str, str, str]] = []
    for theme, type_map in cl.THEME_TO_PACKS.items():
        for outfit_type, pack_names in type_map.items():
            for pn in pack_names:
                if outfit_type not in cl.CONCEPT_PACKS:
                    cl_missing.append((theme, outfit_type, pn))
                elif pn not in cl.CONCEPT_PACKS[outfit_type]:
                    cl_missing.append((theme, outfit_type, pn))

    if not cl_missing:
        _ok("All THEME_TO_PACKS references are valid in clothing_vocab")
    else:
        _fail(f"THEME_TO_PACKS references {len(cl_missing)} invalid packs: {cl_missing[:5]}")

    # 2e. LOC_TAG_MAP equivalence: hand-written vs auto-generated (Phase 4)
    try:
        from vocab.loc_tag_builder import build_loc_tag_map

        overrides_path = os.path.join(REPO_DIR, "vocab", "data", "background_alias_overrides.json")
        if os.path.exists(overrides_path):
            with open(overrides_path, "r", encoding="utf-8") as f:
                alias_overrides = json.load(f)
        else:
            alias_overrides = {}

        auto_map = build_loc_tag_map(bg.CONCEPT_PACKS, alias_overrides)

        # Compare: every key in hand-written should be in auto, with same pack list
        hand_keys = set(loc_map.keys())
        auto_keys = set(auto_map.keys())
        missing_in_auto = hand_keys - auto_keys
        extra_in_auto = auto_keys - hand_keys

        # Check value equivalence for common keys
        value_mismatches = []
        for k in hand_keys & auto_keys:
            if sorted(loc_map[k]) != sorted(auto_map[k]):
                value_mismatches.append(f"{k}: hand={loc_map[k]} vs auto={auto_map[k]}")

        if not missing_in_auto and not value_mismatches:
            _ok(f"Auto-generated LOC_TAG_MAP covers all {len(hand_keys)} hand-written entries")
        else:
            if missing_in_auto:
                _fail(f"Auto-generated LOC_TAG_MAP missing {len(missing_in_auto)} keys: {sorted(missing_in_auto)[:5]}")
            if value_mismatches:
                _fail(f"LOC_TAG_MAP value mismatches: {value_mismatches[:5]}")

        if extra_in_auto:
            # Extra keys are OK (pack keys auto-registered)
            pass
    except ImportError:
        _warn("vocab.loc_tag_builder not found, skipping equivalence test")


def _detect_duplicate_dict_keys(filepath: str, target_name: str) -> None:
    """Source-level duplicate key detection by simple line parsing."""
    import re
    duplicates: List[str] = []
    seen_keys: Dict[str, int] = {}
    in_target = False
    brace_depth = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            stripped = line.strip()

            # Detect start of target dict
            if not in_target:
                if re.match(rf"^{re.escape(target_name)}\s*[:\[]?\s*.*=\s*\{{", stripped) or \
                   re.match(rf'^{re.escape(target_name)}\s*:', stripped):
                    in_target = True
                    brace_depth = line.count("{") - line.count("}")
                continue

            brace_depth += line.count("{") - line.count("}")

            # Only count top-level keys (depth == 1)
            if brace_depth == 1:
                m = re.match(r'^\s*["\'](.+?)["\']\s*:', stripped)
                if m:
                    key = m.group(1)
                    if key in seen_keys:
                        duplicates.append(f"'{key}' (lines {seen_keys[key]} & {lineno})")
                    seen_keys[key] = lineno

            if brace_depth <= 0:
                break

    if duplicates:
        _warn(f"Duplicate keys in {target_name}: {duplicates}")
    else:
        _ok(f"No duplicate keys found in {target_name} ({len(seen_keys)} unique keys)")


# =========================================================================
# 3. Seed Determinism
# =========================================================================
def check_seed_determinism() -> None:
    """同一seed → 同一出力 を検証"""
    print("\n=== 3. Seed Determinism ===")

    from nodes_dictionary_expand import ThemeClothingExpander, ThemeLocationExpander
    from nodes_garnish import GarnishSampler

    cloth = ThemeClothingExpander()
    loc_exp = ThemeLocationExpander()
    garnish = GarnishSampler()

    test_seeds = [0, 42, 12345, 99999, 2**32 - 1]

    # Test clothing expander
    import clothing_vocab as cl
    theme_keys = list(cl.THEME_TO_PACKS.keys())[:3]

    clothing_ok = True
    for seed in test_seeds:
        for tk in theme_keys:
            r1 = cloth.expand_clothing(theme_key=tk, seed=seed, outfit_mode="random", outerwear_chance=0.3)
            r2 = cloth.expand_clothing(theme_key=tk, seed=seed, outfit_mode="random", outerwear_chance=0.3)
            if r1 != r2:
                _fail(f"ThemeClothingExpander non-deterministic: seed={seed}, theme={tk}")
                clothing_ok = False
                break
        if not clothing_ok:
            break
    if clothing_ok:
        _ok(f"ThemeClothingExpander deterministic across {len(test_seeds)} seeds × {len(theme_keys)} themes")

    # Test location expander
    import background_vocab as bg
    loc_tags = list(bg.LOC_TAG_MAP.keys())[:5]

    location_ok = True
    for seed in test_seeds:
        for lt in loc_tags:
            r1 = loc_exp.expand_location(loc_tag=lt, seed=seed, mode="detailed")
            r2 = loc_exp.expand_location(loc_tag=lt, seed=seed, mode="detailed")
            if r1 != r2:
                _fail(f"ThemeLocationExpander non-deterministic: seed={seed}, loc={lt}")
                location_ok = False
                break
        if not location_ok:
            break
    if location_ok:
        _ok(f"ThemeLocationExpander deterministic across {len(test_seeds)} seeds × {len(loc_tags)} tags")

    # Test garnish sampler
    garnish_ok = True
    test_actions = ["sitting reading a book", "running", "singing on stage"]
    test_moods = ["joy", "sadness", "neutral"]
    for seed in test_seeds:
        for action, mood in zip(test_actions, test_moods):
            r1 = garnish.sample(
                action_text=action, meta_mood_key=mood, seed=seed,
                max_items=3, include_camera=False, context_loc="classroom", context_costume="school_uniform"
            )
            r2 = garnish.sample(
                action_text=action, meta_mood_key=mood, seed=seed,
                max_items=3, include_camera=False, context_loc="classroom", context_costume="school_uniform"
            )
            if r1 != r2:
                _fail(f"GarnishSampler non-deterministic: seed={seed}, action={action}")
                garnish_ok = False
                break
        if not garnish_ok:
            break
    if garnish_ok:
        _ok(f"GarnishSampler deterministic across {len(test_seeds)} seeds × {len(test_actions)} actions")


# =========================================================================
# 4. Performance Measurement
# =========================================================================
def check_performance() -> None:
    """Import 時間・メモリの簡易計測"""
    print("\n=== 4. Performance Measurement ===")

    modules_to_test = [
        "background_vocab",
        "clothing_vocab",
        "improved_pose_emotion_vocab",
    ]

    for mod_name in modules_to_test:
        # Remove from cache to measure fresh import
        if mod_name in sys.modules:
            del sys.modules[mod_name]

        gc.collect()
        tracemalloc.start()
        t0 = time.perf_counter()

        __import__(mod_name)

        t1 = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        elapsed_ms = (t1 - t0) * 1000
        peak_kb = peak / 1024

        print(f"  [{mod_name}] import: {elapsed_ms:.1f}ms, peak memory: {peak_kb:.1f}KB")

        if elapsed_ms > 1000:
            _warn(f"{mod_name} import took > 1s ({elapsed_ms:.0f}ms)")
        else:
            _ok(f"{mod_name} import time OK ({elapsed_ms:.1f}ms)")


# =========================================================================
# 5. Cross-reference: prompts.jsonl → vocab
# =========================================================================
def check_prompts_cross_reference() -> None:
    """prompts.jsonl のキーが実際の vocab に存在するか確認"""
    print("\n=== 5. Prompts Cross-Reference ===")

    prompts_path = os.path.join(REPO_DIR, "prompts.jsonl")
    if not os.path.exists(prompts_path):
        _warn("prompts.jsonl not found, skipping cross-reference")
        return

    import background_vocab as bg
    import clothing_vocab as cl

    prompts = []
    with open(prompts_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                prompts.append(json.loads(line))

    missing_locs: Set[str] = set()
    missing_costumes: Set[str] = set()

    for p in prompts:
        loc = (p.get("loc_tag", "") or p.get("loc", "")).lower().strip()
        costume = (p.get("costume_key", "") or p.get("costume", "")).lower().strip()

        if loc and loc not in bg.LOC_TAG_MAP:
            missing_locs.add(loc)
        if costume and costume not in cl.THEME_TO_PACKS:
            missing_costumes.add(costume)

    if not missing_locs:
        _ok(f"All {len(prompts)} prompt loc_tags found in LOC_TAG_MAP")
    else:
        _warn(f"Prompts reference {len(missing_locs)} missing loc_tags: {sorted(missing_locs)}")

    if not missing_costumes:
        _ok(f"All prompt costume_keys found in THEME_TO_PACKS")
    else:
        _warn(f"Prompts reference {len(missing_costumes)} missing costume_keys (may be aliases): {sorted(missing_costumes)}")


# =========================================================================
# Main
# =========================================================================
def main() -> int:
    global _passed, _failed, _warned

    parser = argparse.ArgumentParser(description="Prompt Builder Refactoring Verification")
    parser.add_argument("--quick", action="store_true", help="Run only seed determinism check")
    args = parser.parse_args()

    print("=" * 60)
    print("  Prompt Builder — Refactoring Verification Script")
    print("=" * 60)

    try:
        if args.quick:
            check_seed_determinism()
        else:
            check_api_snapshot()
            check_loc_tag_map_integrity()
            check_seed_determinism()
            check_performance()
            check_prompts_cross_reference()
    except Exception as e:
        print(f"\n  [FATAL] Unexpected error: {e}")
        traceback.print_exc()
        return 1

    print("\n" + "=" * 60)
    print(f"  Results: {_passed} passed, {_failed} FAILED, {_warned} warnings")
    print("=" * 60)

    return 1 if _failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
