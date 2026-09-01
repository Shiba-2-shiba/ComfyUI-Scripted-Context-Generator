from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nodes_context import ContextCharacterProfile, ContextSceneVariator, ContextSource
from pipeline.source_pipeline import _pick_preferred_prompt_payload
from tools.analyze_variation_candidates import load_candidate_catalog
from tools import analyze_variation_candidates as candidate_analyzer
from tools.compare_variation_prompt_pair import (
    _declared_run_contract,
    final_scene_decision,
    scene_action_pool_witness,
)
from tools.plan_variation_prompt_schedule import (
    build_candidate_rows,
    validate_coverage_contract,
)
from tools.prompt_quality_loop import build_source_manifest
from tools.workflow_prompt_runner import (
    WorkflowValidationError,
    canonical_json_bytes,
    derive_randomized_seed,
    load_profile,
)
from workflow_widget_validation import collect_input_specs, load_workflow


CONTRACT_SCHEMA_VERSION = "variation-final-coverage-contract/v1"
SCHEDULE_SCHEMA_VERSION = "variation-prompt-final-coverage-schedule/v2"
ALGORITHM_VERSION = "fixed-cohort-row-slot-beam/v1"
PROBE_TRANSFORM = {
    "source_mode": "json_only",
    "forced_nodes": [1],
    "unchanged_nodes": [2, 3],
    "terminal_node": 3,
    "quality_metric_selection": False,
    "extra_seed_count": 0,
}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _hash_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl_hash(rows: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(
        b"".join(canonical_json_bytes(dict(row)) for row in rows)
    ).hexdigest()


def _action_index(action_pools: Mapping[str, Any], locations: Sequence[str]) -> dict[str, set[str]]:
    return {
        location: {
            str(item.get("text", "") if isinstance(item, Mapping) else item).strip()
            for item in action_pools.get(location, [])
            if str(item.get("text", "") if isinstance(item, Mapping) else item).strip()
        }
        for location in locations
    }


def selector_slot_groups(rows: Sequence[Mapping[str, Any]], seeds: Sequence[int]) -> list[list[int]]:
    if len(rows) != len({str(row.get("loc", "")) for row in rows}):
        raise WorkflowValidationError("duplicate_schedule_location", "selector rows must have unique locations")
    daily_locations = {str(row["loc"]) for row in rows}
    row_index = {str(row["loc"]): index for index, row in enumerate(rows)}
    groups = [[] for _ in rows]
    for run_seed in seeds:
        source_seed = derive_randomized_seed(int(run_seed), 1, "seed")
        selected = _pick_preferred_prompt_payload(list(rows), source_seed, daily_locations)
        groups[row_index[str(selected["loc"])]].append(int(run_seed))
    if any(not group for group in groups):
        raise WorkflowValidationError(
            "fixed_cohort_selector_slot_unreachable",
            "fixed cohort does not reach every selector slot",
            slots=[index for index, group in enumerate(groups) if not group],
        )
    return groups


def simulate_forced_scene(
    row: Mapping[str, Any],
    run_seed: int,
    *,
    source_node: ContextSource,
    character_node: ContextCharacterProfile,
    scene_node: ContextSceneVariator,
) -> dict[str, Any]:
    source_seed = derive_randomized_seed(int(run_seed), 1, "seed")
    character_seed = derive_randomized_seed(int(run_seed), 2, "seed")
    scene_seed = derive_randomized_seed(int(run_seed), 3, "seed")
    source_context = source_node.build_context(
        json.dumps(dict(row), ensure_ascii=False), source_seed, "json_only"
    )[0]
    character_context = character_node.apply_profile(
        "random", "Aiko (Quiet)", character_seed, source_context
    )[0]
    final_context = json.loads(
        scene_node.variate_context(scene_seed, "full", character_context)[0]
    )
    decision = final_scene_decision(final_context)
    if decision is None:
        return {
            "run_seed": int(run_seed),
            "final_location": str(final_context.get("loc", "")),
            "raw_pool_action": "",
            "rendered_action": "",
            "valid_scene_decision": False,
        }
    raw_action = scene_action_pool_witness(decision)
    rendered_action = str(
        decision.get("new_action")
        or decision.get("normalized_action")
        or raw_action
    ).strip()
    return {
        "run_seed": int(run_seed),
        "final_location": str(final_context.get("loc", "")),
        "raw_pool_action": raw_action,
        "rendered_action": rendered_action,
        "source_subject": str(final_context.get("extras", {}).get("source_subj_key", "")),
        "decision_sha256": _hash_value(decision),
        "final_context_sha256": _hash_value(final_context),
        "valid_scene_decision": True,
    }


def candidate_row_variants(catalog: Mapping[str, Any]) -> list[dict[str, Any]]:
    base_rows = {str(row["loc"]): row for row in build_candidate_rows(catalog)}
    subjects = {str(item["id"]): item for item in catalog["subjects"]}
    locations = {str(item["id"]): item for item in catalog["locations"]}
    variants: list[dict[str, Any]] = []
    for location_id in sorted(locations):
        location = locations[location_id]
        for subject_id in sorted(subjects):
            subject = subjects[subject_id]
            compatible = bool(location.get("universal")) or bool(
                set(subject.get("tags", [])) & set(location.get("compatibility_tags", []))
            )
            if not compatible:
                continue
            row = json.loads(json.dumps(base_rows[location_id], ensure_ascii=False))
            row["subj"] = subject_id
            row["costume"] = str(subject["default_costume"])
            variants.append(
                {
                    "variant_id": f"{location_id}:{subject_id}",
                    "source_location": location_id,
                    "subject": subject_id,
                    "row": row,
                }
            )
    return variants


def _load_bound_catalog(repository_root: Path, relative_path: str) -> dict[str, Any]:
    analyzer_root = candidate_analyzer.ROOT
    try:
        candidate_analyzer.ROOT = repository_root
        return load_candidate_catalog(repository_root / relative_path)
    finally:
        candidate_analyzer.ROOT = analyzer_root


def _validate_probe_workflow(candidate_root: Path, run_contract: Mapping[str, Any]) -> None:
    workflow = load_workflow(candidate_root / str(run_contract.get("workflow", "")))
    nodes = {int(node["id"]): node for node in workflow.get("nodes", []) if isinstance(node, Mapping) and "id" in node}
    expected_widgets = {
        1: ["{}", 0, "randomize", "auto"],
        2: ["random", "Aiko (Quiet)", 0, "randomize"],
        3: [0, "randomize", "full"],
    }
    expected_types = {1: "ContextSource", 2: "ContextCharacterProfile", 3: "ContextSceneVariator"}
    if any(
        node_id not in nodes
        or nodes[node_id].get("type") != expected_types[node_id]
        or nodes[node_id].get("widgets_values") != widgets
        for node_id, widgets in expected_widgets.items()
    ):
        raise WorkflowValidationError("final_coverage_probe_workflow_drift", "nodes 1-3 widget contract drifted")
    input_contracts = {
        1: [name for name, _type, _options in collect_input_specs(ContextSource)],
        2: [name for name, _type, _options in collect_input_specs(ContextCharacterProfile)],
        3: [name for name, _type, _options in collect_input_specs(ContextSceneVariator)],
    }
    if (
        input_contracts[1] != ["json_string", "seed", "source_mode"]
        or input_contracts[2][:3] != ["mode", "character_name", "seed"]
        or input_contracts[2][-1:] != ["context_json"]
        or input_contracts[3] != ["seed", "variation_mode", "context_json"]
    ):
        raise WorkflowValidationError("final_coverage_probe_workflow_drift", "nodes 1-3 input schema drifted")
    profile = load_profile(candidate_root / str(run_contract.get("profile", "")))
    explicit_nodes = {int(node_id) for node_id in run_contract.get("overrides", {})}
    if ({1, 2, 3} & set(profile.resolved_overrides())) or ({1, 2, 3} & explicit_nodes):
        raise WorkflowValidationError("final_coverage_probe_override_drift", "probe nodes cannot be overridden")
    experiment_contract = {
        "workflow": run_contract.get("workflow"),
        "profile": run_contract.get("profile"),
        "run_contract": run_contract,
    }
    if _declared_run_contract(candidate_root, experiment_contract) != {
        field: run_contract[field]
        for field in ("workflow_hash", "profile_hash", "override_hash", "effective_workflow_hash")
    }:
        raise WorkflowValidationError("final_coverage_run_contract_drift", "calibration run contract drifted")


@dataclass(frozen=True)
class AssignmentState:
    used_location_mask: int
    coverage_mask: int
    subject_mask: int
    choices: tuple[int, ...]


def solve_row_slot_assignment(
    *,
    slot_variant_masks: Sequence[Sequence[int]],
    variant_locations: Sequence[int],
    variant_subjects: Sequence[int],
    target_count: int,
    subject_count: int,
    beam_width: int = 5000,
) -> AssignmentState:
    if beam_width < 1:
        raise ValueError("beam_width must be positive")
    states = [AssignmentState(0, 0, 0, ())]
    for slot, masks in enumerate(slot_variant_masks):
        next_states: dict[tuple[int, int, int], AssignmentState] = {}
        for state in states:
            for variant_index, coverage_mask in enumerate(masks):
                location_bit = 1 << int(variant_locations[variant_index])
                if state.used_location_mask & location_bit:
                    continue
                candidate = AssignmentState(
                    state.used_location_mask | location_bit,
                    state.coverage_mask | int(coverage_mask),
                    state.subject_mask | (1 << int(variant_subjects[variant_index])),
                    state.choices + (variant_index,),
                )
                key = (
                    candidate.used_location_mask,
                    candidate.coverage_mask,
                    candidate.subject_mask,
                )
                incumbent = next_states.get(key)
                if incumbent is None or candidate.choices < incumbent.choices:
                    next_states[key] = candidate
        states = sorted(
            next_states.values(),
            key=lambda state: (
                -state.coverage_mask.bit_count(),
                -state.subject_mask.bit_count(),
                state.choices,
            ),
        )[:beam_width]
        if not states:
            raise WorkflowValidationError(
                "final_coverage_search_inconclusive",
                "bounded row-slot search exhausted",
                slot=slot,
            )
    best = states[0]
    if best.coverage_mask.bit_count() != target_count or best.subject_mask.bit_count() != subject_count:
        raise WorkflowValidationError(
            "final_coverage_search_inconclusive",
            "bounded search did not find full final location and subject coverage",
            covered_locations=best.coverage_mask.bit_count(),
            covered_subjects=best.subject_mask.bit_count(),
            target_locations=target_count,
            target_subjects=subject_count,
        )
    return best


def validate_final_coverage_contract(contract: Mapping[str, Any], *, repository_root: Path) -> dict[str, Any]:
    if contract.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        raise WorkflowValidationError("invalid_final_coverage_contract", "final coverage contract schema is unsupported")
    body = {key: value for key, value in contract.items() if key != "contract_sha256"}
    if _hash_value(body) != contract.get("contract_sha256"):
        raise WorkflowValidationError("final_coverage_contract_hash_mismatch", "final coverage contract hash drifted")
    if (
        contract.get("coverage_is_quality_evidence") is not False
        or contract.get("fixed_quality_verdict") != "reject"
        or contract.get("promotion_ready") is not False
        or contract.get("extra_seed_count") != 0
    ):
        raise WorkflowValidationError("final_coverage_contract_widens_authority", "final coverage contract widens authority")
    parent_receipt = repository_root / str(contract.get("parent_rejection_receipt_path", ""))
    calibration_manifest = repository_root / str(contract.get("calibration_snapshot_manifest_path", ""))
    if _hash_path(parent_receipt) != contract.get("parent_rejection_receipt_sha256"):
        raise WorkflowValidationError("final_coverage_parent_drift", "parent rejection receipt drifted")
    if _hash_path(calibration_manifest) != contract.get("calibration_snapshot_manifest_sha256"):
        raise WorkflowValidationError("final_coverage_calibration_drift", "calibration snapshot manifest drifted")
    manifest = _read_json(calibration_manifest)
    calibration_root = calibration_manifest.parent
    candidate_root = calibration_root / "candidate-root"
    action_pools_path = candidate_root / "vocab/data/action_pools.json"
    catalog = _load_bound_catalog(
        repository_root, str(contract.get("candidate_iteration_path", ""))
    )
    if (
        manifest.get("state") != "SNAPSHOT_READY"
        or not manifest.get("prompt_generation_allowed")
        or manifest.get("candidate_source_tree_sha256")
        != contract.get("calibration_candidate_source_tree_sha256")
        or _hash_path(action_pools_path) != contract.get("calibration_action_pools_sha256")
        or contract.get("probe_transform") != PROBE_TRANSFORM
        or contract.get("probe_transform_sha256") != _hash_value(PROBE_TRANSFORM)
        or contract.get("algorithm_version") != ALGORITHM_VERSION
        or _hash_path(repository_root / str(contract.get("candidate_iteration_path", "")))
        != contract.get("candidate_iteration_sha256")
        or _hash_value(catalog) != contract.get("effective_catalog_sha256")
    ):
        raise WorkflowValidationError(
            "final_coverage_calibration_mismatch",
            "calibration snapshot, action pools, or probe contract drifted",
        )
    _validate_probe_workflow(candidate_root, contract.get("run_contract", {}))
    cohort = contract.get("cohort", {})
    seeds = list(cohort.get("control_seeds", [])) + list(cohort.get("exploration_seeds", []))
    if (
        len(cohort.get("control_seeds", [])) != 64
        or len(cohort.get("exploration_seeds", [])) != 16
        or len(seeds) != len(set(seeds))
    ):
        raise WorkflowValidationError("final_coverage_cohort_drift", "final coverage cohort is not exact 64+16")
    return {"status": "pass", "contract_sha256": contract["contract_sha256"]}


def build_final_coverage_schedule(
    *,
    contract_path: Path,
    repository_root: Path,
    beam_width: int = 5000,
    matrix_output: Path | None = None,
) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    contract = _read_json(contract_path)
    validate_final_coverage_contract(contract, repository_root=repository_root)
    if build_source_manifest(ROOT)["source_tree_hash"] != contract.get("calibration_candidate_source_tree_sha256"):
        raise WorkflowValidationError(
            "final_coverage_calibration_source_drift",
            "planner is not running inside the bound calibration candidate root",
        )
    catalog = _load_bound_catalog(repository_root, str(contract["candidate_iteration_path"]))
    variants = candidate_row_variants(catalog)
    locations = sorted(str(item["id"]) for item in catalog["locations"])
    subjects = sorted(str(item["id"]) for item in catalog["subjects"])
    location_index = {value: index for index, value in enumerate(locations)}
    subject_index = {value: index for index, value in enumerate(subjects)}
    base_rows = build_candidate_rows(catalog)
    cohort = contract["cohort"]
    fixed_seeds = [int(seed) for seed in cohort["control_seeds"] + cohort["exploration_seeds"]]
    groups = selector_slot_groups(base_rows, fixed_seeds)
    action_pools = _read_json(ROOT / "vocab/data/action_pools.json")
    action_index = _action_index(action_pools, locations)
    source_node = ContextSource()
    character_node = ContextCharacterProfile()
    scene_node = ContextSceneVariator()
    slot_variant_masks: list[list[int]] = []
    slot_variant_witnesses: list[list[dict[str, list[dict[str, Any]]]]] = []
    matrix_entries: list[dict[str, Any]] = []
    probe_count = 0
    valid_witness_count = 0
    for slot, seeds in enumerate(groups):
        slot_masks: list[int] = []
        slot_witnesses: list[dict[str, list[dict[str, Any]]]] = []
        for variant in variants:
            mask = 0
            witnesses: dict[str, list[dict[str, Any]]] = {}
            for run_seed in seeds:
                probe_count += 1
                outcome = simulate_forced_scene(
                    variant["row"],
                    run_seed,
                    source_node=source_node,
                    character_node=character_node,
                    scene_node=scene_node,
                )
                final_location = outcome["final_location"]
                raw_action = outcome["raw_pool_action"]
                if final_location not in location_index or raw_action not in action_index[final_location]:
                    continue
                mask |= 1 << location_index[final_location]
                witnesses.setdefault(final_location, []).append(outcome)
                valid_witness_count += 1
            slot_masks.append(mask)
            slot_witnesses.append(witnesses)
            if witnesses:
                matrix_entries.append(
                    {
                        "slot": slot,
                        "variant_id": variant["variant_id"],
                        "witnesses": [
                            {
                                "decision_sha256": item["decision_sha256"],
                                "final_location": final_location,
                                "final_context_sha256": item["final_context_sha256"],
                                "raw_pool_action": item["raw_pool_action"],
                                "rendered_action": item["rendered_action"],
                                "run_seed": item["run_seed"],
                            }
                            for final_location in sorted(witnesses)
                            for item in sorted(
                                witnesses[final_location], key=lambda value: value["run_seed"]
                            )
                        ],
                    }
                )
        slot_variant_masks.append(slot_masks)
        slot_variant_witnesses.append(slot_witnesses)
    best = solve_row_slot_assignment(
        slot_variant_masks=slot_variant_masks,
        variant_locations=[location_index[item["source_location"]] for item in variants],
        variant_subjects=[subject_index[item["subject"]] for item in variants],
        target_count=len(locations),
        subject_count=len(subjects),
        beam_width=beam_width,
    )
    rows = [variants[index]["row"] for index in best.choices]
    final_witnesses: dict[str, dict[str, Any]] = {}
    for slot, variant_index in enumerate(best.choices):
        for final_location, outcomes in slot_variant_witnesses[slot][variant_index].items():
            candidate = min(
                outcomes,
                key=lambda item: (
                    0 if item["run_seed"] in cohort["control_seeds"] else 1,
                    item["run_seed"],
                    item["raw_pool_action"],
                ),
            )
            incumbent = final_witnesses.get(final_location)
            if incumbent is None or (
                0 if candidate["run_seed"] in cohort["control_seeds"] else 1,
                candidate["run_seed"],
                candidate["raw_pool_action"],
            ) < (
                0 if incumbent["run_seed"] in cohort["control_seeds"] else 1,
                incumbent["run_seed"],
                incumbent["raw_pool_action"],
            ):
                final_witnesses[final_location] = {
                    **candidate,
                    "selector_slot": slot,
                    "source_location": variants[variant_index]["source_location"],
                    "source_subject": variants[variant_index]["subject"],
                    "row_sha256": _hash_value(variants[variant_index]["row"]),
                }
    if set(final_witnesses) != set(locations):
        raise WorkflowValidationError("fixed_cohort_final_coverage_unreachable", "chosen assignment lacks final witnesses")
    matrix_artifact = {
        "schema_version": "variation-final-coverage-witness-matrix/v1",
        "contract_sha256": contract["contract_sha256"],
        "calibration_candidate_source_tree_sha256": contract[
            "calibration_candidate_source_tree_sha256"
        ],
        "effective_catalog_sha256": _hash_value(catalog),
        "calibration_action_pools_sha256": contract["calibration_action_pools_sha256"],
        "run_contract": contract["run_contract"],
        "probe_transform_sha256": _hash_value(PROBE_TRANSFORM),
        "algorithm_version": ALGORITHM_VERSION,
        "probe_count": probe_count,
        "valid_witness_count": valid_witness_count,
        "edges": matrix_entries,
    }
    matrix_artifact["matrix_sha256"] = _hash_value(matrix_artifact)
    if matrix_output is not None:
        matrix_output.parent.mkdir(parents=True, exist_ok=True)
        matrix_output.write_bytes(canonical_json_bytes(matrix_artifact))
    schedule = {
        "schema_version": SCHEDULE_SCHEMA_VERSION,
        "schedule_id": "v150-candidate-shape-iteration-006",
        "full_coverage_contract_path": contract_path.resolve().relative_to(repository_root).as_posix(),
        "full_coverage_contract_sha256": contract["contract_sha256"],
        "effective_catalog_sha256": _hash_value(catalog),
        "algorithm_version": ALGORITHM_VERSION,
        "beam_width": beam_width,
        "probe_transform": PROBE_TRANSFORM,
        "probe_transform_sha256": _hash_value(PROBE_TRANSFORM),
        "witness_matrix_path": contract["witness_matrix_path"],
        "witness_matrix_sha256": matrix_artifact["matrix_sha256"],
        "probe_count": probe_count,
        "valid_witness_count": valid_witness_count,
        "cohort": cohort,
        "run_contract": contract["run_contract"],
        "candidate_rows": rows,
        "candidate_prompts_jsonl_sha256": _jsonl_hash(rows),
        "expected_subjects": subjects,
        "expected_locations": locations,
        "expected_location_actions": [
            {
                "location": location,
                "action": final_witnesses[location]["raw_pool_action"],
            }
            for location in locations
        ],
        "final_witnesses": [
            {"location": location, **final_witnesses[location]} for location in locations
        ],
        "matching_cardinality": best.coverage_mask.bit_count(),
        "subject_coverage_count": best.subject_mask.bit_count(),
        "extra_seed_count": 0,
        "coverage_is_quality_evidence": False,
        "fixed_verdict": "reject",
        "promotion_ready": False,
    }
    schedule["schedule_sha256"] = _hash_value(schedule)
    return schedule


def verify_materialized_final_schedule(
    *,
    schedule_path: Path,
    repository_root: Path,
) -> dict[str, Any]:
    from tools.plan_variation_prompt_schedule import validate_prompt_schedule

    schedule = _read_json(schedule_path)
    validate_prompt_schedule(schedule, source_root=repository_root.resolve())
    rows = [dict(row) for row in schedule["candidate_rows"]]
    prompts_path = ROOT / "prompts.jsonl"
    if _hash_path(prompts_path) != schedule.get("candidate_prompts_jsonl_sha256"):
        raise WorkflowValidationError(
            "final_coverage_prompt_hash_mismatch",
            "materialized prompts do not match final coverage schedule",
        )
    cohort = schedule["cohort"]
    fixed_seeds = [int(seed) for seed in cohort["control_seeds"] + cohort["exploration_seeds"]]
    groups = selector_slot_groups(rows, fixed_seeds)
    source_node = ContextSource()
    character_node = ContextCharacterProfile()
    scene_node = ContextSceneVariator()
    verified: list[dict[str, Any]] = []
    for witness in schedule["final_witnesses"]:
        slot = int(witness["selector_slot"])
        run_seed = int(witness["run_seed"])
        if slot < 0 or slot >= len(rows) or run_seed not in groups[slot]:
            raise WorkflowValidationError(
                "final_coverage_witness_slot_mismatch",
                "witness seed does not select its bound prompt slot",
                location=witness["location"],
            )
        outcome = simulate_forced_scene(
            rows[slot],
            run_seed,
            source_node=source_node,
            character_node=character_node,
            scene_node=scene_node,
        )
        expected = {
            "final_location": witness["location"],
            "raw_pool_action": witness["raw_pool_action"],
            "run_seed": run_seed,
        }
        actual = {key: outcome.get(key) for key in expected}
        if actual != expected:
            raise WorkflowValidationError(
                "final_coverage_witness_replay_mismatch",
                "materialized final coverage witness drifted",
                location=witness["location"],
            )
        verified.append(
            {
                **expected,
                "decision_sha256": outcome["decision_sha256"],
                "final_context_sha256": outcome["final_context_sha256"],
                "rendered_action": outcome["rendered_action"],
                "historical_decision_sha256_match": outcome["decision_sha256"]
                == witness["decision_sha256"],
                "historical_final_context_sha256_match": outcome["final_context_sha256"]
                == witness["final_context_sha256"],
            }
        )
    if (
        len(verified) != len(schedule["expected_locations"])
        or {item["final_location"] for item in verified}
        != set(schedule["expected_locations"])
        or len({str(row["subj"]) for row in rows}) != len(schedule["expected_subjects"])
    ):
        raise WorkflowValidationError(
            "final_coverage_witness_set_mismatch",
            "materialized witness certificate is incomplete",
        )
    report = {
        "schema_version": "variation-final-coverage-verification/v1",
        "schedule_sha256": schedule["schedule_sha256"],
        "witness_matrix_sha256": schedule["witness_matrix_sha256"],
        "cohort_hash": cohort["cohort_hash"],
        "fixed_seed_count": len(fixed_seeds),
        "extra_seed_count": 0,
        "verified_location_count": len(verified),
        "verified_subject_count": len({str(row["subj"]) for row in rows}),
        "verified_witnesses_sha256": _hash_value(verified),
        "historical_debug_hash_match_count": sum(
            1
            for item in verified
            if item["historical_decision_sha256_match"]
            and item["historical_final_context_sha256_match"]
        ),
        "coverage_identity_fields": ["run_seed", "final_location", "raw_pool_action"],
        "coverage_is_quality_evidence": False,
        "fixed_verdict": "reject",
        "promotion_ready": False,
        "status": "pass",
    }
    report["verification_sha256"] = _hash_value(report)
    return report


def compact_witness_matrix(matrix: Mapping[str, Any]) -> dict[str, Any]:
    body = {key: value for key, value in matrix.items() if key != "matrix_sha256"}
    if _hash_value(body) != matrix.get("matrix_sha256"):
        raise WorkflowValidationError("witness_matrix_hash_mismatch", "source witness matrix drifted")
    compact_edges = []
    for edge in matrix.get("edges", []):
        witnesses = list(edge.get("witnesses", []))
        compact_edges.append(
            {
                "slot": int(edge["slot"]),
                "variant_id": str(edge["variant_id"]),
                "coverage_locations": sorted(
                    {str(item["final_location"]) for item in witnesses}
                ),
                "witness_count": len(witnesses),
                "witnesses_sha256": _hash_value(witnesses),
            }
        )
    compact = {
        key: value
        for key, value in body.items()
        if key != "edges"
    }
    compact["schema_version"] = "variation-final-coverage-witness-matrix/v2"
    compact["source_matrix_sha256"] = matrix["matrix_sha256"]
    compact["edges"] = compact_edges
    compact["matrix_sha256"] = _hash_value(compact)
    return compact


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan final workflow coverage on the fixed variation cohort.")
    parser.add_argument("--contract")
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--beam-width", type=int, default=5000)
    parser.add_argument("--matrix-output")
    parser.add_argument("--schedule-output")
    parser.add_argument("--verify-schedule")
    parser.add_argument("--compact-matrix-input")
    parser.add_argument("--compact-matrix-output")
    parser.add_argument("--compact-schedule-input")
    parser.add_argument("--compact-schedule-output")
    args = parser.parse_args(argv)
    try:
        if args.compact_matrix_input:
            required = (
                args.compact_matrix_output,
                args.compact_schedule_input,
                args.compact_schedule_output,
            )
            if any(value is None for value in required):
                raise WorkflowValidationError("missing_compaction_argument", "all compaction paths are required")
            compact = compact_witness_matrix(_read_json(Path(args.compact_matrix_input)))
            schedule_value = _read_json(Path(args.compact_schedule_input))
            schedule_value["witness_matrix_sha256"] = compact["matrix_sha256"]
            schedule_value["witness_matrix_source_sha256"] = compact["source_matrix_sha256"]
            schedule_value.pop("schedule_sha256", None)
            schedule_value["schedule_sha256"] = _hash_value(schedule_value)
            matrix_output = Path(args.compact_matrix_output)
            schedule_output = Path(args.compact_schedule_output)
            matrix_output.parent.mkdir(parents=True, exist_ok=True)
            schedule_output.parent.mkdir(parents=True, exist_ok=True)
            matrix_output.write_bytes(canonical_json_bytes(compact))
            schedule_output.write_bytes(canonical_json_bytes(schedule_value))
            schedule = schedule_value
        elif args.verify_schedule:
            schedule = verify_materialized_final_schedule(
                schedule_path=Path(args.verify_schedule),
                repository_root=Path(args.repository_root),
            )
        else:
            if not args.contract:
                raise WorkflowValidationError("missing_final_coverage_contract", "--contract is required")
            schedule = build_final_coverage_schedule(
                contract_path=Path(args.contract),
                repository_root=Path(args.repository_root),
                beam_width=args.beam_width,
                matrix_output=Path(args.matrix_output) if args.matrix_output else None,
            )
            if args.schedule_output:
                schedule_output = Path(args.schedule_output)
                schedule_output.parent.mkdir(parents=True, exist_ok=True)
                schedule_output.write_bytes(canonical_json_bytes(schedule))
    except (OSError, ValueError, json.JSONDecodeError, WorkflowValidationError) as exc:
        envelope = exc.to_envelope() if isinstance(exc, WorkflowValidationError) else WorkflowValidationError(
            "final_coverage_planning_failed",
            "final coverage planning failed",
            exception_type=type(exc).__name__,
        ).to_envelope()
        sys.stderr.buffer.write(canonical_json_bytes(envelope))
        return 2
    sys.stdout.buffer.write(canonical_json_bytes(schedule))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
