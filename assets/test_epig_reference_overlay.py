import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestEpigReferenceOverlay(unittest.TestCase):
    def _make_repo(self, root: Path) -> None:
        data_dir = root / "vocab" / "data"
        garnish_dir = root / "vocab" / "garnish"
        action_dir = root / "vocab" / "source" / "action_pools"
        data_dir.mkdir(parents=True)
        garnish_dir.mkdir(parents=True)
        action_dir.mkdir(parents=True)
        (data_dir / "sample.json").write_text(
            json.dumps({"descriptors": [{"text": "bright smile"}, {"text": "calm posture"}]}),
            encoding="utf-8",
        )
        (action_dir / "pool.json").write_text(json.dumps({"actions": ["holding an open book"]}), encoding="utf-8")
        (garnish_dir / "sample.py").write_text('TAGS = ["focused gaze"]\n', encoding="utf-8")

    def _make_references(self, root: Path) -> None:
        epig_dir = root / "EPIG" / "data"
        nrc_mwe_dir = root / "NRC-VAD-Lexicon-v2.1" / "NRC-VAD-Lexicon-v2.1" / "MWE"
        nrc_dir = root / "NRC-VAD-Lexicon-v2.1" / "NRC-VAD-Lexicon-v2.1"
        ed_dir = root / "EmotionDynamics" / "code" / "uedLib" / "lexicons"
        emolex_dir = root / "EmotionDynamics" / "lexicons"
        epig_dir.mkdir(parents=True)
        nrc_mwe_dir.mkdir(parents=True)
        ed_dir.mkdir(parents=True)
        emolex_dir.mkdir(parents=True)
        (epig_dir / "NRC_VAD_with_subject_centric.csv").write_text(
            "Word,Valence,Arousal,Dominance,subject_centric\ncalm,0.8,0.2,0.5,1\n",
            encoding="utf-8",
        )
        (nrc_dir / "NRC-VAD-Lexicon-v2.1.txt").write_text(
            "term\tvalence\tarousal\tdominance\nbook\t0\t-0.2\t0.1\n",
            encoding="utf-8",
        )
        (nrc_mwe_dir / "mwe-NRC-VAD-Lexicon-v2.1.txt").write_text(
            "term\tvalence\tarousal\tdominance\nbright smile\t1\t0.2\t0\n",
            encoding="utf-8",
        )
        (ed_dir / "NRC-VAD-Lexicon.csv").write_text(
            "word,valence,arousal,dominance\nfocused gaze,0.6,0.4,0.7\n",
            encoding="utf-8",
        )
        (emolex_dir / "NRC_EmoLex_joy.csv").write_text("word,val\nsmile,1\n", encoding="utf-8")

    def test_overlay_prefers_exact_mwe_and_uses_token_fallback(self):
        from tools.extract_epig_reference_overlay import build_overlay, collect_current_vocabulary, load_reference_sources

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "repo"
            refs = root / "refs"
            self._make_repo(repo)
            self._make_references(refs)

            vocabulary = collect_current_vocabulary(repo)
            sources, warnings = load_reference_sources(refs)
            overlay = build_overlay(vocabulary, sources, warnings)

        self.assertEqual(overlay["matches"]["bright smile"]["match_type"], "exact")
        self.assertTrue(any(item["source"] == "nrc_vad_v2_1_mwe" for item in overlay["matches"]["bright smile"]["references"]))
        self.assertEqual(overlay["matches"]["calm posture"]["match_type"], "token_fallback")
        self.assertEqual(overlay["matches"]["focused gaze"]["match_type"], "exact")

    def test_write_overlay_creates_json(self):
        from tools.extract_epig_reference_overlay import write_overlay

        with tempfile.TemporaryDirectory() as tmpdir:
            output = write_overlay({"schema_version": "1.0"}, Path(tmpdir) / "overlay.json")
            self.assertTrue(output.exists())
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["schema_version"], "1.0")


if __name__ == "__main__":
    unittest.main()
