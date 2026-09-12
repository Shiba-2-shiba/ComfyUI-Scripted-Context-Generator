import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestSemanticSpace(unittest.TestCase):
    def test_rank_candidates_prefers_closest_vector(self):
        from vocab.semantic_space import rank_candidates

        ranked = rank_candidates(
            [
                {"text": "low energy", "vector": {"energy": 0.1, "precision": 0.8}},
                {"text": "high energy", "vector": {"energy": 0.9, "precision": 0.2}},
            ],
            {"energy": 0.2, "precision": 0.75},
            ["energy", "precision"],
        )

        self.assertEqual(ranked[0]["text"], "low energy")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])

    def test_rank_candidates_is_deterministic_for_ties(self):
        from vocab.semantic_space import rank_candidates

        ranked = rank_candidates(
            [
                {"text": "beta", "vector": {"axis": 0.5}},
                {"text": "alpha", "vector": {"axis": 0.5}},
            ],
            {"axis": 0.5},
            ["axis"],
        )

        self.assertEqual([item["text"] for item in ranked], ["alpha", "beta"])

    def test_missing_axis_defaults_to_midpoint(self):
        from vocab.semantic_space import normalize_vector

        self.assertEqual(normalize_vector({"known": 0.25}, ["known", "missing"]), {"known": 0.25, "missing": 0.5})

    def test_validate_axis_payload_flags_schema_and_vector_errors(self):
        from vocab.semantic_space import validate_axis_payload

        warnings = validate_axis_payload(
            {
                "schema_version": "1.0",
                "axes": ["energy", "precision"],
                "descriptors": {
                    "slot": [
                        {"text": "bad", "vector": {"energy": 1.5, "unknown": 0.2}},
                    ]
                },
            },
            required_axes=["energy", "precision", "social"],
        )

        self.assertTrue(any("missing required axis 'social'" in item for item in warnings))
        self.assertTrue(any("energy must be between" in item for item in warnings))
        self.assertTrue(any("unknown is not declared" in item for item in warnings))
        self.assertTrue(any("missing axis 'precision'" in item for item in warnings))


if __name__ == "__main__":
    unittest.main()
