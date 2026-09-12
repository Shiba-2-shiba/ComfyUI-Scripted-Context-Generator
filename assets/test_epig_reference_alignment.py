import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestEpigReferenceAlignment(unittest.TestCase):
    def test_normalize_nrc_score_converts_minus_one_to_one(self):
        from vocab.epig_reference import normalize_nrc_score

        self.assertEqual(normalize_nrc_score("-1"), 0.0)
        self.assertEqual(normalize_nrc_score("0"), 0.5)
        self.assertEqual(normalize_nrc_score("1"), 1.0)

    def test_epig_subject_centric_csv_parses(self):
        from vocab.epig_reference import read_epig_subject_centric_csv

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "epig.csv"
            path.write_text(
                "Word,Valence,Arousal,Dominance,subject_centric\n"
                "Afraid,0.01,0.775,0.245,1\n"
                "Stone,0.5,0.3,0.4,0\n",
                encoding="utf-8",
            )
            records = read_epig_subject_centric_csv(path)

        self.assertTrue(records["afraid"]["subject_centric"])
        self.assertFalse(records["stone"]["subject_centric"])
        self.assertEqual(records["afraid"]["scale"], "0..1")

    def test_nrc_vad_tsv_parses_and_normalizes(self):
        from vocab.epig_reference import read_nrc_vad_tsv

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nrc.tsv"
            path.write_text("term\tvalence\tarousal\tdominance\nbright smile\t1\t0\t-1\n", encoding="utf-8")
            records = read_nrc_vad_tsv(path)

        self.assertEqual(records["bright smile"]["valence"], 1.0)
        self.assertEqual(records["bright smile"]["arousal"], 0.5)
        self.assertEqual(records["bright smile"]["dominance"], 0.0)

    def test_emotiondynamics_vad_and_emolex_csv_parse(self):
        from vocab.epig_reference import read_emolex_csv, read_vad_csv

        with tempfile.TemporaryDirectory() as tmpdir:
            vad_path = Path(tmpdir) / "NRC_VAD_valence.csv"
            vad_path.write_text("word,val\ncalm,0.8\n", encoding="utf-8")
            emolex_path = Path(tmpdir) / "NRC_EmoLex_joy.csv"
            emolex_path.write_text("word,val\nsmile,1\n", encoding="utf-8")

            vad = read_vad_csv(vad_path, source="emotiondynamics_vad")
            emolex = read_emolex_csv(emolex_path, source="emotiondynamics_emolex")

        self.assertEqual(vad["calm"]["valence"], 0.8)
        self.assertEqual(emolex["smile"]["emotion"], "joy")
        self.assertEqual(emolex["smile"]["association"], 1)

    def test_lookup_term_uses_normalized_exact_match(self):
        from vocab.epig_reference import lookup_term

        source = {"bright smile": {"term": "bright smile", "valence": 0.9}}

        self.assertEqual(lookup_term("Bright-Smile", source)["valence"], 0.9)

    def test_alignment_audit_reports_profile_matches(self):
        from tools.audit_epig_reference_alignment import audit_reference_alignment

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "repo"
            refs = root / "refs"
            (repo / "vocab" / "data").mkdir(parents=True)
            (repo / "vocab" / "garnish").mkdir(parents=True)
            (repo / "vocab" / "source" / "action_pools").mkdir(parents=True)
            (repo / "vocab" / "data" / "emotion_vad_profiles.json").write_text(
                '{"categories":{"joy":{"vad":[0.8,0.7],"aliases":["happy"]}},"nuances":{"calm":[0.7,0.2]}}',
                encoding="utf-8",
            )
            (repo / "vocab" / "data" / "personality_behavior_profiles.json").write_text(
                '{"descriptors":{"gaze":[{"text":"focused gaze"},{"text":"unknown posture"}]}}',
                encoding="utf-8",
            )
            (repo / "vocab" / "data" / "sample.json").write_text('{"text":"happy smile"}', encoding="utf-8")
            (refs / "EPIG" / "data").mkdir(parents=True)
            (refs / "EPIG" / "data" / "NRC_VAD_with_subject_centric.csv").write_text(
                "Word,Valence,Arousal,Dominance,subject_centric\nhappy,0.9,0.7,0.6,1\ncalm,0.8,0.2,0.5,1\nfocused gaze,0.6,0.4,0.7,1\n",
                encoding="utf-8",
            )
            (refs / "EPIG" / "data" / "llm_expanded_prompts.csv").write_text(
                "base_prompt,emotion,expanded_prompt\n"
                'room,joy,"best quality, cinematic, closeup, room"\n',
                encoding="utf-8",
            )
            result = audit_reference_alignment(repo, refs)

        self.assertGreaterEqual(result["emotion_profile_alignment"]["matched_count"], 1)
        self.assertGreaterEqual(result["personality_descriptor_coverage"]["exact_match_count"], 1)
        self.assertGreaterEqual(result["subject_centric_summary"]["subject_centric_record_count"], 1)
        self.assertGreaterEqual(result["llm_expanded_prompt_policy_scan"]["policy_issue_count"], 1)
        self.assertTrue(result["policy"]["reference_scores_are_local_only"])


if __name__ == "__main__":
    unittest.main()
