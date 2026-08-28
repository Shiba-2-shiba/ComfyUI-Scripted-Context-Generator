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
) -> dict[str, Any]:
    if not isinstance(review_policy, Mapping) or not review_policy:
        raise ValueError("blind review requires an explicit frozen review policy")
    before, after = _records(before_records), _records(after_records)
    if set(before) != set(after):
        raise ValueError("before and after review cohorts must contain identical seeds")
    affected = list(dict.fromkeys(int(seed) for seed in affected_seeds))

    def rank(seed: int) -> str:
        return hashlib.sha256(f"{experiment_id}:review-sample:{seed}".encode()).hexdigest()

    if selected_seeds is not None:
        selected = list(dict.fromkeys(int(seed) for seed in selected_seeds))
        if len(selected) != 20 or any(seed not in before for seed in selected):
            raise ValueError("targeted review requires exactly 20 unique paired seeds")
        controls, exploration = [], []
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
    rubric = (
        f"Blindly compare A and B for {', '.join(DIMENSIONS)}. "
        f"Hypothesis targets are {', '.join(targets)}; guards are {', '.join(guards)}. "
        "Vote A_better, B_better, equal, or abstain per dimension and record hard defects by side."
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
        "reviewed_run_provenance": {
            "after": _record_provenance(after_records),
            "before": _record_provenance(before_records),
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
    for lane_number in (1, 2):
        lane_id = f"lane-{lane_number}"
        pairs, assignments = [], []
        for index, seed in enumerate(selected, start=1):
            digest = hashlib.sha256(f"{experiment_id}:{lane_id}:{seed}".encode()).digest()
            candidate_side = "A" if int.from_bytes(digest[:8], "big") % 2 == 0 else "B"
            incumbent_side = "B" if candidate_side == "A" else "A"
            prompts = {
                candidate_side: after[seed]["cleaned_prompt"],
                incumbent_side: before[seed]["cleaned_prompt"],
            }
            pair_id = f"pair-{index:02d}"
            pairs.append({
                "cohort": before[seed]["cohort"],
                "pair_id": pair_id,
                "prompts": {"A": prompts["A"], "B": prompts["B"]},
                "run_seed": seed,
            })
            assignments.append({
                "candidate_side": candidate_side,
                "incumbent_side": incumbent_side,
                "pair_id": pair_id,
                "run_seed": seed,
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
            "schema_version": "prompt-quality-blind-review-lane/v1",
            "target_qualitative_dimensions": targets,
        }
        lane_content = canonical_json_bytes(lane)
        _atomic_write(output_dir / f"{lane_id}.json", lane_content)
        assignment_key["lanes"].append({
            "assignment_seed_hash": hashlib.sha256(f"{experiment_id}:{lane_id}".encode()).hexdigest(),
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
    )
    sys.stdout.buffer.write(canonical_json_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
