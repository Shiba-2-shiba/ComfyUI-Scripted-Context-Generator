# -*- coding: utf-8 -*-
"""
test_personality_garnish.py — context garnish stage personality連動ユニットテスト

Phase 0: テストを先行作成（現状はpersonalityが未接続なので分布テストはスキップ）
Phase 1実装後: PERSONALITY_DIVERSITYテストがPASSになることを確認する

Usage:
    python assets/test_personality_garnish.py
"""
import sys
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestContextGarnishPersonality(unittest.TestCase):
    """context garnish stage の personality 引数が正しく動作するかを検証"""

    def setUp(self):
        from pipeline.context_pipeline import sample_garnish_fields
        self.sample_garnish = sample_garnish_fields
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

    def test_visual_inspection_keeps_action_attention_authoritative(self):
        from vocab.garnish.logic import _is_out_of_context

        for action in (
            "studying fresh tracks across the cabin floor",
            "reading a notice attached above the doorway",
            "examining a loose screw on the workbench",
            "inspecting a crack in the ceiling",
        ):
            for tag in ("looking directly ahead", "attention locked forward", "looking slightly away"):
                with self.subTest(action=action, tag=tag):
                    self.assertTrue(_is_out_of_context(tag, "", "", action))
            for tag in ("focused gaze", "steady gaze", "eyes fixed on what she is doing", "calm expression"):
                with self.subTest(action=action, tag=tag):
                    self.assertFalse(_is_out_of_context(tag, "", "", action))
        for action in ("walking along the path", "carrying a closed book", "discussing a reading assignment"):
            self.assertFalse(_is_out_of_context("looking directly ahead", "", "", action))
        self.assertTrue(_is_out_of_context("looking directly ahead", "", "", "looking down at her shoes"))

    def test_confident_personality_does_not_override_inspection_gaze(self):
        args = dict(action_text="studying fresh tracks across the cabin floor",
                    meta_mood_key="quiet_focused", seed=0, max_items=3, include_camera=False,
                    context_loc="forest_cabin", context_costume="cozy_cafe", scene_tags="{}", personality="confident")
        first = self.sample_garnish(**args)
        self.assertEqual(first, self.sample_garnish(**args))
        self.assertNotIn("looking directly ahead", first[0])
        self.assertTrue(first[0])

    def test_elevated_visual_targets_exclude_downward_gaze_in_any_slot(self):
        from vocab.garnish.logic import _is_out_of_context

        for action in (
            "checking the skyline beyond the tables",
            "watching the horizon from the terrace",
            "inspecting the ceiling for cracks",
            "looking up at the clouds",
        ):
            for tag in ("downcast eyes", "looking down"):
                with self.subTest(action=action, tag=tag):
                    self.assertTrue(_is_out_of_context(tag, "", "", action))
            for tag in ("focused gaze", "steady gaze", "soft eyes", "faint frown", "calm expression"):
                with self.subTest(action=action, tag=tag):
                    self.assertFalse(_is_out_of_context(tag, "", "", action))

        for action in (
            "checking the bill while waiting near the table",
            "reading a rain gauge beside the garden bed",
            "reading a book about the skyline",
            "checking a sky chart on the table",
            "standing beside the rooftop rail",
        ):
            with self.subTest(action=action):
                self.assertFalse(_is_out_of_context("downcast eyes", "rooftop_cafe", "", action))

    def test_skyline_action_does_not_receive_gloomy_downcast_eyes(self):
        for mood in ("peaceful_relaxed", "melancholic_sadness"):
            for seed in range(8):
                args = dict(action_text="checking the skyline beyond the tables",
                            meta_mood_key=mood, seed=seed, max_items=3, include_camera=False,
                            context_loc="rooftop_cafe", context_costume="casual",
                            scene_tags="{}", personality="gloomy")
                with self.subTest(mood=mood, seed=seed):
                    first = self.sample_garnish(**args)
                    self.assertEqual(first, self.sample_garnish(**args))
                    self.assertNotIn("downcast eyes", first[0])
                    self.assertNotIn("looking down", first[0])
                    self.assertTrue(first[0])

    def test_output_type_all_personalities(self):
        """全personalityで出力がstr型かつ非空であることを確認"""
        for personality in self.personalities:
            with self.subTest(personality=personality):
                garnish, debug = self.sample_garnish(
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
                r1 = self.sample_garnish(**args)
                r2 = self.sample_garnish(**args)
                self.assertEqual(r1[0], r2[0],
                    f"personality={personality!r}: non-deterministic output")

    def test_no_crash_with_unknown_personality(self):
        """未知のpersonalityでクラッシュしないこと"""
        garnish, debug = self.sample_garnish(
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

    def test_personality_behavior_active_debug_is_recorded(self):
        garnish, debug = self.sample_garnish(
            action_text="standing near the classroom door",
            meta_mood_key="quiet_focused",
            seed=42,
            max_items=3,
            include_camera=False,
            context_loc="school_classroom",
            context_costume="school_uniform",
            scene_tags="{}",
            personality="shy",
        )
        decision = debug.get("decision", {})
        personality_debug = decision["semantic_epig"]["personality_behavior"]

        self.assertIsInstance(garnish, str)
        self.assertEqual(personality_debug["mode"], "active")
        self.assertEqual(personality_debug["personality"], "shy")
        self.assertEqual(personality_debug["prefer_category"], "care")
        self.assertTrue(personality_debug["selected_by_semantic"])
        self.assertTrue(personality_debug["semantic_scoring_enabled"])
        self.assertFalse(personality_debug["fallback_used"])
        self.assertEqual(personality_debug["rejected_candidates"], [])
        self.assertIsNotNone(personality_debug["selected_candidate_rank"])
        self.assertIn("gaze", personality_debug["slot_rankings"])
        self.assertEqual(
            personality_debug["subject_centric_overrides"]["adoption_state"],
            "active_candidate_selection",
        )
        self.assertGreaterEqual(
            personality_debug["subject_centric_overrides"]["available_count"],
            1,
        )
        self.assertTrue(personality_debug["selected"])
        if personality_debug.get("selected_candidate_role") == "subject_centric_override":
            override_tags = {
                item["text"]
                for item in personality_debug["subject_centric_overrides"]["candidates"]
            }
            self.assertEqual(personality_debug["selected_candidate_rank"], 0)
            self.assertIn(personality_debug["selected"], override_tags)
        else:
            ranked_tags = {
                item["text"]
                for ranking in personality_debug["slot_rankings"].values()
                for item in ranking[:1]
            }
            self.assertIn(personality_debug["selected"], ranked_tags)

    def test_max_items_respected(self):
        """max_itemsの上限が守られること"""
        for max_items in [1, 2, 3, 5]:
            with self.subTest(max_items=max_items):
                garnish, _ = self.sample_garnish(
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

    def test_active_actions_exclude_stillness_posture_tags(self):
        stillness_tags = {"still posture", "body held carefully still", "lingering in stillness"}
        for seed in range(32):
            garnish, _ = self.sample_garnish(
                action_text="carrying harvested vegetables toward the tool shed",
                meta_mood_key="quiet_focused",
                seed=seed,
                max_items=3,
                include_camera=False,
                context_loc="community_garden",
                context_costume="casual",
                scene_tags="{}",
                personality="mysterious",
            )
            tags = {tag.strip() for tag in garnish.split(",") if tag.strip()}
            self.assertTrue(stillness_tags.isdisjoint(tags), msg=f"seed={seed}: {garnish}")

    def test_action_load_keywords_require_word_boundaries(self):
        _garnish, debug = self.sample_garnish(
            action_text="matching seed packets to the labeled beds",
            meta_mood_key="peaceful_relaxed",
            seed=0,
            max_items=3,
            include_camera=False,
            context_loc="community_garden",
            context_costume="mori_natural",
            scene_tags="{}",
            personality="mysterious",
        )
        decision = debug.get("decision", debug)
        self.assertEqual(decision["action_load"], "calm")

    def test_calm_task_actions_use_at_most_two_non_generic_garnish_tags(self):
        for action_text in (
            "checking condensation on a chilled glass",
            "reading a service note on a clipboard",
            "inspecting a tray of newly germinated seeds",
            "matching seed packets to the labeled beds",
        ):
            for seed in range(16):
                garnish, _debug = self.sample_garnish(
                    action_text=action_text,
                    meta_mood_key="energetic_joy",
                    seed=seed,
                    max_items=3,
                    include_camera=False,
                    context_loc="modern_office",
                    context_costume="office_lady",
                    scene_tags="{}",
                    personality="mysterious",
                )
                tags = [tag.strip() for tag in garnish.split(",") if tag.strip()]
                self.assertLessEqual(len(tags), 2, msg=f"seed={seed}, {action_text}: {garnish}")
                self.assertNotIn("holding herself with easy energy", tags)


class TestPersonalityDiversityPhase1(unittest.TestCase):
    """
    Phase 1実装後に有意義になるテスト。
    現状は「分布が異なる」ことを要求しない（Skipして現状記録のみ）。
    Phase 1実装後は skipIf を外すこと。
    """

    PHASE1_IMPLEMENTED = True  # Phase 1実装完了

    def setUp(self):
        from pipeline.context_pipeline import sample_garnish_fields
        self.sample_garnish = sample_garnish_fields

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
                garnish, _ = self.sample_garnish(
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
            garnish, _ = self.sample_garnish(
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
