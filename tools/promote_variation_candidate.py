from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

PREFLIGHT_SCHEMA = "variation-v150-promotion-preflight/v1"
PROMOTION_SCHEMA = "variation-v150-promotion-receipt/v1"
ROLLBACK_SCHEMA = "variation-v150-rollback-receipt/v1"
JOURNAL_SCHEMA = "variation-v150-promotion-journal/v1"
ALLOWLIST = {
    "prompts.jsonl", "assets/compatibility_review.csv", "vocab/data/action_pools.json",
    "vocab/data/background_packs.json", "vocab/data/location_axis_profiles.json",
    "vocab/data/scene_compatibility.json", "vocab/data/variation_scope.json",
    "vocab/source/action_pools/_manifest.json",
}
ARTIFACT_SCHEMAS = {
    "automatic_comparison": ("variation-nonselected-quality-comparison/v2",),
    "semantic_comparison": ("prompt-quality-comparison/v2", "prompt-quality-comparison/v3", "prompt-quality-comparison/v4"),
    "review": ("prompt-quality-review/v4", "prompt-quality-review/v5", "prompt-quality-review/v6"),
    "confirmation": ("variation-v150-confirmation-bundle/v1",),
    "verification": ("variation-v150-verification-receipt/v1",),
}


class PromotionError(RuntimeError):
    def __init__(self, code: str, message: str, **details: Any):
        super().__init__(message); self.code, self.message, self.details = code, message, details
    def envelope(self) -> dict[str, Any]:
        return {"schema_version": "variation-v150-promotion-error/v1", "code": self.code, "message": self.message, "details": self.details}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def value_hash(value: Any) -> str: return hashlib.sha256(canonical_bytes(value)).hexdigest()
