import unittest

from pipeline.location_builder import (
    _filter_action_redundant_options,
    _filter_spatial_environment_options,
)


class LocationSpatialContextTests(unittest.TestCase):
    def test_exterior_action_prefers_exterior_environment(self):
        options = [
            "warm timber cabin interior with an iron stove",
            "conifer clearing beside the cabin steps",
        ]
        self.assertEqual(
            _filter_spatial_environment_options(
                options,
                "studying fresh tracks beside the cabin steps",
            ),
            ["conifer clearing beside the cabin steps"],
        )

    def test_neutral_action_preserves_environment_options(self):
        options = ["quiet workshop interior", "covered yard beside the workshop"]
        self.assertEqual(
            _filter_spatial_environment_options(options, "checking a service note"),
            options,
        )

    def test_scene_option_repeating_two_action_anchors_is_removed(self):
        options = [
            "arched pedestrian bridge and weathered waterside railing",
            "stone steps descending toward the canal",
        ]
        self.assertEqual(
            _filter_action_redundant_options(
                options,
                "resting a hand on the weathered railing",
            ),
            ["stone steps descending toward the canal"],
        )

    def test_action_anchor_filter_preserves_only_available_option(self):
        options = ["weathered waterside railing"]
        self.assertEqual(
            _filter_action_redundant_options(options, "resting on the weathered railing"),
            options,
        )


if __name__ == "__main__":
    unittest.main()
