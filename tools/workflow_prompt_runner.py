"""Strict, deterministic in-process runner for the supported prompt workflow.

This module deliberately only reads workflow/source data and returns records.  It
does not edit source files, invoke git, or run data builders.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow_class_map import build_class_map_for_workflows
from workflow_widget_validation import build_widget_plan, collect_input_specs, load_workflow


RUNNER_SCHEMA_VERSION = "prompt-workflow-runner/v1"
RECORD_SCHEMA_VERSION = "prompt-quality-record/v1"
SEED_INPUT_NAMES = frozenset({"seed", "noise_seed"})


def canonical_json_bytes(value: Any) -> bytes:
    """Return the repository canonical JSON representation (UTF-8, LF)."""

    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


class WorkflowValidationError(RuntimeError):
    """Stable validation/execution error exposed by the strict runner."""

    def __init__(self, code: str, message: str, **details: Any):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(sorted(details.items()))

    def to_envelope(self) -> dict[str, Any]:
        return {
            "schema_version": RUNNER_SCHEMA_VERSION,
            "status": "error",
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
        }


@dataclass(frozen=True)
class WorkflowProfile:
    """Immutable supported-workflow contract."""

    profile_id: str
    version: str
    allowed_node_types: tuple[str, ...]
    output_selectors: Mapping[str, Mapping[str, Any]]
    excluded_terminal_nodes: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    overrides: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorkflowProfile":
        selectors = value.get("output_selectors", value.get("outputs"))
        if not isinstance(selectors, Mapping) or not selectors:
            raise WorkflowValidationError(
                "invalid_profile", "profile must declare non-empty output_selectors"
            )
        allowed = value.get("allowed_node_types", value.get("supported_node_types"))
        if not isinstance(allowed, (list, tuple)) or not allowed:
            raise WorkflowValidationError(
                "invalid_profile", "profile must declare allowed_node_types"
            )
        frozen_selectors: dict[str, Mapping[str, Any]] = {}
        for name, selector in selectors.items():
            if not isinstance(selector, Mapping):
                raise WorkflowValidationError(
                    "invalid_profile", "output selector must be an object", output=str(name)
                )
            frozen_selectors[str(name)] = dict(selector)
        excluded = value.get("excluded_terminal_nodes", ())
        if not isinstance(excluded, (list, tuple)):
            raise WorkflowValidationError(
                "invalid_profile", "excluded_terminal_nodes must be an array"
            )
        raw_overrides = value.get("overrides", ())
        if isinstance(raw_overrides, Mapping):
            override_items = [
                {"node_id": node_id, "input_name": input_name, "value": input_value}
                for node_id, node_values in raw_overrides.items()
                for input_name, input_value in node_values.items()
            ]
        elif isinstance(raw_overrides, (list, tuple)):
            override_items = list(raw_overrides)
        else:
            raise WorkflowValidationError("invalid_profile", "profile overrides must be an array or object")
        for item in override_items:
            if not isinstance(item, Mapping) or not {"node_id", "input_name", "value"}.issubset(item):
                raise WorkflowValidationError(
                    "invalid_profile", "each profile override must declare node_id, input_name and value"
                )
        return cls(
            profile_id=str(value.get("profile_id", value.get("id", "custom"))),
            version=str(value.get("version", "1")),
            allowed_node_types=tuple(str(item) for item in allowed),
            output_selectors=frozen_selectors,
            excluded_terminal_nodes=tuple(dict(item) for item in excluded),
            overrides=tuple(copy.deepcopy(dict(item)) for item in override_items),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed_node_types": list(self.allowed_node_types),
            "excluded_terminal_nodes": [dict(item) for item in self.excluded_terminal_nodes],
            "output_selectors": {
                name: dict(selector) for name, selector in sorted(self.output_selectors.items())
            },
            "overrides": [dict(item) for item in self.overrides],
            "profile_id": self.profile_id,
            "version": self.version,
        }

    @property
    def hash(self) -> str:
        return _content_hash(self.as_dict())

    def resolved_overrides(self) -> dict[int, dict[str, Any]]:
        result: dict[int, dict[str, Any]] = {}
        for item in self.overrides:
            node_id = int(item["node_id"])
            result.setdefault(node_id, {})[str(item["input_name"])] = copy.deepcopy(item["value"])
        return result


DEFAULT_SUPPORTED_PROFILE = WorkflowProfile.from_mapping(
    {
        "profile_id": "context-natural-v1",
        "version": "1",
        "allowed_node_types": [
            "ContextSource",
            "ContextCharacterProfile",
            "ContextSceneVariator",
            "ContextClothingExpander",
            "ContextLocationExpander",
            "ContextMoodExpander",
            "ContextGarnish",
            "ContextPromptBuilder",
            "PromptCleaner",
            "ContextInspector",
        ],
        "output_selectors": {
            "final_context": {"node_id": 7, "slot": 0, "encoding": "json"},
            "raw_prompt": {"node_id": 8, "slot": 0},
            "cleaned_prompt": {"node_id": 9, "slot": 0},
            "summary_text": {"node_id": 10, "slot": 1},
        },
        "excluded_terminal_nodes": [
            {"node_id": 11, "node_type": "PreviewAny", "reason": "UI preview terminal"}
        ],
    }
)
SUPPORTED_WORKFLOW_PROFILE = DEFAULT_SUPPORTED_PROFILE


def load_profile(source: WorkflowProfile | Mapping[str, Any] | str | Path | None = None) -> WorkflowProfile:
    if source is None:
        return DEFAULT_SUPPORTED_PROFILE
    if isinstance(source, WorkflowProfile):
        return source
    if isinstance(source, Mapping):
        return WorkflowProfile.from_mapping(source)
    path = Path(source)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowValidationError(
            "invalid_profile", "could not load workflow profile", path=str(path), error=type(exc).__name__
        ) from None
    if not isinstance(value, Mapping):
        raise WorkflowValidationError("invalid_profile", "workflow profile root must be an object")
    return WorkflowProfile.from_mapping(value)


def derive_randomized_seed(run_seed: int, node_id: int, input_name: str) -> int:
    digest = hashlib.sha256(f"{run_seed}:{node_id}:{input_name}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & 0xFFFFFFFFFFFFFFFF


def _normalise_overrides(overrides: Mapping[Any, Mapping[str, Any]] | None) -> dict[int, dict[str, Any]]:
    if overrides is None:
        return {}
    if not isinstance(overrides, Mapping):
        raise WorkflowValidationError("invalid_override", "overrides must be an object")
    result: dict[int, dict[str, Any]] = {}
    for raw_node_id, values in overrides.items():
        try:
            node_id = int(raw_node_id)
        except (TypeError, ValueError):
            raise WorkflowValidationError(
                "invalid_override", "override node id must be an integer", node_id=str(raw_node_id)
            ) from None
        if not isinstance(values, Mapping):
            raise WorkflowValidationError(
                "invalid_override", "node overrides must be an object", node_id=node_id
            )
        result[node_id] = {str(name): copy.deepcopy(value) for name, value in sorted(values.items())}
    return dict(sorted(result.items()))


def _node_map(workflow: Mapping[str, Any]) -> dict[int, Mapping[str, Any]]:
    nodes = workflow.get("nodes")
    links = workflow.get("links")
    if not isinstance(nodes, list) or not isinstance(links, list):
        raise WorkflowValidationError(
            "malformed_workflow", "workflow must contain nodes and links arrays"
        )
    result: dict[int, Mapping[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, Mapping) or "id" not in node or "type" not in node:
            raise WorkflowValidationError(
                "malformed_workflow", "each workflow node must contain id and type"
            )
        try:
            node_id = int(node["id"])
        except (TypeError, ValueError):
            raise WorkflowValidationError(
                "malformed_workflow", "node id must be an integer", node_id=str(node.get("id"))
            ) from None
        if node_id in result:
            raise WorkflowValidationError("duplicate_node_id", "workflow node id is duplicated", node_id=node_id)
        result[node_id] = node
    return result


def _link_map(workflow: Mapping[str, Any]) -> dict[int, tuple[Any, ...]]:
    result: dict[int, tuple[Any, ...]] = {}
    for raw in workflow.get("links", []):
        if not isinstance(raw, list) or len(raw) < 6:
            raise WorkflowValidationError("malformed_link", "workflow link must contain six fields")
        try:
            link_id = int(raw[0])
        except (TypeError, ValueError):
            raise WorkflowValidationError("malformed_link", "link id must be an integer") from None
        if link_id in result:
            raise WorkflowValidationError("duplicate_link_id", "workflow link id is duplicated", link_id=link_id)
        result[link_id] = tuple(raw[:6])
    return result


def _resolve_selectors(
    profile: WorkflowProfile, nodes: Mapping[int, Mapping[str, Any]]
) -> dict[str, tuple[int, int, str | None]]:
    resolved: dict[str, tuple[int, int, str | None]] = {}
    for output_name, selector in sorted(profile.output_selectors.items()):
        has_id = "node_id" in selector
        has_type = "node_type" in selector
        if has_id == has_type:
            raise WorkflowValidationError(
                "ambiguous_output_selector",
                "output selector must declare exactly one of node_id or node_type",
                output=output_name,
            )
        if has_id:
            try:
                node_id = int(selector["node_id"])
            except (TypeError, ValueError):
                raise WorkflowValidationError(
                    "invalid_output_selector", "selector node_id must be an integer", output=output_name
                ) from None
            if node_id not in nodes:
                raise WorkflowValidationError(
                    "missing_output_node", "configured output node does not exist", output=output_name, node_id=node_id
                )
        else:
            node_type = str(selector["node_type"])
            matches = sorted(node_id for node_id, node in nodes.items() if node.get("type") == node_type)
            if len(matches) != 1:
                raise WorkflowValidationError(
                    "ambiguous_output_selector",
                    "node_type output selector must resolve to exactly one node",
                    output=output_name,
                    node_type=node_type,
                    matching_node_ids=matches,
                )
            node_id = matches[0]
        try:
            slot = int(selector.get("slot", 0))
        except (TypeError, ValueError):
            raise WorkflowValidationError(
                "invalid_output_selector", "selector slot must be an integer", output=output_name
            ) from None
        if slot < 0:
            raise WorkflowValidationError(
                "invalid_output_selector", "selector slot cannot be negative", output=output_name, slot=slot
            )
        resolved[output_name] = (node_id, slot, selector.get("encoding"))
    return resolved


def _input_links(
    nodes: Mapping[int, Mapping[str, Any]], links: Mapping[int, tuple[Any, ...]]
) -> dict[int, dict[str, tuple[int, int]]]:
    result: dict[int, dict[str, tuple[int, int]]] = {}
    for node_id, node in nodes.items():
        node_sources: dict[str, tuple[int, int]] = {}
        inputs = node.get("inputs", []) or []
        if not isinstance(inputs, list):
            raise WorkflowValidationError("malformed_workflow", "node inputs must be an array", node_id=node_id)
        for item in inputs:
            if not isinstance(item, Mapping) or "name" not in item:
                raise WorkflowValidationError("malformed_workflow", "node input must contain name", node_id=node_id)
            raw_link_id = item.get("link")
            if raw_link_id in (None, 0):
                continue
            try:
                link_id = int(raw_link_id)
            except (TypeError, ValueError):
                raise WorkflowValidationError("malformed_link", "input link id must be an integer", node_id=node_id) from None
            if link_id not in links:
                raise WorkflowValidationError(
                    "missing_upstream", "node input references a missing link", node_id=node_id, input_name=str(item["name"]), link_id=link_id
                )
            _lid, raw_origin_id, raw_origin_slot, raw_target_id, _target_slot, _type = links[link_id]
            try:
                origin_id = int(raw_origin_id)
                origin_slot = int(raw_origin_slot)
                target_id = int(raw_target_id)
            except (TypeError, ValueError):
                raise WorkflowValidationError("malformed_link", "link endpoints and slot must be integers", link_id=link_id) from None
            if target_id != node_id:
                raise WorkflowValidationError(
                    "malformed_link", "link target does not match input node", link_id=link_id, node_id=node_id, target_id=target_id
                )
            if origin_id not in nodes:
                raise WorkflowValidationError(
                    "missing_upstream", "link origin node does not exist", link_id=link_id, origin_node_id=origin_id
                )
            node_sources[str(item["name"])] = (origin_id, origin_slot)
        result[node_id] = node_sources
    return result


def _ancestor_closure(output_node_ids: Sequence[int], sources: Mapping[int, Mapping[str, tuple[int, int]]]) -> set[int]:
    closure: set[int] = set()
    active = list(output_node_ids)
    while active:
        node_id = active.pop()
        if node_id in closure:
            continue
        closure.add(node_id)
        active.extend(origin_id for origin_id, _slot in sources.get(node_id, {}).values())
    return closure


def _stable_order(node: Mapping[str, Any], node_id: int) -> tuple[float, int]:
    try:
        order = float(node.get("order", 0))
    except (TypeError, ValueError):
        order = 0.0
    return order, node_id


def _topological_order(
    closure: set[int], nodes: Mapping[int, Mapping[str, Any]], sources: Mapping[int, Mapping[str, tuple[int, int]]]
) -> list[int]:
    indegree = {node_id: 0 for node_id in closure}
    dependents = {node_id: [] for node_id in closure}
    for target_id in closure:
        for origin_id, _slot in sources.get(target_id, {}).values():
            if origin_id in closure:
                indegree[target_id] += 1
                dependents[origin_id].append(target_id)
    ready = sorted(
        (node_id for node_id, degree in indegree.items() if degree == 0),
        key=lambda node_id: _stable_order(nodes[node_id], node_id),
    )
    ordered: list[int] = []
    while ready:
        node_id = ready.pop(0)
        ordered.append(node_id)
        for dependent in dependents[node_id]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
                ready.sort(key=lambda item: _stable_order(nodes[item], item))
    if len(ordered) != len(closure):
        cycle_nodes = sorted(node_id for node_id, degree in indegree.items() if degree > 0)
        raise WorkflowValidationError("cycle_detected", "workflow ancestor closure contains a cycle", node_ids=cycle_nodes)
    return ordered


def _excluded_terminals(
    profile: WorkflowProfile, nodes: Mapping[int, Mapping[str, Any]], closure: set[int]
) -> list[dict[str, Any]]:
    declared_by_id: dict[int, Mapping[str, Any]] = {}
    for item in profile.excluded_terminal_nodes:
        if "node_id" not in item or "node_type" not in item or not item.get("reason"):
            raise WorkflowValidationError(
                "invalid_profile", "excluded terminal must declare node_id, node_type and reason"
            )
        node_id = int(item["node_id"])
        declared_by_id[node_id] = item
    recorded = []
    for node_id, item in sorted(declared_by_id.items()):
        node = nodes.get(node_id)
        if node is None:
            continue
        if str(node.get("type")) != str(item["node_type"]):
            raise WorkflowValidationError(
                "excluded_terminal_mismatch",
                "excluded terminal type does not match workflow",
                node_id=node_id,
                expected_type=str(item["node_type"]),
                actual_type=str(node.get("type")),
            )
        if node_id in closure:
            raise WorkflowValidationError(
                "excluded_terminal_in_closure", "an excluded terminal is required by a configured output", node_id=node_id
            )
        recorded.append(
            {"node_id": node_id, "node_type": str(node.get("type")), "reason": str(item["reason"])}
        )
    for node_id, node in sorted(nodes.items()):
        if node_id not in closure and str(node.get("type")) not in profile.allowed_node_types and node_id not in declared_by_id:
            raise WorkflowValidationError(
                "unsupported_node",
                "unsupported node outside the ancestor closure is not a declared excluded terminal",
                node_id=node_id,
                node_type=str(node.get("type")),
            )
    return recorded


def _resolve_widget_inputs(node: Mapping[str, Any], node_cls: type, run_seed: int) -> tuple[dict[str, Any], dict[str, Any]]:
    plan = build_widget_plan(node, node_cls)
    widget_values = list(plan["widgets_values"] or [])
    widget_seq = list(plan["widget_seq"] or [])
    if len(widget_values) != len(widget_seq):
        raise WorkflowValidationError(
            "widget_mismatch",
            "widgets_values length does not match the current node input contract",
            node_id=int(node["id"]),
            node_type=str(node["type"]),
            actual=len(widget_values),
            expected=len(widget_seq),
        )
    resolved: dict[str, Any] = {}
    controls: dict[str, Any] = {}
    for index, (name, _type_spec, _options) in enumerate(widget_seq):
        value = copy.deepcopy(widget_values[index])
        if str(name).endswith("__control"):
            controls[str(name).split("__control", 1)[0]] = value
        else:
            resolved[str(name)] = value
    for name in SEED_INPUT_NAMES:
        if name in resolved and controls.get(name) == "randomize":
            resolved[name] = derive_randomized_seed(run_seed, int(node["id"]), name)
    return resolved, controls


def execute_workflow(
    workflow: Mapping[str, Any],
    run_seed: int,
    profile: WorkflowProfile | Mapping[str, Any] | str | Path | None = None,
    overrides: Mapping[Any, Mapping[str, Any]] | None = None,
    class_map: Mapping[str, type] | None = None,
) -> dict[str, Any]:
    """Validate and execute only the configured outputs' ancestor closure."""

    selected_profile = load_profile(profile)
    workflow_copy = copy.deepcopy(dict(workflow))
    nodes = _node_map(workflow_copy)
    links = _link_map(workflow_copy)
    selectors = _resolve_selectors(selected_profile, nodes)
    sources = _input_links(nodes, links)
    closure = _ancestor_closure([value[0] for value in selectors.values()], sources)
    excluded = _excluded_terminals(selected_profile, nodes, closure)
    ordered_ids = _topological_order(closure, nodes, sources)
    profile_overrides = selected_profile.resolved_overrides()
    explicit_overrides = _normalise_overrides(overrides)
    normalized_overrides = copy.deepcopy(profile_overrides)
    for node_id, node_values in explicit_overrides.items():
        normalized_overrides.setdefault(node_id, {}).update(node_values)
    normalized_overrides = dict(sorted(normalized_overrides.items()))

    unknown_override_nodes = sorted(set(normalized_overrides) - set(nodes))
    if unknown_override_nodes:
        raise WorkflowValidationError(
            "invalid_override", "override references a missing node", node_ids=unknown_override_nodes
        )
    outside_override_nodes = sorted(set(normalized_overrides) - closure)
    if outside_override_nodes:
        raise WorkflowValidationError(
            "invalid_override", "override references a node outside the execution closure", node_ids=outside_override_nodes
        )

    resolved_class_map = dict(class_map or build_class_map_for_workflows([workflow_copy]))
    allowed = set(selected_profile.allowed_node_types)
    for node_id in ordered_ids:
        node_type = str(nodes[node_id].get("type"))
        if node_type not in allowed or node_type not in resolved_class_map:
            raise WorkflowValidationError(
                "unsupported_node", "ancestor closure contains an unsupported node", node_id=node_id, node_type=node_type
            )

    node_outputs: dict[int, tuple[Any, ...]] = {}
    execution_trace: list[dict[str, Any]] = []
    resolved_seeds: dict[str, int] = {}
    for node_id in ordered_ids:
        node = nodes[node_id]
        node_type = str(node["type"])
        node_cls = resolved_class_map[node_type]
        linked_sources = sources.get(node_id, {})
        widget_inputs, widget_controls = _resolve_widget_inputs(node, node_cls, int(run_seed))
        input_specs = collect_input_specs(node_cls)
        valid_input_names = {str(name) for name, _type, _options in input_specs}
        node_overrides = normalized_overrides.get(node_id, {})
        invalid_names = sorted(set(node_overrides) - valid_input_names)
        linked_override_names = sorted(set(node_overrides) & set(linked_sources))
        if invalid_names or linked_override_names:
            raise WorkflowValidationError(
                "invalid_override",
                "override must target an existing unlinked node input",
                node_id=node_id,
                invalid_input_names=invalid_names,
                linked_input_names=linked_override_names,
            )
        kwargs: dict[str, Any] = {}
        for name, _type_spec, options in input_specs:
            name = str(name)
            if name in linked_sources:
                origin_id, origin_slot = linked_sources[name]
                outputs = node_outputs.get(origin_id)
                if outputs is None or origin_slot < 0 or origin_slot >= len(outputs):
                    raise WorkflowValidationError(
                        "missing_upstream_slot",
                        "linked upstream output slot is unavailable",
                        node_id=node_id,
                        input_name=name,
                        origin_node_id=origin_id,
                        origin_slot=origin_slot,
                    )
                kwargs[name] = outputs[origin_slot]
            elif name in widget_inputs:
                kwargs[name] = widget_inputs[name]
            elif options.get("forceInput", False):
                continue
        kwargs.update(copy.deepcopy(node_overrides))
        for seed_name in SEED_INPUT_NAMES:
            seed_value = kwargs.get(seed_name)
            if isinstance(seed_value, int) and not isinstance(seed_value, bool):
                resolved_seeds[f"{node_id}:{seed_name}"] = seed_value
        function_name = getattr(node_cls, "FUNCTION", None)
        if not isinstance(function_name, str) or not hasattr(node_cls, function_name):
            raise WorkflowValidationError(
                "invalid_node_contract", "node class does not expose its declared function", node_id=node_id, node_type=node_type
            )
        try:
            result = getattr(node_cls(), function_name)(**kwargs)
        except Exception as exc:
            raise WorkflowValidationError(
                "execution_error",
                "node execution failed",
                node_id=node_id,
                node_type=node_type,
                exception_type=type(exc).__name__,
            ) from None
        if not isinstance(result, tuple):
            result = (result,)
        node_outputs[node_id] = result
        execution_trace.append(
            {
                "controls": widget_controls,
                "function": function_name,
                "inputs": kwargs,
                "node_id": node_id,
                "node_type": node_type,
            }
        )

    selected_outputs: dict[str, Any] = {}
    raw_outputs: dict[str, Any] = {}
    for output_name, (node_id, slot, encoding) in selectors.items():
        values = node_outputs.get(node_id)
        if values is None or slot >= len(values):
            raise WorkflowValidationError(
                "missing_output_slot", "configured output slot is unavailable", output=output_name, node_id=node_id, slot=slot
            )
        value = values[slot]
        raw_outputs[output_name] = value
        if encoding == "json":
            if not isinstance(value, str):
                raise WorkflowValidationError(
                    "output_decode_error", "configured JSON output is not text", output=output_name, node_id=node_id, slot=slot
                )
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise WorkflowValidationError(
                    "output_decode_error", "configured JSON output is invalid", output=output_name, node_id=node_id, slot=slot
                ) from None
        selected_outputs[output_name] = value

    base_workflow_hash = _content_hash(workflow_copy)
    override_hash = _content_hash(
        {"explicit": explicit_overrides, "profile": profile_overrides}
    )
    effective_workflow_hash = _content_hash(
        {"base_workflow_hash": base_workflow_hash, "override_hash": override_hash}
    )
    config_hash = _content_hash(
        {"override_hash": override_hash, "profile_hash": selected_profile.hash}
    )
    return {
        "base_workflow_hash": base_workflow_hash,
        "config_hash": config_hash,
        "effective_workflow_hash": effective_workflow_hash,
        "excluded_terminal_nodes": excluded,
        "execution_trace": execution_trace,
        "node_outputs": node_outputs,
        "output_selectors": {
            name: {"node_id": value[0], "slot": value[1]} for name, value in sorted(selectors.items())
        },
        "outputs": selected_outputs,
        "override_hash": override_hash,
        "overrides": normalized_overrides,
        "profile_hash": selected_profile.hash,
        "profile_id": selected_profile.profile_id,
        "raw_outputs": raw_outputs,
        "resolved_seeds": dict(sorted(resolved_seeds.items())),
        "run_seed": int(run_seed),
        "schema_version": RUNNER_SCHEMA_VERSION,
    }


