import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "__pycache__",
}


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


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


def expected_widget_sequence(input_specs, linked_inputs):
    seq = []
    for name, type_spec, options in input_specs:
        if not is_widget_input(options):
            continue
        if name in linked_inputs:
            continue
        seq.append((name, type_spec, options))
    return seq


def check_node(node, cls):
    issues = []
    input_specs = collect_input_specs(cls)
    linked_inputs = {
        i["name"]
        for i in node.get("inputs", [])
        if i.get("link") not in (None, 0)
    }
    widget_seq = expected_widget_sequence(input_specs, linked_inputs)
    widget_count = len(widget_seq)
    widgets_values = node.get("widgets_values") or []
    values_len = len(widgets_values)

    # Expand expected sequence to include control widgets if present in serialization.
    expanded_widget_seq = []
    for name, type_spec, options in widget_seq:
        expanded_widget_seq.append((name, type_spec, options))
        if options.get("control_after_generate") or name in ("seed", "noise_seed"):
            if type_label(type_spec) in ("INT", "FLOAT"):
                expanded_widget_seq.append((f"{name}__control", "CONTROL", {}))

    if values_len == len(expanded_widget_seq):
        widget_seq = expanded_widget_seq
        widget_count = len(expanded_widget_seq)

    force_input_count = sum(1 for _, _, opt in input_specs if opt.get("forceInput"))

    if values_len != widget_count:
        issues.append(
            f"widgets_values length {values_len} != expected {widget_count}"
        )
        if force_input_count and values_len == widget_count + force_input_count:
            issues.append(
                "length matches expected + forceInput count; likely legacy dummy values present"
            )

    for idx, (name, type_spec, _opt) in enumerate(widget_seq):
        if idx >= values_len:
            break
        val = widgets_values[idx]
        tlabel = type_label(type_spec)
        if tlabel == "CONTROL":
            continue
        if is_number_type(type_spec):
            if isinstance(val, str) and val.lower() == "randomize":
                issues.append(
                    f"widget '{name}' expects {tlabel} but got 'randomize' string"
                )
            if isinstance(val, float) and (val != val):
                issues.append(
                    f"widget '{name}' expects {tlabel} but got NaN"
                )
        if tlabel == "COMBO":
            if val is None or (isinstance(val, float) and val != val):
                issues.append(
                    f"widget '{name}' expects COMBO value but got invalid"
                )
    return issues, widget_seq


def iter_workflow_files(root: Path):
    for path in root.rglob("*.json"):
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        yield path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", help="paths to scan (default: repo root)")
    args = parser.parse_args()

    roots = [Path(p) for p in args.paths] if args.paths else [ROOT]

    from nodes_pack_parser import PackParser
    from nodes_scene_variator import SceneVariator
    from nodes_dictionary_expand import DictionaryExpand, ThemeClothingExpander, ThemeLocationExpander
    from nodes_garnish import GarnishSampler
    from nodes_simple_template import SimpleTemplateBuilder
    from nodes_prompt_cleaner import PromptCleaner
    from nodes_character_profile import CharacterProfileNode

    class_map = {
        "PackParser": PackParser,
        "SceneVariator": SceneVariator,
        "DictionaryExpand": DictionaryExpand,
        "ThemeClothingExpander": ThemeClothingExpander,
        "ThemeLocationExpander": ThemeLocationExpander,
        "GarnishSampler": GarnishSampler,
        "SimpleTemplateBuilder": SimpleTemplateBuilder,
        "PromptCleaner": PromptCleaner,
        "CharacterProfileNode": CharacterProfileNode,
    }

    report = []
    scanned = 0

    for root in roots:
        for path in iter_workflow_files(root):
            data = load_json(path)
            if not data or "nodes" not in data:
                continue
            nodes = data.get("nodes")
            if not isinstance(nodes, list):
                continue
            scanned += 1
            for node in nodes:
                ntype = node.get("type")
                cls = class_map.get(ntype)
                if not cls:
                    continue
                issues, widget_seq = check_node(node, cls)
                if issues:
                    report.append({
                        "file": str(path),
                        "node_id": node.get("id"),
                        "node_type": ntype,
                        "widgets_values": node.get("widgets_values"),
                        "expected_widgets": [name for name, _, _ in widget_seq],
                        "issues": issues,
                    })

    out_path = ROOT / "tools" / "widgets_values_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if report:
        print(f"Detected issues in {len(report)} nodes across {scanned} workflow files.")
        print(f"Report: {out_path}")
    else:
        print(f"OK: no issues detected across {scanned} workflow files.")
        print(f"Report: {out_path}")


if __name__ == "__main__":
    main()
