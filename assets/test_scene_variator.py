import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pipeline.context_pipeline import (  # noqa: E402
    _build_exclusion_set,
    _get_compatible_locs,
    can_generate_action_for_location,
)
from registry import load_scene_compatibility  # noqa: E402


class TestSceneVariatorCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compat = load_scene_compatibility()
        cls.excluded = _build_exclusion_set(cls.compat)

    def test_full_mode_exposes_tagged_and_universal_locations(self):
        locs = _get_compatible_locs("business girl", self.compat, self.excluded, mode="full")
        sources = {source for _loc, source in locs}

        self.assertGreater(len(locs), 5)
        self.assertTrue(any(source.startswith("tag:") for source in sources))
        self.assertIn("universal", sources)

    def test_character_exclusions_still_apply(self):
        elf_locs = {
            loc
            for loc, _source in _get_compatible_locs(
                "blonde elf archer",
                self.compat,
                self.excluded,
                mode="full",
            )
        }
        cyber_locs = {
            loc
            for loc, _source in _get_compatible_locs(
                "cyberpunk girl",
                self.compat,
                self.excluded,
                mode="full",
            )
        }

        self.assertTrue({"modern_office", "boardroom", "commuter_transport", "street_cafe"}.isdisjoint(elf_locs))
        self.assertTrue({"shinto_shrine", "bamboo_forest", "botanical_garden", "picnic_park"}.isdisjoint(cyber_locs))

    def test_scene_candidate_pool_has_seed_diversity(self):
        locs = _get_compatible_locs("business girl", self.compat, self.excluded, mode="full")
        unique_locs = {loc for loc, _source in locs}

        self.assertGreater(len(unique_locs), 3)

    def test_all_compat_locations_can_generate_actions(self):
        all_locs = set()
        for tag_locs in self.compat["loc_tags"].values():
            all_locs.update(tag_locs)
        all_locs.update(self.compat["universal_locs"])

        missing = sorted(
            loc
            for loc in all_locs
            if not can_generate_action_for_location(loc, self.compat)
        )

        self.assertEqual(missing, [])

    def test_genre_only_mode_does_not_add_universal_source_candidates(self):
        genre_locs = _get_compatible_locs("business girl", self.compat, self.excluded, mode="genre_only")

        self.assertTrue(genre_locs)
        self.assertNotIn("universal", {source for _loc, source in genre_locs})


if __name__ == "__main__":
    unittest.main()
