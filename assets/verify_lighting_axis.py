# -*- coding: utf-8 -*-
"""
verify_lighting_axis.py — 光源・時間帯軸の検証スクリプト

Phase 0: background_packs.json に lighting フィールドが存在しないことを記録。
Phase 3実装後: 各パックにlightingフィールドが存在し、ThemeLocationExpanderが
              lighting_modeパラメータで光源情報を出力に含めることを確認する。

Usage:
    python assets/verify_lighting_axis.py
"""
import sys
import os
import json
import inspect

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

BG_PACKS_PATH = os.path.join(ROOT, "vocab", "data", "background_packs.json")
TEST_LOC_TAGS = ["classroom", "cafe", "park", "office", "beach"]


class Checker:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warned = 0

    def ok(self, msg):
        self.passed += 1
        print(f"  [PASS] {msg}")

    def fail(self, msg):
        self.failed += 1
        print(f"  [FAIL] {msg}")

    def warn(self, msg):
        self.warned += 1
        print(f"  [WARN] {msg}")


def check_lighting_field_in_packs(c):
    """background_packs.jsonの各パックにlightingフィールドが存在するか確認"""
    print("\n=== 1. background_packs.json lighting フィールドチェック ===")

    if not os.path.exists(BG_PACKS_PATH):
        c.fail(f"background_packs.json が見つかりません: {BG_PACKS_PATH}")
        return False

    with open(BG_PACKS_PATH, "r", encoding="utf-8") as f:
        packs = json.load(f)

    total = len(packs)
    has_lighting = [k for k, v in packs.items()
                    if "lighting" in v and isinstance(v["lighting"], list) and v["lighting"]]
    no_lighting = [k for k in packs if k not in has_lighting]

    if not no_lighting:
        c.ok(f"全 {total} パックに lighting フィールドが存在します")
        return True
    elif has_lighting:
        ratio = len(has_lighting) / total
        c.warn(f"lighting フィールドがあるパック: {len(has_lighting)}/{total} ({ratio:.0%})")
        c.warn(f"lighting未対応パック（先頭5件）: {no_lighting[:5]}")
        return False
    else:
        c.warn(f"lighting フィールドが全パックに未追加 [Phase 3で対応予定]")
        return False


def check_location_expander_lighting_mode(c):
    """ThemeLocationExpanderがlighting_modeパラメータを受け付けるか確認"""
    print("\n=== 2. ThemeLocationExpander lighting_mode パラメータチェック ===")

    from nodes_dictionary_expand import ThemeLocationExpander
    node = ThemeLocationExpander()

    sig = inspect.signature(node.expand_location)
    params = list(sig.parameters.keys())

    if "lighting_mode" in params:
        c.ok(f"ThemeLocationExpander.expand_location() に lighting_mode パラメータあり")

        from background_vocab import LOC_TAG_MAP
        test_locs = [loc for loc in TEST_LOC_TAGS if loc in LOC_TAG_MAP][:3]

        for loc in test_locs:
            outputs = set()
            for seed in range(5):
                out = node.expand_location(loc_tag=loc, seed=seed,
                                           mode="detailed", lighting_mode="auto")
                outputs.add(out[0])
            if len(outputs) > 1:
                c.ok(f"  {loc}: lighting_mode=auto で複数バリエーションあり ({len(outputs)} 種)")
            else:
                c.warn(f"  {loc}: lighting_mode=auto でも出力が単一 — lightingフィールド要確認")
        return True
    else:
        c.warn(f"ThemeLocationExpander.expand_location() に lighting_mode パラメータなし [Phase 3で対応予定]")
        c.warn(f"  現在のパラメータ: {params}")
        return False


def check_lighting_variation(c):
    """光源モードによる出力バリエーションを確認（Phase 3実装後のみ有意）"""
    print("\n=== 3. 光源バリエーション確認 ===")

    from nodes_dictionary_expand import ThemeLocationExpander
    node = ThemeLocationExpander()

    sig = inspect.signature(node.expand_location)
    if "lighting_mode" not in sig.parameters:
        c.warn("lighting_mode パラメータ未実装のためスキップ [Phase 3待ち]")
        return True

    from background_vocab import LOC_TAG_MAP
    test_locs = [loc for loc in TEST_LOC_TAGS if loc in LOC_TAG_MAP][:3]

    for loc in test_locs:
        out_auto = node.expand_location(loc_tag=loc, seed=42,
                                        mode="detailed", lighting_mode="auto")[0]
        out_off = node.expand_location(loc_tag=loc, seed=42,
                                       mode="detailed", lighting_mode="off")[0]
        if out_auto != out_off:
            c.ok(f"  {loc}: auto vs off で出力が異なる（光源情報が付加されている）")
        else:
            c.warn(f"  {loc}: auto と off の出力が同一（lightingデータを確認してください）")

    return True


def main():
    print("=" * 60)
    print("  verify_lighting_axis.py")
    print("  光源・時間帯軸の検証")
    print("=" * 60)

    c = Checker()

    lighting_in_packs = check_lighting_field_in_packs(c)
    lighting_mode_supported = check_location_expander_lighting_mode(c)
    check_lighting_variation(c)

    print(f"\n  結果: {c.passed} passed, {c.failed} FAILED, {c.warned} warnings")
    print("=" * 60)

    if c.failed > 0:
        print("  [FAILURE] verify_lighting_axis failed")
        sys.exit(1)
    elif not lighting_in_packs or not lighting_mode_supported:
        print("  [INFO] Phase 3未実装: lighting フィールド/パラメータは未追加")
        print("  [INFO] Phase 3実装後に全 PASS になります")
        sys.exit(0)  # Phase 3実装前はPASS扱い
    else:
        print("  [SUCCESS] verify_lighting_axis passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
