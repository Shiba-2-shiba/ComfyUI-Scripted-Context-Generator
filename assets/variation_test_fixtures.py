"""Disposable regression inputs; historical experiment evidence stays immutable.

The old experiments bind a developer's worktree bytes and ignored run outputs.
Tests bind current code to a frozen arithmetic baseline and generate prerequisites.
The production validators run normally against those explicit test bindings.
"""

import atexit
import hashlib
import json
import shutil
import tempfile
from contextlib import ExitStack, contextmanager
from functools import lru_cache
from pathlib import Path
from unittest.mock import patch

from tools import analyze_variation_candidates as analyzer
from tools import materialize_variation_candidate_snapshot as materializer
from tools import plan_variation_target as planner
from tools.workflow_prompt_runner import canonical_json_bytes


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BASELINE_FIXTURE = REPOSITORY_ROOT / "assets/fixtures/variation_baseline"
EXPERIMENTS = Path("docs/variation_expansion/experiments")
BASELINE_PATH = EXPERIMENTS / "v150-planner-l0/manifest.json"
ITERATION_TWO = EXPERIMENTS / "v150-candidate-l2-iteration-002"
ITERATION_FOUR = EXPERIMENTS / "v150-candidate-shape-iteration-004"
FIXTURE_ITERATIONS = (
    EXPERIMENTS / "v150-candidate-l2",
    ITERATION_TWO,
    EXPERIMENTS / "v150-candidate-shape-iteration-003",
    ITERATION_FOUR,
    EXPERIMENTS / "v150-candidate-shape-iteration-019",
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hash_value(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))
    return value


def seal(value, field):
    value.pop(field, None)
    value[field] = hash_value(value)
    return value


@contextmanager
def fixture_environment(root):
    """Select fixture data without replacing any validator or computed result."""
    import location_service
    import scene_service
    from tools import (build_action_pools, build_compatibility_review, check_variation_scope,
                       model_variation_candidate_contributions, plan_variation_prompt_schedule)

    services = (location_service, scene_service)
    cached_loaders = {value for module in services for value in vars(module).values()
                      if callable(getattr(value, "cache_clear", None))}
    for loader in cached_loaders:
        loader.cache_clear()
    with ExitStack() as stack:
        # Clear fixture values on exit, including when a test fails.
        for loader in cached_loaders:
            stack.callback(loader.cache_clear)
        for module in services:
            stack.enter_context(patch.object(module, "DATA_DIR", str(root / "vocab/data")))
        for module in (planner, analyzer, materializer, model_variation_candidate_contributions,
                       plan_variation_prompt_schedule, build_action_pools, build_compatibility_review,
                       check_variation_scope):
            stack.enter_context(patch.object(module, "ROOT", root))
        stack.enter_context(patch.object(check_variation_scope.load_variation_scope, "__defaults__",
                                        (root / "vocab/data/variation_scope.json",)))
        stack.enter_context(patch.object(build_compatibility_review, "PROMPTS_PATH", root / "prompts.jsonl"))
        stack.enter_context(patch.object(build_compatibility_review._load_prompt_rows, "__defaults__",
                                        (root / "prompts.jsonl",)))
        source_dir = root / "vocab/source/action_pools"
        for module, name, path in (
            (analyzer, "ACTION_MANIFEST_PATH", source_dir / "_manifest.json"),
            (analyzer, "ACTION_SOURCE_DIR", source_dir),
            (build_action_pools, "SOURCE_DIR", source_dir),
            (build_action_pools, "SHARED_FAMILIES_PATH", source_dir / "_shared_families.json"),
        ):
            stack.enter_context(patch.object(module, name, path))
        stack.enter_context(patch.object(planner, "L0_BASELINE_MANIFEST_PATH", root / BASELINE_PATH))
        for module in (planner, analyzer):
            stack.enter_context(patch.object(module, "L0_POOL_POLICY_PATH", root / EXPERIMENTS / "v150-planner-l0/pool-policy.json"))
        yield


