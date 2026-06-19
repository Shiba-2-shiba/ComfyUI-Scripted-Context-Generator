import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestSemanticEpigAudit(unittest.TestCase):
    def test_fixture_loads(self):
        from tools.audit_semantic_epig_outputs import load_cases

        cases = load_cases(Path(ROOT) / "assets" / "fixtures" / "semantic_epig_audit_cases.json")

        self.assertGreaterEqual(len(cases), 5)
        self.assertTrue(all(case.get("case_id") for case in cases))

    def test_audit_is_deterministic_for_same_seed(self):
        from tools.audit_semantic_epig_outputs import audit_case, load_cases

        case = load_cases(Path(ROOT) / "assets" / "fixtures" / "semantic_epig_audit_cases.json")[0]
        first = audit_case(case, 2)
        second = audit_case(case, 2)

        self.assertEqual(first["passive_prompt"], second["passive_prompt"])
        self.assertEqual(first["active_prompt"], second["active_prompt"])
        self.assertEqual(first["changed_domains"], second["changed_domains"])
        self.assertIn("active", first["semantic_debug"])
        self.assertIn("policy_issues", first)

    def test_audit_writes_json_output(self):
        from tools.audit_semantic_epig_outputs import audit_cases, load_cases, write_audit

        cases = load_cases(Path(ROOT) / "assets" / "fixtures" / "semantic_epig_audit_cases.json")[:1]
        result = audit_cases(cases, seed_start=0, seed_count=1)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = write_audit(result, Path(tmpdir) / "semantic_epig_audit.json")
            self.assertTrue(output_path.exists())

        self.assertEqual(result["record_count"], 1)
        self.assertIn("records", result)

    def test_audit_exposes_subject_centric_override_debug(self):
        from tools.audit_semantic_epig_outputs import audit_case, load_cases

        cases = load_cases(Path(ROOT) / "assets" / "fixtures" / "semantic_epig_audit_cases.json")
        case = next(item for item in cases if item["case_id"] == "shy_classroom_door")
        result = audit_case(case, 0)
        personality_debug = result["semantic_debug"]["active"]["personality_behavior"]
        override_debug = personality_debug["subject_centric_overrides"]

        self.assertEqual(override_debug["mode"], "active")
        self.assertEqual(override_debug["adoption_state"], "active_candidate_selection")
        self.assertGreaterEqual(override_debug["available_count"], 1)

    def test_audit_fixture_covers_active_curious_override(self):
        from tools.audit_semantic_epig_outputs import audit_case, load_cases

        cases = load_cases(Path(ROOT) / "assets" / "fixtures" / "semantic_epig_audit_cases.json")
        case = next(item for item in cases if item["case_id"] == "mysterious_bookstore_corner")
        result = audit_case(case, 0)
        personality_debug = result["semantic_debug"]["active"]["personality_behavior"]

        self.assertEqual(
            personality_debug["subject_centric_override_selected"]["id"],
            "sc_gaze_curious_01",
        )
        self.assertEqual(personality_debug["subject_centric_override_selected"]["text"], "curious eyes")
        self.assertEqual(result["policy_issues"], [])

    def test_audit_fixture_covers_mood_gated_hands_override(self):
        from tools.audit_semantic_epig_outputs import audit_case, load_cases

        cases = load_cases(Path(ROOT) / "assets" / "fixtures" / "semantic_epig_audit_cases.json")
        case = next(item for item in cases if item["case_id"] == "shy_moved_station_reunion")
        result = audit_case(case, 0)
        personality_debug = result["semantic_debug"]["active"]["personality_behavior"]

        self.assertEqual(
            personality_debug["subject_centric_override_selected"]["id"],
            "sc_hands_touching_lips_01",
        )
        self.assertEqual(
            personality_debug["subject_centric_override_selected"]["text"],
            "fingers resting near her lips",
        )
        self.assertEqual(result["policy_issues"], [])

    def test_audit_fixture_covers_calm_mood_gated_override(self):
        from tools.audit_semantic_epig_outputs import audit_case, load_cases

        cases = load_cases(Path(ROOT) / "assets" / "fixtures" / "semantic_epig_audit_cases.json")
        case = next(item for item in cases if item["case_id"] == "neutral_calm_balcony_pause")
        result = audit_case(case, 0)
        personality_debug = result["semantic_debug"]["active"]["personality_behavior"]

        self.assertEqual(
            personality_debug["subject_centric_override_selected"]["id"],
            "sc_expression_calm_01",
        )
        self.assertEqual(personality_debug["subject_centric_override_selected"]["text"], "calm expression")
        self.assertEqual(result["policy_issues"], [])

    def test_audit_fixture_still_covers_reassuring_override(self):
        from tools.audit_semantic_epig_outputs import audit_case, load_cases

        cases = load_cases(Path(ROOT) / "assets" / "fixtures" / "semantic_epig_audit_cases.json")
        case = next(item for item in cases if item["case_id"] == "faithful_library_note")
        result = audit_case(case, 0)
        personality_debug = result["semantic_debug"]["active"]["personality_behavior"]

        self.assertEqual(
            personality_debug["subject_centric_override_selected"]["id"],
            "sc_expression_reassuring_01",
        )
        self.assertEqual(
            personality_debug["subject_centric_override_selected"]["text"],
            "small reassuring smile",
        )
        self.assertEqual(result["policy_issues"], [])

    def test_audit_fixture_covers_contented_mood_gated_override(self):
        from tools.audit_semantic_epig_outputs import audit_case, load_cases

        cases = load_cases(Path(ROOT) / "assets" / "fixtures" / "semantic_epig_audit_cases.json")
        case = next(item for item in cases if item["case_id"] == "cheerful_joy_market_chat")
        result = audit_case(case, 0)
        personality_debug = result["semantic_debug"]["active"]["personality_behavior"]

        self.assertEqual(
            personality_debug["subject_centric_override_selected"]["id"],
            "sc_expression_contented_01",
        )
        self.assertEqual(
            personality_debug["subject_centric_override_selected"]["text"],
            "contented mouth",
        )
        self.assertEqual(result["policy_issues"], [])

    def test_audit_fixture_covers_wry_mood_gated_override(self):
        from tools.audit_semantic_epig_outputs import audit_case, load_cases

        cases = load_cases(Path(ROOT) / "assets" / "fixtures" / "semantic_epig_audit_cases.json")
        case = next(item for item in cases if item["case_id"] == "serious_awkward_office_paperwork")
        result = audit_case(case, 0)
        personality_debug = result["semantic_debug"]["active"]["personality_behavior"]

        self.assertEqual(
            personality_debug["subject_centric_override_selected"]["id"],
            "sc_expression_wry_01",
        )
        self.assertEqual(
            personality_debug["subject_centric_override_selected"]["text"],
            "wry grin",
        )
        self.assertEqual(result["policy_issues"], [])


if __name__ == "__main__":
    unittest.main()
