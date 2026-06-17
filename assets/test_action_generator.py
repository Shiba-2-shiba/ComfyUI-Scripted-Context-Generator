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
from pipeline.action_parser import (
    action_verb as parser_action_verb,
    parse_pool_action_to_slots as parser_parse_pool_action_to_slots,
)
from pipeline.action_relation_binder import apply_object_relation_slots
from pipeline.action_renderer import (
    append_clause,
    render_action_slots as renderer_render_action_slots,
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
        self.assertEqual(debug["semantic_epig"]["action"]["mode"], "active")
        self.assertTrue(debug["semantic_epig"]["action"]["selected_by_semantic"])
        self.assertIn("target_vector", debug["semantic_epig"]["action"])
        self.assertIn("slot_rankings", debug["semantic_epig"]["action"])
        self.assertIn("slot_changes", debug["semantic_epig"]["action"])
        self.assertIn("selection_changed_by_semantic", debug["semantic_epig"]["action"])

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
        self.assertEqual(debug["semantic_epig"]["action"]["mode"], "active")
        self.assertTrue(debug["semantic_epig"]["action"]["selected_by_semantic"])

    def test_solo_safety_filters_people_and_spill_pool_actions(self):
        pool = [
            {"text": "standing aside as students pass through the corridor", "load": "calm"},
            {"text": "wiping spill off table", "load": "calm"},
            {"text": "checking the next task at her desk", "load": "calm"},
        ]

        action, debug = generate_action_for_location(
            "modern_office",
            self.compat,
            self.scene_axes,
            random.Random(1),
            pool=pool,
            recent_verbs=[],
            recent_objects=[],
        )

        lowered = action.lower()
        self.assertEqual(debug["base_action"], "checking the next task at her desk")
        self.assertNotIn("students pass", lowered)
        self.assertNotIn("people", lowered)
        self.assertNotIn("crowd", lowered)
        self.assertNotIn("spill", lowered)

    def test_solo_safety_falls_back_when_pool_is_only_unsafe(self):
        action, debug = generate_action_for_location(
            "modern_office",
            self.compat,
            self.scene_axes,
            random.Random(4),
            pool=[
                {"text": "moving carefully around the people nearby", "load": "calm"},
                {"text": "dabbing stain with napkin", "load": "calm"},
            ],
            recent_verbs=[],
            recent_objects=[],
        )

        lowered = action.lower()
        self.assertEqual(debug["generator_mode"], "compositional")
        self.assertNotIn("people nearby", lowered)
        self.assertNotIn("stain", lowered)
        self.assertNotIn("napkin", lowered)

    def test_solo_safety_sanitizes_slot_overrides(self):
        slots = build_action_slots(
            "modern_office",
            self.compat,
            self.scene_axes,
            random.Random(9),
            slot_overrides={
                "social_distance": "crowd",
                "social_clause": "moving carefully around the people nearby",
                "obstacle_or_trigger": "spill",
                "obstacle_clause": "after a small mess interrupts the rhythm",
            },
        )
        rendered = render_action_slots(slots)

        self.assertIn(slots["social_distance"], {"alone", "acquaintance", "stranger"})
        self.assertEqual(slots["obstacle_or_trigger"], "")
        self.assertNotIn("people", rendered.lower())
        self.assertNotIn("spill", rendered.lower())

    def test_action_semantic_active_selection_is_deterministic(self):
        action_without_debug, _debug_without_assertion = generate_action_for_location(
            "modern_office",
            self.compat,
            self.scene_axes,
            random.Random(19),
            recent_verbs=["typing"],
            recent_objects=[],
        )
        action_with_debug, debug = generate_action_for_location(
            "modern_office",
            self.compat,
            self.scene_axes,
            random.Random(19),
            recent_verbs=["typing"],
            recent_objects=[],
        )

        self.assertEqual(action_with_debug, action_without_debug)
        self.assertEqual(debug["normalized_action"], action_with_debug)
        self.assertIn("semantic_epig", debug)
        self.assertTrue(debug["semantic_epig"]["action"]["selected_by_semantic"])
        self.assertTrue(debug["semantic_epig"]["action"]["semantic_scoring_enabled"])

    def test_action_semantic_debug_includes_descriptor_supplied_candidates(self):
        from pipeline.action_generator import build_action_slots

        semantic_debug = {}
        build_action_slots(
            "school_library",
            self.compat,
            self.scene_axes,
            random.Random(5),
            slot_overrides={"purpose": "study", "location": "school_library"},
            semantic_debug=semantic_debug,
        )

        hand_rankings = semantic_debug["action"]["slot_rankings"]["hand_action"]
        self.assertIn("thumb keeping the page open", {item["text"] for item in hand_rankings})

    def test_object_relation_active_adds_object_state_without_overwriting_existing_slots(self):
        action, debug = generate_action_for_location(
            "school_library",
            self.compat,
            self.scene_axes,
            random.Random(3),
            pool=[{"text": "reading a book quietly", "load": "calm"}],
            recent_verbs=[],
            recent_objects=[],
        )

        relation_debug = debug["semantic_epig"]["object_relation"]
        self.assertEqual(relation_debug["mode"], "active")
        self.assertEqual(relation_debug["relation_key"], "book:reading")
        self.assertIn("gaze_target", relation_debug["required_roles"])
        self.assertEqual(relation_debug["applied_slots"]["object_state"], "open pages visible")
        self.assertIn("hand_action", relation_debug["skipped_slots"])
        self.assertEqual(debug["slots"]["object_state"], "open pages visible")
        self.assertIn("open pages visible", action)
        self.assertEqual(debug["normalized_action"], action)

    def test_action_relation_binder_preserves_existing_slots(self):
        slots = {
            "hand_action": "hands already keeping the book open",
            "gaze_target": "eyes already on the open page",
        }

        relation_debug = apply_object_relation_slots(slots, "reading a book quietly")

        self.assertEqual(relation_debug["relation_key"], "book:reading")
        self.assertEqual(slots["hand_action"], "hands already keeping the book open")
        self.assertEqual(slots["gaze_target"], "eyes already on the open page")
        self.assertEqual(relation_debug["skipped_slots"]["hand_action"], "existing slot already set")
        self.assertEqual(relation_debug["skipped_slots"]["gaze_target"], "existing slot already set")
        self.assertEqual(slots["object_state"], "open pages visible")
        self.assertEqual(relation_debug["applied_slots"]["object_state"], "open pages visible")

    def test_render_action_slots_dedupes_anchor_and_preserves_clause_order(self):
        rendered = render_action_slots(
            {
                "anchor": "by the window",
                "posture": "standing by the window",
                "hand_action": "straightening a stack of printouts",
                "object_state": "printouts squared into a neat stack",
                "gaze_target": "checking the top page",
                "optional_micro_action": "checking the top page",
                "time_or_weather": "during lunch break",
            }
        )
        renderer_rendered = renderer_render_action_slots(
            {
                "anchor": "by the window",
                "posture": "standing by the window",
                "hand_action": "straightening a stack of printouts",
                "object_state": "printouts squared into a neat stack",
                "gaze_target": "checking the top page",
                "optional_micro_action": "checking the top page",
                "time_or_weather": "during lunch break",
            }
        )

        self.assertEqual(
            rendered,
            "holding onto the moment in front of her, standing by the window, "
            "straightening a stack of printouts, printouts squared into a neat stack, "
            "checking the top page, during lunch break",
        )
        self.assertEqual(renderer_rendered, rendered)

    def test_render_action_slots_activity_first_starts_with_hand_action(self):
        rendered = render_action_slots(
            {
                "posture": "standing by the poster wall",
                "hand_action": "turning a ticket over in her fingers",
                "purpose_clause": "checking the entry time",
                "gaze_target": "looking toward the queue",
            },
            activity_first=True,
        )
        renderer_rendered = renderer_render_action_slots(
            {
                "posture": "standing by the poster wall",
                "hand_action": "turning a ticket over in her fingers",
                "purpose_clause": "checking the entry time",
                "gaze_target": "looking toward the queue",
            },
            activity_first=True,
        )

        self.assertEqual(
            rendered,
            "turning a ticket over in her fingers, standing by the poster wall, looking toward the queue",
        )
        self.assertEqual(renderer_rendered, rendered)

    def test_action_renderer_append_clause_dedupes_existing_text(self):
        self.assertEqual(append_clause("", "checking the entry time."), "checking the entry time")
        self.assertEqual(
            append_clause("checking the entry time", "checking the entry time"),
            "checking the entry time",
        )
        self.assertEqual(
            append_clause("checking the entry time.", "looking toward the queue."),
            "checking the entry time, looking toward the queue",
        )

    def test_parse_pool_action_to_slots_extracts_posture_and_hand_action(self):
        slots = parse_pool_action_to_slots(
            "standing by the window straightening a stack of printouts",
            loc="modern_office",
            compat=self.compat,
        )
        parser_slots = parser_parse_pool_action_to_slots(
            "standing by the window straightening a stack of printouts",
            loc="modern_office",
            compat=self.compat,
        )
        self.assertEqual(parser_slots, slots)
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
        parser_actual = parser_action_verb(text)
        case_label = label or text
        self.assertEqual(
            actual,
            expected,
            msg=f"{case_label}\nexpected normalized verb: {expected}\nactual normalized verb: {actual}\naction: {text}",
        )
        self.assertEqual(parser_actual, actual)

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
