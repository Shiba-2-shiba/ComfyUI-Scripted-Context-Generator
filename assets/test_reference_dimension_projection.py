import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestReferenceDimensionProjection(unittest.TestCase):
    def _write_fixture_repo(self, repo: Path) -> None:
        data = repo / "vocab" / "data"
        garnish = repo / "vocab" / "garnish"
        actions = repo / "vocab" / "source" / "action_pools"
        data.mkdir(parents=True)
        garnish.mkdir(parents=True)
        actions.mkdir(parents=True)
        (data / "personality_behavior_profiles.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "axes": ["sociability", "restraint", "confidence", "curiosity", "meticulousness", "warmth"],
                    "profiles": {
                        "confident": {
                            "vector": {
                                "sociability": 0.8,
                                "restraint": 0.2,
                                "confidence": 0.9,
                                "curiosity": 0.5,
                                "meticulousness": 0.5,
                                "warmth": 0.6,
                            }
                        }
                    },
                    "descriptors": {
                        "posture": [
                            {
                                "text": "steady stance",
                                "vector": {
                                    "sociability": 0.7,
                                    "restraint": 0.25,
                                    "confidence": 0.85,
                                    "curiosity": 0.5,
                                    "meticulousness": 0.5,
                                    "warmth": 0.6,
                                },
                            },
                            {
                                "text": "folded posture",
                                "vector": {
                                    "sociability": 0.2,
                                    "restraint": 0.9,
                                    "confidence": 0.2,
                                    "curiosity": 0.5,
                                    "meticulousness": 0.5,
                                    "warmth": 0.3,
                                },
                            },
                        ]
                    },
                }
            ),
            encoding="utf-8",
        )
        (data / "sample.json").write_text('{"prompt":"steady stance and folded posture"}', encoding="utf-8")
        (garnish / "logic.py").write_text("EMOTION_MODEL = {'focus': {'posture': ['steady stance']}}\n", encoding="utf-8")
        (actions / "sample.json").write_text('{"actions":["steady stance"]}', encoding="utf-8")

    def _write_fixture_refs(self, refs: Path) -> None:
        epig_data = refs / "EPIG" / "data"
        epig_data.mkdir(parents=True)
        (epig_data / "NRC_VAD_with_subject_centric.csv").write_text(
            "Word,Valence,Arousal,Dominance,subject_centric\n"
            "steady stance,0.7,0.4,0.9,1\n"
            "folded posture,0.3,0.3,0.2,1\n",
            encoding="utf-8",
        )
        ed_lexicons = refs / "EmotionDynamics" / "lexicons"
        ed_lexicons.mkdir(parents=True)
        (ed_lexicons / "NRC_VAD_valence.csv").write_text("word,val\nsteady stance,0.7\n", encoding="utf-8")

    def test_projection_audit_reports_rank_deltas_and_coverage(self):
        from tools.audit_reference_dimension_projection import audit_reference_dimension_projection

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "repo"
            refs = root / "refs"
            self._write_fixture_repo(repo)
            self._write_fixture_refs(refs)

            result = audit_reference_dimension_projection(repo, refs)

        self.assertEqual(result["generated_kind"], "reference_dimension_projection_audit")
        self.assertGreaterEqual(result["personality_dominance_projection"]["comparison_count"], 1)
        self.assertGreaterEqual(result["current_vocabulary_coverage"]["exact_match_count"], 1)
        self.assertIn("valence", result["current_vocabulary_coverage"]["average_vad"])
        self.assertFalse(result["optional_lexicons"]["worrywords_available"])
        self.assertFalse(result["optional_lexicons"]["words_of_warmth_available"])
        self.assertTrue(result["policy"]["runtime_output_unchanged"])

    def test_write_audit_creates_json(self):
        from tools.audit_reference_dimension_projection import audit_reference_dimension_projection, write_audit

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "repo"
            refs = root / "refs"
            output = root / "out" / "projection.json"
            self._write_fixture_repo(repo)
            self._write_fixture_refs(refs)

            result = audit_reference_dimension_projection(repo, refs)
            written = write_audit(result, output)
            payload = json.loads(written.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_version"], "1.0")
        self.assertTrue(payload["personality_dominance_projection"]["records"])


if __name__ == "__main__":
    unittest.main()
