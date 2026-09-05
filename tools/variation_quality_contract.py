from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from tools import analyze_variation_candidates as candidate_analyzer
from tools.analyze_variation_candidates import load_candidate_catalog
from tools.prompt_quality_loop import build_cohort
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


SCHEMA_VERSION = "variation-nonselected-quality-contract/v1"
PROSPECTIVE_SCHEMA_VERSION = "variation-nonselected-quality-contract/v2"
CONTRACT_FIELDS = {
    "schema_version",
    "contract_id",
    "coverage_receipt_path",
    "coverage_receipt_sha256",
    "guard_remediation_receipt_path",
    "guard_remediation_receipt_sha256",
    "current_source_refresh_path",
    "current_source_refresh_sha256",
    "candidate_iteration_path",
    "candidate_iteration_sha256",
    "effective_catalog_sha256",
    "candidate_source_tree_sha256",
    "candidate_ids",
    "coverage_eligibility",
    "cohort",
    "run_contract",
    "surface",
    "authority",
    "contract_sha256",
}
PROSPECTIVE_CONTRACT_FIELDS = (CONTRACT_FIELDS - {
    "coverage_receipt_path", "coverage_receipt_sha256",
    "guard_remediation_receipt_path", "guard_remediation_receipt_sha256",
    "current_source_refresh_path", "current_source_refresh_sha256",
}) | {
    "coverage_snapshot_manifest_path", "coverage_snapshot_manifest_sha256",
    "coverage_snapshot_content_sha256", "coverage_schedule_path", "coverage_schedule_sha256",
}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _hash_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value.strip() or Path(value).is_absolute():
        raise WorkflowValidationError(
            "invalid_variation_quality_contract_path",
            "quality contract path must be a non-empty repository-relative string",
        )
    path = (root / value).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        raise WorkflowValidationError(
            "variation_quality_contract_path_escape",
            "quality contract path escapes repository",
        ) from None
    return path


def validate_variation_quality_contract(
    contract: Mapping[str, Any], *, repository_root: Path
) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    schema = contract.get("schema_version")
    if schema not in {SCHEMA_VERSION, PROSPECTIVE_SCHEMA_VERSION}:
        raise WorkflowValidationError(
            "invalid_variation_quality_contract",
            "non-selected quality contract schema is unsupported",
        )
    expected_fields = PROSPECTIVE_CONTRACT_FIELDS if schema == PROSPECTIVE_SCHEMA_VERSION else CONTRACT_FIELDS
    if set(contract) != expected_fields:
        raise WorkflowValidationError(
            "invalid_variation_quality_contract_fields",
            "non-selected quality contract fields are not closed",
            missing=sorted(expected_fields - set(contract)),
            extra=sorted(set(contract) - expected_fields),
        )
    body = {key: value for key, value in contract.items() if key != "contract_sha256"}
    if _hash_value(body) != contract.get("contract_sha256"):
        raise WorkflowValidationError(
            "variation_quality_contract_hash_mismatch",
            "non-selected quality contract hash drifted",
        )
    authority = contract.get("authority", {})
    surface = contract.get("surface", {})
    if (
        authority
        != {
            "coverage_is_quality_evidence": False,
            "quality_evidence": True,
            "promotion_ready": False,
        }
        or surface
        != {
            "baseline_rows": 80,
            "candidate_rows": 80,
            "kind": "default_fixed_64_16",
            "prompt_selection": "default_unselected",
            "uses_output_metrics_for_selection": False,
        }
    ):
        raise WorkflowValidationError(
            "variation_quality_contract_widens_authority",
            "non-selected quality authority or surface contract drifted",
        )

    if schema == PROSPECTIVE_SCHEMA_VERSION:
        coverage_eligibility = _validate_fresh_coverage(contract, repository_root)
    else:
        coverage_eligibility = _validate_historical_coverage(contract, repository_root)
    _validate_candidate_and_cohort(contract, repository_root)
    return {
        "status": "pass",
        "contract_sha256": contract["contract_sha256"],
        "effective_catalog_sha256": contract["effective_catalog_sha256"],
        "coverage_eligibility": coverage_eligibility,
    }


