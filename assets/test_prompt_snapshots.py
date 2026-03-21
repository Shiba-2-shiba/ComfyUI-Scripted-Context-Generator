import json
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(str(ROOT))

from core.context_ops import patch_context
from core.semantic_policy import find_banned_terms
from pipeline.clothing_builder import apply_clothing_expansion
from pipeline.location_builder import apply_location_expansion
from pipeline.prompt_orchestrator import build_prompt_from_context
from pipeline.context_pipeline import apply_garnish


SNAPSHOT_FIXTURE_PATH = ROOT / "assets" / "fixtures" / "prompt_snapshot_cases.json"
REQUIRED_CATEGORIES = {
    "daily_life_school",
    "daily_life_office",
    "daily_life_suburban",
    "japanese",
    "fantasy",
    "sci_fi",
}


class TestPromptSnapshots(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.snapshot_cases = json.loads(SNAPSHOT_FIXTURE_PATH.read_text(encoding="utf-8"))

    def _build_prompt(self, case):
        ctx = patch_context(
            {},
            updates={
                "subj": case["subj"],
                "costume": case["costume"],
                "loc": case["loc"],
                "action": case["action"],
                "seed": case["seed"],
            },
            meta={"mood": case["mood"]},
        )
        ctx, _clothing = apply_clothing_expansion(
            ctx,
            case["seed"],
            "random",
            0.3,
            case["palette"],
        )
        ctx, _location = apply_location_expansion(ctx, case["seed"], "detailed", "off")
        ctx, _garnish, _debug = apply_garnish(
            ctx,
            case["seed"],
            3,
            False,
            emotion_nuance=case["nuance"],
            personality=case["personality"],
        )
        _ctx, prompt = build_prompt_from_context(ctx, "", True, case["seed"])
        return prompt

    def test_snapshot_matrix_covers_required_categories(self):
        categories = {case["category"] for case in self.snapshot_cases}
        self.assertEqual(categories, REQUIRED_CATEGORIES)

    def test_prompt_snapshots_match_expected_outputs(self):
        for case in self.snapshot_cases:
            with self.subTest(case=case["name"]):
                prompt = self._build_prompt(case)
                self.assertEqual(prompt, case["expected_prompt"])
                self.assertEqual(find_banned_terms(prompt), {})


if __name__ == "__main__":
    unittest.main()