def _copy_sources(root):
    materializer._copy_filtered_source(REPOSITORY_ROOT, root)
    for source in BASELINE_FIXTURE.rglob("*"):
        if source.is_file() and source.name != "README.md":
            destination = root / source.relative_to(BASELINE_FIXTURE)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    source_dir = root / "vocab/source/action_pools"
    baseline_locations = set(read_json(source_dir / "_manifest.json")["location_order"])
    for path in source_dir.glob("*.json"):
        if not path.name.startswith("_") and path.stem not in baseline_locations:
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError("fixture source path escapes disposable root")
            path.unlink()
    (root / "assets/results").mkdir(parents=True, exist_ok=True)


def _refresh_inputs(root):
    baseline = read_json(root / BASELINE_PATH)
    baseline["experiment_id"] = "regression-current-source-fixture"
    baseline["input_hashes"] = {
        name: hash_file(root / name) for name in planner.L0_PROTECTED_INPUT_PATHS
    }
    write_json(root / BASELINE_PATH, baseline)
    replacements = {"7bb90af6b124b724c484034fddbe1dad05006fc897947ce359d6f5a769acae54": hash_file(root / BASELINE_PATH)}

    def replace(value):
        if isinstance(value, str):
            return replacements.get(value, value)
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, dict):
            return {key: replace(item) for key, item in value.items()}
        return value

    scenarios = [root / "assets/fixtures/variation_target_planner/valid_mixed_v1.json"]
    scenarios.extend(path for directory in FIXTURE_ITERATIONS
                     if (path := root / directory / "scenario-manifest.json").is_file())
    for path in scenarios:
        old = read_json(path)
        if old.get("stage_id") != "V150":
            continue
        scenario = replace(old)
        report = planner.build_projection_report(scenario, target=150000)
        replacements[hash_value(old)] = report["scenario_manifest_sha256"]
        replacements[hash_value(planner._normalize_projection_manifest(old))] = report["scenario_manifest_sha256"]
        write_json(path, scenario)
        projection = path.with_name("projection-report.json")
        if projection.exists():
            replacements[hash_value(read_json(projection))] = hash_value(report)
            write_json(projection, report)
        elif "fixtures" in path.parts:
            fixture_catalog = root / "assets/fixtures/variation_candidate_analyzer/valid_catalog_v1.json"
            payload = read_json(fixture_catalog)
            replacements[payload["scenario_binding"]["projection_report_sha256"]] = hash_value(report)

    refreshed = set()

    def refresh_catalog(path):
        if path in refreshed:
            return
        payload = replace(read_json(path))
        if not str(payload.get("schema_version", "")).startswith("variation-quality-candidate-"):
            return
        if "base_catalog_path" in payload:
            base = root / payload["base_catalog_path"]
            refresh_catalog(base)
            payload["base_catalog_sha256"] = hash_file(base)
        for field in ("action_overrides", "location_additions", "location_overrides"):
            if field + "_path" in payload:
                payload[field + "_sha256"] = hash_file(root / payload[field + "_path"])
        write_json(path, payload)
        refreshed.add(path)

    catalog_paths = [path for directory in FIXTURE_ITERATIONS for path in (root / directory).glob("candidate-*.json")]
    catalog_paths.extend((root / "assets/fixtures/variation_candidate_analyzer").glob("*.json"))
    for path in catalog_paths:
        refresh_catalog(path)
    for directory in (ITERATION_TWO, ITERATION_FOUR):
        base = root / directory
        analysis = analyzer.analyze_candidate_catalog(
            analyzer.load_candidate_catalog(base / "candidate-iteration.json"),
            scenario_manifest=read_json(base / "scenario-manifest.json"),
            projection_report=read_json(base / "projection-report.json"),
        )
        write_json(base / "analysis-report.json", analysis)