def file_hash(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise PromotionError("artifact_not_object", "promotion artifact must be a JSON object", path=str(path))
    return value


def _write_fsync(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(canonical_bytes(value)); handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, path)
    try:
        directory_fd = os.open(str(path.parent), os.O_RDONLY)
        try: os.fsync(directory_fd)
        finally: os.close(directory_fd)
    except OSError:
        pass


def _relative_files(root: Path) -> list[Path]:
    return sorted((path.relative_to(root) for path in root.rglob("*") if path.is_file() and ".promotion-state" not in path.parts), key=lambda p: p.as_posix())


def default_source_hash(root: Path) -> str:
    try:
        from tools.prompt_quality_loop import build_source_manifest
        return str(build_source_manifest(root)["source_tree_hash"])
    except (ImportError, KeyError, TypeError):
        return value_hash([{"path": p.as_posix(), "sha256": file_hash(root / p)} for p in _relative_files(root)])


def default_content_hash(root: Path) -> str:
    try:
        from tools.materialize_variation_candidate_snapshot import _hash_value, _manifest_entries
        return str(_hash_value(_manifest_entries(root)))
    except (ImportError, TypeError):
        return value_hash({p.as_posix(): file_hash(root / p) for p in _relative_files(root)})


def _action_source_allowlist(manifest: Mapping[str, Any]) -> set[str]:
    locations = manifest.get("candidate_ids", {}).get("locations", [])
    if not isinstance(locations, list) or len(locations) != 19 or len(set(locations)) != 19:
        raise PromotionError("candidate_location_allowlist_invalid", "snapshot must bind exactly 19 candidate locations")
    return {f"vocab/source/action_pools/{location}.json" for location in locations}


def _validate_artifact(name: str, path: Path, experiment_id: str, candidate_source_hash: str, candidate_content_hash: str) -> dict[str, Any]:
    value = _read_json(path)
    if value.get("schema_version") not in ARTIFACT_SCHEMAS[name]:
        raise PromotionError("artifact_schema_mismatch", "unknown promotion artifact schema", artifact=name, schema=value.get("schema_version"))
    if name != "automatic_comparison" and value.get("experiment_id") != experiment_id:
        raise PromotionError("artifact_experiment_mismatch", "promotion artifact mixes experiments", artifact=name)
    if name == "automatic_comparison" and value.get("experiment_id") not in {None, experiment_id}:
        raise PromotionError("artifact_experiment_mismatch", "automatic comparison explicitly binds another experiment", artifact=name)
    terminal = value.get("status", value.get("validation_verdict", value.get("quality_verdict")))
    verdict = value.get("verdict", value.get("quality_verdict"))
    accepted = terminal in {"pass", "complete", "verified"} or verdict in {"pass", "promote"}
    if not accepted:
        raise PromotionError("artifact_not_passing", "promotion artifact is not terminal-pass", artifact=name, status=terminal, verdict=verdict)
    source_values = [value.get(key) for key in ("candidate_source_tree_sha256", "candidate_source_tree_hash", "source_tree_hash") if value.get(key) is not None]
    content_values = [value.get(key) for key in ("candidate_snapshot_content_sha256", "snapshot_content_sha256") if value.get(key) is not None]
    if source_values and any(item != candidate_source_hash for item in source_values):
        raise PromotionError("artifact_candidate_source_mismatch", "artifact binds another candidate source", artifact=name)
    if content_values and any(item != candidate_content_hash for item in content_values):
        raise PromotionError("artifact_candidate_content_mismatch", "artifact binds another candidate content", artifact=name)
    return {"path": str(path), "sha256": file_hash(path), "schema_version": value["schema_version"]}


def build_preflight(*, active_root: Path, candidate_root: Path, snapshot_manifest_path: Path, artifact_paths: Mapping[str, Path], experiment_id: str, source_hasher: Callable[[Path], str] = default_source_hash, content_hasher: Callable[[Path], str] = default_content_hash) -> dict[str, Any]:
    active_root, candidate_root = active_root.resolve(), candidate_root.resolve()
    manifest = _read_json(snapshot_manifest_path)
    if manifest.get("schema_version") != "variation-candidate-snapshot/v1" or manifest.get("state") != "SNAPSHOT_READY" or manifest.get("active_source_unchanged") is not True:
        raise PromotionError("snapshot_not_promotion_ready", "snapshot manifest is not frozen and non-mutating")
    allowlist = ALLOWLIST | _action_source_allowlist(manifest)
    changed = manifest.get("changed_files")
    if not isinstance(changed, list) or set(changed) != allowlist or len(changed) != len(allowlist):
        raise PromotionError("snapshot_changed_files_not_allowlisted", "snapshot changed_files must equal the closed promotion allowlist", extra=sorted(set(changed or []) - allowlist), missing=sorted(allowlist - set(changed or [])))
    active_source, active_content = source_hasher(active_root), content_hasher(active_root)
    candidate_source, candidate_content = source_hasher(candidate_root), content_hasher(candidate_root)
    if active_source != manifest.get("baseline_source_tree_sha256") or active_content != manifest.get("baseline_snapshot_content_sha256"):
        raise PromotionError("active_baseline_drift", "active source-tree or snapshot-content hash drifted")
    if candidate_source != manifest.get("candidate_source_tree_sha256") or candidate_content != manifest.get("candidate_snapshot_content_sha256"):
        raise PromotionError("candidate_snapshot_drift", "candidate source-tree or snapshot-content hash drifted")
    missing = sorted(name for name in ARTIFACT_SCHEMAS if name not in artifact_paths)
    extra = sorted(set(artifact_paths) - set(ARTIFACT_SCHEMAS))
    if missing or extra: raise PromotionError("receipt_dag_incomplete", "promotion receipt DAG input set is not exact", missing=missing, extra=extra)
    artifacts = {name: _validate_artifact(name, Path(artifact_paths[name]), experiment_id, candidate_source, candidate_content) for name in ARTIFACT_SCHEMAS}
    semantic_hash, review_hash = artifacts["semantic_comparison"]["sha256"], artifacts["review"]["sha256"]
    comparison = _read_json(Path(artifact_paths["semantic_comparison"])); review = _read_json(Path(artifact_paths["review"])); confirmation = _read_json(Path(artifact_paths["confirmation"])); verification = _read_json(Path(artifact_paths["verification"]))
    expected_review_schema = {
        "prompt-quality-comparison/v2": "prompt-quality-review/v4",
        "prompt-quality-comparison/v3": "prompt-quality-review/v5",
        "prompt-quality-comparison/v4": "prompt-quality-review/v6",
    }[comparison["schema_version"]]
    if review.get("schema_version") != expected_review_schema:
        raise PromotionError("artifact_schema_generation_mismatch", "semantic comparison and review schemas must belong to one generation")
    automatic_path = Path(artifact_paths["automatic_comparison"]).resolve()
    if Path(str(comparison.get("automatic_comparison_path", ""))).resolve() != automatic_path or comparison.get("automatic_comparison_hash") != artifacts["automatic_comparison"]["sha256"] or comparison.get("automatic_comparison_verdict") != "pass" or comparison.get("uses_output_metrics_for_selection") is not False:
        raise PromotionError("receipt_dag_link_mismatch", "semantic comparison does not bind the passing automatic comparison bytes", edge="automatic_to_semantic")
    review_comparison_hash = review.get("comparison_artifact_sha256", review.get("comparison_artifact_hash"))
    if review_comparison_hash != semantic_hash:
        raise PromotionError("receipt_dag_link_mismatch", "review does not bind the semantic comparison bytes", edge="comparison_to_review")
    if confirmation.get("comparison_artifact_sha256") != semantic_hash or confirmation.get("review_artifact_sha256") != review_hash:
        raise PromotionError("receipt_dag_link_mismatch", "confirmation does not bind comparison and review bytes", edge="review_to_confirmation")
    if verification.get("comparison_artifact_sha256") != semantic_hash or verification.get("review_artifact_sha256") != review_hash:
        raise PromotionError("receipt_dag_link_mismatch", "verification does not bind comparison and review bytes", edge="review_to_verification")
    for name, value in (("confirmation", confirmation), ("verification", verification)):
        if Path(str(value.get("candidate_root", ""))).resolve() != candidate_root or value.get("candidate_source_tree_sha256") != candidate_source or value.get("candidate_snapshot_content_sha256") != candidate_content:
            raise PromotionError("receipt_candidate_binding_mismatch", "receipt does not bind the exact candidate root/source/content", artifact=name)
    expected_gates = {"action_pools", "blind_review", "browser", "compatibility_review", "data_validation", "frontend", "full_flow", "prompt_quality_confirmation", "python_tests", "target_comparison", "widgets"}
    gates = verification.get("quality_gates", {})
    observed_gates = set(gates) if isinstance(gates, Mapping) else set(gates) if isinstance(gates, list) else set()
    if observed_gates != expected_gates:
        raise PromotionError("verification_gate_inventory_mismatch", "verification must bind exactly eleven gates", missing=sorted(expected_gates-observed_gates), extra=sorted(observed_gates-expected_gates))
    for gate_name, gate in gates.items():
        if not isinstance(gate, Mapping) or gate.get("status") != "pass":
            raise PromotionError("verification_gate_not_passing", "verification gate is not terminal-pass", gate=gate_name)
        for kind in ("evidence", "result"):
            path = Path(str(gate.get(f"{kind}_path", "")))
            if not path.is_file() or file_hash(path) != gate.get(f"{kind}_sha256"):
                raise PromotionError("verification_gate_artifact_drift", "verification gate bytes drifted", gate=gate_name, kind=kind)
    direct_results = {"target_comparison": Path(artifact_paths["semantic_comparison"]).resolve(), "blind_review": Path(artifact_paths["review"]).resolve(), "prompt_quality_confirmation": Path(artifact_paths["confirmation"]).resolve()}
    for gate_name, expected_path in direct_results.items():
        if Path(str(gates[gate_name]["result_path"])).resolve() != expected_path:
            raise PromotionError("verification_gate_direct_link_mismatch", "direct verification gate points to another artifact", gate=gate_name)
    intended = {relative: file_hash(candidate_root / relative) for relative in sorted(allowlist) if (candidate_root / relative).is_file()}
    absent_candidate = sorted(allowlist - set(intended))
    if absent_candidate: raise PromotionError("candidate_allowlisted_file_missing", "candidate snapshot lacks allowlisted files", paths=absent_candidate)
    result = {"schema_version": PREFLIGHT_SCHEMA, "experiment_id": experiment_id, "verdict": "promote", "status": "pass", "active_root": str(active_root), "candidate_root": str(candidate_root),
              "snapshot_manifest": {"path": str(snapshot_manifest_path), "sha256": file_hash(snapshot_manifest_path)}, "baseline_source_tree_sha256": active_source, "baseline_snapshot_content_sha256": active_content,
              "candidate_source_tree_sha256": candidate_source, "candidate_snapshot_content_sha256": candidate_content, "allowlist": sorted(allowlist), "candidate_file_hashes": intended, "artifacts": artifacts}
    result["preflight_sha256"] = value_hash(result)
    return result


def _validate_preflight(preflight_path: Path, source_hasher: Callable[[Path], str], content_hasher: Callable[[Path], str]) -> tuple[dict[str, Any], Path, Path]:
    preflight = _read_json(preflight_path)
    body = {key: value for key, value in preflight.items() if key != "preflight_sha256"}
    if preflight.get("schema_version") != PREFLIGHT_SCHEMA or value_hash(body) != preflight.get("preflight_sha256") or preflight.get("status") != "pass" or preflight.get("verdict") != "promote":
        raise PromotionError("preflight_invalid", "promotion preflight is not a hash-valid promote verdict")
    active, candidate = Path(preflight["active_root"]).resolve(), Path(preflight["candidate_root"]).resolve()
    if source_hasher(active) != preflight["baseline_source_tree_sha256"] or content_hasher(active) != preflight["baseline_snapshot_content_sha256"]:
        raise PromotionError("active_baseline_drift", "active root changed after preflight")
    if source_hasher(candidate) != preflight["candidate_source_tree_sha256"] or content_hasher(candidate) != preflight["candidate_snapshot_content_sha256"]:
        raise PromotionError("candidate_snapshot_drift", "candidate root changed after preflight")
    for binding in preflight["artifacts"].values():
        if file_hash(Path(binding["path"])) != binding["sha256"]: raise PromotionError("receipt_dag_drift", "an upstream promotion artifact changed")
    return preflight, active, candidate


class ExclusiveLock:
    def __init__(self, path: Path): self.path, self.fd = path, None
    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try: self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc: raise PromotionError("promotion_lock_held", "another promotion transaction owns the lock") from exc
        os.write(self.fd, str(os.getpid()).encode()); os.fsync(self.fd); return self
    def __exit__(self, *_):
        if self.fd is not None: os.close(self.fd)
        self.path.unlink(missing_ok=True)


def _stage(preflight: Mapping[str, Any], active: Path, candidate: Path, generator: Callable[[Path], None] | None) -> Path:
    stage = Path(tempfile.mkdtemp(prefix=".v150-stage-", dir=active.parent))
    shutil.copytree(active, stage, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".promotion-state"))
    for relative in preflight["allowlist"]:
        destination = stage / relative; destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(candidate / relative, destination)
    if generator is not None:
        generator(stage)
    else:
        for script, argument in (("tools/build_action_pools.py", "--write"), ("tools/build_compatibility_review.py", "--write")):
            completed = subprocess.run([sys.executable, str(stage / script), argument], cwd=stage, capture_output=True, check=False)
            if completed.returncode: raise PromotionError("staging_generation_failed", "derived artifact generation failed in staging", script=script, returncode=completed.returncode)
    for relative, expected in preflight["candidate_file_hashes"].items():
        if not (stage / relative).is_file() or file_hash(stage / relative) != expected:
            raise PromotionError("staged_hash_mismatch", "staged allowlisted file differs from frozen candidate", path=relative)
    return stage


