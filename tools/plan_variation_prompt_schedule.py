from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.source_pipeline import _pick_preferred_prompt_payload, _source_payload_score
from nodes_context import ContextSource
from tools.analyze_variation_candidates import load_candidate_catalog
from tools.prompt_quality_loop import build_cohort
from tools.workflow_prompt_runner import (
    WorkflowValidationError,
    canonical_json_bytes,
    derive_randomized_seed,
)
from workflow_widget_validation import collect_input_specs, load_workflow


SCHEDULE_SCHEMA_VERSION = "variation-prompt-coverage-schedule/v1"
SELECTOR_CONTRACT = {
    "node_id": 1,
    "node_type": "ContextSource",
    "seed_input": "seed",
    "seed_control": "randomize",
    "source_mode": "auto",
    "selection": "actual_preferred_pool/v1",
}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _hash_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl_hash(rows: Sequence[Mapping[str, Any]]) -> str:
    content = b"".join(canonical_json_bytes(dict(row)) for row in rows)
    return hashlib.sha256(content).hexdigest()


def _contract_path(source_root: Path, value: Any) -> Path:
    path = (source_root / str(value)).resolve()
    try:
        path.relative_to(source_root.resolve())
    except ValueError:
        raise WorkflowValidationError("coverage_contract_path_escape", "coverage contract path escapes the repository") from None
    return path


def validate_coverage_contract(contract: Mapping[str, Any], *, source_root: Path = ROOT) -> dict[str, Any]:
    if contract.get("schema_version") != "variation-prompt-coverage-contract/v1":
        raise WorkflowValidationError("invalid_coverage_contract", "coverage contract schema is unsupported")
    contract_hash = contract.get("contract_sha256")
    contract_body = {key: value for key, value in contract.items() if key != "contract_sha256"}
    if _hash_value(contract_body) != contract_hash:
        raise WorkflowValidationError("coverage_contract_hash_mismatch", "coverage contract hash drifted")
    if contract.get("coverage_is_quality_evidence") is not False or contract.get("fixed_verdict") != "reject" or contract.get("promotion_ready") is not False:
        raise WorkflowValidationError("coverage_contract_widens_authority", "coverage contract cannot change quality verdict authority")
    experiment_path = _contract_path(source_root, contract.get("parent_experiment_path"))
    comparison_path = _contract_path(source_root, contract.get("parent_comparison_path"))
    receipt_path = _contract_path(source_root, contract.get("parent_rejection_receipt_path"))
    experiment = _read_json(experiment_path)
    comparison = _read_json(comparison_path)
    receipt = _read_json(receipt_path)
    if _hash_value(experiment) != contract.get("parent_experiment_sha256"):
        raise WorkflowValidationError("coverage_contract_parent_drift", "parent experiment drifted")
    comparison_body = {key: value for key, value in comparison.items() if key != "comparison_sha256"}
    if _hash_value(comparison_body) != contract.get("parent_comparison_sha256"):
        raise WorkflowValidationError("coverage_contract_parent_drift", "parent comparison drifted")
    if _hash_path(receipt_path) != contract.get("parent_rejection_receipt_sha256"):
        raise WorkflowValidationError("coverage_contract_parent_drift", "parent rejection receipt drifted")
    coverage = comparison.get("candidate_coverage", {})
    if (
        comparison.get("verdict") != "reject"
        or receipt.get("terminal_state") != "REJECTED"
        or contract.get("target_unseen_locations") != coverage.get("unseen_locations")
        or contract.get("target_unseen_action_pool_locations") != coverage.get("unseen_action_pool_locations")
        or contract.get("cohort") != experiment.get("cohort")
        or contract.get("run_contract") != experiment.get("run_contract")
    ):
        raise WorkflowValidationError("coverage_contract_parent_mismatch", "coverage contract does not reproduce parent evidence")
    return {"status": "pass", "contract_sha256": contract_hash}


def _compatible(subject: Mapping[str, Any], location: Mapping[str, Any]) -> bool:
    return bool(location.get("universal")) or bool(
        set(subject.get("tags", [])) & set(location.get("compatibility_tags", []))
    )


