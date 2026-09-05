"""Collect candidate-owned gate executions and bind their original evidence.

Python gates run in a fresh candidate process. External gate producers can use
``--bind-result`` and ``--run-record`` to bind reports from an actual prior run;
the record must contain command, cwd, exit_code, before/after identities,
log_path and (for frontend/browser) sentinel_path. Binding does not run a gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.build_prompt_quality_confirmation import (
    _import_sentinel, _sanitized_environment, _snapshot_content_hash,
)
from tools.build_prompt_quality_verification import (
    REQUIRED_GATES, _candidate_root_identity, _validate_summary,
    _validate_v150_evidence,
)
from tools.prompt_quality_loop import build_source_manifest
from tools.workflow_prompt_runner import canonical_json_bytes

PYTHON_GATES = {
    "action_pools": ("build_action_pools.py", ["--check"]),
    "compatibility_review": ("build_compatibility_review.py", ["--check"]),
    "data_validation": ("validate_prompt_data.py", []),
    "full_flow": ("verify_full_flow.py", []),
    "widgets": ("check_widgets_values.py", []),
    "python_tests": (None, []),
}
DIRECT_GATES = {"target_comparison", "blind_review", "prompt_quality_confirmation"}


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(root: Path) -> dict:
    return {
        "candidate_root": str(root.resolve()),
        "candidate_root_identity_sha256": _candidate_root_identity(root),
        "candidate_source_tree_sha256": build_source_manifest(root)["source_tree_hash"],
        "candidate_snapshot_content_sha256": _snapshot_content_hash(root),
    }


def parse_summary(gate: str, output: str) -> dict:
    """Require the gate's actual report; an exit status alone is insufficient."""
    if gate in {"action_pools", "compatibility_review", "data_validation"}:
        report = json.loads(output)
        if not isinstance(report, dict) or not isinstance(report.get("ERROR"), list):
            raise ValueError("Gate did not emit its structured error report")
        errors = len(report["ERROR"])
        if gate == "data_validation":
            if not isinstance(report.get("WARNING"), list):
                raise ValueError("Data validation warning report is missing")
            return {"errors": errors, "warnings": len(report["WARNING"])}
        code = ("action_pool_source_summary" if gate == "action_pools"
                else "compatibility_review_generation_summary")
        rows = [row for row in report.get("INFO", []) if row.get("code") == code]
        if len(rows) != 1:
            raise ValueError(f"Missing or ambiguous {code}")
        row = rows[0]
        if gate == "compatibility_review":
            return {"errors": errors, "missing_rows": row["missing_current_rows"],
                    "extra_rows": row["extra_generated_rows"]}
        counts = [row.get(key) for key in ("runtime_location_count", "source_location_count")]
        if any(type(count) is not int or count <= 0 for count in counts):
            raise ValueError("Action pool counts are absent or empty")
        missing = sum(len(item.get("missing_source_locations", [])) for item in report["ERROR"])
        return {"errors": errors, "missing_pools": max(missing, counts[0] - counts[1])}
    if gate == "full_flow" and output.strip() == "OK: verify_full_flow passed":
        # The script reports one successful full-flow suite, not per-assert counts.
        return {"checks_passed": 1, "failures": 0}
    if gate == "widgets":
        lines = [line for line in output.splitlines() if line.strip()]
        if lines and all(re.fullmatch(r"OK: no widget_values issues detected for .+ \[.+\]\.", line) for line in lines):
            return {"issues": 0, "samples_checked": len(lines)}
    raise ValueError(f"No complete successful {gate} report")


def external_summary(gate: str, report: dict) -> dict:
    """Read counters emitted by Vitest/Playwright, retaining their failure rules."""
    if gate == "frontend":
        fields = ("numTotalTests", "numPassedTests", "numFailedTests", "numPendingTests", "numTodoTests")
        if any(type(report.get(field)) is not int or report[field] < 0 for field in fields):
            raise ValueError("Incomplete Vitest JSON report")
        if (report.get("success") is not True or report["numTotalTests"] != report["numPassedTests"]
                or any(report[field] != 0 for field in fields[2:])):
            raise ValueError("Vitest report contains incomplete or unsuccessful tests")
        return {"tests_passed": report["numPassedTests"], "failures": report["numFailedTests"]}
    if gate == "browser":
        stats = report.get("stats", {})
        fields = ("expected", "unexpected", "flaky", "skipped")
        if any(type(stats.get(field)) is not int or stats[field] < 0 for field in fields):
            raise ValueError("Incomplete Playwright JSON report")
        if any(stats[field] != 0 for field in fields[1:]) or report.get("errors") != []:
            raise ValueError("Playwright report contains errors, flaky or skipped tests")
        return {"tests_passed": stats["expected"], "failures": stats["unexpected"]}
    raise ValueError(f"Unsupported external report: {gate}")


