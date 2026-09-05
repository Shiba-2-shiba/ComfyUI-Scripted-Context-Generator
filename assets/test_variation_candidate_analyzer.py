import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from assets.variation_test_fixtures import fixture_environment, fixture_repository
from tools import analyze_variation_candidates as analyzer
from tools import plan_variation_target as planner
from tools.plan_variation_target import build_projection_report, load_projection_manifest
from tools.workflow_prompt_runner import WorkflowValidationError, canonical_json_bytes


ROOT = fixture_repository()
FIXTURE = ROOT / "assets" / "fixtures" / "variation_candidate_analyzer" / "valid_catalog_v1.json"
SCENARIO_FIXTURE = ROOT / "assets" / "fixtures" / "variation_target_planner" / "valid_mixed_v1.json"
SCENARIO_MANIFEST = load_projection_manifest(SCENARIO_FIXTURE)
with fixture_environment(ROOT):
    PROJECTION_REPORT = build_projection_report(SCENARIO_MANIFEST, target=150000)
REAL_ITERATION_ROOT = (
    ROOT / "docs" / "variation_expansion" / "experiments" / "v150-candidate-l2-iteration-002"
)
COMPOSED_FIXTURE = (
    ROOT / "assets" / "fixtures" / "variation_candidate_analyzer" / "composed_iteration_v2.json"
)
LOCATION_ADDITIONS_FIXTURE = (
    ROOT / "assets" / "fixtures" / "variation_candidate_analyzer" / "location_additions_v1.json"
)


def _catalog():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _load_temporary_composition(additions, *, mutate_manifest=None):
    with tempfile.TemporaryDirectory(prefix="candidate-composition-", dir=ROOT / "assets" / "results") as temp_dir:
        temp_root = Path(temp_dir)
        additions_path = temp_root / "location-additions.json"
        additions_path.write_text(json.dumps(additions), encoding="utf-8")
        manifest = json.loads(COMPOSED_FIXTURE.read_text(encoding="utf-8"))
        manifest["location_additions_path"] = additions_path.relative_to(ROOT).as_posix()
        manifest["location_additions_sha256"] = hashlib.sha256(additions_path.read_bytes()).hexdigest()
        if mutate_manifest is not None:
            mutate_manifest(manifest)
        manifest_path = temp_root / "candidate-iteration.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return analyzer.load_candidate_catalog(manifest_path)


def _error_codes(catalog):
    return [
        error["code"]
        for error in analyzer.validate_candidate_catalog(
            catalog,
            scenario_manifest=SCENARIO_MANIFEST,
            projection_report=PROJECTION_REPORT,
        )
    ]


def _analyze(catalog):
    return analyzer.analyze_candidate_catalog(
        catalog,
        scenario_manifest=SCENARIO_MANIFEST,
        projection_report=PROJECTION_REPORT,
    )


