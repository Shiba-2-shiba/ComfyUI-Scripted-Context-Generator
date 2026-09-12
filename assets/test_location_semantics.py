import os
import sys
import unittest
from pathlib import Path


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestLocationSemantics(unittest.TestCase):
    def test_library_study_target_prefers_orderly_quiet_segments(self):
        from pipeline.location_semantics import build_scene_target_vector, rank_location_segment_options

        target = build_scene_target_vector("school_library", action_text="reading a book")
        ranked = rank_location_segment_options(
            "props",
            ["overhead transit signs", "neatly arranged shelves"],
            target,
            loc_key="school_library",
        )

        self.assertEqual(ranked[0]["text"], "neatly arranged shelves")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])

    def test_commuter_waiting_target_prefers_crowd_and_time_pressure(self):
        from pipeline.location_semantics import build_scene_target_vector, rank_location_segment_options

        target = build_scene_target_vector("commuter_transport", action_text="waiting for the next train", mood_text="tense")
        ranked = rank_location_segment_options(
            "crowd",
            ["completely empty", "commuters moving through the background"],
            target,
            loc_key="commuter_transport",
        )

        self.assertEqual(ranked[0]["text"], "commuters moving through the background")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])

    def test_unknown_location_uses_neutral_vector_without_crashing(self):
        from pipeline.location_semantics import build_scene_target_vector, rank_location_segment_options

        target = build_scene_target_vector("unknown_place", action_text="walking")
        ranked = rank_location_segment_options("props", ["plain prop"], target, loc_key="unknown_place")

        self.assertEqual(ranked[0]["text"], "plain prop")
        self.assertIn("score", ranked[0])

    def test_debug_payload_uses_config_mode_and_is_compact(self):
        from pipeline.location_semantics import (
            build_scene_target_vector,
            rank_location_segment_options,
            semantic_location_debug_payload,
        )

        target = build_scene_target_vector("school_library", action_text="studying")
        ranking = rank_location_segment_options("core", ["quiet reading tables"], target)
        payload = semantic_location_debug_payload(target_vector=target, segment_rankings={"core": ranking})

        self.assertEqual(payload["mode"], "active")
        self.assertFalse(payload["selected_by_semantic"])
        self.assertTrue(payload["semantic_scoring_enabled"])
        self.assertFalse(payload["selection_changed_by_semantic"])
        self.assertEqual(payload["changed_sections"], [])
        self.assertEqual(payload["segment_rankings"]["core"][0]["text"], "quiet reading tables")

    def test_debug_payload_caps_each_segment_ranking_and_keeps_counts(self):
        from pipeline.location_semantics import semantic_location_debug_payload

        ranking = [
            {
                "text": f"candidate {index}",
                "score": 1.0 - index * 0.1,
                "distance": index * 0.1,
                "source": f"fixture[{index}]",
                "role": "core",
            }
            for index in range(5)
        ]
        payload = semantic_location_debug_payload(segment_rankings={"core": ranking})

        self.assertEqual(len(payload["segment_rankings"]["core"]), 3)
        self.assertEqual(payload["segment_ranking_counts"]["core"], 5)
        self.assertEqual(payload["segment_ranking_truncated_counts"]["core"], 2)

    def test_compacted_ranking_keeps_selected_identity_outside_top_three(self):
        from pipeline.location_semantics import semantic_location_debug_payload

        ranking = [
            {
                "text": f"candidate {index}",
                "score": 1.0 - index * 0.1,
                "distance": index * 0.1,
                "source": f"fixture[{index}]",
                "role": "core",
            }
            for index in range(5)
        ]
        payload = semantic_location_debug_payload(
            segment_rankings={"core": ranking},
            section_changes={
                "core": {
                    "baseline": "candidate 0",
                    "semantic": "candidate 4",
                    "changed": True,
                    "semantic_top_candidate": "candidate 0",
                    "selected_candidate_rank": 4,
                }
            },
        )

        self.assertEqual(payload["section_changes"]["core"]["semantic"], "candidate 4")
        self.assertEqual(payload["section_changes"]["core"]["selected_candidate_rank"], 4)

    def test_location_policy_filters_lighting_and_disallowed_fx(self):
        from pipeline.location_policy import filter_fx_candidates, filter_off_mode_options

        self.assertEqual(
            filter_off_mode_options(["warm ambient glow", "plain ceramic tiles"], fallback_all=False),
            ["plain ceramic tiles"],
        )
        self.assertEqual(
            filter_fx_candidates(["bokeh", "snowflakes drifting near the path", "sparkling eyes", "bokeh"]),
            ["snowflakes drifting near the path", "sparkling eyes"],
        )

    def test_location_expansion_filters_solo_unsafe_segments(self):
        from unittest.mock import patch

        from pipeline import location_builder

        packs = {
            "solo_safety_room": {
                "environment": ["quiet private room", "crowded train"],
                "core": ["single desk", "students pass through the corridor"],
                "props": ["plain notebook", "people waiting near display"],
                "crowd": ["line of people waiting", "friends sharing a booth nearby"],
                "time": [],
                "weather": [],
                "texture": [],
                "fx": [],
            }
        }

        with patch.object(location_builder.background_vocab, "CONCEPT_PACKS", packs):
            prompt, debug = location_builder.expand_location_prompt(
                "solo_safety_room",
                12,
                "detailed",
                return_debug=True,
            )

        lowered = prompt.lower()
        self.assertEqual(debug["pack_key"], "solo_safety_room")
        self.assertIn("quiet private room", lowered)
        self.assertNotIn("crowded", lowered)
        self.assertNotIn("students pass", lowered)
        self.assertNotIn("people", lowered)
        self.assertNotIn("friends", lowered)

    def test_location_expansion_filters_ambient_secondary_people_candidates(self):
        from unittest.mock import patch

        from pipeline import location_builder

        unsafe_phrases = [
            "a few residents checking the bulletin board",
            "small groups gathering",
            "teacher supervising",
            "one child waiting near the poster board",
            "families sharing meals",
            "neighbors browsing from store to store",
            "a few shoppers scanning labels",
            "visitors returning books at the counter",
            "students looking for seats",
            "shopkeepers arranging goods near the entrance",
            "clerk tidying the display nearby",
        ]
        packs = {
            "ambient_people_room": {
                "environment": ["quiet private room"],
                "core": [],
                "props": [],
                "crowd": unsafe_phrases + ["empty background"],
                "time": [],
                "weather": [],
                "texture": [],
                "fx": [],
            }
        }

        with patch.object(location_builder.background_vocab, "CONCEPT_PACKS", packs):
            prompts = [
                location_builder.expand_location_prompt("ambient_people_room", seed, "detailed")
                for seed in range(40)
            ]

        joined = "\n".join(prompts).lower()
        for phrase in unsafe_phrases:
            self.assertNotIn(phrase, joined)

    def test_location_expansion_filters_implied_crowd_occupancy_candidates(self):
        from unittest.mock import patch

        from pipeline import location_builder

        packs = {
            "occupancy_room": {
                "environment": ["quiet private room"],
                "core": [],
                "props": [],
                "crowd": ["standing room only", "packed like sardines", "mostly empty seats"],
                "time": ["quiet midday"],
                "weather": [],
                "texture": [],
                "fx": [],
            }
        }

        with patch.object(location_builder.background_vocab, "CONCEPT_PACKS", packs):
            prompts = [
                location_builder.expand_location_prompt("occupancy_room", seed, "detailed")
                for seed in range(40)
            ]

        joined = "\n".join(prompts).lower()
        self.assertNotIn("standing room only", joined)
        self.assertNotIn("packed like sardines", joined)
        self.assertTrue(any("mostly empty seats" in prompt for prompt in prompts))
        self.assertTrue(all("quiet private room" in prompt for prompt in prompts))

    def test_location_expansion_filters_time_candidates_that_conflict_with_environment_or_action(self):
        from unittest.mock import patch

        from pipeline import location_builder

        packs = {
            "time_consistency_room": {
                "environment": ["swaying bus interior at night"],
                "core": [],
                "props": [],
                "crowd": [],
                "time": ["late night last train", "quiet midday"],
                "weather": [],
                "texture": [],
                "fx": [],
            },
            "action_time_consistency_room": {
                "environment": ["quiet station concourse"],
                "core": [],
                "props": [],
                "crowd": [],
                "time": ["quiet morning rush", "quiet midday"],
                "weather": [],
                "texture": [],
                "fx": [],
            },
            "cross_segment_time_consistency_room": {
                "environment": ["quiet station concourse"],
                "core": [],
                "props": [],
                "crowd": ["quiet weekday morning"],
                "time": ["evening stroll"],
                "weather": [],
                "texture": [],
                "fx": [],
            }
        }

        with patch.object(location_builder.background_vocab, "CONCEPT_PACKS", packs):
            prompts = [
                location_builder.expand_location_prompt(
                    "time_consistency_room",
                    seed,
                    "detailed",
                )
                for seed in range(80)
            ]
            cross_segment_prompts = [
                location_builder.expand_location_prompt(
                    "cross_segment_time_consistency_room",
                    seed,
                    "detailed",
                )
                for seed in range(160)
            ]
            action_prompts = [
                location_builder.expand_location_prompt(
                    "action_time_consistency_room",
                    seed,
                    "detailed",
                    action_text="during the evening rush",
                )
                for seed in range(80)
            ]

        midday_prompts = [prompt for prompt in prompts if "quiet midday" in prompt]
        self.assertEqual(midday_prompts, [])
        self.assertTrue(any("late night last train" in prompt for prompt in prompts))
        self.assertTrue(all("quiet morning rush" not in prompt for prompt in action_prompts))
        self.assertTrue(all("quiet midday" not in prompt for prompt in action_prompts))
        self.assertTrue(any("evening stroll" in prompt for prompt in cross_segment_prompts))
        evening_prompts = [prompt for prompt in cross_segment_prompts if "evening stroll" in prompt]
        self.assertTrue(all("quiet weekday morning" not in prompt for prompt in evening_prompts))

    def test_location_expansion_filters_daylight_environment_for_evening_action_seed_33(self):
        from pipeline.location_builder import expand_location_prompt

        kwargs = {
            "loc_tag": "clean_modern_kitchen",
            # ContextLocationExpander's resolved seed for blind-review master seed 33.
            "seed": 9463846182915048562,
            "mode": "detailed",
            "action_text": (
                "opening the stainless steel fridge close to where she needs to be, "
                "settling into a quieter pace, looking toward the next thing she needs, "
                "letting the pause settle properly, keeping to herself, "
                "as the last part falls into place, late in the evening"
            ),
        }
        first = expand_location_prompt(**kwargs)
        replay = expand_location_prompt(**kwargs)

        self.assertEqual(first, replay)
        self.assertIn("pristine modern kitchen with island", first)
        self.assertNotIn("bright sunlit breakfast nook", first)
        self.assertNotIn("morning sunlight", first)

    def test_breakfast_nook_anchor_does_not_cancel_explicit_evening_time(self):
        from pipeline.location_policy import filter_time_options_for_context

        action = "sitting at the breakfast nook with coffee, late in the evening"
        options = ["refreshing morning", "soft daylight", "warm ambient light"]

        self.assertEqual(filter_time_options_for_context(options, action), ["warm ambient light"])

    def test_g004_confirmation_conflict_seeds_filter_morning_location_segments(self):
        from tools.workflow_prompt_runner import build_canonical_record, load_profile
        from workflow_widget_validation import load_workflow

        root = Path(ROOT)
        workflow = load_workflow(root / "ComfyUI-workflow-context.json")
        profile = load_profile(root / "verification/fixtures/prompt_quality_supported_profile.json")
        failing_seeds = (10218210002619448939, 17005474289886835286)

        for seed in failing_seeds:
            with self.subTest(seed=seed):
                first = build_canonical_record(workflow, seed, profile=profile, cohort="confirmation")
                replay = build_canonical_record(workflow, seed, profile=profile, cohort="confirmation")
                self.assertEqual(first, replay)
                self.assertTrue(
                    any(cue in first["context"]["action"] for cue in ("evening", "night", "bed")),
                    msg=first["context"]["action"],
                )
                location_prompt = first["context"]["extras"]["location_prompt"].lower()
                self.assertNotIn("morning", location_prompt)
                self.assertNotIn("sunlit", location_prompt)

    def test_evening_context_filters_bright_terms_from_all_selectable_segment_categories(self):
        from pipeline.location_builder import expand_location_prompt

        cases = {
            "school_classroom": ("lunch break", "reflecting sunlight"),
            "bamboo_forest": ("sunlight filtering through leaves",),
            "wave_barrel": ("bright sunlight at the tunnel end", "sunlit mist"),
            "riverside_walk": ("sunlit asphalt path",),
            "rooftop_laundry_area": ("sunlit concrete roof surface",),
            "neighborhood_playground": ("sunlit painted metal equipment",),
        }
        action = "finishing the task late in the evening"

        for location, forbidden in cases.items():
            with self.subTest(location=location):
                first = [expand_location_prompt(location, seed, "detailed", action_text=action) for seed in range(64)]
                replay = [expand_location_prompt(location, seed, "detailed", action_text=action) for seed in range(64)]
                self.assertEqual(first, replay)
                joined = "\n".join(first).lower()
                for phrase in forbidden:
                    self.assertNotIn(phrase, joined)

    def test_final_review_seed_30_suppresses_fx_redundant_with_energetic_mood(self):
        import json
        from tools.workflow_prompt_runner import build_canonical_record, load_profile
        from workflow_widget_validation import load_workflow

        root = Path(ROOT)
        workflow = load_workflow(root / "ComfyUI-workflow-context.json")
        profile = load_profile(root / "verification/fixtures/prompt_quality_supported_profile.json")
        source = {
            "subj": "fitness model", "costume": "gym_workout", "loc": "karaoke_bar",
            "action": "checking a song title on the karaoke screen",
            "meta": {"mood": "energetic_joy", "tags": {"purpose": "leisure"}},
        }
        overrides = {"1": {"json_string": json.dumps(source), "source_mode": "json_only"},
                     "3": {"variation_mode": "original"}}
        first = build_canonical_record(workflow, 30, profile=profile, cohort="control", overrides=overrides)
        replay = build_canonical_record(workflow, 30, profile=profile, cohort="control", overrides=overrides)

        self.assertEqual(first, replay)
        self.assertEqual(first["context"]["loc"], "karaoke_bar")
        self.assertIn("kind of excitement", first["cleaned_prompt"])
        self.assertNotIn("energetic party vibe", first["cleaned_prompt"])
        self.assertNotIn("energetic party vibe", first["context"]["extras"]["location_prompt"])

    def test_energetic_fx_is_retained_when_context_has_no_overlapping_family(self):
        from unittest.mock import patch

        from pipeline import location_builder

        pack = {
            "environment": ["plain rehearsal room"],
            "core": [], "props": [], "texture": [], "time": [], "weather": [], "crowd": [],
            "fx": ["energetic party vibe"],
        }
        with patch.object(location_builder.background_vocab, "CONCEPT_PACKS", {"nonredundant_fx_room": pack}):
            first = [
                location_builder.expand_location_prompt(
                    "nonredundant_fx_room", seed, "detailed",
                    action_text="standing quietly near the wall", mood_text="calm_focus",
                )
                for seed in range(128)
            ]
            replay = [
                location_builder.expand_location_prompt(
                    "nonredundant_fx_room", seed, "detailed",
                    action_text="standing quietly near the wall", mood_text="calm_focus",
                )
                for seed in range(128)
            ]

        self.assertEqual(first, replay)
        self.assertTrue(any("energetic party vibe" in prompt for prompt in first))

    def test_fx_redundancy_classifier_uses_boundaries_and_does_not_match_substrings(self):
        from pipeline.location_policy import filter_semantic_redundant_fx

        self.assertEqual(
            filter_semantic_redundant_fx(["mist over lake surface"], "a gentle facial expression"),
            ["mist over lake surface"],
        )
        self.assertEqual(
            filter_semantic_redundant_fx(["breathtaking mountain light"], "taking a slow breath"),
            ["breathtaking mountain light"],
        )
        self.assertEqual(
            filter_semantic_redundant_fx(["energetic party vibe", "rotating reflections"], "energetic_joy"),
            ["rotating reflections"],
        )

    def test_shopping_mall_seed_27_filters_morning_crowd_after_night_weather(self):
        from pipeline.location_builder import expand_location_prompt

        first = expand_location_prompt("shopping_mall_atrium", 27, "detailed")
        replay = expand_location_prompt("shopping_mall_atrium", 27, "detailed")

        self.assertEqual(first, replay)
        self.assertIn("night sky through glass roof", first)
        self.assertNotIn("quiet weekday morning", first)

    def test_weather_and_crowd_time_context_is_cumulative_in_both_directions(self):
        from unittest.mock import patch

        from pipeline import location_builder

        def prompts_for(pack):
            with patch.object(location_builder.background_vocab, "CONCEPT_PACKS", {"cumulative_room": pack}):
                first = [location_builder.expand_location_prompt("cumulative_room", seed, "detailed") for seed in range(256)]
                replay = [location_builder.expand_location_prompt("cumulative_room", seed, "detailed") for seed in range(256)]
            self.assertEqual(first, replay)
            return first

        shared = {
            "environment": ["plain indoor room"], "core": [], "props": [], "texture": [],
            "time": [], "fx": [],
        }
        night_then_morning = prompts_for({
            **shared, "weather": ["night sky beyond the windows"], "crowd": ["quiet weekday morning"],
        })
        morning_then_night = prompts_for({
            **shared, "weather": ["soft morning sunlight"], "crowd": ["late night closing atmosphere"],
        })

        self.assertTrue(any("night sky beyond the windows" in prompt for prompt in night_then_morning))
        self.assertTrue(any("quiet weekday morning" in prompt for prompt in night_then_morning))
        self.assertFalse(any(
            "night sky beyond the windows" in prompt and "quiet weekday morning" in prompt
            for prompt in night_then_morning
        ))
        self.assertTrue(any("soft morning sunlight" in prompt for prompt in morning_then_night))
        self.assertTrue(any("late night closing atmosphere" in prompt for prompt in morning_then_night))
        self.assertFalse(any(
            "soft morning sunlight" in prompt and "late night closing atmosphere" in prompt
            for prompt in morning_then_night
        ))

    def test_location_expansion_uses_plain_connectors_for_core_and_props(self):
        from unittest.mock import patch

        from pipeline import location_builder

        packs = {
            "connector_room": {
                "environment": ["plain room"],
                "core": ["large movie poster", "ticket kiosk"],
                "props": ["small popcorn tub", "folded program"],
                "crowd": [],
                "time": [],
                "weather": [],
                "texture": [],
                "fx": [],
            }
        }

        with patch.object(location_builder.background_vocab, "CONCEPT_PACKS", packs):
            prompts = [
                location_builder.expand_location_prompt(
                    "connector_room",
                    seed,
                    "detailed",
                )
                for seed in range(50)
            ]

        joined = "\n".join(prompts).lower()
        self.assertNotIn("featuring large movie poster featuring ticket kiosk", joined)
        self.assertNotIn("featuring ticket kiosk featuring large movie poster", joined)
        self.assertNotIn("scattered with", joined)
        self.assertNotIn("filled with", joined)

    def test_location_expansion_avoids_repeating_background_object_classes(self):
        from unittest.mock import patch

        from pipeline import location_builder

        packs = {
            "repeat_room": {
                "environment": ["quiet lobby"],
                "core": ["large movie poster", "ticket kiosk"],
                "props": ["folded program"],
                "crowd": [],
                "time": [],
                "weather": [],
                "texture": [],
                "fx": [],
            }
        }

        with patch.object(location_builder.background_vocab, "CONCEPT_PACKS", packs):
            for seed in range(30):
                prompt, debug = location_builder.expand_location_prompt(
                    "repeat_room",
                    seed,
                    "detailed",
                    return_debug=True,
                )
                lowered = prompt.lower()
                self.assertFalse(
                    "large movie poster" in lowered and "ticket kiosk" in lowered,
                    msg=prompt,
                )
                self.assertLessEqual(len(debug["objects"]), 1)

    def test_location_segment_selector_prefers_semantic_scores_without_losing_determinism(self):
        import random

        from pipeline.location_segment_selector import semantic_choice, semantic_score_multiplier

        options = ["quiet reading tables", "overhead transit signs"]
        semantic_scores = {"quiet reading tables": 1.5, "overhead transit signs": 0.0}

        self.assertGreater(
            semantic_score_multiplier("quiet reading tables", semantic_scores),
            semantic_score_multiplier("overhead transit signs", semantic_scores),
        )
        self.assertEqual(
            semantic_choice(options, random.Random(4), semantic_scores),
            semantic_choice(options, random.Random(4), semantic_scores),
        )


class TestTimePhaseFiltering(unittest.TestCase):
    def test_morning_and_afternoon_options_are_mutually_exclusive(self):
        from pipeline.location_policy import filter_time_options_for_context

        options = ["fresh morning", "daytime", "late afternoon", "during the evening"]
        afternoon = filter_time_options_for_context(options, "in the late afternoon")
        morning = filter_time_options_for_context(options, "during fresh morning")

        self.assertNotIn("fresh morning", afternoon)
        self.assertIn("late afternoon", afternoon)
        self.assertNotIn("late afternoon", morning)
        self.assertIn("fresh morning", morning)

    def test_bedtime_context_rejects_morning_options(self):
        from pipeline.location_policy import filter_time_options_for_context

        options = ["lazy morning", "refreshing morning", "during quiet night"]

        for context in ("before sleeping", "before heading to bed"):
            with self.subTest(context=context):
                filtered = filter_time_options_for_context(options, context)
                self.assertNotIn("lazy morning", filtered)
                self.assertNotIn("refreshing morning", filtered)
                self.assertIn("during quiet night", filtered)


if __name__ == "__main__":
    unittest.main()
