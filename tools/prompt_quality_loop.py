"""L0 prompt-quality baseline/generate harness.

The harness is intentionally generation-only: it writes artifacts beneath the
chosen artifact root and never edits source, invokes builders, or mutates git.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
import platform
import socket
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow_widget_validation import load_workflow
from tools.workflow_prompt_runner import (
    WorkflowValidationError,
    build_canonical_record,
    canonical_json_bytes,
    load_profile,
)


LOOP_SCHEMA_VERSION = "prompt-quality-loop/v1"
DEFAULT_ARTIFACT_ROOT = ROOT / "assets" / "results" / "prompt_quality_loop"
SOURCE_MANIFEST_RULES_VERSION = "prompt-quality-source-manifest/v1"
CONTROL_COUNT = 64
EXPLORATION_COUNT = 16
DEFAULT_SAMPLE_COUNT = CONTROL_COUNT + EXPLORATION_COUNT
CONFIRMATION_COUNT = 256
STATE_SCHEMA_VERSION = "prompt-quality-experiment-state/v1"
IMMUTABLE_HYPOTHESIS_FIELDS = (
    "hypothesis",
    "target_metric",
    "guard_metrics",
    "owned_files",
    "policy_version",
    "cohort_version",
    "source_tree_hash",
)
STATE_TRANSITIONS = {
    "DRAFT": {"HYPOTHESIS_LOCKED", "ABORTED"},
    "HYPOTHESIS_LOCKED": {"BASELINE_READY", "ABORTED"},
    "BASELINE_READY": {"CANDIDATE_SNAPSHOT_LOCKED", "ABORTED"},
    "CANDIDATE_SNAPSHOT_LOCKED": {"GENERATED", "ABORTED"},
    "GENERATED": {"ANALYZED", "ABORTED"},
    "ANALYZED": {"COMPARED", "ABORTED"},
    "COMPARED": {"REVIEWED", "ABORTED", "REJECTED"},
    "REVIEWED": {"VERIFIED", "ABORTED", "REJECTED"},
    "VERIFIED": {"PROMOTED", "REJECTED", "ABORTED"},
    "PROMOTED": set(),
    "REJECTED": set(),
    "ABORTED": set(),
}
TRANSITION_REQUIRED_FIELDS = {
    "BASELINE_READY": (
        "baseline_source_tree_hash", "workflow_hash", "policy_hash", "runner_hash",
        "analyzer_hash", "cohort_hash", "artifact_hashes",
    ),
    "CANDIDATE_SNAPSHOT_LOCKED": ("candidate_source_tree_hash", "candidate_patch_hash"),
    "GENERATED": ("candidate_patch_hash", "artifact_hashes"),
    "ANALYZED": ("candidate_patch_hash", "analyzer_hash", "policy_hash", "artifact_hashes"),
    "COMPARED": (
        "candidate_patch_hash", "workflow_hash", "policy_hash", "analyzer_hash", "cohort_hash", "artifact_hashes",
    ),
    "REVIEWED": ("candidate_patch_hash", "review_hash"),
    "VERIFIED": ("candidate_patch_hash", "verification_hash"),
    "PROMOTED": ("candidate_patch_hash", "verdict_hash", "artifact_hashes"),
    "REJECTED": ("candidate_patch_hash", "verdict_hash", "artifact_hashes"),
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _derive_exploration_seed(experiment_seed: int, iteration_id: str, index: int) -> int:
    payload = f"{experiment_seed}:{iteration_id}:{index}"
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:8], "big")


def build_cohort(
    experiment_seed: int = 0,
    iteration_id: str | int = "0",
    control_seeds: Sequence[int] | None = None,
    samples: int = DEFAULT_SAMPLE_COUNT,
) -> dict[str, Any]:
    """Build the standard 64 fixed + 16 rotating deterministic cohort."""

    if samples < 50 or samples > 100:
        raise WorkflowValidationError(
            "invalid_sample_count", "sample count must be between 50 and 100", samples=samples
        )
    if control_seeds is None:
        controls = list(range(CONTROL_COUNT))
    else:
        controls = [int(seed) for seed in control_seeds]
    if len(controls) != len(set(controls)):
        raise WorkflowValidationError("duplicate_seed", "control cohort contains duplicate seeds")
    if samples < len(controls):
        controls = controls[:samples]
    exploration_count = samples - len(controls)
    exploration: list[int] = []
    used = set(controls)
    candidate_index = 0
    while len(exploration) < exploration_count:
        seed = _derive_exploration_seed(int(experiment_seed), str(iteration_id), candidate_index)
        candidate_index += 1
        if seed in used:
            continue
        used.add(seed)
        exploration.append(seed)
    cohort = {
        "control_seeds": controls,
        "exploration_seeds": exploration,
        "experiment_seed": int(experiment_seed),
        "iteration_id": str(iteration_id),
        "schema_version": "prompt-quality-cohort/v1",
    }
    cohort["cohort_hash"] = _sha256_bytes(canonical_json_bytes(cohort))
    validate_cohort(cohort, expected_samples=samples)
    return cohort


def validate_cohort(cohort: Mapping[str, Any], expected_samples: int = DEFAULT_SAMPLE_COUNT) -> None:
    controls = [int(seed) for seed in cohort.get("control_seeds", [])]
    exploration = [int(seed) for seed in cohort.get("exploration_seeds", [])]
    all_seeds = controls + exploration
    if len(all_seeds) != expected_samples:
        raise WorkflowValidationError(
            "missing_seed",
            "cohort does not contain the expected number of seeds",
            actual=len(all_seeds),
            expected=expected_samples,
        )
    if len(all_seeds) != len(set(all_seeds)):
        raise WorkflowValidationError("duplicate_seed", "control and exploration cohorts must be disjoint")
    if expected_samples == DEFAULT_SAMPLE_COUNT and (
        len(controls) != CONTROL_COUNT or len(exploration) != EXPLORATION_COUNT
    ):
        raise WorkflowValidationError(
            "cohort_drift",
            "standard cohort must contain exactly 64 control and 16 exploration seeds",
            control_count=len(controls),
            exploration_count=len(exploration),
        )


def build_confirmation_cohort(excluded_seeds: Sequence[int] | None = None) -> dict[str, Any]:
    excluded = {int(seed) for seed in (excluded_seeds or [])}
    seeds: list[int] = []
    index = 0
    while len(seeds) < CONFIRMATION_COUNT:
        payload = f"prompt-quality-confirmation-v1:{index}".encode("utf-8")
        index += 1
        seed = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
        if seed in excluded or seed in seeds:
            continue
        seeds.append(seed)
    cohort = {
        "confirmation_seeds": seeds,
        "schema_version": "prompt-quality-confirmation-cohort/v1",
    }
    cohort["cohort_hash"] = _sha256_bytes(canonical_json_bytes(cohort))
    return cohort


def _source_files(root: Path) -> list[Path]:
    files: set[Path] = set()
    for path in root.glob("*.py"):
        files.add(path)
    for directory in ("core", "pipeline", "vocab", "rules", "tools"):
        base = root / directory
        if base.exists():
            files.update(path for path in base.rglob("*") if path.is_file())
    assets = root / "assets"
    if assets.exists():
        files.update(path for path in assets.glob("test_*.py") if path.is_file())
        fixtures = assets / "fixtures"
        if fixtures.exists():
            files.update(path for path in fixtures.rglob("*") if path.is_file())
    verification = root / "verification"
    if verification.exists():
        files.update(path for path in verification.rglob("*") if path.is_file())
    files.update(path for path in root.glob("ComfyUI-workflow*.json") if path.is_file())
    return sorted(
        (
            path
            for path in files
            if "__pycache__" not in path.parts
            and ".pytest_cache" not in path.parts
            and "assets/results" not in path.relative_to(root).as_posix()
            and path.suffix not in {".pyc", ".pyo"}
        ),
        key=lambda item: item.relative_to(root).as_posix(),
    )


def build_source_manifest(root: Path = ROOT) -> dict[str, Any]:
    entries = []
    for path in _source_files(root):
        data = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256_bytes(data),
                "size": len(data),
            }
        )
    rules = {
        "include": ["/*.py", "/core/**", "/pipeline/**", "/vocab/**", "/rules/**", "/tools/**", "/assets/test_*.py", "/assets/fixtures/**", "/verification/**", "/ComfyUI-workflow*.json"],
        "exclude": ["/.git/**", "/.omx/**", "/assets/results/**", "**/__pycache__/**", "**/*.pyc", "external checkouts"],
        "version": SOURCE_MANIFEST_RULES_VERSION,
    }
    manifest = {"entries": entries, "rules": rules}
    manifest["source_tree_hash"] = _sha256_bytes(canonical_json_bytes(manifest))
    return manifest


def _records_bytes(records: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(record) for record in records)


def replay_records(
    workflow: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    profile: Any = None,
    overrides: Mapping[Any, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    mismatches = []
    for expected in records:
        seed = int(expected["run_seed"])
        actual = build_canonical_record(
            workflow,
            seed,
            profile=profile,
            overrides=overrides,
            cohort=expected.get("cohort"),
        )
        if canonical_json_bytes(actual) != canonical_json_bytes(expected):
            mismatches.append(seed)
    return {
        "checked": len(records),
        "mismatch_count": len(mismatches),
        "mismatched_seeds": mismatches,
        "status": "pass" if not mismatches else "fail",
    }


def _atomic_write(path: Path, content: bytes) -> None:
    staging = path.parent / ".staging"
    staging.mkdir(parents=True, exist_ok=True)
    temporary = staging / f"{path.name}.{uuid.uuid4().hex}.tmp"
    temporary.write_bytes(content)
    os.replace(temporary, path)


def _artifact_hashes(path: Path) -> dict[str, str]:
    return {
        item.relative_to(path).as_posix(): _sha256_bytes(item.read_bytes())
        for item in sorted(path.rglob("*"), key=lambda value: value.as_posix())
        if item.is_file() and ".staging" not in item.parts and item.name != ".writer.lock"
    }


def _state_record_hash(record: Mapping[str, Any]) -> str:
    payload = dict(record)
    payload.pop("record_hash", None)
    return _sha256_bytes(canonical_json_bytes(payload))


def load_state_records(experiment_dir: str | Path) -> list[dict[str, Any]]:
    """Load and verify append-only transition records.

    Corruption, sequence gaps and hash-chain drift fail closed instead of being
    treated as resumable state.
    """

    state_dir = Path(experiment_dir) / "state"
    if not state_dir.exists():
        return []
    records: list[dict[str, Any]] = []
    for expected_sequence, path in enumerate(sorted(state_dir.glob("*.json")), start=1):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkflowValidationError(
                "corrupt_state_record", "experiment state record is unreadable", path=str(path), exception_type=type(exc).__name__
            ) from exc
        if not isinstance(record, dict) or int(record.get("sequence", -1)) != expected_sequence:
            raise WorkflowValidationError(
                "state_sequence_gap", "experiment state sequence is not contiguous", expected=expected_sequence, path=str(path)
            )
        if record.get("record_hash") != _state_record_hash(record):
            raise WorkflowValidationError("state_hash_mismatch", "experiment state record hash does not match", path=str(path))
        previous_hash = records[-1]["record_hash"] if records else None
        if record.get("previous_record_hash") != previous_hash:
            raise WorkflowValidationError("state_hash_mismatch", "experiment state hash chain is broken", path=str(path))
        records.append(record)
    return records


@contextmanager
def experiment_writer_lock(experiment_dir: str | Path, transition_id: str):
    """Acquire an experiment-scoped OS-exclusive single-writer lock."""

    experiment_path = Path(experiment_dir)
    experiment_path.mkdir(parents=True, exist_ok=True)
    lock_path = experiment_path / ".writer.lock"
    lock_payload = canonical_json_bytes({
        "host": socket.gethostname(),
        "owner": str(uuid.uuid4()),
        "pid": os.getpid(),
        "transition_id": transition_id,
    })
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise WorkflowValidationError(
            "experiment_locked", "another writer owns this experiment", lock_path=str(lock_path)
        ) from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(lock_payload)
            handle.flush()
            os.fsync(handle.fileno())
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _validate_hypothesis_payload(payload: Mapping[str, Any]) -> None:
    missing = [field for field in IMMUTABLE_HYPOTHESIS_FIELDS if field not in payload]
    if missing:
        raise WorkflowValidationError(
            "incomplete_hypothesis_lock", "hypothesis lock omits required immutable fields", missing_fields=missing
        )
    if not isinstance(payload.get("hypothesis"), str) or not payload["hypothesis"].strip():
        raise WorkflowValidationError("invalid_hypothesis", "one non-empty primary hypothesis is required")
    if not isinstance(payload.get("target_metric"), str) or not payload["target_metric"].strip():
        raise WorkflowValidationError("invalid_target_metric", "exactly one target metric path is required")
    for field in ("guard_metrics", "owned_files"):
        if not isinstance(payload.get(field), list) or not all(isinstance(item, str) for item in payload[field]):
            raise WorkflowValidationError("invalid_hypothesis_lock", f"{field} must be an array of strings", field=field)
    if not _is_sha256(payload.get("source_tree_hash")):
        raise WorkflowValidationError("invalid_content_hash", "source_tree_hash must be a lowercase SHA-256 value")
    for field in ("policy_version", "cohort_version"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise WorkflowValidationError("invalid_hypothesis_lock", f"{field} must be a non-empty string", field=field)
    for owned_file in payload["owned_files"]:
        owned_path = Path(owned_file)
        if owned_path.is_absolute() or ".." in owned_path.parts:
            raise WorkflowValidationError(
                "invalid_owned_file", "owned files must be repository-relative paths without parent traversal", path=owned_file
            )


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _validate_transition_payload(state: str, payload: Mapping[str, Any]) -> None:
    required = TRANSITION_REQUIRED_FIELDS.get(state, ())
    missing = [field for field in required if field not in payload]
    if missing:
        raise WorkflowValidationError(
            "missing_transition_hashes", "transition omits required reconstructability fields", state=state, missing_fields=missing
        )
    for field in required:
        if field == "artifact_hashes":
            hashes = payload[field]
            if not isinstance(hashes, Mapping) or not hashes or not all(
                isinstance(name, str) and _is_sha256(value) for name, value in hashes.items()
            ):
                raise WorkflowValidationError(
                    "invalid_content_hash", "artifact_hashes must map artifact names to SHA-256 values", state=state
                )
        elif field.endswith("_hash") and not _is_sha256(payload[field]):
            raise WorkflowValidationError(
                "invalid_content_hash", "transition content hashes must be lowercase SHA-256 values", state=state, field=field
            )


def _validate_published_artifacts(payload: Mapping[str, Any], artifact_root: Path) -> None:
    hashes = payload.get("artifact_hashes")
    if hashes is None:
        return
    paths = payload.get("artifact_paths")
    if not isinstance(paths, Mapping) or set(paths) != set(hashes):
        raise WorkflowValidationError(
            "artifact_paths_invalid", "artifact_paths must map every artifact hash label to one repository-relative file"
        )
    resolved_root = artifact_root.resolve()
    for label, expected_hash in hashes.items():
        relative = Path(str(paths[label]))
        if relative.is_absolute() or ".." in relative.parts:
            raise WorkflowValidationError("artifact_path_invalid", "published artifact path is outside scope", artifact=label)
        resolved = (resolved_root / relative).resolve()
        try:
            resolved.relative_to(resolved_root)
        except ValueError:
            raise WorkflowValidationError("artifact_path_invalid", "published artifact path is outside scope", artifact=label) from None
        if not resolved.is_file():
            raise WorkflowValidationError("artifact_missing", "published artifact does not exist", artifact=label, path=str(relative))
        actual_hash = _sha256_bytes(resolved.read_bytes())
        if actual_hash != expected_hash:
            raise WorkflowValidationError(
                "artifact_hash_mismatch", "published artifact content does not match transition hash",
                artifact=label, expected=expected_hash, actual=actual_hash,
            )


def commit_transition(
    experiment_dir: str | Path,
    transition_id: str,
    next_state: str,
    payload: Mapping[str, Any],
    *,
    artifact_root: str | Path,
) -> dict[str, Any]:
    """Atomically append one validated experiment transition.

    ``transition_id`` is an idempotency key.  Reusing it with another payload
    fails; an identical transition returns the already committed record.
    """

    experiment_path, _ = _assert_artifact_scope(Path(experiment_dir), Path(artifact_root))
    if not transition_id or any(character in transition_id for character in "/\\"):
        raise WorkflowValidationError("invalid_transition_id", "transition id must be a non-empty path-safe value")
    if next_state not in STATE_TRANSITIONS:
        raise WorkflowValidationError("invalid_state", "unknown experiment state", state=next_state)
    requested_payload = json.loads(canonical_json_bytes(dict(payload)))
    with experiment_writer_lock(experiment_path, transition_id):
        records = load_state_records(experiment_path)
        for existing in records:
            if existing.get("transition_id") == transition_id:
                if existing.get("state") == next_state and existing.get("payload") == requested_payload:
                    return existing
                raise WorkflowValidationError(
                    "transition_id_conflict", "transition id was already committed with a different payload", transition_id=transition_id
                )
        previous_state = records[-1]["state"] if records else "DRAFT"
        if next_state not in STATE_TRANSITIONS[previous_state]:
            raise WorkflowValidationError(
                "invalid_state_transition", "requested state does not follow the current state", previous_state=previous_state, next_state=next_state
            )
        if next_state == "HYPOTHESIS_LOCKED":
            _validate_hypothesis_payload(requested_payload)
        _validate_transition_payload(next_state, requested_payload)
        _validate_published_artifacts(requested_payload, Path(artifact_root))
        locked = next((item["payload"] for item in records if item["state"] == "HYPOTHESIS_LOCKED"), None)
        if locked is not None:
            changed = [
                field for field in IMMUTABLE_HYPOTHESIS_FIELDS
                if field in requested_payload and requested_payload[field] != locked[field]
            ]
            if changed:
                raise WorkflowValidationError(
                    "immutable_hypothesis_changed", "hypothesis lock fields cannot change after lock", changed_fields=changed
                )
            if "baseline_source_tree_hash" in requested_payload and requested_payload["baseline_source_tree_hash"] != locked["source_tree_hash"]:
                raise WorkflowValidationError(
                    "baseline_source_drift", "baseline source does not match the immutable hypothesis source snapshot",
                    locked=locked["source_tree_hash"], actual=requested_payload["baseline_source_tree_hash"]
                )
        snapshot = next((item["payload"] for item in records if item["state"] == "CANDIDATE_SNAPSHOT_LOCKED"), None)
        if snapshot is not None and "candidate_patch_hash" in requested_payload:
            if requested_payload["candidate_patch_hash"] != snapshot.get("candidate_patch_hash"):
                raise WorkflowValidationError(
                    "candidate_patch_drift", "candidate patch changed after snapshot lock",
                    locked=snapshot.get("candidate_patch_hash"), actual=requested_payload["candidate_patch_hash"]
                )
        sequence = len(records) + 1
        record = {
            "payload": requested_payload,
            "previous_record_hash": records[-1]["record_hash"] if records else None,
            "previous_state": previous_state,
            "schema_version": STATE_SCHEMA_VERSION,
            "sequence": sequence,
            "state": next_state,
            "transition_id": transition_id,
        }
        record["record_hash"] = _state_record_hash(record)
        state_dir = experiment_path / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        filename = state_dir / f"{sequence:04d}-{transition_id}.json"
        _atomic_write(filename, canonical_json_bytes(record))
        return record


def recover_experiment(
    experiment_dir: str | Path,
    *,
    artifact_root: str | Path,
    transition_id: str | None = None,
    next_state: str | None = None,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Recover an interrupted transition without treating orphan files as committed.

    A caller that published artifacts but missed the state commit supplies the
    intended transition and payload; the normal idempotent commit path finishes
    it.  Temporary files left before publication are quarantined and the active
    experiment is marked ABORTED.
    """

    experiment_path, _ = _assert_artifact_scope(Path(experiment_dir), Path(artifact_root))
    staging_dir = experiment_path / ".staging"
    orphan_paths = sorted(path for path in staging_dir.rglob("*") if path.is_file()) if staging_dir.exists() else []
    if orphan_paths:
        recovery_id = f"recovery-{uuid.uuid4().hex}"
        recovery_dir = experiment_path / "recovery" / recovery_id
        artifact_hashes: dict[str, str] = {}
        artifact_paths: dict[str, str] = {}
        with experiment_writer_lock(experiment_path, recovery_id):
            recovery_dir.mkdir(parents=True, exist_ok=True)
            for index, orphan in enumerate(orphan_paths, start=1):
                content = orphan.read_bytes()
                artifact_hashes[f"orphan-{index:04d}"] = _sha256_bytes(content)
                recovered_path = recovery_dir / f"orphan-{index:04d}.tmp"
                os.replace(orphan, recovered_path)
                artifact_paths[f"orphan-{index:04d}"] = recovered_path.relative_to(Path(artifact_root).resolve()).as_posix()
            report = {
                "artifact_hashes": artifact_hashes,
                "artifact_paths": artifact_paths,
                "recovery_id": recovery_id,
                "schema_version": "prompt-quality-recovery/v1",
                "status": "quarantined",
            }
            _atomic_write(recovery_dir / "recovery.json", canonical_json_bytes(report))
        records = load_state_records(experiment_path)
        previous_state = records[-1]["state"] if records else "DRAFT"
        state_record = None
        if "ABORTED" in STATE_TRANSITIONS.get(previous_state, set()):
            state_record = commit_transition(
                experiment_path,
                recovery_id,
                "ABORTED",
                {"artifact_hashes": artifact_hashes, "artifact_paths": artifact_paths, "recovery_id": recovery_id},
                artifact_root=artifact_root,
            )
        return {"recovery": report, "state_record": state_record}

    if transition_id and next_state and payload is not None:
        record = commit_transition(
            experiment_path,
            transition_id,
            next_state,
            payload,
            artifact_root=artifact_root,
        )
        return {"recovery": {"status": "committed"}, "state_record": record}
    return {"recovery": {"status": "clean"}, "state_record": None}