def _validate_historical_coverage(contract: Mapping[str, Any], repository_root: Path) -> dict[str, Any]:

    coverage_path = _resolve(repository_root, contract.get("coverage_receipt_path"))
    remediation_path = _resolve(repository_root, contract.get("guard_remediation_receipt_path"))
    refresh_path = _resolve(repository_root, contract.get("current_source_refresh_path"))
    coverage = _read_json(coverage_path)
    remediation = _read_json(remediation_path)
    refresh = _read_json(refresh_path)
    refresh_body = {
        key: value for key, value in refresh.items() if key != "refresh_sha256"
    }
    refresh_snapshot_path = _resolve(
        repository_root, refresh.get("snapshot_manifest_path")
    )
    refresh_snapshot = _read_json(refresh_snapshot_path)
    coverage_eligibility = contract.get("coverage_eligibility", {})
    expected_eligibility = {
        "candidate_action_pool_locations": 19,
        "candidate_locations": 19,
        "candidate_subjects": 15,
        "extra_seed_count": 0,
        "fixed_seed_count": 80,
        "prompt_schedule_sha256": refresh.get(
            "prompt_schedule_sha256"
        ),
        "status": "pass",
        "witness_matrix_sha256": refresh.get(
            "witness_matrix_sha256"
        ),
    }
    if (
        _hash_path(coverage_path) != contract.get("coverage_receipt_sha256")
        or coverage.get("terminal_state") != "REJECTED"
        or coverage.get("authority", {}).get("coverage_verdict") != "pass"
        or coverage.get("observed_coverage", {}).get("candidate_locations_unseen") != 0
        or coverage.get("observed_coverage", {}).get("candidate_action_pool_locations_unseen") != 0
        or _hash_path(remediation_path) != contract.get("guard_remediation_receipt_sha256")
        or remediation.get("terminal_state") != "VERIFIED_DIAGNOSTIC"
        or remediation.get("guard_results", {}).get("failures") != []
        or remediation.get("authority", {}).get("coverage_verdict") != "pass"
        or remediation.get("authority", {}).get("diagnostic_pair_verdict") != "pass"
        or remediation.get("authority", {}).get("fixed_quality_verdict") != "reject"
        or remediation.get("authority", {}).get("promotion_ready") is not False
        or remediation.get("local_snapshot", {}).get("witness_certificate_status") != "pass"
        or remediation.get("local_snapshot", {}).get("verified_locations") != 19
        or remediation.get("local_snapshot", {}).get("verified_subjects") != 15
        or remediation.get("local_snapshot", {}).get("fixed_seed_count") != 80
        or remediation.get("local_snapshot", {}).get("extra_seed_count") != 0
        or remediation.get("run_artifacts", {}).get("replay_mismatch_count") != 0
        or _hash_path(refresh_path) != contract.get("current_source_refresh_sha256")
        or refresh.get("schema_version")
        != "variation-current-source-coverage-refresh/v1"
        or _hash_value(refresh_body) != refresh.get("refresh_sha256")
        or refresh.get("status") != "pass"
        or refresh.get("parent_guard_remediation_receipt_sha256")
        != contract.get("guard_remediation_receipt_sha256")
        or refresh.get("candidate_source_tree_sha256")
        != contract.get("candidate_source_tree_sha256")
        or refresh.get("verified_locations") != 19
        or refresh.get("verified_subjects") != 15
        or refresh.get("verified_witnesses") != 19
        or refresh.get("fixed_seed_count") != 80
        or refresh.get("extra_seed_count") != 0
        or refresh.get("coverage_is_quality_evidence") is not False
        or refresh.get("promotion_ready") is not False
        or _hash_path(refresh_snapshot_path) != refresh.get("snapshot_manifest_sha256")
        or refresh_snapshot.get("state") != "SNAPSHOT_READY"
        or not refresh_snapshot.get("prompt_generation_allowed")
        or refresh_snapshot.get("candidate_source_tree_sha256")
        != refresh.get("candidate_source_tree_sha256")
        or refresh_snapshot.get("prompt_schedule_sha256")
        != refresh.get("prompt_schedule_sha256")
        or refresh_snapshot.get("prompt_schedule_verification", {}).get("status")
        != "pass"
        or refresh_snapshot.get("prompt_schedule_verification", {}).get(
            "verification_sha256"
        )
        != refresh.get("certificate_verification_sha256")
        or coverage.get("local_snapshot", {}).get("prompt_schedule_sha256")
        != refresh.get("prompt_schedule_sha256")
        or coverage.get("local_snapshot", {}).get("witness_matrix_sha256")
        != refresh.get("witness_matrix_sha256")
        or coverage_eligibility != expected_eligibility
    ):
        raise WorkflowValidationError(
            "variation_quality_parent_evidence_mismatch",
            "coverage or guard-remediation evidence drifted",
        )
    return coverage_eligibility


def _validate_candidate_and_cohort(contract: Mapping[str, Any], repository_root: Path) -> None:

    iteration_path = _resolve(repository_root, contract.get("candidate_iteration_path"))
    if _hash_path(iteration_path) != contract.get("candidate_iteration_sha256"):
        raise WorkflowValidationError(
            "variation_quality_candidate_iteration_drift",
            "candidate iteration drifted",
        )
    original_root = candidate_analyzer.ROOT
    try:
        candidate_analyzer.ROOT = repository_root
        catalog = load_candidate_catalog(iteration_path)
    finally:
        candidate_analyzer.ROOT = original_root
    if _hash_value(catalog) != contract.get("effective_catalog_sha256"):
        raise WorkflowValidationError(
            "variation_quality_catalog_drift",
            "effective candidate catalog drifted",
        )
    expected_subjects = sorted(str(item["id"]) for item in catalog["subjects"])
    expected_locations = sorted(str(item["id"]) for item in catalog["locations"])
    if (
        contract.get("candidate_ids")
        != {"subjects": expected_subjects, "locations": expected_locations}
    ):
        raise WorkflowValidationError(
            "variation_quality_candidate_identity_drift",
            "quality contract candidate identities drifted",
        )

    cohort = contract.get("cohort", {})
    reproduced = build_cohort(
        int(cohort.get("experiment_seed", 0)),
        str(cohort.get("iteration_id", "")),
        list(cohort.get("control_seeds", [])),
        len(cohort.get("control_seeds", [])) + len(cohort.get("exploration_seeds", [])),
    )
    if reproduced != cohort or len(cohort.get("control_seeds", [])) != 64 or len(cohort.get("exploration_seeds", [])) != 16:
        raise WorkflowValidationError(
            "variation_quality_cohort_drift",
            "non-selected quality cohort is not exact fixed 64+16",
        )


