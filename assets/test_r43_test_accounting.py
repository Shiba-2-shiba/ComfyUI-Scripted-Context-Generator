"""No skipped, deselected, xfailed or unexecuted tests masquerade as a clean run."""
import copy
from types import SimpleNamespace
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tools import verify_realizer_v2_candidate as verifier


def outcome():
    return {"schema_version": "r43-test-outcomes/v1", "exit_code": 0,
            "collected_nodeids": ["assets/test_a.py::test_a"], "items": [{
                "nodeid": "assets/test_a.py::test_a",
                "phases": {"setup": "passed", "call": "passed", "teardown": "passed"},
                "xfail": False, "xpass": False,
                "subtests": {"passed": 2, "failed": 0, "skipped": 0, "xfail": 0, "xpass": 0},
            }], "deselected_nodeids": [], "collection_errors": [], "collection_skipped": [], "duplicate_reports": []}


def test_full_execution_and_subtest_accounting_are_distinct():
    payload = outcome()
    counts = verifier.validate_outcomes(payload, payload["collected_nodeids"])
    assert counts["tests"] == counts["passed"] == 1 and counts["subtests"] == 2
    for field in ("items", "collected_nodeids"):
        broken = copy.deepcopy(payload)
        broken[field] = []
        with pytest.raises(ValueError):
            verifier.validate_outcomes(broken, payload["collected_nodeids"])


@pytest.mark.parametrize("kind", ["skipped", "xfail", "xpass", "setup", "teardown", "subtest", "deselected", "collect_error"])
def test_exceptional_outcomes_have_explicit_nonzero_counters(kind):
    payload = outcome()
    item = payload["items"][0]
    if kind in {"skipped", "xfail"}:
        item["phases"]["call"] = "skipped"
        item["xfail"] = kind == "xfail"
    elif kind == "xpass":
        item["xpass"] = True
    elif kind in {"setup", "teardown"}:
        item["phases"][kind] = "failed"
    elif kind == "subtest":
        item["subtests"]["failed"] = 1
    elif kind == "deselected":
        payload["deselected_nodeids"] = ["assets/test_b.py::test_b"]
    else:
        payload["collection_errors"] = ["assets/test_b.py"]
    counts = verifier.validate_outcomes(payload, payload["collected_nodeids"])
    assert any(counts[key] for key in counts if key not in {"tests", "passed", "subtests"})


def test_duplicate_phase_and_missing_teardown_are_invalid():
    for mutation in ("duplicate", "teardown"):
        payload = outcome()
        if mutation == "duplicate":
            payload["duplicate_reports"] = ["assets/test_a.py::test_a:call"]
        else:
            del payload["items"][0]["phases"]["teardown"]
        with pytest.raises(ValueError):
            verifier.validate_outcomes(payload, payload["collected_nodeids"])


def test_subtest_reports_do_not_replace_main_test_phases(monkeypatch):
    report = {"items": {}, "deselected_nodeids": [], "collection_errors": [], "duplicate_reports": []}
    with monkeypatch.context() as scoped:
        scoped.setattr(verifier, "_TEST_REPORT", report)
        for phase in ("setup", "call", "teardown"):
            verifier.pytest_runtest_logreport(SimpleNamespace(nodeid="node", when=phase, outcome="passed", passed=True, skipped=False))
        verifier.pytest_runtest_logreport(SimpleNamespace(nodeid="node", when="call", outcome="failed",
            passed=False, skipped=False, context=SimpleNamespace()))
    assert report["items"]["node"]["phases"]["call"] == "passed"
    assert report["items"]["node"]["subtests"]["failed"] == 1
    assert not report["duplicate_reports"]


def test_module_level_skip_is_recorded_even_when_other_tests_pass(tmp_path):
    (tmp_path / "test_pass.py").write_text("def test_ok():\n    pass\n")
    (tmp_path / "test_skip.py").write_text("import pytest\npytest.skip('module unavailable', allow_module_level=True)\n")
    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)
    env[verifier.COLLECTION_ENV] = str(tmp_path / "collected.json")
    env[verifier.OUTCOMES_ENV] = str(tmp_path / "outcomes.json")
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
        "-p", "tools.verify_realizer_v2_candidate", "--rootdir", str(tmp_path),
        str(tmp_path / "test_pass.py"), str(tmp_path / "test_skip.py")],
        cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads((tmp_path / "outcomes.json").read_text())
    assert payload["collection_skipped"] and len(payload["collected_nodeids"]) == 1
    counts = verifier.validate_outcomes(payload, payload["collected_nodeids"])
    assert counts["collection_skipped"] == 1
