"""Run existing R43 development checks; exit 0=pass, 1=failure, 2=invalid/error.

Intake composes existing checks; adoption preflight never runs formal gates.
This is also a pytest plugin
that records exact collected node IDs, without parsing pytest's human output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COLLECTION_ENV = "SCG_R43_TEST_COLLECTION"
OUTCOMES_ENV = "SCG_R43_TEST_OUTCOMES"
STAGES = ("focused", "regression", "intake", "adoption-preflight")
_TEST_REPORT = None

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def canonical_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def write_json(path, value):
    with path.open("xb") as handle:
        handle.write(canonical_bytes(value))


def supplemental_inputs(root):
    # Preserve the existing source hash contract while covering its known gaps.
    return {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest() if (root / name).is_file() else None
        for name in ("assets/calc_variations.py", "assets/compatibility_review.csv", "mood_map.json", "prompts.jsonl",
                     "pytest.ini", "templates.txt", "assets/conftest.py", "pyproject.toml", "setup.cfg", "tox.ini",
                     "docs/diversity_refactor/spec.md", "docs/diversity_refactor/r43_metric_contract.json",
                     "docs/diversity_refactor/r43_development_review.json")
    }


def pytest_collection_finish(session):
    destination = os.environ.get(COLLECTION_ENV)
    if destination:
        write_json(Path(destination), {"nodeids": sorted(item.nodeid for item in session.items)})


def pytest_sessionstart(session):
    global _TEST_REPORT
    _TEST_REPORT = {"items": {}, "deselected_nodeids": [], "collection_errors": [], "collection_skipped": [], "duplicate_reports": []}


def pytest_deselected(items):
    if _TEST_REPORT is not None:
        _TEST_REPORT["deselected_nodeids"].extend(item.nodeid for item in items)


def pytest_collectreport(report):
    if _TEST_REPORT is not None:
        if report.failed:
            _TEST_REPORT["collection_errors"].append(report.nodeid)
        elif report.skipped:
            _TEST_REPORT["collection_skipped"].append(report.nodeid)


def pytest_runtest_logreport(report):
    if _TEST_REPORT is None:
        return
    item = _TEST_REPORT["items"].setdefault(report.nodeid, {
        "nodeid": report.nodeid, "phases": {}, "xfail": False, "xpass": False,
        "subtests": {"passed": 0, "failed": 0, "skipped": 0, "xfail": 0, "xpass": 0},
    })
    wasxfail = hasattr(report, "wasxfail")
    outcome = ("xfail" if report.skipped else "xpass") if wasxfail else report.outcome
    if hasattr(report, "context"):
        item["subtests"][outcome] += 1
    else:
        if report.when in item["phases"]:
            _TEST_REPORT["duplicate_reports"].append(report.nodeid + ":" + report.when)
        item["phases"][report.when] = report.outcome
        item["xfail"] |= wasxfail and report.skipped
        item["xpass"] |= wasxfail and report.passed


def pytest_sessionfinish(session, exitstatus):
    destination = os.environ.get(OUTCOMES_ENV)
    if destination and _TEST_REPORT is not None:
        write_json(Path(destination), {
            "schema_version": "r43-test-outcomes/v1", "exit_code": int(exitstatus),
            "collected_nodeids": sorted(item.nodeid for item in session.items),
            "items": [_TEST_REPORT["items"][key] for key in sorted(_TEST_REPORT["items"])],
            "deselected_nodeids": sorted(_TEST_REPORT["deselected_nodeids"]),
            "collection_errors": sorted(_TEST_REPORT["collection_errors"]),
            "collection_skipped": sorted(_TEST_REPORT["collection_skipped"]),
            "duplicate_reports": sorted(_TEST_REPORT["duplicate_reports"]),
        })


def validate_outcomes(payload, nodeids):
    if (not isinstance(payload, dict) or payload.get("schema_version") != "r43-test-outcomes/v1"
            or type(payload.get("exit_code")) is not int
            or payload.get("collected_nodeids") != nodeids or not isinstance(payload.get("items"), list)):
        raise ValueError("Test outcomes do not match the collected tests")
    items = payload["items"]
    if [item.get("nodeid") for item in items] != nodeids:
        raise ValueError("Missing, duplicate or uncollected executed test")
    counts = dict(tests=len(nodeids), passed=0, failed=0, skipped=0, xfail=0, xpass=0,
                  setup_teardown_errors=0, deselected=0, collection_errors=0, collection_skipped=0,
                  subtests=0, subtests_failed=0, subtests_skipped=0, subtests_xfail=0, subtests_xpass=0)
    for item in items:
        phases, subtests = item.get("phases"), item.get("subtests")
        if (not isinstance(phases, dict) or set(phases) - {"setup", "call", "teardown"}
                or any(outcome not in {"passed", "failed", "skipped"} for outcome in phases.values())
                or not {"setup", "teardown"} <= phases.keys()
                or phases["setup"] == "passed" and "call" not in phases
                or not isinstance(subtests, dict) or set(subtests) != {"passed", "failed", "skipped", "xfail", "xpass"}
                or any(type(count) is not int or count < 0 for count in subtests.values())
                or type(item.get("xfail")) is not bool or type(item.get("xpass")) is not bool):
            raise ValueError("Malformed test phase/subtest outcomes")
        for field in ("xfail", "xpass"):
            counts[field] += int(item[field])
        counts["setup_teardown_errors"] += sum(phases[phase] == "failed" for phase in ("setup", "teardown"))
        counts["failed"] += int("failed" in phases.values())
        counts["skipped"] += int("skipped" in phases.values() and not item["xfail"])
        counts["passed"] += int(all(outcome == "passed" for outcome in phases.values()) and not item["xpass"])
        counts["subtests"] += sum(subtests.values())
        for field in ("failed", "skipped", "xfail", "xpass"):
            counts["subtests_" + field] += subtests[field]
    for field in ("deselected_nodeids", "collection_errors", "collection_skipped", "duplicate_reports"):
        if not isinstance(payload.get(field), list) or any(not isinstance(value, str) for value in payload[field]):
            raise ValueError("Missing or malformed test accounting")
    counts["deselected"] = len(payload["deselected_nodeids"])
    counts["collection_errors"] = len(payload["collection_errors"])
    counts["collection_skipped"] = len(payload["collection_skipped"])
    if payload["duplicate_reports"]:
        raise ValueError("Duplicated test phase reports")
    return counts


def test_files(root, stage):
    if stage == "focused":
        patterns = ("test_n27*.py", "test_r43*.py")
        names = ("test_syntax_family_selector.py", "test_prompt_realizer_v2.py")
    elif stage == "regression":
        patterns = ("test_context*.py",)
        names = ("test_schema.py", "test_prompt_renderer.py", "test_prompt_snapshots.py", "test_vocab_lint.py")
    else:
        raise ValueError(f"Stage is not implemented: {stage}")
    files = {f"assets/{name}" for name in names}
    for pattern in patterns:
        matches = list((root / "assets").glob(pattern))
        if not matches:
            raise ValueError(f"No test files match assets/{pattern}")
        files.update(path.relative_to(root).as_posix() for path in matches)
    for name in files:
        if not (root / name).is_file():
            raise ValueError(f"Missing test input: {name}")
    return sorted(files)


def commands_for(stage, files):
    commands = [("pytest", [sys.executable, "-m", "pytest", "--rootdir=.",
                            "-o", "addopts=", "-p", "no:cacheprovider",
                            "-p", "tools.verify_realizer_v2_candidate", "-q", *files])]
    if stage == "regression":
        commands.extend((name, [sys.executable, script, *args]) for name, script, args in (
            ("variations", "assets/calc_variations.py", ["--json"]),
            ("prompt_data", "tools/validate_prompt_data.py", []),
            ("variation_scope", "tools/check_variation_scope.py", []),
            ("action_pools", "tools/build_action_pools.py", ["--check"]),
            ("compatibility", "tools/build_compatibility_review.py", ["--check"]),
            ("full_flow", "tools/verify_full_flow.py", []),
        ))
        commands.append(("asset_validation", [sys.executable, "-c",
            "from asset_validator import validate_assets; issues=validate_assets(); print(issues); raise SystemExit(bool(issues))"]))
    return commands


def run_command(name, command, root, output, env):
    log = output / "logs" / f"{name}.log"
    started = time.perf_counter()
    error = None
    with log.open("x", encoding="utf-8") as handle:
        try:
            result = subprocess.run(command, cwd=root, env=env, shell=False,
                                    stdout=handle, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace")
            code = result.returncode
        except OSError as exc:
            code = 2
            error = str(exc)
            handle.write(error + "\n")
    log_bytes = log.read_bytes()
    dependency_error = b"ModuleNotFoundError:" in log_bytes or b"ImportError:" in log_bytes
    status = "PASS" if code == 0 else "FAIL"
    if error or dependency_error or code not in (0, 1):
        status = "ERROR"
    check = {"name": name, "exit_code": code, "status": status}
    record = {**check, "command": command, "cwd": str(root),
              "elapsed_seconds": time.perf_counter() - started,
              "log_path": str(log), "log_sha256": hashlib.sha256(log_bytes).hexdigest(),
              "execution_error": error}
    return check, record


def verify(stage, output, *, root=ROOT, baseline_root=None, review_receipt=None, intake_root=None, v150_baseline_root=None):
    """Create a new receipt directory and run the requested existing checks."""
    root, output = Path(root).resolve(), Path(output).resolve()
    if stage == "intake":
        from tools.realizer_candidate_intake import verify_intake
        return verify_intake(output, root=root, baseline_root=baseline_root, review_receipt=review_receipt)
    if stage == "adoption-preflight":
        from tools.realizer_candidate_intake import adoption_preflight
        return adoption_preflight(output, root=root, intake_root=intake_root, v150_baseline_root=v150_baseline_root)
    try:
        files = test_files(root, stage)
        commands = commands_for(stage, files)
        for name, command in commands:
            if command[1] not in ("-m", "-c") and not (root / command[1]).is_file():
                raise ValueError(f"Missing command input: {command[1]}")
        output.mkdir(parents=True, exist_ok=False)
    except (OSError, ValueError) as exc:
        print(f"Verification input error: {exc}", file=sys.stderr)
        return 2

    (output / "logs").mkdir()
    checks, records, errors = [], [], []
    before = after = None
    supplemental_before = supplemental_after = None
    collection_hash = None
    test_counts = None
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    env["PYTHONUTF8"] = "1"
    raw_collection = output / "logs" / "collected-tests.json"
    env[COLLECTION_ENV] = str(raw_collection)
    env[OUTCOMES_ENV] = str(output / "test-outcomes.json")
    try:
        from tools.prompt_quality_loop import build_source_manifest

        before = build_source_manifest(root)
        supplemental_before = supplemental_inputs(root)
        write_json(output / "source-manifest.json", before)
        for name, command in commands:
            check, record = run_command(name, command, root, output, env)
            checks.append(check)
            records.append(record)
        try:
            nodeids = json.loads(raw_collection.read_text(encoding="utf-8"))["nodeids"]
            if (not isinstance(nodeids, list) or not nodeids
                    or any(not isinstance(nodeid, str) or nodeid.split("::", 1)[0] not in files for nodeid in nodeids)
                    or len(set(nodeids)) != len(nodeids)):
                raise ValueError("Collected test IDs are empty, duplicated or outside the selected files")
            nodeids = sorted(nodeids)
            collection_hash = hashlib.sha256(canonical_bytes(nodeids)).hexdigest()
            write_json(output / "test-collection.json", {
                "schema_version": "r43-test-collection/v1", "stage": stage,
                "test_files": files, "nodeids": nodeids, "count": len(nodeids), "sha256": collection_hash,
            })
            outcomes = json.loads((output / "test-outcomes.json").read_text(encoding="utf-8"))
            test_counts = validate_outcomes(outcomes, nodeids)
            if checks[0]["exit_code"] == 0 and outcomes["exit_code"] != 0:
                raise ValueError("Test exit status contradicts command result")
            if any(test_counts[field] for field in test_counts if field not in {"tests", "passed", "subtests"}):
                checks.append({"name": "test_outcomes", "exit_code": 1, "status": "FAIL"})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append("test_collection_unavailable")
            print(f"Collection evidence error: {exc}", file=sys.stderr)
    except (OSError, ValueError, ImportError) as exc:
        errors.append("verification_execution_error")
        print(f"Verification execution error: {exc}", file=sys.stderr)
    finally:
        if before is not None:
            try:
                after = build_source_manifest(root)
                supplemental_after = supplemental_inputs(root)
                write_json(output / "source-manifest-after.json", after)
            except (OSError, ValueError) as exc:
                errors.append("source_manifest_unavailable")
                print(f"Source evidence error: {exc}", file=sys.stderr)

    status = "PASS"
    if any(check["status"] == "FAIL" for check in checks):
        status = "FAIL"
    if errors or any(check["status"] == "ERROR" for check in checks):
        status = "ERROR"
    if ((before is not None and after is not None and before != after)
            or (supplemental_before is not None and supplemental_after is not None
                and supplemental_before != supplemental_after)):
        status = "INVALID"
    code = 0 if status == "PASS" else 1 if status == "FAIL" else 2
    write_json(output / "verdict.json", {
        "schema_version": "r43-development-verification/v1", "stage": stage,
        "status": status, "exit_code": code, "checks": checks, "errors": errors,
        "source_before": before["source_tree_hash"] if before else None,
        "source_after": after["source_tree_hash"] if after else None,
        "supplemental_before": hashlib.sha256(canonical_bytes(supplemental_before)).hexdigest() if supplemental_before is not None else None,
        "supplemental_after": hashlib.sha256(canonical_bytes(supplemental_after)).hexdigest() if supplemental_after is not None else None,
        "test_collection_sha256": collection_hash, "adoption_status": "NOT_EVALUATED",
        "test_counts": test_counts,
    })
    write_json(output / "supplemental-inputs.json", {"before": supplemental_before, "after": supplemental_after})
    write_json(output / "commands.json", records)
    write_json(output / "environment.json", {
        "python": sys.version, "executable": sys.executable,
        "platform": sys.platform, "os_name": os.name, "cwd": str(root), "output_dir": str(output),
    })
    print(f"{stage}: {status}; evidence: {output}")
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path)
    parser.add_argument("--review-receipt", type=Path)
    parser.add_argument("--intake-root", type=Path)
    parser.add_argument("--v150-baseline-root", type=Path)
    args = parser.parse_args(argv)
    try:
        return verify(args.stage, args.output_dir, baseline_root=args.baseline_root,
                      review_receipt=args.review_receipt, intake_root=args.intake_root,
                      v150_baseline_root=args.v150_baseline_root)
    except OSError as exc:
        print(f"Verification evidence error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
