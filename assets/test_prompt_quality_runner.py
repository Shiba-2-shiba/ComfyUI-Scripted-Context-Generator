import copy
import hashlib
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.workflow_prompt_runner import (
    WorkflowProfile,
    WorkflowValidationError,
    build_canonical_record,
    build_canonical_records,
    canonical_json_bytes,
    execute_workflow,
    load_profile,
)
from tools.analyze_context_workflow_diversity import build_run_record as build_adapter_record
from tools.prompt_quality_loop import build_cohort, generate_run, validate_cohort
from workflow_class_map import build_class_map_for_workflows
from workflow_widget_validation import build_widget_plan, collect_input_specs, load_workflow


PROFILE_PATH = ROOT / "verification" / "fixtures" / "prompt_quality_supported_profile.json"
COHORT_PATH = ROOT / "assets" / "fixtures" / "prompt_quality_control_seeds.json"


class ValueNode:
    RETURN_TYPES = ("STRING",)
    FUNCTION = "emit"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"value": ("STRING", {"default": "default"})}}

    def emit(self, value):
        return (value,)


class PassNode:
    RETURN_TYPES = ("STRING",)
    FUNCTION = "forward"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"source": ("STRING", {"forceInput": True})}}

    def forward(self, source):
        return (source,)


class TripleOutputNode:
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    FUNCTION = "emit"

    @classmethod
    def INPUT_TYPES(cls):
        return {}

    def emit(self):
        return ('{"subj":"1girl"}', "raw prompt", "clean prompt")


def profile(outputs, allowed=("Value", "Pass"), excluded=()):
    return WorkflowProfile.from_mapping(
        {
            "profile_id": "test-v1",
            "version": "1",
            "allowed_node_types": list(allowed),
            "output_selectors": outputs,
            "excluded_terminal_nodes": list(excluded),
        }
    )


def value_workflow(values=("first", "second")):
    return {
        "nodes": [
            {"id": index + 1, "type": "Value", "order": index, "inputs": [], "widgets_values": [value]}
            for index, value in enumerate(values)
        ],
        "links": [],
    }


def chained_workflow(origin_slot=0):
    return {
        "nodes": [
            {"id": 1, "type": "Value", "order": 99, "inputs": [], "widgets_values": ["source"]},
            {"id": 2, "type": "Pass", "order": 0, "inputs": [{"name": "source", "link": 1}], "widgets_values": []},
        ],
        "links": [[1, 1, origin_slot, 2, 0, "STRING"]],
    }


def build_direct_chain_oracle(workflow, run_seed):
    """Pre-refactor execution algorithm, independent of the strict runner."""

    class_map = build_class_map_for_workflows([workflow])
    links = {
        int(link[0]): tuple(link[:6])
        for link in workflow.get("links", [])
        if isinstance(link, list) and len(link) >= 6
    }
    node_outputs = {}
    execution_trace = []
    for node in sorted(workflow.get("nodes", []), key=lambda item: item.get("order", 0)):
        node_type = node.get("type")
        node_cls = class_map.get(node_type)
        if node_cls is None:
            continue
        linked_sources = {}
        for item in node.get("inputs", []) or []:
            link_id = item.get("link")
            if link_id in (None, 0):
                continue
            _link_id, origin_id, origin_slot, _target_id, _target_slot, _type = links[link_id]
            linked_sources[item["name"]] = (int(origin_id), int(origin_slot))

        plan = build_widget_plan(node, node_cls)
        widget_inputs = {}
        controls = {}
        for index, (name, _type_spec, _options) in enumerate(plan["widget_seq"]):
            value = plan["widgets_values"][index]
            if str(name).endswith("__control"):
                controls[str(name).split("__control", 1)[0]] = value
            else:
                widget_inputs[str(name)] = value
        for name in ("seed", "noise_seed"):
            if name in widget_inputs and controls.get(name) == "randomize":
                digest = hashlib.sha256(f"{run_seed}:{int(node['id'])}:{name}".encode("utf-8")).digest()
                widget_inputs[name] = int.from_bytes(digest[:8], "big") & 0xFFFFFFFFFFFFFFFF

        kwargs = {}
        for name, _type_spec, options in collect_input_specs(node_cls):
            if name in linked_sources:
                origin_id, origin_slot = linked_sources[name]
                kwargs[name] = node_outputs[origin_id][origin_slot]
            elif name in widget_inputs:
                kwargs[name] = widget_inputs[name]
            elif options.get("forceInput", False):
                continue
        function_name = node_cls.FUNCTION
        result = getattr(node_cls(), function_name)(**kwargs)
        if not isinstance(result, tuple):
            result = (result,)
        node_outputs[int(node["id"])] = result
        execution_trace.append(
            {
                "node_id": int(node["id"]),
                "node_type": node_type,
                "function": function_name,
                "inputs": kwargs,
                "controls": controls,
            }
        )

    nodes_by_type = {
        node["type"]: int(node["id"])
        for node in workflow.get("nodes", [])
        if int(node["id"]) in node_outputs
    }
    inspector = node_outputs.get(nodes_by_type.get("ContextInspector"), ("", ""))
    return {
        "context": json.loads(node_outputs[nodes_by_type["ContextGarnish"]][0]),
        "execution_trace": execution_trace,
        "prompt": node_outputs[nodes_by_type["PromptCleaner"]][0],
        "raw_prompt": node_outputs[nodes_by_type["ContextPromptBuilder"]][0],
        "run_seed": run_seed,
        "summary_text": inspector[1] if len(inspector) > 1 else "",
    }


