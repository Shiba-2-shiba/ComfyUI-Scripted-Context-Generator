"""Create prospective coverage and unselected V150 evaluation from real snapshots.

Run after freezing source. Historical JSON supplies fixed policy settings and an
authentic coverage-parent reference only; all execution evidence is generated anew.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.analyze_variation_candidates import load_candidate_catalog
from tools.build_prompt_quality_confirmation import _sanitized_environment
from tools.compare_variation_prompt_pair import _declared_run_contract
from tools.materialize_variation_candidate_snapshot import build_snapshot_plan, materialize_candidate_snapshots
from tools.plan_variation_final_coverage import ALGORITHM_VERSION, PROBE_TRANSFORM
from tools.prompt_quality_loop import build_cohort, build_source_manifest
from tools.variation_quality_contract import PROSPECTIVE_SCHEMA_VERSION, _hash_path, _hash_value, validate_variation_quality_contract
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes, load_profile
from workflow_widget_validation import load_workflow


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict) -> None:
    path.write_bytes(canonical_json_bytes(value))


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _run(root: Path, logs: Path, name: str, *arguments: str) -> None:
    print(name, flush=True)
    env = _sanitized_environment(root)
    with (logs / f"{name}.stdout.log").open("wb") as stdout, (logs / f"{name}.stderr.log").open("wb") as stderr:
        completed = subprocess.run([sys.executable, *map(str, arguments)], cwd=root, env=env, stdout=stdout, stderr=stderr, check=False)
    if completed.returncode:
        raise WorkflowValidationError("quality_preparation_execution_failed", "evaluation command failed; inspect its logs", stage=name, returncode=completed.returncode)


def _snapshot(experiment: Path, destination: Path, *, schedule: Path | None = None, quality: Path | None = None) -> dict:
    plan = build_snapshot_plan(
        candidate_iteration=experiment / "candidate-iteration.json", scenario_manifest=experiment / "scenario-manifest.json",
        projection_report=experiment / "projection-report.json", analysis_report=experiment / "analysis-report.json",
        baseline_manifest_path=experiment / "baseline-manifest.json", baseline_prompt_mode="active",
        prompt_schedule=schedule, quality_contract=quality, source_root=ROOT,
    )
    return materialize_candidate_snapshots(plan, source_root=ROOT, destination_root=destination)


def _run_contract(root: Path, template: dict) -> dict:
    workflow_name, profile_name = template["workflow"], template["profile"]
    workflow = load_workflow(root / workflow_name)
    profile = load_profile(root / profile_name)
    workflow_hash = _hash_value(workflow)
    override_hash = _hash_value({"explicit": {}, "profile": profile.resolved_overrides()})
    contract = {"workflow": workflow_name, "profile": profile_name, "overrides": {},
                "workflow_hash": workflow_hash, "profile_hash": profile.hash, "override_hash": override_hash,
                "effective_workflow_hash": _hash_value({"base_workflow_hash": workflow_hash, "override_hash": override_hash})}
    _declared_run_contract(root, {"workflow": workflow_name, "profile": profile_name, "run_contract": contract})
    return contract


def prepare(experiment: Path, output: Path) -> dict:
    if output.exists() or not output.is_relative_to(ROOT / "assets/results"):
        raise WorkflowValidationError("quality_preparation_destination", "output must be a new directory below assets/results")
    output.mkdir(parents=True)
    (output / "logs").mkdir()
    source_hash = build_source_manifest(ROOT)["source_tree_hash"]
    iteration = experiment / "candidate-iteration.json"
    catalog = load_candidate_catalog(iteration)
    historical = ROOT / "docs/variation_expansion/experiments/v150-candidate-shape-iteration-019"
    settings = _read(historical / "quality-experiment.json")
    fixed = settings["cohort"]
    cohort = build_cohort(fixed["experiment_seed"], fixed["iteration_id"], list(range(64)), 80)
    if cohort["cohort_hash"] != fixed["cohort_hash"]:
        raise WorkflowValidationError("quality_preparation_cohort_drift", "frozen quality cohort no longer reproduces")
    print("materialize calibration", flush=True)
    calibration = _snapshot(experiment, output / "calibration")
    run_contract = _run_contract(output / "calibration/candidate-root", settings)
    parent_path = ROOT / "docs/variation_expansion/experiments/v150-candidate-shape-iteration-005/rejection-receipt.json"
    # This is an actual immutable historical reference, never a generated status.
    if _read(parent_path).get("terminal_state") != "REJECTED":
        raise WorkflowValidationError("quality_preparation_parent_invalid", "historical coverage parent is not a rejection")
    coverage_contract = {
        "schema_version": "variation-final-coverage-contract/v1", "contract_id": catalog["catalog_id"],
        "algorithm_version": ALGORITHM_VERSION, "cohort": cohort, "run_contract": run_contract,
        "probe_transform": PROBE_TRANSFORM, "probe_transform_sha256": _hash_value(PROBE_TRANSFORM),
        "coverage_is_quality_evidence": False, "fixed_quality_verdict": "reject", "promotion_ready": False, "extra_seed_count": 0,
        "parent_rejection_receipt_path": _relative(parent_path), "parent_rejection_receipt_sha256": _hash_path(parent_path),
        "calibration_snapshot_manifest_path": _relative(output / "calibration/snapshot-manifest.json"),
        "calibration_snapshot_manifest_sha256": _hash_path(output / "calibration/snapshot-manifest.json"),
        "calibration_candidate_source_tree_sha256": calibration["candidate_source_tree_sha256"],
        "calibration_action_pools_sha256": _hash_path(output / "calibration/candidate-root/vocab/data/action_pools.json"),
        "candidate_iteration_path": _relative(iteration), "candidate_iteration_sha256": _hash_path(iteration),
        "effective_catalog_sha256": _hash_value(catalog), "witness_matrix_path": _relative(output / "witness-matrix.json"),
    }
    coverage_contract["contract_sha256"] = _hash_value(coverage_contract)
    _write(output / "coverage-contract.json", coverage_contract)
    schedule_path = output / "coverage-schedule.json"
    _run(output / "calibration/candidate-root", output / "logs", "plan-coverage",
         "tools/plan_variation_final_coverage.py", "--repository-root", ROOT, "--contract", output / "coverage-contract.json",
         "--matrix-output", output / "witness-matrix.json", "--schedule-output", schedule_path)
    print("materialize and replay coverage", flush=True)
    coverage = _snapshot(experiment, output / "coverage", schedule=schedule_path)
    schedule = _read(schedule_path)
    certificate = coverage["prompt_schedule_verification"]
    quality = {
        "schema_version": PROSPECTIVE_SCHEMA_VERSION, "contract_id": str(catalog["catalog_id"]) + "-default-quality",
        "coverage_snapshot_manifest_path": _relative(output / "coverage/snapshot-manifest.json"),
        "coverage_snapshot_manifest_sha256": _hash_path(output / "coverage/snapshot-manifest.json"),
        "coverage_snapshot_content_sha256": coverage["candidate_snapshot_content_sha256"],
        "coverage_schedule_path": _relative(schedule_path), "coverage_schedule_sha256": _hash_path(schedule_path),
        "candidate_iteration_path": _relative(iteration), "candidate_iteration_sha256": _hash_path(iteration),
        "effective_catalog_sha256": _hash_value(catalog), "candidate_source_tree_sha256": coverage["candidate_source_tree_sha256"],
        "candidate_ids": coverage["candidate_ids"], "cohort": cohort, "run_contract": run_contract,
        "coverage_eligibility": {"candidate_action_pool_locations": 19, "candidate_locations": 19, "candidate_subjects": 15,
            "extra_seed_count": 0, "fixed_seed_count": 80, "prompt_schedule_sha256": schedule["schedule_sha256"],
            "witness_matrix_sha256": schedule["witness_matrix_sha256"], "certificate_verification_sha256": certificate["verification_sha256"], "status": "pass"},
        "surface": {"baseline_rows": 80, "candidate_rows": 80, "kind": "default_fixed_64_16", "prompt_selection": "default_unselected", "uses_output_metrics_for_selection": False},
        "authority": {"coverage_is_quality_evidence": False, "quality_evidence": True, "promotion_ready": False},
    }
    quality["contract_sha256"] = _hash_value(quality)
    validate_variation_quality_contract(quality, repository_root=ROOT)
    _write(output / "quality-contract.json", quality)
    print("materialize unselected quality", flush=True)
    final = _snapshot(experiment, output / "quality", quality=output / "quality-contract.json")
    if final["candidate_source_tree_sha256"] != quality["candidate_source_tree_sha256"]:
        raise WorkflowValidationError("quality_preparation_source_drift", "coverage and quality source differ")
    settings.pop("experiment_sha256", None)
    settings.update({"experiment_id": catalog["catalog_id"], "run_contract": run_contract,
                     "quality_contract_sha256": quality["contract_sha256"],
                     "snapshot_manifest_sha256": _hash_path(output / "quality/snapshot-manifest.json"),
                     "default_candidate_prompts_sha256": _hash_path(output / "quality/candidate-root/prompts.jsonl")})
    _write(output / "quality-experiment.json", settings)
    if source_hash != build_source_manifest(ROOT)["source_tree_hash"]:
        raise WorkflowValidationError("quality_preparation_source_drift", "active source changed during preparation")
    receipt = {"schema_version": "variation-quality-preparation/v1", "active_source_tree_sha256": source_hash,
               "candidate_source_tree_sha256": final["candidate_source_tree_sha256"],
               "candidate_snapshot_content_sha256": final["candidate_snapshot_content_sha256"],
               "snapshot_manifest_sha256": _hash_path(output / "quality/snapshot-manifest.json"),
               "quality_experiment_sha256": _hash_path(output / "quality-experiment.json"),
               "status": "prepared", "quality_evaluated": False, "promotion_ready": False}
    _write(output / "preparation.json", receipt)
    return receipt


def automatic(output: Path) -> dict:
    receipt = _read(output / "preparation.json")
    if (build_source_manifest(ROOT)["source_tree_hash"] != receipt["active_source_tree_sha256"]
        or _hash_path(output / "quality-experiment.json") != receipt["quality_experiment_sha256"]
        or _hash_path(output / "quality/snapshot-manifest.json") != receipt["snapshot_manifest_sha256"]):
        raise WorkflowValidationError("quality_preparation_source_drift", "source or frozen evaluation inputs changed")
    experiment = _read(output / "quality-experiment.json")
    cohort = experiment["cohort"]
    for side in ("baseline", "candidate"):
        root = output / "quality" / f"{side}-root"
        run = output / f"{side}-run"
        _run(root, output / "logs", f"generate-{side}", "tools/prompt_quality_loop.py", "generate",
             "--workflow", experiment["workflow"], "--profile", experiment["profile"],
             "--experiment-seed", str(cohort["experiment_seed"]), "--iteration-id", cohort["iteration_id"],
             "--samples", "80", "--artifact-root", output, "--output-dir", run)
        _run(root, output / "logs", f"analyze-{side}", "tools/prompt_quality_loop.py", "analyze", "--run-dir", run, "--artifact-root", output)
    _run(ROOT, output / "logs", "compare-automatic", "tools/compare_variation_prompt_pair.py",
         "--snapshot-root", output / "quality", "--baseline-run", output / "baseline-run", "--candidate-run", output / "candidate-run",
         "--experiment", output / "quality-experiment.json", "--output", output / "automatic-comparison.json")
    return _read(output / "automatic-comparison.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-dir", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--stage", choices=("prepare", "automatic", "all"), default="all")
    args = parser.parse_args()
    output = args.output_root.resolve()
    if args.stage in {"prepare", "all"}:
        result = prepare(args.experiment_dir.resolve(), output)
    if args.stage in {"automatic", "all"}:
        result = automatic(output)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
