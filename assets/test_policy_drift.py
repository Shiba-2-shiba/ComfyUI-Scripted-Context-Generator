import os
import sys
import unittest
from pathlib import Path


ROOT = Path(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(str(ROOT))

from asset_validator import _TARGETED_BANNED_ASSETS, find_banned_asset_terms
from core.semantic_policy import find_banned_terms
from nodes_prompt_cleaner import PromptCleaner


class TestPolicyDrift(unittest.TestCase):
    def setUp(self):
        self.cleaner = PromptCleaner()

    def _cleaner_blocks(self, text):
        return self.cleaner.clean(text=text)[0] != text

    def test_policy_drift_matrix_documents_current_mismatches(self):
        report = {
            "close-up": {
                "semantic": bool(find_banned_terms("close-up")),
                "validator": bool(find_banned_asset_terms("close-up")),
                "cleaner": self._cleaner_blocks("close-up"),
            },
            "volumetric lighting": {
                "semantic": bool(find_banned_terms("volumetric lighting")),
                "validator": bool(find_banned_asset_terms("volumetric lighting")),
                "cleaner": self._cleaner_blocks("volumetric lighting"),
            },
            "slim-fit jacket": {
                "semantic": bool(find_banned_terms("slim-fit jacket")),
                "validator": bool(find_banned_asset_terms("slim-fit jacket")),
                "cleaner": self._cleaner_blocks("slim-fit jacket"),
            },
        }

        self.assertEqual(
            report,
            {
                "close-up": {"semantic": True, "validator": True, "cleaner": True},
                "volumetric lighting": {"semantic": False, "validator": False, "cleaner": True},
                "slim-fit jacket": {"semantic": True, "validator": False, "cleaner": True},
            },
        )

    def test_validator_banned_term_scope_is_still_targeted(self):
        data_assets = {
            path.name for path in (ROOT / "vocab" / "data").glob("*.json")
        }
        targeted_assets = set(_TARGETED_BANNED_ASSETS)

        self.assertTrue(targeted_assets.issubset(data_assets))
        self.assertIn("background_packs.json", targeted_assets)
        self.assertIn("background_defaults.json", targeted_assets)
        self.assertIn("clothing_packs.json", targeted_assets)
        self.assertIn("garnish_base_vocab.json", targeted_assets)
        self.assertIn("garnish_exclusive_groups.json", targeted_assets)
        self.assertIn("garnish_micro_actions.json", targeted_assets)


if __name__ == "__main__":
    unittest.main()
