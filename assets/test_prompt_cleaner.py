import unittest
import sys
import os

# Add parent directory to path to import nodes_prompt_cleaner
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from nodes_prompt_cleaner import PromptCleaner

class TestPromptCleaner(unittest.TestCase):
    def setUp(self):
        self.cleaner = PromptCleaner()

    def clean(self, text, mode="nl"):
        # The node returns a tuple (string,)
        return self.cleaner.clean(mode=mode, text=text)[0]

    def test_text_input_is_optional_for_layout_stability(self):
        specs = PromptCleaner.INPUT_TYPES()
        self.assertNotIn("text", specs.get("required", {}))
        self.assertIn("text", specs.get("optional", {}))

    def test_basic_cleaning(self):
        # Basic whitespace and punctuation
        self.assertEqual(self.clean("hello , world ."), "hello, world.")
        self.assertEqual(self.clean("hello  world"), "hello world")
        self.assertEqual(self.clean("line1\n\n\nline2"), "line1\nline2")

    def test_empty_brackets(self):
        self.assertEqual(self.clean("subject () with []"), "subject")
        self.assertEqual(self.clean("(( weighted ))"), "(( weighted ))") # Should preserve weights

    def test_consecutive_punctuation(self):
        self.assertEqual(self.clean("word, , next"), "word, next")
        self.assertEqual(self.clean("end.."), "end.")
        self.assertEqual(self.clean("end..."), "end.") # Current logic collapses all dots? Check implementation.
        # Implementation says: re.sub(r"\.\s*\.+", ".", s) -> Yes, it collapses multiple dots to one.
        
    def test_dangling_words(self):
        self.assertEqual(self.clean("girl and ."), "girl.")
        self.assertEqual(self.clean("boy with ,"), "boy") # Dedupe removes trailing comma

    def test_nl_extras(self):
        # "is, filled" -> "is filled"
        self.assertEqual(self.clean("The room is, filled with light", mode="nl"), "The room is filled with light")
        
    def test_articles(self):
        # A/An correction
        self.assertEqual(self.clean("a apple"), "an apple")
        self.assertEqual(self.clean("an banana"), "a banana")
        self.assertEqual(self.clean("a hour"), "an hour") # Exception
        self.assertEqual(self.clean("an unicorn"), "a unicorn") # Exception
        self.assertEqual(self.clean("This is a apple."), "This is an apple.") # In sentence

    def test_deduplication(self):
        # Deduplication of comma separated items
        self.assertEqual(self.clean("tag1, tag2, tag1"), "tag1, tag2")
        self.assertEqual(self.clean("tag1, tag2, Tag1"), "tag1, tag2") # Case insensitive dedupe
        self.assertEqual(self.clean("tag1, , tag2"), "tag1, tag2") # Empty item removal + dedupe
        
    def test_pipeline_integration(self):
        # Complex case
        raw = "a apple, red, red, .  "
        # 1. brackets -> "a apple, red, red, .  "
        # 2. punct spacing -> "a apple, red, red, . "
        # 3. articles -> "an apple, red, red, . "
        # 4. dedupe -> "an apple, red, ."
        # 5. consecutive punct -> "an apple, red."
        # 6. dangling -> "an apple, red."
        # 7. sentence spacing -> "an apple, red. "
        # 8. nl extras -> "an apple, red. "
        # 9. whitespace -> "an apple, red."
        self.assertEqual(self.clean(raw), "an apple, red.")

    def test_fx_guardrail(self):
        raw = "sparkling eyes, snowflakes, confetti in the air, beautiful bokeh lights, lens flare, magical sparkles floating in air"
        self.assertEqual(self.clean(raw), "sparkling eyes, snowflakes")

    def test_shared_banned_domain_terms_are_removed(self):
        cleaned = self.clean("close-up, soft lighting, highly detailed textures, anime illustration, classroom")
        self.assertEqual(cleaned, "classroom")

if __name__ == '__main__':
    unittest.main()
