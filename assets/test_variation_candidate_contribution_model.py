import copy
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import model_variation_candidate_contributions as contribution_model
from tools.analyze_variation_candidates import load_candidate_catalog
from tools.model_variation_candidate_contributions import (
    model_candidate_contributions,
    plan_location_additions,
)
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
ITERATION_ROOT = ROOT / "docs" / "variation_expansion" / "experiments" / "v150-candidate-l2-iteration-002"
CATALOG_PATH = ITERATION_ROOT / "candidate-iteration.json"
SCENARIO_PATH = ITERATION_ROOT / "scenario-manifest.json"
PROJECTION_PATH = ITERATION_ROOT / "projection-report.json"
ADDITIONS_PATH = (
    ROOT
    / "assets"
    / "fixtures"
    / "variation_candidate_contribution_model"
    / "v150_location_additions.json"
)
REAL_ADDITION_ROOT = (
    ROOT / "docs" / "variation_expansion" / "experiments" / "v150-candidate-shape-iteration-003"
)
REAL_ADDITION_RECEIPT = REAL_ADDITION_ROOT / "handoff-receipt.json"


def _inputs():
    return (
        load_candidate_catalog(CATALOG_PATH),
        json.loads(SCENARIO_PATH.read_text(encoding="utf-8")),
        json.loads(PROJECTION_PATH.read_text(encoding="utf-8")),
    )


def _model():
    catalog, scenario, projection = _inputs()
    return model_candidate_contributions(
        catalog,
        scenario_manifest=scenario,
        projection_report=projection,
    )


def _additions():
    return json.loads(ADDITIONS_PATH.read_text(encoding="utf-8"))


def _plan_additions(additions=None):
    catalog, _, _ = _inputs()
    return plan_location_additions(
        catalog,
        additions or _additions(),
        base_report=_model(),
    )


