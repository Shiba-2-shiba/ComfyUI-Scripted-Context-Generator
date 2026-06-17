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

    def test_ranked_personality_candidate_stream_is_ordered(self):
        from vocab.personality_semantics import ranked_personality_candidate_stream

        stream = ranked_personality_candidate_stream("shy")

        self.assertGreaterEqual(len(stream), 3)
        self.assertEqual(stream[0]["rank"], 1)
        self.assertGreaterEqual(stream[0]["score"], stream[1]["score"])
        self.assertIn(stream[0]["role"], {"gaze", "posture", "hands"})

    def test_pick_personality_descriptor_tries_next_candidate_after_reject(self):
        import random
        from vocab.personality_semantics import pick_personality_descriptor, ranked_personality_candidate_stream

        stream = ranked_personality_candidate_stream("shy")
        rejected_text = stream[0]["text"]
        debug = {}
        selected = pick_personality_descriptor(
            "shy",
            random.Random(1),
            reject_fn=lambda text: "blocked" if text == rejected_text else "",
            debug=debug,
        )

        self.assertNotEqual(selected, rejected_text)
        self.assertEqual(debug["rejected_candidates"][0]["text"], rejected_text)
        self.assertEqual(debug["selected_candidate_rank"], 2)

    def test_pick_personality_descriptor_returns_empty_when_all_rejected(self):
        import random
        from vocab.personality_semantics import pick_personality_descriptor

        debug = {}
        selected = pick_personality_descriptor(
            "shy",
            random.Random(1),
            reject_fn=lambda _text: "blocked",
            debug=debug,
        )

        self.assertEqual(selected, "")
        self.assertIsNone(debug["selected_candidate_rank"])
        self.assertTrue(debug["rejected_candidates"])


if __name__ == "__main__":
    unittest.main()
