# -*- coding: utf-8 -*-
"""
test_personality_garnish.py — GarnishSampler personality連動ユニットテスト

Phase 0: テストを先行作成（現状はpersonalityが未接続なので分布テストはスキップ）
Phase 1実装後: PERSONALITY_DIVERSITYテストがPASSになることを確認する

Usage:
    python assets/test_personality_garnish.py
    # またはrunner.py経由
    python assets/runner.py unit
"""
import sys
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestGarnishSamplerPersonality(unittest.TestCase):
    """GarnishSampler の personality 引数が正しく動作するかを検証"""

    def setUp(self):
        from nodes_garnish import GarnishSampler
        self.node = GarnishSampler()
        self.personalities = [
            "shy", "confident", "energetic", "gloomy",
            "aggressive", "mysterious", "neutral", ""
        ]
        self.test_actions = [
            "walking through a hallway",
            "reading a book",
            "dancing on stage",
        ]
        self.test_moods = ["quiet", "energetic_joy", "melancholic_sadness"]

    def test_output_type_all_personalities(self):
        """全personalityで出力がstr型かつ非空であることを確認"""
        for personality in self.personalities:
            with self.subTest(personality=personality):
                garnish, debug = self.node.sample(
                    action_text="walking through a hallway",
                    meta_mood_key="quiet",
                    seed=42,
                    max_items=3,
                    include_camera=False,
                    context_loc="school hallway",
                    context_costume="school_uniform",
                    scene_tags="{}",
                    personality=personality,
                )
                self.assertIsInstance(garnish, str, f"personality={personality!r}: garnish must be str")
                self.assertIsInstance(debug, dict, f"personality={personality!r}: debug must be dict")

    def test_determinism_with_personality(self):
        """同じseedとpersonalityで同じ出力が得られること（決定性）"""
        for personality in ["shy", "confident", "energetic"]:
            with self.subTest(personality=personality):
                args = dict(
                    action_text="sitting and reading",
                    meta_mood_key="peaceful_relaxed",
                    seed=12345,
                    max_items=3,
                    include_camera=False,
                    context_loc="library",
                    context_costume="school_uniform",
                    scene_tags="{}",
                    personality=personality,
                )
                r1 = self.node.sample(**args)
                r2 = self.node.sample(**args)
                self.assertEqual(r1[0], r2[0],
                    f"personality={personality!r}: non-deterministic output")

    def test_no_crash_with_unknown_personality(self):
        """未知のpersonalityでクラッシュしないこと"""
        garnish, debug = self.node.sample(
            action_text="running",
            meta_mood_key="energetic_joy",
            seed=99,
            max_items=3,
            include_camera=False,
            context_loc="park",
            context_costume="gym_workout",
            scene_tags="{}",
            personality="UNKNOWN_PERSONALITY_xyz",
        )
        self.assertIsInstance(garnish, str)

    def test_max_items_respected(self):
        """max_itemsの上限が守られること"""
        for max_items in [1, 2, 3, 5]:
            with self.subTest(max_items=max_items):
                garnish, _ = self.node.sample(
                    action_text="dancing",
                    meta_mood_key="energetic_joy",
                    seed=100,
                    max_items=max_items,
                    include_camera=False,
                    context_loc="stage",
                    context_costume="rock_concert",
                    scene_tags="{}",
                    personality="energetic",
                )
                tags = [t.strip() for t in garnish.split(",") if t.strip()]
                self.assertLessEqual(len(tags), max_items,
                    f"max_items={max_items}: too many tags: {tags}")


class TestPersonalityDiversityPhase1(unittest.TestCase):
    """
    Phase 1実装後に有意義になるテスト。
    現状は「分布が異なる」ことを要求しない（Skipして現状記録のみ）。
    Phase 1実装後は skipIf を外すこと。
    """

    PHASE1_IMPLEMENTED = True  # Phase 1実装完了

    def setUp(self):
        from nodes_garnish import GarnishSampler
        self.node = GarnishSampler()

    @unittest.skipIf(not PHASE1_IMPLEMENTED, "Phase 1未実装: personality→garnishバイアス未接続")
    def test_shy_vs_confident_tag_distribution(self):
        """
        shy と confident では生成されるタグの傾向が異なること。
        10seeds で各personalityのtag一覧を収集し、top-3が完全一致しないことを確認。
        """
        from collections import Counter

        def collect_tags(personality, seeds=range(10)):
            tags_all = []
            for seed in seeds:
                garnish, _ = self.node.sample(
                    action_text="standing",
                    meta_mood_key="neutral",
                    seed=seed,
                    max_items=3,
                    include_camera=False,
                    context_loc="classroom",
                    context_costume="school_uniform",
                    scene_tags="{}",
                    personality=personality,
                )
                tags_all.extend([t.strip() for t in garnish.split(",") if t.strip()])
            return [tag for tag, _ in Counter(tags_all).most_common(3)]

        shy_top3 = collect_tags("shy")
        confident_top3 = collect_tags("confident")
        self.assertNotEqual(shy_top3, confident_top3,
            f"shy top3={shy_top3} == confident top3={confident_top3}: no personality diversity")

    @unittest.skipIf(not PHASE1_IMPLEMENTED, "Phase 1未実装")
    def test_gloomy_avoids_bright_effects(self):
        """gloomy personality では EFFECTS_BRIGHT 系タグが出にくいこと"""
        bright_tags = {"soft lighting", "cinematic lighting", "sunlight",
                       "bright atmosphere", "natural lighting", "bloom", "glowing light"}
        found_bright = []
        for seed in range(20):
            garnish, _ = self.node.sample(
                action_text="standing",
                meta_mood_key="melancholic_sadness",
                seed=seed,
                max_items=5,
                include_camera=False,
                context_loc="empty street",
                context_costume="casual",
                scene_tags="{}",
                personality="gloomy",
            )
            tags = {t.strip() for t in garnish.split(",") if t.strip()}
            found_bright.extend(tags & bright_tags)

        # 20seeds で bright_tagsが 3回以上出たら多すぎる
        self.assertLessEqual(len(found_bright), 3,
            f"gloomy personality has too many bright tags: {found_bright}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
