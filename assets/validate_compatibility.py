# -*- coding: utf-8 -*-
"""
validate_compatibility.py
=========================
互換性マトリクスの全組み合わせを列挙し、整合性をチェックする検証スクリプト。

出力:
  - 統計サマリー（総構図数、キャラ別平均、loc別使用数）
  - 警告（未使用loc、偏り、除外ルール該当）
  - CSV出力（人力レビュー用）
"""

import json
import os
import csv
from collections import defaultdict
import math
import statistics

from registry import resolve_location_alias_map

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vocab", "data")


def load_json(name: str) -> dict:
    path = os.path.join(DATA_DIR, name)
    # Return empty dict if file not found to avoid crashing on new files if not yet created (though here they should exist)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_prompts() -> list:
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts.jsonl")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_aliases() -> dict:
    return resolve_location_alias_map()


def get_canonical_loc(loc: str, aliases: dict) -> str:
    return aliases.get(loc, loc)


def build_exclusion_set(compat: dict, aliases: dict) -> set:
    """除外ルールから (character, canonical_loc) ペアの set を構築"""
    excluded = set()
    for rule in compat.get("exclusions", []):
        for char in rule["characters"]:
            for loc in rule["denied_locs"]:
                canon = get_canonical_loc(loc, aliases)
                excluded.add((char, canon))
    return excluded


def get_compatible_locs(char_name: str, char_info: dict, compat: dict, excluded: set, aliases: dict) -> dict:
    """キャラの互換ロケーション一覧を返す。{canonical_loc: {source_type, source_tag, original_loc}} の辞書"""
    result = {}

    # 1. 汎用loc
    for loc in compat["universal_locs"]:
        canon = get_canonical_loc(loc, aliases)
        if (char_name, canon) not in excluded:
            if canon not in result: # 優先順位: 汎用は最も低いが、ベースとして追加
                 result[canon] = {"type": "universal", "tag": None, "original": loc}

    # 2. 世界観タグマッチ
    char_tags = char_info.get("tags", [])
    for tag in char_tags:
        for loc in compat["loc_tags"].get(tag, []):
            canon = get_canonical_loc(loc, aliases)
            if (char_name, canon) not in excluded:
                # タグ由来は汎用より優先されるべきだが、ループ順序的に上書きor追加
                result[canon] = {"type": "tag", "tag": tag, "original": loc}

    return result


def calculate_entropy(counts: list) -> float:
    """Shannon entropy calculation"""
    total = sum(counts)
    if total == 0:
        return 0.0
    probs = [c / total for c in counts]
    return -sum(p * math.log(p, 2) for p in probs if p > 0)


