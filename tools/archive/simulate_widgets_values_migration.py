import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
import sys


TARGET_TYPES = {
    "DictionaryExpand",
    "ThemeClothingExpander",
    "ThemeLocationExpander",
    "SceneVariator",
    "SimpleTemplateBuilder",
    "GarnishSampler",
    "PromptCleaner",
}

SEED_NAMES = {"seed", "noise_seed"}


def load_module_from_path(path: Path):
    repo_root = path.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_node_mappings(repo_root: Path) -> Dict[str, Any]:
    mappings: Dict[str, Any] = {}
    target_files = [
        repo_root / "nodes_dictionary_expand.py",
        repo_root / "nodes_scene_variator.py",
        repo_root / "nodes_simple_template.py",
        repo_root / "nodes_garnish.py",
        repo_root / "nodes_prompt_cleaner.py",
    ]
    for path in target_files:
        if not path.exists():
            continue
        module = load_module_from_path(path)
        node_map = getattr(module, "NODE_CLASS_MAPPINGS", None)
        if isinstance(node_map, dict):
            mappings.update(node_map)
        else:
            # Fallback: direct class lookup if mapping isn't present.
            if path.name == "nodes_prompt_cleaner.py" and hasattr(module, "PromptCleaner"):
                mappings["PromptCleaner"] = module.PromptCleaner
    return mappings


def input_specs_from_class(node_cls: Any) -> List[Dict[str, Any]]:
    types = node_cls.INPUT_TYPES()
    specs: List[Dict[str, Any]] = []
    for group in ("required", "optional"):
        group_inputs = types.get(group, {})
        for name, spec in group_inputs.items():
            input_type = spec[0]
            options = spec[1] if len(spec) > 1 else {}
            specs.append(
                {
                    "name": name,
                    "group": group,
                    "type": input_type,
                    "options": options,
                    "forceInput": bool(options.get("forceInput")),
                    "control_after_generate": options.get("control_after_generate"),
                }
            )
    return specs


def is_numeric_input(spec: Dict[str, Any]) -> bool:
    t = spec["type"]
    if isinstance(t, str):
        return t in ("INT", "FLOAT")
    return False


def widget_names_for_inputs(input_specs: List[Dict[str, Any]]) -> List[str]:
    widgets: List[str] = []
    for spec in input_specs:
        if spec["forceInput"]:
            continue
        widgets.append(spec["name"])
        control_after_generate = spec["control_after_generate"]
        if is_numeric_input(spec) and (
            control_after_generate is True
            or spec["name"] in SEED_NAMES
            or isinstance(control_after_generate, str)
        ):
            widgets.append(
                control_after_generate
                if isinstance(control_after_generate, str)
                else "control_after_generate"
            )
    return widgets


def migrate_widgets_values(
    input_specs: List[Dict[str, Any]],
    widget_names: List[str],
    widgets_values: List[Any],
) -> List[Any]:
    widget_name_set = set(widget_names)
    original_widgets_inputs = [
        spec
        for spec in input_specs
        if spec["forceInput"] or spec["name"] in widget_name_set
    ]

    widget_index_has_force_input: List[bool] = []
    for spec in original_widgets_inputs:
        if spec["control_after_generate"]:
            widget_index_has_force_input.extend([spec["forceInput"], False])
        else:
            widget_index_has_force_input.append(spec["forceInput"])

    if len(widget_index_has_force_input) != len(widgets_values):
        return list(widgets_values)

    return [
        value
        for index, value in enumerate(widgets_values)
        if not widget_index_has_force_input[index]
    ]


def assign_widgets_values(widget_names: List[str], widgets_values: List[Any]) -> Dict[str, Any]:
    assigned: Dict[str, Any] = {}
    idx = 0
    for name in widget_names:
        if idx >= len(widgets_values):
            break
        assigned[name] = widgets_values[idx]
        idx += 1
    return assigned


def summarize_node(node: Dict[str, Any], node_cls: Any) -> Dict[str, Any]:
    input_specs = input_specs_from_class(node_cls)
    widget_names = widget_names_for_inputs(input_specs)
    before = list(node.get("widgets_values", []))
    after = migrate_widgets_values(input_specs, widget_names, before)
    assigned = assign_widgets_values(widget_names, after)

    return {
        "id": node.get("id"),
        "type": node.get("type"),
        "input_specs": [
            {
                "name": s["name"],
                "type": s["type"],
                "forceInput": s["forceInput"],
                "control_after_generate": s["control_after_generate"],
            }
            for s in input_specs
        ],
        "widget_names": widget_names,
        "widgets_values_before": before,
        "widgets_values_after": after,
        "assigned_widgets": assigned,
    }


def main():
    repo_root = Path(".")
    workflow_path = Path(__file__).resolve().parent / "ComfyUI-workflow-exmaple.json"
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    node_mappings = load_node_mappings(repo_root)

    results: List[Dict[str, Any]] = []
    for node in workflow.get("nodes", []):
        node_type = node.get("type")
        if node_type not in node_mappings:
            continue
        if node_type not in TARGET_TYPES:
            continue
        node_cls = node_mappings[node_type]
        results.append(summarize_node(node, node_cls))

    report_path = Path(__file__).resolve().parent / "widgets_values_simulation_report.json"
    report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    for entry in results:
        print(f"Node {entry['id']} {entry['type']}")
        print("  widget_names:", entry["widget_names"])
        print("  before:", entry["widgets_values_before"])
        print("  after :", entry["widgets_values_after"])
        print("  assigned:", entry["assigned_widgets"])
        print("")

    print(f"Wrote report: {report_path}")


if __name__ == "__main__":
    main()