class TestStrictWorkflowValidation(unittest.TestCase):
    def assert_error_code(self, expected_code, workflow, selected_profile, class_map):
        with self.assertRaises(WorkflowValidationError) as caught:
            execute_workflow(workflow, 7, selected_profile, class_map=class_map)
        self.assertEqual(caught.exception.code, expected_code)
        self.assertEqual(caught.exception.to_envelope()["error"]["code"], expected_code)
        return caught.exception

    def test_node_id_and_slot_select_exact_output_not_last_node_of_type(self):
        workflow = value_workflow()
        result = execute_workflow(
            workflow,
            7,
            profile({"selected": {"node_id": 1, "slot": 0}}),
            class_map={"Value": ValueNode},
        )

        self.assertEqual(result["outputs"]["selected"], "first")
        self.assertEqual([item["node_id"] for item in result["execution_trace"]], [1])

    def test_duplicate_node_type_selector_is_ambiguous(self):
        error = self.assert_error_code(
            "ambiguous_output_selector",
            value_workflow(),
            profile({"selected": {"node_type": "Value", "slot": 0}}),
            {"Value": ValueNode},
        )
        self.assertEqual(error.details["matching_node_ids"], [1, 2])

    def test_unknown_node_inside_ancestor_closure_fails(self):
        workflow = chained_workflow()
        workflow["nodes"][0]["type"] = "Unknown"
        self.assert_error_code(
            "unsupported_node",
            workflow,
            profile({"selected": {"node_id": 2, "slot": 0}}),
            {"Pass": PassNode},
        )

    def test_unknown_node_outside_closure_must_be_declared_excluded(self):
        workflow = value_workflow(("selected",))
        workflow["nodes"].append(
            {"id": 9, "type": "PreviewAny", "order": 9, "inputs": [], "widgets_values": []}
        )
        self.assert_error_code(
            "unsupported_node",
            workflow,
            profile({"selected": {"node_id": 1, "slot": 0}}),
            {"Value": ValueNode},
        )

    def test_declared_external_terminal_is_recorded_but_not_executed(self):
        workflow = value_workflow(("selected",))
        workflow["nodes"].append(
            {"id": 9, "type": "PreviewAny", "order": 9, "inputs": [], "widgets_values": []}
        )
        selected_profile = profile(
            {"selected": {"node_id": 1, "slot": 0}},
            excluded=({"node_id": 9, "node_type": "PreviewAny", "reason": "test preview"},),
        )

        result = execute_workflow(workflow, 7, selected_profile, class_map={"Value": ValueNode})

        self.assertEqual(result["excluded_terminal_nodes"], [
            {"node_id": 9, "node_type": "PreviewAny", "reason": "test preview"}
        ])
        self.assertNotIn(9, [item["node_id"] for item in result["execution_trace"]])

    def test_missing_upstream_link_fails_stably(self):
        workflow = chained_workflow()
        workflow["nodes"][1]["inputs"][0]["link"] = 404
        first = self.assert_error_code(
            "missing_upstream", workflow, profile({"selected": {"node_id": 2, "slot": 0}}), {"Value": ValueNode, "Pass": PassNode}
        )
        second = self.assert_error_code(
            "missing_upstream", workflow, profile({"selected": {"node_id": 2, "slot": 0}}), {"Value": ValueNode, "Pass": PassNode}
        )
        self.assertEqual(canonical_json_bytes(first.to_envelope()), canonical_json_bytes(second.to_envelope()))

    def test_missing_upstream_slot_fails_stably(self):
        self.assert_error_code(
            "missing_upstream_slot",
            chained_workflow(origin_slot=3),
            profile({"selected": {"node_id": 2, "slot": 0}}),
            {"Value": ValueNode, "Pass": PassNode},
        )

    def test_cycle_in_output_ancestor_closure_fails(self):
        workflow = {
            "nodes": [
                {"id": 1, "type": "Pass", "order": 1, "inputs": [{"name": "source", "link": 1}], "widgets_values": []},
                {"id": 2, "type": "Pass", "order": 0, "inputs": [{"name": "source", "link": 2}], "widgets_values": []},
            ],
            "links": [[1, 2, 0, 1, 0, "STRING"], [2, 1, 0, 2, 0, "STRING"]],
        }
        error = self.assert_error_code(
            "cycle_detected", workflow, profile({"selected": {"node_id": 2, "slot": 0}}, allowed=("Pass",)), {"Pass": PassNode}
        )
        self.assertEqual(error.details["node_ids"], [1, 2])

    def test_topological_dependencies_override_workflow_order(self):
        result = execute_workflow(
            chained_workflow(),
            7,
            profile({"selected": {"node_id": 2, "slot": 0}}),
            class_map={"Value": ValueNode, "Pass": PassNode},
        )
        self.assertEqual([item["node_id"] for item in result["execution_trace"]], [1, 2])


