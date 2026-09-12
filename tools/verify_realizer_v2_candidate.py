"""Run existing R43 development checks; exit 0=pass, 1=failure, 2=invalid/error.

Only focused and regression stages are implemented. This is also a pytest plugin
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
STAGES = ("focused", "regression")

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
        for name in ("assets/calc_variations.py", "assets/compatibility_review.csv", "mood_map.json", "prompts.jsonl", "pytest.ini", "templates.txt")
    }


def pytest_collection_finish(session):
    destination = os.environ.get(COLLECTION_ENV)
    if destination:
        write_json(Path(destination), {"nodeids": sorted(item.nodeid for item in session.items)})


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


def verify(stage, output, *, root=ROOT):
    """Create a new receipt directory and run the requested existing checks."""
    root, output = Path(root).resolve(), Path(output).resolve()
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
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    env["PYTHONUTF8"] = "1"
    raw_collection = output / "logs" / "collected-tests.json"
    env[COLLECTION_ENV] = str(raw_collection)
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
    args = parser.parse_args(argv)
    try:
        return verify(args.stage, args.output_dir)
    except OSError as exc:
        print(f"Verification evidence error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
