"""Regression coverage for authentic candidate gate execution receipts."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tools import run_variation_verification as collector
from tools.build_prompt_quality_verification import _validate_gate_result, _validate_v150_evidence
from tools.prompt_quality_loop import _source_files


class VerificationCollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory()
        cls.base = Path(cls.workspace.name)
        cls.template = cls.base / "template"
        # Copy real collector dependencies, without historical artifacts or tests.
        for source in _source_files(collector.ROOT):
            relative = source.relative_to(collector.ROOT)
            if relative.parts[0] == "assets":
                continue
            target = cls.template / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        for name in ("prompts.jsonl", "mood_map.json", "templates.txt", "workflow_samples.json"):
            source = collector.ROOT / name
            if source.is_file():
                shutil.copyfile(source, cls.template / name)

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def setUp(self):
        self.case_dir = tempfile.TemporaryDirectory(dir=self.base)
        self.root = Path(self.case_dir.name) / "candidate"
        self.output = Path(self.case_dir.name) / "output"
        shutil.copytree(self.template, self.root)

    def tearDown(self):
        self.case_dir.cleanup()

    def script(self, gate, body):
        filename = collector.PYTHON_GATES[gate][0]
        (self.root / "tools" / filename).write_text(body, encoding="utf-8")

    def run_gate(self, gate):
        return collector.run_gate(gate, self.root, self.output, collector.ROOT)

    def test_real_subprocess_preserves_buffer_and_builder_bindings(self):
        self.script("full_flow", "import sys\nsys.stdout.buffer.write(b'OK: verify_full_flow passed\\n')\n")
        evidence = collector.read_json(self.run_gate("full_flow"))
        binding = collector.identity(self.root)
        _validate_v150_evidence("full_flow", evidence, candidate_root=self.root,
            source_hash=binding["candidate_source_tree_sha256"],
            content_hash=binding["candidate_snapshot_content_sha256"])
        result = collector.read_json(Path(evidence["result_path"]))
        _validate_gate_result("full_flow", {**result,
            "schema_version": "prompt-quality-gate-result/v1",
            "source_tree_hash": binding["candidate_source_tree_sha256"]},
            binding["candidate_source_tree_sha256"])
        self.assertEqual(result["summary"], {"checks_passed": 1, "failures": 0})
        self.assertEqual(evidence["command"][1], str(self.root / "tools/run_variation_verification.py"))
        sentinel = collector.read_json(Path(evidence["process_isolation"]["sentinel_path"]))
        self.assertTrue(sentinel["imported_candidate_modules"])

    def test_process_failure_never_creates_pass_evidence(self):
        self.script("full_flow", "print('OK: verify_full_flow passed')\nraise SystemExit(7)\n")
        with self.assertRaisesRegex(ValueError, "exited 7"):
            self.run_gate("full_flow")
        self.assertFalse((self.output / "full_flow.evidence.json").exists())

    def test_empty_success_is_not_a_report(self):
        self.script("widgets", "pass\n")
        with self.assertRaisesRegex(ValueError, "No complete successful"):
            self.run_gate("widgets")
        self.assertFalse((self.output / "widgets.evidence.json").exists())

    def test_source_drift_fails(self):
        self.script("full_flow", "from pathlib import Path\nPath('changed.py').write_text('x = 1')\nprint('OK: verify_full_flow passed')\n")
        with self.assertRaisesRegex(ValueError, "exited 1"):
            self.run_gate("full_flow")
        self.assertIn("changed during gate", (self.output / "full_flow.log").read_text(encoding="utf-8"))

    def test_active_import_leakage_fails(self):
        source = str(collector.ROOT / "workflow_widget_validation.py")
        self.script("full_flow", f"import importlib.util, sys\nspec = importlib.util.spec_from_file_location('active_leak', {source!r})\nmodule = importlib.util.module_from_spec(spec)\nsys.modules['active_leak'] = module\nspec.loader.exec_module(module)\nprint('OK: verify_full_flow passed')\n")
        with self.assertRaisesRegex(ValueError, "exited 1"):
            self.run_gate("full_flow")
        self.assertIn("active source root", (self.output / "full_flow.log").read_text(encoding="utf-8"))

    def test_real_unittest_result_counts(self):
        assets = self.root / "assets"
        assets.mkdir(exist_ok=True)
        (assets / "test_small.py").write_text(
            "import unittest\nclass Tests(unittest.TestCase):\n    def test_pass(self): self.assertTrue(True)\n",
            encoding="utf-8")
        # The real one-test run must remain below the existing full-regression gate.
        with self.assertRaisesRegex(RuntimeError, "gate result summary"):
            self.run_gate("python_tests")
        record = collector.read_json(self.output / "python_tests.execution.json")
        self.assertEqual(record["summary"], {"tests_run": 1, "tests_passed": 1,
                         "failures": 0, "errors": 0, "skipped": 0})
        self.assertFalse((self.output / "python_tests.evidence.json").exists())

    def test_real_structured_report(self):
        report = {"ERROR": [], "WARNING": [], "INFO": [
            {"code": "compatibility_review_generation_summary", "missing_current_rows": 0,
             "extra_generated_rows": 0}]}
        self.script("compatibility_review", f"print({json.dumps(report)!r})\n")
        evidence = collector.read_json(self.run_gate("compatibility_review"))
        result = collector.read_json(Path(evidence["result_path"]))
        self.assertEqual(result["summary"], {"errors": 0, "missing_rows": 0, "extra_rows": 0})

    def test_report_omitting_required_counts_fails(self):
        with self.assertRaises(ValueError):
            collector.parse_summary("action_pools", '{"ERROR": [], "INFO": []}')

    def test_external_reports_require_authentic_report_counters(self):
        vitest = {"success": True, "numTotalTests": 4, "numPassedTests": 4,
                  "numFailedTests": 0, "numPendingTests": 0, "numTodoTests": 0}
        self.assertEqual(collector.external_summary("frontend", vitest),
                         {"tests_passed": 4, "failures": 0})
        with self.assertRaises(ValueError):
            collector.external_summary("frontend", {**vitest, "numTotalTests": 5})
        playwright = {"stats": {"expected": 2, "unexpected": 0, "flaky": 0, "skipped": 0}, "errors": []}
        self.assertEqual(collector.external_summary("browser", playwright),
                         {"tests_passed": 2, "failures": 0})
        with self.assertRaises(ValueError):
            collector.external_summary("browser", {**playwright, "errors": [{"message": "crashed"}]})

    def test_direct_binding_keeps_original_result_and_rejects_stale_run(self):
        self.output.mkdir()
        binding = collector.identity(self.root)
        raw_path = self.output / "original-review.json"
        collector.write_json(raw_path, {**binding, "status": "pass"})
        log_path = self.output / "review.log"
        log_path.write_text("Original review producer output", encoding="utf-8")
        record = {"before": binding, "after": binding, "command": ["review", "--candidate", str(self.root)],
                  "cwd": str(self.root), "exit_code": 0, "log_path": str(log_path)}
        path = collector.bind_result("blind_review", self.root, self.output, raw_path, record)
        evidence = collector.read_json(path)
        self.assertEqual(evidence["result_path"], str(raw_path))
        self.assertEqual(evidence["result_sha256"], collector.sha256(raw_path))
        with self.assertRaisesRegex(ValueError, "unchanged candidate"):
            collector.bind_result("blind_review", self.root, self.output, raw_path,
                                  {**record, "before": {}})


if __name__ == "__main__":
    unittest.main()
