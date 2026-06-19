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

    def test_subject_centric_descriptor_options_are_gated_and_personality_scoped(self):
        from vocab.personality_semantics import subject_centric_descriptor_debug_payload, subject_centric_descriptor_options

        shy_options = subject_centric_descriptor_options("shy")
        confident_options = subject_centric_descriptor_options("confident")
        active_options = subject_centric_descriptor_options("shy", modes={"active"}, mood_key="focus")
        debug = subject_centric_descriptor_debug_payload("shy")

        self.assertIn("downcast eyes", {item["text"] for item in shy_options})
        self.assertNotIn("downcast eyes", {item["text"] for item in confident_options})
        self.assertEqual([item["text"] for item in active_options], ["downcast eyes"])
        self.assertEqual(
            [item["text"] for item in subject_centric_descriptor_options("mysterious", modes={"active"}, mood_key="focus")],
            ["curious eyes"],
        )
        self.assertEqual(debug["adoption_state"], "active_candidate_selection")
        self.assertGreaterEqual(debug["available_count"], 1)
        self.assertEqual(debug["mode_counts"], {"active": debug["available_count"]})
        self.assertEqual(debug["mode"], "active")

    def test_subject_centric_descriptor_options_respect_optional_mood_keys(self):
        from vocab import personality_semantics

        original_loader = personality_semantics.load_subject_centric_descriptor_overrides
        try:
            personality_semantics.load_subject_centric_descriptor_overrides = lambda: {
                "schema_version": "1.0",
                "descriptors": [
                    {
                        "id": "fixture_mood_override",
                        "personality": ["shy"],
                        "mood_keys": ["moved"],
                        "slot": "hands",
                        "text": "fixture hands near face",
                        "mode": "active",
                        "source_hint": ["fixture"],
                    }
                ],
            }

            moved_options = personality_semantics.subject_centric_descriptor_options(
                "shy",
                modes={"active"},
                mood_key="moved",
            )
            focus_options = personality_semantics.subject_centric_descriptor_options(
                "shy",
                modes={"active"},
                mood_key="focus",
            )
        finally:
            personality_semantics.load_subject_centric_descriptor_overrides = original_loader

        self.assertEqual([item["text"] for item in moved_options], ["fixture hands near face"])
        self.assertEqual(focus_options, [])

    def test_ranked_personality_candidate_stream_is_ordered(self):
        from vocab.personality_semantics import ranked_personality_candidate_stream

        stream = ranked_personality_candidate_stream("shy")

        self.assertGreaterEqual(len(stream), 3)
        self.assertEqual(stream[0]["rank"], 1)
        self.assertGreaterEqual(stream[0]["score"], stream[1]["score"])
        self.assertIn(stream[0]["role"], {"gaze", "posture", "hands"})

    def test_pick_personality_descriptor_tries_next_candidate_after_reject(self):
        import random
        from vocab import personality_semantics

        stream = personality_semantics.ranked_personality_candidate_stream("shy")
        rejected_text = stream[0]["text"]
        original_mode = personality_semantics.subject_centric_override_mode
        personality_semantics.subject_centric_override_mode = lambda: "off"
        debug = {}
        try:
            selected = personality_semantics.pick_personality_descriptor(
                "shy",
                random.Random(1),
                reject_fn=lambda text: "blocked" if text == rejected_text else "",
                debug=debug,
            )
        finally:
            personality_semantics.subject_centric_override_mode = original_mode

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

    def test_pick_personality_descriptor_without_reject_fn_keeps_rng_path(self):
        import random
        from vocab.personality_semantics import pick_personality_descriptor

        debug = {}
        selected = pick_personality_descriptor(
            "gentle",
            random.Random(1),
            debug=debug,
        )

        self.assertIsInstance(selected, str)
        self.assertTrue(selected)
        self.assertIn(selected, debug["candidate_options"])

    def test_active_subject_centric_override_can_be_selected_behind_gate(self):
        import random
        from vocab import personality_semantics

        original_mode = personality_semantics.subject_centric_override_mode
        original_loader = personality_semantics.load_subject_centric_descriptor_overrides
        try:
            personality_semantics.subject_centric_override_mode = lambda: "active"
            personality_semantics.load_subject_centric_descriptor_overrides = lambda: {
                "schema_version": "1.0",
                "descriptors": [
                    {
                        "id": "fixture_active_override",
                        "personality": ["shy"],
                        "slot": "gaze",
                        "text": "fixture active downcast eyes",
                        "mode": "active",
                        "source_hint": ["fixture"],
                    }
                ],
            }
            debug = {}
            selected = personality_semantics.pick_personality_descriptor(
                "shy",
                random.Random(1),
                reject_fn=lambda _text: "",
                debug=debug,
            )
        finally:
            personality_semantics.subject_centric_override_mode = original_mode
            personality_semantics.load_subject_centric_descriptor_overrides = original_loader

        self.assertEqual(selected, "fixture active downcast eyes")
        self.assertEqual(debug["selected_candidate_role"], "subject_centric_override")
        self.assertEqual(debug["selected_candidate_rank"], 0)
        self.assertEqual(debug["subject_centric_override_selected"]["id"], "fixture_active_override")

    def test_active_subject_centric_override_respects_reject_context_terms(self):
        import random
        from vocab import personality_semantics

        original_mode = personality_semantics.subject_centric_override_mode
        original_loader = personality_semantics.load_subject_centric_descriptor_overrides
        try:
            personality_semantics.subject_centric_override_mode = lambda: "active"
            personality_semantics.load_subject_centric_descriptor_overrides = lambda: {
                "schema_version": "1.0",
                "descriptors": [
                    {
                        "id": "fixture_active_context_reject",
                        "personality": ["gentle"],
                        "slot": "posture",
                        "text": "fixture relaxed posture",
                        "mode": "active",
                        "source_hint": ["fixture"],
                        "reject_context_terms": ["running"],
                    }
                ],
            }
            debug = {}
            selected = personality_semantics.pick_personality_descriptor(
                "gentle",
                random.Random(1),
                action_text="running along the path",
                reject_fn=lambda _text: "",
                debug=debug,
            )
        finally:
            personality_semantics.subject_centric_override_mode = original_mode
            personality_semantics.load_subject_centric_descriptor_overrides = original_loader

        self.assertNotEqual(selected, "fixture relaxed posture")
        self.assertEqual(
            debug["subject_centric_override_rejected"][0]["reason"],
            "reject_context_term:running",
        )

    def test_mood_specific_active_override_takes_priority_for_matching_mood(self):
        import random
        from vocab import personality_semantics

        moved_debug = {}
        moved_selected = personality_semantics.pick_personality_descriptor(
            "shy",
            random.Random(1),
            mood_key="moved",
            action_text="waiting with a letter in her hand",
            reject_fn=lambda _text: "",
            debug=moved_debug,
        )
        focus_debug = {}
        focus_selected = personality_semantics.pick_personality_descriptor(
            "shy",
            random.Random(1),
            mood_key="focus",
            action_text="standing near the classroom door",
            reject_fn=lambda _text: "",
            debug=focus_debug,
        )

        self.assertEqual(moved_selected, "fingers resting near her lips")
        self.assertEqual(moved_debug["subject_centric_override_selected"]["id"], "sc_hands_touching_lips_01")
        self.assertEqual(focus_selected, "downcast eyes")
        self.assertEqual(focus_debug["subject_centric_override_selected"]["id"], "sc_gaze_downcast_01")

    def test_calm_active_override_is_mood_gated(self):
        import random
        from vocab import personality_semantics

        calm_debug = {}
        calm_selected = personality_semantics.pick_personality_descriptor(
            "neutral",
            random.Random(1),
            mood_key="calm",
            action_text="standing quietly by the railing",
            reject_fn=lambda _text: "",
            debug=calm_debug,
        )
        tense_debug = {}
        tense_selected = personality_semantics.pick_personality_descriptor(
            "neutral",
            random.Random(1),
            mood_key="tense",
            action_text="waiting for the next train",
            reject_fn=lambda _text: "",
            debug=tense_debug,
        )

        self.assertEqual(calm_selected, "calm expression")
        self.assertEqual(calm_debug["subject_centric_override_selected"]["id"], "sc_expression_calm_01")
        self.assertNotEqual(tense_selected, "calm expression")
        self.assertEqual(tense_debug.get("subject_centric_override_selected"), {})

    def test_contented_active_override_is_mood_gated(self):
        import random
        from vocab import personality_semantics

        joy_debug = {}
        joy_selected = personality_semantics.pick_personality_descriptor(
            "cheerful",
            random.Random(1),
            mood_key="joy",
            action_text="chatting while choosing fruit",
            reject_fn=lambda _text: "",
            debug=joy_debug,
        )
        focus_debug = {}
        focus_selected = personality_semantics.pick_personality_descriptor(
            "cheerful",
            random.Random(1),
            mood_key="focus",
            action_text="checking what needs to be handled next",
            reject_fn=lambda _text: "",
            debug=focus_debug,
        )

        self.assertEqual(joy_selected, "contented mouth")
        self.assertEqual(joy_debug["subject_centric_override_selected"]["id"], "sc_expression_contented_01")
        self.assertEqual(focus_selected, "curious eyes")
        self.assertEqual(focus_debug["subject_centric_override_selected"]["id"], "sc_gaze_curious_01")

    def test_wry_active_override_is_mood_gated(self):
        import random
        from vocab import personality_semantics

        awkward_debug = {}
        awkward_selected = personality_semantics.pick_personality_descriptor(
            "serious",
            random.Random(1),
            mood_key="awkward",
            action_text="realizing the paperwork is upside down",
            reject_fn=lambda _text: "",
            debug=awkward_debug,
        )
        focus_debug = {}
        focus_selected = personality_semantics.pick_personality_descriptor(
            "serious",
            random.Random(1),
            mood_key="focus",
            action_text="reviewing documents",
            reject_fn=lambda _text: "",
            debug=focus_debug,
        )

        self.assertEqual(awkward_selected, "wry grin")
        self.assertEqual(awkward_debug["subject_centric_override_selected"]["id"], "sc_expression_wry_01")
        self.assertNotEqual(focus_selected, "wry grin")
        self.assertEqual(focus_debug.get("subject_centric_override_selected"), {})


if __name__ == "__main__":
    unittest.main()
