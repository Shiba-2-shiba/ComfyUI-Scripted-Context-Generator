"""Keep the diversity refactor on its independently measured V150 base."""

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from assets.calc_variations import calc_base_metrics  # noqa: E402
from tools.check_variation_scope import load_variation_scope  # noqa: E402


# Independent of variation_scope.json: expanding data and its expectations together
# must not silently advance this wave. Update only with a dedicated correction task
# and before/after evidence under docs/diversity_refactor/spec.md section 2.2.
V150_BASELINE = {
    "unique_subjects": 135,
    "unique_locations": 109,
    "total_base_variations": 150184,
    "row_count": 8227,
}


class TestV150FreezeContract(unittest.TestCase):
    def test_runtime_base_remains_v150(self):
        metrics = calc_base_metrics(ROOT)

        self.assertEqual({key: metrics[key] for key in V150_BASELINE}, V150_BASELINE)
        self.assertEqual(metrics["missing_pools_count"], 0)

    def test_scope_cannot_silently_advance_to_a_larger_target(self):
        scope = load_variation_scope()

        self.assertEqual(
            {key: scope["expected_metrics"][key] for key in V150_BASELINE},
            V150_BASELINE,
        )
        self.assertEqual(len(set(scope["variation_subjects"])), V150_BASELINE["unique_subjects"])
        self.assertEqual(len(set(scope["variation_locations"])), V150_BASELINE["unique_locations"])


if __name__ == "__main__":
    unittest.main()
