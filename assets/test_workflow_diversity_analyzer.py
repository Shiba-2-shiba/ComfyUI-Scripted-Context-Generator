import shutil
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from tools.analyze_context_workflow_diversity import (
    build_run_record,
    execute_records,
    summarize_records,
    write_outputs,
)
from core.schema import LEGACY_STYLE_NOTE
from workflow_widget_validation import load_workflow


class TestWorkflowDiversityAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = load_workflow(ROOT / "ComfyUI-workflow-context.json")

    def test_build_run_record_executes_active_workflow_sample(self):
        record = build_run_record(self.workflow, 0)

        self.assertIn("prompt", record)
        self.assertIn("context", record)
        self.assertTrue(record["prompt"])
        self.assertTrue(record["context"].get("loc"))

        trace_by_type = {
            item["node_type"]: item
            for item in record["execution_trace"]
        }
        self.assertEqual(trace_by_type["ContextSource"]["controls"].get("seed"), "randomize")
        self.assertEqual(trace_by_type["ContextGarnish"]["controls"], {})
        self.assertEqual(trace_by_type["ContextGarnish"]["inputs"]["max_items"], 3)
        self.assertEqual(trace_by_type["ContextGarnish"]["inputs"]["emotion_nuance"], "random")

    def test_execute_records_reflects_multi_seed_variation(self):
        records, coverage_progress = execute_records(self.workflow, seed_start=0, runs=8)
        summary = summarize_records(records)
        first = build_run_record(self.workflow, 0)
        second = build_run_record(self.workflow, 1)
        first_trace = {item["node_type"]: item for item in first["execution_trace"]}
        second_trace = {item["node_type"]: item for item in second["execution_trace"]}

        self.assertEqual(len(records), 8)
        self.assertEqual(len(coverage_progress), 8)
        self.assertNotEqual(
            first_trace["ContextSource"]["inputs"]["seed"],
            second_trace["ContextSource"]["inputs"]["seed"],
        )
        self.assertGreater(summary["unique_prompts"], 1)
        self.assertGreater(summary["unique_locations"], 1)
        self.assertIn("top_locations", summary)
        self.assertIn("top_actions", summary)
        self.assertIn("top_moods", summary)
        self.assertTrue(summary["top_locations"])
        self.assertTrue(summary["top_actions"])

    def test_active_workflow_keeps_legacy_style_as_note_not_warning(self):
        record = build_run_record(self.workflow, 0)

        self.assertIn(LEGACY_STYLE_NOTE, record["context"].get("notes", []))
        self.assertEqual(record["context"].get("warnings", []), [])
        self.assertIn("notes=1", record["summary_text"])
        self.assertIn("warnings=0", record["summary_text"])

    def test_summary_and_output_artifacts_include_expected_counters(self):
        records, _coverage_progress = execute_records(self.workflow, seed_start=0, runs=8)
        summary = summarize_records(records)

        for key in (
            "runs",
            "unique_prompts",
            "unique_prompt_ratio",
            "unique_scene_signatures",
            "unique_locations",
            "unique_actions",
            "unique_clothing_prompts",
            "unique_location_prompts",
            "runs_with_warnings",
            "scene_variation_sources",
            "top_warnings",
        ):
            self.assertIn(key, summary)

        self.assertEqual(summary["runs"], 8)
        self.assertGreater(summary["unique_scene_signatures"], 1)
        self.assertGreaterEqual(summary["unique_prompt_ratio"], 0.25)

        output_dir = ROOT / "assets" / "results" / "test_workflow_diversity"
        output_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(output_dir, ignore_errors=True))

        samples_path, summary_path = write_outputs(records, summary, output_dir)

        self.assertTrue(samples_path.exists())
        self.assertTrue(summary_path.exists())
        persisted_summary = summary_path.read_text(encoding="utf-8")
        self.assertIn('"unique_prompts"', persisted_summary)
        self.assertIn('"unique_locations"', persisted_summary)


if __name__ == "__main__":
    unittest.main()
