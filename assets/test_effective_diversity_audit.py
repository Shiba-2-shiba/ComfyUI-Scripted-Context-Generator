"""Small real-runner fixtures for deterministic audit orchestration."""

import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import audit_effective_diversity as audit  # noqa: E402
from tools.workflow_prompt_runner import canonical_json_bytes  # noqa: E402


class TestEffectiveDiversityAudit(unittest.TestCase):
    def setUp(self):
        # Only the test probe schedule is reduced; the real runner still executes.
        self.schedule = patch.dict(audit.PROFILES, {"smoke": (3, 4), "gate": (3, 4), "release": (4, 4)})
        self.schedule.start()
        self.addCleanup(self.schedule.stop)

    def test_reruns_cache_and_overlap_reuse_are_byte_identical(self):
        with patch.object(audit, "build_canonical_record", wraps=audit.build_canonical_record) as generate:
            first = audit.build_audit()
        self.assertEqual(generate.call_count, 4)
        self.assertEqual(first["sample_count"], 3)
        self.assertEqual(first["prefixes"], [3])
        self.assertEqual(first["reference_universe"]["sample_count"], 4)
        with patch.object(audit, "build_canonical_record", wraps=audit.build_canonical_record) as generate:
            cached = audit.build_audit(reference_universe=first["reference_universe"])
        self.assertEqual(generate.call_count, 3)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(cached))
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(audit.build_audit()))
        self.assertEqual(set(first["metrics"]["coverage"]["3"]), set(audit.AXES))
        self.assertEqual(first["diagnostics"]["builder_replay"], {"checked_count": 3, "mismatch_count": 0})

    def test_nonzero_measurement_seeds_do_not_resize_reference(self):
        with patch.object(audit, "build_canonical_record", wraps=audit.build_canonical_record) as generate:
            report = audit.build_audit(seed_start=20, sample_count=2)
        self.assertEqual(generate.call_count, 6)
        self.assertEqual(report["seed_start"], 20)
        self.assertEqual(report["sample_count"], 2)
        self.assertEqual(report["reference_universe"]["seed_start"], 0)
        self.assertEqual(report["reference_universe"]["sample_count"], 4)

    def test_reference_tampering_and_stale_identity_are_rejected(self):
        baseline = audit.build_audit()["reference_universe"]
        for key in ("source_hash", "effective_workflow_hash", "config_hash", "records_sha256"):
            reference = copy.deepcopy(baseline)
            reference[key] = "0" * 64
            with self.subTest(key=key), self.assertRaises(audit.AuditError):
                audit.build_audit(reference_universe=reference)
        for key in ("source_hash", "effective_workflow_hash", "config_hash"):
            reference = {**baseline, key: "0" * 64}
            reference["reference_hash"] = audit.content_hash({k: v for k, v in reference.items() if k != "reference_hash"})
            with self.subTest(identity_key=key), self.assertRaises(audit.AuditError) as raised:
                audit.build_audit(reference_universe=reference)
            self.assertEqual(raised.exception.code, "reference_identity_mismatch")
        for changes in ({"sample_count": 128}, {"seed_start": 1}, {"schema_version": "bad"}, {"axes": {}}):
            reference = {**baseline, **changes}
            reference["reference_hash"] = audit.content_hash({k: v for k, v in reference.items() if k != "reference_hash"})
            with self.subTest(changes=changes), self.assertRaises(audit.AuditError):
                audit.build_audit(reference_universe=reference)

    def test_profile_and_invalid_counts_fail_before_generation(self):
        for kwargs in ({"profile": "invalid"}, {"sample_count": 0}, {"sample_count": -1},
                       {"sample_count": True}, {"sample_count": 2.5}, {"seed_start": True}):
            with self.subTest(kwargs=kwargs), patch.object(audit, "build_canonical_record") as generate:
                with self.assertRaises(audit.AuditError):
                    audit.build_audit(**kwargs)
                generate.assert_not_called()

    def test_builder_replay_mismatch_fails_closed(self):
        original = audit.build_prompt_from_context

        def mismatch(*args, **kwargs):
            context, prompt = original(*args, **kwargs)
            return context, prompt + " changed"

        with patch.object(audit, "build_prompt_from_context", side_effect=mismatch), self.assertRaises(audit.AuditError) as raised:
            audit.build_audit()
        self.assertEqual(raised.exception.code, "builder_replay_mismatch")

    def test_unknown_syntax_family_is_rejected(self):
        original = audit.build_semantic_signatures

        def unknown(*args, **kwargs):
            result = original(*args, **kwargs)
            result["axes"]["syntax_family"] = "not-an-active-family"
            return result

        with patch.object(audit, "build_semantic_signatures", side_effect=unknown), self.assertRaises(audit.AuditError):
            audit.build_audit()

    def test_probe_only_empty_prompt_cannot_contaminate_reference(self):
        original = audit.build_canonical_record

        def empty_probe(workflow, seed):
            record = original(workflow, seed)
            if seed == 3:  # outside the three measured records
                record["cleaned_prompt"] = " "
            return record

        with patch.object(audit, "build_canonical_record", side_effect=empty_probe), self.assertRaises(audit.AuditError):
            audit.build_audit()

    def test_loaded_workflow_must_match_captured_source(self):
        original = audit.capture_source

        def changed(*args, **kwargs):
            snapshot = original(*args, **kwargs)
            snapshot["workflow_hash"] = "0" * 64
            return snapshot

        with patch.object(audit, "capture_source", side_effect=changed), self.assertRaises(audit.AuditError):
            audit.build_audit()

    def test_builder_selector_trace_and_consumed_context_are_bound(self):
        record = audit.build_canonical_record(audit.load_workflow(audit.WORKFLOW_PATH), 0)
        for broken in ("slot", "trace", "context"):
            changed = copy.deepcopy(record)
            if broken == "slot":
                changed["output_selectors"]["raw_prompt"]["slot"] = 1
            elif broken == "trace":
                changed["execution_trace"] = []
            else:
                changed["final_context"]["action"] = "different"
            with self.subTest(broken=broken), self.assertRaises(audit.AuditError):
                audit._project(changed, [], audit.ACTIVE_V1_FAMILIES)

    def test_outside_reference_values_stay_outside_coverage_numerator(self):
        report = audit.build_audit(seed_start=20, sample_count=2)
        axes = report["metrics"]["coverage"]["2"]
        self.assertTrue(any(axis["out_of_reference_values"] for axis in axes.values()))
        for axis in axes.values():
            self.assertEqual(axis["observed_unique_count"], axis["covered_unique_count"] + len(axis["out_of_reference_values"]))
            if axis["reference_count"]:
                self.assertLessEqual(axis["rate"], 1.0)

    def test_input_snapshot_change_fails_closed(self):
        original = audit.capture_source
        for field in ("source_tree_hash", "supplemental_inputs", "contract_sha256"):
            calls = 0

            def drift(*args, **kwargs):
                nonlocal calls
                calls += 1
                snapshot = original(*args, **kwargs)
                if calls > 1:
                    if field == "contract_sha256":
                        snapshot[field] = "0" * 64
                    else:
                        snapshot["source_identity"][field] = "changed"
                return snapshot

            with self.subTest(field=field), patch.object(audit, "capture_source", side_effect=drift):
                with self.assertRaises(audit.AuditError) as raised:
                    audit.build_audit()
                self.assertEqual(raised.exception.code, "inputs_changed")

    def test_record_order_duplicates_and_mixed_configs(self):
        records = [audit.build_canonical_record(audit.load_workflow(audit.WORKFLOW_PATH), seed) for seed in (2, 0, 1)]
        ordered = audit.ordered_records(records)
        self.assertEqual([r["run_seed"] for r in ordered], [0, 1, 2])
        self.assertEqual([r["run_seed"] for r in records], [2, 0, 1])
        for changed in ([*records, records[0]], [{**records[0], "run_seed": True}],
                        [records[0], {**records[1], "config_hash": "other"}]):
            with self.subTest(changed=len(changed)), self.assertRaises(audit.AuditError):
                audit.ordered_records(changed)

    def test_file_input_is_validated_before_execution(self):
        for path in ("../outside.json", " mood_map.json"):
            workflow = audit.load_workflow(audit.WORKFLOW_PATH)
            mood = next(n for n in workflow["nodes"] if n["type"] == "ContextMoodExpander")
            mood["widgets_values"] = [value if value != "mood_map.json" else path for value in mood["widgets_values"]]
            with self.subTest(path=path), patch.object(audit, "load_workflow", return_value=workflow), patch.object(audit, "build_canonical_record") as generate:
                with self.assertRaises(audit.AuditError):
                    audit.build_audit()
                generate.assert_not_called()

    def test_source_identity_binds_supplemental_files_and_contract(self):
        snapshot = audit.capture_source([ROOT / "mood_map.json"])
        paths = {item["path"] for item in snapshot["source_identity"]["supplemental_inputs"]}
        self.assertTrue({"mood_map.json", "prompts.jsonl", "templates.txt"} <= paths)
        self.assertEqual(len(snapshot["contract_sha256"]), 64)

    def test_output_protects_sources_and_input_artifacts(self):
        for target in (ROOT / "mood_map.json", ROOT / "tools/new-audit.json", ROOT / ".git/new-file"):
            with self.subTest(target=target), self.assertRaises(audit.AuditError):
                audit.output_path(target)
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "report.json"
            report = audit.build_audit()
            audit.write_report(destination, report)
            self.assertEqual(destination.read_bytes(), canonical_json_bytes(report))

    def test_cli_invalid_profile_is_a_structured_error(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/audit_effective_diversity.py"), "--profile", "bad"],
                                cwd=ROOT, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        error = json.loads(result.stdout)
        self.assertEqual(error["status"], "error")
        self.assertNotIn("metrics", error)

    def test_cli_preserves_previous_output_on_failure_and_rejects_collisions(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "report.json"
            target.write_bytes(b"previous report")
            for args in (("--sample-count", "0"), ("--write-reference", str(target)), ("--reference", str(target))):
                result = subprocess.run([sys.executable, str(ROOT / "tools/audit_effective_diversity.py"),
                                         "--output", str(target), *args], cwd=ROOT, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(json.loads(result.stdout)["status"], "error")
                self.assertEqual(target.read_bytes(), b"previous report")

    def test_malformed_workflow_is_rejected_before_class_map_or_execution(self):
        for workflow in ({"nodes": [None]}, {"nodes": {}}, {"nodes": [{"type": "ContextMoodExpander", "inputs": [None]}]}):
            with self.subTest(workflow=workflow), self.assertRaises(audit.AuditError):
                audit._preflight(workflow, 0)

    def test_reference_write_failure_does_not_publish_success_report(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "report.json"
            reference = Path(temp) / "reference.json"
            destination.write_bytes(b"previous report")
            original = audit.write_report

            def fail_reference(path, value):
                if path == reference:
                    raise OSError("simulated export failure")
                original(path, value)

            output = io.StringIO()
            with patch.object(audit, "write_report", side_effect=fail_reference), redirect_stdout(output):
                code = audit.main(["--output", str(destination), "--write-reference", str(reference)])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(output.getvalue())["status"], "error")
            self.assertEqual(destination.read_bytes(), b"previous report")


if __name__ == "__main__":
    unittest.main()
