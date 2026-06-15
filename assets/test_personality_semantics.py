import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestPersonalitySemantics(unittest.TestCase):
    def test_shy_prefers_restrained_descriptors(self):
        from vocab.personality_semantics import rank_personality_descriptors

        ranked = rank_personality_descriptors(
            "shy",
            "gaze",
            ["looking directly ahead", "looking slightly away"],
        )

        self.assertEqual(ranked[0]["text"], "looking slightly away")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])

    def test_confident_prefers_direct_upright_descriptors(self):
        from vocab.personality_semantics import rank_personality_descriptors

        ranked = rank_personality_descriptors(
            "confident",
            "posture",
            ["shoulders drawn inward", "open posture"],
        )

        self.assertEqual(ranked[0]["text"], "open posture")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])

    def test_serious_prefers_focused_descriptor(self):
        from vocab.personality_semantics import rank_personality_descriptors

        ranked = rank_personality_descriptors(
            "serious",
            "gaze",
            ["looking slightly away", "focused gaze"],
        )

        self.assertEqual(ranked[0]["text"], "focused gaze")

    def test_neutral_has_no_forced_prefer_category(self):
        from vocab.personality_semantics import prefer_category_for_personality

        self.assertIsNone(prefer_category_for_personality("neutral"))

    def test_unknown_personality_returns_empty_ranking(self):
        from vocab.personality_semantics import rank_personality_descriptors

        self.assertEqual(rank_personality_descriptors("unknown", "gaze"), [])


if __name__ == "__main__":
    unittest.main()
