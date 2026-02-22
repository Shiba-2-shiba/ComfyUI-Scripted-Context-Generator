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


def expected_widget_sequence(input_specs, linked_inputs):
    seq = []
    for name, type_spec, options in input_specs:
        if not is_widget_input(options):
            continue
        if name in linked_inputs:
            continue
        seq.append((name, type_spec, options))
    return seq


def expand_with_control_widgets(widget_seq):
    expanded = []
    for name, type_spec, options in widget_seq:
        expanded.append((name, type_spec, options))
        if options.get("control_after_generate") or name in ("seed", "noise_seed"):
            if type_label(type_spec) in ("INT", "FLOAT"):
                expanded.append((f"{name}__control", "CONTROL", {}))
    return expanded


def build_legacy_sequence(input_specs):
    # Legacy sequence includes forceInput positions (dummy values)
    seq = []
    for name, type_spec, options in input_specs:
        if options.get("forceInput"):
            seq.append((name, "FORCE_INPUT", options))
        else:
            seq.append((name, type_spec, options))
    return seq


def normalize_widgets_values(node, cls):
    input_specs = collect_input_specs(cls)
    linked_inputs = {
        i["name"]
        for i in node.get("inputs", [])
        if i.get("link") not in (None, 0)
    }
    widget_seq = expected_widget_sequence(input_specs, linked_inputs)
    expanded_seq = expand_with_control_widgets(widget_seq)
    legacy_seq = build_legacy_sequence(input_specs)

    values = list(node.get("widgets_values") or [])

    # Case 1: matches expanded (control widgets included) -> drop control entries
    if len(values) == len(expanded_seq):
        cleaned = []
        for val, (_, tlabel, _opts) in zip(values, expanded_seq):
            if tlabel == "CONTROL":
                continue
            cleaned.append(val)
        return cleaned, True

    # Case 1b: expanded + trailing legacy booleans -> trim and retry
    if len(values) > len(expanded_seq):
        trimmed = list(values)
        while len(trimmed) > len(expanded_seq) and isinstance(trimmed[-1], bool):
            trimmed.pop()
        if len(trimmed) == len(expanded_seq):
            cleaned = []
            for val, (_, tlabel, _opts) in zip(trimmed, expanded_seq):
                if tlabel == "CONTROL":
                    continue
                cleaned.append(val)
            return cleaned, True

    # Case 2: matches legacy (forceInput dummy present) -> drop forceInput entries
    if len(values) == len(legacy_seq):
        cleaned = []
        for val, (_name, tlabel, _opts) in zip(values, legacy_seq):
            if tlabel == "FORCE_INPUT":
                continue
            cleaned.append(val)
        return cleaned, True

    # Case 3: already expected length -> leave
    if len(values) == len(widget_seq):
        return values, False

    return values, False


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
    from nodes_garnish import GarnishSampler, ActionMerge
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
        "ActionMerge": ActionMerge,
        "SimpleTemplateBuilder": SimpleTemplateBuilder,
        "PromptCleaner": PromptCleaner,
        "CharacterProfileNode": CharacterProfileNode,
    }

    changed_files = 0
    changed_nodes = 0

    for root in roots:
        for path in iter_workflow_files(root):
            data = load_json(path)
            if not data or "nodes" not in data:
                continue
            nodes = data.get("nodes")
            if not isinstance(nodes, list):
                continue
            changed = False
            for node in nodes:
                ntype = node.get("type")
                cls = class_map.get(ntype)
                if not cls:
                    continue
                new_vals, did_change = normalize_widgets_values(node, cls)
                if did_change:
                    node["widgets_values"] = new_vals
                    changed = True
                    changed_nodes += 1
            if changed:
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                changed_files += 1

    print(f"Updated {changed_nodes} nodes across {changed_files} workflow files.")


if __name__ == "__main__":
    main()
