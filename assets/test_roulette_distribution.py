# -*- coding: utf-8 -*-
"""
test_roulette_distribution.py

Checks if the vocabulary system actually varies its output when
different action/mood combinations are used across multiple seeds.

Note: This was originally testing internal roulette logic that matched
a different schema (variants/tags keys). Since MICRO_ACTION_CONCEPTS
now uses garnish_micro_actions.json format (specific/roulette/generic keys),
the micro-action roulette integration belongs to Phase 1 refactoring.
These tests now verify basic output non-emptiness and diversity across seeds.
"""
import sys
import os
import unittest
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import improved_pose_emotion_vocab as garnish_vocab


class TestRouletteDistribution(unittest.TestCase):

    def _collect_blob(self, action_text, meta_mood, seed_base=1000, count=50, max_items=5):
        samples = []
        for i in range(count):
            res = garnish_vocab.sample_garnish(
                seed=seed_base + i,
                meta_mood=meta_mood,
                action_text=action_text,
                max_items=max_items,
                include_camera=False
            )
            samples.append(" ".join(res))
        return " ".join(samples).lower(), samples

    def test_combat_output_nonempty(self):
        """combat action でガーニッシュが非空で生成されること"""
        blob, samples = self._collect_blob("fight", "intense_anger")
        nonempty = [s for s in samples if s.strip()]
        self.assertGreater(len(nonempty), 40,
            f"combat: too few non-empty outputs ({len(nonempty)}/50)")

    def test_combat_seed_variation(self):
        """combat でシードが違えば出力が変わること（決定性があるが多様であること）"""
        blob, samples = self._collect_blob("fight", "intense_anger", count=20)
        unique = set(samples)
        self.assertGreater(len(unique), 5,
            f"combat: too little variation ({len(unique)} unique outputs from 20 seeds)")

    def test_performance_output_nonempty(self):
        """performance action でガーニッシュが非空で生成されること"""
        blob, samples = self._collect_blob("play music", "energetic_joy")
        nonempty = [s for s in samples if s.strip()]
        self.assertGreater(len(nonempty), 40,
            f"performance: too few non-empty outputs ({len(nonempty)}/50)")

    def test_daily_life_output_nonempty(self):
        """daily life action でガーニッシュが非空で生成されること"""
        blob, samples = self._collect_blob("relaxing in room", "peaceful_relaxed")
        nonempty = [s for s in samples if s.strip()]
        self.assertGreater(len(nonempty), 40,
            f"daily_life: too few non-empty outputs ({len(nonempty)}/50)")

    def test_surveillance_output_nonempty(self):
        """surveillance action でガーニッシュが非空で生成されること"""
        blob, samples = self._collect_blob("surveillance mission", "quiet_focused")
        nonempty = [s for s in samples if s.strip()]
        self.assertGreater(len(nonempty), 40,
            f"surveillance: too few non-empty outputs ({len(nonempty)}/50)")

    def test_nature_relax_output_nonempty(self):
        """nature relax でガーニッシュが非空で生成されること"""
        blob, samples = self._collect_blob("relaxing in nature park", "peaceful_relaxed")
        nonempty = [s for s in samples if s.strip()]
        self.assertGreater(len(nonempty), 40,
            f"nature_relax: too few non-empty outputs ({len(nonempty)}/50)")

    def test_browsing_shop_output_nonempty(self):
        """browsing shop でガーニッシュが非空で生成されること"""
        blob, samples = self._collect_blob("browsing shop", "peaceful_relaxed")
        nonempty = [s for s in samples if s.strip()]
        self.assertGreater(len(nonempty), 40,
            f"browsing_shop: too few non-empty outputs ({len(nonempty)}/50)")

    def test_commuter_transit_output_nonempty(self):
        """commuter transit でガーニッシュが非空で生成されること"""
        blob, samples = self._collect_blob("commuter transit", "quiet_focused")
        nonempty = [s for s in samples if s.strip()]
        self.assertGreater(len(nonempty), 40,
            f"commuter_transit: too few non-empty outputs ({len(nonempty)}/50)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