def assign_subjects_to_locations(catalog: Mapping[str, Any]) -> dict[str, str]:
    subjects = {str(item["id"]): item for item in catalog["subjects"]}
    locations = {str(item["id"]): item for item in catalog["locations"]}
    compatible = {
        subject_id: sorted(
            location_id
            for location_id, location in locations.items()
            if _compatible(subject, location)
        )
        for subject_id, subject in subjects.items()
    }
    if any(not values for values in compatible.values()):
        missing = sorted(key for key, values in compatible.items() if not values)
        raise WorkflowValidationError(
            "coverage_schedule_unmatched_subject",
            "candidate subject has no compatible candidate location",
            subjects=missing,
        )

    location_to_subject: dict[str, str] = {}

    def match(subject_id: str, visited: set[str]) -> bool:
        for location_id in compatible[subject_id]:
            if location_id in visited:
                continue
            visited.add(location_id)
            incumbent = location_to_subject.get(location_id)
            if incumbent is None or match(incumbent, visited):
                location_to_subject[location_id] = subject_id
                return True
        return False

    for subject_id in sorted(subjects):
        if not match(subject_id, set()):
            raise WorkflowValidationError(
                "coverage_schedule_matching_failed",
                "candidate subjects cannot be assigned to distinct candidate locations",
                subject=subject_id,
            )

    subject_load = Counter(location_to_subject.values())
    for location_id in sorted(locations):
        if location_id in location_to_subject:
            continue
        candidates = sorted(
            subject_id
            for subject_id, subject in subjects.items()
            if _compatible(subject, locations[location_id])
        )
        if not candidates:
            raise WorkflowValidationError(
                "coverage_schedule_unmatched_location",
                "candidate location has no compatible candidate subject",
                location=location_id,
            )
        chosen = min(candidates, key=lambda subject_id: (subject_load[subject_id], subject_id))
        location_to_subject[location_id] = chosen
        subject_load[chosen] += 1
    return dict(sorted(location_to_subject.items()))


def build_candidate_rows(catalog: Mapping[str, Any]) -> list[dict[str, Any]]:
    subjects = {str(item["id"]): item for item in catalog["subjects"]}
    locations = {str(item["id"]): item for item in catalog["locations"]}
    assignments = assign_subjects_to_locations(catalog)
    used_actions: set[str] = set()
    rows: list[dict[str, Any]] = []
    for location_id in sorted(locations):
        location = locations[location_id]
        subject = subjects[assignments[location_id]]
        actions = [
            str(item.get("text", ""))
            for item in location.get("action_plan", {}).get("direct_actions", [])
            if isinstance(item, Mapping) and str(item.get("text", ""))
        ]
        action = next((text for text in actions if text not in used_actions), None)
        if action is None:
            raise WorkflowValidationError(
                "coverage_schedule_action_collision",
                "candidate location has no unique direct action for its sentinel row",
                location=location_id,
            )
        used_actions.add(action)
        rows.append(
            {
                "subj": str(subject["id"]),
                "costume": str(subject["default_costume"]),
                "loc": location_id,
                "action": action,
                "meta": {
                    "mood": "quiet_focused",
                    "tags": {
                        "place_type": "public",
                        "purpose": "work",
                        "social_distance": "alone",
                        "progress": "midway",
                        "emotion_nuance": "absorbed",
                    },
                },
            }
        )
    return rows


def _validate_workflow_selector(workflow: Mapping[str, Any]) -> None:
    nodes = [node for node in workflow.get("nodes", []) if node.get("id") == SELECTOR_CONTRACT["node_id"]]
    if len(nodes) != 1 or nodes[0].get("type") != SELECTOR_CONTRACT["node_type"]:
        raise WorkflowValidationError("coverage_selector_drift", "ContextSource node contract drifted")
    widgets = nodes[0].get("widgets_values", [])
    if (
        len(widgets) < 4
        or str(widgets[0]).strip() not in {"", "{}"}
        or widgets[2] != SELECTOR_CONTRACT["seed_control"]
        or widgets[3] != SELECTOR_CONTRACT["source_mode"]
    ):
        raise WorkflowValidationError("coverage_selector_drift", "ContextSource widget contract drifted")
    input_names = [name for name, _type, _options in collect_input_specs(ContextSource)]
    if input_names != ["json_string", "seed", "source_mode"]:
        raise WorkflowValidationError("coverage_selector_drift", "ContextSource input schema drifted")


