import unittest

import prompt_renderer
from tools.build_prompt_quality_confirmation import _apply_baseline_ablation


class ConfirmationAblationBoundaryTests(unittest.TestCase):
    def test_g005_ablation_restores_legacy_staging_punctuation(self):
        original_normalizer = prompt_renderer.normalize_composition_punctuation
        original_append = prompt_renderer._append_staging_tags
        try:
            feature = _apply_baseline_ablation("g005")
            self.assertEqual(feature, "disable_composition_punctuation_normalization")
            self.assertEqual(
                prompt_renderer._append_staging_tags("scene.", "careful hands"),
                "scene., careful hands",
            )
        finally:
            prompt_renderer.normalize_composition_punctuation = original_normalizer
            prompt_renderer._append_staging_tags = original_append


if __name__ == "__main__":
    unittest.main()
