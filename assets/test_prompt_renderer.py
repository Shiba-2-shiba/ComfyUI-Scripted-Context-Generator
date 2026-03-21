import os
import sys
import unittest
import logging


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from prompt_renderer import _normalize_prompt, build_prompt_text, logger


class TestPromptRenderer(unittest.TestCase):
    def test_prompt_renderer_does_not_attach_file_logging_by_default(self):
        self.assertFalse(
            any(isinstance(handler, logging.FileHandler) for handler in logger.handlers),
            "prompt_renderer should not write debug logs unless explicitly enabled",
        )

    def test_build_prompt_text_composes_prompt_without_deprecated_style(self):
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
            meta_style="photo",
            return_debug=True,
        )
        self.assertIsInstance(prompt, str)
        self.assertIn("template_roles", debug)
        self.assertNotIn("photo", prompt.lower())

    def test_normalize_prompt_uses_shared_semantic_sanitization(self):
        self.assertEqual(
            _normalize_prompt("soft lighting, hallway , ."),
            "hallway",
        )

    def test_build_prompt_text_applies_semantic_family_budget_across_layers(self):
        prompt, debug = build_prompt_text(
            template="{action_clause}. {meta_mood}.",
            composition_mode=False,
            seed=7,
            subj="girl",
            costume="dress",
            loc="room",
            action="looking out the window, one hand holding the curtain",
            garnish="steady gaze, one hand near her chest, relaxed posture, focused expression",
            meta_mood="the room settling while her breathing slows and her expression stays calm",
            staging_tags="slow breath, downcast gaze, loose hands, still posture, calm expression",
            return_debug=True,
        )
        self.assertIn("relaxed posture", prompt)
        self.assertNotIn("steady gaze", prompt)
        self.assertNotIn("one hand near her chest", prompt)
        self.assertNotIn("focused expression", prompt)
        self.assertNotIn("slow breath", prompt)
        self.assertNotIn("downcast gaze", prompt)
        self.assertNotIn("loose hands", prompt)
        self.assertNotIn("still posture", prompt)
        self.assertNotIn("calm expression", prompt)
        self.assertIn("semantic_family_budget", debug)
        self.assertIn("gaze", debug["semantic_family_budget"]["base_families"])
        self.assertIn("breath", debug["semantic_family_budget"]["base_families"])

    def test_build_prompt_text_keeps_punctuation_clean_when_semantic_budget_drops_all_addons(self):
        prompt = build_prompt_text(
            template="{action_clause}. {meta_mood}.",
            composition_mode=False,
            seed=9,
            subj="girl",
            costume="dress",
            loc="room",
            action="looking down, hands gripping a bag, shoulders tense",
            garnish="steady gaze, loose hands",
            meta_mood="her breathing stays even and her expression does not change",
            staging_tags="slow breath, downcast gaze, still posture, careful hands",
        )
        self.assertNotIn(", ,", prompt)
        self.assertNotIn("steady gaze", prompt)
        self.assertNotIn("slow breath", prompt)
        self.assertNotIn("downcast gaze", prompt)
        self.assertNotIn("careful hands", prompt)


if __name__ == "__main__":
    unittest.main()