def _reachability(rows: list[dict[str, Any]], seeds: Sequence[int]) -> dict[str, list[int]]:
    daily_locations = {str(row["loc"]) for row in rows}
    result = {location: [] for location in sorted(daily_locations)}
    for run_seed in seeds:
        node_seed = derive_randomized_seed(int(run_seed), int(SELECTOR_CONTRACT["node_id"]), "seed")
        selected = _pick_preferred_prompt_payload(rows, node_seed, daily_locations)
        location = str(selected.get("loc", ""))
        if location in result:
            result[location].append(int(run_seed))
    return result


def build_prompt_schedule(
    *,
    candidate_iteration: Path,
    coverage_contract_path: Path,
    workflow_path: Path,
    source_root: Path = ROOT,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    catalog = load_candidate_catalog(candidate_iteration)
    coverage_contract = _read_json(coverage_contract_path)
    validate_coverage_contract(coverage_contract, source_root=source_root)
    contract_hash = coverage_contract.get("contract_sha256")
    workflow = load_workflow(workflow_path)
    _validate_workflow_selector(workflow)
    rows = build_candidate_rows(catalog)
    scores = [_source_payload_score(row, {str(item["loc"]) for item in rows}) for row in rows]
    if len(set(scores)) != 1:
        raise WorkflowValidationError(
            "coverage_schedule_score_drift",
            "candidate sentinel rows are not uniformly selectable",
            scores=scores,
        )
    cohort_contract = coverage_contract.get("cohort", {})
    controls = list(range(int(cohort_contract.get("control_count", 0))))
    cohort = build_cohort(
        int(cohort_contract.get("experiment_seed", 0)),
        str(cohort_contract.get("iteration_id", "")),
        controls,
        int(cohort_contract.get("samples", 0)),
    )
    if cohort.get("cohort_hash") != cohort_contract.get("cohort_hash"):
        raise WorkflowValidationError("coverage_schedule_cohort_drift", "fixed cohort no longer reproduces")
    control_reachability = _reachability(rows, cohort["control_seeds"])
    exploration_reachability = _reachability(rows, cohort["exploration_seeds"])
    unreachable = sorted(location for location, seeds in control_reachability.items() if not seeds)
    if unreachable:
        raise WorkflowValidationError(
            "coverage_schedule_control_unreachable",
            "control64 cannot reach every candidate sentinel row",
            locations=unreachable,
        )
    schedule = {
        "schema_version": SCHEDULE_SCHEMA_VERSION,
        "schedule_id": "v150-candidate-shape-iteration-005",
        "catalog_id": str(catalog["catalog_id"]),
        "candidate_iteration_path": candidate_iteration.resolve().relative_to(source_root).as_posix(),
        "candidate_iteration_sha256": _hash_path(candidate_iteration),
        "effective_catalog_sha256": _hash_value(catalog),
        "coverage_contract_path": coverage_contract_path.resolve().relative_to(source_root).as_posix(),
        "coverage_contract_sha256": contract_hash,
        "workflow_path": workflow_path.resolve().relative_to(source_root).as_posix(),
        "workflow_sha256": _hash_value(workflow),
        "source_selector_path": "pipeline/source_pipeline.py",
        "source_selector_sha256": _hash_path(source_root / "pipeline/source_pipeline.py"),
        "run_contract": coverage_contract["run_contract"],
        "cohort": cohort,
        "selector_contract": SELECTOR_CONTRACT,
        "row_score": scores[0],
        "candidate_rows": rows,
        "candidate_prompts_sha256": _hash_value(rows),
        "candidate_prompts_jsonl_sha256": _jsonl_hash(rows),
        "expected_subjects": sorted({str(row["subj"]) for row in rows}),
        "expected_locations": sorted({str(row["loc"]) for row in rows}),
        "expected_location_actions": [
            {"location": str(row["loc"]), "action": str(row["action"])} for row in rows
        ],
        "control_reachability": control_reachability,
        "exploration_reachability": exploration_reachability,
        "coverage_is_quality_evidence": False,
        "fixed_verdict": "reject",
        "promotion_ready": False,
    }
    schedule["schedule_sha256"] = _hash_value(schedule)
    return schedule


def validate_prompt_schedule(schedule: Mapping[str, Any], *, source_root: Path = ROOT) -> dict[str, Any]:
    schema_version = schedule.get("schema_version")
    if schema_version not in {SCHEDULE_SCHEMA_VERSION, "variation-prompt-final-coverage-schedule/v2"}:
        raise WorkflowValidationError("invalid_coverage_schedule", "coverage schedule schema is unsupported")
    stored_hash = schedule.get("schedule_sha256")
    body = {key: value for key, value in schedule.items() if key != "schedule_sha256"}
    if _hash_value(body) != stored_hash:
        raise WorkflowValidationError("coverage_schedule_hash_mismatch", "coverage schedule hash drifted")
    if schedule.get("coverage_is_quality_evidence") is not False or schedule.get("fixed_verdict") != "reject" or schedule.get("promotion_ready") is not False:
        raise WorkflowValidationError("coverage_schedule_widens_authority", "coverage schedule cannot change quality verdict authority")
    if schema_version == "variation-prompt-final-coverage-schedule/v2":
        from tools.plan_variation_final_coverage import validate_final_coverage_contract

        contract_path = source_root / str(schedule.get("full_coverage_contract_path", ""))
        contract = _read_json(contract_path)
        validate_final_coverage_contract(contract, repository_root=source_root)
        matrix_path = source_root / str(schedule.get("witness_matrix_path", ""))
        matrix = _read_json(matrix_path)
        matrix_body = {key: value for key, value in matrix.items() if key != "matrix_sha256"}
        rows = schedule.get("candidate_rows", [])
        expected_locations = schedule.get("expected_locations", [])
        expected_subjects = schedule.get("expected_subjects", [])
        if (
            schedule.get("full_coverage_contract_sha256") != contract.get("contract_sha256")
            or schedule.get("witness_matrix_path") != contract.get("witness_matrix_path")
            or _hash_value(matrix_body) != matrix.get("matrix_sha256")
            or schedule.get("witness_matrix_sha256") != matrix.get("matrix_sha256")
            or matrix.get("contract_sha256") != contract.get("contract_sha256")
            or schedule.get("run_contract") != contract.get("run_contract")
            or schedule.get("extra_seed_count") != 0
            or schedule.get("matching_cardinality") != len(expected_locations)
            or schedule.get("subject_coverage_count") != len(expected_subjects)
            or not isinstance(rows, list)
            or len(rows) != len(expected_locations)
            or sorted(str(row.get("loc", "")) for row in rows) != expected_locations
            or sorted({str(row.get("subj", "")) for row in rows}) != expected_subjects
            or _jsonl_hash(rows) != schedule.get("candidate_prompts_jsonl_sha256")
            or len(schedule.get("final_witnesses", [])) != len(expected_locations)
            or len(schedule.get("expected_location_actions", [])) != len(expected_locations)
        ):
            raise WorkflowValidationError(
                "final_coverage_schedule_mismatch",
                "final workflow coverage schedule fields drifted",
            )
        return {"status": "pass", "schedule_sha256": stored_hash}
    expected = build_prompt_schedule(
        candidate_iteration=source_root / str(schedule["candidate_iteration_path"]),
        coverage_contract_path=source_root / str(schedule["coverage_contract_path"]),
        workflow_path=source_root / str(schedule["workflow_path"]),
        source_root=source_root,
    )
    if canonical_json_bytes(expected) != canonical_json_bytes(dict(schedule)):
        raise WorkflowValidationError("coverage_schedule_recompute_mismatch", "coverage schedule does not match bound sources")
    return {"status": "pass", "schedule_sha256": stored_hash}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan a fixed-cohort candidate prompt coverage schedule.")
    parser.add_argument("--candidate-iteration", required=True)
    parser.add_argument("--coverage-contract", required=True)
    parser.add_argument("--workflow", default="ComfyUI-workflow-context.json")
    args = parser.parse_args(argv)
    try:
        schedule = build_prompt_schedule(
            candidate_iteration=ROOT / args.candidate_iteration,
            coverage_contract_path=ROOT / args.coverage_contract,
            workflow_path=ROOT / args.workflow,
        )
    except (OSError, ValueError, json.JSONDecodeError, WorkflowValidationError) as exc:
        envelope = exc.to_envelope() if isinstance(exc, WorkflowValidationError) else WorkflowValidationError(
            "coverage_schedule_failed",
            "coverage schedule planning failed",
            exception_type=type(exc).__name__,
        ).to_envelope()
        sys.stderr.buffer.write(canonical_json_bytes(envelope))
        return 2
    sys.stdout.buffer.write(canonical_json_bytes(schedule))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
