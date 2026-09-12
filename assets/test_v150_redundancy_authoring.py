"""Prospective authoring invariants, separate from live candidate quality gates."""
from pathlib import Path
import re
import unittest

from tools.analyze_variation_candidates import load_candidate_catalog

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "docs/variation_expansion/experiments"


class TestV150RedundancyAuthoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = load_candidate_catalog(EXPERIMENTS / "v150-final-v7-20260905/candidate-iteration.json")
        cls.candidate = load_candidate_catalog(EXPERIMENTS / "v150-v7-redundancy-remediation-20260905/candidate-iteration.json")
        cls.locations = {item["id"]: item for item in cls.candidate["locations"]}

    def test_only_background_wording_changes_not_counted_surface(self):
        self.assertEqual(self.candidate["subjects"], self.original["subjects"])
        self.assertEqual(len(self.locations), 19)
        originals = {item["id"]: item for item in self.original["locations"]}
        self.assertEqual(set(self.locations), set(originals))
        for key, location in self.locations.items():
            self.assertEqual({k: v for k, v in location.items() if k != "background_pack"},
                             {k: v for k, v in originals[key].items() if k != "background_pack"})
            self.assertEqual(len(location["action_plan"]["direct_actions"]), 20)
            self.assertEqual(location["background_pack"]["aliases"], originals[key]["background_pack"]["aliases"])

    def test_concise_identity_labels_leave_objects_to_rich_detail_slots(self):
        for key, location in self.locations.items():
            pack = location["background_pack"]
            with self.subTest(location=key):
                self.assertGreaterEqual(len(pack["environment"]), 2)
                for label in pack["environment"]:
                    self.assertLessEqual(len(label.split()), 9, label)
                    self.assertNotRegex(label, r"(?i)\b(filled with|lined with|centered on|opening onto)\b")
                for slot, minimum in (("core", 4), ("props", 4), ("texture", 2), ("time", 2), ("crowd", 2)):
                    self.assertGreaterEqual(len(pack[slot]), minimum, slot)
                    self.assertEqual(len(pack[slot]), len(set(pack[slot])), slot)

    def test_reviewed_anchor_details_have_one_home(self):
        groups = {
            "fire_station": ("readiness",),
            "greenhouse_nursery": ("seedlings?", "roof(?: panels?| panes?)?"),
            "public_plaza": ("fountain", "monument", "geometric"),
            "forest_cabin": ("porch", "firewood"),
        }
        for location, anchors in groups.items():
            pack = self.locations[location]["background_pack"]
            text = " ".join(term for slot, terms in pack.items() if slot != "aliases" for term in terms)
            for anchor in anchors:
                with self.subTest(location=location, anchor=anchor):
                    self.assertEqual(len(re.findall(rf"\b(?:{anchor})\b", text, flags=re.I)), 1)


if __name__ == "__main__":
    unittest.main()
