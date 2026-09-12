import unittest

from core.semantic_families import semantic_families_for_text


class TestSemanticFamilyTokenBoundaries(unittest.TestCase):
    def test_location_overlooking_does_not_count_as_protagonist_gaze(self):
        self.assertNotIn(
            "gaze",
            semantic_families_for_text("small apartment balcony overlooking the street"),
        )

    def test_clothing_sleeves_do_not_count_as_hand_action(self):
        self.assertNotIn(
            "hands",
            semantic_families_for_text("black cotton twill rolled sleeves structured wrap dress"),
        )

    def test_exact_action_terms_still_map_to_semantic_families(self):
        self.assertEqual(
            semantic_families_for_text("her eyes follow the detail while her fingers tighten"),
            {"gaze", "hands"},
        )


if __name__ == "__main__":
    unittest.main()
