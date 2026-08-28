"""Validate, unblind, and aggregate two prompt-quality review lanes."""

from __future__ import annotations

import argparse
import collections
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


ALL_DIMENSIONS = (
    "protagonist_clarity", "consistency", "naturalness", "redundancy", "diversity", "image_prompt_suitability",
)
LANE_FIELDS = {
    "blinded", "dimensions", "experiment_label", "guard_qualitative_dimensions",
    "implementation_details_visible", "lane_id", "pair_count", "pairs",
    "result_contract", "review_prompt_hash", "rubric", "rubric_version",
    "schema_version", "target_qualitative_dimensions",
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def _defects(vote: Mapping[str, Any]) -> dict[str, set[str]]:
    raw = vote.get("hard_defects", {})
    if isinstance(raw, list):
        result = {"A": set(), "B": set()}
        for item in raw:
            result[str(item["side"])].add(str(item["code"]))
        return result
    return {side: {str(code) for code in raw.get(side, [])} for side in ("A", "B")}


def _valid_hard_defects(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == {"A", "B"}
        and all(
            isinstance(value[side], list)
            and all(isinstance(code, str) and code.strip() for code in value[side])
            for side in ("A", "B")
        )
    )


def aggregate_review(
    review_dir: Path,
    output: Path | None,
    *,
    experiment: Mapping[str, Any] | Path | None = None,
    policy: Mapping[str, Any] | Path | None = None,
) -> dict[str, Any]:
    key_path = review_dir / "assignment-key.json"
    key = _load(key_path)
    experiment_value = _load(experiment) if isinstance(experiment, Path) else dict(experiment or {})
    policy_value = _load(policy) if isinstance(policy, Path) else dict(policy or {})
    first_lane = _load(review_dir / "lane-1.json")
    target_dimensions = list(experiment_value.get(
        "target_qualitative_dimensions", first_lane.get("target_qualitative_dimensions", [])
    ))
    guard_dimensions = list(experiment_value.get(
        "guard_qualitative_dimensions", first_lane.get("guard_qualitative_dimensions", [])
    ))
    if set(target_dimensions) | set(guard_dimensions) != set(ALL_DIMENSIONS) or set(target_dimensions) & set(guard_dimensions):
        raise ValueError("experiment target and guard dimensions must form a disjoint complete rubric partition")
    review_policy = key.get("review_contract")
    if not isinstance(review_policy, Mapping) or not review_policy:
        raise ValueError("assignment key is missing its frozen review contract")
    supplied_review_policy = policy_value.get("review")
    if supplied_review_policy is not None and supplied_review_policy != review_policy:
        raise ValueError("supplied review policy does not match the frozen assignment contract")
    target_contract = review_policy.get("target_dimension_contract")
    guard_contract = review_policy.get("guard_dimension_contract")
    if not isinstance(target_contract, Mapping) or not isinstance(guard_contract, Mapping):
        raise ValueError("frozen review contract is incomplete")
    computed_review_contract_hash = hashlib.sha256(canonical_json_bytes(dict(review_policy))).hexdigest()
    review_contract_hash_valid = key.get("review_contract_hash") == computed_review_contract_hash
    failures: list[dict[str, Any]] = []
    if not review_contract_hash_valid:
        failures.append({"code": "review_contract_hash_mismatch"})
    aggregate = {dimension: collections.Counter() for dimension in ALL_DIMENSIONS}
    lane_directions: dict[str, dict[str, str]] = {dimension: {} for dimension in ALL_DIMENSIONS}
    hard_defects = {"candidate_only": collections.Counter(), "incumbent_only": collections.Counter(), "shared": collections.Counter()}
    lane_hashes, result_hashes, reviewers = {}, {}, []

    for lane_key in key.get("lanes", []):
        lane_id = str(lane_key["lane_id"])
        lane_path = review_dir / f"{lane_id}.json"
        result_path = review_dir / f"{lane_id}-result.json"
        lane, result = _load(lane_path), _load(result_path)
        lane_hash = hashlib.sha256(lane_path.read_bytes()).hexdigest()
        result_hash = hashlib.sha256(result_path.read_bytes()).hexdigest()
        lane_hashes[lane_id], result_hashes[lane_id] = lane_hash, result_hash
        required = lane.get("result_contract", {}).get("required_fields", [])
        missing = [field for field in required if field not in result]
        if missing:
            failures.append({"code": "missing_result_metadata", "lane_id": lane_id, "missing_fields": missing})
        if (
            set(lane) != LANE_FIELDS
            or lane.get("schema_version") != "prompt-quality-blind-review-lane/v1"
            or lane.get("lane_id") != lane_id
            or lane.get("pair_count") != 20
            or lane.get("blinded") is not True
            or lane.get("implementation_details_visible") is not False
            or lane.get("dimensions") != list(ALL_DIMENSIONS)
            or not isinstance(lane.get("pairs"), list)
            or len(lane["pairs"]) != 20
            or any(
                not isinstance(pair, Mapping)
                or set(pair) != {"cohort", "pair_id", "prompts", "run_seed"}
                or not isinstance(pair.get("prompts"), Mapping)
                or set(pair["prompts"]) != {"A", "B"}
                for pair in lane.get("pairs", [])
            )
        ):
            failures.append({"code": "invalid_lane_contract", "lane_id": lane_id})
        if not isinstance(required, list) or set(result) != set(required):
            failures.append({"code": "invalid_result_contract", "lane_id": lane_id})
        if (
            result.get("schema_version") != lane.get("result_contract", {}).get("schema_version")
            or result.get("lane_id") != lane_id
            or result.get("blinded") is not True
            or not isinstance(result.get("reviewer_id"), str)
            or not result["reviewer_id"].strip()
            or not isinstance(result.get("reviewer_type"), str)
            or not result["reviewer_type"].strip()
            or not isinstance(result.get("reviewer_model_version"), str)
            or not result["reviewer_model_version"].strip()
        ):
            failures.append({"code": "invalid_result_metadata", "lane_id": lane_id})
        if result.get("input_hash") != lane_hash or lane_key.get("lane_artifact_hash") != lane_hash:
            failures.append({"code": "lane_input_hash_mismatch", "lane_id": lane_id})
        for field in ("rubric_version", "review_prompt_hash"):
            if result.get(field) != lane.get(field):
                failures.append({"code": f"{field}_mismatch", "lane_id": lane_id})
        if result.get("rubric_hash") != lane.get("review_prompt_hash"):
            failures.append({"code": "rubric_hash_mismatch", "lane_id": lane_id})
        reviewers.append({
            "lane_id": lane_id,
            "reviewer_id": result.get("reviewer_id"),
            "reviewer_model_version": result.get("reviewer_model_version"),
            "reviewer_type": result.get("reviewer_type"),
        })
        expected_pairs = {(item["pair_id"], int(item["run_seed"])) for item in lane.get("pairs", [])}
        votes = result.get("votes", []) if isinstance(result.get("votes"), list) else []
        valid_votes = [
            item for item in votes
            if isinstance(item, Mapping)
            and set(item) == {"dimensions", "hard_defects", "pair_id", "run_seed"}
            and "pair_id" in item
            and "run_seed" in item
            and isinstance(item.get("dimensions"), Mapping)
            and set(item["dimensions"]) == set(ALL_DIMENSIONS)
            and all(value in {"A_better", "B_better", "equal", "abstain"} for value in item["dimensions"].values())
            and _valid_hard_defects(item.get("hard_defects"))
        ]
        if len(valid_votes) != len(votes) or len(valid_votes) != 20:
            failures.append({"code": "invalid_vote_contract", "lane_id": lane_id})
        actual_pairs = {(item["pair_id"], int(item["run_seed"])) for item in valid_votes}
        if expected_pairs != actual_pairs or len(actual_pairs) != 20 or len(valid_votes) != 20:
            failures.append({"code": "review_pair_mismatch", "lane_id": lane_id})
        assignments = {item["pair_id"]: item for item in lane_key["assignments"]}
        for assignment in assignments.values():
            seed = int(assignment["run_seed"])
            digest = hashlib.sha256(f"{key.get('experiment_id')}:{lane_id}:{seed}".encode()).digest()
            expected_candidate = "A" if int.from_bytes(digest[:8], "big") % 2 == 0 else "B"
            if (
                assignment.get("candidate_side") != expected_candidate
                or assignment.get("incumbent_side") != ("B" if expected_candidate == "A" else "A")
            ):
                failures.append({
                    "code": "assignment_side_drift",
                    "lane_id": lane_id,
                    "pair_id": assignment.get("pair_id"),
                })
        if lane.get("target_qualitative_dimensions") != target_dimensions or lane.get("guard_qualitative_dimensions") != guard_dimensions:
            failures.append({"code": "qualitative_scope_mismatch", "lane_id": lane_id})
        lane_counts = {dimension: collections.Counter() for dimension in ALL_DIMENSIONS}
        for vote in valid_votes:
            assignment = assignments[vote["pair_id"]]
            candidate_side, incumbent_side = assignment["candidate_side"], assignment["incumbent_side"]
            for dimension in ALL_DIMENSIONS:
                raw_vote = vote.get("dimensions", {}).get(dimension)
                if raw_vote in {"equal", "abstain"}:
                    outcome = raw_vote
                elif raw_vote in {"A_better", "B_better"}:
                    outcome = "candidate_better" if raw_vote[0] == candidate_side else "candidate_worse"
                else:
                    failures.append({"code": "invalid_vote", "lane_id": lane_id, "pair_id": vote["pair_id"], "dimension": dimension})
                    continue
                aggregate[dimension][outcome] += 1
                lane_counts[dimension][outcome] += 1
            defects = _defects(vote)
            candidate_codes, incumbent_codes = defects[candidate_side], defects[incumbent_side]
            for code in candidate_codes & incumbent_codes:
                hard_defects["shared"][code] += 1
            for code in candidate_codes - incumbent_codes:
                hard_defects["candidate_only"][code] += 1
            for code in incumbent_codes - candidate_codes:
                hard_defects["incumbent_only"][code] += 1
        for dimension, counts in lane_counts.items():
            better, worse = counts["candidate_better"], counts["candidate_worse"]
            lane_directions[dimension][lane_id] = "improvement" if better > worse else "regression" if worse > better else "no_change"

    reviewer_ids = [item["reviewer_id"] for item in reviewers]
    if (
        len(reviewer_ids) != 2
        or any(not isinstance(value, str) or not value.strip() for value in reviewer_ids)
        or len(set(reviewer_ids)) != 2
    ):
        failures.append({"code": "reviewer_identity_not_independent"})
    dimensions: dict[str, Any] = {}
    for dimension, counts in aggregate.items():
        better, worse = counts["candidate_better"], counts["candidate_worse"]
        valid = better + worse
        support = better / valid if valid else 0.0
        worse_rate = worse / valid if valid else 0.0
        is_target = dimension in target_dimensions
        contract = target_contract if is_target else guard_contract
        max_worse = float(contract.get("max_candidate_worse_rate", 0.10))
        passed = worse_rate <= max_worse
        if is_target:
            minimum_valid = int(contract.get("minimum_valid_votes", 36))
            minimum_support = float(contract.get("min_improvement_support", 0.65))
            passed = passed and valid >= minimum_valid and support >= minimum_support
            if valid < minimum_valid:
                failures.append({"code": "insufficient_valid_votes", "dimension": dimension, "actual": valid, "required": minimum_valid})
            if support < minimum_support:
                failures.append({"code": "insufficient_improvement_support", "dimension": dimension, "actual": round(support, 6), "required": minimum_support})
        if bool(contract.get("require_lane_direction_agreement", is_target)) and len(set(lane_directions[dimension].values())) != 1:
            passed = False
            failures.append({"code": "lane_direction_disagreement", "dimension": dimension, "lane_directions": lane_directions[dimension]})
        if worse_rate > max_worse:
            failures.append({"code": "candidate_regression_rate", "dimension": dimension, "actual": round(worse_rate, 6), "maximum": max_worse})
        dimensions[dimension] = {
            "candidate_better": better, "candidate_worse": worse,
            "equal": counts["equal"], "abstain": counts["abstain"],
            "improvement_support": round(support, 6), "lane_directions": lane_directions[dimension],
            "passed": passed, "scope": "target" if is_target else "guard",
            "valid_votes": valid, "worse_rate": round(worse_rate, 6),
        }
    candidate_hard_count = sum(hard_defects["candidate_only"].values())
    if candidate_hard_count:
        failures.append({"code": "candidate_hard_defect", "count": candidate_hard_count})
    result = {
        "assignment_key_hash": hashlib.sha256(key_path.read_bytes()).hexdigest(),
        "candidate_hard_defect_count": candidate_hard_count,
        "dimensions": dimensions,
        "experiment_id": key.get("experiment_id"),
        "failures": failures,
        "guard_qualitative_dimensions": guard_dimensions,
        "hard_defects": {group: dict(sorted(counts.items())) for group, counts in hard_defects.items()},
        "hash_validation": "pass" if not any("hash" in failure["code"] for failure in failures) else "fail",
        "lane_input_hashes": lane_hashes,
        "lane_result_hashes": result_hashes,
        "pair_count_per_lane": 20,
        "qualitative_scope_hash": key.get("qualitative_scope_hash"),
        "reviewers": reviewers,
        "review_contract_hash": computed_review_contract_hash,
        "reviewed_record_hashes": key.get("reviewed_record_hashes", {}),
        "reviewed_run_provenance": key.get("reviewed_run_provenance", {}),
        "schema_version": "prompt-quality-review/v1",
        "status": "pass" if not failures else "fail",
        "verdict": "pass" if not failures else "reject",
        "target_qualitative_dimensions": target_dimensions,
    }
    if output is not None:
        _atomic_write(output, canonical_json_bytes(result))
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--policy", required=True)
    args = parser.parse_args(argv)
    result = aggregate_review(
        Path(args.review_dir), Path(args.output), experiment=Path(args.experiment), policy=Path(args.policy)
    )
    sys.stdout.buffer.write(canonical_json_bytes({"output": args.output, "status": result["status"], "failures": result["failures"]}))
    return 0 if result["status"] == "pass" else 3


if __name__ == "__main__":
    raise SystemExit(main())
