"""R43 measures captured evidence without extending the candidate's permissions."""
import copy
import json
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from pipeline.prompt_realizer import ContentPlan, realize_content_plan
from pipeline.v2_candidate_bridge import render_candidate
from prompt_renderer import _finalize_prompt
from tools import realizer_reachability_diagnostics as diagnostics
from assets.test_prompt_realizer_v2 import fixture
from assets.test_n27_r4_integration import subordinate_case


FIXTURES = Path(__file__).parent / "fixtures"
DIRECT_CASES = json.loads((FIXTURES / "n27_r1_direct_cases.json").read_text(encoding="utf-8"))
PRODUCTIVE_CASES = json.loads((FIXTURES / "n27_r4_productive_cases.json").read_text(encoding="utf-8"))


def snapshot_for(case):
    """Synthetic finalization around an existing captured real-case bridge input."""
    plan = ContentPlan(**case["slots"])
    legacy, debug = realize_content_plan(plan, return_debug=True)
    captured = []
    template, _, _ = render_candidate(
        plan, legacy, debug, case["frame"], case["surface"], case["replacements"],
        case["builder_seed"], audit_sink=captured.append,
    )
    finalization = {"replacements": case["replacements"], "staging_tags": "",
                    "action": dict(case["replacements"])["{action}"], "composition_mode": True}
    return {"bridge": captured[0], "finalization": finalization,
            "raw_prompt": _finalize_prompt(template, **finalization)}


