"""Prepare new, prospective candidate inputs from tracked authoring data.

Historical bindings are recorded as origins, never repaired in place or reused
as evaluation evidence. Projection and structural analysis are recomputed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import plan_variation_target as planner
from tools.analyze_variation_candidates import analyze_candidate_catalog, load_candidate_catalog
from tools.materialize_variation_candidate_snapshot import build_snapshot_plan
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def prepare_candidate(*, iteration: Path, destination: Path, experiment_id: str) -> dict:
    iteration, destination = iteration.resolve(), destination.resolve()
    if not destination.is_relative_to(ROOT / "docs/variation_expansion/experiments"):
        raise WorkflowValidationError("candidate_preparation_destination", "destination must be a new experiment directory")
    if destination.exists():
        raise WorkflowValidationError("candidate_preparation_exists", "prospective experiment already exists")
    origins = []
    copied: dict[Path, Path] = {}
    visiting: set[Path] = set()

    def copy_input(source: Path, *, catalog: bool = False) -> Path:
        source = source.resolve()
        if not source.is_relative_to(ROOT) or source.is_symlink():
            raise WorkflowValidationError("candidate_preparation_input", "authoring input must be inside the repository")
        if source in visiting:
            raise WorkflowValidationError("candidate_catalog_cycle", "candidate catalog composition contains a cycle")
        if source in copied:
            return copied[source]
        visiting.add(source)
        target = destination / "authoring" / source.relative_to(ROOT)
        value = _read(source)
        if catalog:
            for name in ("base_catalog", "action_overrides", "location_additions", "location_overrides"):
                if name + "_path" in value:
                    child = copy_input(ROOT / value[name + "_path"], catalog=name == "base_catalog")
                    value[name + "_path"] = child.relative_to(ROOT).as_posix()
                    value[name + "_sha256"] = _hash(child)
            value["prompt_quality_receipt"] = None
        _write(target, value)
        origins.append({"source_path": source.relative_to(ROOT).as_posix(), "source_sha256": _hash(source),
                        "prepared_path": target.relative_to(ROOT).as_posix(), "prepared_sha256": _hash(target)})
        copied[source] = target
        visiting.remove(source)
        return target

    # Bind only real current inputs and retain the existing pool-counting policy.
    baseline = {
        "schema_version": "variation-planner-experiment-manifest/v1",
        "experiment_id": experiment_id,
        "state": "BASELINE_READY",
        "provenance": "prospective current-source baseline; no historical evaluation receipts reused",
        "input_hashes": {name: _hash(ROOT / name) for name in planner.L0_PROTECTED_INPUT_PATHS},
        "artifact_hashes": {"pool-policy.json": _hash(planner.L0_POOL_POLICY_PATH)},
    }
    baseline_path = destination / "baseline-manifest.json"
    _write(baseline_path, baseline)
    scenario_source = iteration.with_name("scenario-manifest.json")
    scenario = _read(scenario_source)
    scenario["baseline_manifest_sha256"] = _hash(baseline_path)
    scenario["scenarios"][0]["id"] = experiment_id
    _write(destination / "scenario-manifest.json", scenario)
    projection = planner.build_projection_report(scenario, target=150000, baseline_manifest_path=baseline_path)
    _write(destination / "projection-report.json", projection)
    prepared = copy_input(iteration, catalog=True)
    candidate = _read(prepared)
    candidate["catalog_id"] = experiment_id
    candidate["scenario_binding"] = {
        "scenario_manifest_sha256": projection["scenario_manifest_sha256"],
        "projection_report_sha256": hashlib.sha256(canonical_json_bytes(projection)).hexdigest(),
        "scenario_id": experiment_id,
        "baseline_manifest_sha256": _hash(baseline_path),
    }
    candidate_path = destination / "candidate-iteration.json"
    _write(candidate_path, candidate)
    analysis = analyze_candidate_catalog(load_candidate_catalog(candidate_path), scenario_manifest=scenario,
                                         projection_report=projection, baseline_manifest_path=baseline_path)
    _write(destination / "analysis-report.json", analysis)
    receipt = {
        "schema_version": "variation-candidate-preparation/v1", "experiment_id": experiment_id,
        "purpose": "new prospective authoring; not historical replay or quality approval",
        "origins": sorted(origins, key=lambda item: item["source_path"]),
        "scenario_origin": {"path": scenario_source.relative_to(ROOT).as_posix(), "sha256": _hash(scenario_source)},
        "candidate_iteration_sha256": _hash(candidate_path),
        "baseline_manifest_sha256": _hash(baseline_path),
        "structural_status": analysis["structural_status"],
    }
    _write(destination / "preparation.json", receipt)
    if analysis["structural_status"] == "pass":
        _write(destination / "snapshot-plan.json", build_prepared_snapshot_plan(destination))
    return receipt


def build_prepared_snapshot_plan(destination: Path, *, quality_contract: Path | None = None) -> dict:
    """Bind a prepared draft to current source bytes immediately before materializing."""
    return build_snapshot_plan(
        candidate_iteration=destination / "candidate-iteration.json",
        scenario_manifest=destination / "scenario-manifest.json",
        projection_report=destination / "projection-report.json",
        analysis_report=destination / "analysis-report.json",
        baseline_manifest_path=destination / "baseline-manifest.json",
        baseline_prompt_mode="active", quality_contract=quality_contract, source_root=ROOT,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iteration", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    args = parser.parse_args()
    receipt = prepare_candidate(iteration=args.iteration, destination=args.destination, experiment_id=args.experiment_id)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["structural_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