def child_run(gate: str, root: Path, forbidden_root: Path, record_path: Path) -> int:
    if ROOT != root.resolve() or Path.cwd().resolve() != ROOT:
        raise ValueError("Child must execute the candidate-owned collector from its root")
    before = identity(root)
    record = {"before": before, "cwd": str(Path.cwd().resolve()), "gate_name": gate}
    exit_code = 0
    try:
        filename, arguments = PYTHON_GATES[gate]
        if gate == "python_tests":
            suite = unittest.defaultTestLoader.discover(str(root / "assets"), pattern="test_*.py")
            result = unittest.TextTestRunner(verbosity=1).run(suite)
            failed = len(result.failures)
            errors = len(result.errors)
            skipped = len(result.skipped)
            expected = len(result.expectedFailures)
            unexpected = len(result.unexpectedSuccesses)
            record["summary"] = {
                "tests_run": result.testsRun,
                "tests_passed": result.testsRun - failed - errors - skipped - expected - unexpected,
                "failures": failed + unexpected, "errors": errors, "skipped": skipped + expected,
            }
            exit_code = 0 if result.wasSuccessful() else 1
        else:
            entrypoint = root / "tools" / filename
            record["entrypoint"] = str(entrypoint)
            sys.argv = [str(entrypoint), *arguments]
            sys.path.insert(0, str(root / "tools"))
            runpy.run_path(str(entrypoint), run_name="__main__")
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    except Exception:
        traceback.print_exc()
        exit_code = 1
    try:
        record["sentinel"] = _import_sentinel(root, forbidden_root)
        record["after"] = identity(root)
        if record["after"] != before:
            raise ValueError("Candidate source or content changed during gate execution")
    except Exception:
        traceback.print_exc()
        exit_code = 1
    record["exit_code"] = exit_code
    write_json(record_path, record)
    return exit_code


def bind_result(gate: str, root: Path, output_dir: Path, result_path: Path, run_record: dict) -> Path:
    binding = identity(root)
    if run_record.get("before") != binding or run_record.get("after") != binding:
        raise ValueError("Execution must prove unchanged candidate identity before and after the run")
    command = run_record.get("command")
    if (run_record.get("exit_code") != 0 or not isinstance(command, list) or not command
            or any(not isinstance(arg, str) or not arg for arg in command)
            or run_record.get("cwd") != str(root.resolve())):
        raise ValueError("Execution record is not a successful candidate command")
    log_path = Path(run_record["log_path"]).resolve()
    if not log_path.is_file():
        raise ValueError("Execution log is missing")
    result = read_json(result_path)
    if gate in {"frontend", "browser"}:
        raw_path = result_path.resolve()
        summary = external_summary(gate, result)
        _validate_summary(gate, summary)
        result = {
            **binding, "schema_version": "prompt-quality-gate-result/v2",
            "gate_name": gate, "status": "pass", "exit_code": 0,
            "summary": summary, "raw_result_path": str(raw_path), "raw_result_sha256": sha256(raw_path),
        }
        result_path = output_dir / f"{gate}.result.json"
        if result_path.resolve() == raw_path:
            raise ValueError("Raw report path must differ from the normalized result path")
        write_json(result_path, result)
    evidence = {
        **binding, "schema_version": "prompt-quality-verification-evidence/v2",
        "gate_name": gate, "status": "pass", "exit_code": 0,
        "command": command, "cwd": run_record["cwd"],
        "result_path": str(result_path.resolve()), "result_sha256": sha256(result_path),
        "log_path": str(log_path), "log_sha256": sha256(log_path),
        "execution": run_record,
    }
    if gate not in DIRECT_GATES:
        if (result.get("schema_version") != "prompt-quality-gate-result/v2"
                or result.get("status") != "pass" or result.get("exit_code") != 0
                or result.get("gate_name") != gate
                or any(result.get(key) != value for key, value in binding.items())):
            raise ValueError("Gate result is not a passing candidate-bound report")
        _validate_summary(gate, result["summary"])
        sentinel_path = Path(run_record["sentinel_path"]).resolve()
        sentinel = read_json(sentinel_path)
        candidate_modules = sentinel.get("imported_candidate_modules")
        if candidate_modules is not None:
            if not candidate_modules or sentinel.get("candidate_root") != str(root.resolve()):
                raise ValueError("Python sentinel has no candidate imports")
            for module_path in candidate_modules.values():
                Path(module_path).resolve().relative_to(root.resolve())
        elif (sentinel.get("loaded_candidate_root") != str(root.resolve())
              or sentinel.get("loaded_active_plugin") is not False):
            raise ValueError("External sentinel does not prove candidate isolation")
        evidence["process_isolation"] = {
            "cwd": run_record["cwd"], "loaded_active_plugin": False,
            "loaded_candidate_root": str(root.resolve()),
            "sentinel_sha256": sha256(sentinel_path), "sentinel_path": str(sentinel_path),
        }
    else:
        source = result.get("candidate_source_tree_sha256")
        if source != binding["candidate_source_tree_sha256"]:
            raise ValueError("Direct artifact is bound to a different source tree")
        verdict = result.get("automatic_comparison_verdict", result.get("automatic_verdict")) if gate == "target_comparison" else result.get("status", result.get("verdict"))
        if verdict != "pass":
            raise ValueError("Direct artifact did not pass")
        # The final builder still checks comparison/review/confirmation schemas,
        # cross-artifact hashes, and the exact eleven-gate inventory.
    _validate_v150_evidence(gate, evidence, candidate_root=root,
                           source_hash=binding["candidate_source_tree_sha256"],
                           content_hash=binding["candidate_snapshot_content_sha256"])
    evidence_path = output_dir / f"{gate}.evidence.json"
    if evidence_path.exists():
        raise ValueError("Evidence already exists; use a fresh output directory")
    write_json(evidence_path, evidence)
    return evidence_path