def _assert_artifact_scope(path: Path, artifact_root: Path) -> tuple[Path, Path]:
    resolved_path = path.resolve()
    resolved_root = artifact_root.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError:
        raise WorkflowValidationError(
            "write_scope_violation",
            "output directory must be beneath the configured artifact root",
            artifact_root=str(resolved_root),
            output_dir=str(resolved_path),
        ) from None
    return resolved_path, resolved_root


def generate_run(
    workflow: Mapping[str, Any],
    output_dir: Path,
    *,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
    experiment_seed: int = 0,
    iteration_id: str | int = "0",
    control_seeds: Sequence[int] | None = None,
    samples: int = DEFAULT_SAMPLE_COUNT,
    profile: Any = None,
    overrides: Mapping[Any, Mapping[str, Any]] | None = None,
    run_kind: str = "generate",
    verify_replay: bool = True,
) -> dict[str, Any]:
    """Generate canonical records plus separated manifest, metrics and telemetry."""

    output_dir, artifact_root = _assert_artifact_scope(output_dir, artifact_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_profile = load_profile(profile)
    cohort = build_cohort(experiment_seed, iteration_id, control_seeds, samples)
    cohort_by_seed = {
        **{seed: "control" for seed in cohort["control_seeds"]},
        **{seed: "exploration" for seed in cohort["exploration_seeds"]},
    }
    seeds = cohort["control_seeds"] + cohort["exploration_seeds"]
    source_before = build_source_manifest()
    records = []
    durations = []
    started = time.perf_counter()
    for seed in seeds:
        node_started = time.perf_counter()
        records.append(
            build_canonical_record(
                workflow,
                seed,
                profile=selected_profile,
                overrides=overrides,
                cohort=cohort_by_seed[seed],
            )
        )
        durations.append(
            {"duration_ms": round((time.perf_counter() - node_started) * 1000, 3), "run_seed": seed}
        )
    replay = replay_records(workflow, records, selected_profile, overrides) if verify_replay else {
        "checked": 0,
        "mismatch_count": 0,
        "mismatched_seeds": [],
        "status": "not_run",
    }
    if replay["status"] == "fail":
        raise WorkflowValidationError(
            "deterministic_replay_mismatch",
            "canonical record replay was not byte-identical",
            mismatched_seeds=replay["mismatched_seeds"],
        )
    source_after = build_source_manifest()
    if source_before["source_tree_hash"] != source_after["source_tree_hash"]:
        raise WorkflowValidationError(
            "protected_source_changed",
            "protected source content changed while the loop command was running",
            before=source_before["source_tree_hash"],
            after=source_after["source_tree_hash"],
        )

    records_content = _records_bytes(records)
    workflow_hash = records[0]["base_workflow_hash"] if records else ""
    effective_hash = records[0]["effective_workflow_hash"] if records else ""
    metrics = {
        "cohort_hash": cohort["cohort_hash"],
        "control_count": len(cohort["control_seeds"]),
        "effective_workflow_hash": effective_hash,
        "exploration_count": len(cohort["exploration_seeds"]),
        "record_count": len(records),
        "records_sha256": _sha256_bytes(records_content),
        "replay": replay,
        "schema_version": "prompt-quality-metrics/v1",
        "workflow_hash": workflow_hash,
    }
    metrics_content = canonical_json_bytes(metrics)
    telemetry = {
        "run_duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "runs": durations,
        "schema_version": "prompt-quality-telemetry/v1",
    }
    manifest = {
        "artifact_hashes": {
            "metrics.json": _sha256_bytes(metrics_content),
            "records.jsonl": _sha256_bytes(records_content),
            "source-manifest.json": _sha256_bytes(canonical_json_bytes(source_before)),
            "telemetry.json": _sha256_bytes(canonical_json_bytes(telemetry)),
        },
        "cohort_hash": cohort["cohort_hash"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dirty_state_marker": "content-addressed-snapshot",
        "effective_workflow_hash": effective_hash,
        "host": {"hostname": socket.gethostname(), "platform": platform.platform(), "python": platform.python_version()},
        "profile_hash": selected_profile.hash,
        "run_id": output_dir.name,
        "run_kind": run_kind,
        "schema_version": LOOP_SCHEMA_VERSION,
        "source_tree_hash": source_before["source_tree_hash"],
        "workflow_hash": workflow_hash,
    }
    _atomic_write(output_dir / "records.jsonl", records_content)
    _atomic_write(output_dir / "metrics.json", metrics_content)
    _atomic_write(output_dir / "source-manifest.json", canonical_json_bytes(source_before))
    _atomic_write(output_dir / "telemetry.json", canonical_json_bytes(telemetry))
    _atomic_write(output_dir / "run-manifest.json", canonical_json_bytes(manifest))
    return {
        "cohort": cohort,
        "manifest": manifest,
        "metrics": metrics,
        "output_dir": output_dir,
        "records": records,
        "telemetry": telemetry,
    }


def _load_json_object(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise WorkflowValidationError("invalid_configuration", "configuration root must be an object", path=str(path))
    return value


def _read_control_seeds(path: str | Path | None) -> Sequence[int] | None:
    if path is None:
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(value, dict):
        value = value.get("control_seeds")
    if not isinstance(value, list):
        raise WorkflowValidationError("invalid_cohort", "control seed file must contain an array")
    return [int(seed) for seed in value]


def _add_generation_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workflow", default=str(ROOT / "ComfyUI-workflow-context.json"))
    parser.add_argument("--profile")
    parser.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    parser.add_argument("--output-dir")
    parser.add_argument("--run-id")
    parser.add_argument("--experiment-seed", type=int, default=0)
    parser.add_argument("--iteration-id", default="0")
    parser.add_argument("--control-seeds")
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLE_COUNT)
    parser.add_argument("--overrides")
    parser.add_argument("--no-replay", action="store_true")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt quality engineering loop.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    baseline = subparsers.add_parser("baseline")
    _add_generation_args(baseline)
    generate = subparsers.add_parser("generate")
    _add_generation_args(generate)
    generate.add_argument("--experiment", help="JSON manifest whose values are used as generation defaults")
    analyze = subparsers.add_parser("analyze")
    analyze.add_argument("--run-id")
    analyze.add_argument("--run-dir")
    analyze.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    analyze.add_argument("--policy")
    compare = subparsers.add_parser("compare")
    compare.add_argument("--before", required=True)
    compare.add_argument("--after", required=True)
    compare.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    compare.add_argument("--policy", required=True)
    compare.add_argument("--experiment", required=True)
    compare.add_argument("--output", required=True)
    promote = subparsers.add_parser("promote-check")
    promote.add_argument("--comparison", required=True)
    promote.add_argument("--review")
    promote.add_argument("--verification")
    promote.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    promote.add_argument("--output", required=True)
    transition = subparsers.add_parser("transition")
    transition.add_argument("--experiment-dir", required=True)
    transition.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    transition.add_argument("--transition-id", required=True)
    transition.add_argument("--state", required=True, choices=sorted(STATE_TRANSITIONS))
    transition.add_argument("--payload", required=True)
    confirmation = subparsers.add_parser("confirmation")
    confirmation.add_argument("--objective", required=True, choices=("g004", "g005", "g006"))
    confirmation.add_argument("--output-dir", required=True)
    confirmation.add_argument("--seed-file", required=True)
    recover = subparsers.add_parser("recover")
    recover.add_argument("--experiment-dir", required=True)
    recover.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    recover.add_argument("--transition-id")
    recover.add_argument("--state", choices=sorted(STATE_TRANSITIONS))
    recover.add_argument("--payload")
    return parser.parse_args(argv)


def _resolve_run_dir(value: str | None, artifact_root: Path) -> Path:
    if not value:
        raise WorkflowValidationError("missing_run_id", "analyze requires --run-id or --run-dir")
    candidate = Path(value)
    if not candidate.is_absolute() and candidate.parent == Path("."):
        candidate = artifact_root / candidate
    resolved, _ = _assert_artifact_scope(candidate, artifact_root)
    return resolved


def _write_loop_artifact(path: Path, artifact_root: Path, value: Mapping[str, Any]) -> Path:
    if not path.is_absolute():
        candidate = path.resolve()
        try:
            candidate.relative_to(artifact_root.resolve())
        except ValueError:
            path = artifact_root / path
    resolved, _ = _assert_artifact_scope(path, artifact_root)
    _atomic_write(resolved, canonical_json_bytes(value))
    return resolved


def _record_analysis_hashes(run_dir: Path, result: Mapping[str, Any]) -> None:
    manifest_path = run_dir / "run-manifest.json"
    manifest = _load_json_object(manifest_path)
    metrics_bytes = canonical_json_bytes(result["metrics"])
    issues_bytes = canonical_json_bytes(result["issues"])
    manifest["analyzer_version"] = result["metrics"].get("analyzer_version")
    manifest["policy_version"] = result["metrics"].get("policy_version")
    manifest.setdefault("artifact_hashes", {})["metrics.json"] = _sha256_bytes(metrics_bytes)
    manifest["artifact_hashes"]["issues.json"] = _sha256_bytes(issues_bytes)
    _atomic_write(manifest_path, canonical_json_bytes(manifest))


def _assert_source_unchanged(before: Mapping[str, Any]) -> None:
    after = build_source_manifest()
    if before.get("source_tree_hash") != after.get("source_tree_hash"):
        raise WorkflowValidationError(
            "protected_source_changed",
            "protected source content changed while the loop command was running",
            before=before.get("source_tree_hash"),
            after=after.get("source_tree_hash"),
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "confirmation":
            from tools.build_prompt_quality_confirmation import build_confirmation

            result = build_confirmation(
                objective=args.objective,
                output_dir=Path(args.output_dir),
                seed_file=Path(args.seed_file),
            )
            sys.stdout.buffer.write(canonical_json_bytes(result))
            return 0

        if args.command == "recover":
            payload = _load_json_object(args.payload) if args.payload else None
            result = recover_experiment(
                args.experiment_dir,
                artifact_root=args.artifact_root,
                transition_id=args.transition_id,
                next_state=args.state,
                payload=payload,
            )
            sys.stdout.buffer.write(canonical_json_bytes(result))
            return 0

        if args.command == "transition":
            record = commit_transition(
                args.experiment_dir,
                args.transition_id,
                args.state,
                _load_json_object(args.payload),
                artifact_root=args.artifact_root,
            )
            sys.stdout.buffer.write(canonical_json_bytes(record))
            return 0

        if args.command == "analyze":
            from tools.analyze_prompt_quality import write_analysis

            artifact_root = Path(args.artifact_root)
            run_dir = _resolve_run_dir(args.run_dir or args.run_id, artifact_root)
            source_before = build_source_manifest()
            result = write_analysis(
                run_dir / "records.jsonl",
                run_dir / "metrics.json",
                run_dir / "issues.json",
                policy_path=args.policy,
            )
            _record_analysis_hashes(run_dir, result)
            _assert_source_unchanged(source_before)
            sys.stdout.buffer.write(canonical_json_bytes({"output_dir": str(run_dir), "result": result}))
            return 0

        if args.command == "compare":
            from tools.compare_prompt_quality import compare_runs

            artifact_root = Path(args.artifact_root)
            source_before = build_source_manifest()
            before_dir = _resolve_run_dir(args.before, artifact_root)
            after_dir = _resolve_run_dir(args.after, artifact_root)
            result = compare_runs(before_dir, after_dir, policy=args.policy, experiment=args.experiment)
            output_path = _write_loop_artifact(Path(args.output), artifact_root, result)
            _assert_source_unchanged(source_before)
            sys.stdout.buffer.write(canonical_json_bytes({"output": str(output_path), "verdict": result["automatic_verdict"]}))
            return 0

        if args.command == "promote-check":
            from tools.compare_prompt_quality import promote_check

            artifact_root = Path(args.artifact_root)
            source_before = build_source_manifest()
            result = promote_check(args.comparison, review=args.review, verification=args.verification)
            output_path = _write_loop_artifact(Path(args.output), artifact_root, result)
            _assert_source_unchanged(source_before)
            sys.stdout.buffer.write(canonical_json_bytes({"output": str(output_path), "verdict": result["verdict"]}))
            return 0

        experiment = _load_json_object(getattr(args, "experiment", None))
        workflow_path = Path(experiment.get("workflow", args.workflow))
        artifact_root = Path(experiment.get("artifact_root", args.artifact_root))
        run_id = experiment.get("run_id", args.run_id) or f"{args.command}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        output_dir = Path(experiment.get("output_dir", args.output_dir or artifact_root / run_id))
        overrides = experiment.get("overrides", _load_json_object(args.overrides))
        result = generate_run(
            load_workflow(workflow_path),
            output_dir,
            artifact_root=artifact_root,
            experiment_seed=int(experiment.get("experiment_seed", args.experiment_seed)),
            iteration_id=experiment.get("iteration_id", args.iteration_id),
            control_seeds=_read_control_seeds(experiment.get("control_seeds_file", args.control_seeds)),
            samples=int(experiment.get("samples", args.samples)),
            profile=experiment.get("profile", args.profile),
            overrides=overrides,
            run_kind=args.command,
            verify_replay=not bool(experiment.get("no_replay", args.no_replay)),
        )
        print(json.dumps({"output_dir": str(result["output_dir"]), "run_id": result["manifest"]["run_id"]}, ensure_ascii=False))
        return 0
    except (OSError, json.JSONDecodeError, WorkflowValidationError) as exc:
        if isinstance(exc, WorkflowValidationError):
            envelope = exc.to_envelope()
        else:
            envelope = WorkflowValidationError(
                "configuration_error", "could not load loop input", exception_type=type(exc).__name__
            ).to_envelope()
        sys.stderr.buffer.write(canonical_json_bytes(envelope))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
