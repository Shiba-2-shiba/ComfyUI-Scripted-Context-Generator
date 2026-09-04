import unittest

from prompt_renderer import (
    _arbitrate_prompt_cues,
    _prune_action_incompatible_fillers,
    _prune_redundant_prompt_fillers,
    build_prompt_text,
)


class PromptCueArbitrationTests(unittest.TestCase):
    def test_exact_garnish_drop_does_not_starve_staging_family(self):
        result = _arbitrate_prompt_cues(
            action="checking the display",
            garnish="one hand near the display",
            meta_mood="quiet focus",
            staging_tags="careful hands",
            action_frame={"hand_action": "one hand near the display"},
            composition_mode=True,
        )
        self.assertEqual(result["garnish"], "")
        self.assertEqual(result["staging_tags"], "careful hands")
        self.assertEqual(result["debug"]["exact_redundancy_dropped"], ["one hand near the display"])

    def test_staging_without_placeholder_is_inserted_before_terminal_period(self):
        prompt = build_prompt_text(
            template="{subject_clause}, {action_clause}, {scene_clause}.",
            composition_mode=False,
            seed=1,
            subj="solo girl",
            costume="blue coat",
            loc="quiet station",
            action="checking the timetable",
            garnish="steady gaze",
            meta_mood="late evening",
            staging_tags="careful hands",
        )
        self.assertNotIn(".,", prompt)
        self.assertIn("late evening, careful hands", prompt)

    def test_redundant_composition_fillers_are_bounded(self):
        prompt = _prune_redundant_prompt_fillers(
            "right where her attention settles, measuring a component, "
            "leaving room for the rest of the scene, with everything else held at the edge"
        )
        self.assertIn("measuring a component", prompt)
        self.assertLessEqual(
            sum(
                phrase in prompt
                for phrase in (
                    "right where her attention settles",
                    "leaving room for the rest of the scene",
                    "with everything else held at the edge",
                )
            ),
            1,
        )

    def test_next_part_filler_keeps_location_clause(self):
        prompt = _prune_redundant_prompt_fillers(
            "moving with the next part of the day, checking a plaza map, "
            "with the next part of the day waiting in open civic plaza"
        )
        self.assertNotIn("next part of the day", prompt)
        self.assertEqual(prompt, "checking a plaza map, in open civic plaza")

    def test_active_action_removes_stasis_but_keeps_scene(self):
        prompt = _prune_action_incompatible_fillers(
            "caught in a brief pause, placing a price tag beside a potted plant, "
            "the moment lingering in a sunlit greenhouse, "
            "the moment kept deliberate rather than urgent",
            "placing a price tag beside a potted plant",
        )
        self.assertEqual(
            prompt,
            "placing a price tag beside a potted plant, in a sunlit greenhouse",
        )

    def test_low_value_scaffolding_is_removed_around_core_action(self):
        prompt = _prune_redundant_prompt_fillers(
            "caught in a brief pause, keeping to the edge of the moment, "
            "gathering herself for what comes next, comparing a machined part, "
            "holding herself with easy energy, the moment staying with her, "
            "turned toward the next exchange, the moment gathering around her, "
            "the moment lingering in a bright fabrication studio, "
            "the moment kept deliberate rather than urgent, "
            "measured pause"
        )
        self.assertEqual(
            prompt,
            "comparing a machined part, in a bright fabrication studio",
        )


if __name__ == "__main__":
    unittest.main()
