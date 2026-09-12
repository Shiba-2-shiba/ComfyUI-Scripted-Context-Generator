import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.analyze_variation_candidates import load_candidate_catalog
from tools.plan_variation_prompt_schedule import (
    assign_subjects_to_locations,
    build_prompt_schedule,
    validate_prompt_schedule,
)
from tools.compare_variation_prompt_pair import scheduled_location_action_coverage
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
ITERATION = ROOT / "docs/variation_expansion/experiments/v150-candidate-shape-iteration-004/candidate-iteration.json"
COVERAGE_CONTRACT = ROOT / "docs/variation_expansion/experiments/v150-candidate-shape-iteration-005/coverage-contract.json"
WORKFLOW = ROOT / "ComfyUI-workflow-context.json"


class TestVariationPromptSchedule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_candidate_catalog(ITERATION)
        cls.schedule = build_prompt_schedule(
            candidate_iteration=ITERATION,
            coverage_contract_path=COVERAGE_CONTRACT,
            workflow_path=WORKFLOW,
            source_root=ROOT,
        )

    def test_subject_matching_is_deterministic_and_covers_all_subjects(self):
        first = assign_subjects_to_locations(self.catalog)
        second = assign_subjects_to_locations(self.catalog)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 19)
        self.assertEqual(set(first.values()), {item["id"] for item in self.catalog["subjects"]})

    def test_schedule_has_one_unique_row_and_action_per_location(self):
        rows = self.schedule["candidate_rows"]

        self.assertEqual(len(rows), 19)
        self.assertEqual(len({row["loc"] for row in rows}), 19)
        self.assertEqual(len({row["action"] for row in rows}), 19)
        self.assertEqual({row["loc"] for row in rows}, {item["id"] for item in self.catalog["locations"]})

    def test_control64_reaches_every_candidate_location(self):
        reachability = self.schedule["control_reachability"]

        self.assertEqual(len(reachability), 19)
        self.assertTrue(all(seeds for seeds in reachability.values()))
        self.assertEqual(
            {seed for seeds in reachability.values() for seed in seeds},
            set(range(64)),
        )

    def test_fixed_cohort_and_quality_authority_are_preserved(self):
        cohort = self.schedule["cohort"]

        self.assertEqual(len(cohort["control_seeds"]), 64)
        self.assertEqual(len(cohort["exploration_seeds"]), 16)
        self.assertFalse(self.schedule["coverage_is_quality_evidence"])
        self.assertEqual(self.schedule["fixed_verdict"], "reject")
        self.assertFalse(self.schedule["promotion_ready"])

    def test_schedule_is_canonical_and_recomputable(self):
        replay = build_prompt_schedule(
            candidate_iteration=ITERATION,
            coverage_contract_path=COVERAGE_CONTRACT,
            workflow_path=WORKFLOW,
            source_root=ROOT,
        )

        self.assertEqual(canonical_json_bytes(self.schedule), canonical_json_bytes(replay))
        self.assertEqual(validate_prompt_schedule(self.schedule, source_root=ROOT)["status"], "pass")

    def test_schedule_tampering_fails_closed(self):
        tampered = copy.deepcopy(self.schedule)
        tampered["candidate_rows"][0]["loc"] = "wrong_location"

        with self.assertRaises(WorkflowValidationError) as raised:
            validate_prompt_schedule(tampered, source_root=ROOT)

        self.assertEqual(raised.exception.code, "coverage_schedule_hash_mismatch")

    def test_scheduled_action_coverage_requires_exact_final_pair(self):
        first = self.schedule["expected_location_actions"][0]
        exact = {
            "final_context": {
                "loc": first["location"],
                "history": [{
                    "node": "ContextSceneVariator",
                    "decision": {"action": first["action"], "selected_loc": first["location"]},
                }],
            }
        }
        wrong_location = copy.deepcopy(exact)
        wrong_location["final_context"]["loc"] = "other_location"

        exact_result = scheduled_location_action_coverage([exact], self.schedule)
        wrong_result = scheduled_location_action_coverage([wrong_location], self.schedule)

        self.assertEqual(exact_result["observed_count"], 1)
        self.assertEqual(wrong_result["observed_count"], 0)

    def test_nonempty_context_source_json_bypassing_prompts_is_rejected(self):
        workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
        node = next(item for item in workflow["nodes"] if item["id"] == 1)
        node["widgets_values"][0] = '{"subj":"bypass"}'
        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
            path = Path(temp_dir) / "workflow.json"
            path.write_text(json.dumps(workflow), encoding="utf-8")
            with self.assertRaises(WorkflowValidationError) as raised:
                build_prompt_schedule(
                    candidate_iteration=ITERATION,
                    coverage_contract_path=COVERAGE_CONTRACT,
                    workflow_path=path,
                    source_root=ROOT,
                )

        self.assertEqual(raised.exception.code, "coverage_selector_drift")


if __name__ == "__main__":
    unittest.main()
