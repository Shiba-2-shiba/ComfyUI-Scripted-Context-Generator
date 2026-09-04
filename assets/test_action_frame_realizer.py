import unittest
from pathlib import Path
from unittest.mock import patch


from core.context_ops import patch_context
from core.context_state import generation_state_from_context
from core.schema import ActionFrame
from pipeline.prompt_orchestrator import build_prompt_from_context, build_prompt_text


class TestActionFrameRealizer(unittest.TestCase):
    def test_action_frame_round_trip_preserves_typed_roles_and_legacy_slots(self):
        slots = {
            "location": "station",
            "posture": "standing near the route map",
            "hand_action": "checking a transit card",
            "gaze_target": "watching the platform display",
            "progress_state": "midway",
            "obstacle_or_trigger": "delay",
            "social_distance": "alone",
            "time_or_weather": "during the evening rush",
        }
        frame = ActionFrame.from_slots(
            slots,
            legacy_text="checking a transit card while watching the platform display",
            main_verb="checking",
            primary_object="card",
        )

        restored = ActionFrame.from_dict(frame.to_dict())
        self.assertEqual(restored, frame)
        self.assertEqual(restored.to_slot_dict(), slots)
        self.assertEqual(restored.main_verb, "checking")
        self.assertEqual(restored.primary_object, "card")
        self.assertEqual(restored.progress, "midway")
        self.assertEqual(restored.stimulus_or_obstacle, "delay")
        self.assertEqual(restored.social_relation, "alone")

    def test_generation_state_reads_and_writes_persisted_action_frame_without_losing_unknown_extras(self):
        frame = ActionFrame.from_slots(
            {"posture": "standing by the window", "gaze_target": "watching the rain"},
            legacy_text="standing by the window, watching the rain",
            main_verb="standing",
        )
        ctx = patch_context(
            {},
            updates={"action": frame.legacy_text},
            extras={"action_frame": frame.to_dict(), "extension_field": {"keep": True}},
        )

        state = generation_state_from_context(ctx)
        patched = patch_context(ctx, extras=state.to_extras_patch())
        self.assertEqual(state.action, frame)
        self.assertEqual(patched.extras["action_frame"], frame.to_dict())
        self.assertEqual(patched.extras["extension_field"], {"keep": True})

    def test_generation_state_rejects_stale_or_unknown_action_frame_authority(self):
        stale = ActionFrame.from_slots(
            {"hand_action": "holding a book"},
            legacy_text="holding a book",
            main_verb="holding",
            primary_object="book",
        ).to_dict()
        stale_context = patch_context(
            {},
            updates={"action": "checking a transit card"},
            extras={"action_frame": stale, "extension_field": "preserved"},
        )
        unknown = {**stale, "schema_version": "action-frame/v999"}
        unknown_context = patch_context(
            {},
            updates={"action": "holding a book"},
            extras={"action_frame": unknown},
        )

        self.assertFalse(generation_state_from_context(stale_context).action.has_content())
        self.assertFalse(generation_state_from_context(unknown_context).action.has_content())
        self.assertEqual(stale_context.extras["extension_field"], "preserved")

    def test_prompt_builder_persists_legacy_action_as_frame_and_matches_debug_payload(self):
        ctx = patch_context(
            {},
            updates={
                "subj": "a solo girl",
                "costume": "navy coat",
                "loc": "station platform",
                "action": "checking a transit card, watching the platform display",
            },
            extras={"garnish": "focused gaze"},
        )

        updated, prompt = build_prompt_from_context(ctx, "", True, 37)
        frame_payload = updated.extras["action_frame"]
        debug = updated.history[-1].decision

        self.assertTrue(prompt)
        self.assertEqual(debug["action_frame"], frame_payload)
        self.assertEqual(debug["action_frame"]["legacy_slots"], debug["action_slots"])
        self.assertTrue(debug["action_frame_matches_debug_slots"])
        self.assertIn("content_plan", debug)
        self.assertEqual(
            set(debug["content_plan"]["named_seed_streams"]),
            {"lexical", "syntax", "template"},
        )

    def test_workflow_persists_generated_frame_equal_to_scene_debug(self):
        from tools.workflow_prompt_runner import build_canonical_record
        from workflow_widget_validation import load_workflow

        record = build_canonical_record(
            load_workflow(Path("ComfyUI-workflow-context.json")),
            0,
            profile="verification/fixtures/prompt_quality_supported_profile.json",
            overrides={8: {"composition_mode": True}},
        )
        context = record["final_context"]
        frame = context["extras"]["action_frame"]
        scene_debug = next(
            item["decision"] for item in context["history"]
            if item["node"] == "ContextSceneVariator"
        )
        self.assertEqual(frame, scene_debug["action_frame"])
        self.assertEqual(frame["legacy_slots"], scene_debug["slots"])

    def test_staging_append_avoids_period_comma_in_both_modes(self):
        kwargs = {
            "template": "{subject_clause}, {action_clause}, {scene_clause}.",
            "seed": 19,
            "subj": "a solo girl",
            "costume": "navy coat",
            "loc": "station platform",
            "action": "checking a transit card",
            "garnish": "focused gaze",
            "meta_mood": "quiet evening",
            "staging_tags": "bubbly smile",
        }
        legacy = build_prompt_text(composition_mode=False, **kwargs)
        natural = build_prompt_text(composition_mode=True, **kwargs)

        self.assertNotIn(".,", legacy)
        self.assertNotIn(",.", legacy)
        self.assertNotIn(".,", natural)
        self.assertNotIn(",.", natural)

    def test_content_plan_is_deterministic_and_missing_optional_slots_do_not_fragment(self):
        frame = ActionFrame.from_slots(
            {"hand_action": "checking a transit card"},
            legacy_text="checking a transit card",
            main_verb="checking",
            primary_object="card",
        )
        kwargs = {
            "template": "",
            "composition_mode": True,
            "seed": 23,
            "subj": "a solo girl",
            "costume": "navy coat",
            "loc": "station platform",
            "action": frame.legacy_text,
            "action_frame": frame.to_dict(),
            "return_debug": True,
        }

        first_prompt, first_debug = build_prompt_text(**kwargs)
        second_prompt, second_debug = build_prompt_text(**kwargs)
        self.assertEqual(first_prompt, second_prompt)
        self.assertEqual(first_debug["content_plan"], second_debug["content_plan"])
        self.assertNotRegex(first_prompt, r"(?:,\s*){2,}")
        self.assertNotIn("None", first_prompt)
        self.assertNotIn("{}", first_prompt)

    def test_composition_renderer_uses_content_plan_as_realization_authority(self):
        with patch("prompt_renderer.realize_content_plan", return_value="{subject_clause}, {action_clause}, {scene_clause}.") as realize:
            prompt = build_prompt_text(
                template="",
                composition_mode=True,
                seed=31,
                subj="a solo girl",
                costume="navy coat",
                loc="station platform",
                action="checking a transit card",
            )

        realize.assert_called_once()
        self.assertIn("a solo girl", prompt)
        self.assertIn("checking a transit card", prompt)
        self.assertIn("station platform", prompt)

    def test_renderer_emits_only_girl_and_removes_race_or_skin_descriptors(self):
        for composition_mode in (False, True):
            with self.subTest(composition_mode=composition_mode):
                prompt = build_prompt_text(
                    template="{subject_clause}, {action_clause}, {scene_clause}.",
                    composition_mode=composition_mode,
                    seed=41,
                    subj="a Nigerian dark-skinned woman with dreadlocks",
                    costume="black dress",
                    loc="station platform",
                    action="checking a transit card beside a woman",
                    garnish="deep brown skin, dusky-skinned, bronze skin, skin tone: dark brown, of African descent, focused gaze",
                )

                self.assertIn("girl", prompt.lower())
                self.assertIn("black dress", prompt.lower())
                self.assertNotRegex(prompt.lower(), r"\b(?:woman|women|lady|female)\b")
                self.assertNotIn("dark-skinned", prompt.lower())
                self.assertNotIn("brown skin", prompt.lower())
                self.assertNotIn("dusky-skinned", prompt.lower())
                self.assertNotIn("bronze skin", prompt.lower())
                self.assertNotIn("skin tone", prompt.lower())
                self.assertNotIn("african descent", prompt.lower())
                self.assertNotIn("nigerian", prompt.lower())
                self.assertNotIn("dreadlocks", prompt.lower())

        tag_prompt = build_prompt_text(
            template="{subject_clause}, {action_clause}, {scene_clause}.",
            composition_mode=False,
            seed=42,
            subj="1woman",
            costume="black dress",
            loc="station platform",
            action="checking a transit card",
        )
        self.assertIn("girl", tag_prompt.lower())
        self.assertNotIn("1woman", tag_prompt.lower())

        retained_hair = build_prompt_text(
            template="{subject_clause}, {action_clause}, {scene_clause}.",
            composition_mode=False,
            seed=43,
            subj="a woman with dreadlocks, dark brown hair",
            costume="black dress",
            loc="station platform",
            action="checking a transit card",
        )
        self.assertIn("girl with dark brown hair", retained_hair.lower())


if __name__ == "__main__":
    unittest.main()