def validate():
    compat = load_json("scene_compatibility.json")
    action_pools = load_json("action_pools.json")
    bg_packs = load_json("background_packs.json")
    aliases = load_aliases()
    prompts = load_prompts()

    excluded = build_exclusion_set(compat, aliases)
    characters = compat["characters"]
    all_bg_locs = set(bg_packs.keys())
    
    # 既存の prompts.jsonl 組み合わせ (canonical化)
    existing_combos = set()
    for p in prompts:
        canon = get_canonical_loc(p["loc"], aliases)
        existing_combos.add((p["subj"], canon))

    all_combos = []
    char_loc_counts = defaultdict(int)
    loc_usage_counts = defaultdict(int)

    # --- 組み合わせ列挙 ---
    for char_name, char_info in characters.items():
        # 既存エントリ
        for subj, canon_loc in existing_combos:
            if subj == char_name:
                all_combos.append({
                    "subj": char_name,
                    "loc": canon_loc,
                    "canonical_loc": canon_loc,
                    "source": "existing",
                    "source_tag": "",
                    "is_tag": 0,
                    "is_universal": 0,
                    "is_existing": 1,
                    "is_alias": 1 if canon_loc != p["loc"] else 0, # 注意: p["loc"] はループ外なので厳密ではないが、existingはcanonical化済みとして扱う
                    "costume": char_info["default_costume"]
                })
                char_loc_counts[char_name] += 1
                loc_usage_counts[canon_loc] += 1

        # 互換ロケーション
        compatible = get_compatible_locs(char_name, char_info, compat, excluded, aliases)
        for canon, meta in compatible.items():
            if (char_name, canon) not in existing_combos:
                is_alias = 1 if canon != meta["original"] else 0
                all_combos.append({
                    "subj": char_name,
                    "loc": meta["original"],
                    "canonical_loc": canon,
                    "source": f"{meta['type']}:{meta['tag']}" if meta['tag'] else meta['type'],
                    "source_tag": meta['tag'] or "",
                    "is_tag": 1 if meta['type'] == 'tag' else 0,
                    "is_universal": 1 if meta['type'] == 'universal' else 0,
                    "is_existing": 0,
                    "is_alias": is_alias,
                    "costume": char_info["default_costume"]
                })
                char_loc_counts[char_name] += 1
                loc_usage_counts[canon] += 1

    # --- 指標計算 ---
    total_combos = len(all_combos)
    total_chars = len(characters)
    
    loc_counts_per_char = list(char_loc_counts.values())
    min_locs = min(loc_counts_per_char) if loc_counts_per_char else 0
    max_locs = max(loc_counts_per_char) if loc_counts_per_char else 0
    avg_locs = statistics.mean(loc_counts_per_char) if loc_counts_per_char else 0
    p10_locs = statistics.quantiles(loc_counts_per_char, n=10)[0] if len(loc_counts_per_char) >= 2 else min_locs # approx P10

    loc_coverage_values = [count / total_chars for count in loc_usage_counts.values()]
    max_coverage = max(loc_coverage_values) if loc_coverage_values else 0
    
    loc_entropy = calculate_entropy(list(loc_usage_counts.values()))

    # --- 検証チェック ---
    warnings = []
    errors = []

    # 1. action_pool 未定義チェック (canonical loc でチェック)
    used_canon_locs = set(loc_usage_counts.keys())
    action_pool_keys = {k for k in action_pools.keys() if not k.startswith("_")}
    missing_action = used_canon_locs - action_pool_keys
    if missing_action:
        errors.append(f"action_pools.json に定義なし (canonical): {missing_action}")

    # 2. 未使用loc (original locでチェック)
    used_original_locs = {c["loc"] for c in all_combos}
    unused_locs = all_bg_locs - used_original_locs
    if unused_locs:
        warnings.append(f"未使用ロケーション: {len(unused_locs)}件 ({list(unused_locs)[:5]}...)")

    # 3. 偏りチェック
    biased_locs = [loc for loc, count in loc_usage_counts.items() if count / total_chars > 0.8]
    if biased_locs:
        warnings.append(f"偏り警告 (>80%): {len(biased_locs)}件 ({biased_locs[:5]}...)")

    # --- ガードレールチェック ---
    guard_failures = []
    
    # Find char with min locs for reporting
    min_char = min(char_loc_counts, key=char_loc_counts.get) if char_loc_counts else "None"
    min_val = char_loc_counts[min_char] if char_loc_counts else 0
    
    if min_val < 8: # Strictly enforce 8, warn 10
        errors.append(f"[Guards] Min locs per char < 8 (Char: {min_char}, Count: {min_val})")
    elif min_val < 10:
        warnings.append(f"[Guards] Min locs per char < 10 (Char: {min_char}, Count: {min_val})")

    if max_coverage > 0.95:
         warnings.append(f"[Guards] Max coverage > 95% ({max_coverage*100:.1f}%) - Consider reducing universal locs")

    if total_combos < 600:
        errors.append(f"[Guards] Total combos too low (< 600): {total_combos}")
    
    # --- 統計出力 ---
    print("=" * 60)
    print("互換性マトリクス 検証レポート (Phase 1: Observability)")
    print("=" * 60)
    print(f"\n[Basic Stats]")
    print(f"  Total Combos: {total_combos}")
    print(f"  Total Chars:  {total_chars}")
    print(f"  Action Pool Errors: {len(missing_action)}")
    print(f"  Unused Locs: {len(unused_locs)}")
    
    print(f"\n[Distribution Metrics]")
    print(f"  Locs per Char: Min={min_locs}, Max={max_locs}, Avg={avg_locs:.1f}, P10={p10_locs:.1f}")
    print(f"  Max Loc Coverage: {max_coverage*100:.1f}%")
    print(f"  Loc Entropy: {loc_entropy:.4f}")

    if warnings:
        print(f"\n[Warnings] ({len(warnings)})")
        for w in warnings:
            print(f"  ⚠ {w}")

    if errors:
        print(f"\n[Errors] ({len(errors)})")
        for e in errors:
            print(f"  ✗ {e}")
            
    if guard_failures:
        print(f"\n[Guardrail Failures] (Reference)")
        for g in guard_failures:
            print(f"  ! {g}")

    # --- CSV出力 ---
    csv_path = os.path.join(os.path.dirname(__file__), "compatibility_review.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = ["subj", "loc", "canonical_loc", "source", "source_tag", 
                      "is_tag", "is_universal", "is_existing", "is_alias", "costume"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(all_combos, key=lambda x: (x["subj"], x["canonical_loc"])))
    print(f"\nCSV出力: {csv_path}")

    return len(errors) == 0


if __name__ == "__main__":
    ok = validate()
    exit(0 if ok else 1)
