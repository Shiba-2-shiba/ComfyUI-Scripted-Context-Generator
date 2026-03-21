import os
import sys
import random
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from core.semantic_policy import find_banned_terms
from pipeline.action_generator import (
    action_verb,
    _weighted_slot_choice,
    build_action_slots,
    generate_action_for_location,
    parse_pool_action_to_slots,
    render_action_slots,
)
from pipeline.context_pipeline import _load_action_pools, _load_compatibility, _load_scene_axes


class TestActionGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compat = _load_compatibility()
        cls.scene_axes = _load_scene_axes()
        cls.action_pools = _load_action_pools()

    def test_build_action_slots_contains_required_semantic_units(self):
        slots = build_action_slots(
            "train_station_platform",
            self.compat,
            self.scene_axes,
            random.Random(7),
            recent_verbs=["waiting"],
            recent_objects=[],
        )
        for key in (
            "purpose",
            "progress_state",
            "social_distance",
            "posture",
            "hand_action",
            "gaze_target",
            "optional_micro_action",
        ):
            self.assertIn(key, slots)
            self.assertIsInstance(slots[key], str)
        rendered = render_action_slots(slots)
        self.assertTrue(rendered)
        self.assertEqual(find_banned_terms(rendered), {})

    def test_generate_action_for_location_without_pool_uses_compositional_mode(self):
        action, debug = generate_action_for_location(
            "train_station_platform",
            self.compat,
            self.scene_axes,
            random.Random(11),
            recent_verbs=["waiting"],
            recent_objects=[],
        )
        self.assertTrue(action)
        self.assertEqual(debug["generator_mode"], "compositional")
        self.assertIn("slots", debug)
        self.assertIn("slot_sources", debug)
        self.assertIn("object_focus", debug)
        self.assertEqual(debug["normalized_action"], action)
        self.assertEqual(find_banned_terms(action), {})

    def test_generate_action_for_location_with_pool_enriches_pool_result(self):
        pool = [a for a in self.action_pools["modern_office"]]
        action, debug = generate_action_for_location(
            "modern_office",
            self.compat,
            self.scene_axes,
            random.Random(7),
            pool=pool,
            recent_verbs=["writing"],
            recent_objects=[],
        )
        self.assertEqual(debug["generator_mode"], "pool")
        self.assertIn("base_action", debug)
        self.assertIn("normalized_action", debug)
        self.assertIn("pool_slots", debug)
        self.assertIn("slot_sources", debug)
        self.assertIn("object_focus", debug)
        self.assertNotEqual(debug["base_action"], action)
        self.assertEqual(debug["normalized_action"], action)
        self.assertTrue(any(source == "pool" for source in debug["slot_sources"].values()))
        self.assertEqual(find_banned_terms(action), {})

    def test_parse_pool_action_to_slots_extracts_posture_and_hand_action(self):
        slots = parse_pool_action_to_slots(
            "standing by the window straightening a stack of printouts",
            loc="modern_office",
            compat=self.compat,
        )
        self.assertEqual(slots["posture"], "standing by the window")
        self.assertEqual(slots["hand_action"], "straightening a stack of printouts")
        self.assertEqual(slots["anchor"], "by the window")
        self.assertEqual(slots["purpose"], "work")

    def test_parse_pool_action_to_slots_splits_contextual_clause(self):
        slots = parse_pool_action_to_slots(
            "checking a document while on a call",
            loc="modern_office",
            compat=self.compat,
        )
        self.assertEqual(slots["hand_action"], "checking a document")
        self.assertEqual(slots["optional_micro_action"], "while on a call")
        self.assertEqual(slots["purpose"], "work")
        self.assertNotIn("anchor", slots)

    def test_parse_pool_action_to_slots_tracks_before_clause_as_preparing(self):
        slots = parse_pool_action_to_slots(
            "rearranging name cards before everyone arrives",
            loc="boardroom",
            compat=self.compat,
        )
        self.assertEqual(slots["hand_action"], "rearranging name cards")
        self.assertEqual(slots["progress_state"], "preparing")
        self.assertEqual(slots["optional_micro_action"], "before everyone arrives")

    def test_parse_pool_action_to_slots_treats_following_as_gaze(self):
        slots = parse_pool_action_to_slots(
            "standing and following the station names overhead",
            loc="commuter_transport",
            compat=self.compat,
        )
        self.assertEqual(slots["posture"], "standing")
        self.assertEqual(slots["gaze_target"], "following the station names overhead")

    def assertNormalizedVerb(self, text: str, expected: str, label: str | None = None):
        actual = action_verb(text)
        case_label = label or text
        self.assertEqual(
            actual,
            expected,
            msg=f"{case_label}\nexpected normalized verb: {expected}\nactual normalized verb: {actual}\naction: {text}",
        )

    def test_action_verb_skips_fragment_subject_tokens(self):
        self.assertNormalizedVerb("hands settling and then shifting again", "settling")
        self.assertNormalizedVerb("fingers easing out of their tension", "easing")
        self.assertNormalizedVerb("one hand keeping her place", "keeping")

    def test_action_verb_handles_hyphenated_and_posture_led_clauses(self):
        self.assertNormalizedVerb("double-checking what stands out", "checking")
        self.assertNormalizedVerb("standing and checking her watch", "checking")
        self.assertNormalizedVerb("standing and following the station names overhead", "following")

    def test_action_verb_recovers_noun_phrase_actions(self):
        self.assertNormalizedVerb("deep sigh near the side of the room", "sighing")
        self.assertNormalizedVerb("reading quietly, sitting at a table", "reading")
        self.assertNormalizedVerb(
            "hands busy with the material in front of her, walking towards the fence with a smile",
            "walking",
        )
        self.assertNormalizedVerb(
            "hands busy with the material in front of her near the part of the scene she is using, "
            "walking towards the fence with a smile",
            "walking",
        )
        self.assertNormalizedVerb("hurriedly checking the notice board", "checking")
        self.assertNormalizedVerb("mentally lining up the next task", "lining")

    def test_action_verb_matches_representative_audit_samples(self):
        cases = [
            (
                "school_rooftop fragment-led clause with trailing motion",
                "hands settling and then shifting again near the part of the scene she is using, "
                "walking towards the fence with a smile, looking toward the next thing she needs, "
                "measuring the pause instead of rushing it, leaving room for casual conversation, "
                "while setting up the next step, before class starts",
                "settling",
            ),
            (
                "school_rooftop busy-hands clause should not collapse to using",
                "hands busy with the material in front of her near the part of the scene she is using, "
                "walking towards the fence with a smile, looking toward the next thing she needs, "
                "quietly marking her place, lost in her own rhythm, as she gets herself ready, during a lunch break",
                "walking",
            ),
            (
                "school_library quiet table action stays on the primary verb",
                "reading quietly, sitting at a table, looking toward the part of the room she needs, "
                "rechecking a small detail, lost in her own rhythm, while bringing it to a close, during the last quiet hour",
                "reading",
            ),
            (
                "neighborhood_playground hyphenated clause normalizes to checking",
                "double-checking what stands out close to the doorway, hovering in place while she decides, "
                "fingers checking the item in front of her, watching what is happening just ahead, "
                "half-ready to answer someone nearby, near the point where she can move on, face-palm gesture, on the way back home",
                "checking",
            ),
            (
                "apartment_balcony noun phrase recovers as holding",
                "holding onto the quiet for a second longer near the railing, settling into a quieter pace, "
                "one hand resting lightly where it lands, letting her gaze drift before returning, "
                "letting the pause settle properly, keeping to herself, as she gets herself ready, late in the evening",
                "holding",
            ),
            (
                "school_clubroom noun phrase recovers as sighing",
                "deep sigh near the side of the room, taking on an easy unhurried posture, "
                "one hand resting lightly where it lands, looking off for a quiet second, "
                "letting the pause settle properly, half-ready to answer someone nearby, before fully getting started, during a lunch break",
                "sighing",
            ),
        ]

        for label, text, expected in cases:
            with self.subTest(label=label):
                self.assertNormalizedVerb(text, expected, label=label)

    def test_all_action_pool_entries_normalize_into_slots(self):
        structural_keys = {"posture", "hand_action", "gaze_target", "optional_micro_action", "anchor", "purpose"}
        for loc, pool in self.action_pools.items():
            if str(loc).startswith("_") or loc == "schema_version":
                continue
            for item in pool:
                text = item.get("text", "") if isinstance(item, dict) else str(item)
                slots = parse_pool_action_to_slots(text, loc=loc, compat=self.compat)
                self.assertTrue(
                    any(slots.get(key) for key in structural_keys),
                    msg=f"{loc}: {text}",
                )

    def test_weighted_slot_choice_penalizes_true_bias_action_objects(self):
        rng = random.Random(123)
        phone_hits = 0
        total = 1500
        for _ in range(total):
            value = _weighted_slot_choice(
                ["checking phone", "holding a strap"],
                rng,
                loc="commuter_transport",
            )
            if "phone" in value:
                phone_hits += 1
        self.assertLess(phone_hits / total, 0.20)

    def test_weighted_slot_choice_avoids_repeating_selected_object(self):
        rng = random.Random(321)
        book_hits = 0
        total = 1500
        for _ in range(total):
            value = _weighted_slot_choice(
                ["reading a book", "adjusting her sleeve"],
                rng,
                loc="school_library",
                selected_objects={"book"},
            )
            if "book" in value:
                book_hits += 1
        self.assertLess(book_hits / total, 0.40)


if __name__ == "__main__":
    unittest.main()