def build_canonical_record(
    workflow: Mapping[str, Any],
    run_seed: int,
    profile: WorkflowProfile | Mapping[str, Any] | str | Path | None = None,
    overrides: Mapping[Any, Mapping[str, Any]] | None = None,
    class_map: Mapping[str, type] | None = None,
    cohort: str | None = None,
) -> dict[str, Any]:
    executed = execute_workflow(workflow, run_seed, profile, overrides, class_map)
    outputs = executed["outputs"]
    context = outputs.get("final_context")
    if not isinstance(context, Mapping):
        raise WorkflowValidationError(
            "output_decode_error", "final_context selector must produce a JSON object"
        )
    raw_context_json = executed["raw_outputs"].get("final_context")
    if not isinstance(raw_context_json, str):
        raw_context_json = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    record = {
        "base_workflow_hash": executed["base_workflow_hash"],
        "cleaned_prompt": outputs.get("cleaned_prompt", ""),
        "config_hash": executed["config_hash"],
        "context": context,
        "context_json": raw_context_json,
        "context_json_bytes": len(raw_context_json.encode("utf-8")),
        "effective_workflow_hash": executed["effective_workflow_hash"],
        "excluded_terminal_nodes": executed["excluded_terminal_nodes"],
        "execution_trace": executed["execution_trace"],
        "final_context": context,
        "final_context_json": raw_context_json,
        "output_selectors": executed["output_selectors"],
        "override_hash": executed["override_hash"],
        "profile_hash": executed["profile_hash"],
        "profile_id": executed["profile_id"],
        "raw_prompt": outputs.get("raw_prompt", ""),
        "resolved_seeds": executed["resolved_seeds"],
        "run_seed": int(run_seed),
        "schema_version": RECORD_SCHEMA_VERSION,
        "summary_text": outputs.get("summary_text", ""),
    }
    if cohort is not None:
        record["cohort"] = str(cohort)
    return record


