import os
import sys
import unittest
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from vocab.garnish import logic as garnish_logic


class TestSoloSafety(unittest.TestCase):
    def test_garnish_filters_people_and_spill_artifacts(self):
        unsafe_model = {
            "expression": ["looking at someone with care"],
            "gaze": ["watching people pass by"],
            "mouth": ["dabbing stain with napkin"],
            "posture": ["standing calmly"],
            "hands": ["holding wet sleeve away"],
            "behavior": ["keeping close without crowding"],
        }

        with patch.dict(garnish_logic.EMOTION_MODEL, {"care": unsafe_model}):
            tags = garnish_logic.sample_garnish(
                seed=7,
                meta_mood="care",
                action_text="standing still",
                max_items=6,
                context_loc="modern_office",
            )

        lowered = ", ".join(tags).lower()
        self.assertIn("standing calmly", lowered)
        self.assertNotIn("someone", lowered)
        self.assertNotIn("people", lowered)
        self.assertNotIn("pass by", lowered)
        self.assertNotIn("stain", lowered)
        self.assertNotIn("napkin", lowered)
        self.assertNotIn("wet sleeve", lowered)
        self.assertNotIn("crowd", lowered)


if __name__ == "__main__":
    unittest.main()