def _validate_fresh_coverage(contract: Mapping[str, Any], repository_root: Path) -> dict[str, Any]:
    # Import lazily: the materializer also validates quality contracts. Coverage
    # snapshots are required to be schedule-only, making this dependency acyclic.
    from tools.materialize_variation_candidate_snapshot import validate_snapshot_manifest

    manifest_path = _resolve(repository_root, contract.get("coverage_snapshot_manifest_path"))
    schedule_path = _resolve(repository_root, contract.get("coverage_schedule_path"))
    if (
        _hash_path(manifest_path) != contract.get("coverage_snapshot_manifest_sha256")
        or _hash_path(schedule_path) != contract.get("coverage_schedule_sha256")
    ):
        raise WorkflowValidationError("variation_quality_coverage_input_drift", "fresh coverage input bytes drifted")
    manifest = _read_json(manifest_path)
    plan = _read_json(manifest_path.parent / "snapshot-plan.json")
    schedule = _read_json(schedule_path)
    inputs = plan.get("inputs", {})
    certificate = manifest.get("prompt_schedule_verification") or {}
    expected_eligibility = {
        "candidate_action_pool_locations": 19,
        "candidate_locations": 19,
        "candidate_subjects": 15,
        "extra_seed_count": 0,
        "fixed_seed_count": 80,
        "prompt_schedule_sha256": schedule.get("schedule_sha256"),
        "witness_matrix_sha256": schedule.get("witness_matrix_sha256"),
        "certificate_verification_sha256": certificate.get("verification_sha256"),
        "status": "pass",
    }
    candidate_ids = contract.get("candidate_ids", {})
    if (
        "quality_contract" in inputs
        or plan.get("baseline_prompt_mode") != "active"
        or plan.get("quality_contract_sha256") is not None
        or manifest.get("quality_contract_sha256") is not None
        or manifest.get("state") != "SNAPSHOT_READY"
        or manifest.get("prompt_generation_allowed") is not True
        or manifest.get("candidate_source_tree_sha256") != contract.get("candidate_source_tree_sha256")
        or manifest.get("candidate_snapshot_content_sha256") != contract.get("coverage_snapshot_content_sha256")
        or manifest.get("candidate_ids") != candidate_ids
        or len(candidate_ids.get("locations", [])) != 19
        or len(candidate_ids.get("subjects", [])) != 15
        or plan.get("effective_catalog_sha256") != contract.get("effective_catalog_sha256")
        or inputs.get("candidate_iteration") != {
            "path": contract.get("candidate_iteration_path"), "sha256": contract.get("candidate_iteration_sha256"),
        }
        or inputs.get("prompt_schedule") != {
            "path": contract.get("coverage_schedule_path"), "sha256": contract.get("coverage_schedule_sha256"),
        }
        or schedule.get("schema_version") != "variation-prompt-final-coverage-schedule/v2"
        or schedule.get("effective_catalog_sha256") != contract.get("effective_catalog_sha256")
        or schedule.get("cohort") != contract.get("cohort")
        or schedule.get("run_contract") != contract.get("run_contract")
        or schedule.get("expected_subjects") != candidate_ids.get("subjects")
        or schedule.get("expected_locations") != candidate_ids.get("locations")
        or manifest.get("prompt_schedule_sha256") != schedule.get("schedule_sha256")
        or certificate.get("status") != "pass"
        or certificate.get("schedule_sha256") != schedule.get("schedule_sha256")
        or certificate.get("witness_matrix_sha256") != schedule.get("witness_matrix_sha256")
        or certificate.get("cohort_hash") != contract.get("cohort", {}).get("cohort_hash")
        or certificate.get("verified_location_count") != 19
        or certificate.get("verified_subject_count") != 15
        or certificate.get("fixed_seed_count") != 80
        or certificate.get("extra_seed_count") != 0
        or certificate.get("coverage_is_quality_evidence") is not False
        or certificate.get("promotion_ready") is not False
        or contract.get("coverage_eligibility") != expected_eligibility
    ):
        raise WorkflowValidationError("variation_quality_fresh_coverage_mismatch", "fresh coverage contract bindings drifted")
    # This recomputes source/content hashes and the plan, then executes the
    # candidate's real witness replay. A stored 'pass' alone is not evidence.
    validate_snapshot_manifest(manifest_path.parent, manifest, source_root=repository_root)
    return expected_eligibility
