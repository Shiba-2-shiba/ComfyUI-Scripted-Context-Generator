import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import plan_variation_target as planner
from tools.plan_variation_target import (
    action_backed_compatible_locations,
    build_target_report,
    location_candidate_deltas,
    scenario_metrics,
    subject_candidate_deltas,
)
from tools.check_variation_scope import load_variation_scope
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "assets" / "fixtures" / "variation_target_planner"
LOCKED_BASELINE_MANIFEST = (
    ROOT / "docs" / "variation_expansion" / "experiments" / "v150-planner-l0" / "manifest.json"
)
LOCKED_BASELINE_SHA256 = "7bb90af6b124b724c484034fddbe1dad05006fc897947ce359d6f5a769acae54"
BASELINE = {
    "unique_subjects": 120,
    "unique_locations": 90,
    "row_count": 5806,
    "total_base_variations": 103212,
}


def _valid_manifest():
    return json.loads((FIXTURE_ROOT / "valid_mixed_v1.json").read_text(encoding="utf-8"))


def _build_projection(manifest=None, *, target=150000):
    return planner.build_projection_report(
        manifest or _valid_manifest(),
        target=target,
        baseline=BASELINE,
    )


def _scenario(report, scenario_id):
    return {row["id"]: row for row in report["hypothetical_scenarios"]}[scenario_id]


def _error_code(manifest):
    with unittest.TestCase().assertRaises(WorkflowValidationError) as raised:
        _build_projection(manifest)
    code = raised.exception.code
    if not isinstance(code, str) or not code:
        raise AssertionError("projection validation must expose a stable non-empty error code")
    return code


class TestVariationTargetPlanner(unittest.TestCase):
    def test_current_scope_matches_base_variation_baseline(self):
        scope = load_variation_scope()
        metrics = scenario_metrics(scope["variation_subjects"], scope["variation_locations"], scope=scope)

        self.assertEqual(metrics["unique_subjects"], 120)
        self.assertEqual(metrics["unique_locations"], 90)
        self.assertEqual(metrics["row_count"], 5806)
        self.assertEqual(metrics["total_base_variations"], 103212)
        self.assertEqual(metrics["missing_pools_count"], 0)

    def test_planning_scenarios_match_current_restricted_surface(self):
        report = build_target_report(target=100000)
        scenarios = {row["name"]: row for row in report["scenarios"]}

        self.assertEqual(scenarios["all_known_subjects_current_locations"]["total_base_variations"], 103212)
        self.assertEqual(
            scenarios["current_subjects_all_action_backed_compatible_locations"]["total_base_variations"],
            103212,
        )
        self.assertEqual(
            scenarios["all_known_subjects_all_action_backed_compatible_locations"]["total_base_variations"],
            103212,
        )

        action_scenarios = {row["minimum_actions"]: row for row in report["minimum_action_scenarios"]}
        self.assertEqual(action_scenarios[12]["total_base_variations"], 103212)
        self.assertEqual(action_scenarios[16]["total_base_variations"], 105260)
        self.assertEqual(action_scenarios[20]["total_base_variations"], 116120)
        self.assertEqual(report["first_minimum_action_target_met"]["minimum_actions"], 12)

    def test_candidate_deltas_are_empty_after_p11_action_refactor(self):
        self.assertEqual(subject_candidate_deltas(limit=5), [])
        self.assertEqual(location_candidate_deltas(), [])

    def test_action_backed_location_pool_matches_current_scope(self):
        locations = action_backed_compatible_locations()

        self.assertEqual(len(locations), 90)
        self.assertIn("local_market_street", locations)
        self.assertIn("train_station_platform", locations)