class TestReachabilityDiagnostics(unittest.TestCase):
    def test_simple_route_all_six_including_real_baseline_constructor(self):
        plan, frame = fixture("single-sentence-scene-tail", action="checking a transit card", surface="gerund")
        case = {
            "slots": plan.to_dict(), "frame": frame.to_dict(), "builder_seed": 7,
            "surface": {"surface": "gerund", "rendered_clause": plan.semantic_slots["adjunct"]},
            "replacements": [["{action}", frame.legacy_text]],
        }
        snapshot = snapshot_for(case)
        self.assertEqual(len(snapshot["bridge"]["selectable"]), 6)
        result = diagnostics.diagnose_snapshot(snapshot, force_families=True)
        self.assertEqual(result["route"], "simple_legacy_compatible")
        self.assertEqual(result["errors"], [])
        self.assertTrue(all(row["runtime_eligible"] for row in result["families"].values()))
        self.assertTrue(all(row["constructor_v2"] for row in result["families"].values()))
        self.assertFalse(result["families"][diagnostics.BASELINE_FAMILY]["baseline_marker"])
        # Find a genuine ordinary baseline-family draw, rather than relabeling
        # a sink snapshot after execution.
        for seed in range(32):
            candidate = snapshot_for({**case, "builder_seed": seed})
            if candidate["bridge"]["selected"] == diagnostics.BASELINE_FAMILY:
                selected = diagnostics.diagnose_snapshot(candidate, force_families=True)["families"][diagnostics.BASELINE_FAMILY]
                self.assertTrue(selected["executed_v2"])
                self.assertTrue(selected["forced_render_v2"])
                break
        else:
            self.fail("bounded deterministic seed sweep did not exercise baseline-family selection")

    def test_r4_trace_is_legacy_route_not_r43_common_evidence(self):
        snapshot = snapshot_for(subordinate_case())
        self.assertTrue(snapshot["bridge"]["structural_evidence_used"])
        result = diagnostics.diagnose_snapshot(snapshot, force_families=True)
        self.assertEqual(result["route"], "legacy_direct")
        self.assertEqual(result["trace_mode"], "legacy_r4_structural")
        self.assertEqual(result["errors"], [])

    def test_noncomposition_snapshot_reports_unavailable_without_forcing(self):
        snapshot = {"bridge": None, "finalization": {"composition_mode": False}, "raw_prompt": "a prompt"}
        with patch.object(diagnostics, "_force", side_effect=AssertionError("must not force")):
            result = diagnostics.diagnose_snapshot(snapshot, force_families=True)
        self.assertEqual(len(result["families"]), 6)
        self.assertEqual(result["errors"], [])
        for row in result["families"].values():
            self.assertFalse(row["runtime_eligible"])
            self.assertIsNone(row["constructor_v2"])
            self.assertIsNone(row["forced_render_v2"])
            self.assertEqual(row["semantic_parity"], "NOT_RUN")
        for row in result["domains"].values():
            self.assertIsNone(row["constructor_supported"])
            self.assertIsNone(row["binding_success"])
            self.assertEqual(row["status"], "NOT_AVAILABLE")

    def test_off_does_not_force_and_preserves_snapshot_and_rng(self):
        snapshot = snapshot_for(DIRECT_CASES[0])
        before, state = copy.deepcopy(snapshot), random.getstate()
        with patch.object(diagnostics, "_force", side_effect=AssertionError("must not force")):
            result = diagnostics.diagnose_snapshot(snapshot)
        self.assertEqual(snapshot, before)
        self.assertEqual(random.getstate(), state)
        for row in result["families"].values():
            self.assertIsNone(row["constructor_v2"])
            self.assertIsNone(row["forced_render_v2"])
            self.assertIsNone(row["forced"])
            self.assertEqual(row["semantic_parity"], "NOT_RUN")

    def test_stages_route_ceiling_and_exact_ordinary_equivalence(self):
        snapshot = snapshot_for(DIRECT_CASES[0])
        before, state = copy.deepcopy(snapshot), random.getstate()
        result = diagnostics.diagnose_snapshot(snapshot, force_families=True)
        self.assertEqual(snapshot, before)
        self.assertEqual(random.getstate(), state)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["route"], "legacy_direct")
        expected = set(snapshot["bridge"]["selectable"]) - {diagnostics.BASELINE_FAMILY}
        self.assertEqual({key for key, row in result["families"].items() if row["runtime_eligible"]}, expected)
        self.assertLessEqual(len(expected), 3)
        selected = snapshot["bridge"]["selected"]
        self.assertTrue(result["families"][selected]["selected"])
        self.assertTrue(result["families"][selected]["executed_v2"])
        self.assertTrue(result["families"][selected]["forced_render_v2"])
        self.assertEqual(result["families"][selected]["semantic_parity"], "EXACT_ORDINARY_OUTPUT")
        for family, row in result["families"].items():
            if family not in expected:
                self.assertEqual(row["forced"]["status"], "NOT_ELIGIBLE")
                self.assertIsNone(row["constructor_v2"])
            elif family != selected:
                self.assertTrue(row["constructor_v2"])
                self.assertIsNone(row["forced_render_v2"])
                self.assertEqual(row["semantic_parity"], "NOT_AVAILABLE")

    def test_constructor_recognition_does_not_invent_origin_binding(self):
        result = diagnostics.diagnose_snapshot(snapshot_for(DIRECT_CASES[0]))
        self.assertTrue(result["domains"]["action"]["constructor_supported"])
        self.assertTrue(result["domains"]["action"]["constructor_paths"]["legacy_direct"])
        for domain in ("subject", "clothing", "scene", "garnish", "mood"):
            row = result["domains"][domain]
            self.assertTrue(row["constructor_supported"], domain)
            self.assertIsNone(row["binding_success"], domain)
            self.assertFalse(row["runtime_available"], domain)
            self.assertTrue(row["unknown"], domain)

    def test_lexical_counter_is_not_semantic_certification(self):
        snapshot = snapshot_for(DIRECT_CASES[0])
        snapshot["raw_prompt"] = snapshot["raw_prompt"].replace("old mechanical clocks", "mechanical old clocks")
        result = diagnostics.diagnose_snapshot(snapshot, force_families=True)
        selected = result["families"][snapshot["bridge"]["selected"]]
        self.assertTrue(selected["constructor_v2"])
        self.assertTrue(selected["forced"]["lexical_counter_equal_auxiliary"])
        self.assertIsNone(selected["forced_render_v2"])
        self.assertEqual(selected["semantic_parity"], "NOT_AVAILABLE")

    def test_eligible_constructor_fallback_is_an_explicit_error(self):
        snapshot = snapshot_for(DIRECT_CASES[0])
        with patch.object(diagnostics, "realize_content_plan", return_value=("fallback", {
            "realizer_version": "v1", "syntax_family": diagnostics.BASELINE_FAMILY,
        })):
            result = diagnostics.diagnose_snapshot(snapshot, force_families=True)
        self.assertEqual(len(result["errors"]), len(snapshot["bridge"]["selectable"]))
        self.assertTrue(all(item["id"] == "render.proof_constructor_mismatch" for item in result["errors"]))
        self.assertFalse(any(row["forced_render_v2"] for row in result["families"].values()))

    def test_ordinary_selected_constructor_mismatch_is_error_without_forcing(self):
        for version in ("v1", "v2"):
            with self.subTest(version=version):
                snapshot = snapshot_for(DIRECT_CASES[0])
                snapshot["bridge"]["output_debug"].update(
                    realizer_version=version, syntax_family=diagnostics.BASELINE_FAMILY)
                with patch.object(diagnostics, "_force", side_effect=AssertionError("must not force")):
                    result = diagnostics.diagnose_snapshot(snapshot, force_families=False)
                selected = snapshot["bridge"]["selected"]
                self.assertEqual(result["errors"], [{
                    "id": "render.proof_constructor_mismatch", "family": selected,
                    "detail": "ordinary_selected_constructor_not_executed_v2",
                }])
                self.assertIn("render.proof_constructor_mismatch", result["families"][selected]["blockers"])
                self.assertIsNone(result["families"][selected]["constructor_v2"])

    def test_ordinary_and_forced_constructor_mismatch_are_not_double_counted(self):
        snapshot = snapshot_for(DIRECT_CASES[0])
        snapshot["bridge"]["output_debug"].update(realizer_version="v1", syntax_family=diagnostics.BASELINE_FAMILY)
        with patch.object(diagnostics, "realize_content_plan", return_value=("fallback", {
            "realizer_version": "v1", "syntax_family": diagnostics.BASELINE_FAMILY,
        })):
            result = diagnostics.diagnose_snapshot(snapshot, force_families=True)
        selected_errors = [error for error in result["errors"] if error["family"] == snapshot["bridge"]["selected"]]
        self.assertEqual(len(selected_errors), 1)
        self.assertEqual(len(result["errors"]), len(snapshot["bridge"]["selectable"]))

    def test_constructor_exception_is_an_explicit_error(self):
        snapshot = snapshot_for(DIRECT_CASES[0])
        with patch.object(diagnostics, "realize_content_plan", side_effect=ValueError("test")):
            result = diagnostics.diagnose_snapshot(snapshot, force_families=True)
        self.assertTrue(result["errors"])
        selected = result["families"][snapshot["bridge"]["selected"]]
        self.assertEqual(selected["forced"]["error_type"], "ValueError")
        self.assertFalse(selected["constructor_v2"])

    def test_fallback_still_reports_independent_component_blockers(self):
        snapshot = snapshot_for(PRODUCTIVE_CASES[0])
        self.assertFalse(snapshot["bridge"]["output_debug"]["candidate_v2_applied"])
        # Separate unrecognized components must not disappear behind common fallback.
        changed = dict(snapshot["bridge"]["replacements"])
        changed.update({"{subj}": "unrecognized subject", "{costume}": "unrecognized clothes",
                        "{loc}": "unrecognized scene", "{garnish}": "unrecognized garnish",
                        "{meta_mood}": "unrecognized mood", "{action}": "unrecognized action"})
        snapshot["bridge"]["replacements"] = list(changed.items())
        snapshot["bridge"]["input_plan"]["semantic_slots"]["scene"] = "unsupported topology"
        with patch.object(diagnostics, "_force", side_effect=AssertionError("ineligible must not force")):
            result = diagnostics.diagnose_snapshot(snapshot, force_families=True)
        expected = {"subject.unsupported_constructor", "clothing.owner_unknown", "clothing.number_unknown",
                    "scene.source_field_unknown", "scene.attachment_unknown", "garnish.attachment_unknown",
                    "mood.attachment_unknown", "template.topology_unsupported",
                    "binding.frame_current_text_mismatch", "action.leaf_grammar_unknown"}
        ids = [item["id"] for item in result["blockers"]]
        self.assertTrue(expected <= set(ids))
        self.assertEqual(ids, sorted(set(ids)))
        self.assertTrue(all(item["kind"] in {"unknown", "policy", "unimplemented", "route", "hard_rejection"}
                            for item in result["blockers"]))
        self.assertEqual(next(item for item in result["blockers"]
                              if item["id"] == "binding.frame_current_text_mismatch")["kind"], "hard_rejection")
        self.assertEqual(result, diagnostics.diagnose_snapshot(snapshot, force_families=True))

    def test_positive_independent_subject_is_hard_rejection(self):
        snapshot = snapshot_for(PRODUCTIVE_CASES[0])
        values = dict(snapshot["bridge"]["replacements"])
        values["{action}"] = "she checks a transit card"
        snapshot["bridge"]["replacements"] = list(values.items())
        result = diagnostics.diagnose_snapshot(snapshot)
        self.assertEqual(next(item for item in result["blockers"]
                              if item["id"] == "action.independent_subject")["kind"], "hard_rejection")


if __name__ == "__main__":
    unittest.main()
