import json
from pathlib import Path


def load_workflow(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def collect_input_specs(cls):
    specs = cls.INPUT_TYPES()
    ordered = []
    for group_name in ("required", "optional"):
        group = specs.get(group_name, {})
        for name, spec in group.items():
            if isinstance(spec, (list, tuple)) and len(spec) >= 1:
                type_spec = spec[0]
                options = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
            else:
                type_spec = spec
                options = {}
            ordered.append((name, type_spec, options))
    return ordered


def is_widget_input(options: dict):
    return not options.get("forceInput", False)


def expected_widget_sequence(input_specs, linked_inputs):
    seq = []
    for name, type_spec, options in input_specs:
        if not is_widget_input(options):
            continue
        if name in linked_inputs:
            continue
        seq.append((name, type_spec, options))
    return seq


def type_label(type_spec):
    if isinstance(type_spec, (list, tuple)):
        return "COMBO"
    if isinstance(type_spec, str):
        return type_spec
    return str(type_spec)


def is_number_type(type_spec):
    if isinstance(type_spec, (list, tuple)):
        return False
    return type_spec in ("INT", "FLOAT")


def expand_with_control_widgets(widget_seq):
    expanded = []
    for name, type_spec, options in widget_seq:
        expanded.append((name, type_spec, options))
        if options.get("control_after_generate") or name in ("seed", "noise_seed"):
            if type_label(type_spec) in ("INT", "FLOAT"):
                expanded.append((f"{name}__control", "CONTROL", {}))
    return expanded


def build_widget_plan(node, cls):
    input_specs = collect_input_specs(cls)
    linked_inputs = {
        item["name"]
        for item in node.get("inputs", [])
        if item.get("link") not in (None, 0)
    }
    widget_seq = expected_widget_sequence(input_specs, linked_inputs)
    expanded_widget_seq = expand_with_control_widgets(widget_seq)
    widgets_values = node.get("widgets_values") or []

    if len(widgets_values) == len(expanded_widget_seq):
        return {
            "input_specs": input_specs,
            "linked_inputs": linked_inputs,
            "widget_seq": expanded_widget_seq,
            "base_widget_seq": widget_seq,
            "widgets_values": widgets_values,
            "force_input_count": sum(1 for _, _, opt in input_specs if opt.get("forceInput")),
            "uses_control_widgets": True,
        }

    return {
        "input_specs": input_specs,
        "linked_inputs": linked_inputs,
        "widget_seq": widget_seq,
        "base_widget_seq": widget_seq,
        "widgets_values": widgets_values,
        "force_input_count": sum(1 for _, _, opt in input_specs if opt.get("forceInput")),
        "uses_control_widgets": False,
    }


def check_node_widgets(node, cls):
    issues = []
    plan = build_widget_plan(node, cls)
    widget_seq = plan["widget_seq"]
    widgets_values = plan["widgets_values"]
    force_input_count = plan["force_input_count"]

    if len(widgets_values) != len(widget_seq):
        issues.append(
            f"widgets_values length {len(widgets_values)} != expected {len(widget_seq)}"
        )
        if force_input_count and len(widgets_values) == len(widget_seq) + force_input_count:
            issues.append(
                "length matches expected + forceInput count; likely legacy dummy values present"
            )

    for idx, (name, type_spec, _opt) in enumerate(widget_seq):
        if idx >= len(widgets_values):
            break
        val = widgets_values[idx]
        tlabel = type_label(type_spec)
        if tlabel == "CONTROL":
            continue
        if is_number_type(type_spec):
            if isinstance(val, str) and val.lower() == "randomize":
                issues.append(f"widget '{name}' expects {tlabel} but got 'randomize' string")
            if isinstance(val, float) and (val != val):
                issues.append(f"widget '{name}' expects {tlabel} but got NaN")
        if tlabel == "COMBO":
            if val is None or (isinstance(val, (int, float)) and val != val):
                issues.append(f"widget '{name}' expects COMBO value but got invalid")
    return issues, plan


def simulate_frontend_widget_roundtrip(node, cls):
    issues, plan = check_node_widgets(node, cls)
    if issues:
        return issues, plan, None

    original_values = list(plan["widgets_values"])
    serialized_values = list(original_values)
    if serialized_values != original_values:
        issues.append("frontend-style widget roundtrip changed widgets_values")
    return issues, plan, serialized_values


def validate_workflow_widgets(workflow, class_map):
    problems = []
    for node in workflow.get("nodes", []):
        cls = class_map.get(node.get("type"))
        if not cls:
            continue
        issues, plan = check_node_widgets(node, cls)
        if issues:
            problems.append(
                (
                    node.get("id"),
                    node.get("type"),
                    issues,
                    plan["widget_seq"],
                    plan["widgets_values"],
                )
            )
    return problems


def validate_workflow_roundtrip(workflow, class_map):
    problems = []
    for node in workflow.get("nodes", []):
        cls = class_map.get(node.get("type"))
        if not cls:
            continue
        issues, plan, serialized_values = simulate_frontend_widget_roundtrip(node, cls)
        if issues:
            problems.append(
                (
                    node.get("id"),
                    node.get("type"),
                    issues,
                    plan["widget_seq"],
                    plan["widgets_values"],
                    serialized_values,
                )
            )
    return problems
