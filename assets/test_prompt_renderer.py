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


if __name__ == "__main__":
    unittest.main()
