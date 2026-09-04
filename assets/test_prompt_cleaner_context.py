import unittest

from nodes_prompt_cleaner import PromptCleaner


class PromptCleanerContextTests(unittest.TestCase):
    def test_botanical_bloom_action_is_preserved(self):
        cleaner = PromptCleaner()
        text = "a solo girl, comparing bloom sizes across two display buckets, calm expression"
        cleaned, = cleaner.clean(text=text)
        self.assertIn("comparing bloom sizes across two display buckets", cleaned)

    def test_standalone_bloom_fx_is_removed(self):
        cleaner = PromptCleaner()
        cleaned, = cleaner.clean(text="a solo girl, bloom, calm expression")
        self.assertNotIn("bloom", cleaned)
        self.assertIn("calm expression", cleaned)


if __name__ == "__main__":
    unittest.main()
