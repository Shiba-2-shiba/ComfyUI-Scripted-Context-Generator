from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from collections import Counter
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.materialize_variation_candidate_snapshot import validate_snapshot_manifest
from tools.plan_variation_prompt_schedule import validate_prompt_schedule
from tools.variation_quality_contract import PROSPECTIVE_SCHEMA_VERSION, validate_variation_quality_contract
from tools.semantic_review_contract import V7_TARGETS, V7_GUARDS, validate_v7_review_contract, v7_dimension_eligibility
from core.semantic_policy import find_banned_terms
from tools.analyze_prompt_quality import analyze_records, load_policy
from tools.prompt_quality_loop import build_source_manifest
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes, load_profile
from workflow_widget_validation import load_workflow


REPORT_SCHEMA_VERSION = "variation-prompt-pair-comparison/v1"
QUALITY_REPORT_SCHEMA_VERSION = "variation-nonselected-quality-comparison/v2"
QUALITY_EXPERIMENT_SCHEMA_VERSION = "variation-nonselected-quality-experiment/v2"
SEMANTIC_COMPARISON_SCHEMA_VERSION = "prompt-quality-comparison/v2"
SEMANTIC_COMPARISON_V5_SCHEMA_VERSION = "prompt-quality-comparison/v3"
SEMANTIC_COMPARISON_V6_SCHEMA_VERSION = "prompt-quality-comparison/v4"
SEMANTIC_COMPARISON_V7_SCHEMA_VERSION = "prompt-quality-comparison/v5"
SEMANTIC_CONTRACT_SCHEMA_VERSION = "variation-semantic-pair-contract/v1"
SEMANTIC_GENERATION_SCHEMA_VERSION = "variation-semantic-pair-generation-receipt/v1"
SEMANTIC_VALIDATION_SCHEMA_VERSION = "variation-semantic-pair-validation/v1"
SEMANTIC_REVIEW_POLICY_SCHEMA_VERSION = "prompt-quality-review-contract/v4"
SEMANTIC_REVIEW_POLICY_V5_SCHEMA_VERSION = "prompt-quality-review-contract/v5"
SEMANTIC_REVIEW_POLICY_V6_SCHEMA_VERSION = "prompt-quality-review-contract/v6"
SEMANTIC_REVIEW_POLICY_V7_SCHEMA_VERSION = "prompt-quality-review-contract/v7"
SEMANTIC_REVIEW_DIMENSIONS = (
    "protagonist_clarity",
    "consistency",
    "naturalness",
    "redundancy",
    "diversity",
    "image_prompt_suitability",
)
REQUIRED_RUN_ARTIFACTS = (
    "records.jsonl",
    "metrics.json",
    "issues.json",
    "source-manifest.json",
    "telemetry.json",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _semantic_value_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_embedded_hash(value: Mapping[str, Any], field: str, code: str) -> None:
    body = dict(value)
    declared = body.pop(field, None)
    if declared != _semantic_value_hash(body):
        raise WorkflowValidationError(code, "artifact canonical hash is invalid", field=field)


def build_semantic_pair_comparison(
    *,
    automatic_comparison_path: Path,
    contract_path: Path,
    generation_receipt_path: Path,
    validation_path: Path,
    baseline_records_path: Path,
    candidate_records_path: Path,
    review_policy: Mapping[str, Any],
) -> dict[str, Any]:
    automatic = _read_json(automatic_comparison_path)
    contract = _read_json(contract_path)
    generation = _read_json(generation_receipt_path)
    validation = _read_json(validation_path)
    if automatic.get("schema_version") != QUALITY_REPORT_SCHEMA_VERSION:
        raise WorkflowValidationError(
            "semantic_automatic_comparison_schema_mismatch",
            "semantic comparison requires the passing non-selected automatic comparison",
        )
    if (
        automatic.get("quality_verdict") != "pass"
        or automatic.get("validation_verdict") != "pass"
        or automatic.get("review_ready") is not True
        or automatic.get("promotion_ready") is not False
    ):
        raise WorkflowValidationError(
            "semantic_automatic_comparison_not_ready",
            "automatic comparison is not eligible for semantic review",
        )
    if contract.get("schema_version") != SEMANTIC_CONTRACT_SCHEMA_VERSION:
        raise WorkflowValidationError(
            "semantic_pair_contract_schema_mismatch",
            "semantic pair contract schema is unsupported",
        )
    _validate_embedded_hash(contract, "contract_sha256", "semantic_pair_contract_hash_mismatch")
    automatic_binding = contract.get("automatic_comparison")
    if (
        not isinstance(automatic_binding, Mapping)
        or automatic_binding.get("sha256") != _hash_path(automatic_comparison_path)
    ):
        raise WorkflowValidationError(
            "semantic_automatic_comparison_binding_mismatch",
            "semantic contract does not bind the supplied automatic comparison",
        )
    experiment_id = str(contract.get("experiment_id") or "")
    if not experiment_id or automatic.get("experiment_id", experiment_id) != experiment_id:
        raise WorkflowValidationError(
            "semantic_pair_experiment_mismatch",
            "semantic artifacts do not share one experiment id",
        )
    if generation.get("schema_version") != SEMANTIC_GENERATION_SCHEMA_VERSION:
        raise WorkflowValidationError(
            "semantic_pair_generation_schema_mismatch",
            "semantic pair generation receipt schema is unsupported",
        )
    _validate_embedded_hash(
        generation,
        "generation_receipt_sha256",
        "semantic_pair_generation_hash_mismatch",
    )
    if (
        generation.get("status") != "generated"
        or generation.get("experiment_id") != experiment_id
        or generation.get("contract_sha256") != contract.get("contract_sha256")
    ):
        raise WorkflowValidationError(
            "semantic_pair_generation_binding_mismatch",
            "generation receipt does not bind the semantic contract",
        )
    if validation.get("schema_version") != SEMANTIC_VALIDATION_SCHEMA_VERSION:
        raise WorkflowValidationError(
            "semantic_pair_validation_schema_mismatch",
            "semantic pair validation schema is unsupported",
        )
    _validate_embedded_hash(
        validation,
        "validation_sha256",
        "semantic_pair_validation_hash_mismatch",
    )
    if (
        validation.get("status") != "pass"
        or validation.get("experiment_id") != experiment_id
        or validation.get("contract_sha256") != contract.get("contract_sha256")
        or validation.get("generation_receipt_sha256")
        != generation.get("generation_receipt_sha256")
        or validation.get("validated_pair_count") != 20
        or any(
            validation.get(field) != 0
            for field in (
                "identity_mismatch_count",
                "seed_mismatch_count",
                "record_hash_mismatch_count",
            )
        )
        or validation.get("mismatches") != []
    ):
        raise WorkflowValidationError(
            "semantic_pair_validation_failed",
            "semantic pair validation is not a passing twenty-pair receipt",
        )
    actual_record_hashes = {
        "baseline_records_sha256": _hash_path(baseline_records_path),
        "candidate_records_sha256": _hash_path(candidate_records_path),
    }
    if any(generation.get(field) != value for field, value in actual_record_hashes.items()):
        raise WorkflowValidationError(
            "semantic_pair_record_hash_mismatch",
            "semantic pair record bytes drifted from the generation receipt",
        )
    snapshot = contract.get("candidate_snapshot")
    if not isinstance(snapshot, Mapping):
        raise WorkflowValidationError(
            "semantic_pair_snapshot_binding_missing",
            "semantic contract omits the candidate snapshot binding",
        )
    candidate_source_hash = snapshot.get("candidate_source_tree_sha256")
    candidate_content_hash = snapshot.get("candidate_snapshot_content_sha256")
    if not all(isinstance(item, str) and len(item) == 64 for item in (candidate_source_hash, candidate_content_hash)):
        raise WorkflowValidationError(
            "semantic_pair_snapshot_binding_invalid",
            "candidate snapshot source/content hashes are invalid",
        )
    review_contract_schema = review_policy.get("schema_version")
    if review_contract_schema not in {
        SEMANTIC_REVIEW_POLICY_SCHEMA_VERSION,
        SEMANTIC_REVIEW_POLICY_V5_SCHEMA_VERSION,
        SEMANTIC_REVIEW_POLICY_V6_SCHEMA_VERSION,
        SEMANTIC_REVIEW_POLICY_V7_SCHEMA_VERSION,
    }:
        raise WorkflowValidationError(
            "semantic_review_policy_schema_mismatch",
            "semantic review requires review-contract/v4, v5, v6, or v7",
        )
    is_v5 = review_contract_schema == SEMANTIC_REVIEW_POLICY_V5_SCHEMA_VERSION
    is_v6 = review_contract_schema == SEMANTIC_REVIEW_POLICY_V6_SCHEMA_VERSION
    is_v7 = review_contract_schema == SEMANTIC_REVIEW_POLICY_V7_SCHEMA_VERSION
    if is_v7:
        validate_v7_review_contract(review_policy)
    pairs = contract.get("pairs")
    if (
        not isinstance(pairs, list)
        or len(pairs) != 20
        or len({str(item.get("pair_id")) for item in pairs if isinstance(item, Mapping)}) != 20
    ):
        raise WorkflowValidationError(
            "semantic_pair_contract_pair_count_invalid",
            "semantic review requires twenty unique contract pairs",
        )
    pair_specs = [
        {
            "pair_id": str(pair["pair_id"]),
            "cohort": str(pair["cohort"]),
            "run_seed": int(pair["run_seed"]),
        }
        for pair in pairs
    ]
    pair_ids = [item["pair_id"] for item in pair_specs]
    target_dimensions = {
        "consistency", "naturalness", "image_prompt_suitability",
    } if is_v6 else {
        "protagonist_clarity", "consistency", "naturalness", "image_prompt_suitability",
    }
    dimensions = {
        dimension: {
            "authority": (
                "current_source_corpus_confirmation"
                if dimension == "diversity"
                else "semantic_pairwise"
            ),
            **(
                {
                    "minimum_non_abstain_votes": 36 if (dimension in target_dimensions or (is_v6 and dimension != "diversity")) else 0,
                    "minimum_directional_votes": 20 if dimension in target_dimensions else 0,
                }
                if is_v5 or is_v6 else
                {"minimum_valid_votes": 36 if dimension in target_dimensions else 0}
            ),
            "pair_ids": [] if dimension == "diversity" else pair_ids,
        }
        for dimension in SEMANTIC_REVIEW_DIMENSIONS
    }
    if is_v7:
        dimensions = v7_dimension_eligibility(pair_ids)
    selection = {"pairs": pair_specs, "dimensions": dimensions}
    selection["selection_hash"] = _content_hash(selection)
    scope = {
        "guard_qualitative_dimensions": (
            ["protagonist_clarity", "redundancy", "diversity"]
            if is_v6 else ["redundancy", "diversity"]
        ),
        "target_qualitative_dimensions": (
            ["consistency", "naturalness", "image_prompt_suitability"]
            if is_v6 else ["consistency", "naturalness", "protagonist_clarity", "image_prompt_suitability"]
        ),
    }
    if is_v7:
        scope = {"target_qualitative_dimensions": V7_TARGETS, "guard_qualitative_dimensions": V7_GUARDS}
    return {
        "schema_version": SEMANTIC_COMPARISON_V7_SCHEMA_VERSION if is_v7 else SEMANTIC_COMPARISON_V6_SCHEMA_VERSION if is_v6 else SEMANTIC_COMPARISON_V5_SCHEMA_VERSION if is_v5 else SEMANTIC_COMPARISON_SCHEMA_VERSION,
        "experiment_id": experiment_id,
        "review_contract_hash": _content_hash(dict(review_policy)),
        "qualitative_scope_hash": _content_hash(scope),
        "automatic_comparison_path": str(automatic_comparison_path),
        "automatic_comparison_hash": _hash_path(automatic_comparison_path),
        "automatic_comparison_verdict": "pass",
        "candidate_source_tree_sha256": candidate_source_hash,
        "candidate_snapshot_content_sha256": candidate_content_hash,
        "uses_output_metrics_for_selection": False,
        "semantic_pair_contract_sha256": _hash_path(contract_path),
        "pair_generation_receipt_sha256": _hash_path(generation_receipt_path),
        "pair_validation_sha256": _hash_path(validation_path),
        "selection_salt_sha256": contract.get("selection_salt_sha256"),
        "compatibility_graph_sha256": contract.get("compatibility_graph_sha256"),
        **actual_record_hashes,
        "review_selection": selection,
    }


def _resolve_contract_path(source_root: Path, value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise WorkflowValidationError("invalid_variation_experiment", f"run_contract.{field} must be a relative path")
    path = (source_root / value).resolve()
    try:
        path.relative_to(source_root.resolve())
    except ValueError:
        raise WorkflowValidationError("invalid_variation_experiment", f"run_contract.{field} escapes the snapshot root") from None
    return path


def _normalise_explicit_overrides(value: Any) -> dict[int, dict[str, Any]]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise WorkflowValidationError("invalid_variation_experiment", "run_contract.overrides must be an object")
    result: dict[int, dict[str, Any]] = {}
    for raw_node_id, raw_values in value.items():
        try:
            node_id = int(raw_node_id)
        except (TypeError, ValueError):
            raise WorkflowValidationError("invalid_variation_experiment", "run_contract override node ids must be integers") from None
        if not isinstance(raw_values, Mapping):
            raise WorkflowValidationError("invalid_variation_experiment", "run_contract override values must be objects")
        result[node_id] = {str(name): raw_values[name] for name in sorted(raw_values)}
    return dict(sorted(result.items()))


def _declared_run_contract(source_root: Path, experiment: Mapping[str, Any]) -> dict[str, str]:
    contract = experiment.get("run_contract")
    if not isinstance(contract, Mapping):
        raise WorkflowValidationError("invalid_variation_experiment", "run_contract is required")
    workflow_name = contract.get("workflow")
    profile_name = contract.get("profile")
    if experiment.get("workflow") != workflow_name or experiment.get("profile") != profile_name:
        raise WorkflowValidationError("invalid_variation_experiment", "top-level workflow/profile must match run_contract")
    workflow = load_workflow(_resolve_contract_path(source_root, workflow_name, "workflow"))
    profile = load_profile(_resolve_contract_path(source_root, profile_name, "profile"))
    explicit_overrides = _normalise_explicit_overrides(contract.get("overrides", {}))
    workflow_hash = _content_hash(workflow)
    override_hash = _content_hash(
        {"explicit": explicit_overrides, "profile": profile.resolved_overrides()}
    )
    actual = {
        "workflow_hash": workflow_hash,
        "profile_hash": profile.hash,
        "override_hash": override_hash,
        "effective_workflow_hash": _content_hash(
            {"base_workflow_hash": workflow_hash, "override_hash": override_hash}
        ),
    }
    drift = [field for field, value in actual.items() if contract.get(field) != value]
    if drift:
        raise WorkflowValidationError(
            "variation_experiment_run_contract_mismatch",
            "declared run contract does not match snapshot workflow/profile/overrides",
            fields=drift,
        )
    return actual


def _records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _metric(metrics: Mapping[str, Any], path: str) -> float:
    value: Any = metrics
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            raise WorkflowValidationError("missing_pair_metric", "pair metric is missing", metric=path)
        value = value[part]
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise WorkflowValidationError("invalid_pair_metric", "pair metric must be numeric", metric=path)
    return float(value)


def _validate_run(
    run_dir: Path,
    *,
    expected_source_hash: str,
    snapshot_source_root: Path,
    policy: Mapping[str, Any],
    require_prompt_corpus: bool = False,
) -> tuple[dict, dict, list[dict]]:
    manifest = _read_json(run_dir / "run-manifest.json")
    declared = manifest.get("artifact_hashes", {})
    if not isinstance(declared, Mapping):
        raise WorkflowValidationError("missing_run_artifact_hashes", "run manifest omits artifact hashes")
    for name in REQUIRED_RUN_ARTIFACTS:
        path = run_dir / name
        if not path.is_file() or declared.get(name) != _hash_path(path):
            raise WorkflowValidationError("run_artifact_hash_mismatch", "run artifact hash drifted", path=str(path))
    if manifest.get("source_tree_hash") != expected_source_hash:
        raise WorkflowValidationError(
            "run_snapshot_source_mismatch",
            "run source tree does not match its snapshot",
            expected=expected_source_hash,
            actual=manifest.get("source_tree_hash"),
        )
    if require_prompt_corpus and manifest.get("prompt_corpus_sha256") != _hash_path(snapshot_source_root / "prompts.jsonl"):
        raise WorkflowValidationError(
            "run_snapshot_prompt_corpus_mismatch",
            "run omits or differs from the snapshot prompt corpus binding",
        )
    replay = manifest.get("replay_evidence", {})
    if replay != {"checked": 80, "mismatch_count": 0, "status": "pass"}:
        raise WorkflowValidationError("run_replay_failed", "run replay evidence is incomplete", replay=replay)
    records = _records(run_dir / "records.jsonl")
    recomputed = analyze_records(records, policy)
    metrics = _read_json(run_dir / "metrics.json")
    issues = _read_json(run_dir / "issues.json")
    if canonical_json_bytes(metrics) != canonical_json_bytes(recomputed["metrics"]):
        raise WorkflowValidationError("run_metrics_recompute_mismatch", "run metrics do not match record recomputation")
    if canonical_json_bytes(issues) != canonical_json_bytes(recomputed["issues"]):
        raise WorkflowValidationError("run_issues_recompute_mismatch", "run issues do not match record recomputation")
    source_manifest = _read_json(run_dir / "source-manifest.json")
    expected_source_manifest = build_source_manifest(snapshot_source_root)
    if canonical_json_bytes(source_manifest) != canonical_json_bytes(expected_source_manifest):
        raise WorkflowValidationError(
            "run_source_manifest_mismatch",
            "run source manifest does not match the snapshot source tree",
        )
    return manifest, recomputed["metrics"], records


def candidate_record_coverage(
    record: Mapping[str, Any],
    expected_subjects: set[str],
    expected_locations: set[str],
    action_to_locations: Mapping[str, set[str]],
) -> tuple[set[str], set[str], set[str]]:
    subjects_seen: set[str] = set()
    locations_seen: set[str] = set()
    action_locations_seen: set[str] = set()
    context = record.get("final_context", {})
    if not isinstance(context, Mapping):
        return subjects_seen, locations_seen, action_locations_seen
    extras = context.get("extras", {})
    if isinstance(extras, Mapping):
        source_subject = extras.get("source_subj_key")
        if source_subject in expected_subjects:
            subjects_seen.add(str(source_subject))
    location = context.get("loc")
    if location in expected_locations:
        locations_seen.add(str(location))
    decision = final_scene_decision(context)
    if decision is not None:
        action = scene_action_pool_witness(decision)
        if location in expected_locations and action in action_to_locations and location in action_to_locations[action]:
            action_locations_seen.add(str(location))
    return subjects_seen, locations_seen, action_locations_seen


def scene_action_pool_witness(decision: Mapping[str, Any]) -> str:
    updated = decision.get("action_updated", False)
    if type(updated) is not bool:
        raise WorkflowValidationError(
            "invalid_scene_action_update_flag",
            "SceneVariator action_updated must be boolean",
        )
    if updated:
        return str(decision.get("base_action") or "").strip()
    return str(decision.get("action") or "").strip()


def final_scene_decision(context: Mapping[str, Any]) -> Mapping[str, Any] | None:
    final_location = str(context.get("loc", ""))
    if not final_location:
        return None
    history = context.get("history", [])
    if not isinstance(history, list):
        return None
    for entry in reversed(history):
        if not isinstance(entry, Mapping) or entry.get("node") != "ContextSceneVariator":
            continue
        decision = entry.get("decision", {})
        if not isinstance(decision, Mapping) or str(decision.get("selected_loc", "")) != final_location:
            return None
        return decision
    return None


def candidate_coverage(records: list[dict], candidate_root: Path, candidate_ids: Mapping[str, Any]) -> dict:
    expected_subjects = set(candidate_ids.get("subjects", []))
    expected_locations = set(candidate_ids.get("locations", []))
    action_pools = _read_json(candidate_root / "vocab/data/action_pools.json")
    action_to_locations: dict[str, set[str]] = {}
    for location in expected_locations:
        for action in action_pools.get(location, []):
            text = str(action.get("text", "") if isinstance(action, Mapping) else action)
            action_to_locations.setdefault(text, set()).add(location)
    subjects_seen: set[str] = set()
    locations_seen: set[str] = set()
    action_locations_seen: set[str] = set()
    for record in records:
        record_subjects, record_locations, record_action_locations = candidate_record_coverage(
            record, expected_subjects, expected_locations, action_to_locations
        )
        subjects_seen.update(record_subjects)
        locations_seen.update(record_locations)
        action_locations_seen.update(record_action_locations)
    return {
        "subjects_seen": sorted(subjects_seen),
        "locations_seen": sorted(locations_seen),
        "action_pool_locations_seen": sorted(action_locations_seen),
        "unseen_subjects": sorted(expected_subjects - subjects_seen),
        "unseen_locations": sorted(expected_locations - locations_seen),
        "unseen_action_pool_locations": sorted(expected_locations - action_locations_seen),
    }


def _load_bound_prompt_schedule(
    snapshot_root: Path,
    snapshot_manifest: Mapping[str, Any],
    experiment: Mapping[str, Any],
) -> dict[str, Any] | None:
    snapshot_plan_path = snapshot_root / "snapshot-plan.json"
    if not snapshot_plan_path.is_file():
        if experiment.get("coverage_schedule_sha256") is not None:
            raise WorkflowValidationError(
                "variation_experiment_schedule_mismatch",
                "experiment declares a prompt schedule but snapshot plan is missing",
            )
        return None
    snapshot_plan = _read_json(snapshot_plan_path)
    binding = snapshot_plan.get("inputs", {}).get("prompt_schedule")
    if binding is None:
        if experiment.get("coverage_schedule_sha256") is not None:
            raise WorkflowValidationError(
                "variation_experiment_schedule_mismatch",
                "experiment declares a prompt schedule but snapshot does not",
            )
        return None
    schedule_path = (ROOT / str(binding.get("path", ""))).resolve()
    try:
        schedule_path.relative_to(ROOT.resolve())
    except ValueError:
        raise WorkflowValidationError("variation_schedule_path_escape", "prompt schedule escapes repository") from None
    if not schedule_path.is_file() or _hash_path(schedule_path) != binding.get("sha256"):
        raise WorkflowValidationError("variation_schedule_input_drift", "bound prompt schedule file drifted")
    schedule = _read_json(schedule_path)
    validate_prompt_schedule(schedule, source_root=ROOT)
    schedule_hash = schedule.get("schedule_sha256")
    if (
        schedule_hash != snapshot_plan.get("prompt_schedule_sha256")
        or schedule_hash != snapshot_manifest.get("prompt_schedule_sha256")
        or schedule_hash != experiment.get("coverage_schedule_sha256")
        or _hash_path(snapshot_root / "candidate-root/prompts.jsonl")
        != schedule.get("candidate_prompts_jsonl_sha256")
    ):
        raise WorkflowValidationError(
            "variation_experiment_schedule_mismatch",
            "experiment, snapshot, and prompt schedule bindings differ",
        )
    return schedule


def _load_bound_quality_contract(
    snapshot_root: Path,
    snapshot_manifest: Mapping[str, Any],
    experiment: Mapping[str, Any],
) -> dict[str, Any] | None:
    snapshot_plan_path = snapshot_root / "snapshot-plan.json"
    if not snapshot_plan_path.is_file():
        return None
    snapshot_plan = _read_json(snapshot_plan_path)
    binding = snapshot_plan.get("inputs", {}).get("quality_contract")
    if binding is None:
        if experiment.get("quality_contract_sha256") is not None:
            raise WorkflowValidationError(
                "variation_experiment_quality_contract_mismatch",
                "experiment declares a quality contract but snapshot does not",
            )
        return None
    if snapshot_plan.get("inputs", {}).get("prompt_schedule") is not None:
        raise WorkflowValidationError(
            "variation_quality_surface_scheduled",
            "non-selected quality surface cannot bind a prompt schedule",
        )
    contract_path = (ROOT / str(binding.get("path", ""))).resolve()
    try:
        contract_path.relative_to(ROOT.resolve())
    except ValueError:
        raise WorkflowValidationError(
            "variation_quality_contract_path_escape",
            "quality contract escapes repository",
        ) from None
    if not contract_path.is_file() or _hash_path(contract_path) != binding.get("sha256"):
        raise WorkflowValidationError(
            "variation_quality_contract_input_drift",
            "bound quality contract file drifted",
        )
    contract = _read_json(contract_path)
    validation = validate_variation_quality_contract(contract, repository_root=ROOT)
    contract_hash = contract.get("contract_sha256")
    prompt_rows = snapshot_manifest.get("prompt_rows", {})
    if contract.get("schema_version") == PROSPECTIVE_SCHEMA_VERSION:
        # Input corpus size is independent of the exact 80 generated records.
        # Prospective evaluation preserves the active baseline corpus verbatim.
        valid_prompt_surface = (
            snapshot_plan.get("baseline_prompt_mode") == "active"
            and prompt_rows.get("candidate") == 80
            and isinstance(prompt_rows.get("baseline"), int)
            and prompt_rows["baseline"] > 0
            and _hash_path(snapshot_root / "baseline-root/prompts.jsonl") == _hash_path(ROOT / "prompts.jsonl")
        )
        frozen_cohort = contract["cohort"]
        if experiment.get("cohort") != {
            "cohort_hash": frozen_cohort["cohort_hash"],
            "experiment_seed": frozen_cohort["experiment_seed"],
            "iteration_id": frozen_cohort["iteration_id"],
            "control_count": 64, "exploration_count": 16, "samples": 80,
        }:
            raise WorkflowValidationError("variation_quality_cohort_drift", "experiment does not bind the frozen quality cohort")
    else:
        valid_prompt_surface = prompt_rows == {"baseline": 80, "candidate": 80}
    if (
        contract_hash != snapshot_plan.get("quality_contract_sha256")
        or contract_hash != snapshot_manifest.get("quality_contract_sha256")
        or contract_hash != experiment.get("quality_contract_sha256")
        or experiment.get("comparison_authority") != "quality_non_selected"
        or experiment.get("surface_kind") != "default_fixed_64_16"
        or experiment.get("prompt_selection") != "default_unselected"
        or experiment.get("schema_version") != QUALITY_EXPERIMENT_SCHEMA_VERSION
        or not valid_prompt_surface
        or snapshot_manifest.get("prompt_schedule_sha256") is not None
        or snapshot_manifest.get("candidate_source_tree_sha256")
        != contract.get("candidate_source_tree_sha256")
        or snapshot_manifest.get("candidate_ids") != contract.get("candidate_ids")
        or experiment.get("run_contract") != contract.get("run_contract")
        or experiment.get("default_candidate_prompts_sha256")
        != _hash_path(snapshot_root / "candidate-root/prompts.jsonl")
    ):
        raise WorkflowValidationError(
            "variation_experiment_quality_contract_mismatch",
            "experiment, snapshot, and non-selected quality contract differ",
        )
    bound_contract = dict(contract)
    bound_contract["_validated_coverage_eligibility"] = validation[
        "coverage_eligibility"
    ]
    return bound_contract


def _validate_quality_cohort_records(contract: Mapping[str, Any], records: list[dict], cohort_hash: Any) -> None:
    cohort = contract["cohort"]
    expected = {int(seed): name for name in ("control", "exploration") for seed in cohort[name + "_seeds"]}
    actual = {int(row["run_seed"]): row.get("cohort") for row in records}
    if cohort_hash != cohort["cohort_hash"] or len(records) != 80 or actual != expected:
        raise WorkflowValidationError("variation_quality_cohort_drift", "run seeds or cohort labels differ from the frozen quality cohort")


def scheduled_location_action_coverage(records: list[dict], schedule: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        (str(item["location"]), str(item["action"]))
        for item in schedule.get("expected_location_actions", [])
    }
    observed: set[tuple[str, str]] = set()
    for record in records:
        context = record.get("final_context", {})
        if not isinstance(context, Mapping):
            continue
        location = str(context.get("loc", ""))
        decision = final_scene_decision(context)
        if decision is not None:
            action = scene_action_pool_witness(decision) if isinstance(decision, Mapping) else ""
            pair = (location, action)
            if pair in expected:
                observed.add(pair)
    missing = sorted(expected - observed)
    return {
        "expected_count": len(expected),
        "observed_count": len(observed),
        "observed_location_actions": [
            {"location": location, "action": action} for location, action in sorted(observed)
        ],
        "missing_location_actions": [
            {"location": location, "action": action} for location, action in missing
        ],
        "status": "pass" if not missing else "fail",
    }


def compare_variation_prompt_pair(
    *,
    snapshot_root: Path,
    baseline_run: Path,
    candidate_run: Path,
    experiment: Mapping[str, Any] | Path,
) -> dict:
    snapshot_root = snapshot_root.resolve()
    snapshot_manifest = _read_json(snapshot_root / "snapshot-manifest.json")
    validate_snapshot_manifest(snapshot_root, snapshot_manifest)
    if snapshot_manifest.get("state") != "SNAPSHOT_READY" or not snapshot_manifest.get("prompt_generation_allowed"):
        raise WorkflowValidationError("snapshot_prompt_generation_blocked", "snapshot does not permit prompt comparison")
    experiment_value = _read_json(experiment) if isinstance(experiment, Path) else dict(experiment)
    if experiment_value.get("schema_version") not in {
        "prompt-quality-experiment/v1",
        QUALITY_EXPERIMENT_SCHEMA_VERSION,
    }:
        raise WorkflowValidationError("invalid_variation_experiment", "variation experiment schema is invalid")
    expected_snapshot_hash = experiment_value.get("snapshot_manifest_sha256")
    actual_snapshot_hash = _hash_path(snapshot_root / "snapshot-manifest.json")
    if expected_snapshot_hash != actual_snapshot_hash:
        raise WorkflowValidationError("variation_experiment_snapshot_mismatch", "experiment snapshot binding drifted")
    prompt_schedule = _load_bound_prompt_schedule(snapshot_root, snapshot_manifest, experiment_value)
    quality_contract = _load_bound_quality_contract(
        snapshot_root, snapshot_manifest, experiment_value
    )
    if prompt_schedule is not None and quality_contract is not None:
        raise WorkflowValidationError(
            "variation_quality_surface_conflict",
            "comparison cannot use scheduled coverage and non-selected quality authority together",
        )
    is_quality_experiment = (
        experiment_value.get("schema_version") == QUALITY_EXPERIMENT_SCHEMA_VERSION
    )
    if is_quality_experiment and quality_contract is None:
        raise WorkflowValidationError(
            "variation_quality_contract_required",
            "v2 non-selected quality experiment requires a bound quality contract",
        )
    if not is_quality_experiment and quality_contract is not None:
        raise WorkflowValidationError(
            "variation_quality_contract_forbidden",
            "v1 variation experiment cannot use non-selected quality authority",
        )
    baseline_run_contract = _declared_run_contract(snapshot_root / "baseline-root", experiment_value)
    candidate_run_contract = _declared_run_contract(snapshot_root / "candidate-root", experiment_value)
    if baseline_run_contract != candidate_run_contract:
        raise WorkflowValidationError(
            "variation_pair_contract_drift",
            "baseline and candidate snapshot workflow contracts differ",
        )
    baseline_policy_path = snapshot_root / "baseline-root/vocab/data/prompt_quality_policy.json"
    candidate_policy_path = snapshot_root / "candidate-root/vocab/data/prompt_quality_policy.json"
    if _hash_path(baseline_policy_path) != _hash_path(candidate_policy_path):
        raise WorkflowValidationError("variation_pair_policy_drift", "baseline and candidate policy files differ")
    policy = load_policy(candidate_policy_path)
    baseline_manifest, baseline_metrics, baseline_records = _validate_run(
        baseline_run,
        expected_source_hash=str(snapshot_manifest["baseline_source_tree_sha256"]),
        snapshot_source_root=snapshot_root / "baseline-root",
        policy=policy,
        require_prompt_corpus=quality_contract is not None and quality_contract.get("schema_version") == PROSPECTIVE_SCHEMA_VERSION,
    )
    candidate_manifest, candidate_metrics, candidate_records = _validate_run(
        candidate_run,
        expected_source_hash=str(snapshot_manifest["candidate_source_tree_sha256"]),
        snapshot_source_root=snapshot_root / "candidate-root",
        policy=policy,
        require_prompt_corpus=quality_contract is not None and quality_contract.get("schema_version") == PROSPECTIVE_SCHEMA_VERSION,
    )
    if quality_contract is not None and quality_contract.get("schema_version") == PROSPECTIVE_SCHEMA_VERSION:
        _validate_quality_cohort_records(quality_contract, baseline_records, baseline_manifest.get("cohort_hash"))
        _validate_quality_cohort_records(quality_contract, candidate_records, candidate_manifest.get("cohort_hash"))
    shared_fields = ("cohort_hash", "workflow_hash", "effective_workflow_hash", "profile_hash", "override_hash")
    drift = [field for field in shared_fields if baseline_manifest.get(field) != candidate_manifest.get(field)]
    if drift:
        raise WorkflowValidationError("variation_pair_contract_drift", "paired run contract drifted", fields=drift)
    run_contract_drift = [
        field
        for field, expected in baseline_run_contract.items()
        if baseline_manifest.get(field) != expected or candidate_manifest.get(field) != expected
    ]
    if run_contract_drift:
        raise WorkflowValidationError(
            "variation_experiment_run_contract_mismatch",
            "paired run manifests do not match the authenticated experiment contract",
            fields=run_contract_drift,
        )
    baseline_index = {int(record["run_seed"]): record for record in baseline_records}
    candidate_index = {int(record["run_seed"]): record for record in candidate_records}
    if set(baseline_index) != set(candidate_index) or len(baseline_index) != 80:
        raise WorkflowValidationError("variation_pair_seed_mismatch", "paired seed sets differ or are incomplete")
    if any(baseline_index[seed].get("cohort") != candidate_index[seed].get("cohort") for seed in baseline_index):
        raise WorkflowValidationError("variation_pair_cohort_label_mismatch", "paired cohort labels differ")
    for side, records in (("baseline", baseline_records), ("candidate", candidate_records)):
        counts = Counter(str(record.get("cohort", "")) for record in records)
        if counts != {"control": 64, "exploration": 16}:
            raise WorkflowValidationError(
                "variation_pair_cohort_label_mismatch",
                "paired runs must contain exactly 64 control and 16 exploration labels",
                side=side,
            counts=dict(counts),
            )
    cohort_contract = experiment_value.get("cohort", {})
    if (
        not isinstance(cohort_contract, Mapping)
        or cohort_contract.get("cohort_hash") != baseline_manifest.get("cohort_hash")
        or cohort_contract.get("control_count") != 64
        or cohort_contract.get("exploration_count") != 16
        or cohort_contract.get("samples") != 80
    ):
        raise WorkflowValidationError("variation_experiment_cohort_mismatch", "experiment cohort binding drifted")

    metric_scope = str(experiment_value.get("metric_scope", "all80"))
    if is_quality_experiment and metric_scope != "control64":
        raise WorkflowValidationError(
            "variation_quality_metric_scope_mismatch",
            "v2 non-selected quality experiment must use control64 metrics",
        )
    if metric_scope == "control64":
        baseline_metric_records = [
            record for record in baseline_records if record.get("cohort") == "control"
        ]
        candidate_metric_records = [
            record for record in candidate_records if record.get("cohort") == "control"
        ]
        if len(baseline_metric_records) != 64 or len(candidate_metric_records) != 64:
            raise WorkflowValidationError(
                "variation_metric_scope_record_mismatch",
                "control64 metric scope requires exactly 64 records per side",
            )
        baseline_metrics = analyze_records(baseline_metric_records, policy)["metrics"]
        candidate_metrics = analyze_records(candidate_metric_records, policy)["metrics"]
    elif metric_scope == "all80":
        baseline_metric_records = baseline_records
        candidate_metric_records = candidate_records
        baseline_metrics = dict(baseline_metrics)
        candidate_metrics = dict(candidate_metrics)
    else:
        raise WorkflowValidationError(
            "variation_metric_scope_unsupported",
            "variation comparison metric scope is unsupported",
            metric_scope=metric_scope,
        )
    baseline_metrics.setdefault(
        "policy",
        {"policy_issue_count": sum(1 for record in baseline_metric_records if find_banned_terms(str(record.get("cleaned_prompt", ""))))},
    )
    candidate_metrics.setdefault(
        "policy",
        {"policy_issue_count": sum(1 for record in candidate_metric_records if find_banned_terms(str(record.get("cleaned_prompt", ""))))},
    )

    target_path = "diversity.location_signature_entropy"
    nonincrease_guards = (
        "naturalness.punctuation_anomaly_count",
        "naturalness.repeated_ngram_count",
        "naturalness.semantic_family_repetition_count",
        "identity.missing_female_protagonist_count",
        "identity.male_pronoun_drift_count",
        "identity.other_person_solo_conflict_count",
        "identity.duplicate_protagonist_mention_count",
        "identity.person_demographic_descriptor_count",
        "consistency.hard_conflict_count",
        "runtime.fallback_rate",
        "runtime.deterministic_replay_mismatch_count",
        "runtime.context_json_bytes_p95",
        "runtime.context_json_bytes_max",
        "policy.policy_issue_count",
    )
    nondecrease_guards = ("diversity.exact_unique_ratio",)
    comparisons = {}
    failures = []
    before_target = _metric(baseline_metrics, target_path)
    after_target = _metric(candidate_metrics, target_path)
    comparisons[target_path] = {"before": before_target, "after": after_target, "delta": after_target - before_target}
    if after_target <= before_target:
        failures.append(f"target_not_improved:{target_path}")
    for path in nonincrease_guards:
        before = _metric(baseline_metrics, path)
        after = _metric(candidate_metrics, path)
        comparisons[path] = {"before": before, "after": after, "delta": after - before}
        if after > before:
            failures.append(f"guard_regressed:{path}")
    for path in nondecrease_guards:
        before = _metric(baseline_metrics, path)
        after = _metric(candidate_metrics, path)
        comparisons[path] = {"before": before, "after": after, "delta": after - before}
        if after < before:
            failures.append(f"guard_regressed:{path}")

    changed_seeds = sorted(
        seed
        for seed in baseline_index
        if baseline_index[seed].get("cleaned_prompt") != candidate_index[seed].get("cleaned_prompt")
    )
    coverage = candidate_coverage(
        candidate_records,
        snapshot_root / "candidate-root",
        snapshot_manifest["candidate_ids"],
    )
    coverage_failures = []
    if coverage["unseen_subjects"]:
        coverage_failures.append("candidate_subject_coverage_incomplete")
    if coverage["unseen_locations"]:
        coverage_failures.append("candidate_location_coverage_incomplete")
    if coverage["unseen_action_pool_locations"]:
        coverage_failures.append("candidate_action_pool_coverage_incomplete")
    if quality_contract is None:
        failures.extend(coverage_failures)
    scheduled_coverage = None
    if prompt_schedule is not None:
        scheduled_coverage = scheduled_location_action_coverage(candidate_records, prompt_schedule)
        if scheduled_coverage["status"] != "pass":
            failures.append("scheduled_location_action_coverage_incomplete")
    if not changed_seeds:
        failures.append("candidate_changed_seed_missing")
    diagnostic_pair_verdict = "pass" if not failures else "reject"
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "snapshot_manifest_sha256": _hash_path(snapshot_root / "snapshot-manifest.json"),
        "experiment_sha256": hashlib.sha256(canonical_json_bytes(experiment_value)).hexdigest(),
        "baseline_run_manifest_sha256": _hash_path(baseline_run / "run-manifest.json"),
        "candidate_run_manifest_sha256": _hash_path(candidate_run / "run-manifest.json"),
        "cohort_hash": baseline_manifest["cohort_hash"],
        "record_count": len(baseline_index),
        "metric_scope": metric_scope,
        "metric_record_count": len(baseline_metric_records),
        "changed_seed_count": len(changed_seeds),
        "changed_seeds": changed_seeds,
        "candidate_coverage": coverage,
        "metric_comparisons": dict(sorted(comparisons.items())),
        "failures": sorted(failures),
        "verdict": diagnostic_pair_verdict,
        "prompt_quality_state": "COMPARED",
        "promotion_ready": False,
    }
    if prompt_schedule is not None:
        coverage_failures = [
            failure
            for failure in failures
            if failure in {
                "candidate_subject_coverage_incomplete",
                "candidate_location_coverage_incomplete",
                "candidate_action_pool_coverage_incomplete",
                "scheduled_location_action_coverage_incomplete",
            }
        ]
        report["coverage_schedule_sha256"] = prompt_schedule["schedule_sha256"]
        report["scheduled_location_action_coverage"] = scheduled_coverage
        report["coverage_is_quality_evidence"] = False
        report["coverage_verdict"] = "pass" if not coverage_failures else "reject"
        report["diagnostic_pair_verdict"] = diagnostic_pair_verdict
        report["fixed_quality_verdict"] = "reject"
        report["verdict"] = "reject"
    if quality_contract is not None:
        quality_failures = sorted(failures)
        quality_verdict = "pass" if not quality_failures else "reject"
        coverage_eligibility_verdict = "pass"
        validation_verdict = (
            "pass"
            if quality_verdict == "pass" and coverage_eligibility_verdict == "pass"
            else "reject"
        )
        report["schema_version"] = QUALITY_REPORT_SCHEMA_VERSION
        report["comparison_authority"] = "quality_non_selected"
        report["surface_kind"] = "default_fixed_64_16"
        report["prompt_selection"] = "default_unselected"
        report["quality_contract_sha256"] = quality_contract["contract_sha256"]
        report["quality_evidence"] = True
        report["coverage_is_quality_evidence"] = False
        report["coverage_eligibility"] = {
            **{
                field: quality_contract[field]
                for field in (
                    "coverage_receipt_sha256", "guard_remediation_receipt_sha256",
                    "coverage_snapshot_manifest_sha256", "coverage_snapshot_content_sha256",
                    "coverage_schedule_sha256",
                )
                if field in quality_contract
            },
            **quality_contract["_validated_coverage_eligibility"],
        }
        report["informational_current_coverage"] = coverage
        report["informational_coverage_failures"] = coverage_failures
        report["quality_failures"] = quality_failures
        report["coverage_evidence_failures"] = []
        if "coverage_receipt_sha256" in quality_contract:
            report["parent_fixed_quality_verdict"] = "reject"
        report["quality_verdict"] = quality_verdict
        report["coverage_eligibility_verdict"] = coverage_eligibility_verdict
        report["validation_verdict"] = validation_verdict
        report["verdict"] = validation_verdict
        report["review_ready"] = validation_verdict == "pass"
        report["blind_review_run"] = False
        report["confirmation_run"] = False
        report["promotion_ready"] = False
    report["comparison_sha256"] = hashlib.sha256(canonical_json_bytes(report)).hexdigest()
    return report


def comparison_exit_code(report: Mapping[str, Any]) -> int:
    return 0 if report.get("verdict") == "pass" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare prompt-quality runs from a declared variation snapshot pair.")
    parser.add_argument("--snapshot-root")
    parser.add_argument("--baseline-run")
    parser.add_argument("--candidate-run")
    parser.add_argument("--experiment")
    parser.add_argument("--automatic-comparison")
    parser.add_argument("--semantic-contract")
    parser.add_argument("--generation-receipt")
    parser.add_argument("--pair-validation")
    parser.add_argument("--baseline-records")
    parser.add_argument("--candidate-records")
    parser.add_argument("--review-policy")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        if args.semantic_contract:
            required = {
                "automatic_comparison": args.automatic_comparison,
                "generation_receipt": args.generation_receipt,
                "pair_validation": args.pair_validation,
                "baseline_records": args.baseline_records,
                "candidate_records": args.candidate_records,
                "review_policy": args.review_policy,
            }
            missing = sorted(name for name, value in required.items() if not value)
            if missing:
                raise WorkflowValidationError(
                    "semantic_comparison_argument_missing",
                    "semantic comparison arguments are incomplete",
                    fields=missing,
                )
            policy_file = _read_json(Path(args.review_policy))
            review_policy = policy_file.get("review", policy_file)
            report = build_semantic_pair_comparison(
                automatic_comparison_path=Path(args.automatic_comparison),
                contract_path=Path(args.semantic_contract),
                generation_receipt_path=Path(args.generation_receipt),
                validation_path=Path(args.pair_validation),
                baseline_records_path=Path(args.baseline_records),
                candidate_records_path=Path(args.candidate_records),
                review_policy=review_policy,
            )
            if args.output:
                Path(args.output).write_bytes(canonical_json_bytes(report))
        else:
            required = {
                "snapshot_root": args.snapshot_root,
                "baseline_run": args.baseline_run,
                "candidate_run": args.candidate_run,
                "experiment": args.experiment,
            }
            missing = sorted(name for name, value in required.items() if not value)
            if missing:
                raise WorkflowValidationError(
                    "variation_comparison_argument_missing",
                    "variation comparison arguments are incomplete",
                    fields=missing,
                )
            report = compare_variation_prompt_pair(
                snapshot_root=Path(args.snapshot_root),
                baseline_run=Path(args.baseline_run),
                candidate_run=Path(args.candidate_run),
                experiment=Path(args.experiment),
            )
            if args.output:
                Path(args.output).write_bytes(canonical_json_bytes(report))
    except (OSError, ValueError, json.JSONDecodeError, WorkflowValidationError) as exc:
        envelope = exc.to_envelope() if isinstance(exc, WorkflowValidationError) else WorkflowValidationError(
            "variation_pair_comparison_failed",
            "variation prompt pair comparison failed",
            exception_type=type(exc).__name__,
        ).to_envelope()
        sys.stderr.buffer.write(canonical_json_bytes(envelope))
        return 2
    sys.stdout.buffer.write(canonical_json_bytes(report))
    return 0 if args.semantic_contract else comparison_exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
