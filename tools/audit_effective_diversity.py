"""Deterministic, read-only audit of the bundled context workflow."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
from contextlib import redirect_stdout
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.context_codec import context_from_json
from pipeline.prompt_orchestrator import build_prompt_from_context
from tools.effective_diversity_metrics import axis_coverage, metric_prefixes, repetition_metrics, semantic_uniqueness, syntax_entropy
from tools.effective_diversity_signatures import build_semantic_signatures
from tools.prompt_quality_loop import build_source_manifest
from tools.workflow_prompt_runner import (
    WorkflowValidationError, _resolve_widget_inputs, build_canonical_record, canonical_json_bytes,
)
from workflow_class_map import build_class_map_for_workflows
from workflow_widget_validation import load_workflow

SCHEMA_VERSION = "effective-diversity-audit/v1"
REFERENCE_VERSION = "effective-diversity-reference/v1"
WORKFLOW_PATH = ROOT / "ComfyUI-workflow-context.json"
CONTRACT_PATH = ROOT / "docs/diversity_refactor/spec.md"
PROFILES = {"smoke": (128, 128), "gate": (2048, 8192), "release": (8192, 8192)}
AXES = ("subject", "location", "action_family", "primary_object_family", "mood", "clothing_family", "garnish_family", "syntax_family")
IDENTITY_FIELDS = ("base_workflow_hash", "effective_workflow_hash", "config_hash", "profile_hash", "override_hash")
ACTIVE_V1_FAMILIES = ["single-sentence-scene-tail", "two-sentence-scene-tail"]


class AuditError(ValueError):
    def __init__(self, code: str, **details: Any):
        super().__init__(code)
        self.code, self.details = code, details

    def envelope(self) -> dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, "status": "error", "error": {"code": self.code, "details": self.details}}


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _input_path(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT) or not resolved.is_file():
        raise AuditError("unsupported_file_input")
    if resolved.is_relative_to(ROOT / "assets/results") or resolved.relative_to(ROOT).parts[0] in {".git", ".omx"}:
        raise AuditError("unsupported_file_input")
    return resolved


def capture_source(file_inputs: Sequence[Path]) -> dict[str, Any]:
    """Bind existing source rules plus root inputs missing from that manifest."""
    manifest = build_source_manifest(ROOT)
    for entry in manifest["entries"]:
        _input_path(ROOT / entry["path"])
    inputs = {_input_path(ROOT / name) for name in ("prompts.jsonl", "mood_map.json", "templates.txt")}
    inputs.update(_input_path(path) for path in file_inputs)
    return {
        "source_identity": {
            "source_tree_hash": manifest["source_tree_hash"],
            "supplemental_inputs": [{"path": path.relative_to(ROOT).as_posix(), "sha256": _file_hash(path)}
                                    for path in sorted(inputs)],
        },
        "contract_sha256": _file_hash(_input_path(CONTRACT_PATH)),
        "workflow_hash": content_hash(load_workflow(_input_path(WORKFLOW_PATH))),
    }


def _preflight(workflow: dict[str, Any], seed: int) -> tuple[list[Path], list[str]]:
    if not isinstance(workflow, dict) or not isinstance(workflow.get("nodes"), list):
        raise AuditError("unsupported_workflow")
    for node in workflow["nodes"]:
        if (not isinstance(node, dict) or not isinstance(node.get("type"), str)
                or not isinstance(node.get("inputs", []), list)
                or any(not isinstance(item, dict) for item in node.get("inputs", []))):
            raise AuditError("unsupported_workflow")
    classes = build_class_map_for_workflows([workflow])
    moods = [node for node in workflow["nodes"] if node["type"] == "ContextMoodExpander"]
    builders = [node for node in workflow["nodes"] if node["type"] == "ContextPromptBuilder"]
    if len(moods) != 1 or len(builders) != 1:
        raise AuditError("unsupported_workflow")
    paths = []
    active = []
    for node, guarded in ((moods[0], "json_path"), (builders[0], "composition_mode")):
        if any(item.get("name") == guarded and item.get("link") is not None for item in node.get("inputs", [])):
            raise AuditError("unsupported_dynamic_input", input_name=guarded)
        inputs, _ = _resolve_widget_inputs(node, classes[node["type"]], seed)
        if guarded == "json_path":
            value = inputs.get("json_path")
            if not isinstance(value, str):
                raise AuditError("unsupported_file_input")
            paths.append(_input_path(ROOT / (value if value.strip() else "mood_map.json")))
        else:
            if type(inputs.get("composition_mode")) is not bool:
                raise AuditError("unsupported_workflow")
            active = list(ACTIVE_V1_FAMILIES) if inputs["composition_mode"] else []
    return paths, active


def ordered_records(records: Sequence[Mapping[str, Any]], *, expected_identity: Mapping[str, Any] | None = None) -> list[Mapping[str, Any]]:
    seen = set()
    identity = expected_identity
    for record in records:
        seed = record.get("run_seed")
        if type(seed) is not int or seed in seen:
            raise AuditError("invalid_or_duplicate_seed")
        seen.add(seed)
        current = {key: record.get(key) for key in IDENTITY_FIELDS}
        if any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in current.values()):
            raise AuditError("invalid_record_identity")
        if identity is None:
            identity = current
        if current != identity:
            raise AuditError("mixed_record_identity")
    return sorted(records, key=lambda record: record["run_seed"])


def _project(record: Mapping[str, Any], mood_keys: Sequence[str], active: list[str]) -> dict[str, Any]:
    selector = record.get("output_selectors", {}).get("raw_prompt", {})
    traces = [trace for trace in record.get("execution_trace", []) if trace.get("node_id") == selector.get("node_id")]
    if (selector.get("slot") != 0 or len(traces) != 1 or traces[0].get("node_type") != "ContextPromptBuilder"
            or traces[0].get("function") != "build_prompt_context"):
        raise AuditError("invalid_builder_trace")
    inputs = traces[0]["inputs"]
    if type(inputs.get("seed")) is not int or type(inputs.get("composition_mode")) is not bool:
        raise AuditError("invalid_builder_trace")
    # The semantic record must describe the context actually consumed by this builder.
    if json.loads(inputs["context_json"]) != record.get("final_context"):
        raise AuditError("builder_context_mismatch")
    context, prompt = build_prompt_from_context(
        context_from_json(inputs["context_json"], default_seed=inputs["seed"]),
        inputs["template"], inputs["composition_mode"], inputs["seed"],
    )
    if prompt != record.get("raw_prompt"):
        raise AuditError("builder_replay_mismatch", run_seed=record["run_seed"])
    if not context.history or context.history[-1].node != "ContextPromptBuilder":
        raise AuditError("missing_builder_metadata")
    projected = build_semantic_signatures(record, builder_decision=context.history[-1].decision, mood_keys=mood_keys)
    family = projected["axes"]["syntax_family"]
    if family is not None and family not in active:
        raise AuditError("unknown_syntax_family", family=family)
    if active and family is None:
        raise AuditError("missing_builder_metadata")
    return projected


def _validate_reference(reference: Any, identity: Mapping[str, Any], count: int) -> dict[str, Any]:
    keys = {"schema_version", "source_hash", "effective_workflow_hash", "config_hash", "seed_start",
            "sample_count", "records_sha256", "axes", "reference_hash"}
    if not isinstance(reference, dict) or set(reference) != keys:
        raise AuditError("invalid_reference")
    payload = {key: value for key, value in reference.items() if key != "reference_hash"}
    if reference["reference_hash"] != content_hash(payload):
        raise AuditError("reference_hash_mismatch")
    if (reference["schema_version"] != REFERENCE_VERSION or type(reference["seed_start"]) is not int
            or reference["seed_start"] != 0 or type(reference["sample_count"]) is not int
            or reference["sample_count"] != count):
        raise AuditError("reference_probe_mismatch")
    if any(reference[key] != value for key, value in identity.items()):
        raise AuditError("reference_identity_mismatch")
    if not isinstance(reference["records_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", reference["records_sha256"]):
        raise AuditError("invalid_reference")
    axes = reference["axes"]
    if not isinstance(axes, dict) or set(axes) != set(AXES):
        raise AuditError("invalid_reference_axes")
    for values in axes.values():
        if (not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values)
                or values != sorted(set(values))):
            raise AuditError("invalid_reference_axes")
    return reference


def _metrics(rows: list[dict[str, Any]], reference: dict[str, Any], active: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {key: {} for key in ("semantic_unique", "coverage", "repetition", "syntax_entropy")}
    for n in metric_prefixes(len(rows)):
        prefix = rows[:n]
        projections = [row["projection"] for row in prefix]
        core = [item["core"] if item["valid"] else None for item in projections]
        frame = [item["frame"] if item["valid"] else None for item in projections]
        values = {axis: [item["axes"][axis] for item in projections] for axis in AXES}
        key = str(n)
        result["semantic_unique"][key] = {"core": semantic_uniqueness(core), "frame": semantic_uniqueness(frame)}
        result["coverage"][key] = {axis: axis_coverage(values[axis], reference["axes"][axis]) for axis in AXES}
        result["repetition"][key] = repetition_metrics([row["cleaned_prompt"] for row in prefix], core, frame,
                                                       values["action_family"], values["syntax_family"])
        result["syntax_entropy"][key] = syntax_entropy(values["syntax_family"], active)
    return result


def build_audit(*, profile: str = "smoke", seed_start: int = 0, sample_count: int | None = None,
                reference_universe: dict[str, Any] | None = None) -> dict[str, Any]:
    """Audit the bundled workflow. Invoke in a fresh process for a new source snapshot."""
    if profile not in PROFILES:
        raise AuditError("invalid_profile", profile=profile)
    default_count, reference_count = PROFILES[profile]
    count = default_count if sample_count is None else sample_count
    if type(count) is not int or count <= 0 or type(seed_start) is not int:
        raise AuditError("invalid_sample_range")
    workflow = load_workflow(WORKFLOW_PATH)
    file_inputs, active = _preflight(workflow, seed_start)
    before = capture_source(file_inputs)
    if content_hash(workflow) != before["workflow_hash"]:
        raise AuditError("inputs_changed")
    mood_keys = list(json.loads(file_inputs[0].read_text(encoding="utf-8")))
    measure_seeds = set(range(seed_start, seed_start + count))
    probe_seeds = set(range(reference_count)) if reference_universe is None else set()
    seeds = sorted(measure_seeds | probe_seeds)
    first = build_canonical_record(workflow, seeds[0])
    ordered_records([first])
    runner_identity = {key: first[key] for key in IDENTITY_FIELDS}
    config = {
        "runner_config_hash": first["config_hash"],
        "signature_versions": {"core": "semantic_signature_v1/core", "frame": "semantic_signature_v1/frame"},
        "normalization_version": "effective-diversity-normalization/v1",
        "contract_sha256": before["contract_sha256"], "active_syntax_families": active,
    }
    identity = {"source_hash": content_hash(before["source_identity"]),
                "effective_workflow_hash": first["effective_workflow_hash"], "config_hash": content_hash(config)}
    if reference_universe is not None:
        _validate_reference(reference_universe, identity, reference_count)
    ref_axes: dict[str, set[str]] = {axis: set() for axis in AXES}
    probe_hash, record_hash = hashlib.sha256(), hashlib.sha256()
    rows = []
    for seed in seeds:
        record = first if seed == seeds[0] else build_canonical_record(workflow, seed)
        ordered_records([record], expected_identity=runner_identity)
        if record["run_seed"] != seed:
            raise AuditError("record_seed_mismatch")
        if not isinstance(record.get("cleaned_prompt"), str) or not record["cleaned_prompt"].strip():
            raise AuditError("invalid_cleaned_prompt", run_seed=seed)
        projection = _project(record, mood_keys, active)
        encoded = canonical_json_bytes(record)
        if seed in probe_seeds:
            probe_hash.update(encoded)
            for axis, value in projection["axes"].items():
                if value is not None:
                    ref_axes[axis].update([value] if isinstance(value, str) else value)
        if seed in measure_seeds:
            record_hash.update(encoded)
            rows.append({"cleaned_prompt": record["cleaned_prompt"], "projection": projection})
    reference = reference_universe
    if reference is None:
        reference = {"schema_version": REFERENCE_VERSION, **identity, "seed_start": 0,
                     "sample_count": reference_count, "records_sha256": probe_hash.hexdigest(),
                     "axes": {axis: sorted(values) for axis, values in ref_axes.items()}}
        reference["reference_hash"] = content_hash(reference)
    missing = {kind: Counter({key: 0 for key in rows[0]["projection"][kind]}) for kind in ("core", "frame")}
    sources: dict[str, Counter] = {}
    for row in rows:
        diagnostics = row["projection"]["diagnostics"]
        for kind in missing:
            missing[kind].update(diagnostics["missing_fields"][kind])
        for field, source in diagnostics["extraction_sources"].items():
            sources.setdefault(field, Counter())[source] += 1
    metrics = _metrics(rows, reference, active)
    if before != capture_source(file_inputs):
        raise AuditError("inputs_changed")
    return {
        "schema_version": SCHEMA_VERSION, "status": "ok", "profile": profile,
        **identity, "source_identity": before["source_identity"], "workflow_hash": first["base_workflow_hash"],
        "runner_config_hash": first["config_hash"], "audit_config": config,
        "seed_start": seed_start, "sample_count": count, "prefixes": metric_prefixes(count),
        "records_sha256": record_hash.hexdigest(), "reference_universe": reference,
        "diagnostics": {"signature_missing_counts": {kind: dict(values) for kind, values in missing.items()},
                        "extraction_sources": {field: dict(values) for field, values in sources.items()},
                        "builder_replay": {"checked_count": count, "mismatch_count": 0}},
        "metrics": metrics,
    }


def output_path(path: Path) -> Path:
    destination = path.resolve()
    if (destination.is_dir() or (destination.is_relative_to(ROOT)
            and not destination.is_relative_to(ROOT / "assets/results"))):
        raise AuditError("unsafe_output_path")
    return destination


def write_report(path: Path, value: Any) -> None:
    destination = output_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(canonical_json_bytes(value))
        os.replace(temporary, destination)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise AuditError("invalid_arguments", message=message)


def _emit(value: Any) -> None:
    data = canonical_json_bytes(value)
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write(data)
    else:
        sys.stdout.write(data.decode("utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = _Parser(description=__doc__)
    parser.add_argument("--profile", default="smoke", choices=tuple(PROFILES))
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--sample-count", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reference", type=Path, help="Matching reference JSON from --write-reference")
    parser.add_argument("--write-reference", type=Path)
    try:
        args = parser.parse_args(argv)
        outputs = [output_path(path) for path in (args.output, args.write_reference) if path is not None]
        if len(outputs) != len(set(outputs)) or (args.reference is not None and args.reference.resolve() in outputs):
            raise AuditError("artifact_path_collision")
        reference = json.loads(args.reference.read_text(encoding="utf-8")) if args.reference else None
        with redirect_stdout(sys.stderr):
            report = build_audit(profile=args.profile, seed_start=args.seed_start,
                                 sample_count=args.sample_count, reference_universe=reference)
        # Serialize both before publishing either; the success report is last.
        canonical_json_bytes(report)
        canonical_json_bytes(report["reference_universe"])
        if args.write_reference:
            write_report(args.write_reference, report["reference_universe"])
        if args.output:
            write_report(args.output, report)
        if not args.output:
            _emit(report)
        return 0
    except AuditError as exc:
        error = exc
    except WorkflowValidationError as exc:
        error = AuditError("workflow_validation_error", runner_code=exc.code)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        error = AuditError("invalid_input_or_io", exception_type=type(exc).__name__)
    _emit(error.envelope())
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
