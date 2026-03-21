import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from workflow_class_map import build_class_map_for_workflows
from workflow_widget_validation import build_widget_plan, collect_input_specs, load_workflow


RESULTS_ROOT = ROOT / "assets" / "results" / "workflow_diversity"
SEED_INPUT_NAMES = {"seed", "noise_seed"}


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def derive_randomized_seed(run_seed: int, node_id: int, input_name: str) -> int:
    digest = hashlib.sha256(f"{run_seed}:{node_id}:{input_name}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & 0xFFFFFFFFFFFFFFFF


def build_link_lookup(workflow: dict) -> dict[int, tuple[int, int, int, int, str]]:
    lookup = {}
    for link in workflow.get("links", []):
        if isinstance(link, list) and len(link) >= 6:
            lookup[link[0]] = tuple(link[:6])
    return lookup


def linked_input_sources(node: dict, link_lookup: dict) -> dict[str, tuple[int, int]]:
    sources = {}
    for item in node.get("inputs", []) or []:
        link_id = item.get("link")
        if link_id in (None, 0):
            continue
        link = link_lookup.get(link_id)
        if not link:
            continue
        _link_id, origin_id, origin_slot, _target_id, _target_slot, _type = link
        sources[item["name"]] = (origin_id, origin_slot)
    return sources


def resolve_widget_inputs(node: dict, node_cls, run_seed: int) -> tuple[dict, dict]:
    plan = build_widget_plan(node, node_cls)
    widget_values = list(plan["widgets_values"] or [])
    widget_seq = list(plan["widget_seq"] or [])
    resolved = {}
    controls = {}

    for widget_index, (name, _type_spec, _options) in enumerate(widget_seq):
        if widget_index >= len(widget_values):
            continue

        value = widget_values[widget_index]
        if str(name).endswith("__control"):
            controls[name.split("__control", 1)[0]] = value
            continue

        resolved[name] = value

    for name in SEED_INPUT_NAMES:
        if name in resolved and controls.get(name) == "randomize":
            resolved[name] = derive_randomized_seed(run_seed, int(node["id"]), name)

    return resolved, controls


def execute_custom_workflow(workflow: dict, run_seed: int) -> dict:
    class_map = build_class_map_for_workflows([workflow])
    link_lookup = build_link_lookup(workflow)
    node_outputs = {}
    execution_trace = []

    for node in sorted(workflow.get("nodes", []), key=lambda item: item.get("order", 0)):
        node_type = node.get("type")
        node_cls = class_map.get(node_type)
        if not node_cls:
            continue

        node_instance = node_cls()
        function_name = getattr(node_cls, "FUNCTION")
        function = getattr(node_instance, function_name)
        input_specs = collect_input_specs(node_cls)
        linked_sources = linked_input_sources(node, link_lookup)
        widget_inputs, widget_controls = resolve_widget_inputs(node, node_cls, run_seed)

        kwargs = {}
        for name, _type_spec, options in input_specs:
            if name in linked_sources:
                origin_id, origin_slot = linked_sources[name]
                kwargs[name] = node_outputs[origin_id][origin_slot]
                continue
            if name in widget_inputs:
                kwargs[name] = widget_inputs[name]
                continue
            if options.get("forceInput", False):
                continue

        result = function(**kwargs)
        if not isinstance(result, tuple):
            result = (result,)
        node_outputs[int(node["id"])] = result
        execution_trace.append(
            {
                "node_id": int(node["id"]),
                "node_type": node_type,
                "function": function_name,
                "inputs": kwargs,
                "controls": widget_controls,
            }
        )

    return {
        "node_outputs": node_outputs,
        "execution_trace": execution_trace,
    }


def build_run_record(workflow: dict, run_seed: int) -> dict:
    executed = execute_custom_workflow(workflow, run_seed)
    node_outputs = executed["node_outputs"]
    nodes_by_type = {
        node["type"]: int(node["id"])
        for node in workflow.get("nodes", [])
        if int(node["id"]) in node_outputs
    }

    final_context_json = node_outputs[nodes_by_type["ContextGarnish"]][0]
    final_context = json.loads(final_context_json)
    raw_prompt = node_outputs[nodes_by_type["ContextPromptBuilder"]][0]
    cleaned_prompt = node_outputs[nodes_by_type["PromptCleaner"]][0]
    inspector_outputs = node_outputs.get(nodes_by_type.get("ContextInspector"), ("", ""))

    return {
        "run_seed": run_seed,
        "prompt": cleaned_prompt,
        "raw_prompt": raw_prompt,
        "summary_text": inspector_outputs[1] if len(inspector_outputs) > 1 else "",
        "context": final_context,
        "execution_trace": executed["execution_trace"],
    }


def top_items(counter: Counter, limit: int = 10) -> list[dict]:
    return [{"value": value, "count": count} for value, count in counter.most_common(limit)]


def summarize_records(records: list[dict]) -> dict:
    prompt_counter = Counter(record["prompt"] for record in records)
    character_counter = Counter(
        record["context"].get("extras", {}).get("character_name") or record["context"].get("subj", "")
        for record in records
    )
    location_counter = Counter(record["context"].get("loc", "") for record in records)
    action_counter = Counter(record["context"].get("action", "") for record in records)
    clothing_counter = Counter(record["context"].get("extras", {}).get("clothing_prompt", "") for record in records)
    location_prompt_counter = Counter(record["context"].get("extras", {}).get("location_prompt", "") for record in records)
    mood_counter = Counter(record["context"].get("meta", {}).get("mood", "") for record in records)
    signature_counter = Counter(
        (
            record["context"].get("extras", {}).get("character_name") or record["context"].get("subj", ""),
            record["context"].get("loc", ""),
            record["context"].get("action", ""),
            record["context"].get("meta", {}).get("mood", ""),
        )
        for record in records
    )
    warning_counter = Counter(
        warning
        for record in records
        for warning in record["context"].get("warnings", [])
    )
    scene_source_counter = Counter(
        history_item.get("decision", {}).get("selected_source", "unknown")
        for record in records
        for history_item in record["context"].get("history", [])
        if history_item.get("node") == "ContextSceneVariator"
    )

    prompt_lengths = [len(record["prompt"]) for record in records]
    unique_prompt_count = len(prompt_counter)
    run_count = len(records)

    return {
        "runs": run_count,
        "unique_prompts": unique_prompt_count,
        "unique_prompt_ratio": round(unique_prompt_count / run_count, 4) if run_count else 0.0,
        "unique_scene_signatures": len(signature_counter),
        "unique_locations": len(location_counter),
        "unique_actions": len(action_counter),
        "unique_clothing_prompts": len(clothing_counter),
        "unique_location_prompts": len(location_prompt_counter),
        "runs_with_warnings": sum(1 for record in records if record["context"].get("warnings")),
        "avg_prompt_length": round(sum(prompt_lengths) / run_count, 2) if run_count else 0.0,
        "min_prompt_length": min(prompt_lengths) if prompt_lengths else 0,
        "max_prompt_length": max(prompt_lengths) if prompt_lengths else 0,
        "top_characters": top_items(character_counter),
        "top_locations": top_items(location_counter),
        "top_actions": top_items(action_counter),
        "top_moods": top_items(mood_counter),
        "scene_variation_sources": top_items(scene_source_counter),
        "top_warnings": top_items(warning_counter),
        "top_prompt_duplicates": [
            {"prompt": prompt, "count": count}
            for prompt, count in prompt_counter.most_common(10)
        ],
        "top_scene_signatures": [
            {
                "character": signature[0],
                "location": signature[1],
                "action": signature[2],
                "mood": signature[3],
                "count": count,
            }
            for signature, count in signature_counter.most_common(10)
        ],
    }


def execute_records(
    workflow: dict,
    seed_start: int,
    runs: int,
    coverage_target_locations: int = 0,
    max_runs: int = 0,
) -> tuple[list[dict], list[dict]]:
    records = []
    seen_locations = set()
    coverage_progress = []

    if coverage_target_locations > 0:
        run_limit = max_runs if max_runs > 0 else max(runs, coverage_target_locations * 6)
    else:
        run_limit = runs

    for offset in range(run_limit):
        record = build_run_record(workflow, seed_start + offset)
        records.append(record)
        location = record["context"].get("loc", "")
        if location:
            seen_locations.add(location)
        coverage_progress.append(
            {
                "run": offset + 1,
                "seed": seed_start + offset,
                "unique_locations": len(seen_locations),
                "location": location,
            }
        )
        if coverage_target_locations > 0 and len(seen_locations) >= coverage_target_locations:
            break

    return records, coverage_progress


def write_outputs(records: list[dict], summary: dict, output_dir: Path):
    ensure_dir(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    samples_path = output_dir / f"context_workflow_samples_{timestamp}.jsonl"
    summary_path = output_dir / f"context_workflow_summary_{timestamp}.json"

    with samples_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return samples_path, summary_path


def print_summary(summary: dict, samples_path: Path, summary_path: Path):
    print("Workflow diversity analysis")
    print("==========================")
    print(f"runs: {summary['runs']}")
    print(f"unique prompts: {summary['unique_prompts']} ({summary['unique_prompt_ratio']:.2%})")
    print(f"unique scene signatures: {summary['unique_scene_signatures']}")
    print(f"unique locations: {summary['unique_locations']}")
    print(f"unique actions: {summary['unique_actions']}")
    print(f"unique clothing prompts: {summary['unique_clothing_prompts']}")
    print(f"unique location prompts: {summary['unique_location_prompts']}")
    if summary.get("coverage_target_locations"):
        print(
            "location coverage target: "
            f"{summary['coverage_target_locations']} "
            f"(reached={summary['coverage_reached']}, "
            f"runs_to_target={summary['runs_to_target']})"
        )
    print(f"runs with warnings: {summary['runs_with_warnings']}")
    print(
        "prompt length: "
        f"avg={summary['avg_prompt_length']} min={summary['min_prompt_length']} max={summary['max_prompt_length']}"
    )

    def print_counter_block(label: str, items: list[dict], key_name: str = "value"):
        print("")
        print(label)
        for item in items[:5]:
            print(f"- {item[key_name]}: {item['count']}")

    print_counter_block("Top characters", summary["top_characters"])
    print_counter_block("Top locations", summary["top_locations"])
    print_counter_block("Top moods", summary["top_moods"])
    print_counter_block("Scene variation sources", summary["scene_variation_sources"])
    print_counter_block("Top warnings", summary["top_warnings"])
    print("")
    print(f"samples: {samples_path}")
    print(f"summary: {summary_path}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Execute ComfyUI-workflow-context.json in-process and analyze output diversity."
    )
    parser.add_argument(
        "--workflow",
        default=str(ROOT / "ComfyUI-workflow-context.json"),
        help="Path to the workflow JSON to analyze.",
    )
    parser.add_argument("--runs", type=int, default=150, help="Number of workflow executions.")
    parser.add_argument("--seed-start", type=int, default=0, help="Starting master seed.")
    parser.add_argument(
        "--coverage-target-locations",
        type=int,
        default=0,
        help="Continue running until this many unique raw locations are seen, or max-runs is hit.",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=0,
        help="Hard cap when using --coverage-target-locations. Defaults to max(runs, target*6).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(RESULTS_ROOT),
        help="Directory for JSONL samples and summary JSON.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    workflow_path = Path(args.workflow)
    workflow = load_workflow(workflow_path)

    records, coverage_progress = execute_records(
        workflow,
        seed_start=args.seed_start,
        runs=args.runs,
        coverage_target_locations=args.coverage_target_locations,
        max_runs=args.max_runs,
    )
    summary = summarize_records(records)
    summary["workflow"] = str(workflow_path)
    summary["seed_start"] = args.seed_start
    summary["coverage_target_locations"] = args.coverage_target_locations
    summary["max_runs"] = args.max_runs
    summary["coverage_reached"] = (
        summary["unique_locations"] >= args.coverage_target_locations
        if args.coverage_target_locations > 0
        else False
    )
    summary["runs_to_target"] = (
        next(
            (
                item["run"]
                for item in coverage_progress
                if item["unique_locations"] >= args.coverage_target_locations
            ),
            None,
        )
        if args.coverage_target_locations > 0
        else None
    )
    summary["locations_seen"] = sorted(
        {record["context"].get("loc", "") for record in records if record["context"].get("loc", "")}
    )
    summary["location_coverage_progress"] = coverage_progress

    samples_path, summary_path = write_outputs(records, summary, Path(args.output_dir))
    print_summary(summary, samples_path, summary_path)


if __name__ == "__main__":
    main()
