import json
import os
import sys
import unittest
from collections import Counter


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from core.semantic_families import semantic_families_for_text


class TestMoodMapRepetitionControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "mood_map.json"), "r", encoding="utf-8") as handle:
            cls.mood_map = json.load(handle)

    def test_high_frequency_mood_descriptions_avoid_tracked_body_families(self):
        for mood_key in ("quiet_focused", "peaceful_relaxed"):
            descriptions = self.mood_map[mood_key]["description"]
            for description in descriptions:
                self.assertEqual(
                    semantic_families_for_text(description),
                    set(),
                    msg=f"mood={mood_key} description={description}",
                )

    def test_high_frequency_mood_staging_has_no_breath_family_and_no_duplicate_family_slots(self):
        for mood_key in ("quiet_focused", "peaceful_relaxed"):
            family_counts = Counter()
            for tag in self.mood_map[mood_key]["staging_tags"]:
                families = semantic_families_for_text(tag)
                self.assertNotIn(
                    "breath",
                    families,
                    msg=f"mood={mood_key} tag={tag}",
                )
                for family in families:
                    family_counts[family] += 1

            self.assertTrue(
                all(count <= 1 for count in family_counts.values()),
                msg=f"mood={mood_key} family_counts={dict(family_counts)}",
            )


if __name__ == "__main__":
    unittest.main()
