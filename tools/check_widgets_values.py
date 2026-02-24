import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_workflow(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def collect_input_specs(cls):
    specs = cls.INPUT_TYPES()
    ordered = []
    for group_name in ("required", "optional"):
        group = specs.get(group_name, {})
        for name, spec in group.items():
            # spec format: (type, options_dict)
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
        # If the widget input is linked, it may not be serialized in widgets_values.
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

    force_input_count = sum(1 for _, _, opt in input_specs if opt.get("forceInput"))

    # Control widget heuristic: seed/noise_seed uses control widget in frontend by default.
    # If widgets_values includes control widget values, expand expected sequence.
    expanded_widget_seq = []
    for name, type_spec, options in widget_seq:
        expanded_widget_seq.append((name, type_spec, options))
        if options.get("control_after_generate") or name in ("seed", "noise_seed"):
            if type_label(type_spec) in ("INT", "FLOAT"):
                expanded_widget_seq.append((f"{name}__control", "CONTROL", {}))

    if values_len == len(expanded_widget_seq):
        widget_seq = expanded_widget_seq
        widget_count = len(expanded_widget_seq)

    if values_len != widget_count:
        issues.append(
            f"widgets_values length {values_len} != expected {widget_count}"
        )

        # Heuristic: if length equals expected + forceInput_count, likely legacy dummy values.
        if force_input_count and values_len == widget_count + force_input_count:
            issues.append(
                "length matches expected + forceInput count; likely legacy dummy values present"
            )

    # Type sanity check for existing values
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
            if val is None or (isinstance(val, (int, float)) and val != val):
                issues.append(
                    f"widget '{name}' expects COMBO value but got invalid"
                )
    return issues, widget_seq


def main():
    wf_path = ROOT / "ComfyUI-workflow-exmaple.json"
    wf = load_workflow(wf_path)

    # Register custom node classes here
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

    nodes = wf.get("nodes", [])
    problems = []

    for node in nodes:
        ntype = node.get("type")
        cls = class_map.get(ntype)
        if not cls:
            continue
        issues, widget_seq = check_node(node, cls)
        if issues:
            problems.append((node.get("id"), ntype, issues, widget_seq, node.get("widgets_values")))

    if not problems:
        print("OK: no widget_values issues detected for custom nodes.")
        return

    print("Detected widget_values issues:")
    for node_id, ntype, issues, widget_seq, widget_vals in problems:
        print(f"- Node {node_id} ({ntype})")
        print(f"  widgets_values: {widget_vals}")
        print(f"  expected widgets: {[name for name, _, _ in widget_seq]}")
        for issue in issues:
            print(f"  - {issue}")


if __name__ == "__main__":
    main()
