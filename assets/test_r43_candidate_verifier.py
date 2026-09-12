"""Bounded verifier checks: subprocesses are mocked to avoid recursive runs."""

import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from tools import verify_realizer_v2_candidate as verifier


def write_accounting(env, nodeids):
    Path(env[verifier.COLLECTION_ENV]).write_text(json.dumps({"nodeids": nodeids}), encoding="utf-8")
    Path(env[verifier.OUTCOMES_ENV]).write_text(json.dumps({
        "schema_version": "r43-test-outcomes/v1", "exit_code": 0, "collected_nodeids": sorted(nodeids),
        "items": [{"nodeid": nodeid, "phases": {"setup": "passed", "call": "passed", "teardown": "passed"},
                   "xfail": False, "xpass": False,
                   "subtests": {"passed": 0, "failed": 0, "skipped": 0, "xfail": 0, "xpass": 0}}
                  for nodeid in sorted(nodeids)],
        "deselected_nodeids": [], "collection_errors": [], "collection_skipped": [], "duplicate_reports": [],
    }), encoding="utf-8")


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "source"
    for name in (
        "assets/test_n27_z.py", "assets/test_n27_a.py",
        "assets/test_r43_transport.py", "assets/test_prompt_realizer_v2.py",
        "assets/test_syntax_family_selector.py", "prompt_renderer.py",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# source\n", encoding="utf-8")
    return root


def command_result(code=0, *, write_collection=True, change_source=None):
    def run(command, **kwargs):
        if write_collection:
            write_accounting(kwargs["env"], [
                    "assets/test_n27_a.py::test_case[punctuation::kept]",
                    "assets/test_r43_transport.py::test_transport",
                ])
        if change_source is not None:
            change_source.write_text("# changed during verification\n", encoding="utf-8")
        kwargs["stdout"].write("bounded command output\n")
        return subprocess.CompletedProcess(command, code)
    return run


def verdict(output):
    return json.loads((output / "verdict.json").read_text(encoding="utf-8"))


def test_focused_files_are_sorted_and_include_new_r43_tests(source):
    files = verifier.test_files(source, "focused")
    assert files == sorted(files)
    assert "assets/test_r43_transport.py" in files
    assert "assets/test_n27_a.py" in files
    assert "assets/test_n27_z.py" in files
    assert "assets/test_prompt_realizer_v2.py" in files
    assert "assets/test_syntax_family_selector.py" in files


@pytest.mark.parametrize("command_exit, expected_exit, status", [
    (0, 0, "PASS"), (1, 1, "FAIL"), (2, 2, "ERROR"), (5, 2, "ERROR"),
])
def test_command_failures_are_not_success(source, tmp_path, command_exit, expected_exit, status):
    output = tmp_path / "receipt"
    with mock.patch.object(verifier.subprocess, "run", side_effect=command_result(command_exit)):
        assert verifier.verify("focused", output, root=source) == expected_exit
    result = verdict(output)
    assert result["status"] == status
    assert result["checks"][0]["exit_code"] == command_exit


def test_existing_output_is_preserved_without_running_commands(source, tmp_path):
    output = tmp_path / "receipt"
    output.mkdir()
    sentinel = output / "verdict.json"
    sentinel.write_bytes(b"existing evidence")
    with mock.patch.object(verifier.subprocess, "run") as run:
        assert verifier.verify("focused", output, root=source) == 2
    run.assert_not_called()
    assert sentinel.read_bytes() == b"existing evidence"


def test_missing_executable_is_an_environment_error(source, tmp_path):
    output = tmp_path / "receipt"
    with mock.patch.object(verifier.subprocess, "run", side_effect=FileNotFoundError("python missing")):
        assert verifier.verify("focused", output, root=source) == 2
    assert verdict(output)["status"] == "ERROR"


def test_missing_collection_cannot_pass(source, tmp_path):
    output = tmp_path / "receipt"
    with mock.patch.object(verifier.subprocess, "run", side_effect=command_result(write_collection=False)):
        assert verifier.verify("focused", output, root=source) == 2
    assert verdict(output)["status"] == "ERROR"


def test_source_change_invalidates_success(source, tmp_path):
    output = tmp_path / "receipt"
    with mock.patch.object(verifier.subprocess, "run", side_effect=command_result(change_source=source / "prompt_renderer.py")):
        assert verifier.verify("focused", output, root=source) == 2
    result = verdict(output)
    assert result["status"] == "INVALID"
    assert result["source_before"] != result["source_after"]


def test_previously_missing_supplemental_input_invalidates_success(source, tmp_path):
    output = tmp_path / "receipt"
    with mock.patch.object(verifier.subprocess, "run", side_effect=command_result(change_source=source / "prompts.jsonl")):
        assert verifier.verify("focused", output, root=source) == 2
    result = verdict(output)
    assert result["status"] == "INVALID"
    assert result["source_before"] == result["source_after"]
    assert result["supplemental_before"] != result["supplemental_after"]
    supplemental = json.loads((output / "supplemental-inputs.json").read_text(encoding="utf-8"))
    assert supplemental["before"]["prompts.jsonl"] is None
    assert supplemental["after"]["prompts.jsonl"] is not None


def test_executed_variation_script_change_invalidates_success(source, tmp_path):
    script = source / "assets/calc_variations.py"
    script.write_text("# original variation calculator\n", encoding="utf-8")
    output = tmp_path / "receipt"
    with mock.patch.object(verifier.subprocess, "run", side_effect=command_result(change_source=script)):
        assert verifier.verify("focused", output, root=source) == 2
    result = verdict(output)
    assert result["status"] == "INVALID"
    assert result["source_before"] == result["source_after"]
    assert result["supplemental_before"] != result["supplemental_after"]


def test_canonical_receipts_are_identical_across_output_paths(source, tmp_path):
    outputs = [tmp_path / "one", tmp_path / "two"]
    for output in outputs:
        with mock.patch.object(verifier.subprocess, "run", side_effect=command_result()):
            assert verifier.verify("focused", output, root=source) == 0
    for name in ("verdict.json", "test-collection.json"):
        assert (outputs[0] / name).read_bytes() == (outputs[1] / name).read_bytes()
        assert str(tmp_path) not in (outputs[0] / name).read_text(encoding="utf-8")
    collection = json.loads((outputs[0] / "test-collection.json").read_text(encoding="utf-8"))
    expected = hashlib.sha256(verifier.canonical_bytes(collection["nodeids"])).hexdigest()
    assert collection["sha256"] == expected


def test_collection_hook_keeps_full_parametrized_ids(tmp_path, monkeypatch):
    destination = tmp_path / "collected.json"
    monkeypatch.setenv(verifier.COLLECTION_ENV, str(destination))
    nodeids = ["assets/test_z.py::test_value[space :: unicode 日本語]", "assets/test_a.py::test_a"]
    session = SimpleNamespace(items=[SimpleNamespace(nodeid=nodeid) for nodeid in nodeids])
    verifier.pytest_collection_finish(session)
    assert json.loads(destination.read_text(encoding="utf-8"))["nodeids"] == sorted(nodeids)


def test_unimplemented_stage_and_missing_inputs_are_errors(source, tmp_path):
    with mock.patch.object(verifier.subprocess, "run") as run:
        assert verifier.verify("intake", tmp_path / "intake", root=source) == 2
        (source / "assets/test_syntax_family_selector.py").unlink()
        assert verifier.verify("focused", tmp_path / "missing", root=source) == 2
    run.assert_not_called()


@pytest.mark.parametrize("nodeids", [[], [42], ["outside.py::test_a"],
    ["assets/test_n27_a.py::test_a", "assets/test_n27_a.py::test_a"]])
def test_malformed_collection_cannot_pass(source, tmp_path, nodeids):
    def run(command, **kwargs):
        Path(kwargs["env"][verifier.COLLECTION_ENV]).write_text(
            json.dumps({"nodeids": nodeids}), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    output = tmp_path / "receipt"
    with mock.patch.object(verifier.subprocess, "run", side_effect=run):
        assert verifier.verify("focused", output, root=source) == 2
    assert verdict(output)["status"] == "ERROR"


def test_regression_records_later_failure_and_runs_all_existing_checks(source, tmp_path, monkeypatch):
    for name in (
        "assets/test_context_codec.py", "assets/test_schema.py", "assets/test_prompt_renderer.py",
        "assets/test_prompt_snapshots.py", "assets/test_vocab_lint.py", "assets/calc_variations.py",
        "tools/validate_prompt_data.py", "tools/check_variation_scope.py", "tools/build_action_pools.py",
        "tools/build_compatibility_review.py", "tools/verify_full_flow.py", "asset_validator.py",
    ):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# input\n", encoding="utf-8")
    monkeypatch.setenv("PYTEST_ADDOPTS", "-k ignore_contract")
    executed = []

    def run(command, **kwargs):
        executed.append(command)
        assert kwargs["shell"] is False
        assert "PYTEST_ADDOPTS" not in kwargs["env"]
        assert "install" not in command
        if command[1:3] == ["-m", "pytest"]:
            write_accounting(kwargs["env"], ["assets/test_schema.py::test_contract"])
        return subprocess.CompletedProcess(command, 1 if command[1] == "tools/verify_full_flow.py" else 0)

    output = tmp_path / "receipt"
    with mock.patch.object(verifier.subprocess, "run", side_effect=run):
        assert verifier.verify("regression", output, root=source) == 1
    checks = {check["name"]: check for check in verdict(output)["checks"]}
    assert checks["full_flow"]["status"] == "FAIL"
    assert checks["asset_validation"]["status"] == "PASS"
    assert len(executed) == 8


def test_missing_validator_dependency_is_error(tmp_path):
    output = tmp_path / "receipt"
    (output / "logs").mkdir(parents=True)

    def run(command, **kwargs):
        kwargs["stdout"].write("ModuleNotFoundError: No module named 'missing_dependency'\n")
        return subprocess.CompletedProcess(command, 1)

    with mock.patch.object(verifier.subprocess, "run", side_effect=run):
        check, _ = verifier.run_command("validator", ["python", "validator.py"], tmp_path, output, {})
    assert check["exit_code"] == 1
    assert check["status"] == "ERROR"
