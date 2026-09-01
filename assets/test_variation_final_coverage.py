import unittest
import json
from pathlib import Path

from tools.plan_variation_final_coverage import (
    solve_row_slot_assignment,
    validate_final_coverage_contract,
)
from tools.plan_variation_prompt_schedule import validate_prompt_schedule
from tools.workflow_prompt_runner import WorkflowValidationError


class TestVariationFinalCoveragePlanner(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]
    EXPERIMENT = ROOT / "docs/variation_expansion/experiments/v150-candidate-shape-iteration-006"

    def test_tracked_contract_schedule_and_matrix_are_self_consistent(self):
        contract_path = self.EXPERIMENT / "full-workflow-coverage-contract.json"
        schedule_path = self.EXPERIMENT / "full-workflow-schedule.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        schedule = json.loads(schedule_path.read_text(encoding="utf-8"))

        self.assertEqual(
            validate_final_coverage_contract(contract, repository_root=self.ROOT)["status"],
            "pass",
        )
        self.assertEqual(
            validate_prompt_schedule(schedule, source_root=self.ROOT)["status"],
            "pass",
        )
        self.assertEqual(schedule["matching_cardinality"], 19)
        self.assertEqual(schedule["subject_coverage_count"], 15)
        self.assertEqual(schedule["extra_seed_count"], 0)
        self.assertEqual(len(schedule["final_witnesses"]), 19)

    def test_assignment_is_deterministic_and_covers_all_targets_and_subjects(self):
        masks = [
            [0b001, 0b010, 0b100],
            [0b010, 0b100, 0b001],
            [0b100, 0b001, 0b010],
        ]

        first = solve_row_slot_assignment(
            slot_variant_masks=masks,
            variant_locations=[0, 1, 2],
            variant_subjects=[0, 1, 2],
            target_count=3,
            subject_count=3,
            beam_width=32,
        )
        replay = solve_row_slot_assignment(
            slot_variant_masks=masks,
            variant_locations=[0, 1, 2],
            variant_subjects=[0, 1, 2],
            target_count=3,
            subject_count=3,
            beam_width=32,
        )

        self.assertEqual(first, replay)
        self.assertEqual(first.coverage_mask.bit_count(), 3)
        self.assertEqual(first.subject_mask.bit_count(), 3)
        self.assertEqual(len(set(first.choices)), 3)

    def test_location_rows_cannot_be_reused_across_slots(self):
        state = solve_row_slot_assignment(
            slot_variant_masks=[
                [0b001, 0b001, 0b010],
                [0b010, 0b100, 0b100],
            ],
            variant_locations=[0, 0, 1],
            variant_subjects=[0, 1, 1],
            target_count=2,
            subject_count=2,
            beam_width=32,
        )

        self.assertNotEqual(state.choices, (0, 1))
        self.assertEqual(state.used_location_mask.bit_count(), 2)

    def test_partial_location_coverage_fails_closed(self):
        with self.assertRaises(WorkflowValidationError) as raised:
            solve_row_slot_assignment(
                slot_variant_masks=[[0b001, 0], [0b001, 0]],
                variant_locations=[0, 1],
                variant_subjects=[0, 1],
                target_count=2,
                subject_count=2,
                beam_width=8,
            )

        self.assertEqual(raised.exception.code, "final_coverage_search_inconclusive")

    def test_full_location_coverage_without_all_subjects_fails_closed(self):
        with self.assertRaises(WorkflowValidationError) as raised:
            solve_row_slot_assignment(
                slot_variant_masks=[[0b01, 0b10], [0b10, 0b01]],
                variant_locations=[0, 1],
                variant_subjects=[0, 0],
                target_count=2,
                subject_count=2,
                beam_width=8,
            )

        self.assertEqual(raised.exception.code, "final_coverage_search_inconclusive")


if __name__ == "__main__":
    unittest.main()