class TestRunnerCliBoundary(unittest.TestCase):
    def run_cli(self, workflow_path, output_path):
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "workflow_prompt_runner.py"),
                "--workflow",
                str(workflow_path),
                "--seed",
                "7",
                "--output",
                str(output_path),
            ],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )

    def assert_stable_cli_error(self, expected_code, workflow_path, output_path):
        first = self.run_cli(workflow_path, output_path)
        second = self.run_cli(workflow_path, output_path)
        self.assertNotEqual(first.returncode, 0)
        self.assertEqual(first.stderr, second.stderr)
        self.assertNotIn(b"Traceback", first.stderr)
        envelope = json.loads(first.stderr.decode("utf-8"))
        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["error"]["code"], expected_code)

    def test_missing_workflow_emits_stable_canonical_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assert_stable_cli_error(
                "workflow_not_found", root / "missing.json", root / "records.jsonl"
            )

    def test_malformed_workflow_json_emits_stable_canonical_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workflow_path = root / "malformed.json"
            workflow_path.write_text('{"nodes": [', encoding="utf-8")
            self.assert_stable_cli_error(
                "malformed_workflow_json", workflow_path, root / "records.jsonl"
            )

    def test_workflow_read_oserror_emits_stable_canonical_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workflow_directory = root / "workflow-directory"
            workflow_directory.mkdir()
            self.assert_stable_cli_error(
                "workflow_read_error", workflow_directory, root / "records.jsonl"
            )


class TestCanonicalRunnerArtifacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = load_workflow(ROOT / "ComfyUI-workflow-context.json")
        cls.profile = load_profile(PROFILE_PATH)

    def test_sample_workflow_executes_only_output_ancestor_closure(self):
        record = build_canonical_record(self.workflow, 3, self.profile)

        self.assertTrue(record["raw_prompt"])
        self.assertTrue(record["cleaned_prompt"])
        self.assertTrue(record["context"]["subj"])
        self.assertNotIn(11, [item["node_id"] for item in record["execution_trace"]])
        self.assertEqual(record["excluded_terminal_nodes"][0]["node_type"], "PreviewAny")

    def test_compat_adapter_matches_independent_direct_chain_oracle(self):
        for seed in (0, 3, 13, 21):
            with self.subTest(seed=seed):
                expected = build_direct_chain_oracle(self.workflow, seed)
                actual = build_adapter_record(self.workflow, seed)
                self.assertEqual(actual, expected)
                self.assertEqual(
                    set(actual),
                    {"context", "execution_trace", "prompt", "raw_prompt", "run_seed", "summary_text"},
                )

    def test_override_hash_is_immutable_and_part_of_effective_workflow_hash(self):
        base = execute_workflow(self.workflow, 3, self.profile)
        overrides = {8: {"composition_mode": False}}
        original = copy.deepcopy(overrides)
        candidate = execute_workflow(self.workflow, 3, self.profile, overrides=overrides)

        self.assertEqual(overrides, original)
        self.assertEqual(base["base_workflow_hash"], candidate["base_workflow_hash"])
        self.assertNotEqual(base["override_hash"], candidate["override_hash"])
        self.assertNotEqual(base["effective_workflow_hash"], candidate["effective_workflow_hash"])
        self.assertEqual(candidate["overrides"], overrides)

    def test_explicit_false_override_keeps_legacy_renderer_available(self):
        overrides = {8: {"composition_mode": False}}
        first = build_canonical_record(self.workflow, 3, self.profile, overrides=overrides)
        second = build_canonical_record(self.workflow, 3, self.profile, overrides=overrides)
        prompt_step = next(
            item for item in first["execution_trace"]
            if item["node_type"] == "ContextPromptBuilder"
        )

        self.assertIs(prompt_step["inputs"]["composition_mode"], False)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))

    def test_canonical_record_is_byte_identical_and_excludes_manifest_telemetry(self):
        first = build_canonical_record(self.workflow, 13, self.profile)
        second = build_canonical_record(self.workflow, 13, self.profile)

        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        self.assertTrue(canonical_json_bytes(first).endswith(b"\n"))
        for forbidden in ("run_id", "timestamp", "host", "dirty_state", "duration", "resources"):
            self.assertNotIn(forbidden, first)

    def test_control_and_exploration_cohort_builds_exactly_64_plus_16(self):
        fixture = json.loads(COHORT_PATH.read_text(encoding="utf-8"))
        control = fixture["control_seeds"]
        experiment_seed = fixture["exploration"]["experiment_seed"]
        cohort = build_cohort(experiment_seed, iteration_id=1, control_seeds=control)
        exploration = cohort["exploration_seeds"]
        seeds = control + exploration
        workflow = value_workflow(("unused",))
        workflow["nodes"] = [{"id": 1, "type": "Triple", "order": 0, "inputs": [], "widgets_values": []}]
        selected_profile = profile(
            {
                "final_context": {"node_id": 1, "slot": 0, "encoding": "json"},
                "raw_prompt": {"node_id": 1, "slot": 1},
                "cleaned_prompt": {"node_id": 1, "slot": 2},
            },
            allowed=("Triple",),
        )
        cohorts = {seed: ("control" if seed in set(control) else "exploration") for seed in seeds}

        records = build_canonical_records(
            workflow, seeds, selected_profile, class_map={"Triple": TripleOutputNode}, cohort_by_seed=cohorts
        )

        self.assertEqual(len(control), 64)
        self.assertEqual(len(exploration), 16)
        self.assertEqual(len(records), 80)
        self.assertEqual(sum(item["cohort"] == "control" for item in records), 64)
        self.assertEqual(sum(item["cohort"] == "exploration" for item in records), 16)
        self.assertEqual(len(set(seeds)), 80)

    def test_exploration_cohort_is_deterministic_and_rotates_by_iteration(self):
        fixture = json.loads(COHORT_PATH.read_text(encoding="utf-8"))
        kwargs = {
            "experiment_seed": fixture["exploration"]["experiment_seed"],
            "control_seeds": fixture["control_seeds"],
        }

        first = build_cohort(iteration_id="iteration-001", **kwargs)
        replay = build_cohort(iteration_id="iteration-001", **kwargs)
        rotated = build_cohort(iteration_id="iteration-002", **kwargs)

        self.assertEqual(first, replay)
        self.assertNotEqual(first["exploration_seeds"], rotated["exploration_seeds"])
        self.assertTrue(set(first["control_seeds"]).isdisjoint(first["exploration_seeds"]))

    def test_missing_duplicate_and_drifted_cohorts_are_rejected(self):
        cases = (
            ({"control_seeds": list(range(64)), "exploration_seeds": list(range(100, 115))}, "missing_seed"),
            ({"control_seeds": list(range(64)), "exploration_seeds": [63] + list(range(100, 115))}, "duplicate_seed"),
            ({"control_seeds": list(range(63)), "exploration_seeds": list(range(100, 117))}, "cohort_drift"),
        )
        for cohort, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                with self.assertRaises(WorkflowValidationError) as caught:
                    validate_cohort(cohort)
                self.assertEqual(caught.exception.code, expected_code)

    def test_generated_run_separates_canonical_manifest_and_telemetry(self):
        artifact_parent = ROOT / "assets" / "results"
        artifact_parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix="prompt-quality-l0-", dir=artifact_parent))
        self.addCleanup(lambda: shutil.rmtree(temporary, ignore_errors=True))

        result = generate_run(
            self.workflow,
            temporary / "run",
            artifact_root=temporary,
            experiment_seed=11,
            iteration_id="fixture",
            control_seeds=json.loads(COHORT_PATH.read_text(encoding="utf-8"))["control_seeds"],
            profile=self.profile,
            verify_replay=False,
        )

        records_text = (temporary / "run" / "records.jsonl").read_text(encoding="utf-8")
        metrics = json.loads((temporary / "run" / "metrics.json").read_text(encoding="utf-8"))
        manifest = json.loads((temporary / "run" / "run-manifest.json").read_text(encoding="utf-8"))
        telemetry = json.loads((temporary / "run" / "telemetry.json").read_text(encoding="utf-8"))
        first_record = json.loads(records_text.splitlines()[0])

        self.assertEqual(result["metrics"]["record_count"], 80)
        self.assertEqual(metrics["control_count"], 64)
        self.assertEqual(metrics["exploration_count"], 16)
        self.assertIn("run_id", manifest)
        self.assertIn("created_at", manifest)
        self.assertIn("host", manifest)
        self.assertIn("run_duration_ms", telemetry)
        self.assertIn("duration_ms", telemetry["runs"][0])
        for dynamic_key in ("run_id", "created_at", "host", "run_duration_ms", "duration_ms"):
            self.assertNotIn(dynamic_key, first_record)
            self.assertNotIn(dynamic_key, metrics)

    def test_duplicate_seed_is_rejected(self):
        with self.assertRaises(WorkflowValidationError) as caught:
            build_canonical_records(
                {"nodes": [{"id": 1, "type": "Triple", "order": 0, "inputs": [], "widgets_values": []}], "links": []},
                [7, 7],
                profile({"final_context": {"node_id": 1, "slot": 0, "encoding": "json"}}, allowed=("Triple",)),
                class_map={"Triple": TripleOutputNode},
            )
        self.assertEqual(caught.exception.code, "duplicate_seed")


