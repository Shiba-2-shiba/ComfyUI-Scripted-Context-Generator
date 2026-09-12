import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestLlmExpandedPromptPolicy(unittest.TestCase):
    def test_hand_authored_negative_fixture_hits_expected_domains(self):
        from core.semantic_policy import find_banned_terms

        fixture_path = Path(ROOT) / "assets" / "fixtures" / "semantic_policy_negative_examples.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["source"], "repo_authored_policy_fixture")
        for example in payload["examples"]:
            hits = find_banned_terms(example["text"])
            for domain in example["expected_domains"]:
                self.assertIn(domain, hits, example["id"])

    def test_scan_llm_expanded_prompts_counts_all_policy_domains(self):
        from tools.audit_llm_expanded_prompt_policy import scan_llm_expanded_prompts

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            refs = root / "refs"
            data = refs / "EPIG" / "data"
            data.mkdir(parents=True)
            (data / "llm_expanded_prompts.csv").write_text(
                "base_prompt,emotion,expanded_prompt\n"
                'room,joy,"anime style, masterpiece, close-up, soft lighting, petite subject"\n'
                'street,calm,"quiet street with a waiting posture"\n',
                encoding="utf-8",
            )

            result = scan_llm_expanded_prompts(refs)

        self.assertTrue(result["available"])
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["rows_with_policy_issues"], 1)
        self.assertGreaterEqual(result["domain_counts"]["style"], 1)
        self.assertGreaterEqual(result["domain_counts"]["quality"], 1)
        self.assertGreaterEqual(result["domain_counts"]["camera"], 1)
        self.assertGreaterEqual(result["domain_counts"]["render"], 1)
        self.assertGreaterEqual(result["domain_counts"]["body_type"], 1)
        self.assertTrue(result["policy"]["negative_corpus_only"])

    def test_write_audit_creates_json(self):
        from tools.audit_llm_expanded_prompt_policy import scan_llm_expanded_prompts, write_audit

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            refs = root / "refs"
            data = refs / "EPIG" / "data"
            output = root / "out" / "policy.json"
            data.mkdir(parents=True)
            (data / "llm_expanded_prompts.csv").write_text(
                "base_prompt,emotion,expanded_prompt\n"
                'room,joy,"best quality, close-up, room"\n',
                encoding="utf-8",
            )

            result = scan_llm_expanded_prompts(refs)
            written = write_audit(result, output)
            payload = json.loads(written.read_text(encoding="utf-8"))

        self.assertEqual(payload["generated_kind"], "llm_expanded_prompt_policy_audit")
        self.assertEqual(payload["row_count"], 1)


if __name__ == "__main__":
    unittest.main()
