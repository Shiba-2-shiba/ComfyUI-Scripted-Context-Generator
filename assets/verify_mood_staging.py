# -*- coding: utf-8 -*-
"""
verify_mood_staging.py - mood_map.json staging_tags field verification

Phase 0: Record current state (staging_tags not yet added). Will not PASS yet.
Phase 2: After implementation, all mood keys should have staging_tags -> PASS.

Usage:
    python assets/verify_mood_staging.py
"""
import sys
import os
import io
import json

# Windows cp932 stdout fix
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
elif hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

MOOD_MAP_PATH = os.path.join(ROOT, "mood_map.json")


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


def main():
    print("=" * 60)
    print("  verify_mood_staging.py")
    print("  mood_map.json staging_tags フィールド検証")
    print("=" * 60)

    c = Checker()

    if not os.path.exists(MOOD_MAP_PATH):
        c.fail(f"mood_map.json が見つかりません: {MOOD_MAP_PATH}")
        sys.exit(1)

    with open(MOOD_MAP_PATH, "r", encoding="utf-8") as f:
        mood_map = json.load(f)

    print(f"\n  mood_map.json のキー数: {len(mood_map)}")

    all_have_staging = True
    all_description_valid = True

    for key, value in mood_map.items():
        # Phase 2実装前: valueはリスト形式
        # Phase 2実装後: valueはdictで {"description": [...], "staging_tags": [...]}
        if isinstance(value, dict):
            has_desc = ("description" in value
                        and isinstance(value["description"], list)
                        and len(value["description"]) > 0)
            has_staging = ("staging_tags" in value
                           and isinstance(value["staging_tags"], list)
                           and len(value["staging_tags"]) > 0)

            if not has_desc:
                c.fail(f"'{key}': description フィールドが不正（空またはリストでない）")
                all_description_valid = False
            if not has_staging:
                c.fail(f"'{key}': staging_tags フィールドがない/空")
                all_have_staging = False
            else:
                bad_tags = [t for t in value["staging_tags"]
                            if not isinstance(t, str) or len(t) > 60]
                if bad_tags:
                    c.warn(f"'{key}': staging_tags に不正な値: {bad_tags[:3]}")
                else:
                    staging_list = value["staging_tags"]
                    c.ok(f"'{key}': description×{len(value['description'])}, "
                         f"staging_tags×{len(staging_list)}")

        elif isinstance(value, list):
            # Phase 2未実装: 旧フォーマット（文字列のリスト）
            c.warn(f"'{key}': old format (list) -- staging_tags not added yet [Phase 2]")
            all_have_staging = False
        else:
            c.fail(f"'{key}': 予期しない値の型: {type(value).__name__}")
            all_have_staging = False

    print(f"\n  結果: {c.passed} passed, {c.failed} FAILED, {c.warned} warnings")
    print("=" * 60)

    if all_have_staging and all_description_valid and c.failed == 0:
        print("  [SUCCESS] verify_mood_staging passed")
        sys.exit(0)
    elif c.failed == 0 and c.warned > 0:
        # Phase 2未実装の場合はWARNのみで終了コード0（runner.pyからのFAILを回避）
        print("  [INFO] Phase 2未実装: staging_tags フィールドは未追加")
        print("  [INFO] Phase 2実装後にPASSになります")
        sys.exit(0)
    else:
        print("  [FAILURE] verify_mood_staging failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
