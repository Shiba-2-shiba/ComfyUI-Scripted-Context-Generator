import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from core.semantic_policy import (
    contains_banned_terms,
    filter_candidate_strings,
    find_banned_term_matches,
    normalize_fragment_text,
    sanitize_text,
)


class TestSemanticPolicy(unittest.TestCase):
    def test_sanitize_text_removes_banned_render_and_camera_terms(self):
        text = "soft lighting, close-up, a solo girl in a classroom"
        cleaned = sanitize_text(text)
        self.assertNotIn("soft lighting", cleaned.lower())
        self.assertNotIn("close-up", cleaned.lower())
        self.assertIn("classroom", cleaned.lower())

    def test_filter_candidate_strings_drops_banned_candidates(self):
        filtered = filter_candidate_strings([
            "soft lighting",
            "depth of field",
            "quiet afternoon hallway",
        ])
        self.assertEqual(filtered, ["quiet afternoon hallway"])

    def test_contains_banned_terms_detects_quality_terms(self):
        self.assertTrue(contains_banned_terms("highly detailed textures"))
        self.assertFalse(contains_banned_terms("during a lunch break"))

    def test_find_banned_term_matches_can_ignore_hyphenated_body_type_false_positives(self):
        self.assertEqual(
            find_banned_term_matches("slim-fit jacket"),
            [("body_type", "slim")],
        )
        self.assertEqual(
            find_banned_term_matches("slim-fit jacket", ignore_hyphenated_body_type=True),
            [],
        )

    def test_normalize_fragment_text_is_shared_compact_cleanup_only(self):
        self.assertEqual(
            normalize_fragment_text("hello , world ."),
            "hello, world.",
        )
        self.assertEqual(
            sanitize_text("a apple, soft lighting"),
            "a apple",
        )


if __name__ == "__main__":
    unittest.main()
