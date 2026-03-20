# -*- coding: utf-8 -*-
"""
verify_personality_variation.py — personality別tag分布の差異を確認する整合性チェック

Phase 0: 現状（personality未接続）の分布を記録するための基準計測スクリプト。
Phase 1実装後: personality間の top-3 tag が重複しないことを確認する。

Usage:
    python assets/verify_personality_variation.py
    python assets/verify_personality_variation.py --phase1  # Phase1後にPASS基準を適用
"""
import sys
import os
import argparse
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PERSONALITIES = ["shy", "confident", "energetic", "gloomy", "aggressive", "neutral"]
TEST_SEEDS = list(range(20))
TEST_ACTION = "standing in a room"
TEST_MOOD = "neutral"


def collect_tags(personality, seeds):
    from pipeline.context_pipeline import sample_garnish_fields

    tags_all = []
    for seed in seeds:
        garnish, _ = sample_garnish_fields(
            action_text=TEST_ACTION,
            meta_mood_key=TEST_MOOD,
            seed=seed,
            max_items=4,
            include_camera=False,
            context_loc="classroom",
            context_costume="school_uniform",
            scene_tags="{}",
            personality=personality,
        )
        tags_all.extend([t.strip() for t in garnish.split(",") if t.strip()])
    return tags_all


def main(check_diversity=False):
    print("=" * 60)
    print("  verify_personality_variation.py")
    print("  personality 別 garnish tag 分布チェック")
    print("=" * 60)

    distribution = {}
    for personality in PERSONALITIES:
        tags = collect_tags(personality, TEST_SEEDS)
        counter = Counter(tags)
        top5 = [tag for tag, _ in counter.most_common(5)]
        distribution[personality] = {
            "top5": top5,
            "total_tags": len(tags),
            "unique_tags": len(set(tags)),
            "counter": dict(counter.most_common(10))
        }
        print(f"\n[{personality}]")
        print(f"  総tag数: {len(tags)}, ユニーク数: {len(set(tags))}")
        print(f"  top-5: {top5}")

    # diversity チェック（Phase 1以降で有効）
    failed = False
    if check_diversity:
        print("\n=== Diversity Check (Phase 1 mode) ===")
        # shy と confident の top-3 が完全一致しないこと
        shy_top3 = distribution["shy"]["top5"][:3]
        conf_top3 = distribution["confident"]["top5"][:3]
        if shy_top3 == conf_top3:
            print(f"  [FAIL] shy top3 == confident top3: {shy_top3}")
            failed = True
        else:
            print(f"  [PASS] shy top3 vs confident top3: {shy_top3} vs {conf_top3}")

        # gloomy と energetic の top-3 が完全一致しないこと
        gloomy_top3 = distribution["gloomy"]["top5"][:3]
        ener_top3 = distribution["energetic"]["top5"][:3]
        if gloomy_top3 == ener_top3:
            print(f"  [FAIL] gloomy top3 == energetic top3: {gloomy_top3}")
            failed = True
        else:
            print(f"  [PASS] gloomy top3 vs energetic top3: {gloomy_top3} vs {ener_top3}")

        # 全 personality が少なくとも1つユニークなtopタグを持つこと
        all_top5_sets = [set(v["top5"]) for v in distribution.values()]
        for i, p in enumerate(PERSONALITIES):
            others = set()
            for j, s in enumerate(all_top5_sets):
                if j != i:
                    others |= s
            unique_to_p = all_top5_sets[i] - others
            if not unique_to_p:
                print(f"  [WARN] {p}: top5に固有tagなし（他と完全重複）")
            else:
                print(f"  [PASS] {p}: 固有tag={unique_to_p}")
    else:
        print("\n  [INFO] Phase 0 mode: 分布記録のみ（diversity基準は未適用）")
        print("  [INFO] Phase 1実装後は --phase1 オプションで基準チェックを実行してください")

    print("\n" + "=" * 60)
    if not failed:
        print("  [SUCCESS] verify_personality_variation passed")
        sys.exit(0)
    else:
        print("  [FAILURE] verify_personality_variation failed")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase1", action="store_true",
                        help="Phase 1実装後のdiversity基準チェックを有効化")
    args = parser.parse_args()
    main(check_diversity=args.phase1)