def _rollback(journal: dict[str, Any], active: Path, journal_path: Path, *, fail_rollback: bool = False, source_hasher: Callable[[Path], str] = default_source_hash, content_hasher: Callable[[Path], str] = default_content_hash) -> dict[str, Any]:
    try:
        for entry in reversed(journal["entries"]):
            target = active / entry["path"]
            if fail_rollback: raise OSError("injected rollback failure")
            if entry["absent_before"]: target.unlink(missing_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(Path(entry["backup_path"]), target)
            entry["rollback_sha256"] = file_hash(target) if target.is_file() else None
            _write_fsync(journal_path, journal)
        for entry in journal["entries"]:
            actual = file_hash(active / entry["path"]) if (active / entry["path"]).is_file() else None
            if actual != entry["before_sha256"]: raise PromotionError("rollback_path_hash_mismatch", "rollback did not restore an exact path", path=entry["path"])
        if source_hasher(active) != journal["baseline_source_tree_sha256"] or content_hasher(active) != journal["baseline_snapshot_content_sha256"]:
            raise PromotionError("rollback_tree_hash_mismatch", "rollback did not restore exact baseline source-tree and snapshot-content hashes")
        journal["state"] = "ROLLED_BACK"; _write_fsync(journal_path, journal)
        return {"schema_version": ROLLBACK_SCHEMA, "experiment_id": journal["experiment_id"], "state": "ROLLED_BACK", "journal_sha256": file_hash(journal_path), "entries_sha256": value_hash(journal["entries"])}
    except Exception as exc:
        journal["state"] = "RECOVERY_REQUIRED"; journal["rollback_error"] = type(exc).__name__; _write_fsync(journal_path, journal)
        return {"schema_version": ROLLBACK_SCHEMA, "experiment_id": journal["experiment_id"], "state": "RECOVERY_REQUIRED", "journal_sha256": file_hash(journal_path)}


def apply_promotion(*, preflight_path: Path, state_dir: Path, generator: Callable[[Path], None] | None = None, fail_after: int | None = None, fail_rollback: bool = False, source_hasher: Callable[[Path], str] = default_source_hash, content_hasher: Callable[[Path], str] = default_content_hash) -> dict[str, Any]:
    state_dir.mkdir(parents=True, exist_ok=True); journal_path, lock_path = state_dir / "journal.json", state_dir / "promotion.lock"
    if journal_path.exists() and _read_json(journal_path).get("state") in {"APPLYING", "ROLLING_BACK", "RECOVERY_REQUIRED"}:
        raise PromotionError("incomplete_journal_blocks_apply", "rollback-only recovery is required before apply")
    with ExclusiveLock(lock_path):
        preflight, active, candidate = _validate_preflight(preflight_path, source_hasher, content_hasher)
        stage = _stage(preflight, active, candidate, generator)
        backup_root = state_dir / ("backup-" + preflight["preflight_sha256"][:12]); backup_root.mkdir(parents=True, exist_ok=True)
        entries = []
        for relative in preflight["allowlist"]:
            target, backup = active / relative, backup_root / relative
            absent = not target.exists()
            if not absent: backup.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(target, backup)
            entries.append({"path": relative, "absent_before": absent, "before_sha256": None if absent else file_hash(target), "staged_sha256": file_hash(stage / relative), "backup_path": str(backup), "after_sha256": None})
        journal = {"schema_version": JOURNAL_SCHEMA, "experiment_id": preflight["experiment_id"], "preflight_path": str(preflight_path), "preflight_sha256": preflight["preflight_sha256"], "baseline_source_tree_sha256": preflight["baseline_source_tree_sha256"], "baseline_snapshot_content_sha256": preflight["baseline_snapshot_content_sha256"], "state": "APPLYING", "entries": entries}
        _write_fsync(journal_path, journal)
        try:
            for index, entry in enumerate(entries, 1):
                target = active / entry["path"]; target.parent.mkdir(parents=True, exist_ok=True)
                replacement = stage / (entry["path"] + ".replacement"); replacement.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(stage / entry["path"], replacement); os.replace(replacement, target)
                entry["after_sha256"] = file_hash(target); _write_fsync(journal_path, journal)
                if fail_after == index: raise OSError("injected replacement failure")
            journal["state"] = "POSTCHECK"; _write_fsync(journal_path, journal)
            for entry in entries:
                if file_hash(active / entry["path"]) != entry["staged_sha256"]: raise PromotionError("post_apply_hash_mismatch", "read-only postcheck detected mutation", path=entry["path"])
            if source_hasher(active) != preflight["candidate_source_tree_sha256"] or content_hasher(active) != preflight["candidate_snapshot_content_sha256"]:
                raise PromotionError("post_apply_tree_hash_mismatch", "active tree does not equal frozen candidate after apply")
            journal["state"] = "PROMOTED"; _write_fsync(journal_path, journal)
            receipt = {"schema_version": PROMOTION_SCHEMA, "experiment_id": preflight["experiment_id"], "state": "PROMOTED", "preflight_sha256": preflight["preflight_sha256"], "journal_sha256": file_hash(journal_path), "candidate_source_tree_sha256": preflight["candidate_source_tree_sha256"], "candidate_snapshot_content_sha256": preflight["candidate_snapshot_content_sha256"], "entries_sha256": value_hash(entries)}
            receipt["promotion_receipt_sha256"] = value_hash(receipt); return receipt
        except Exception:
            journal["state"] = "ROLLING_BACK"; _write_fsync(journal_path, journal)
            return _rollback(journal, active, journal_path, fail_rollback=fail_rollback, source_hasher=source_hasher, content_hasher=content_hasher)
        finally:
            shutil.rmtree(stage, ignore_errors=True)


def recover(*, state_dir: Path, source_hasher: Callable[[Path], str] = default_source_hash, content_hasher: Callable[[Path], str] = default_content_hash) -> dict[str, Any]:
    journal_path, lock_path = state_dir / "journal.json", state_dir / "promotion.lock"
    if not journal_path.is_file(): raise PromotionError("recovery_journal_missing", "no promotion journal exists")
    with ExclusiveLock(lock_path):
        journal = _read_json(journal_path)
        if journal.get("schema_version") != JOURNAL_SCHEMA or journal.get("state") not in {"APPLYING", "ROLLING_BACK", "RECOVERY_REQUIRED"}:
            raise PromotionError("recovery_not_required", "journal is not in a recoverable incomplete state")
        preflight = _read_json(Path(journal["preflight_path"])); active = Path(preflight["active_root"])
        return _rollback(journal, active, journal_path, source_hasher=source_hasher, content_hasher=content_hasher)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(); modes = parser.add_mutually_exclusive_group(required=True); modes.add_argument("--preflight", action="store_true"); modes.add_argument("--apply", action="store_true"); modes.add_argument("--recover", action="store_true")
    parser.add_argument("--active-root"); parser.add_argument("--candidate-root"); parser.add_argument("--snapshot-manifest"); parser.add_argument("--experiment-id"); parser.add_argument("--automatic-comparison"); parser.add_argument("--semantic-comparison"); parser.add_argument("--review"); parser.add_argument("--confirmation"); parser.add_argument("--verification"); parser.add_argument("--preflight-receipt"); parser.add_argument("--state-dir"); parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.preflight:
            artifacts = {name: Path(getattr(args, name)) for name in ARTIFACT_SCHEMAS}
            result = build_preflight(active_root=Path(args.active_root), candidate_root=Path(args.candidate_root), snapshot_manifest_path=Path(args.snapshot_manifest), artifact_paths=artifacts, experiment_id=args.experiment_id)
        elif args.apply: result = apply_promotion(preflight_path=Path(args.preflight_receipt), state_dir=Path(args.state_dir))
        else: result = recover(state_dir=Path(args.state_dir))
        Path(args.output).write_bytes(canonical_bytes(result)); sys.stdout.buffer.write(canonical_bytes(result)); return 0 if result.get("state") != "RECOVERY_REQUIRED" else 2
    except (OSError, ValueError, json.JSONDecodeError, PromotionError) as exc:
        error = exc if isinstance(exc, PromotionError) else PromotionError("promotion_failed", "promotion operation failed", exception_type=type(exc).__name__)
        sys.stderr.buffer.write(canonical_bytes(error.envelope())); return 2


if __name__ == "__main__": raise SystemExit(main())
