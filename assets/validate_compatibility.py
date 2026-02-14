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

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vocab", "data")


def load_json(name: str) -> dict:
    path = os.path.join(DATA_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_prompts() -> list:
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts.jsonl")
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_exclusion_set(compat: dict) -> set:
    """除外ルールから (character, loc) ペアの set を構築"""
    excluded = set()
    for rule in compat.get("exclusions", []):
        for char in rule["characters"]:
            for loc in rule["denied_locs"]:
                excluded.add((char, loc))
    return excluded


def get_compatible_locs(char_name: str, char_info: dict, compat: dict, excluded: set) -> dict:
    """キャラの互換ロケーション一覧を返す。{loc: source} の辞書"""
    result = {}

    # 1. 汎用loc
    for loc in compat["universal_locs"]:
        if (char_name, loc) not in excluded:
            result[loc] = "universal"

    # 2. 世界観タグマッチ
    char_tags = char_info.get("tags", [])
    for tag in char_tags:
        for loc in compat["loc_tags"].get(tag, []):
            if loc not in result and (char_name, loc) not in excluded:
                result[loc] = f"tag:{tag}"

    return result


def validate():
    compat = load_json("scene_compatibility.json")
    action_pools = load_json("action_pools.json")
    bg_packs = load_json("background_packs.json")
    prompts = load_prompts()

    # 既存の prompts.jsonl 組み合わせ
    existing_combos = {(p["subj"], p["loc"]) for p in prompts}

    excluded = build_exclusion_set(compat)
    characters = compat["characters"]

    all_bg_locs = set(bg_packs.keys())
    all_combos = []
    char_combo_count = defaultdict(int)
    loc_usage = defaultdict(int)

    # --- 組み合わせ列挙 ---
    for char_name, char_info in characters.items():
        # 既存エントリ
        for subj, loc in existing_combos:
            if subj == char_name:
                all_combos.append({
                    "subj": char_name,
                    "loc": loc,
                    "source": "existing",
                    "costume": char_info["default_costume"]
                })
                char_combo_count[char_name] += 1
                loc_usage[loc] += 1

        # 互換ロケーション
        compatible = get_compatible_locs(char_name, char_info, compat, excluded)
        for loc, source in compatible.items():
            if (char_name, loc) not in existing_combos:
                all_combos.append({
                    "subj": char_name,
                    "loc": loc,
                    "source": source,
                    "costume": char_info["default_costume"]
                })
                char_combo_count[char_name] += 1
                loc_usage[loc] += 1

    # --- 検証チェック ---
    warnings = []
    errors = []

    # 1. action_pool 未定義チェック
    used_locs = {c["loc"] for c in all_combos}
    action_pool_keys = {k for k in action_pools.keys() if not k.startswith("_")}
    missing_action = used_locs - action_pool_keys
    if missing_action:
        errors.append(f"action_pools.json に定義なし: {missing_action}")

    # 2. 未使用loc
    unused_locs = all_bg_locs - {c["loc"] for c in all_combos}
    if unused_locs:
        warnings.append(f"未使用ロケーション: {unused_locs}")

    # 3. 偏りチェック（loc使用数が全キャラの80%以上）
    total_chars = len(characters)
    for loc, count in sorted(loc_usage.items(), key=lambda x: -x[1]):
        if count > total_chars * 0.8:
            warnings.append(f"偏り警告: {loc} が {count}/{total_chars} キャラに使用")

    # 4. 除外ルール検証
    exclusion_violations = [(c["subj"], c["loc"]) for c in all_combos
                            if (c["subj"], c["loc"]) in excluded]
    if exclusion_violations:
        errors.append(f"除外ルール違反: {exclusion_violations}")

    # --- 統計出力 ---
    print("=" * 60)
    print("互換性マトリクス 検証レポート")
    print("=" * 60)
    print(f"\n総構図数: {len(all_combos)}")
    print(f"  既存 (prompts.jsonl): {sum(1 for c in all_combos if c['source'] == 'existing')}")
    print(f"  タグマッチ:           {sum(1 for c in all_combos if c['source'].startswith('tag:'))}")
    print(f"  汎用loc:              {sum(1 for c in all_combos if c['source'] == 'universal')}")
    print(f"\nキャラ数: {len(characters)}")
    print(f"キャラ別平均構図数: {len(all_combos)/len(characters):.1f}")

    print(f"\n--- キャラ別構図数 ---")
    for char, count in sorted(char_combo_count.items(), key=lambda x: -x[1]):
        print(f"  {char:25s}: {count:3d}")

    print(f"\n--- loc別使用キャラ数 (Top 15) ---")
    for loc, count in sorted(loc_usage.items(), key=lambda x: -x[1])[:15]:
        print(f"  {loc:25s}: {count:3d}")

    if warnings:
        print(f"\n--- 警告 ({len(warnings)}) ---")
        for w in warnings:
            print(f"  ⚠ {w}")

    if errors:
        print(f"\n--- エラー ({len(errors)}) ---")
        for e in errors:
            print(f"  ✗ {e}")

    # --- CSV出力 ---
    csv_path = os.path.join(os.path.dirname(__file__), "compatibility_review.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["subj", "loc", "source", "costume"])
        writer.writeheader()
        writer.writerows(sorted(all_combos, key=lambda x: (x["subj"], x["source"], x["loc"])))
    print(f"\nCSV出力: {csv_path}")
    print(f"  → 人力レビュー用。不自然な組み合わせを確認してください。")

    return len(errors) == 0


if __name__ == "__main__":
    ok = validate()
    exit(0 if ok else 1)
