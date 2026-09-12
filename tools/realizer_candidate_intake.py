"""Thin orchestration of existing R43 tools and explicit development receipts."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

from tools.prompt_quality_loop import build_source_manifest
from tools.verify_realizer_v2_candidate import canonical_bytes, run_command, supplemental_inputs, write_json

REVIEW_PATH = "docs/diversity_refactor/r43_development_review.json"
_CONTRACT = "docs/diversity_refactor/r43_metric_contract.json"
_PROGRESS = "docs/diversity_refactor/progress.md"
_INTAKE_ARTIFACTS = (
    "source-manifest.json", "source-manifest-after.json", "baseline-source.json", "baseline-source-after.json",
    "protected-inputs.json", "review-input.json", "prose-review.json", "preservation.json",
    "focused/verdict.json", "focused/test-collection.json", "focused/test-outcomes.json",
    "regression/verdict.json", "regression/test-collection.json", "regression/test-outcomes.json",
    "reachability/records.jsonl", "reachability/normal-pairs.jsonl", "reachability/rows.jsonl",
    "baseline/baseline-pairs.jsonl", "baseline/baseline-identity.json",
    "replay-root/summary.json", "replay-root/evidence.jsonl", "replay-root/family-rows.jsonl",
    "replay-package/summary.json", "replay-package/evidence.jsonl", "replay-package/family-rows.jsonl",
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def source_guard(root, *, require_contract=True):
    root = Path(root)
    manifest = build_source_manifest(root)
    text = (root / _PROGRESS).read_text(encoding="utf-8")
    heading = "## 7. Locked Target / Guard Metrics"
    lock = heading + text.split(heading, 1)[1].split("\n---", 1)[0]
    lock_hash = hashlib.sha256(lock.encode()).hexdigest()
    if require_contract or (root / _CONTRACT).is_file():
        require(lock_hash == read_json(root / _CONTRACT)["a16_lock_sha256"], "A1.6 lock mismatch")
    return {"manifest": manifest, "supplemental": supplemental_inputs(root), "a16_lock": lock_hash}


def protected_inputs(root):
    paths = [root / name for name in (
        "assets/compatibility_review.csv", "core/schema.py", "nodes_context.py", "nodes_prompt_cleaner.py",
        "__init__.py", "ComfyUI-workflow-context.json", "prompts.jsonl", "mood_map.json", "templates.txt")]
    for directory in ("vocab/data", "vocab/source"):
        paths.extend((root / directory).rglob("*.json"))
    return {path.relative_to(root).as_posix(): file_hash(path) for path in sorted(set(paths))}


def copy_source(root, destination, manifest):
    destination.mkdir()
    names = {entry["path"] for entry in manifest["entries"]}
    names.update(name for name, value in supplemental_inputs(root).items() if value is not None)
    names.update((_PROGRESS, REVIEW_PATH))
    for name in sorted(names):
        source, target = root / name, destination / name
        require(source.is_file(), "Missing snapshot input: " + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    require(build_source_manifest(destination) == manifest, "Source copy differs")


def review_prose(receipt, replay, family_rows, audit, new_cases):
    """Match an explicit scoped review to actual current inputs and final prose."""
    require(receipt.get("schema_version") == "r43-development-prose-review/v1"
            and receipt.get("verdict") == "PASS", "Missing passing scoped prose review")
    require(receipt.get("runtime_source_identity") == replay["runtime_source_identity"], "Review runtime source is stale")
    require(receipt.get("workflow_hash") == audit["identity"]["workflow_hash"]
            and receipt.get("config_hash") == audit["identity"]["runner_config_hash"], "Review cohort/config differs")
    actual = {(row["run_seed"], item["proof"]["family"]): item for row in family_rows for item in row["families"]}
    reviewed = set()
    for case in receipt.get("cases", []):
        key = (case["run_seed"], case["family"])
        require(type(case["run_seed"]) is int and key not in reviewed and key in actual, "Invalid or duplicate prose review case")
        observed = actual[key]
        require(observed["proof"]["eligible"] is True and observed["forced_realizer_version"] == "v2"
                and observed["forced_family"] == case["family"], "Reviewed constructor is not currently proved")
        require(observed["proof"]["input_binding_sha256"] == case["input_binding_sha256"], "Reviewed input binding changed")
        for field in ("raw", "cleaned"):
            require(hashlib.sha256(observed[field].encode()).hexdigest() == case[field + "_sha256"], "Reviewed prose changed")
        reviewed.add(key)
    require({case["family"] for case in receipt["cases"]} == set(replay["families"]), "Prose review lacks a family")
    require(all((case["run_seed"], case["family"]) in reviewed for case in new_cases), "New ordinary prose lacks review")
    for case in new_cases:
        observed = actual[(case["run_seed"], case["family"])]
        require(case.get("after_raw") == observed["raw"] and case.get("after_cleaned") == observed["cleaned"],
                "Actual ordinary prose differs from reviewed forced prose")
    return {"status": "PASS", "reviewed_cases": len(reviewed), "scope": receipt.get("review_kind")}


def decide_development(audit, preservation, replay, review, architecture_ok=True):
    families = replay["families"]
    forced = sum(value["common_forced_v2"] > 0 for value in families.values())
    ordinary = audit["actual"]["v2_applied_count"]
    executed = audit["actual"]["executed_v2_family_count"]
    blockers = []
    if preservation["status"] != "PASS":
        blockers.append("preservation_failed")
    if ordinary <= 9 or preservation["new_ordinary_v2_count"] <= 0:
        blockers.append("ordinary_application_not_increased")
    if len(families) != 6 or forced != 6:
        blockers.append("real_graph_family_missing")
    if replay["proof_constructor_mismatches"] or audit["actual"]["errors"]:
        blockers.append("proof_constructor_error")
    if review.get("status") != "PASS":
        blockers.append("prose_review_missing")
    return {
        "architecture_status": "PASS" if architecture_ok else "BLOCKED",
        "development_status": "PASS" if architecture_ok and not blockers else "BLOCKED",
        "adoption_status": "BLOCKED", "development_blockers": blockers,
        "ordinary_v2_count_512": ordinary, "ordinary_v2_family_count": executed,
        "forced_real_graph_family_count": forced,
        "observed_structure_count_including_fallback": audit["actual"]["observed_structure_count"],
        "development_guide": {"minimum_v2_count_512": 64, "minimum_ordinary_families": 5,
                              "met": ordinary >= 64 and executed >= 5},
        "formal": {name: "NOT_RUN" for name in ("reference8192", "gate2048", "fixed80", "release8192")},
        "full_suite": "NOT_RUN", "frontend_browser": "NOT_RUN", "typecheck": "NOT_CONFIGURED",
    }


def verify_intake(output, *, root, baseline_root=None, review_receipt=None):
    root, output = Path(root).resolve(), Path(output).resolve()
    review_path = Path(review_receipt).resolve() if review_receipt else root / REVIEW_PATH
    try:
        require(baseline_root is not None, "intake requires --baseline-root with the nine-case development source")
        baseline = Path(baseline_root).resolve()
        require(baseline != root and baseline.is_dir(), "A distinct baseline source root is required")
        before, baseline_before = source_guard(root), source_guard(baseline, require_contract=False)
        require(before["a16_lock"] == baseline_before["a16_lock"], "Baseline A1.6 lock differs")
        require(protected_inputs(root) == protected_inputs(baseline), "Protected/public/runner inputs differ")
        review_before = file_hash(review_path)
        for name in ("tools/audit_realizer_reachability.py", "tools/realizer_candidate_replay.py",
                     "tools/realizer_candidate_preservation.py"):
            require((root / name).is_file(), "Missing verifier input: " + name)
        output.mkdir(parents=True, exist_ok=False)
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        print(f"Intake input error: {error}", file=sys.stderr)
        return 2
    (output / "logs").mkdir()
    checks, commands, errors, error_details = [], [], [], []
    result = {"architecture_status": "BLOCKED", "development_status": "BLOCKED", "adoption_status": "BLOCKED"}
    status, exit_code = "ERROR", 2
    env = dict(os.environ)
    for key in ("PYTEST_ADDOPTS", "PYTHONPATH", "SCG_R43_TEST_COLLECTION", "SCG_R43_TEST_OUTCOMES"):
        env.pop(key, None)
    env["PYTHONUTF8"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    write_json(output / "source-manifest.json", before)
    write_json(output / "baseline-source.json", baseline_before)
    write_json(output / "protected-inputs.json", protected_inputs(root))
    write_json(output / "review-input.json", read_json(review_path))
    try:
        def execute(name, arguments, *, hashseed="0"):
            check, command = run_command(name, [sys.executable, "-B", *map(str, arguments)], root, output,
                                          {**env, "PYTHONHASHSEED": hashseed})
            checks.append(check)
            commands.append(command)
            if check["exit_code"]:
                return False
            require(source_guard(root) == before and source_guard(baseline, require_contract=False) == baseline_before
                    and file_hash(review_path) == review_before, "Source changed during intake")
            return True

        stages = [("focused", ["tools/verify_realizer_v2_candidate.py", "--stage", "focused", "--output-dir", output / "focused"]),
                  ("regression", ["tools/verify_realizer_v2_candidate.py", "--stage", "regression", "--output-dir", output / "regression"]),
                  ("reachability", ["tools/audit_realizer_reachability.py", "--profile", "intake", "--force-families", "all",
                                    "--output-dir", output / "reachability"]),
                  ("baseline", ["-c", "import pathlib,sys; from tools.audit_realizer_reachability import baseline_pairs; out=pathlib.Path(sys.argv[1]); out.mkdir(); baseline_pairs(pathlib.Path(sys.argv[2]),out,0,512)",
                                output / "baseline", baseline]),
                  ("preservation", ["tools/realizer_candidate_preservation.py", "--baseline-pairs", output / "baseline/baseline-pairs.jsonl",
                                    "--current-pairs", output / "reachability/normal-pairs.jsonl", "--output", output / "preservation.json"])]
        for name, arguments in stages:
            if not execute(name, arguments):
                break
        if len(checks) == len(stages) and all(check["exit_code"] == 0 for check in checks):
            for stage in ("focused", "regression"):
                child = read_json(output / stage / "verdict.json")
                require(child["status"] == "PASS" and child["source_before"] == child["source_after"] == before["manifest"]["source_tree_hash"],
                        "Child test receipt is stale or failed")
                require(child["test_counts"] is not None, "Missing test outcome accounting")
            sizes = read_json(output / "regression/logs/variations.log")["base"]
            require(all(sizes[key] == value for key, value in {
                "unique_subjects": 135, "unique_locations": 109, "row_count": 8227, "total_base_variations": 150184}.items()), "V150 counts changed")
            require(read_json(output / "baseline/baseline-identity.json")["source_tree_hash"] == baseline_before["manifest"]["source_tree_hash"],
                    "Baseline receipt source mismatch")
            copy_source(root, output / "replay-source", before["manifest"])
            for name, mode, order, seed, source in (
                ("replay-root", "root", "ascending", "0", root),
                ("replay-package", "package", "reverse", "123", output / "replay-source"),
            ):
                if not execute(name, ["tools/realizer_candidate_replay.py", "--source-root", source,
                    "--pairs", output / "reachability/normal-pairs.jsonl", "--output-dir", output / name,
                    "--import-mode", mode, "--order", order], hashseed=seed):
                    break
            if all(check["exit_code"] == 0 for check in checks):
                left, right = (read_json(output / name / "summary.json") for name in ("replay-root", "replay-package"))
                require(left == right and left["status"] == "PASS" and left["sample_count"] == 512
                        and left["source_tree_hash"] == before["manifest"]["source_tree_hash"], "Replay summaries differ")
                for name in ("evidence.jsonl", "family-rows.jsonl"):
                    require(file_hash(output / "replay-root" / name) == file_hash(output / "replay-package" / name), "Replay bytes differ")
                executions = [read_json(output / name / "execution.json") for name in ("replay-root", "replay-package")]
                require([item["pythonhashseed"] for item in executions] == ["0", "123"]
                        and all(item["ignore_environment"] == 0 for item in executions)
                        and executions[0]["hash_sentinel"] != executions[1]["hash_sentinel"]
                        and not executions[1]["source_root_on_sys_path"], "Requested interpreter isolation was not exercised")
                audit = read_json(output / "reachability/reachability.json")
                require(audit["status"] == "ok" and audit["cohort"]["sample_count"] == 512
                        and audit["identity"]["source_tree_hash"] == before["manifest"]["source_tree_hash"], "Invalid audit receipt")
                preservation = read_json(output / "preservation.json")
                rows = [json.loads(line) for line in (output / "replay-root/family-rows.jsonl").read_text(encoding="utf-8").splitlines()]
                review = review_prose(read_json(review_path), left, rows, audit, preservation["new_cases"])
                write_json(output / "prose-review.json", review)
                result = decide_development(audit, preservation, left, review)
                result["test_counts"] = {stage: read_json(output / stage / "verdict.json")["test_counts"] for stage in ("focused", "regression")}
                result["baseline_source_tree_hash"] = baseline_before["manifest"]["source_tree_hash"]
                result["preservation"] = preservation
                result["replay"] = left
                result["reachability"] = {key: audit[key] for key in ("actual", "families", "domains", "routes", "blockers", "blocker_pairs", "blocker_triples")}
                status, exit_code = ("PASS", 0) if result["development_status"] == "PASS" else ("FAIL", 1)
        if any(check["exit_code"] for check in checks):
            status = "ERROR" if any(check["status"] == "ERROR" for check in checks) else "FAIL"
            exit_code = 2 if status == "ERROR" else 1
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        errors.append("intake_evidence_invalid")
        error_details.append(str(error))
    try:
        after, baseline_after = source_guard(root), source_guard(baseline, require_contract=False)
        write_json(output / "source-manifest-after.json", after)
        write_json(output / "baseline-source-after.json", baseline_after)
        if after != before or baseline_after != baseline_before or file_hash(review_path) != review_before:
            status, exit_code = "INVALID", 2
            result.update(architecture_status="BLOCKED", development_status="BLOCKED")
            errors.append("source_changed")
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        status, exit_code = "INVALID", 2
        result.update(architecture_status="BLOCKED", development_status="BLOCKED")
        errors.append("source_guard_unavailable")
        error_details.append(str(error))
    inventory = {name: file_hash(output / name) for name in _INTAKE_ARTIFACTS if (output / name).is_file()}
    if status == "PASS" and len(inventory) != len(_INTAKE_ARTIFACTS):
        status, exit_code = "ERROR", 2
        result.update(architecture_status="BLOCKED", development_status="BLOCKED")
        errors.append("incomplete_evidence_inventory")
    result.update(schema_version="r43-intake/v1", stage="intake", status=status, exit_code=exit_code,
                  source_tree_hash=before["manifest"]["source_tree_hash"], a16_lock=before["a16_lock"],
                  checks=checks, errors=errors, prose_review_sha256=review_before, evidence=inventory)
    write_json(output / "verdict.json", result)
    write_json(output / "commands.json", commands)
    write_json(output / "environment.json", {"python": sys.version, "executable": sys.executable, "platform": sys.platform,
                                            "source_root": str(root), "baseline_root": str(baseline), "output_dir": str(output),
                                            "error_details": error_details})
    print(f"intake: {status}; architecture={result['architecture_status']}; development={result['development_status']}; adoption=BLOCKED")
    return exit_code


def adoption_preflight(output, *, root, intake_root=None, v150_baseline_root=None):
    root, output = Path(root).resolve(), Path(output).resolve()
    try:
        require(intake_root is not None, "adoption-preflight requires --intake-root")
        intake = read_json(Path(intake_root) / "verdict.json")
        guard = source_guard(root)
        require(intake["schema_version"] == "r43-intake/v1" and intake["status"] == "PASS"
                and intake["source_tree_hash"] == guard["manifest"]["source_tree_hash"]
                and intake["a16_lock"] == guard["a16_lock"], "Intake receipt is stale or not passing")
        require(read_json(Path(intake_root) / "source-manifest.json") == guard, "Intake supplemental inputs changed")
        require(set(intake.get("evidence", {})) == set(_INTAKE_ARTIFACTS), "Incomplete intake evidence inventory")
        for name, expected in intake["evidence"].items():
            path = (Path(intake_root) / name).resolve()
            require(path.is_relative_to(Path(intake_root).resolve()) and file_hash(path) == expected, "Intake evidence changed")
        output.mkdir(parents=True, exist_ok=False)
        blockers = ["formal_baseline_and_quality_receipts_require_R43_10_validation"]
        if not intake["development_guide"]["met"]:
            blockers.append("development_guide_not_met")
        original = None
        if v150_baseline_root is None:
            blockers.append("original_v150_source_missing")
        else:
            source = Path(v150_baseline_root).resolve()
            original = build_source_manifest(source)
            require(protected_inputs(source) == protected_inputs(root), "Original V150 protected inputs differ")
        require(source_guard(root) == guard, "Source changed during preflight")
        write_json(output / "verdict.json", {
            "schema_version": "r43-adoption-preflight/v1", "stage": "adoption-preflight", "status": "BLOCKED", "exit_code": 2,
            "source_tree_hash": guard["manifest"]["source_tree_hash"], "intake_sha256": file_hash(Path(intake_root) / "verdict.json"),
            "original_v150_source_tree_hash": original["source_tree_hash"] if original else None,
            "adoption_status": "BLOCKED", "blockers": blockers, "formal": intake["formal"],
        })
        print("adoption-preflight: BLOCKED; no formal evaluation executed")
        return 2
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        print(f"Preflight input error: {error}", file=sys.stderr)
        return 2