def run_gate(gate: str, root: Path, output_dir: Path, forbidden_root: Path) -> Path:
    root, output_dir, forbidden_root = root.resolve(), output_dir.resolve(), forbidden_root.resolve()
    if root == forbidden_root or not root.is_dir():
        raise ValueError("A separate existing candidate root is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / f"{gate}.evidence.json"
    if evidence_path.exists():
        raise ValueError(f"Evidence already exists: {evidence_path}; use a fresh output directory")
    before = identity(root)
    child_path = output_dir / f"{gate}.execution.json"
    log_path = output_dir / f"{gate}.log"
    command = [sys.executable, str(root / "tools/run_variation_verification.py"),
               "--candidate-root", str(root), "--output-dir", str(output_dir),
               "--forbidden-root", str(forbidden_root), "--gate", gate,
               "--child-record", str(child_path)]
    with log_path.open("wb") as log:
        completed = subprocess.run(command, cwd=root, env=_sanitized_environment(root),
                                   stdout=log, stderr=subprocess.STDOUT, check=False)
    after = identity(root)
    if completed.returncode != 0:
        raise ValueError(f"{gate} exited {completed.returncode}; see {log_path}")
    record = read_json(child_path)
    if record.get("before") != before or record.get("after") != after or before != after:
        raise ValueError("Candidate changed during the gate execution")
    summary = record.get("summary") if gate == "python_tests" else parse_summary(gate, log_path.read_text(encoding="utf-8"))
    _validate_summary(gate, summary)
    result_path = output_dir / f"{gate}.result.json"
    write_json(result_path, {**before, "schema_version": "prompt-quality-gate-result/v2",
                            "gate_name": gate, "status": "pass", "exit_code": 0, "summary": summary})
    sentinel_path = output_dir / f"{gate}.sentinel.json"
    write_json(sentinel_path, record.pop("sentinel"))
    record.update(command=command, log_path=str(log_path), sentinel_path=str(sentinel_path))
    write_json(child_path, record)
    return bind_result(gate, root, output_dir, result_path, record)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--gate", action="append", choices=["all", *sorted(REQUIRED_GATES)], required=True)
    parser.add_argument("--forbidden-root", type=Path, default=ROOT)
    parser.add_argument("--bind-result", type=Path)
    parser.add_argument("--run-record", type=Path)
    parser.add_argument("--child-record", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    gates = list(PYTHON_GATES) if "all" in args.gate else list(dict.fromkeys(args.gate))
    try:
        if args.child_record:
            if len(gates) != 1 or gates[0] not in PYTHON_GATES:
                raise ValueError("Child execution requires one Python gate")
            return child_run(gates[0], args.candidate_root, args.forbidden_root, args.child_record)
        if args.bind_result or args.run_record:
            if not (args.bind_result and args.run_record) or len(gates) != 1:
                raise ValueError("Binding requires one gate, --bind-result and --run-record")
            print(bind_result(gates[0], args.candidate_root, args.output_dir,
                              args.bind_result, read_json(args.run_record)))
        else:
            for gate in gates:
                if gate not in PYTHON_GATES:
                    raise ValueError(f"{gate} requires an original result and execution record")
                print(run_gate(gate, args.candidate_root, args.output_dir, args.forbidden_root), flush=True)
    except (ValueError, OSError, KeyError, RuntimeError) as exc:
        print(f"Verification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