class TestVariationCandidateAnalyzer(unittest.TestCase):
    def test_explicit_baseline_manifest_is_used_by_candidate_analysis(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline_path = Path(temp_dir) / "baseline.json"
            baseline_path.write_bytes(planner.L0_BASELINE_MANIFEST_PATH.read_bytes())
            with patch.object(planner, "L0_BASELINE_MANIFEST_PATH", Path(temp_dir) / "missing.json"):
                report = analyzer.analyze_candidate_catalog(
                    _catalog(), scenario_manifest=SCENARIO_MANIFEST,
                    projection_report=PROJECTION_REPORT, baseline_manifest_path=baseline_path,
                )
                self.assertEqual(report["structural_status"], "pass")
                baseline_path.write_bytes(baseline_path.read_bytes() + b"\n")
                rejected = analyzer.analyze_candidate_catalog(
                    _catalog(), scenario_manifest=SCENARIO_MANIFEST,
                    projection_report=PROJECTION_REPORT, baseline_manifest_path=baseline_path,
                )
                self.assertEqual(rejected["structural_status"], "fail")
                self.assertIn("baseline_manifest_hash_mismatch", [error["code"] for error in rejected["errors"]])

    def test_hash_bound_iteration_catalog_materializes_action_overrides(self):
        catalog = analyzer.load_candidate_catalog(REAL_ITERATION_ROOT / "candidate-iteration.json")

        self.assertEqual(catalog["schema_version"], "variation-quality-candidate-catalog/v1")
        self.assertEqual(catalog["catalog_id"], "v150-candidate-002")
        self.assertEqual(len(catalog["subjects"]), 15)
        self.assertEqual(len(catalog["locations"]), 15)
        for location in catalog["locations"]:
            self.assertEqual(
                len(location["action_plan"]["direct_actions"])
                + sum(ref["take"] for ref in location["action_plan"]["family_refs"]),
                20,
            )

    def test_iteration_catalog_rejects_bound_artifact_hash_drift(self):
        iteration = json.loads(
            (REAL_ITERATION_ROOT / "candidate-iteration.json").read_text(encoding="utf-8")
        )
        iteration["action_overrides_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "iteration.json"
            path.write_text(json.dumps(iteration), encoding="utf-8")
            with self.assertRaises(analyzer.WorkflowValidationError) as raised:
                analyzer.load_candidate_catalog(path)

        self.assertEqual(raised.exception.code, "action_overrides_hash_mismatch")

    def test_real_iteration_two_passes_structure_but_not_prompt_quality(self):
        catalog = analyzer.load_candidate_catalog(REAL_ITERATION_ROOT / "candidate-iteration.json")
        scenario = json.loads((REAL_ITERATION_ROOT / "scenario-manifest.json").read_text(encoding="utf-8"))
        projection = json.loads((REAL_ITERATION_ROOT / "projection-report.json").read_text(encoding="utf-8"))

        report = analyzer.analyze_candidate_catalog(
            catalog,
            scenario_manifest=scenario,
            projection_report=projection,
        )

        self.assertEqual(report["structural_status"], "pass")
        self.assertTrue(report["eligible_for_prompt_evaluation"])
        self.assertFalse(report["promotion_ready"])
        self.assertEqual(report["prompt_quality"]["status"], "not_evaluated")
        self.assertEqual(report["compatibility_coverage"]["coverage_margin"], 21)
        self.assertEqual(report["duplicate_pressure"]["candidate_duplicate_occurrences"], 0)


class TestVariationCandidateCatalogComposition(unittest.TestCase):
    def test_recursive_composition_has_exact_subject_location_and_action_depth(self):
        catalog = analyzer.load_candidate_catalog(COMPOSED_FIXTURE)
        added_ids = {
            "community_theater_backstage",
            "greenhouse_nursery",
            "postal_service_counter",
            "vehicle_repair_garage",
        }

        self.assertEqual(catalog["catalog_id"], "v150-candidate-004-test")
        self.assertEqual(len(catalog["subjects"]), 15)
        self.assertEqual(len(catalog["locations"]), 19)
        self.assertEqual(added_ids, {row["id"] for row in catalog["locations"]} - {
            row["id"] for row in analyzer.load_candidate_catalog(
                REAL_ITERATION_ROOT / "candidate-iteration.json"
            )["locations"]
        })
        for location in catalog["locations"]:
            with self.subTest(location=location["id"]):
                depth = len(location["action_plan"]["direct_actions"]) + sum(
                    int(ref["take"]) for ref in location["action_plan"]["family_refs"]
                )
                self.assertEqual(depth, 20)

    def test_composed_catalog_is_deterministic_across_repeated_loads(self):
        first = analyzer.load_candidate_catalog(COMPOSED_FIXTURE)
        second = analyzer.load_candidate_catalog(COMPOSED_FIXTURE)

        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))

    def test_addition_order_does_not_change_composed_catalog(self):
        additions = json.loads(LOCATION_ADDITIONS_FIXTURE.read_text(encoding="utf-8"))
        reversed_additions = copy.deepcopy(additions)
        reversed_additions["locations"].reverse()

        first = _load_temporary_composition(additions)
        second = _load_temporary_composition(reversed_additions)

        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))

    def test_bound_base_and_addition_hash_drift_are_rejected(self):
        manifest = json.loads(COMPOSED_FIXTURE.read_text(encoding="utf-8"))
        cases = (
            ("base_catalog_sha256", "base_catalog_hash_mismatch"),
            ("location_additions_sha256", "location_additions_hash_mismatch"),
        )
        for field, expected in cases:
            with self.subTest(field=field):
                drifted = copy.deepcopy(manifest)
                drifted[field] = "0" * 64
                with tempfile.TemporaryDirectory(
                    prefix="candidate-composition-drift-", dir=ROOT / "assets" / "results"
                ) as temp_dir:
                    path = Path(temp_dir) / "candidate-iteration.json"
                    path.write_text(json.dumps(drifted), encoding="utf-8")
                    with self.assertRaises(WorkflowValidationError) as raised:
                        analyzer.load_candidate_catalog(path)
                self.assertEqual(raised.exception.code, expected)

    def test_composed_catalog_rejects_path_escape(self):
        manifest = json.loads(COMPOSED_FIXTURE.read_text(encoding="utf-8"))
        manifest["location_additions_path"] = "../outside.json"
        with tempfile.TemporaryDirectory(
            prefix="candidate-composition-path-", dir=ROOT / "assets" / "results"
        ) as temp_dir:
            path = Path(temp_dir) / "candidate-iteration.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(WorkflowValidationError) as raised:
                analyzer.load_candidate_catalog(path)

        self.assertEqual(raised.exception.code, "invalid_location_additions_path")

    def test_composed_catalog_rejects_base_collision_and_duplicate_additions(self):
        original = json.loads(LOCATION_ADDITIONS_FIXTURE.read_text(encoding="utf-8"))
        collision = copy.deepcopy(original)
        collision["locations"][0]["id"] = "tram_platform"
        duplicate = copy.deepcopy(original)
        duplicate["locations"][1]["id"] = duplicate["locations"][0]["id"]

        for additions in (collision, duplicate):
            with self.subTest(ids=[row["id"] for row in additions["locations"]]):
                with self.assertRaises(WorkflowValidationError) as raised:
                    _load_temporary_composition(additions)
                self.assertEqual(raised.exception.code, "location_addition_id_collision")

    def test_composition_does_not_mutate_bound_artifacts(self):
        protected = [
            COMPOSED_FIXTURE,
            LOCATION_ADDITIONS_FIXTURE,
            REAL_ITERATION_ROOT / "candidate-iteration.json",
            ROOT / "vocab" / "data" / "variation_scope.json",
        ]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}

        analyzer.load_candidate_catalog(COMPOSED_FIXTURE)

        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        self.assertEqual(after, before)

    def test_load_candidate_catalog_reads_valid_fixture(self):
        loaded = analyzer.load_candidate_catalog(FIXTURE)

        self.assertEqual(loaded, _catalog())

    def test_valid_catalog_passes_structure_but_cannot_promote_before_prompt_review(self):
        catalog = _catalog()

        self.assertEqual(_error_codes(catalog), [])
        report = _analyze(catalog)

        self.assertEqual(report["structural_status"], "pass")
        self.assertTrue(report["eligible_for_prompt_evaluation"])
        self.assertFalse(report["promotion_ready"])
        self.assertEqual(
            report["prompt_quality"],
            {"status": "not_evaluated", "receipt_sha256": None},
        )
        self.assertEqual(report["scenario_binding"]["scenario_id"], "balanced-growth-001")
        self.assertEqual(report["errors"], [])
        for key in (
            "identity_analysis",
            "utility_analysis",
            "compatibility_coverage",
            "action_family_analysis",
            "duplicate_pressure",
            "policy_findings",
        ):
            self.assertIn(key, report)

    def test_scenario_id_and_exact_proposal_ids_are_bound_to_l1_projection(self):
        wrong_scenario = _catalog()
        wrong_scenario["scenario_binding"]["scenario_id"] = "tie-break-001"
        wrong_subject = _catalog()
        wrong_subject["subjects"][0]["id"] = "replacement-subject"
        wrong_location = _catalog()
        wrong_location["locations"][0]["id"] = "replacement-location"

        for catalog in (wrong_scenario, wrong_subject, wrong_location):
            with self.subTest(catalog=catalog["scenario_binding"]["scenario_id"]):
                self.assertIn("proposal_id_mismatch", _error_codes(catalog))

    def test_subject_scope_collision_is_rejected(self):
        catalog = _catalog()
        catalog["subjects"][0]["id"] = "student"

        self.assertIn("subject_scope_collision", _error_codes(catalog))

    def test_location_scope_alias_and_non_counted_collisions_are_rejected(self):
        for location in ("street_cafe", "neon_city_street", "steampunk_airship", "messy_kitchen"):
            with self.subTest(location=location):
                catalog = _catalog()
                catalog["locations"][0]["id"] = location
                self.assertIn("location_canonical_collision", _error_codes(catalog))

    def test_case_and_format_variants_cannot_evade_scope_collisions(self):
        subject = _catalog()
        subject["subjects"][0]["id"] = "Student"
        location = _catalog()
        location["locations"][0]["id"] = "Street_Cafe"

        self.assertIn("invalid_candidate_id_format", _error_codes(subject))
        self.assertIn("subject_scope_collision", _error_codes(subject))
        self.assertIn("invalid_candidate_id_format", _error_codes(location))
        for subject_variant in ("office_worker", "office-worker"):
            with self.subTest(subject_variant=subject_variant):
                catalog = _catalog()
                catalog["subjects"][0]["id"] = subject_variant
                self.assertIn("subject_scope_collision", _error_codes(catalog))

    def test_unknown_compatibility_tag_is_rejected(self):
        catalog = _catalog()
        catalog["locations"][0]["compatibility_tags"] = ["not-a-real-tag"]

        self.assertIn("unknown_compatibility_tag", _error_codes(catalog))

    def test_utility_claim_requires_visible_distinction_and_known_reference(self):
        invalid_claim = _catalog()
        invalid_claim["subjects"][0]["utility_claim"]["prompt_visible_terms"] = None
        unknown_reference = _catalog()
        unknown_reference["locations"][0]["utility_claim"]["distinct_from"] = ["unknown-place"]

        self.assertIn("invalid_utility_claim", _error_codes(invalid_claim))
        self.assertIn("unknown_distinct_from", _error_codes(unknown_reference))

    def test_shared_action_family_must_exist_and_slice_must_be_in_range(self):
        missing = _catalog()
        missing["locations"][0]["action_plan"]["family_refs"][0]["name"] = "missing-family"
        invalid_slice = _catalog()
        invalid_slice["locations"][0]["action_plan"]["family_refs"][0]["offset"] = -1

        self.assertIn("missing_action_family", _error_codes(missing))
        self.assertIn("invalid_action_family_slice", _error_codes(invalid_slice))

    def test_action_family_ref_schema_is_closed(self):
        catalog = _catalog()
        catalog["locations"][0]["action_plan"]["family_refs"][0]["unexpected"] = True

        self.assertIn("unknown_catalog_field", _error_codes(catalog))

    def test_policy_banned_candidate_term_is_rejected(self):
        catalog = _catalog()
        catalog["locations"][0]["action_plan"]["direct_actions"][0]["text"] = (
            "checking a masterpiece route board"
        )

        self.assertIn("banned_candidate_term", _error_codes(catalog))

    def test_exact_duplicate_candidate_actions_are_rejected(self):
        catalog = _catalog()
        catalog["locations"][0]["action_plan"]["direct_actions"][0] = {
            "text": "standing and checking what needs attention next",
            "load": "calm",
        }

        self.assertIn("duplicate_candidate_action", _error_codes(catalog))

    def test_shared_family_reuse_pressure_above_catalog_limit_is_rejected(self):
        catalog = _catalog()
        catalog["quality_limits"]["max_shared_family_location_reuse"] = 5
        for location in catalog["locations"]:
            location["action_plan"]["family_refs"] = [
                {"name": "public_navigation", "offset": 0, "take": 1}
            ]

        self.assertIn("action_family_reuse_exceeded", _error_codes(catalog))

    def test_total_duplicate_pressure_includes_shared_family_reuse(self):
        catalog = _catalog()
        catalog["quality_limits"]["max_exact_duplicate_pressure_basis_points"] = 100

        self.assertIn("duplicate_pressure_exceeded", _error_codes(catalog))

    def test_non_null_prompt_quality_receipt_is_rejected_in_l2(self):
        catalog = _catalog()
        catalog["prompt_quality_receipt"] = "docs/prompt_quality/fabricated.json"

        report = _analyze(catalog)
        self.assertIn("prompt_quality_receipt_not_supported_in_l2", [item["code"] for item in report["errors"]])
        self.assertEqual(report["prompt_quality"]["status"], "not_evaluated")
        self.assertFalse(report["promotion_ready"])

    def test_universal_requires_a_real_json_boolean(self):
        catalog = _catalog()
        catalog["locations"][0]["universal"] = "false"

        self.assertIn("invalid_universal_flag", _error_codes(catalog))

    def test_analysis_is_canonical_and_byte_deterministic(self):
        catalog = _catalog()

        first = canonical_json_bytes(_analyze(copy.deepcopy(catalog)))
        second = canonical_json_bytes(_analyze(copy.deepcopy(catalog)))

        self.assertEqual(first, second)
        self.assertEqual(
            hashlib.sha256(first).hexdigest(),
            hashlib.sha256(second).hexdigest(),
        )

    def test_invalid_analysis_does_not_mutate_repository_sources(self):
        protected = [
            ROOT / "vocab" / "data" / "variation_scope.json",
            ROOT / "vocab" / "data" / "scene_compatibility.json",
            ROOT / "vocab" / "data" / "prompt_quality_policy.json",
            ROOT / "vocab" / "source" / "action_pools" / "_shared_families.json",
            ROOT / "assets" / "fixtures" / "variation_target_planner" / "valid_mixed_v1.json",
        ]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        catalog = _catalog()
        catalog["locations"][0]["compatibility_tags"] = ["not-a-real-tag"]

        report = _analyze(catalog)

        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        self.assertEqual(after, before)
        self.assertEqual(report["structural_status"], "fail")
        self.assertFalse(report["eligible_for_prompt_evaluation"])
        self.assertFalse(report["promotion_ready"])


def setUpModule():
    global _fixture_context
    _fixture_context = fixture_environment(ROOT)
    _fixture_context.__enter__()


def tearDownModule():
    _fixture_context.__exit__(None, None, None)


if __name__ == "__main__":
    unittest.main()
