"""Build deterministic, implementation-blind prompt review lanes."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.prompt_quality_loop import _atomic_write
from tools.workflow_prompt_runner import canonical_json_bytes


DIMENSIONS = [
    "protagonist_clarity", "consistency", "naturalness", "redundancy",
    "diversity", "image_prompt_suitability",
]


def _records(path: Path) -> dict[int, dict[str, Any]]:
    return {
        int(record["run_seed"]): record
        for record in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)
    }


def _paired_records(path: Path) -> dict[str, dict[str, Any]]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if any(not isinstance(record, Mapping) or not isinstance(record.get("pair_id"), str) for record in records):
        raise ValueError(f"semantic review records require pair_id: {path}")
    result = {record["pair_id"]: record for record in records}
    if len(result) != len(records):
        raise ValueError(f"semantic review records contain duplicate pair_id: {path}")
    return result


def _record_provenance(path: Path) -> dict[str, str]:
    for name in ("run-manifest.json", "confirmation.json"):
        candidate = path.parent / name
        if not candidate.exists():
            continue
        value = json.loads(candidate.read_text(encoding="utf-8"))
        source_hash = value.get("source_tree_hash")
        cohort_hash = value.get("cohort_hash")
        if all(isinstance(item, str) and len(item) == 64 for item in (source_hash, cohort_hash)):
            return {"cohort_hash": cohort_hash, "source_tree_hash": source_hash}
    raise ValueError(f"review records require adjacent run-manifest.json or confirmation.json provenance: {path}")


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        raise ValueError(f"review records must be beneath repository root: {path}") from None


def build_review(
    before_records: Path,
    after_records: Path,
    output_dir: Path,
    experiment_id: str,
    affected_seeds: Sequence[int],
    selected_seeds: Sequence[int] | None = None,
    target_dimensions: Sequence[str] | None = None,
    guard_dimensions: Sequence[str] | None = None,
    review_policy: Mapping[str, Any] | None = None,
    comparison: Mapping[str, Any] | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(review_policy, Mapping) or not review_policy:
        raise ValueError("blind review requires an explicit frozen review policy")
    contract_schema = review_policy.get("schema_version")
    if contract_schema not in {
        None,
        "prompt-quality-review-contract/v1",
        "prompt-quality-review-contract/v3",
        "prompt-quality-review-contract/v4",
        "prompt-quality-review-contract/v5",
        "prompt-quality-review-contract/v6",
    }:
        raise ValueError(f"unsupported review contract schema: {contract_schema!r}")
    is_v3 = contract_schema == "prompt-quality-review-contract/v3"
    is_v4 = contract_schema == "prompt-quality-review-contract/v4"
    is_v5 = contract_schema == "prompt-quality-review-contract/v5"
    is_v6 = contract_schema == "prompt-quality-review-contract/v6"
    is_semantic = is_v4 or is_v5 or is_v6
    before = _paired_records(before_records) if is_semantic else _records(before_records)
    after = _paired_records(after_records) if is_semantic else _records(after_records)
    if set(before) != set(after):
        noun = "pair IDs" if is_semantic else "seeds"
        raise ValueError(f"before and after review cohorts must contain identical {noun}")
    affected = list(dict.fromkeys(int(seed) for seed in affected_seeds))
    comparison_value: dict[str, Any] = {}
    comparison_hash: str | None = None
    comparison_path: str | None = None
    if is_v3:
        if not isinstance(comparison, Path):
            raise ValueError("review-contract/v3 requires a comparison artifact path")
        comparison_value = json.loads(comparison.read_text(encoding="utf-8"))
        if comparison_value.get("schema_version") != "prompt-quality-comparison/v1":
            raise ValueError("review-contract/v3 requires a canonical comparison/v1 artifact")
        if comparison_value.get("experiment_id") != experiment_id:
            raise ValueError("v3 comparison experiment does not match the review experiment")
        frozen_contract_hash = hashlib.sha256(canonical_json_bytes(dict(review_policy))).hexdigest()
        if comparison_value.get("review_contract_hash") != frozen_contract_hash:
            raise ValueError("v3 comparison review contract does not match the supplied policy")
        comparison_hash = hashlib.sha256(comparison.read_bytes()).hexdigest()
        comparison_path = _repo_relative(comparison)
        frozen = comparison_value.get("review_selection")
        if not isinstance(frozen, Mapping):
            raise ValueError("v3 comparison is missing its frozen review selection")
        computed_selection = dict(frozen)
        frozen_hash = computed_selection.pop("selection_hash", None)
        if frozen_hash != hashlib.sha256(canonical_json_bytes(computed_selection)).hexdigest():
            raise ValueError("v3 comparison selection hash is invalid")
        expected_hashes = comparison_value.get("record_artifact_hashes", {})
        actual_hashes = {
            "before": hashlib.sha256(before_records.read_bytes()).hexdigest(),
            "after": hashlib.sha256(after_records.read_bytes()).hexdigest(),
        }
        if expected_hashes != actual_hashes:
            raise ValueError("v3 comparison does not bind the supplied review records")
        affected = list(frozen.get("affected_seeds", []))
        selected_seeds = list(frozen.get("selected_seeds", []))
    elif is_semantic:
        if not isinstance(comparison, Path):
            raise ValueError("semantic review contract requires a comparison artifact path")
        comparison_value = json.loads(comparison.read_text(encoding="utf-8"))
        expected_fields = {
            "schema_version", "experiment_id", "review_contract_hash", "qualitative_scope_hash",
            "automatic_comparison_path", "automatic_comparison_hash", "automatic_comparison_verdict",
            "candidate_source_tree_sha256", "candidate_snapshot_content_sha256", "uses_output_metrics_for_selection",
            "semantic_pair_contract_sha256", "pair_generation_receipt_sha256",
            "pair_validation_sha256", "selection_salt_sha256", "compatibility_graph_sha256",
            "baseline_records_sha256", "candidate_records_sha256", "review_selection",
        }
        if not isinstance(comparison_value, dict) or set(comparison_value) != expected_fields:
            raise ValueError("review-contract/v4 requires the exact comparison/v2 contract")
        expected_comparison_schema = "prompt-quality-comparison/v4" if is_v6 else "prompt-quality-comparison/v3" if is_v5 else "prompt-quality-comparison/v2"
        if comparison_value.get("schema_version") != expected_comparison_schema:
            raise ValueError(f"review contract requires a canonical {expected_comparison_schema} artifact")
        if comparison_value.get("experiment_id") != experiment_id:
            raise ValueError("v4 comparison experiment does not match the review experiment")
        frozen_contract_hash = hashlib.sha256(canonical_json_bytes(dict(review_policy))).hexdigest()
        if comparison_value.get("review_contract_hash") != frozen_contract_hash:
            raise ValueError("v4 comparison review contract does not match the supplied policy")
        if comparison_value.get("automatic_comparison_verdict") != "pass":
            raise ValueError("v4 comparison requires a passing automatic comparison")
        if comparison_value.get("uses_output_metrics_for_selection") is not False:
            raise ValueError("v4 comparison selection must not use generated output metrics")
        actual_hashes = {
            "baseline_records_sha256": hashlib.sha256(before_records.read_bytes()).hexdigest(),
            "candidate_records_sha256": hashlib.sha256(after_records.read_bytes()).hexdigest(),
        }
        if any(comparison_value.get(field) != value for field, value in actual_hashes.items()):
            raise ValueError("v4 comparison does not bind the supplied semantic-pair records")
        comparison_hash = hashlib.sha256(comparison.read_bytes()).hexdigest()
        comparison_path = _repo_relative(comparison)
        frozen = comparison_value.get("review_selection")
        if not isinstance(frozen, Mapping) or set(frozen) != {"pairs", "dimensions", "selection_hash"}:
            raise ValueError("v4 comparison is missing its exact frozen review selection")
        computed_selection = dict(frozen)
        frozen_hash = computed_selection.pop("selection_hash", None)
        if frozen_hash != hashlib.sha256(canonical_json_bytes(computed_selection)).hexdigest():
            raise ValueError("v4 comparison selection hash is invalid")
        pair_specs = frozen.get("pairs")
        if (
            not isinstance(pair_specs, list) or len(pair_specs) != 20
            or any(not isinstance(item, Mapping) or set(item) != {"pair_id", "cohort", "run_seed"} for item in pair_specs)
        ):
            raise ValueError("v4 comparison requires exactly 20 frozen pair bindings")
        selected_pair_ids = [str(item["pair_id"]) for item in pair_specs]
        if len(set(selected_pair_ids)) != 20 or set(selected_pair_ids) != set(before):
            raise ValueError("v4 comparison pair IDs do not match the supplied records")
        for item in pair_specs:
            pair_id = str(item["pair_id"])
            if int(before[pair_id].get("run_seed")) != int(item["run_seed"]) or int(after[pair_id].get("run_seed")) != int(item["run_seed"]):
                raise ValueError("v4 comparison run-seed binding mismatch")
        selected_seeds = None

    def rank(seed: int) -> str:
        return hashlib.sha256(f"{experiment_id}:review-sample:{seed}".encode()).hexdigest()

    if is_semantic:
        selected = selected_pair_ids
        selection = {"pairs": list(frozen["pairs"])}
    elif selected_seeds is not None:
        selected = list(dict.fromkeys(int(seed) for seed in selected_seeds))
        if len(selected) != 20 or any(seed not in before for seed in selected):
            raise ValueError("targeted review requires exactly 20 unique paired seeds")
        selection = {"repro_cohort": selected}
    else:
        if len(affected) > 16 or any(seed not in before or before[seed].get("cohort") != "control" for seed in affected):
            raise ValueError("affected seeds must be at most 16 members of the control cohort")
        control_needed = 16 - len(affected)
        controls = sorted(
            (seed for seed, record in before.items() if record.get("cohort") == "control" and seed not in affected),
            key=rank,
        )[:control_needed]
        exploration = sorted(
            (seed for seed, record in before.items() if record.get("cohort") == "exploration"), key=rank
        )[:4]
        selected = affected + controls + exploration
        if len(selected) != 20:
            raise ValueError("review requires exactly 16 control and 4 exploration pairs")
        selection = {"affected_control": affected, "unaffected_control": controls, "exploration": exploration}

    targets = list(target_dimensions or [
        "consistency", "naturalness", "protagonist_clarity", "image_prompt_suitability",
    ])
    guards = list(guard_dimensions or [dimension for dimension in DIMENSIONS if dimension not in targets])
    if len(targets) != len(set(targets)) or len(guards) != len(set(guards)) or set(targets) & set(guards):
        raise ValueError("target and guard qualitative dimensions must be unique and disjoint")
    if set(targets) | set(guards) != set(DIMENSIONS):
        raise ValueError("target and guard qualitative dimensions must partition the review rubric")
    if is_v3:
        scope_hash = hashlib.sha256(canonical_json_bytes({
            "guard_qualitative_dimensions": guards,
            "target_qualitative_dimensions": targets,
        })).hexdigest()
        if comparison_value.get("qualitative_scope_hash") != scope_hash:
            raise ValueError("v3 comparison qualitative scope does not match the review assignment")
    elif is_semantic:
        scope_hash = hashlib.sha256(canonical_json_bytes({
            "guard_qualitative_dimensions": guards,
            "target_qualitative_dimensions": targets,
        })).hexdigest()
        if comparison_value.get("qualitative_scope_hash") != scope_hash:
            raise ValueError("v4 comparison qualitative scope does not match the review assignment")
    rubric = (
        f"Blindly compare A and B for {', '.join(DIMENSIONS)}. "
        f"Hypothesis targets are {', '.join(targets)}; guards are {', '.join(guards)}. "
        "Vote A_better, B_better, equal, or abstain per dimension and record hard defects by side."
    )
    if is_v3 or is_semantic:
        rubric += " Hard defects must use one closed atomic code and non-empty free-text evidence per observation."
    if is_semantic:
        rubric = (
            f"Blindly compare A and B for {', '.join(DIMENSIONS)}. "
            "Vote A_better, B_better, equal, or abstain per dimension. "
            + ("Equal means both prompts are assessable and neither is better; abstain means the dimension cannot be assessed for this pair. " if is_v5 or is_v6 else "")
            + "Record hard defects by side. "
            "Hard defects must use one closed atomic code and non-empty free-text evidence per observation."
        )
    rubric_hash = hashlib.sha256(rubric.encode()).hexdigest()
    assignment_key: dict[str, Any] = {
        "experiment_id": experiment_id,
        "lanes": [],
        "reviewed_record_hashes": {
            "after": hashlib.sha256(after_records.read_bytes()).hexdigest(),
            "before": hashlib.sha256(before_records.read_bytes()).hexdigest(),
        },
        "reviewed_record_paths": {
            "after": _repo_relative(after_records),
            "before": _repo_relative(before_records),
        },
        "reviewed_run_provenance": {} if is_semantic else {
            "after": _record_provenance(after_records), "before": _record_provenance(before_records),
        },
        "review_contract": dict(review_policy),
        "review_contract_hash": hashlib.sha256(canonical_json_bytes(dict(review_policy))).hexdigest(),
        "qualitative_scope_hash": hashlib.sha256(canonical_json_bytes({
            "guard_qualitative_dimensions": guards,
            "target_qualitative_dimensions": targets,
        })).hexdigest(),
        "schema_version": "prompt-quality-review-assignment-key/v1",
        "selection": selection,
    }
    if is_v3:
        frozen = comparison_value["review_selection"]
        assignment_key.update({
            "comparison_artifact_hash": comparison_hash,
            "comparison_artifact_path": comparison_path,
            "dimension_eligibility": frozen["dimensions"],
            "selection": {
                key: value for key, value in frozen.items()
                if key not in {"dimensions", "selection_hash"}
            },
            "selection_hash": frozen["selection_hash"],
            "schema_version": "prompt-quality-review-assignment-key/v3",
        })
    elif is_semantic:
        dimensions = comparison_value["review_selection"]["dimensions"]
        if not isinstance(dimensions, Mapping) or set(dimensions) != set(DIMENSIONS):
            raise ValueError("semantic comparison dimension eligibility must cover the exact rubric")
        eligibility_fields = (
            {"authority", "minimum_non_abstain_votes", "minimum_directional_votes", "pair_ids"}
            if is_v5 or is_v6 else {"authority", "minimum_valid_votes", "pair_ids"}
        )
        for dimension, eligibility in dimensions.items():
            if not isinstance(eligibility, Mapping) or set(eligibility) != eligibility_fields:
                raise ValueError(f"invalid semantic dimension eligibility: {dimension}")
        consistency = dimensions["consistency"]
        if set(consistency["pair_ids"]) != set(selected):
            raise ValueError("semantic consistency eligibility requires all 20 pairs")
        if is_v5 or is_v6:
            if consistency["minimum_non_abstain_votes"] != 36 or consistency["minimum_directional_votes"] != 20:
                raise ValueError("v5 consistency requires 36 non-abstain and 20 directional votes")
        elif consistency["minimum_valid_votes"] != 36:
            raise ValueError("v4 consistency requires all 20 pairs and exactly 36 minimum valid votes")
        binding_fields = (
            "semantic_pair_contract_sha256", "pair_generation_receipt_sha256", "pair_validation_sha256",
            "selection_salt_sha256", "compatibility_graph_sha256", "baseline_records_sha256",
            "candidate_records_sha256", "candidate_source_tree_sha256",
            "candidate_snapshot_content_sha256",
        )
        assignment_key.update({
            "comparison_artifact_hash": comparison_hash,
            "comparison_artifact_path": comparison_path,
            "dimension_eligibility": dimensions,
            "pair_evidence_bindings": {field: comparison_value[field] for field in binding_fields},
            "selection_hash": frozen["selection_hash"],
            "schema_version": "prompt-quality-review-assignment-key/v6" if is_v6 else "prompt-quality-review-assignment-key/v5" if is_v5 else "prompt-quality-review-assignment-key/v4",
        })
    for lane_number in (1, 2):
        lane_id = f"lane-{lane_number}"
        pairs, assignments = [], []
        for index, selected_id in enumerate(selected, start=1):
            pair_id = selected_id if is_semantic else f"pair-{index:02d}"
            seed = int(before[pair_id]["run_seed"]) if is_semantic else int(selected_id)
            assignment_material = f"{comparison_hash}:{lane_id}:{pair_id}" if is_semantic else f"{experiment_id}:{lane_id}:{seed}"
            digest = hashlib.sha256(assignment_material.encode()).digest()
            candidate_side = "A" if int.from_bytes(digest[:8], "big") % 2 == 0 else "B"
            incumbent_side = "B" if candidate_side == "A" else "A"
            prompts = {
                candidate_side: after[pair_id if is_semantic else seed]["cleaned_prompt"],
                incumbent_side: before[pair_id if is_semantic else seed]["cleaned_prompt"],
            }
            if is_semantic:
                pairs.append({"pair_id": pair_id, "prompts": {"A": prompts["A"], "B": prompts["B"]}})
            else:
                pairs.append({
                    "cohort": before[seed]["cohort"], "pair_id": pair_id,
                    "prompts": {"A": prompts["A"], "B": prompts["B"]}, "run_seed": seed,
                })
            assignments.append({
                "candidate_side": candidate_side,
                "incumbent_side": incumbent_side,
                "pair_id": pair_id,
                **({} if is_semantic else {"run_seed": seed}),
            })
        lane = {
            "blinded": True,
            "dimensions": DIMENSIONS,
            "experiment_label": "experiment-g003",
            "implementation_details_visible": False,
            "lane_id": lane_id,
            "pair_count": 20,
            "pairs": pairs,
            "review_prompt_hash": rubric_hash,
            "result_contract": {
                "allowed_votes": ["A_better", "B_better", "equal", "abstain"],
                "required_fields": [
                    "schema_version", "lane_id", "reviewer_id", "reviewer_type",
                    "reviewer_model_version", "blinded", "rubric_version", "rubric_hash",
                    "review_prompt_hash", "input_hash", "votes",
                ],
                "schema_version": "prompt-quality-blind-review-result/v1",
            },
            "guard_qualitative_dimensions": guards,
            "rubric": rubric,
            "rubric_version": "prompt-quality-review-rubric/v2",
            "schema_version": "prompt-quality-blind-review-lane/v6" if is_v6 else "prompt-quality-blind-review-lane/v5" if is_v5 else "prompt-quality-blind-review-lane/v4" if is_v4 else "prompt-quality-blind-review-lane/v3" if is_v3 else "prompt-quality-blind-review-lane/v1",
            "target_qualitative_dimensions": targets,
        }
        if is_v3:
            lane["dimension_eligibility"] = assignment_key["dimension_eligibility"]
            lane["selection_hash"] = assignment_key["selection_hash"]
            lane["result_contract"]["schema_version"] = "prompt-quality-blind-review-result/v3"
            lane["result_contract"]["hard_defects"] = {
                "allowed_codes": list(review_policy.get("hard_defect_codes", [])),
                "item_fields": ["code", "evidence"],
                "unknown_codes": "reject",
            }
        elif is_semantic:
            lane.pop("experiment_label")
            lane.pop("guard_qualitative_dimensions")
            lane.pop("target_qualitative_dimensions")
            lane["result_contract"]["schema_version"] = "prompt-quality-blind-review-result/v6" if is_v6 else "prompt-quality-blind-review-result/v5" if is_v5 else "prompt-quality-blind-review-result/v4"
            lane["result_contract"]["required_fields"].append("review_session_id")
            lane["result_contract"]["hard_defects"] = {
                "allowed_codes": list(review_policy.get("hard_defect_codes", [])),
                "item_fields": ["code", "evidence"], "unknown_codes": "reject",
            }
        lane_content = canonical_json_bytes(lane)
        _atomic_write(output_dir / f"{lane_id}.json", lane_content)
        assignment_key["lanes"].append({
            "assignment_seed_hash": hashlib.sha256(
                (f"{comparison_hash}:{lane_id}" if is_semantic else f"{experiment_id}:{lane_id}").encode()
            ).hexdigest(),
            "assignments": assignments,
            "lane_artifact_hash": hashlib.sha256(lane_content).hexdigest(),
            "lane_id": lane_id,
        })
    key_content = canonical_json_bytes(assignment_key)
    _atomic_write(output_dir / "assignment-key.json", key_content)
    return {
        "assignment_key_hash": hashlib.sha256(key_content).hexdigest(),
        "output_dir": str(output_dir),
        "rubric_hash": rubric_hash,
        "selected_seeds": selected,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-records", required=True)
    parser.add_argument("--after-records", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--affected-seeds", required=True)
    parser.add_argument("--selected-seeds")
    parser.add_argument("--target-dimensions")
    parser.add_argument("--guard-dimensions")
    parser.add_argument("--policy", required=True)
    parser.add_argument("--comparison")
    args = parser.parse_args(argv)
    policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))
    result = build_review(
        Path(args.before_records), Path(args.after_records), Path(args.output_dir), args.experiment_id,
        [int(seed) for seed in args.affected_seeds.split(",") if seed],
        selected_seeds=[int(seed) for seed in args.selected_seeds.split(",") if seed]
        if args.selected_seeds else None,
        target_dimensions=args.target_dimensions.split(",") if args.target_dimensions else None,
        guard_dimensions=args.guard_dimensions.split(",") if args.guard_dimensions else None,
        review_policy=policy.get("review"),
        comparison=Path(args.comparison) if args.comparison else None,
    )
    sys.stdout.buffer.write(canonical_json_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