class TestVariationCandidateContributionModel(unittest.TestCase):
    def test_existing_and_candidate_location_contributions_are_separate(self):
        report = _model()

        self.assertEqual(report["baseline"], {"rows": 5806, "base_variations": 103212})
        self.assertEqual(
            report["contributions"],
            {
                "new_subject_existing_location": {"rows": 589, "base_variations": 10332},
                "existing_subject_new_location": {"rows": 1296},
                "new_subject_new_location": {"rows": 126},
                "all_new_location_rows": {"rows": 1422, "base_variations": 28440},
            },
        )
        self.assertEqual(report["subject_breakdown"]["architect"], {"rows": 30, "base_variations": 520})
        self.assertEqual(
            report["location_breakdown"]["bike_station"],
            {
                "existing_subject_rows": 107,
                "proposed_subject_rows": 8,
                "rows": 115,
                "actions": 20,
                "base_variations": 2300,
            },
        )

    def test_iteration_two_realized_model_misses_v150_target(self):
        report = _model()

        self.assertEqual(
            report["estimated"],
            {
                "rows": 7817,
                "base_variations": 141984,
                "target": 150000,
                "target_gap": 8016,
                "target_met": False,
            },
        )
        self.assertEqual(
            report["projection_comparison"],
            {
                "projected_rows": 7796,
                "projected_base_variations": 155920,
                "row_delta": 21,
                "base_variation_delta": -13936,
            },
        )

    def test_alias_and_canonical_location_sources_count_once(self):
        catalog, scenario, projection = _inputs()
        compatibility = copy.deepcopy(contribution_model.load_scene_compatibility())
        compatibility["loc_tags"]["workplace"] = [
            *compatibility["loc_tags"]["workplace"],
            "neon_city_street",
            "cyberpunk_street",
        ]

        with patch.object(contribution_model, "load_scene_compatibility", return_value=compatibility):
            report = model_candidate_contributions(
                catalog,
                scenario_manifest=scenario,
                projection_report=projection,
            )

        self.assertEqual(report["subject_breakdown"]["architect"], {"rows": 31, "base_variations": 536})

    def test_report_is_canonical_and_deterministic(self):
        first = canonical_json_bytes(_model())
        second = canonical_json_bytes(_model())

        self.assertEqual(first, second)

    def test_model_does_not_mutate_active_sources(self):
        protected = [
            ROOT / "vocab" / "data" / "variation_scope.json",
            ROOT / "vocab" / "data" / "scene_compatibility.json",
            ROOT / "vocab" / "data" / "action_pools.json",
            ROOT / "vocab" / "source" / "action_pools" / "_shared_families.json",
            CATALOG_PATH,
            SCENARIO_PATH,
            PROJECTION_PATH,
        ]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}

        _model()

        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        self.assertEqual(after, before)

    def test_cli_emits_report_and_returns_one_for_target_miss(self):
        completed = subprocess.run(
            [
                sys.executable,
                "tools/model_variation_candidate_contributions.py",
                "--catalog",
                str(CATALOG_PATH),
                "--scenario-file",
                str(SCENARIO_PATH),
                "--projection-report",
                str(PROJECTION_PATH),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "")
        report = json.loads(completed.stdout)
        self.assertEqual(report["estimated"]["base_variations"], 141984)
        self.assertFalse(report["estimated"]["target_met"])


class TestVariationLocationAdditionPlan(unittest.TestCase):
    def test_iteration_three_handoff_receipt_hashes_all_artifacts(self):
        receipt = json.loads(REAL_ADDITION_RECEIPT.read_text(encoding="utf-8"))

        for relative_path, expected in receipt["artifact_hashes"].items():
            with self.subTest(path=relative_path):
                actual = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
                self.assertEqual(actual, expected)

    def test_real_iteration_three_artifacts_are_canonical_and_exact(self):
        catalog, _, _ = _inputs()
        additions = json.loads((REAL_ADDITION_ROOT / "location-additions.json").read_text(encoding="utf-8"))
        expected = json.loads((REAL_ADDITION_ROOT / "location-addition-report.json").read_text(encoding="utf-8"))
        actual = plan_location_additions(catalog, additions, base_report=_model())

        self.assertEqual(canonical_json_bytes(actual), canonical_json_bytes(expected))
        self.assertEqual(actual["added_rows"], 410)
        self.assertEqual(actual["added_base_variations"], 8200)
        self.assertEqual(actual["estimated_total_base_variations"], 150184)

    def test_exact_rows_actions_and_contributions_close_target_gap(self):
        report = _plan_additions()
        additions = {row["id"]: row for row in report["additions"]}

        self.assertEqual(
            additions["community_theater_backstage"],
            {
                "id": "community_theater_backstage",
                "compatibility_tags": ["leisure", "music", "workplace"],
                "action_count": 20,
                "existing_subject_rows": 95,
                "proposed_subject_rows": 11,
                "rows": 106,
                "base_variations": 2120,
                "utility_group": "civic_creative_work",
                "distinct_from": "opera_house",
                "rationale": "Adds rehearsal preparation, prop handling, and scheduling behind a community performance space rather than another audience-facing hall.",
            },
        )
        self.assertEqual(additions["greenhouse_nursery"]["base_variations"], 113 * 20)
        self.assertEqual(additions["postal_service_counter"]["base_variations"], 118 * 20)
        self.assertEqual(additions["vehicle_repair_garage"]["base_variations"], 73 * 20)

    def test_cumulative_plan_reaches_v150_with_bounded_overshoot(self):
        report = _plan_additions()

        self.assertEqual(report["starting_base_variations"], 141984)
        self.assertEqual(report["starting_target_gap"], 8016)
        self.assertEqual(report["added_rows"], 410)
        self.assertEqual(report["added_base_variations"], 8200)
        self.assertEqual(report["estimated_total_base_variations"], 150184)
        self.assertEqual(report["target_gap"], -184)
        self.assertTrue(report["target_met"])

    def test_current_candidate_and_alias_location_collisions_are_rejected(self):
        for location_id in ("street_cafe", "tram_platform", "neon_city_street", "messy_kitchen"):
            with self.subTest(location_id=location_id):
                additions = _additions()
                additions["additions"][0]["id"] = location_id
                with self.assertRaises(WorkflowValidationError) as raised:
                    _plan_additions(additions)
                self.assertEqual(raised.exception.code, "location_addition_collision")

    def test_duplicate_location_addition_ids_are_rejected(self):
        additions = _additions()
        additions["additions"][1]["id"] = additions["additions"][0]["id"]

        with self.assertRaises(WorkflowValidationError) as raised:
            _plan_additions(additions)

        self.assertEqual(raised.exception.code, "duplicate_location_addition_id")

    def test_action_count_must_be_integer_from_one_through_twenty(self):
        for action_count in (0, 21, True):
            with self.subTest(action_count=action_count):
                additions = _additions()
                additions["additions"][0]["action_count"] = action_count
                with self.assertRaises(WorkflowValidationError) as raised:
                    _plan_additions(additions)
                self.assertEqual(raised.exception.code, "invalid_location_addition_action_count")

    def test_unknown_compatibility_tag_is_rejected(self):
        additions = _additions()
        additions["additions"][0]["compatibility_tags"] = ["not_a_known_tag"]

        with self.assertRaises(WorkflowValidationError) as raised:
            _plan_additions(additions)

        self.assertEqual(raised.exception.code, "unknown_location_addition_tag")

    def test_addition_and_tag_order_do_not_change_canonical_report(self):
        additions = _additions()
        reordered = copy.deepcopy(additions)
        reordered["additions"].reverse()
        for row in reordered["additions"]:
            row["compatibility_tags"].reverse()

        self.assertEqual(
            canonical_json_bytes(_plan_additions(additions)),
            canonical_json_bytes(_plan_additions(reordered)),
        )

    def test_location_addition_planning_does_not_mutate_sources(self):
        protected = [
            ROOT / "vocab" / "data" / "variation_scope.json",
            ROOT / "vocab" / "data" / "scene_compatibility.json",
            ROOT / "vocab" / "data" / "action_pools.json",
            CATALOG_PATH,
            ADDITIONS_PATH,
        ]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}

        _plan_additions()

        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        self.assertEqual(after, before)

    def test_cli_location_additions_returns_success_for_target_met_plan(self):
        completed = subprocess.run(
            [
                sys.executable,
                "tools/model_variation_candidate_contributions.py",
                "--catalog",
                str(CATALOG_PATH),
                "--scenario-file",
                str(SCENARIO_PATH),
                "--projection-report",
                str(PROJECTION_PATH),
                "--location-additions",
                str(ADDITIONS_PATH),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        report = json.loads(completed.stdout)
        self.assertEqual(report["estimated_total_base_variations"], 150184)
        self.assertTrue(report["target_met"])


if __name__ == "__main__":
    unittest.main()