class TestVerificationAssets(unittest.TestCase):
    def test_environment_manifest_is_pinned_and_declares_required_parity_outputs(self):
        manifest = json.loads((ROOT / "verification" / "environment.json").read_text(encoding="utf-8"))
        for repository in manifest["repositories"].values():
            self.assertRegex(repository["commit"], r"^[0-9a-f]{40}$")
            self.assertTrue(repository["path"])
            self.assertTrue(repository["ref"])
        self.assertEqual(
            manifest["parity"]["required_outputs"],
            ["final_context", "raw_prompt", "cleaned_prompt"],
        )
        self.assertEqual(len(manifest["parity"]["sentinel_seeds"]), 8)

    def test_parity_workflow_connects_all_three_outputs_to_verification_sink(self):
        workflow = load_workflow(ROOT / "verification" / "fixtures" / "prompt_parity_workflow.json")
        sink = next(node for node in workflow["nodes"] if node["type"] == "PromptQualityVerificationSink")
        self.assertEqual(
            {item["name"] for item in sink["inputs"]},
            {"final_context", "raw_prompt", "cleaned_prompt"},
        )
        self.assertTrue(workflow["extra"]["verification_only"])

    def test_verification_sink_canonicalizes_context_without_product_registration(self):
        package_registry = importlib.import_module("__init__")
        sink_module = importlib.import_module("verification.comfyui_sink")
        sink_cls = sink_module.NODE_CLASS_MAPPINGS["PromptQualityVerificationSink"]

        envelope = sink_cls().capture('{"z":2,"a":1}', "raw", "clean")
        payload_text, = envelope["result"]

        self.assertEqual(
            payload_text,
            '{"cleaned_prompt":"clean","final_context":{"a":1,"z":2},"raw_prompt":"raw"}',
        )
        self.assertEqual(envelope["ui"], {"canonical_outputs": [payload_text]})
        self.assertNotIn("PromptQualityVerificationSink", package_registry.NODE_CLASS_MAPPINGS)
        self.assertNotIn("verification.comfyui_sink", package_registry.NODE_SURFACE_GROUPS.values())


if __name__ == "__main__":
    unittest.main()
