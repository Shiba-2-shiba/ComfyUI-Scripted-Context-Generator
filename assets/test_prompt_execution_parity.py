import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import verify_prompt_execution_parity as parity


class PromptExecutionParityTests(unittest.TestCase):
    def _environment(self, root: Path) -> Path:
        for name in ("ComfyUI", "ComfyUI_frontend"):
            checkout = root / name
            checkout.mkdir()
            (checkout / ".git").mkdir()
        sink = root / "verification" / "comfyui_sink"
        sink.mkdir(parents=True)
        (sink / "__init__.py").write_text("", encoding="utf-8")
        (sink / "nodes.py").write_text("", encoding="utf-8")
        fixture = root / "verification" / "fixtures" / "workflow.json"
        fixture.parent.mkdir(parents=True)
        fixture.write_text("{}", encoding="utf-8")
        manifest = {
            "environment_id": "test",
            "repositories": {
                "comfyui": {"path": "ComfyUI", "commit": "a" * 40},
                "comfyui_frontend": {"path": "ComfyUI_frontend", "commit": "b" * 40},
            },
            "sink": {"version": 1, "source": "verification/comfyui_sink", "install_path": "ComfyUI/custom_nodes/sink", "node_type": "Sink"},
            "parity": {"workflow": "verification/fixtures/workflow.json", "sentinel_seeds": [0, 1, 2, 3, 5, 8, 13, 21], "required_outputs": ["final_context", "raw_prompt", "cleaned_prompt"]},
        }
        path = root / "verification" / "environment.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_missing_checkout_has_stable_error(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            path = root / "verification" / "environment.json"
            path.parent.mkdir()
            path.write_text(json.dumps({
                "repositories": {"comfyui": {"path": "ComfyUI", "commit": "a" * 40}, "comfyui_frontend": {"path": "ComfyUI_frontend", "commit": "b" * 40}},
                "sink": {"version": 1}, "parity": {},
            }), encoding="utf-8")
            with self.assertRaises(parity.ParityError) as caught:
                parity.validate_environment(path)
            self.assertEqual(caught.exception.code, "missing_checkout")

    def test_commit_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as name, mock.patch.object(parity, "_git_head", return_value="c" * 40):
            path = self._environment(Path(name))
            with self.assertRaises(parity.ParityError) as caught:
                parity.validate_environment(path)
            self.assertEqual(caught.exception.code, "version_mismatch")
            self.assertEqual(caught.exception.details["repository"], "comfyui")

    def test_environment_accepts_exact_pins_and_eight_seeds(self):
        with tempfile.TemporaryDirectory() as name, mock.patch.object(parity, "_git_head", side_effect=["a" * 40, "b" * 40]):
            context = parity.validate_environment(self._environment(Path(name)))
            self.assertEqual(context["parity"]["sentinel_seeds"], [0, 1, 2, 3, 5, 8, 13, 21])

    def test_canonical_outputs_decodes_context_and_requires_all_fields(self):
        result = parity.canonical_outputs({"final_context": '{"z":2,"a":1}', "raw_prompt": "raw", "cleaned_prompt": "clean"}, ["final_context", "raw_prompt", "cleaned_prompt"], 3)
        self.assertEqual(result["final_context"], {"a": 1, "z": 2})
        with self.assertRaises(parity.ParityError) as caught:
            parity.canonical_outputs({"final_context": {}}, ["final_context", "raw_prompt"], 3)
        self.assertEqual(caught.exception.code, "required_output_missing")

    def test_history_without_observable_sink_output_fails_closed(self):
        history = {"p": {"status": {"status_str": "success"}, "outputs": {}}}
        with self.assertRaises(parity.ParityError) as caught:
            parity._extract_sink_output(history, "p", "12", ["final_context", "raw_prompt", "cleaned_prompt"], 8)
        self.assertEqual(caught.exception.code, "required_output_missing")

    def test_history_extracts_sink_ui_canonical_json(self):
        text = json.dumps({"cleaned_prompt": "clean", "final_context": {"a": 1}, "raw_prompt": "raw"})
        history = {"p": {"status": {"status_str": "success"}, "outputs": {"12": {"canonical_outputs": [text]}}}}
        result = parity._extract_sink_output(history, "p", "12", ["final_context", "raw_prompt", "cleaned_prompt"], 13)
        self.assertEqual(result, {"cleaned_prompt": "clean", "final_context": {"a": 1}, "raw_prompt": "raw"})

    def test_http_execution_checks_sink_registration_before_queueing(self):
        with mock.patch.object(parity, "_request_json", return_value={}):
            with self.assertRaises(parity.ParityError) as caught:
                parity.execute_via_http("http://test", {"nodes": []}, [0], object(), "Sink", "custom_nodes.sink", ["final_context"], 1)
        self.assertEqual(caught.exception.code, "sink_registration_failed")

    def test_http_execution_rejects_sink_registered_from_wrong_path(self):
        with mock.patch.object(parity, "_request_json", return_value={"Sink": {"python_module": "product.registry"}}):
            with self.assertRaises(parity.ParityError) as caught:
                parity.execute_via_http("http://test", {"nodes": []}, [0], object(), "Sink", "custom_nodes.sink", ["final_context"], 1)
        self.assertEqual(caught.exception.code, "sink_registration_failed")
        self.assertEqual(caught.exception.details["actual_module"], "product.registry")

    def test_product_registration_symlink_is_owned_and_cleaned(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "source"
            target = root / "custom_nodes" / "product"
            marker = root / "custom_nodes" / "marker.json"
            source.mkdir()
            target.parent.mkdir()
            kind = parity._create_product_registration(target, source, marker, "owned")
            self.assertIn(kind, {"symlink", "junction"})
            self.assertEqual(target.resolve(), source.resolve())
            parity._remove_product_registration(target, source, marker, "owned", kind)
            self.assertFalse(target.exists())
            self.assertFalse(marker.exists())

    def test_windows_symlink_failure_falls_back_to_directory_junction(self):
        if parity.os.name != "nt":
            self.skipTest("directory junction fallback is Windows-specific")
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "source"
            target = root / "custom_nodes" / "product"
            marker = root / "custom_nodes" / "marker.json"
            source.mkdir()
            target.parent.mkdir()

            with mock.patch.object(Path, "symlink_to", side_effect=OSError("denied")) as link, mock.patch.object(parity.subprocess, "run", wraps=subprocess.run) as run:
                kind = parity._create_product_registration(target, source, marker, "owned", platform="nt")
            self.assertEqual(kind, "junction")
            self.assertEqual(link.call_count, 1)
            self.assertIn("/J", run.call_args.args[0])
            parity._remove_product_registration(target, source, marker, "owned", kind)

    def test_product_cleanup_refuses_wrong_ownership_token(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "source"
            target = root / "product"
            marker = root / "marker.json"
            source.mkdir()
            kind = parity._create_product_registration(target, source, marker, "owner")
            try:
                with self.assertRaises(parity.ParityError) as caught:
                    parity._remove_product_registration(target, source, marker, "other", kind)
                self.assertEqual(caught.exception.code, "cleanup_failed")
                self.assertTrue(target.exists())
            finally:
                parity._remove_product_registration(target, source, marker, "owner", kind)

    def test_cli_missing_real_checkout_emits_canonical_json_and_nonzero(self):
        with tempfile.TemporaryDirectory() as name:
            environment = Path(name) / "verification" / "environment.json"
            environment.parent.mkdir()
            environment.write_text(json.dumps({
                "repositories": {"comfyui": {"path": "ComfyUI", "commit": "a" * 40}, "comfyui_frontend": {"path": "ComfyUI_frontend", "commit": "b" * 40}},
                "sink": {"version": 1}, "parity": {},
            }), encoding="utf-8")
            completed = subprocess.run([sys.executable, str(ROOT / "tools" / "verify_prompt_execution_parity.py"), "--environment", str(environment)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 2)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "missing_checkout")
        self.assertEqual(completed.stdout, json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    unittest.main()