class TestVariationTargetProjection(unittest.TestCase):
    def test_cli_scenario_file_adds_projection_without_replacing_legacy_report(self):
        protected = [
            ROOT / "vocab" / "data" / "variation_scope.json",
            ROOT / "vocab" / "data" / "scene_compatibility.json",
            ROOT / "vocab" / "data" / "action_pools.json",
            ROOT / "assets" / "compatibility_review.csv",
        ]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "plan_variation_target.py"),
                "--target",
                "150000",
                "--scenario-file",
                str(FIXTURE_ROOT / "valid_mixed_v1.json"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["current_metrics"]["total_base_variations"], 103212)
        self.assertEqual(payload["projection"]["stage_id"], "V150")
        self.assertEqual(
            _scenario(payload["projection"], "balanced-growth-001")["projected_base_variations"],
            138120,
        )
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        self.assertEqual(after, before)

    def test_cli_invalid_scenario_file_returns_stable_error_envelope(self):
        manifest = _valid_manifest()
        manifest["scenarios"][0]["compatibility_density_basis_points"] = 0
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "invalid.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "plan_variation_target.py"),
                    "--target",
                    "150000",
                    "--scenario-file",
                    str(path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 2)
        envelope = json.loads(completed.stderr)
        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["error"]["code"], "invalid_compatibility_density")

    def test_cli_rejects_non_positive_legacy_inputs(self):
        cases = [
            (["--target", "0"], "invalid_target"),
            (["--minimum-actions=-1"], "invalid_minimum_action"),
            (["--minimum-actions="], "missing_minimum_actions"),
        ]
        for arguments, expected_code in cases:
            with self.subTest(arguments=arguments):
                completed = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "plan_variation_target.py"), *arguments],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(json.loads(completed.stderr)["error"]["code"], expected_code)

    def test_default_report_remains_byte_equivalent_to_locked_baseline(self):
        report = build_target_report(target=500000)
        locked = json.loads(
            (
                ROOT
                / "docs"
                / "variation_expansion"
                / "experiments"
                / "v150-planner-l0"
                / "baseline-report.json"
            ).read_text(encoding="utf-8")
        )
        expected = {
            key: value
            for key, value in locked.items()
            if key not in {"schema_version", "captured_at", "command", "conclusion"}
        }

        self.assertEqual(canonical_json_bytes(report), canonical_json_bytes(expected))
        self.assertEqual(report["current_metrics"]["unique_subjects"], 120)
        self.assertEqual(report["current_metrics"]["unique_locations"], 90)
        self.assertEqual(report["current_metrics"]["row_count"], 5806)
        self.assertEqual(report["current_metrics"]["total_base_variations"], 103212)
        self.assertNotIn("projection", report)
        self.assertNotIn("hypothetical_scenarios", report)

    def test_locked_baseline_hash_used_by_fixture_is_current(self):
        actual = hashlib.sha256(LOCKED_BASELINE_MANIFEST.read_bytes()).hexdigest()

        self.assertEqual(actual, LOCKED_BASELINE_SHA256)
        self.assertEqual(_valid_manifest()["baseline_manifest_sha256"].lower(), actual)

    def test_valid_mixed_scenario_has_exact_rows_and_contributions(self):
        result = _scenario(_build_projection(), "balanced-growth-001")

        self.assertEqual(result["eligible_pairs"], 14175)
        self.assertEqual(result["projected_rows"], 7938)
        self.assertEqual(result["realized_density_basis_points"], 5600)
        self.assertEqual(
            result["action_depth_allocation"],
            [
                {"actions": 12, "row_share_basis_points": 1500, "rows": 1191, "base_variations": 14292},
                {"actions": 16, "row_share_basis_points": 4500, "rows": 3572, "base_variations": 57152},
                {"actions": 20, "row_share_basis_points": 3000, "rows": 2381, "base_variations": 47620},
                {"actions": 24, "row_share_basis_points": 1000, "rows": 794, "base_variations": 19056},
            ],
        )
        self.assertEqual(result["projected_base_variations"], 138120)
        self.assertEqual(result["delta_base_variations"], 34908)
        self.assertEqual(result["target_gap"], 11880)
        self.assertFalse(result["target_met"])

    def test_largest_remainder_tie_uses_ascending_action_depth(self):
        result = _scenario(_build_projection(), "tie-break-001")

        self.assertEqual(result["projected_rows"], 1)
        self.assertEqual(
            result["action_depth_allocation"],
            [
                {"actions": 12, "row_share_basis_points": 5000, "rows": 1, "base_variations": 12},
                {"actions": 20, "row_share_basis_points": 5000, "rows": 0, "base_variations": 0},
            ],
        )
        self.assertEqual(result["projected_base_variations"], 12)

    def test_manifest_key_bucket_and_scenario_order_do_not_change_output(self):
        manifest = _valid_manifest()
        reordered = {
            "scenarios": list(reversed(copy.deepcopy(manifest["scenarios"]))),
            "baseline_manifest_sha256": manifest["baseline_manifest_sha256"],
            "stage_id": manifest["stage_id"],
            "schema_version": manifest["schema_version"],
        }
        for scenario in reordered["scenarios"]:
            scenario["action_depth_row_distribution"].reverse()

        self.assertEqual(canonical_json_bytes(_build_projection(manifest)), canonical_json_bytes(_build_projection(reordered)))

    def test_repeated_runs_are_canonical_byte_equivalent(self):
        manifest = _valid_manifest()

        first = canonical_json_bytes(_build_projection(copy.deepcopy(manifest)))
        second = canonical_json_bytes(_build_projection(copy.deepcopy(manifest)))

        self.assertEqual(first, second)

    def test_numeric_and_duplicate_validation_fail_closed_with_stable_codes(self):
        cases = [
            (
                "invalid_action_share_total",
                lambda value: value["scenarios"][0]["action_depth_row_distribution"][0].update(
                    row_share_basis_points=1499
                ),
            ),
            (
                "invalid_compatibility_density",
                lambda value: value["scenarios"][0].update(compatibility_density_basis_points=0),
            ),
            (
                "invalid_compatibility_density",
                lambda value: value["scenarios"][0].update(compatibility_density_basis_points=10001),
            ),
            (
                "duplicate_scenario_id",
                lambda value: value["scenarios"][1].update(id=value["scenarios"][0]["id"]),
            ),
            (
                "duplicate_action_depth",
                lambda value: value["scenarios"][0]["action_depth_row_distribution"][1].update(actions=12),
            ),
            (
                "duplicate_utility_group",
                lambda value: value["scenarios"][0].update(
                    subject_utility_groups=["daily-adult-v1", "daily-adult-v1"]
                ),
            ),
            (
                "duplicate_utility_group",
                lambda value: value["scenarios"][0].update(
                    location_utility_groups=["daily-work-v1", "daily-work-v1"]
                ),
            ),
            ("projection_below_baseline", lambda value: value["scenarios"][0].update(subject_count=119)),
            ("projection_below_baseline", lambda value: value["scenarios"][0].update(location_count=89)),
            ("unknown_projection_field", lambda value: value["scenarios"][0].update(projected_rows=999999)),
        ]
        for expected_code, mutate in cases:
            with self.subTest(expected_code=expected_code):
                manifest = _valid_manifest()
                mutate(manifest)
                first = _error_code(manifest)
                second = _error_code(copy.deepcopy(manifest))
                self.assertEqual(first, expected_code)
                self.assertEqual(first, second)

    def test_scenario_validation_returns_no_errors_for_valid_input(self):
        scenario = _valid_manifest()["scenarios"][0]

        self.assertEqual(planner.validate_projection_scenario(scenario, BASELINE), [])

    def test_baseline_hash_drift_fails_closed(self):
        manifest = _valid_manifest()
        manifest["baseline_manifest_sha256"] = "0" * 64

        self.assertEqual(_error_code(manifest), "baseline_manifest_hash_mismatch")

    def test_untrusted_future_stage_and_stage_target_mismatch_fail_closed(self):
        future = _valid_manifest()
        future["stage_id"] = "V250"
        future["baseline_manifest_sha256"] = "0" * 64
        self.assertEqual(_error_code(future), "unsupported_projection_stage")

        with self.assertRaises(WorkflowValidationError) as raised:
            _build_projection(_valid_manifest(), target=250000)
        self.assertEqual(raised.exception.code, "projection_stage_target_mismatch")

    def test_location_growth_requires_complete_explicit_proposal_ids(self):
        manifest = _valid_manifest()
        manifest["scenarios"][0]["proposed_location_ids"] = []

        self.assertEqual(_error_code(manifest), "proposed_location_count_mismatch")

    def test_non_countable_location_pools_fail_closed(self):
        for location in ("neon_city_street", "steampunk_airship", "messy_kitchen"):
            with self.subTest(location=location):
                manifest = _valid_manifest()
                manifest["scenarios"][0]["proposed_location_ids"][0] = location
                self.assertEqual(_error_code(manifest), "non_countable_location_pool")

    def test_invalid_projection_does_not_mutate_repository_inputs(self):
        protected = [
            ROOT / "vocab" / "data" / "variation_scope.json",
            ROOT / "vocab" / "data" / "scene_compatibility.json",
            ROOT / "vocab" / "data" / "action_pools.json",
            ROOT / "assets" / "compatibility_review.csv",
        ]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        manifest = _valid_manifest()
        manifest["scenarios"][0]["compatibility_density_basis_points"] = 0

        _error_code(manifest)

        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        self.assertEqual(after, before)

    def test_locked_input_hash_validator_detects_same_shape_content_drift(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            path = root / "protected.json"
            path.write_text('{"value":1}', encoding="utf-8")
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest = {"input_hashes": {"protected.json": expected}}

            planner.validate_locked_input_hashes(
                manifest,
                root=root,
                protected_paths=("protected.json",),
            )
            path.write_text('{"value":2}', encoding="utf-8")
            with self.assertRaises(WorkflowValidationError) as raised:
                planner.validate_locked_input_hashes(
                    manifest,
                    root=root,
                    protected_paths=("protected.json",),
                )

        self.assertEqual(raised.exception.code, "baseline_input_hash_mismatch")

    def test_cli_scenario_file_emits_current_report_and_valid_projection(self):
        completed = subprocess.run(
            [
                sys.executable,
                "tools/plan_variation_target.py",
                "--target",
                "150000",
                "--scenario-file",
                str(FIXTURE_ROOT / "valid_mixed_v1.json"),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        report = json.loads(completed.stdout)
        self.assertEqual(report["current_metrics"]["total_base_variations"], 103212)
        self.assertEqual(
            _scenario(report["projection"], "balanced-growth-001")["projected_base_variations"],
            138120,
        )

    def test_cli_invalid_scenario_file_returns_stable_nonzero_error(self):
        manifest = _valid_manifest()
        manifest["scenarios"][0]["compatibility_density_basis_points"] = 0
        with tempfile.TemporaryDirectory() as temp_dir:
            scenario_path = Path(temp_dir) / "invalid-scenario.json"
            scenario_path.write_text(json.dumps(manifest), encoding="utf-8")
            command = [
                sys.executable,
                "tools/plan_variation_target.py",
                "--target",
                "150000",
                "--scenario-file",
                str(scenario_path),
            ]
            first = subprocess.run(
                command,
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            second = subprocess.run(
                command,
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        self.assertEqual(first.returncode, 2)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(first.stdout, "")
        self.assertEqual(second.stdout, "")
        self.assertEqual(first.stderr, second.stderr)
        self.assertEqual(json.loads(first.stderr)["error"]["code"], "invalid_compatibility_density")


if __name__ == "__main__":
    unittest.main()
