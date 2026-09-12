import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from asset_validator import find_banned_asset_terms
from core.semantic_policy import contains_banned_terms
from nodes_prompt_cleaner import PromptCleaner


class TestPolicyAlignment(unittest.TestCase):
    def setUp(self):
        self.cleaner = PromptCleaner()

    def test_shared_banned_terms_are_removed_by_cleaner(self):
        text = "anime illustration, highly detailed textures, soft lighting, close-up, a solo girl in a classroom"
        cleaned = self.cleaner.clean(text=text)[0]

        self.assertFalse(contains_banned_terms(cleaned))
        self.assertEqual(find_banned_asset_terms(cleaned), [])
        self.assertIn("a solo girl in a classroom", cleaned)

    def test_shared_term_samples_match_runtime_and_validator_detection(self):
        for sample in (
            "anime illustration",
            "highly detailed textures",
            "soft lighting",
            "close-up",
            "lens flare",
        ):
            with self.subTest(sample=sample):
                self.assertTrue(contains_banned_terms(sample))
                self.assertTrue(find_banned_asset_terms(sample))


if __name__ == "__main__":
    unittest.main()