def _make_contract_inputs(root):
    """Bind small synthetic parent evidence to real candidate catalog data."""
    from tools.plan_variation_prompt_schedule import build_prompt_schedule
    from tools.prepare_variation_quality_evaluation import _run_contract

    scheduled_dir = root / EXPERIMENTS / "v150-candidate-shape-iteration-005"
    old_schedule = read_json(scheduled_dir / "coverage-plan.json")
    write_json(scheduled_dir / "coverage-plan.json", build_prompt_schedule(
        candidate_iteration=root / ITERATION_FOUR / "candidate-iteration.json",
        coverage_contract_path=root / old_schedule["coverage_contract_path"],
        workflow_path=root / old_schedule["workflow_path"],
        source_root=root,
    ))
    quality_path = root / EXPERIMENTS / "v150-candidate-shape-iteration-008/nonselected-quality-contract.json"
    contract = read_json(quality_path)
    contract["run_contract"] = _run_contract(root, contract["run_contract"])
    catalog_path = root / contract["candidate_iteration_path"]
    catalog = analyzer.load_candidate_catalog(catalog_path)
    contract["candidate_iteration_sha256"] = hash_file(catalog_path)
    contract["effective_catalog_sha256"] = hash_value(catalog)
    refresh_path = root / contract["current_source_refresh_path"]
    refresh = read_json(refresh_path)
    refresh["snapshot_manifest_path"] = "assets/fixtures/variation-runtime/quality-snapshot.json"
    snapshot_path = root / refresh["snapshot_manifest_path"]
    write_json(snapshot_path, {
        "state": "SNAPSHOT_READY", "prompt_generation_allowed": True,
        "candidate_source_tree_sha256": refresh["candidate_source_tree_sha256"],
        "prompt_schedule_sha256": refresh["prompt_schedule_sha256"],
        "prompt_schedule_verification": {
            "status": "pass", "verification_sha256": refresh["certificate_verification_sha256"],
        },
    })
    refresh["snapshot_manifest_sha256"] = hash_file(snapshot_path)
    for prefix in ("coverage_receipt", "guard_remediation_receipt"):
        contract[prefix + "_sha256"] = hash_file(root / contract[prefix + "_path"])
    refresh["parent_guard_remediation_receipt_sha256"] = contract["guard_remediation_receipt_sha256"]
    write_json(refresh_path, seal(refresh, "refresh_sha256"))
    contract["current_source_refresh_sha256"] = hash_file(refresh_path)
    write_json(quality_path, seal(contract, "contract_sha256"))

    final_dir = root / EXPERIMENTS / "v150-candidate-shape-iteration-006"
    final_path = final_dir / "full-workflow-coverage-contract.json"
    final = read_json(final_path)
    final["run_contract"] = _run_contract(root, final["run_contract"])
    calibration_dir = root / "assets/fixtures/variation-runtime/calibration"
    final["calibration_snapshot_manifest_path"] = (calibration_dir / "snapshot-manifest.json").relative_to(root).as_posix()
    final["candidate_iteration_sha256"] = hash_file(catalog_path)
    final["effective_catalog_sha256"] = hash_value(catalog)
    final["parent_rejection_receipt_sha256"] = hash_file(root / final["parent_rejection_receipt_path"])
    write_json(calibration_dir / "snapshot-manifest.json", {
        "state": "SNAPSHOT_READY", "prompt_generation_allowed": True,
        "candidate_source_tree_sha256": final["calibration_candidate_source_tree_sha256"],
    })
    final["calibration_snapshot_manifest_sha256"] = hash_file(calibration_dir / "snapshot-manifest.json")
    for name in ("vocab/data/action_pools.json", final["run_contract"]["workflow"], final["run_contract"]["profile"]):
        dest = calibration_dir / "candidate-root" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, dest)
    final["calibration_action_pools_sha256"] = hash_file(calibration_dir / "candidate-root/vocab/data/action_pools.json")
    write_json(final_path, seal(final, "contract_sha256"))
    matrix_path = root / final["witness_matrix_path"]
    matrix = read_json(matrix_path)
    matrix["contract_sha256"] = final["contract_sha256"]
    write_json(matrix_path, seal(matrix, "matrix_sha256"))
    schedule_path = final_dir / "full-workflow-schedule.json"
    schedule = read_json(schedule_path)
    schedule["run_contract"] = final["run_contract"]
    schedule["full_coverage_contract_sha256"] = final["contract_sha256"]
    schedule["witness_matrix_sha256"] = matrix["matrix_sha256"]
    schedule["effective_catalog_sha256"] = hash_value(catalog)
    write_json(schedule_path, seal(schedule, "schedule_sha256"))


@lru_cache(maxsize=1)
def fixture_repository():
    temporary = tempfile.TemporaryDirectory(prefix="variation-tests-")
    atexit.register(temporary.cleanup)
    root = Path(temporary.name)
    _copy_sources(root)
    with fixture_environment(root):
        _refresh_inputs(root)
        _make_contract_inputs(root)
    return root
