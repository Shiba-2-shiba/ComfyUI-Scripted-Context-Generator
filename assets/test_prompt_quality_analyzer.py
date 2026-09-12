import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.analyze_prompt_quality import analyze_records, load_policy, write_analysis
from tools.workflow_prompt_runner import canonical_json_bytes


FIXTURE = ROOT / "assets" / "fixtures" / "prompt_quality" / "analyzer_precision_cases.json"
POLICY_PATH = ROOT / "vocab" / "data" / "prompt_quality_policy.json"


def deep_update(target, patch):
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_update(target[key], value)
        else:
            target[key] = copy.deepcopy(value)
    return target


def record(seed, prompt):
    context = {
        "subj": "1girl",
        "loc": "sunlit garden",
        "action": "walking while holding a book",
        "costume": "blue day dress",
        "extras": {"character_id": "fixture-girl", "object_focus": "book"},
        "meta": {"mood": "calm"},
        "warnings": [],
    }
    return {
        "run_seed": seed,
        "cohort": "control",
        "raw_prompt": prompt,
        "cleaned_prompt": prompt,
        "final_context": context,
        "execution_trace": [
            {"node_type": "ContextPromptBuilder"},
            {"node_type": "PromptCleaner"},
        ],
        "resolved_seeds": {"8:seed": seed},
        "base_workflow_hash": "a" * 64,
        "effective_workflow_hash": "b" * 64,
    }


class TestPromptQualityAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.policy = load_policy(POLICY_PATH)

    def analyze_case(self, case):
        item = record(101, case["prompt"])
        deep_update(item["final_context"], case.get("context_patch", {}))
        deep_update(item, case.get("record_patch", {}))
        return analyze_records([item], self.policy)

    def test_versioned_precision_cases_detect_and_do_not_detect_expected_issues(self):
        self.assertEqual(self.fixture["schema_version"], "prompt-quality-analyzer-precision/v1")
        for case in self.fixture["cases"]:
            with self.subTest(case=case["id"]):
                analysis = self.analyze_case(case)
                codes = {issue["issue_code"] for issue in analysis["issues"]["issues"]}
                self.assertTrue(set(case.get("expected_present", [])).issubset(codes), codes)
                self.assertTrue(set(case.get("expected_absent", [])).isdisjoint(codes), codes)

    def test_every_issue_has_seed_trace_owner_and_actionable_evidence(self):
        records = []
        for seed, case in enumerate(self.fixture["cases"], 1):
            item = record(seed, case["prompt"])
            deep_update(item["final_context"], case.get("context_patch", {}))
            deep_update(item, case.get("record_patch", {}))
            records.append(item)
        issues = analyze_records(records, self.policy)["issues"]["issues"]

        self.assertTrue(issues)
        required = {
            "issue_code", "severity", "frequency", "confidence", "affected_seeds",
            "trace_nodes", "suspected_owners", "evidence", "recommended_test_surface",
        }
        for issue in issues:
            with self.subTest(issue=issue["issue_code"]):
                self.assertEqual(set(issue), required)
                self.assertTrue(issue["affected_seeds"])
                self.assertTrue(issue["trace_nodes"])
                self.assertTrue(issue["suspected_owners"])
                self.assertTrue(issue["evidence"])
                self.assertTrue(issue["recommended_test_surface"])

    def test_exact_and_normalized_duplicates_have_distinct_detection(self):
        exact = "A girl walks quietly through the garden while holding a book and watching the river from the path."
        normalized_variant = "A GIRL walks quietly through the garden while holding a book—and watching the river from the path!"
        analysis = analyze_records([record(1, exact), record(2, exact), record(3, normalized_variant)], self.policy)
        by_code = {issue["issue_code"]: issue for issue in analysis["issues"]["issues"]}

        self.assertEqual(by_code["exact_duplicate_prompt"]["affected_seeds"], [1, 2])
        self.assertEqual(by_code["normalized_duplicate_prompt"]["affected_seeds"], [1, 2, 3])

    def test_control_secondary_person_phrases_share_solo_safety_detection_and_seed_accounting(self):
        cases = [
            case for case in self.fixture["cases"]
            if case["id"].startswith("control_secondary_")
        ]
        self.assertEqual(len(cases), 7)
        seeds = list(range(700, 707))
        analysis = analyze_records(
            [record(seed, case["prompt"]) for seed, case in zip(seeds, cases)],
            self.policy,
        )
        issue = next(
            item for item in analysis["issues"]["issues"]
            if item["issue_code"] == "other_person_solo_conflict"
        )

        self.assertEqual(issue["affected_seeds"], seeds)
        self.assertEqual(issue["frequency"], 1.0)
        self.assertEqual(
            analysis["metrics"]["identity"]["other_person_solo_conflict_count"],
            7,
        )
        self.assertEqual(
            analysis["metrics"]["identity"]["other_person_solo_conflict_rate"],
            1.0,
        )

    def test_metrics_cover_identity_naturalness_diversity_and_runtime_boundaries(self):
        first = record(1, "A girl watches the river from a quiet garden while holding a book beside the old stone path.")
        second = record(2, "A girl studies drifting clouds from a library window while resting her hands beside an open notebook.")
        second["final_context"].update({"loc": "library", "action": "studying clouds"})
        second["final_context"]["extras"].update({"character_id": "fixture-girl-2", "object_focus": "notebook"})
        first["context_json_bytes"] = 100
        second["context_json_bytes"] = 200
        analysis = analyze_records([first, second], self.policy)
        metrics = analysis["metrics"]

        self.assertEqual(metrics["record_count"], 2)
        self.assertEqual(metrics["runtime"]["context_json_bytes_max"], 200)
        self.assertEqual(metrics["runtime"]["context_json_bytes_p50"], 150)
        self.assertEqual(metrics["diversity"]["location_signature_coverage"], 1.0)
        self.assertGreater(metrics["diversity"]["location_signature_entropy"], 0)
        self.assertGreater(metrics["diversity"]["syntax_entropy"], 0)
        self.assertEqual(metrics["runtime"]["deterministic_replay_mismatch_count"], 0)

    def test_syntax_entropy_distinguishes_sentence_segments_without_terminal_punctuation(self):
        single_sentence = [
            record(seed, f"A girl checks route number {seed} in a quiet station while holding a transit card")
            for seed in range(4)
        ]
        mixed_syntax = [
            record(seed, f"A girl checks route number {seed}. The station remains quiet around her")
            if seed % 2
            else record(seed, f"A girl checks route number {seed} in a quiet station while holding a transit card")
            for seed in range(4)
        ]

        single_entropy = analyze_records(single_sentence, self.policy)["metrics"]["diversity"]["syntax_entropy"]
        mixed_entropy = analyze_records(mixed_syntax, self.policy)["metrics"]["diversity"]["syntax_entropy"]
        self.assertEqual(single_entropy, 0)
        self.assertGreater(mixed_entropy, single_entropy)

    def test_all_consistency_domains_report_observation_reason_codes_and_issues(self):
        observations = (
            ("location_action_object", "hard_reason_codes", "location_object_conflict", 4),
            ("clothing_tpo_weather", "soft_reason_codes", "weather_tpo_soft_conflict", 2),
            ("mood_action_garnish", "hard_reason_codes", "mood_action_hard_conflict", 0),
        )
        records = []
        for seed, (domain, reason_field, reason_code, survivors) in enumerate(observations, 1):
            item = record(seed, f"A girl follows a quiet path through garden number {seed} while holding a book beside the river.")
            item["final_context"]["constraint_results"] = [{
                "domain": domain,
                reason_field: [reason_code],
                "survivor_count": survivors,
            }]
            records.append(item)

        analysis = analyze_records(records, self.policy)
        codes = {issue["issue_code"] for issue in analysis["issues"]["issues"]}
        domains = analysis["metrics"]["consistency"]["domains"]

        for domain, reason_field, reason_code, _survivors in observations:
            with self.subTest(domain=domain):
                metric = domains[domain]
                self.assertEqual(metric["status"], "observed")
                expected_evaluated = 1 if domain == "mood_action_garnish" else 3
                self.assertEqual(metric["evaluated_record_count"], expected_evaluated)
                self.assertEqual(metric["not_observed_record_count"], 3 - expected_evaluated)
                reason_counts = metric["hard_reason_code_counts" if reason_field == "hard_reason_codes" else "soft_reason_code_counts"]
                self.assertEqual(reason_counts[reason_code], 1)
                self.assertIn(f"{domain}_conflict", codes)

    def test_time_of_day_conflict_uses_shared_location_reason_code(self):
        case_ids = {
            "location_time_of_day_conflict",
            "location_night_morning_conflict",
            "location_evening_morning_conflict",
            "location_evening_midday_conflict",
        }
        cases = [item for item in self.fixture["cases"] if item["id"] in case_ids]
        self.assertEqual(len(cases), len(case_ids))

        for case in cases:
            with self.subTest(case=case["id"]):
                analysis = self.analyze_case(case)
                location = analysis["metrics"]["consistency"]["domains"]["location_action_object"]
                self.assertEqual(
                    location["hard_reason_code_counts"],
                    {"night_daylight_scene_conflict": 1},
                )

    def test_unclassified_domain_reason_is_observed_without_claiming_a_conflict(self):
        item = record(1, "A girl follows a quiet path through the garden while holding a book beside the river at sunrise.")
        item["final_context"]["constraint_results"] = [{
            "domain": "mood_action_garnish",
            "reason_codes": ["unclassified_fixture_reason"],
        }]

        analysis = analyze_records([item], self.policy)
        mood = analysis["metrics"]["consistency"]["domains"]["mood_action_garnish"]
        codes = {issue["issue_code"] for issue in analysis["issues"]["issues"]}

        self.assertEqual(mood["status"], "observed")
        self.assertEqual(mood["unclassified_reason_code_counts"], {"unclassified_fixture_reason": 1})
        self.assertEqual(mood["hard_conflict_count"], 0)
        self.assertEqual(mood["soft_conflict_count"], 0)
        self.assertNotIn("mood_action_garnish_conflict", codes)

    def test_survivor_metrics_distinguish_observed_values_from_not_observed(self):
        observed = []
        for seed, count in enumerate((0, 4, 10), 1):
            item = record(seed, f"A girl follows a quiet path through garden number {seed} while holding a book beside the river.")
            item["final_context"]["constraint_results"] = [{
                "domain": "location_action_object",
                "survivor_count": count,
            }]
            observed.append(item)

        survivor = analyze_records(observed, self.policy)["metrics"]["diversity"]["survivor"]
        absent = analyze_records([record(9, self.fixture["cases"][0]["prompt"])], self.policy)["metrics"]["diversity"]["survivor"]

        self.assertEqual(survivor["status"], "observed")
        self.assertEqual(survivor["observed_record_count"], 3)
        self.assertEqual(survivor["not_observed_record_count"], 0)
        self.assertEqual(survivor["count_min"], 0)
        self.assertEqual(survivor["count_max"], 10)
        self.assertEqual(survivor["count_p50"], 4)
        self.assertEqual(survivor["count_p95"], 9.4)
        self.assertEqual(survivor["zero_survivor_observation_count"], 1)
        self.assertEqual(absent["status"], "not_observed")
        self.assertEqual(absent["observed_record_count"], 0)
        self.assertEqual(absent["not_observed_record_count"], 1)
        self.assertIsNone(absent["count_min"])
        self.assertIsNone(absent["count_max"])

    def test_policy_schema_freezes_cohort_hard_gates_effect_sizes_and_review(self):
        raw = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(raw["status"], "frozen")
        self.assertRegex(raw["policy_version"], r"^prompt-quality-policy/v\d+$")
        self.assertEqual(raw["cohort"]["control_count"], 64)
        self.assertEqual(raw["cohort"]["exploration_count"], 16)
        self.assertEqual(raw["cohort"]["formal_promotion_min_samples"], 80)
        self.assertEqual(raw["comparison"]["effect_sizes"]["defect_count_min_reduction"], 2)
        self.assertEqual(raw["comparison"]["effect_sizes"]["defect_rate_min_relative_improvement"], 0.10)
        self.assertEqual(raw["comparison"]["effect_sizes"]["diversity_min_relative_improvement"], 0.05)
        self.assertEqual(raw["comparison"]["guards"]["max_absolute_rate_regression"], 0.02)
        self.assertEqual(raw["review"]["independent_lanes"], 2)
        self.assertEqual(raw["review"]["paired_samples"], 20)
        self.assertEqual(raw["review"]["minimum_valid_votes_per_required_dimension"], "computed_before_voting")
        self.assertEqual(raw["review"]["minimum_valid_vote_fraction"], 0.9)
        self.assertEqual(raw["review"]["minimum_valid_votes_cap"], 36)
        self.assertTrue(raw["comparison"]["hard_gates"])

    def test_analysis_artifacts_are_canonical_and_separated(self):
        result_root = ROOT / "assets" / "results"
        result_root.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix="prompt-quality-analysis-", dir=result_root))
        self.addCleanup(lambda: shutil.rmtree(temporary, ignore_errors=True))
        records_path = temporary / "records.jsonl"
        records_path.write_bytes(canonical_json_bytes(record(1, self.fixture["cases"][0]["prompt"])))

        result = write_analysis(records_path, temporary / "metrics.json", temporary / "issues.json", POLICY_PATH)

        self.assertEqual((temporary / "metrics.json").read_bytes(), canonical_json_bytes(result["metrics"]))
        self.assertEqual((temporary / "issues.json").read_bytes(), canonical_json_bytes(result["issues"]))
        self.assertNotIn("issues", result["metrics"])
        self.assertNotIn("metrics", result["issues"])


if __name__ == "__main__":
    unittest.main()
