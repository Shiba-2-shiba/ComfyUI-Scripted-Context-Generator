"""Exercise PowerShell runtime boundaries without starting external applications."""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PWSH = shutil.which("pwsh")


def ps_quote(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


@unittest.skipUnless(PWSH, "PowerShell 7 is required")
class VerificationRuntimeScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="verification runtime ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "candidate source"
        self.source.mkdir()
        self.active = self.base / "active plugin"
        self.active.mkdir()
        (self.source / "tools").mkdir()
        for name in ("run_frontend_workflow_validation.ps1", "run_custom_workflow_roundtrip.ps1", "sync_upstream_verification_assets.ps1"):
            shutil.copyfile(ROOT / "tools" / name, self.source / "tools" / name)
        shutil.copytree(ROOT / "verification", self.source / "verification")
        (self.source / "__init__.py").write_text("", encoding="utf-8")
        (self.source / "workflow_samples.json").write_text('[{"path":"sample.json"}]', encoding="utf-8")
        (self.source / "sample.json").write_text("{}", encoding="utf-8")
        self.frontend = self.base / "external frontend"
        (self.frontend / "src").mkdir(parents=True)
        (self.frontend / "package.json").write_text("{}", encoding="utf-8")
        (self.frontend / "tools/devtools").mkdir(parents=True)
        (self.frontend / "tools/devtools/__init__.py").write_text("# fixture devtools\n", encoding="utf-8")
        (self.frontend / "tools/devtools/helper.py").write_text("# helper\n", encoding="utf-8")
        (self.frontend / "dist").mkdir()
        (self.frontend / "dist/index.html").write_text("<html>local frontend</html>", encoding="utf-8")
        self.sentinel = self.base / "sentinel.json"
        self.vitest = self.frontend / "node_modules/.bin" / ("vitest.cmd" if os.name == "nt" else "vitest")
        self.vitest.parent.mkdir(parents=True)
        self.vitest.write_text(
            '@echo %VSCG_CUSTOM_NODE_ROOT%>"%VSCG_TEST_SOURCE_CAPTURE%"\n@exit /b 0\n'
            if os.name == "nt" else '#!/bin/sh\nprintf "%s" "$VSCG_CUSTOM_NODE_ROOT" > "$VSCG_TEST_SOURCE_CAPTURE"\n',
            encoding="utf-8",
        )
        self.vitest.chmod(0o755)

    def run_ps(self, body: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        for key in ("VSCG_FRONTEND_ROOT", "VSCG_COMFYUI_ROOT", "VSCG_CUSTOM_NODE_ROOT"):
            env.pop(key, None)
        env["VSCG_TEST_SOURCE_CAPTURE"] = str(self.base / "frontend source.txt")
        mock_git = "function git { $global:LASTEXITCODE=0; 'mock-frontend-revision' }; "
        return subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-Command", mock_git + body], env=env, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=30)

    def call(self, script: str, *, candidate: bool = True) -> str:
        args = f"& {ps_quote(self.source / 'tools' / script)} -FrontendRoot {ps_quote(self.frontend)}"
        if candidate:
            args += f" -CustomNodeRoot {ps_quote(self.source)} -ActivePluginRoot {ps_quote(self.active)}"
        return args

    def test_candidate_local_runner_uses_external_frontend_and_restores_environment(self) -> None:
        body = (
            "$env:VSCG_CUSTOM_NODE_ROOT='before'; "
            + self.call("run_frontend_workflow_validation.ps1")
            + f" -SourceSentinelPath {ps_quote(self.sentinel)}; "
            "if ($env:VSCG_CUSTOM_NODE_ROOT -ne 'before') { throw 'environment leaked' }"
        )
        result = self.run_ps(body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        sentinel = json.loads(self.sentinel.read_text(encoding="utf-8-sig"))
        self.assertFalse(sentinel["loaded_active_plugin"])
        self.assertEqual(Path(sentinel["active_plugin_root"]), self.active)
        self.assertEqual(Path(sentinel["loaded_candidate_root"]), self.source)
        self.assertTrue((self.frontend / "vitest.custom-node.config.mts").is_file())
        self.assertEqual(Path((self.base / "frontend source.txt").read_text().strip()), self.source)

    def test_default_source_reports_active_loading_truthfully(self) -> None:
        result = self.run_ps(self.call("run_frontend_workflow_validation.ps1", candidate=False) + f" -SourceSentinelPath {ps_quote(self.sentinel)}")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(self.sentinel.read_text(encoding="utf-8-sig"))["loaded_active_plugin"])

    def test_explicit_active_source_is_rejected(self) -> None:
        result = self.run_ps(self.call("run_frontend_workflow_validation.ps1").replace(ps_quote(self.active), ps_quote(self.source)))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("isolated candidate", result.stderr)

    def test_missing_frontend_is_reported_without_creating_workspace(self) -> None:
        shutil.rmtree(self.frontend)
        result = self.run_ps(self.call("run_frontend_workflow_validation.ps1"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Frontend workspace", result.stderr)
        self.assertFalse(self.frontend.exists())

    def test_sync_checks_all_sources_before_copying(self) -> None:
        (self.source / "verification/browser/customWorkflowRoundtrip.spec.ts").unlink()
        result = self.run_ps(self.call("sync_upstream_verification_assets.ps1", candidate=False))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("verification asset", result.stderr)
        self.assertFalse((self.frontend / "vitest.custom-node.config.mts").exists())

    def test_failure_restores_source_environment(self) -> None:
        # A sync failure must unwind the same environment boundary as runner failure.
        (self.source / "tools/sync_upstream_verification_assets.ps1").write_text("throw 'forced sync failure'", encoding="utf-8")
        result = self.run_ps("$env:VSCG_CUSTOM_NODE_ROOT='before'; try { " + self.call("run_frontend_workflow_validation.ps1") + " } catch { if ($env:VSCG_CUSTOM_NODE_ROOT -ne 'before') { throw 'environment leaked' }; Write-Output $_.Exception.Message }")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("forced sync failure", result.stdout)

    def test_missing_backend_fails_before_creating_run_directories(self) -> None:
        result = self.run_ps(self.call("run_custom_workflow_roundtrip.ps1") + f" -ComfyRoot {ps_quote(self.base / 'missing backend')}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ComfyUI workspace", result.stderr)
        self.assertFalse((self.source / "test_logs").exists())

    def test_external_frontend_environment_override(self) -> None:
        command = self.call("run_frontend_workflow_validation.ps1").replace(f" -FrontendRoot {ps_quote(self.frontend)}", "")
        result = self.run_ps(f"$env:VSCG_FRONTEND_ROOT={ps_quote(self.frontend)}; " + command)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.frontend / "vitest.custom-node.config.mts").exists())

    @unittest.skipUnless(os.name == "nt", "Windows junction/process argument contract")
    def test_browser_runner_mounts_candidate_and_quotes_paths_without_starting_server(self) -> None:
        comfy = self.base / "external backend"
        comfy.mkdir()
        (comfy / "main.py").write_text("raise AssertionError('must not execute')", encoding="utf-8")
        playwright = self.frontend / "node_modules/.bin/playwright.cmd"
        playwright.parent.mkdir(parents=True, exist_ok=True)
        playwright.write_text('@echo %PLAYWRIGHT_JSON_OUTPUT_FILE%>"%VSCG_TEST_SOURCE_CAPTURE%"\n@echo %*\n@exit /b 0\n', encoding="utf-8")
        captured = self.base / "process arguments.json"
        report = self.base / "browser output/report.json"
        body = (
            "$env:VSCG_CUSTOM_NODE_ROOT='before'; $env:PLAYWRIGHT_TEST_URL='old-url'; $env:TEST_COMFYUI_DIR='old-dir'; $env:PLAYWRIGHT_JSON_OUTPUT_FILE='old-report'; "
            "function Start-Process { param($FilePath,$ArgumentList,$WorkingDirectory,$RedirectStandardOutput,$RedirectStandardError,$WindowStyle,[switch]$PassThru) "
            "[ordered]@{ arguments=$ArgumentList; working_directory=$WorkingDirectory; window_style=$WindowStyle; source=$env:VSCG_CUSTOM_NODE_ROOT } | ConvertTo-Json | Set-Content -LiteralPath "
            + ps_quote(captured) + "; [pscustomobject]@{Id=2147483647;HasExited=$false} }; "
            "$global:probeCount=0; function Test-NetConnection { $global:probeCount++; [pscustomobject]@{TcpTestSucceeded=($global:probeCount -gt 1)} }; "
            + self.call("run_custom_workflow_roundtrip.ps1")
            + f" -ComfyRoot {ps_quote(comfy)} -SourceSentinelPath {ps_quote(self.sentinel)} -TestResultPath {ps_quote(report)}; "
            "if ($env:VSCG_CUSTOM_NODE_ROOT -ne 'before' -or $env:PLAYWRIGHT_TEST_URL -ne 'old-url' -or $env:TEST_COMFYUI_DIR -ne 'old-dir' -or $env:PLAYWRIGHT_JSON_OUTPUT_FILE -ne 'old-report') { throw 'environment leaked' }"
        )
        result = self.run_ps(body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('--reporter=line,json', result.stdout)
        self.assertEqual(Path((self.base / 'frontend source.txt').read_text().strip()), report)
        process = json.loads(captured.read_text(encoding="utf-8-sig"))
        self.assertEqual(process["window_style"], "Hidden")
        self.assertEqual(Path(process["working_directory"]), comfy)
        self.assertEqual(Path(process["source"]), self.source)
        for flag in ("--base-directory", "--user-directory", "--output-directory", "--temp-directory", "--front-end-root"):
            value = process["arguments"][process["arguments"].index(flag) + 1]
            self.assertTrue(value.startswith('"') and value.endswith('"'), value)
        self.assertEqual(process["arguments"][process["arguments"].index("--front-end-root") + 1].strip('"'), str(self.frontend / "dist"))
        sentinel = json.loads(self.sentinel.read_text(encoding="utf-8-sig"))
        self.assertFalse(sentinel["loaded_active_plugin"])
        self.assertEqual(Path(sentinel["mount_path"]).resolve(), self.source.resolve())
        run_root = Path(sentinel["mount_path"]).parents[1]
        self.assertEqual((run_root / "custom_nodes/ComfyUI_devtools").resolve(), self.frontend / "tools/devtools")
        self.assertEqual(sentinel["frontend_revision"], "mock-frontend-revision")
        self.assertEqual(Path(sentinel["frontend_devtools_root"]), self.frontend / "tools/devtools")
        self.assertEqual(sentinel["frontend_devtools_sha256"], {
            name: hashlib.sha256((self.frontend / "tools/devtools" / name).read_bytes()).hexdigest()
            for name in ("__init__.py", "helper.py")
        })
        self.assertTrue(run_root.is_relative_to(self.active / "assets/results/browser"))
        self.assertFalse(run_root.is_relative_to(self.source))

        # Changes to runtime/output trees must not change the source hash or be scanned.
        excluded = [".git", ".omx", "__pycache__", "ComfyUI", "ComfyUI_frontend", "node_modules", "test_logs", "assets/results"]
        for relative in excluded:
            directory = self.source / relative
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "must-not-read.txt").write_text("irrelevant runtime/output", encoding="utf-8")
        outside = self.base / "outside source"
        outside.mkdir()
        (outside / "must-not-read.txt").write_text("external linked data", encoding="utf-8")
        junction = self.source / "external-junction"
        result = self.run_ps(f"New-Item -ItemType Junction -Path {ps_quote(junction)} -Target {ps_quote(outside)} | Out-Null")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        guarded = excluded + ["external-junction"]
        guard = (
            "function Get-ChildItem { param([string]$LiteralPath,[switch]$Recurse,[switch]$File,[switch]$Force) "
            "if ($Recurse) { throw 'unbounded source recursion' }; "
            "$blocked=@(" + ",".join(ps_quote(self.source / item) for item in guarded) + "); "
            "if ($LiteralPath -in $blocked) { throw ('scanned excluded directory: ' + $LiteralPath) }; "
            "Microsoft.PowerShell.Management\\Get-ChildItem @PSBoundParameters }; "
        )
        result = self.run_ps(guard + body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        repeated = json.loads(self.sentinel.read_text(encoding="utf-8-sig"))
        self.assertEqual(repeated["source_content_sha256"], sentinel["source_content_sha256"])
        (self.source / "__init__.py").write_text("# changed candidate source\n", encoding="utf-8")
        result = self.run_ps(guard + body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        changed = json.loads(self.sentinel.read_text(encoding="utf-8-sig"))
        self.assertNotEqual(changed["source_content_sha256"], sentinel["source_content_sha256"])

    def test_browser_runner_rejects_existing_backend_before_writing_logs(self) -> None:
        comfy = self.base / "external backend"
        comfy.mkdir()
        (comfy / "main.py").touch()
        playwright = self.frontend / "node_modules/.bin/playwright.cmd"
        playwright.parent.mkdir(parents=True, exist_ok=True)
        playwright.touch()
        result = self.run_ps("function Test-NetConnection { [pscustomobject]@{TcpTestSucceeded=$true} }; " + self.call("run_custom_workflow_roundtrip.ps1") + f" -ComfyRoot {ps_quote(comfy)}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already in use", result.stderr)
        self.assertFalse((self.source / "test_logs").exists())

    def test_missing_browser_devtools_fails_before_sync_or_runtime_creation(self) -> None:
        comfy = self.base / "external backend"
        comfy.mkdir()
        (comfy / "main.py").touch()
        (self.frontend / "tools/devtools/__init__.py").unlink()
        result = self.run_ps(self.call("run_custom_workflow_roundtrip.ps1") + f" -ComfyRoot {ps_quote(comfy)}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fixture devtools are missing", result.stderr)
        self.assertFalse((self.frontend / "playwright.custom-node.config.mts").exists())
        self.assertFalse((self.active / "assets/results/browser").exists())

    def test_missing_vitest_fails_before_sync_or_sentinel(self) -> None:
        self.vitest.unlink()
        result = self.run_ps(self.call("run_frontend_workflow_validation.ps1") + f" -SourceSentinelPath {ps_quote(self.sentinel)}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Frontend Vitest dependencies are missing", result.stderr)
        self.assertFalse(self.sentinel.exists())
        self.assertFalse((self.frontend / "vitest.custom-node.config.mts").exists())

    def test_browser_rejects_output_root_nested_inside_candidate(self) -> None:
        nested_active = self.source / "nested active"
        nested_active.mkdir()
        comfy = self.base / "external backend"
        comfy.mkdir()
        (comfy / "main.py").touch()
        (self.frontend / "node_modules/.bin/playwright.cmd").touch()
        command = self.call("run_custom_workflow_roundtrip.ps1").replace(ps_quote(self.active), ps_quote(nested_active))
        result = self.run_ps("function Test-NetConnection { [pscustomobject]@{TcpTestSucceeded=$false} }; " + command + f" -ComfyRoot {ps_quote(comfy)}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the isolated candidate", result.stderr)
        self.assertFalse((nested_active / "assets/results/browser").exists())


if __name__ == "__main__":
    unittest.main()
