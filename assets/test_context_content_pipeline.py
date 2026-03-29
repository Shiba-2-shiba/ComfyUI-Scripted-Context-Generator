import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from core.context_ops import append_history, patch_context
from core.schema import DebugInfo
from history_service import clothing_signature_from_decision
from pipeline.mood_builder import apply_mood_expansion
from pipeline.clothing_builder import apply_clothing_expansion, expand_clothing_prompt
from pipeline.location_builder import apply_location_expansion
from pipeline.prompt_orchestrator import (
    _derive_template_roles,
    build_prompt_text,
    build_prompt_from_context,
)


class TestContextContentPipeline(unittest.TestCase):
    def test_apply_mood_expansion_updates_context(self):
        ctx = patch_context({}, updates={"seed": 10}, meta={"mood": "quiet"})
        updated, expanded, staging = apply_mood_expansion(ctx, 10, "mood_map.json", "quiet")
        self.assertIsInstance(expanded, str)
        self.assertEqual(updated.meta.mood, expanded)
        self.assertEqual(updated.extras.get("staging_tags", ""), staging)

    def test_apply_clothing_expansion_writes_extras(self):
        ctx = patch_context({}, updates={"costume": "office_lady", "seed": 11}, extras={"raw_costume_key": "office_lady", "character_palette_str": "navy, white"})
        updated, clothing_prompt = apply_clothing_expansion(ctx, 11, "random", 0.3)
        self.assertIsInstance(clothing_prompt, str)
        self.assertEqual(updated.extras["clothing_prompt"], clothing_prompt)
        self.assertEqual(updated.history[-1].node, "ContextClothingExpander")
        self.assertTrue(updated.history[-1].decision.get("signature"))
        self.assertTrue(updated.history[-1].decision.get("base_variant"))

    def test_apply_clothing_expansion_suppresses_outerwear_for_home_locations(self):
        ctx = patch_context(
            {},
            updates={"costume": "office_lady", "loc": "cozy_living_room", "seed": 11},
            extras={"raw_costume_key": "office_lady", "raw_loc_tag": "cozy_living_room", "character_palette_str": "navy, white"},
        )
        updated, clothing_prompt = apply_clothing_expansion(ctx, 11, "random", 1.0)
        self.assertIsInstance(clothing_prompt, str)
        self.assertEqual(updated.history[-1].decision.get("outerwear_pack", ""), "")
        self.assertNotIn("over it", clothing_prompt)

    def test_expand_clothing_prompt_suppresses_outerwear_for_gym_locations(self):
        clothing_prompt, decision = expand_clothing_prompt(
            "gym_workout",
            21,
            "random",
            1.0,
            "gray, black",
            loc="fitness_gym",
            return_debug=True,
        )
        self.assertIsInstance(clothing_prompt, str)
        self.assertEqual(decision.get("outerwear_pack", ""), "")
        self.assertNotIn("over it", clothing_prompt)

    def test_expand_clothing_prompt_suppresses_outerwear_for_apartment_balcony(self):
        clothing_prompt, decision = expand_clothing_prompt(
            "office_lady",
            21,
            "random",
            1.0,
            "navy, white",
            loc="apartment_balcony",
            return_debug=True,
        )
        self.assertEqual(decision.get("outerwear_pack", ""), "")
        self.assertNotIn("over it", clothing_prompt)

    def test_expand_clothing_prompt_keeps_outerwear_available_for_apartment_entryway(self):
        clothing_prompt, decision = expand_clothing_prompt(
            "office_lady",
            21,
            "random",
            1.0,
            "navy, white",
            loc="apartment_entryway",
            return_debug=True,
        )
        self.assertTrue(decision.get("outerwear_pack"))
        self.assertIn("over it", clothing_prompt)

    def test_expand_clothing_prompt_keeps_outerwear_available_for_non_home_indoor_locations(self):
        clothing_prompt, decision = expand_clothing_prompt(
            "office_lady",
            21,
            "random",
            1.0,
            "navy, white",
            loc="bakery_shop",
            return_debug=True,
        )
        self.assertTrue(decision.get("outerwear_pack"))
        self.assertIn("over it", clothing_prompt)

    def test_clothing_signature_tracks_variant_details_within_same_pack(self):
        first = clothing_signature_from_decision(
            {
                "chosen_type": "separates",
                "base_pack": "modern_office_attire",
                "base_variant": "silk_blouse~pencil_skirt~navy",
                "outerwear_pack": "none",
                "outerwear_variant": "none",
            }
        )
        second = clothing_signature_from_decision(
            {
                "chosen_type": "separates",
                "base_pack": "modern_office_attire",
                "base_variant": "knit_top~tailored_trousers~charcoal",
                "outerwear_pack": "none",
                "outerwear_variant": "none",
            }
        )
        self.assertNotEqual(first, second)

    def test_apply_location_expansion_writes_extras(self):
        ctx = patch_context({}, updates={"loc": "classroom", "seed": 12}, extras={"raw_loc_tag": "classroom"})
        updated, location_prompt = apply_location_expansion(ctx, 12, "detailed", "auto")
        self.assertIsInstance(location_prompt, str)
        self.assertEqual(updated.extras["location_prompt"], location_prompt)
        self.assertEqual(updated.history[-1].node, "ContextLocationExpander")

    def test_apply_location_expansion_off_avoids_lighting_segments(self):
        ctx = patch_context({}, updates={"loc": "street_cafe", "seed": 12}, extras={"raw_loc_tag": "street_cafe"})
        updated, location_prompt = apply_location_expansion(ctx, 12, "detailed", "off")
        self.assertEqual(updated.extras["location_prompt"], location_prompt)
        self.assertNotIn("golden hour", location_prompt.lower())
        self.assertNotIn("bright daylight", location_prompt.lower())
        self.assertNotIn("warm ambient", location_prompt.lower())

    def test_build_prompt_from_context_prefers_expanded_fields(self):
        ctx = patch_context(
            {},
            updates={"subj": "A solo girl", "costume": "office_lady", "loc": "classroom", "action": "reading", "seed": 13},
            meta={"mood": "quiet", "style": "photo"},
            extras={
                "clothing_prompt": "white blouse and navy skirt",
                "location_prompt": "sunlit classroom",
                "garnish": "soft smile",
                "staging_tags": "clean composition",
            },
        )
        updated, prompt = build_prompt_from_context(ctx, "", False, 13)
        self.assertEqual(updated.seed, 13)
        self.assertIsInstance(prompt, str)
        self.assertIn("sunlit classroom", prompt)
        self.assertNotIn("photo", prompt.lower())
        self.assertEqual(updated.history[-1].node, "ContextPromptBuilder")

    def test_build_prompt_text_avoids_recent_template_key_when_composing(self):
        with patch("pipeline.prompt_orchestrator._template_entries") as mocked:
            mocked.side_effect = [
                [
                    {"key": "intro_plain", "text": "{subject_clause}", "roles": ["neutral"]},
                    {"key": "intro_alt", "text": "{subject_clause}, already in the middle of things", "roles": ["neutral"]},
                ],
                [
                    {"key": "body_direct", "text": "{action_clause}", "roles": ["neutral"]},
                ],
                [
                    {"key": "end_direct", "text": "{scene_clause}", "roles": ["neutral"]},
                ],
            ]
            prompt, debug = build_prompt_text(
                template="",
                composition_mode=True,
                seed=42,
                subj="girl",
                costume="dress",
                loc="park",
                action="walking",
                garnish="smiling",
                meta_mood="quiet",
                recent_templates=["intro_plain||body_direct||end_direct"],
                return_debug=True,
            )
        self.assertIsInstance(prompt, str)
        self.assertNotEqual(debug["template_key"], "intro_plain||body_direct||end_direct")
        self.assertEqual(debug["intro_key"], "intro_alt")

    def test_build_prompt_text_returns_role_aware_debug_in_composition_mode(self):
        prompt, debug = build_prompt_text(
            template="",
            composition_mode=True,
            seed=44,
            subj="girl",
            costume="dress",
            loc="station platform",
            action="walking toward the next train",
            garnish="focused gaze",
            meta_mood="on the way home",
            return_debug=True,
        )
        self.assertIsInstance(prompt, str)
        self.assertIn("template_roles", debug)
        self.assertIn("transition", debug["template_roles"]["body_roles"])
        self.assertTrue(debug["intro_key"])
        self.assertTrue(debug["body_key"])
        self.assertTrue(debug["end_key"])

    def test_derive_template_roles_does_not_let_quiet_garnish_override_transition_action(self):
        roles = _derive_template_roles(
            action="walking toward the next train",
            garnish="quiet look around her",
            meta_mood="on the way home",
            loc="station platform",
        )
        self.assertEqual(roles["body_roles"][0], "transition")
        self.assertIn("quiet", roles["body_roles"])

    def test_body_wrapper_templates_append_context_instead_of_prefix_wrapping(self):
        with patch("pipeline.prompt_orchestrator._template_entries") as mocked:
            mocked.side_effect = [
                [
                    {"key": "intro_plain", "text": "{subject_clause}", "roles": ["neutral"]},
                ],
                [
                    {"key": "body_focus", "text": "{action_clause}, her attention fixed on it", "roles": ["focused"]},
                ],
                [
                    {"key": "end_plain", "text": "{scene_clause}", "roles": ["neutral"]},
                ],
            ]
            prompt, debug = build_prompt_text(
                template="",
                composition_mode=True,
                seed=51,
                subj="girl",
                costume="dress",
                loc="library",
                action="fingers easing out of their tension",
                garnish="quiet look around her",
                meta_mood="late in the day",
                return_debug=True,
            )
        self.assertIn("fingers easing out of their tension, quiet look around her, her attention fixed on it", prompt)
        self.assertEqual(debug["body_key"], "body_focus")

    def test_fragment_action_surface_avoids_clause_focused_wrapper(self):
        with patch("pipeline.prompt_orchestrator._template_entries") as mocked:
            mocked.side_effect = [
                [
                    {"key": "intro_plain", "text": "{subject_clause}", "roles": ["focused"]},
                ],
                [
                    {
                        "key": "body_attention",
                        "text": "{action_clause}, her attention fixed on it",
                        "roles": ["focused"],
                        "preferred_surfaces": ["gerund", "clause"],
                        "avoid_surfaces": ["fragment"],
                    },
                    {
                        "key": "body_staying",
                        "text": "{action_clause}, the moment staying with her",
                        "roles": ["focused"],
                        "preferred_surfaces": ["fragment"],
                    },
                ],
                [
                    {"key": "end_plain", "text": "{scene_clause}", "roles": ["focused"]},
                ],
            ]
            prompt, debug = build_prompt_text(
                template="",
                composition_mode=True,
                seed=12,
                subj="girl",
                costume="dress",
                loc="gallery",
                action="hands settling and then shifting again",
                garnish="quiet look around her",
                meta_mood="late in the day",
                return_debug=True,
            )
        self.assertIn("the moment staying with her", prompt)
        self.assertEqual(debug["body_key"], "body_staying")
        self.assertEqual(debug["action_surface"]["surface"], "fragment")

    def test_long_action_avoids_as_garnish_template(self):
        with patch("pipeline.prompt_orchestrator._template_entries") as mocked:
            mocked.side_effect = [
                [
                    {"key": "intro_plain", "text": "{subject_clause}", "roles": ["social"]},
                ],
                [
                    {
                        "key": "body_as_garnish",
                        "text": "{action} as {garnish}",
                        "roles": ["social"],
                        "needs_garnish": True,
                        "preferred_surfaces": ["gerund", "clause"],
                        "max_action_words": 4,
                    },
                    {
                        "key": "body_with_garnish",
                        "text": "{action}, with {garnish}",
                        "roles": ["social"],
                        "needs_garnish": True,
                        "preferred_surfaces": ["gerund", "clause"],
                    },
                ],
                [
                    {"key": "end_plain", "text": "{scene_clause}", "roles": ["social"]},
                ],
            ]
            prompt, debug = build_prompt_text(
                template="",
                composition_mode=True,
                seed=88,
                subj="girl",
                costume="dress",
                loc="gallery",
                action="discussing art quietly with a companion near the far wall",
                garnish="soft smile",
                meta_mood="late in the day",
                return_debug=True,
            )
        self.assertIn(", with soft smile", prompt)
        self.assertEqual(debug["body_key"], "body_with_garnish")

    def test_gerund_action_can_render_as_framed_surface_for_room_template(self):
        with patch("pipeline.prompt_orchestrator._template_entries") as mocked:
            mocked.side_effect = [
                [
                    {"key": "intro_plain", "text": "{subject_clause}", "roles": ["quiet"]},
                ],
                [
                    {
                        "key": "body_room_for_action",
                        "text": "{action_clause}, leaving room for the rest of the scene",
                        "roles": ["quiet"],
                        "preferred_surfaces": ["gerund", "clause"],
                    },
                ],
                [
                    {"key": "end_plain", "text": "{scene_clause}", "roles": ["quiet"]},
                ],
            ]
            prompt, debug = build_prompt_text(
                template="",
                composition_mode=True,
                seed=90,
                subj="girl",
                costume="dress",
                loc="station",
                action="checking a route display before departure",
                garnish="composed posture",
                meta_mood="before departure",
                return_debug=True,
            )
        self.assertIn("in the middle of checking a route display before departure, composed posture", prompt)
        self.assertEqual(debug["body_key"], "body_room_for_action")
        self.assertEqual(debug["action_surface"]["input_surface"], "gerund")
        self.assertEqual(debug["action_surface"]["surface"], "framed")

    def test_build_prompt_from_context_uses_template_history(self):
        ctx = patch_context(
            {},
            updates={"subj": "girl", "costume": "office_lady", "loc": "park", "action": "walking", "seed": 13},
            meta={"mood": "quiet"},
        )
        ctx = append_history(
            ctx,
            DebugInfo(
                node="ContextPromptBuilder",
                seed=12,
                decision={"template_key": "{subject_clause}, {action_clause}, {scene_clause}."},
            ),
        )
        updated, prompt = build_prompt_from_context(ctx, "", False, 13)
        self.assertIsInstance(prompt, str)
        self.assertNotEqual(updated.history[-1].decision["template_key"], "{subject_clause}, {action_clause}, {scene_clause}.")


if __name__ == "__main__":
    unittest.main()
