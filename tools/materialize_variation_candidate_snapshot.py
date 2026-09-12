from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.analyze_variation_candidates import analyze_candidate_catalog, load_candidate_catalog
from tools.plan_variation_prompt_schedule import validate_prompt_schedule
from tools.variation_quality_contract import validate_variation_quality_contract
from tools.prompt_quality_loop import _source_files, build_source_manifest
from tools.build_prompt_quality_confirmation import _sanitized_environment, _verification_input_entries
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


PLAN_SCHEMA_VERSION = "variation-candidate-snapshot-plan/v1"
MANIFEST_SCHEMA_VERSION = "variation-candidate-snapshot/v1"
MATERIALIZER_VERSION = "variation-snapshot-materializer/v1"
EXTRA_RUNTIME_FILES = (
    "prompts.jsonl",
    "mood_map.json",
    "templates.txt",
    "workflow_samples.json",
    "assets/calc_variations.py",
    "assets/compatibility_review.csv",
)
MUTABLE_CANDIDATE_FILES = frozenset(
    {
        "prompts.jsonl",
        "vocab/data/action_pools.json",
        "vocab/data/background_packs.json",
        "vocab/data/location_axis_profiles.json",
        "vocab/data/scene_compatibility.json",
        "vocab/data/variation_scope.json",
        "vocab/source/action_pools/_manifest.json",
        "assets/compatibility_review.csv",
    }
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _repo_relative(path: Path, root: Path = ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise WorkflowValidationError("snapshot_input_outside_repo", "snapshot input must be inside repository") from exc


def _bound_input(path: Path, root: Path = ROOT) -> dict:
    return {"path": _repo_relative(path, root), "sha256": _sha256_path(path)}


def build_snapshot_plan(
    *,
    candidate_iteration: Path,
    scenario_manifest: Path,
    projection_report: Path,
    analysis_report: Path,
    prompt_schedule: Path | None = None,
    quality_contract: Path | None = None,
    baseline_manifest_path: Path | None = None,
    baseline_prompt_mode: str = "synthetic",
    source_root: Path = ROOT,
) -> dict:
    if baseline_prompt_mode not in {"synthetic", "active"}:
        raise WorkflowValidationError("invalid_baseline_prompt_mode", "baseline prompt mode must be synthetic or active")
    source_root = source_root.resolve()
    iteration = candidate_iteration.resolve()
    scenario_path = scenario_manifest.resolve()
    projection_path = projection_report.resolve()
    analysis_path = analysis_report.resolve()
    schedule_path = prompt_schedule.resolve() if prompt_schedule is not None else None
    quality_contract_path = quality_contract.resolve() if quality_contract is not None else None
    if schedule_path is not None and quality_contract_path is not None:
        raise WorkflowValidationError(
            "snapshot_quality_surface_conflict",
            "prompt schedule and non-selected quality contract are mutually exclusive",
        )
    catalog = load_candidate_catalog(iteration)
    scenario = _read_json(scenario_path)
    projection = _read_json(projection_path)
    tracked_analysis = _read_json(analysis_path)
    fresh_analysis = analyze_candidate_catalog(
        catalog, scenario_manifest=scenario, projection_report=projection,
        baseline_manifest_path=baseline_manifest_path,
    )
    if canonical_json_bytes(fresh_analysis) != canonical_json_bytes(tracked_analysis):
        raise WorkflowValidationError(
            "candidate_analysis_drift",
            "tracked candidate analysis does not match current inputs",
        )
    if (
        tracked_analysis.get("structural_status") != "pass"
        or not tracked_analysis.get("eligible_for_prompt_evaluation")
        or tracked_analysis.get("promotion_ready")
        or tracked_analysis.get("prompt_quality", {}).get("status") != "not_evaluated"
    ):
        raise WorkflowValidationError(
            "candidate_not_snapshot_eligible",
            "candidate must be structurally eligible and prompt-quality unevaluated",
        )
    subjects = sorted(str(item["id"]) for item in catalog["subjects"])
    locations = sorted(str(item["id"]) for item in catalog["locations"])
    inputs = {
        "candidate_iteration": _bound_input(iteration, source_root),
        "scenario_manifest": _bound_input(scenario_path, source_root),
        "projection_report": _bound_input(projection_path, source_root),
        "analysis_report": _bound_input(analysis_path, source_root),
    }
    if baseline_manifest_path is not None:
        inputs["baseline_manifest"] = _bound_input(baseline_manifest_path, source_root)
    schedule_hash = None
    quality_contract_hash = None
    if schedule_path is not None:
        schedule = _read_json(schedule_path)
        validate_prompt_schedule(schedule, source_root=source_root)
        if schedule.get("effective_catalog_sha256") != _hash_value(catalog):
            raise WorkflowValidationError(
                "coverage_schedule_catalog_mismatch",
                "prompt coverage schedule does not bind the effective candidate catalog",
            )
        if schedule.get("expected_subjects") != subjects or schedule.get("expected_locations") != locations:
            raise WorkflowValidationError(
                "coverage_schedule_candidate_mismatch",
                "prompt coverage schedule candidate identities drifted",
            )
        inputs["prompt_schedule"] = _bound_input(schedule_path, source_root)
        schedule_hash = schedule.get("schedule_sha256")
    if quality_contract_path is not None:
        quality_value = _read_json(quality_contract_path)
        validate_variation_quality_contract(quality_value, repository_root=source_root)
        if quality_value.get("effective_catalog_sha256") != _hash_value(catalog):
            raise WorkflowValidationError(
                "snapshot_quality_catalog_mismatch",
                "non-selected quality contract does not bind the effective catalog",
            )
        inputs["quality_contract"] = _bound_input(quality_contract_path, source_root)
        quality_contract_hash = quality_value.get("contract_sha256")
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "snapshot_id": str(catalog["catalog_id"]),
        "materializer_version": MATERIALIZER_VERSION,
        **({"baseline_prompt_mode": "active"} if baseline_prompt_mode == "active" else {}),
        "inputs": inputs,
        "prompt_schedule_sha256": schedule_hash,
        "quality_contract_sha256": quality_contract_hash,
        "effective_catalog_sha256": _hash_value(catalog),
        "active_source_tree_sha256": build_source_manifest(source_root)["source_tree_hash"],
        "active_source_content_sha256": _hash_value(_manifest_entries(source_root)),
        "candidate_ids": {"subjects": subjects, "locations": locations},
        "declared_delta": {
            "subjects": len(subjects),
            "locations": len(locations),
            "action_pools": len(locations),
            "actions_per_location": sorted(
                {
                    len(item["action_plan"]["direct_actions"])
                    + sum(int(ref["take"]) for ref in item["action_plan"]["family_refs"])
                    for item in catalog["locations"]
                }
            ),
        },
        "projection_target": int(_read_json(projection_path).get("target", 0)),
        "projected_base_variations": int(
            _read_json(projection_path).get("hypothetical_scenarios", [{}])[0].get("projected_base_variations", 0)
        ),
        "mutable_candidate_files": sorted(MUTABLE_CANDIDATE_FILES),
    }


def _validate_plan_inputs(plan: Mapping[str, Any], source_root: Path) -> None:
    if plan.get("schema_version") != PLAN_SCHEMA_VERSION:
        raise WorkflowValidationError("invalid_snapshot_plan", "snapshot plan schema is unsupported")
    inputs = plan.get("inputs", {})
    required_inputs = {"candidate_iteration", "scenario_manifest", "projection_report", "analysis_report"}
    allowed_inputs = required_inputs | {"prompt_schedule", "quality_contract", "baseline_manifest"}
    if not isinstance(inputs, Mapping) or not required_inputs.issubset(inputs) or not set(inputs).issubset(allowed_inputs):
        raise WorkflowValidationError(
            "invalid_snapshot_inputs",
            "snapshot plan must bind the four L2 inputs and at most one prompt schedule",
            missing=sorted(required_inputs - set(inputs) if isinstance(inputs, Mapping) else required_inputs),
            extra=sorted(set(inputs) - allowed_inputs if isinstance(inputs, Mapping) else []),
        )
    resolved_inputs: dict[str, Path] = {}
    for name, binding in inputs.items():
        if not isinstance(binding, Mapping):
            raise WorkflowValidationError("invalid_snapshot_input", "snapshot input binding must be an object", name=name)
        path = (source_root / str(binding.get("path", ""))).resolve()
        try:
            path.relative_to(source_root.resolve())
        except ValueError as exc:
            raise WorkflowValidationError("snapshot_input_outside_repo", "snapshot input escapes source root") from exc
        if not path.is_file() or _sha256_path(path) != binding.get("sha256"):
            raise WorkflowValidationError("snapshot_input_hash_mismatch", "snapshot input hash drifted", name=name)
        resolved_inputs[name] = path
    expected_plan = build_snapshot_plan(
        candidate_iteration=resolved_inputs["candidate_iteration"],
        scenario_manifest=resolved_inputs["scenario_manifest"],
        projection_report=resolved_inputs["projection_report"],
        analysis_report=resolved_inputs["analysis_report"],
        prompt_schedule=resolved_inputs.get("prompt_schedule"),
        quality_contract=resolved_inputs.get("quality_contract"),
        baseline_manifest_path=resolved_inputs.get("baseline_manifest"),
        baseline_prompt_mode=str(plan.get("baseline_prompt_mode", "synthetic")),
        source_root=source_root,
    )
    if canonical_json_bytes(expected_plan) != canonical_json_bytes(dict(plan)):
        raise WorkflowValidationError(
            "snapshot_plan_derived_field_mismatch",
            "snapshot plan derived fields do not match its bound inputs",
        )


def _copy_filtered_source(source_root: Path, destination_root: Path) -> None:
    support = set(source_root.glob("*.md"))
    support.update(path for path in (source_root / "docs").rglob("*") if path.is_file())
    support.update(path for path in (source_root / "assets").glob("*") if path.is_file())
    support.update(
        source_root / relative for relative in (
            "pytest.ini", ".gitattributes", ".omx/ultragoal/goals.json", ".omx/ultragoal/ledger.jsonl",
        ) if (source_root / relative).is_file()
    )
    for source in set(_source_files(source_root)) | support:
        if source.is_symlink() or not source.resolve().is_relative_to(source_root.resolve()):
            raise WorkflowValidationError("snapshot_symlink_rejected", "source snapshot cannot include symlinks")
        relative = source.relative_to(source_root)
        destination = destination_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    for relative_value in EXTRA_RUNTIME_FILES:
        source = source_root / relative_value
        if source.is_file():
            destination = destination_root / relative_value
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    _write_json(destination_root / ".verification-inputs.json", {
        "schema_version": "snapshot-verification-inputs/v1",
        "files": sorted(path.relative_to(source_root).as_posix() for path in support),
    })


def _candidate_pairs(catalog: Mapping[str, Any]) -> list[tuple[Mapping[str, Any], Mapping[str, Any]]]:
    subjects = list(catalog["subjects"])
    locations = list(catalog["locations"])
    pairs = []
    for index, subject in enumerate(subjects):
        compatible = [
            location
            for location in locations
            if location.get("universal") or set(subject.get("tags", [])) & set(location.get("compatibility_tags", []))
        ]
        if not compatible:
            raise WorkflowValidationError(
                "snapshot_subject_uncovered",
                "candidate subject has no candidate location",
                subject=subject.get("id"),
            )
        pairs.append((subject, compatible[index % len(compatible)]))
    return pairs


def _prompt_rows(catalog: Mapping[str, Any], *, candidate: bool, count: int = 80) -> list[dict]:
    pairs = _candidate_pairs(catalog)
    rows = []
    for index in range(count):
        subject, location = pairs[index % len(pairs)]
        if candidate:
            subject_id = str(subject["id"])
            location_id = str(location["id"])
            costume = str(subject["default_costume"])
            expanded_actions = list(location["action_plan"]["direct_actions"])
            action = str(expanded_actions[index % len(expanded_actions)]["text"])
        else:
            subject_id = str(subject["utility_claim"]["distinct_from"][0])
            location_id = str(location["utility_claim"]["distinct_from"][0])
            costume = "casual"
            action = "standing and checking what needs attention next"
        rows.append(
            {
                "subj": subject_id,
                "costume": costume,
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


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.write_bytes(b"".join(canonical_json_bytes(dict(row)) for row in rows))


def _materialize_candidate_data(candidate_root: Path, catalog: Mapping[str, Any]) -> None:
    scene_path = candidate_root / "vocab/data/scene_compatibility.json"
    scene = _read_json(scene_path)
    for subject in catalog["subjects"]:
        scene.setdefault("characters", {})[subject["id"]] = {
            "tags": list(subject["tags"]),
            "default_costume": subject["default_costume"],
        }
    for location in catalog["locations"]:
        location_id = str(location["id"])
        if location_id not in scene.setdefault("locations", []):
            scene["locations"].append(location_id)
        for tag in location["compatibility_tags"]:
            values = scene.setdefault("loc_tags", {}).setdefault(tag, [])
            if location_id not in values:
                values.append(location_id)
        if location.get("universal") and location_id not in scene.setdefault("universal_locs", []):
            scene["universal_locs"].append(location_id)
        daily = scene.setdefault("daily_life_locs", [])
        if location_id not in daily:
            daily.append(location_id)
    _write_json(scene_path, scene)

    packs_path = candidate_root / "vocab/data/background_packs.json"
    packs = _read_json(packs_path)
    for location in catalog["locations"]:
        location_id = str(location["id"])
        terms = list(location["environment_terms"])
        background_pack = location.get("background_pack")
        if isinstance(background_pack, Mapping):
            packs[location_id] = {
                "label": location_id.replace("_", " "),
                **copy.deepcopy(dict(background_pack)),
            }
        else:
            packs[location_id] = {
                "label": location_id.replace("_", " "),
                "environment": [terms[0]],
                "core": terms[1:] or [terms[0]],
                "texture": [],
                "props": [],
                "fx": [],
                "time": [],
                "crowd": [],
                "weather": [],
                "aliases": [],
                "lighting": ["natural ambient light"],
            }
    _write_json(packs_path, packs)

    axis_path = candidate_root / "vocab/data/location_axis_profiles.json"
    axes = _read_json(axis_path)
    profiles = axes.setdefault("profiles", {})
    neutral = {name: 0.5 for name in axes.get("axes", [])}
    neutral["weather_intensity"] = 0.0
    for location in catalog["locations"]:
        comparator = str(location["utility_claim"]["distinct_from"][0])
        profiles[location["id"]] = copy.deepcopy(profiles.get(comparator, {"vector": neutral}))
    _write_json(axis_path, axes)

    action_manifest_path = candidate_root / "vocab/source/action_pools/_manifest.json"
    action_manifest = _read_json(action_manifest_path)
    order = action_manifest.setdefault("location_order", [])
    for location in catalog["locations"]:
        location_id = str(location["id"])
        if location_id not in order:
            order.append(location_id)
        _write_json(
            candidate_root / f"vocab/source/action_pools/{location_id}.json",
            {
                "location": location_id,
                "actions": list(location["action_plan"]["direct_actions"]),
                "families": list(location["action_plan"]["family_refs"]),
            },
        )
    _write_json(action_manifest_path, action_manifest)

    scope_path = candidate_root / "vocab/data/variation_scope.json"
    scope = _read_json(scope_path)
    generation = scope.setdefault("compatibility_review_generation", {})
    seeds = generation.setdefault("existing_prompt_rows", [])
    for line in (candidate_root / "prompts.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            prompt = json.loads(line)
            seed = {key: str(prompt.get(key, "")) for key in ("subj", "loc", "costume")}
            if seed not in seeds:
                seeds.append(seed)
    for subject in catalog["subjects"]:
        if subject["id"] not in scope["variation_subjects"]:
            scope["variation_subjects"].append(subject["id"])
    for location in catalog["locations"]:
        if location["id"] not in scope["variation_locations"]:
            scope["variation_locations"].append(location["id"])
    _write_json(scope_path, scope)


def _run_snapshot_command(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        [sys.executable, *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_sanitized_environment(root),
        check=False,
    )
    if completed.returncode != 0:
        raise WorkflowValidationError(
            "snapshot_build_command_failed",
            "snapshot build command failed",
            command=list(arguments),
            stdout=completed.stdout[-2000:],
            stderr=completed.stderr[-2000:],
        )
    return completed.stdout


def _manifest_entries(root: Path) -> dict[str, str]:
    entries = {
        entry["path"]: entry["sha256"]
        for entry in build_source_manifest(root)["entries"]
    }
    for relative_value in EXTRA_RUNTIME_FILES:
        path = root / relative_value
        if path.is_file():
            entries[relative_value] = _sha256_path(path)
    entries.update(_verification_input_entries(root))
    return dict(sorted(entries.items()))


def materialize_candidate_snapshots(
    plan: Mapping[str, Any],
    *,
    source_root: Path,
    destination_root: Path,
) -> dict:
    source_root = source_root.resolve()
    destination_root = destination_root.resolve()
    _validate_plan_inputs(plan, source_root)
    try:
        destination_root.relative_to(source_root)
    except ValueError as exc:
        raise WorkflowValidationError(
            "snapshot_destination_outside_repo",
            "snapshot destination must be beneath the repository artifact tree",
        ) from exc
    expected_parent = (source_root / "assets/results").resolve()
    try:
        destination_root.relative_to(expected_parent)
    except ValueError as exc:
        raise WorkflowValidationError(
            "snapshot_destination_outside_artifacts",
            "snapshot destination must be beneath assets/results",
        ) from exc
    if destination_root.exists():
        raise WorkflowValidationError("snapshot_destination_exists", "snapshot destination already exists")

    active_before = _hash_value(_manifest_entries(source_root))
    temp_root = destination_root.with_name(f"{destination_root.name}.tmp-{uuid.uuid4().hex}")
    temp_root.mkdir(parents=True)
    try:
        baseline_root = temp_root / "baseline-root"
        candidate_root = temp_root / "candidate-root"
        _copy_filtered_source(source_root, baseline_root)
        _copy_filtered_source(source_root, candidate_root)
        iteration_path = source_root / plan["inputs"]["candidate_iteration"]["path"]
        catalog = load_candidate_catalog(iteration_path)
        baseline_prompt_rows = (
            [json.loads(line) for line in (baseline_root / "prompts.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
            if plan.get("baseline_prompt_mode") == "active" else _prompt_rows(catalog, candidate=False)
        )
        candidate_prompt_rows = _prompt_rows(catalog, candidate=True)
        if "prompt_schedule" in plan["inputs"]:
            schedule = _read_json(source_root / plan["inputs"]["prompt_schedule"]["path"])
            validate_prompt_schedule(schedule, source_root=source_root)
            candidate_prompt_rows = list(schedule["candidate_rows"])
        if plan.get("baseline_prompt_mode") != "active":
            _write_jsonl(baseline_root / "prompts.jsonl", baseline_prompt_rows)
        _materialize_candidate_data(candidate_root, catalog)
        _write_jsonl(candidate_root / "prompts.jsonl", candidate_prompt_rows)

        _run_snapshot_command(candidate_root, "tools/build_action_pools.py", "--write")
        _run_snapshot_command(
            candidate_root,
            "tools/build_compatibility_review.py",
            "--write",
            "--output",
            "assets/compatibility_review.csv",
            "--allow-drift",
        )
        metrics = json.loads(_run_snapshot_command(candidate_root, "assets/calc_variations.py", "--json"))
        scope_path = candidate_root / "vocab/data/variation_scope.json"
        scope = _read_json(scope_path)
        scope["expected_metrics"] = {
            "unique_subjects": metrics["base"]["unique_subjects"],
            "unique_locations": metrics["base"]["unique_locations"],
            "row_count": metrics["base"]["row_count"],
            "total_base_variations": metrics["base"]["total_base_variations"],
        }
        _write_json(scope_path, scope)
        _run_snapshot_command(candidate_root, "tools/check_variation_scope.py")
        _run_snapshot_command(candidate_root, "tools/build_action_pools.py", "--check")
        prompt_schedule_verification = None
        if "prompt_schedule" in plan["inputs"]:
            expected_prompt_hash = schedule.get("candidate_prompts_jsonl_sha256")
            if _sha256_path(candidate_root / "prompts.jsonl") != expected_prompt_hash:
                raise WorkflowValidationError(
                    "coverage_schedule_prompt_hash_mismatch",
                    "materialized candidate prompts do not match the bound coverage schedule",
                )
            if schedule.get("schema_version") == "variation-prompt-final-coverage-schedule/v2":
                prompt_schedule_verification = json.loads(
                    _run_snapshot_command(
                        candidate_root,
                        "tools/plan_variation_final_coverage.py",
                        "--verify-schedule",
                        str(source_root / plan["inputs"]["prompt_schedule"]["path"]),
                        "--repository-root",
                        str(source_root),
                    )
                )

        baseline_entries = _manifest_entries(baseline_root)
        candidate_entries = _manifest_entries(candidate_root)
        changed = sorted(
            path
            for path in set(baseline_entries) | set(candidate_entries)
            if baseline_entries.get(path) != candidate_entries.get(path)
        )
        allowed = set(MUTABLE_CANDIDATE_FILES) | {
            f"vocab/source/action_pools/{location}.json" for location in plan["candidate_ids"]["locations"]
        }
        undeclared = sorted(set(changed) - allowed)
        if undeclared:
            raise WorkflowValidationError(
                "snapshot_undeclared_delta",
                "candidate snapshot changed files outside the allowlist",
                files=undeclared,
            )
        manifest = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "snapshot_id": plan["snapshot_id"],
            "materializer_version": MATERIALIZER_VERSION,
            "plan_sha256": _hash_value(dict(plan)),
            "baseline_source_tree_sha256": build_source_manifest(baseline_root)["source_tree_hash"],
            "candidate_source_tree_sha256": build_source_manifest(candidate_root)["source_tree_hash"],
            "baseline_snapshot_content_sha256": _hash_value(baseline_entries),
            "candidate_snapshot_content_sha256": _hash_value(candidate_entries),
            "active_source_before_sha256": active_before,
            "active_source_after_sha256": _hash_value(_manifest_entries(source_root)),
            "active_source_unchanged": active_before == _hash_value(_manifest_entries(source_root)),
            "declared_delta": copy.deepcopy(plan["declared_delta"]),
            "candidate_ids": copy.deepcopy(plan["candidate_ids"]),
            "changed_files": changed,
            "candidate_metrics": metrics["base"],
            "quantitative_gate": {
                "target": int(plan["projection_target"]),
                "projected_base_variations": int(plan["projected_base_variations"]),
                "realized_base_variations": int(metrics["base"]["total_base_variations"]),
                "projection_delta": int(metrics["base"]["total_base_variations"])
                - int(plan["projected_base_variations"]),
                "target_gap": int(plan["projection_target"])
                - int(metrics["base"]["total_base_variations"]),
                "target_met": int(metrics["base"]["total_base_variations"])
                >= int(plan["projection_target"]),
            },
            "prompt_rows": {
                "baseline": len(baseline_prompt_rows),
                "candidate": len(candidate_prompt_rows),
            },
            "prompt_schedule_sha256": plan.get("prompt_schedule_sha256"),
            "quality_contract_sha256": plan.get("quality_contract_sha256"),
            "prompt_schedule_verification": prompt_schedule_verification,
        }
        manifest["state"] = "SNAPSHOT_READY" if manifest["quantitative_gate"]["target_met"] else "REJECTED"
        manifest["prompt_generation_allowed"] = bool(manifest["quantitative_gate"]["target_met"])
        manifest["errors"] = [] if manifest["quantitative_gate"]["target_met"] else [
            {
                "code": "candidate_snapshot_target_not_met",
                "message": "materialized candidate snapshot does not meet its bound stage target",
                "details": copy.deepcopy(manifest["quantitative_gate"]),
            }
        ]
        if not manifest["active_source_unchanged"]:
            raise WorkflowValidationError("active_source_changed", "active source changed during snapshot materialization")
        _write_json(temp_root / "snapshot-plan.json", plan)
        _write_json(temp_root / "snapshot-manifest.json", manifest)
        temp_root.replace(destination_root)
        return manifest
    except Exception:
        if temp_root.exists():
            shutil.rmtree(temp_root)
        raise


def validate_snapshot_manifest(
    snapshot_root: Path,
    manifest: Mapping[str, Any],
    *,
    source_root: Path = ROOT,
) -> dict:
    snapshot_root = snapshot_root.resolve()
    source_root = source_root.resolve()
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise WorkflowValidationError("invalid_snapshot_manifest", "snapshot manifest schema is unsupported")
    baseline_root = snapshot_root / "baseline-root"
    candidate_root = snapshot_root / "candidate-root"
    plan_path = snapshot_root / "snapshot-plan.json"
    try:
        stored_plan = _read_json(plan_path)
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowValidationError(
            "snapshot_plan_unreadable",
            "stored snapshot plan is unreadable",
            exception_type=type(exc).__name__,
        ) from exc
    if not isinstance(stored_plan, dict) or _hash_value(stored_plan) != manifest.get("plan_sha256"):
        raise WorkflowValidationError("snapshot_plan_hash_mismatch", "stored snapshot plan hash drifted")
    _validate_plan_inputs(stored_plan, source_root)
    baseline_hash = build_source_manifest(baseline_root)["source_tree_hash"]
    candidate_hash = build_source_manifest(candidate_root)["source_tree_hash"]
    if baseline_hash != manifest.get("baseline_source_tree_sha256"):
        raise WorkflowValidationError("baseline_snapshot_hash_mismatch", "baseline snapshot hash drifted")
    if candidate_hash != manifest.get("candidate_source_tree_sha256"):
        raise WorkflowValidationError("candidate_snapshot_hash_mismatch", "candidate snapshot hash drifted")
    baseline_content = _hash_value(_manifest_entries(baseline_root))
    candidate_content = _hash_value(_manifest_entries(candidate_root))
    if baseline_content != manifest.get("baseline_snapshot_content_sha256"):
        raise WorkflowValidationError("baseline_snapshot_content_mismatch", "baseline snapshot content hash drifted")
    if candidate_content != manifest.get("candidate_snapshot_content_sha256"):
        raise WorkflowValidationError("candidate_snapshot_content_mismatch", "candidate snapshot content hash drifted")
    baseline_entries = _manifest_entries(baseline_root)
    candidate_entries = _manifest_entries(candidate_root)
    changed = sorted(
        path
        for path in set(baseline_entries) | set(candidate_entries)
        if baseline_entries.get(path) != candidate_entries.get(path)
    )
    allowed = set(stored_plan["mutable_candidate_files"]) | {
        f"vocab/source/action_pools/{location}.json"
        for location in stored_plan["candidate_ids"]["locations"]
    }
    undeclared = sorted(set(changed) - allowed)
    if undeclared or changed != manifest.get("changed_files"):
        raise WorkflowValidationError(
            "snapshot_changed_files_mismatch",
            "snapshot changed-file evidence drifted",
            undeclared=undeclared,
        )
    metrics = json.loads(_run_snapshot_command(candidate_root, "assets/calc_variations.py", "--json"))["base"]
    quantitative_gate = {
        "target": int(stored_plan["projection_target"]),
        "projected_base_variations": int(stored_plan["projected_base_variations"]),
        "realized_base_variations": int(metrics["total_base_variations"]),
        "projection_delta": int(metrics["total_base_variations"])
        - int(stored_plan["projected_base_variations"]),
        "target_gap": int(stored_plan["projection_target"]) - int(metrics["total_base_variations"]),
        "target_met": int(metrics["total_base_variations"]) >= int(stored_plan["projection_target"]),
    }
    expected_state = "SNAPSHOT_READY" if quantitative_gate["target_met"] else "REJECTED"
    expected_prompt_allowed = bool(quantitative_gate["target_met"])
    expected_errors = [] if quantitative_gate["target_met"] else [
        {
            "code": "candidate_snapshot_target_not_met",
            "message": "materialized candidate snapshot does not meet its bound stage target",
            "details": quantitative_gate,
        }
    ]
    active_content = _hash_value(_manifest_entries(source_root))
    prompt_rows = {
        "baseline": len((baseline_root / "prompts.jsonl").read_text(encoding="utf-8").splitlines()),
        "candidate": len((candidate_root / "prompts.jsonl").read_text(encoding="utf-8").splitlines()),
    }
    if "prompt_schedule" in stored_plan["inputs"]:
        schedule = _read_json(source_root / stored_plan["inputs"]["prompt_schedule"]["path"])
        validate_prompt_schedule(schedule, source_root=source_root)
        if (
            schedule.get("schedule_sha256") != stored_plan.get("prompt_schedule_sha256")
            or schedule.get("schedule_sha256") != manifest.get("prompt_schedule_sha256")
            or _sha256_path(candidate_root / "prompts.jsonl")
            != schedule.get("candidate_prompts_jsonl_sha256")
        ):
            raise WorkflowValidationError(
                "coverage_schedule_prompt_hash_mismatch",
                "candidate prompt file no longer matches its bound coverage schedule",
            )
        if schedule.get("schema_version") == "variation-prompt-final-coverage-schedule/v2":
            prompt_schedule_verification = json.loads(
                _run_snapshot_command(
                    candidate_root,
                    "tools/plan_variation_final_coverage.py",
                    "--verify-schedule",
                    str(source_root / stored_plan["inputs"]["prompt_schedule"]["path"]),
                    "--repository-root",
                    str(source_root),
                )
            )
        else:
            prompt_schedule_verification = None
    else:
        prompt_schedule_verification = None
    expected_fields = {
        "snapshot_id": stored_plan["snapshot_id"],
        "materializer_version": MATERIALIZER_VERSION,
        "declared_delta": stored_plan["declared_delta"],
        "candidate_ids": stored_plan["candidate_ids"],
        "candidate_metrics": metrics,
        "quantitative_gate": quantitative_gate,
        "prompt_rows": prompt_rows,
        "prompt_schedule_sha256": stored_plan.get("prompt_schedule_sha256"),
        "quality_contract_sha256": stored_plan.get("quality_contract_sha256"),
        "prompt_schedule_verification": prompt_schedule_verification,
        "state": expected_state,
        "prompt_generation_allowed": expected_prompt_allowed,
        "errors": expected_errors,
        "active_source_before_sha256": stored_plan["active_source_content_sha256"],
        "active_source_after_sha256": active_content,
        "active_source_unchanged": stored_plan["active_source_content_sha256"] == active_content,
    }
    mismatched = [
        field
        for field, expected in expected_fields.items()
        if canonical_json_bytes(manifest.get(field)) != canonical_json_bytes(expected)
    ]
    if mismatched:
        raise WorkflowValidationError(
            "snapshot_decision_field_mismatch",
            "snapshot decision or evidence fields drifted",
            fields=mismatched,
        )
    return {
        "baseline_source_tree_sha256": baseline_hash,
        "candidate_source_tree_sha256": candidate_hash,
        "baseline_snapshot_content_sha256": baseline_content,
        "candidate_snapshot_content_sha256": candidate_content,
        "status": "pass",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize isolated baseline/candidate variation snapshots.")
    parser.add_argument("--candidate-iteration", required=True)
    parser.add_argument("--scenario-file", required=True)
    parser.add_argument("--projection-report", required=True)
    parser.add_argument("--analysis-report", required=True)
    parser.add_argument("--prompt-schedule")
    parser.add_argument("--quality-contract")
    parser.add_argument("--baseline-manifest", type=Path)
    parser.add_argument("--baseline-prompt-mode", choices=("synthetic", "active"), default="synthetic")
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    try:
        plan = build_snapshot_plan(
            candidate_iteration=ROOT / args.candidate_iteration,
            scenario_manifest=ROOT / args.scenario_file,
            projection_report=ROOT / args.projection_report,
            analysis_report=ROOT / args.analysis_report,
            prompt_schedule=ROOT / args.prompt_schedule if args.prompt_schedule else None,
            quality_contract=ROOT / args.quality_contract if args.quality_contract else None,
            baseline_manifest_path=args.baseline_manifest,
            baseline_prompt_mode=args.baseline_prompt_mode,
        )
        manifest = materialize_candidate_snapshots(
            plan,
            source_root=ROOT,
            destination_root=ROOT / args.output_root,
        )
    except (OSError, ValueError, json.JSONDecodeError, WorkflowValidationError) as exc:
        envelope = exc.to_envelope() if isinstance(exc, WorkflowValidationError) else WorkflowValidationError(
            "snapshot_materialization_failed",
            "candidate snapshot materialization failed",
            exception_type=type(exc).__name__,
        ).to_envelope()
        sys.stderr.buffer.write(canonical_json_bytes(envelope))
        return 2
    sys.stdout.buffer.write(canonical_json_bytes(manifest))
    return 0 if manifest.get("prompt_generation_allowed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
