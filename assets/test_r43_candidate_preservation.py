"""Expansion preservation rejects unrelated mutations even on a new v2 case."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from core.context_codec import context_from_json
from nodes_prompt_cleaner import PromptCleaner
from pipeline.prompt_orchestrator import build_prompt_from_context
from tools import realizer_candidate_preservation as preservation
from tools.workflow_prompt_runner import build_canonical_record
from workflow_widget_validation import load_workflow


@pytest.fixture(scope="module")
def ordinary_pair():
    root = Path(__file__).resolve().parents[1]
    fixture = json.loads((root / "assets/fixtures/r43_ordinary_real_cases.json").read_text(encoding="utf-8"))
    case = fixture["cases"][0]
    record = build_canonical_record(load_workflow(root / "ComfyUI-workflow-context.json"), case["run_seed"])
    args = case["builder_inputs"]
    context, raw = build_prompt_from_context(context_from_json(args["context_json"]),
        args["template"], args["composition_mode"], args["seed"])
    assert record["raw_prompt"] == raw
    # A one-row unit cohort reuses the real case without running 512 samples.
    record["run_seed"] = 0
    current = {"record": record, "builder_context": context.to_dict()}
    baseline = copy.deepcopy(current)
    baseline["builder_context"] = case["baseline_builder_context"]
    baseline["record"]["raw_prompt"] = case["baseline_raw"]
    baseline["record"]["cleaned_prompt"] = case["baseline_cleaned"]
    next(t for t in baseline["record"]["execution_trace"] if t["node_type"] == "PromptCleaner")["inputs"]["text"] = case["baseline_raw"]
    assert PromptCleaner().clean(text=raw)[0] == record["cleaned_prompt"]
    return baseline, current


def compare(pair):
    return preservation.compare_pairs([pair[0]], [pair[1]], expected_count=1, require_baseline_v2=0)


def test_real_ordinary_expansion_passes_without_mutating_inputs(ordinary_pair):
    before = copy.deepcopy(ordinary_pair)
    report = compare(ordinary_pair)
    assert report["status"] == "PASS"
    assert report["baseline_v2_count"] == 0 and report["current_v2_count"] == 1
    assert report["new_cases"][0]["family"] == "subject_action__scene_tail"
    assert report["signature_mismatch_count"] == report["upstream_mismatch_count"] == 0
    assert ordinary_pair == before


@pytest.mark.parametrize("target", ["pair", "record", "context", "header", "trace", "builder_input", "cleaner_controls", "decision", "selected_object"])
def test_unrelated_changes_on_new_case_fail(ordinary_pair, target):
    before, after = copy.deepcopy(ordinary_pair)
    record, context = after["record"], after["builder_context"]
    if target == "pair":
        after["unknown"] = True
    elif target == "record":
        record["unknown"] = True
    elif target == "context":
        context["unknown"] = True
    elif target == "header":
        context["history"][-1]["warnings"].append("changed")
    elif target == "trace":
        record["execution_trace"][0]["unknown"] = True
    elif target == "builder_input":
        next(t for t in record["execution_trace"] if t["node_type"] == "ContextPromptBuilder")["inputs"]["template"] = "changed"
    elif target == "cleaner_controls":
        next(t for t in record["execution_trace"] if t["node_type"] == "PromptCleaner")["controls"]["unknown"] = True
    elif target == "decision":
        context["history"][-1]["decision"]["unknown_selection"] = True
    else:
        context["history"][-1]["decision"]["content_plan"]["semantic_slots"]["object"] = "phone"
    assert compare((before, after))["status"] == "FAIL"


@pytest.mark.parametrize("damage", ["count", "partial", "duplicate", "seed", "bool_seed", "order", "record", "context", "history", "prompt", "trace", "cleaner", "selector", "hash", "source_selection", "baseline_count"])
def test_invalid_or_unbound_evidence_raises(ordinary_pair, damage):
    before, after = ([copy.deepcopy(ordinary_pair[0])], [copy.deepcopy(ordinary_pair[1])])
    expected, baseline_count = 1, 0
    if damage == "count":
        after.clear()
    elif damage == "partial":
        expected = 512
    elif damage == "duplicate":
        before *= 2
        after *= 2
        expected = 2
    elif damage == "seed":
        after[0]["record"]["run_seed"] = 5
    elif damage == "bool_seed":
        after[0]["record"]["run_seed"] = False
    elif damage == "order":
        before[0]["record"]["run_seed"] = 1
        after[0]["record"]["run_seed"] = 1
    elif damage == "context":
        after[0]["builder_context"].pop("extras")
    elif damage == "record":
        after[0]["record"].pop("resolved_seeds")
    elif damage == "history":
        after[0]["builder_context"]["history"] = []
    elif damage == "prompt":
        after[0]["builder_context"]["history"][-1]["decision"]["prompt"] = "unbound"
    elif damage == "trace":
        after[0]["record"]["execution_trace"] = []
    elif damage == "cleaner":
        next(t for t in after[0]["record"]["execution_trace"] if t["node_type"] == "PromptCleaner")["inputs"]["text"] = "unbound"
    elif damage == "selector":
        after[0]["record"]["output_selectors"]["raw_prompt"] = []
    elif damage == "hash":
        after[0]["record"]["config_hash"] = "f" * 64
    elif damage == "source_selection":
        after[0]["builder_context"]["history"][-1]["decision"].pop("action_frame")
    else:
        baseline_count = 9
    with pytest.raises(ValueError):
        preservation.compare_pairs(before, after, expected_count=expected, require_baseline_v2=baseline_count)


def test_previous_success_and_remaining_fallback_require_whole_record_equality(ordinary_pair):
    for original, required in ((ordinary_pair[0], 0), (ordinary_pair[1], 1)):
        changed = copy.deepcopy(original)
        changed["record"]["unknown"] = True
        result = preservation.compare_pairs([original], [changed], expected_count=1, require_baseline_v2=required)
        assert result["status"] == "FAIL"
        assert result["new_cases"] == []


def test_existing_cli_output_is_never_overwritten(tmp_path):
    output = tmp_path / "result.json"
    output.write_text("keep", encoding="utf-8")
    assert preservation.main(["--baseline-pairs", "missing", "--current-pairs", "missing", "--output", str(output)]) == 2
    assert output.read_text(encoding="utf-8") == "keep"


def test_optimized_python_cannot_disable_validation():
    result = subprocess.run([sys.executable, "-O", "-c",
        "from tools.realizer_candidate_preservation import compare_pairs; compare_pairs([], [])"],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert result.returncode != 0 and "ValueError: pair cohort count mismatch" in result.stderr
