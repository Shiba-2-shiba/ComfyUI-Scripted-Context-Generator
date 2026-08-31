"""Build a path-bound prompt-quality verification v2 manifest.

The builder does not run verification commands.  It consumes their immutable
result/evidence pairs, verifies every binding, and writes a manifest only when
the exact adoption-gate inventory belongs to one candidate source tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes
from tools.prompt_quality_loop import build_source_manifest


REQUIRED_GATES = frozenset({
    "action_pools",
    "blind_review",
    "browser",
    "compatibility_review",
    "data_validation",
    "frontend",
    "full_flow",
    "prompt_quality_confirmation",
    "python_tests",
    "target_comparison",
    "widgets",
})
CONFIRMATION_OBJECTIVES = frozenset({"g004", "g005", "g006"})
MIN_FULL_REGRESSION_TESTS = 505
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _fail(code: str, message: str, **details: Any) -> None:
    raise WorkflowValidationError(code, message, **details)


def _load_object(path: Path, *, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(code, "could not read a JSON object", path=str(path), exception_type=type(exc).__name__)
    if not isinstance(value, dict):
        _fail(code, "artifact must be a JSON object", path=str(path))
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None


def _repo_path(path: Path, *, code: str, must_exist: bool = True) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        _fail(code, "artifact path must remain inside the repository", path=str(path))
    if must_exist and not resolved.is_file():
        _fail(code, "artifact file is missing", path=str(path))
    return resolved


def _bound_repo_path(value: Any, *, code: str, gate_name: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        _fail(code, "bound artifact path must be a non-empty repository-relative path", gate_name=gate_name)
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        _fail(code, "bound artifact path must be repository-relative", gate_name=gate_name, path=value)
    return _repo_path(ROOT / relative, code=code)


def _number(summary: Mapping[str, Any], name: str) -> int | None:
    value = summary.get(name)
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _validate_summary(gate_name: str, summary: Mapping[str, Any]) -> None:
    invalid = False
    if gate_name == "python_tests":
        tests_run = _number(summary, "tests_run")
        invalid = (
            tests_run is None
            or _number(summary, "tests_passed") != tests_run
            or tests_run < MIN_FULL_REGRESSION_TESTS
            or any(_number(summary, field) != 0 for field in ("failures", "errors", "skipped"))
        )
    elif gate_name == "data_validation":
        invalid = _number(summary, "errors") != 0 or _number(summary, "warnings") != 0
    elif gate_name == "frontend":
        invalid = (_number(summary, "tests_passed") or 0) < 4 or _number(summary, "failures") != 0
    elif gate_name == "browser":
        invalid = (_number(summary, "tests_passed") or 0) < 2 or _number(summary, "failures") != 0
    elif gate_name == "prompt_quality_confirmation":
        invalid = _number(summary, "objectives_passed") != 3 or _number(summary, "hard_gate_failures") != 0
    elif gate_name == "full_flow":
        invalid = _number(summary, "checks_passed") is None or _number(summary, "failures") != 0
    elif gate_name == "widgets":
        invalid = _number(summary, "issues") != 0
    elif gate_name == "compatibility_review":
        invalid = any(_number(summary, field) != 0 for field in ("errors", "missing_rows", "extra_rows"))
    elif gate_name == "action_pools":
        invalid = _number(summary, "errors") != 0 or _number(summary, "missing_pools") != 0
    if invalid:
        _fail("invalid_gate_summary", "gate result summary does not pass its contract", gate_name=gate_name)


def _validate_confirmation(result: Mapping[str, Any], source_tree_hash: str) -> None:
    details = result.get("details")
    objectives = details.get("objectives") if isinstance(details, Mapping) else None
    if not isinstance(objectives, Mapping) or set(objectives) != CONFIRMATION_OBJECTIVES:
        _fail(
            "invalid_confirmation_inventory",
            "confirmation result must bind exactly g004, g005, and g006",
        )
    cohort_hashes: set[str] = set()
    for objective in sorted(CONFIRMATION_OBJECTIVES):
        binding = objectives[objective]
        required = {"artifact_hash", "artifact_path", "cohort_hash", "source_tree_hash", "verdict"}
        if not isinstance(binding, Mapping) or set(binding) != required:
            _fail("invalid_confirmation_binding", "confirmation binding fields are invalid", objective=objective)
        artifact_path = _bound_repo_path(
            binding.get("artifact_path"), code="invalid_confirmation_path", gate_name=objective
        )
        if binding.get("artifact_hash") != _sha256(artifact_path):
            _fail("confirmation_hash_mismatch", "confirmation artifact hash does not match", objective=objective)
        confirmation = _load_object(artifact_path, code="invalid_confirmation_artifact")
        comparison = confirmation.get("comparison")
        expected = {
            "cohort_hash": confirmation.get("cohort_hash"),
            "source_tree_hash": confirmation.get("source_tree_hash"),
            "verdict": comparison.get("verdict") if isinstance(comparison, Mapping) else None,
        }
        if (
            confirmation.get("schema_version") != "prompt-quality-confirmation/v1"
            or confirmation.get("objective") != objective
            or confirmation.get("record_count") != 256
            or expected["source_tree_hash"] != source_tree_hash
            or expected["verdict"] != "pass"
            or any(binding.get(field) != value for field, value in expected.items())
        ):
            _fail(
                "stale_confirmation_artifact",
                "confirmation is not a passing current-source artifact",
                objective=objective,
            )
        cohort_hash = expected["cohort_hash"]
        if not _is_sha256(cohort_hash):
            _fail("invalid_confirmation_cohort", "confirmation cohort hash is invalid", objective=objective)
        cohort_hashes.add(cohort_hash)
    if len(cohort_hashes) != 1:
        _fail("mixed_confirmation_cohort", "all confirmation objectives must use the same cohort")


def _validate_gate_result(gate_name: str, result: Mapping[str, Any], source_tree_hash: str) -> None:
    if (
        result.get("schema_version") != "prompt-quality-gate-result/v1"
        or result.get("gate_name") != gate_name
        or result.get("source_tree_hash") != source_tree_hash
        or result.get("status") != "pass"
        or result.get("exit_code") != 0
        or not isinstance(result.get("summary"), Mapping)
    ):
        _fail("invalid_gate_result", "gate result is not a passing current-source result", gate_name=gate_name)
    _validate_summary(gate_name, result["summary"])
    if gate_name == "prompt_quality_confirmation":
        _validate_confirmation(result, source_tree_hash)


def _collect_evidence_files(evidence_dir: Path) -> dict[str, Path]:
    evidence_files: dict[str, Path] = {}
    for path in sorted(evidence_dir.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, Mapping) and value.get("schema_version") == "prompt-quality-verification-evidence/v1":
            gate_name = value.get("gate_name")
            if not isinstance(gate_name, str) or gate_name in evidence_files:
                _fail("duplicate_verification_gate", "verification evidence gate is invalid or duplicated", path=str(path))
            evidence_files[gate_name] = path.resolve()
    if set(evidence_files) != REQUIRED_GATES:
        _fail(
            "verification_gate_inventory_invalid",
            "verification requires the exact eleven-gate inventory",
            missing=sorted(REQUIRED_GATES - set(evidence_files)),
            unexpected=sorted(set(evidence_files) - REQUIRED_GATES),
        )
    return evidence_files


def _validate_review_binding(
    review: Mapping[str, Any], comparison: Mapping[str, Any], comparison_path: Path, source_tree_hash: str
) -> None:
    review_selection = comparison.get("review_selection")
    requires_v3 = isinstance(review_selection, Mapping)
    expected_schema = "prompt-quality-review/v3" if requires_v3 else "prompt-quality-review/v1"
    if review.get("schema_version") != expected_schema:
        _fail(
            "invalid_review_artifact",
            "review schema does not match the comparison review contract",
            expected_schema=expected_schema,
        )
    review_provenance = review.get("reviewed_run_provenance")
    reviewed_after = review_provenance.get("after") if isinstance(review_provenance, Mapping) else None
    if (
        review.get("status") != "pass"
        or review.get("verdict") != "pass"
        or not isinstance(reviewed_after, Mapping)
        or reviewed_after.get("source_tree_hash") != source_tree_hash
    ):
        _fail("invalid_review_artifact", "review is not a passing current-source result")
    if not requires_v3:
        return

    # Review v3 freezes the exact on-disk comparison artifact, not merely its
    # parsed JSON value.  This matches build_blind_prompt_review/promote_check.
    comparison_hash = _sha256(comparison_path)
    expected_provenance = {
        side: {
            "cohort_hash": comparison.get("cohort_hashes", {}).get(side),
            "source_tree_hash": comparison.get("source_tree_hashes", {}).get(side),
        }
        for side in ("before", "after")
    }
    if (
        review.get("comparison_artifact_hash") != comparison_hash
        or review.get("selection_hash") != review_selection.get("selection_hash")
        or review.get("review_contract_hash") != comparison.get("review_contract_hash")
        or review.get("qualitative_scope_hash") != comparison.get("qualitative_scope_hash")
        or review.get("experiment_id") != comparison.get("experiment_id")
        or review.get("reviewed_record_hashes") != comparison.get("record_artifact_hashes")
        or review_provenance != expected_provenance
    ):
        _fail(
            "invalid_review_v3_binding",
            "v3 review does not match the comparison selection and provenance",
        )


def build_verification(
    *, comparison_path: Path, review_path: Path, evidence_dir: Path, output_path: Path
) -> dict[str, Any]:
    """Validate all gate bindings and atomically write a verification v2 manifest."""

    comparison_path = _repo_path(comparison_path, code="invalid_comparison_path")
    review_path = _repo_path(review_path, code="invalid_review_path")
    evidence_dir = evidence_dir.resolve()
    try:
        evidence_dir.relative_to(ROOT.resolve())
    except ValueError:
        _fail("invalid_evidence_directory", "evidence directory must remain inside the repository")
    if not evidence_dir.is_dir():
        _fail("invalid_evidence_directory", "evidence directory is missing", path=str(evidence_dir))
    output_path = _repo_path(output_path, code="invalid_output_path", must_exist=False)

    comparison = _load_object(comparison_path, code="invalid_comparison_artifact")
    source_hashes = comparison.get("source_tree_hashes")
    source_tree_hash = source_hashes.get("after") if isinstance(source_hashes, Mapping) else None
    if (
        comparison.get("schema_version") != "prompt-quality-comparison/v1"
        or comparison.get("automatic_verdict") != "pass"
        or not _is_sha256(source_tree_hash)
    ):
        _fail("invalid_comparison_artifact", "comparison is not a passing candidate result")
    if build_source_manifest().get("source_tree_hash") != source_tree_hash:
        _fail(
            "stale_comparison_source",
            "comparison candidate does not match the current repository source tree",
        )
    review = _load_object(review_path, code="invalid_review_artifact")
    _validate_review_binding(review, comparison, comparison_path, source_tree_hash)

    expected_results = {
        "target_comparison": comparison_path,
        "blind_review": review_path,
    }
    gates: dict[str, Any] = {}
    for gate_name, evidence_path in sorted(_collect_evidence_files(evidence_dir).items()):
        evidence = _load_object(evidence_path, code="invalid_verification_evidence")
        if (
            evidence.get("gate_name") != gate_name
            or evidence.get("source_tree_hash") != source_tree_hash
            or evidence.get("status") != "pass"
            or evidence.get("exit_code") != 0
            or not isinstance(evidence.get("command"), str)
            or not evidence["command"].strip()
        ):
            _fail(
                "invalid_verification_evidence",
                "evidence is not a passing current-source command record",
                gate_name=gate_name,
            )
        result_path = _bound_repo_path(
            evidence.get("result_path"), code="invalid_result_path", gate_name=gate_name
        )
        if evidence.get("result_hash") != _sha256(result_path):
            _fail("verification_result_hash_mismatch", "result hash does not match", gate_name=gate_name)
        expected_path = expected_results.get(gate_name)
        if expected_path is not None:
            if result_path != expected_path:
                _fail("verification_artifact_binding_mismatch", "comparison/review binding is incorrect", gate_name=gate_name)
        else:
            _validate_gate_result(
                gate_name,
                _load_object(result_path, code="invalid_gate_result"),
                source_tree_hash,
            )
        gates[gate_name] = {
            "evidence_hash": _sha256(evidence_path),
            "evidence_path": evidence_path.relative_to(ROOT.resolve()).as_posix(),
            "status": "pass",
        }

    if build_source_manifest().get("source_tree_hash") != source_tree_hash:
        _fail(
            "source_tree_changed_during_build",
            "repository source changed while verification evidence was being validated",
        )

    manifest = {
        "artifacts": {
            "comparison_hash": hashlib.sha256(canonical_json_bytes(comparison)).hexdigest(),
            "source_tree_hash": source_tree_hash,
        },
        "quality_gates": gates,
        "schema_version": "prompt-quality-verification/v2",
        "status": "pass",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.tmp")
    temporary.write_bytes(canonical_json_bytes(manifest))
    temporary.replace(output_path)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        manifest = build_verification(
            comparison_path=args.comparison,
            review_path=args.review,
            evidence_dir=args.evidence_dir,
            output_path=args.output,
        )
    except WorkflowValidationError as exc:
        print(json.dumps(exc.to_envelope(), ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2
    print(canonical_json_bytes(manifest).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