def build_canonical_records(
    workflow: Mapping[str, Any],
    run_seeds: Sequence[int],
    profile: WorkflowProfile | Mapping[str, Any] | str | Path | None = None,
    overrides: Mapping[Any, Mapping[str, Any]] | None = None,
    class_map: Mapping[str, type] | None = None,
    cohort_by_seed: Mapping[int, str] | None = None,
) -> list[dict[str, Any]]:
    seeds = [int(seed) for seed in run_seeds]
    if len(seeds) != len(set(seeds)):
        raise WorkflowValidationError("duplicate_seed", "run seed cohort contains duplicates")
    return [
        build_canonical_record(
            workflow,
            seed,
            profile,
            overrides,
            class_map,
            cohort=(cohort_by_seed or {}).get(seed),
        )
        for seed in seeds
    ]


def build_failure_record(error: WorkflowValidationError, run_seed: int | None = None) -> dict[str, Any]:
    envelope = error.to_envelope()
    if run_seed is not None:
        envelope["run_seed"] = int(run_seed)
    return envelope


def _main() -> int:
    parser = argparse.ArgumentParser(description="Execute a supported prompt workflow strictly.")
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--profile")
    parser.add_argument("--seed", type=int, action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        workflow_path = Path(args.workflow)
        try:
            workflow = load_workflow(workflow_path)
        except FileNotFoundError:
            raise WorkflowValidationError(
                "workflow_not_found",
                "workflow file does not exist",
                path=str(workflow_path),
            ) from None
        except json.JSONDecodeError:
            raise WorkflowValidationError(
                "malformed_workflow_json",
                "workflow file is not valid JSON",
                path=str(workflow_path),
            ) from None
        except UnicodeError:
            raise WorkflowValidationError(
                "malformed_workflow_json",
                "workflow file is not valid UTF-8 JSON",
                path=str(workflow_path),
            ) from None
        except OSError as exc:
            raise WorkflowValidationError(
                "workflow_read_error",
                "workflow file could not be read",
                path=str(workflow_path),
                exception_type=type(exc).__name__,
            ) from None
        records = build_canonical_records(workflow, args.seed, load_profile(args.profile))
        output = Path(args.output)
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"".join(canonical_json_bytes(record) for record in records))
        except OSError as exc:
            raise WorkflowValidationError(
                "artifact_write_error",
                "canonical records could not be written",
                path=str(output),
                exception_type=type(exc).__name__,
            ) from None
        return 0
    except WorkflowValidationError as exc:
        sys.stderr.buffer.write(canonical_json_bytes(exc.to_envelope()))
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
