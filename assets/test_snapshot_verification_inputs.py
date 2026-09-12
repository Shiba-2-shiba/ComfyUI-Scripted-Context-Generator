import json
import tempfile
import unittest
from pathlib import Path

from tools.build_prompt_quality_confirmation import _snapshot_content_hash
from tools.materialize_variation_candidate_snapshot import _copy_filtered_source, _manifest_entries, _hash_value, _run_snapshot_command
from tools.workflow_prompt_runner import WorkflowValidationError


class SnapshotVerificationInputsTests(unittest.TestCase):
    def test_candidate_command_reads_utf8_output_under_a_unicode_path(self):
        with tempfile.TemporaryDirectory(prefix="検証-") as temporary:
            root = Path(temporary)
            (root / "emit.py").write_text(
                "import sys\nsys.stdout.buffer.write('日本語 🎨'.encode('utf-8'))\n", encoding="utf-8",
            )
            self.assertEqual(_run_snapshot_command(root, "emit.py"), "日本語 🎨")

    def test_snapshot_copies_and_binds_test_support_without_external_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, destination = Path(temporary) / "source", Path(temporary) / "snapshot"
            support = ["docs/fixture.json", "assets/variation_test_fixtures.py", "README.md",
                       ".omx/ultragoal/goals.json", ".omx/ultragoal/ledger.jsonl"]
            for relative in support + ["ComfyUI_frontend/node_modules/unused.js", ".omx/logs/unused.log"]:
                path = source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
            _copy_filtered_source(source, destination)
            for relative in support:
                self.assertEqual((destination / relative).read_bytes(), (source / relative).read_bytes())
            self.assertFalse((destination / "ComfyUI_frontend").exists())
            self.assertFalse((destination / ".omx/logs").exists())
            before = _snapshot_content_hash(destination)
            self.assertEqual(before, _hash_value(_manifest_entries(destination)))
            verification_text = (destination / ".verification-inputs.json").read_bytes().decode("utf-8")
            self.assertEqual(_snapshot_content_hash(source, verification_manifest_text=verification_text), before)
            self.assertFalse((source / ".verification-inputs.json").exists())
            (destination / "docs/fixture.json").write_text('{"changed": true}', encoding="utf-8")
            self.assertNotEqual(_snapshot_content_hash(destination), before)

    def test_support_manifest_rejects_escape_and_missing_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in ("../outside.json", "missing.json"):
                with self.subTest(relative=relative):
                    (root / ".verification-inputs.json").write_text(json.dumps({
                        "schema_version": "snapshot-verification-inputs/v1", "files": [relative],
                    }), encoding="utf-8")
                    with self.assertRaises(WorkflowValidationError):
                        _snapshot_content_hash(root)

    def test_legacy_snapshot_without_support_manifest_keeps_existing_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            (root / "docs/unbound.json").write_text("{}", encoding="utf-8")
            self.assertEqual(_snapshot_content_hash(root), _hash_value(_manifest_entries(root)))
            self.assertEqual(_manifest_entries(root), {})
