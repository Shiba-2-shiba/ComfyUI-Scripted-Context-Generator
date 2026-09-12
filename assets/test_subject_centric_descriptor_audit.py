import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestSubjectCentricDescriptorAudit(unittest.TestCase):
    def _write_fixture_repo(self, repo: Path) -> None:
        data = repo / "vocab" / "data"
        garnish = repo / "vocab" / "garnish"
        data.mkdir(parents=True)
        garnish.mkdir(parents=True)
        (data / "garnish_base_vocab.json").write_text(
            json.dumps(
                {
                    "POSE_STANDING": ["focused gaze", "leaning toward viewer"],
                    "VIEW_FRAMING": ["wide angle"],
                    "MOUTH_BASE": ["unknown expression"],
                }
            ),
            encoding="utf-8",
        )
        (data / "personality_behavior_profiles.json").write_text(
            json.dumps(
                {
                    "descriptors": {
                        "gaze": [
                            {"text": "focused gaze"},
                            {"text": "gentle posture"},
                        ],
                        "posture": [{"text": "unknown expression"}],
                    }
                }
            ),
            encoding="utf-8",
        )
        (data / "garnish_micro_actions.json").write_text(
            json.dumps(
                {
                    "daily_life": {
                        "triggers": ["focus"],
                        "generic": ["checking phone anxiously", "adrenaline rush"],
                        "specific": {"phone": ["holding phone"]},
                    }
                }
            ),
            encoding="utf-8",
        )
        (garnish / "logic.py").write_text(
            "PERSONALITY_GARNISH_BIAS = {'shy': {'prefer': ['soft smile'], 'prefer_category': 'joy'}}\n"
            "EMOTION_MODEL = {'joy': {'expression': ['bright smile']}}\n",
            encoding="utf-8",
        )

    def _write_fixture_refs(self, refs: Path) -> None:
        epig_data = refs / "EPIG" / "data"
        epig_data.mkdir(parents=True)
        (epig_data / "NRC_VAD_with_subject_centric.csv").write_text(
            "Word,Valence,Arousal,Dominance,subject_centric\n"
            "focused gaze,0.7,0.4,0.6,1\n"
            "posture,0.5,0.3,0.6,1\n"
            "rush,0.7,0.8,0.5,1\n"
            "wide angle,0.4,0.5,0.5,0\n"
            "smile,0.8,0.5,0.6,1\n",
            encoding="utf-8",
        )

    def test_audit_classifies_subject_centric_candidates(self):
        from tools.audit_subject_centric_descriptors import audit_subject_centric_descriptors

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "repo"
            refs = root / "refs"
            self._write_fixture_repo(repo)
            self._write_fixture_refs(refs)

            result = audit_subject_centric_descriptors(repo, refs)

        by_text = {record["text"]: record for record in result["records"]}
        self.assertEqual(by_text["focused gaze"]["classification"], "direct")
        self.assertEqual(by_text["gentle posture"]["classification"], "needs_phrase")
        self.assertEqual(by_text["adrenaline rush"]["classification"], "unmatched")
        self.assertEqual(by_text["wide angle"]["classification"], "reject")
        self.assertEqual(by_text["unknown expression"]["classification"], "unmatched")
        self.assertNotIn("joy", by_text)
        self.assertGreaterEqual(result["direct_count"], 1)
        self.assertEqual(result["generated_kind"], "subject_centric_descriptor_candidates")
        self.assertEqual(result["tracked_policy"], "generated_local_only")

    def test_write_report_creates_json(self):
        from tools.audit_subject_centric_descriptors import audit_subject_centric_descriptors, write_report

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "repo"
            refs = root / "refs"
            output = root / "out" / "report.json"
            self._write_fixture_repo(repo)
            self._write_fixture_refs(refs)

            result = audit_subject_centric_descriptors(repo, refs)
            written = write_report(result, output)

            payload = json.loads(written.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_version"], "1.0")
        self.assertTrue(payload["records"])


if __name__ == "__main__":
    unittest.main()
