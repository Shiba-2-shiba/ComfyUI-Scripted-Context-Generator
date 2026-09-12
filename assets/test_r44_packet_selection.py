"""Behavioral tests for diagnostic-only R44 coverage packet selection."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SELECTOR = ROOT / "tools" / "select_r44_coverage_packets.py"
FAMILY = "subject_action_scene"
OTHER_FAMILY = "scene_lead_subject_action"


def rows_for(seeds, *, blockers=("action.leaf_grammar_unknown",),
             domains=("action",), family=FAMILY, constructor="producer-a"):
    """Small structural audit rows; no workflow replay or runtime authorization."""
    signature = {
        "schema_version": "realizer-coverage-signature/v1",
        "route": "fallback",
        "blocked_domains": list(domains),
        "domains": {"action": {"constructor_id": constructor}},
        "eligible_families": [],
        "family_blockers": {family: list(blockers)},
        "proof_basis": "common_reconstructed",
    }
    sha = hashlib.sha256((json.dumps(signature, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")) + "\n").encode()).hexdigest()
    return [{
        "run_seed": seed, "builder_seed": seed,
        "route": "fallback", "trace_mode": "none",
        "normal": {"realizer_version": "v1", "syntax_family": FAMILY},
        "domains": {domain: {"constructor_supported": False, "binding_success": None,
                              "runtime_available": False, "blockers": list(blockers)}
                    for domain in domains},
        "families": {family: {"declared": True, "constructor_present": True,
                              "runtime_eligible": False, "selected": False,
                              "executed_v2": False, "forced_render_v2": None,
                              "forced": None, "blockers": list(blockers)}},
        "blockers": [{"id": blocker, "domains": list(domains), "families": [family]}
                     for blocker in blockers],
        "errors": [], "coverage_signature": deepcopy(signature),
        "coverage_signature_sha256": sha,
    } for seed in seeds]


class PacketSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SELECTOR.exists():
            spec = importlib.util.spec_from_file_location("r44_selector", SELECTOR)
            cls.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.module)
        else:
            cls.module = None

    def select(self, rows, **kwargs):
        self.assertIsNotNone(self.module, "R44 packet selector has not been implemented")
        return self.module.select_packets(rows, **kwargs)

    def test_excludes_existing_v2_successes(self):
        rows = rows_for(range(4))
        rows[0]["normal"]["realizer_version"] = "v2"
        self.assertEqual(self.select(rows), [])

    def test_requires_explicit_ordinary_fallback(self):
        for version in (None, "v3", ""):
            with self.subTest(version=version):
                rows = rows_for(range(4))
                rows[0]["normal"]["realizer_version"] = version
                self.assertEqual(self.select(rows), [])

    def test_excludes_policy_conflict(self):
        self.assertEqual(self.select(rows_for(range(4), blockers=(
            "policy.conflict", "action.leaf_grammar_unknown"))), [])

    def test_excludes_binding_replay_mismatch(self):
        for blocker in ("binding.frame_current_text_mismatch", "binding.replay_mismatch",
                        "binding.current_input_mismatch", "render.proof_constructor_mismatch",
                        "transport.runtime_inputs_missing", "action.current_input_mismatch"):
            for location in ("errors", "signature", "domain", "family"):
                with self.subTest(blocker=blocker, location=location):
                    rows = rows_for(range(4))
                    for row in rows:
                        if location == "errors":
                            row["errors"] = [{"id": blocker}]
                        elif location == "signature":
                            row["coverage_signature"]["family_blockers"][FAMILY].append(blocker)
                        elif location == "domain":
                            row["domains"]["action"]["blockers"].append(blocker)
                        else:
                            row["families"][FAMILY]["blockers"].append(blocker)
                    self.assertEqual(self.select(rows), [])

    def test_excludes_invalid_common_inputs_without_ordinary_error(self):
        rows = rows_for(range(4))
        for row in rows:
            row["coverage_signature"]["proof_basis"] = "invalid_common_inputs"
        self.assertEqual(self.select(rows), [])

    def test_excludes_family_role_mismatch_as_a_coverage_target(self):
        for blocker in ("family.role_mismatch", "family.composition_mode_disabled"):
            with self.subTest(blocker=blocker):
                self.assertEqual(self.select(rows_for(range(4), blockers=(
                    blocker, "action.leaf_grammar_unknown"))), [])

    def test_route_excluded_family_does_not_hide_repairable_family(self):
        rows = rows_for(range(4))
        for row in rows:
            row["coverage_signature"]["family_blockers"][OTHER_FAMILY] = ["family.role_mismatch"]
        self.assertEqual(self.select(rows)[0]["target_family_keys"], [FAMILY])

    def test_route_ceiling_alone_cannot_authorize_packet(self):
        self.assertEqual(self.select(rows_for(range(4), blockers=("family.legacy_route_ceiling",))), [])
        packets = self.select(rows_for(range(4), blockers=(
            "family.legacy_route_ceiling", "scene.attachment_unknown")))
        self.assertEqual(packets[0]["repairable_blocker_ids"], ["scene.attachment_unknown"])

    def test_unknown_nonrepairable_blocker_is_not_a_target(self):
        self.assertEqual(self.select(rows_for(range(4), blockers=(
            "family.unclassified_rejection", "action.leaf_grammar_unknown"))), [])

    def test_fresh_common_blockers_replace_ordinary_route_rejections(self):
        rows = rows_for(range(4))
        for row in rows:
            row["families"][FAMILY]["blockers"] = ["family.role_mismatch"]
            row["blockers"] = [{"id": "family.role_mismatch"}]
        self.assertEqual(self.select(rows)[0]["distinct_seed_count"], 4)

    def test_requires_at_least_four_distinct_seeds(self):
        self.assertEqual(self.select(rows_for([0, 1, 2, 2, 2])), [])
        self.assertEqual(self.select(rows_for([0, 1, 2, 3, 3]))[0]["distinct_seed_count"], 4)

    def test_prefers_more_distinct_seeds(self):
        smaller = rows_for(range(4))
        larger = rows_for(range(10, 15), constructor="producer-b")
        self.assertEqual(self.select(smaller + larger)[0]["seed_set"], [10, 11, 12, 13, 14])

    def test_prefers_unobserved_family_potential_on_tie(self):
        observed = rows_for([100])
        observed[0]["normal"]["realizer_version"] = "v2"
        observed[0]["families"][FAMILY]["executed_v2"] = True
        forced = rows_for(range(10, 14), family=OTHER_FAMILY)
        for row in forced:
            row["families"][OTHER_FAMILY].update(forced_render_v2=True, constructor_v2=True)
        packets = self.select(rows_for(range(4)) + forced + observed)
        self.assertEqual(packets[0]["target_family_keys"], [OTHER_FAMILY])

    def test_prefers_fewer_blocked_domains_on_tie(self):
        packets = self.select(rows_for(range(4), domains=("action", "scene")) +
                              rows_for(range(10, 14)))
        self.assertEqual(packets[0]["blocked_domains"], ["action"])

    def test_prefers_fewer_repairable_blockers_on_tie(self):
        packets = self.select(rows_for(range(4), blockers=("action.leaf_grammar_unknown",
                                                            "action.same_subject_unknown")) +
                              rows_for(range(10, 14)))
        self.assertEqual(packets[0]["seed_set"], [10, 11, 12, 13])

    def test_tie_breaks_by_signature_hash(self):
        rows = rows_for(range(4)) + rows_for(range(10, 14), constructor="producer-b")
        self.assertEqual([p["coverage_signature_sha256"] for p in self.select(rows)],
                         sorted({r["coverage_signature_sha256"] for r in rows}))

    def test_input_row_order_does_not_change_packets(self):
        rows = rows_for(range(20)) + rows_for(range(30, 36), constructor="producer-b")
        before = deepcopy(rows)
        expected = self.select(rows)
        self.assertEqual(rows, before)
        random.Random(42).shuffle(rows)
        self.assertEqual(self.select(rows), expected)

    def test_packets_do_not_share_the_same_seed_signature_group(self):
        rows = rows_for(range(4))
        packets = self.select(rows + deepcopy(rows))
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0]["seed_set"], [0, 1, 2, 3])

    def test_keeps_full_seed_union_and_caps_examples(self):
        packets = self.select(rows_for(range(20)) +
                              rows_for(range(10, 30), constructor="producer-b"))
        self.assertEqual(len(set(packets[0]["seed_set"]) | set(packets[1]["seed_set"])), 30)
        self.assertEqual(packets[0]["projected_upper_bound"], 20)
        self.assertEqual(packets[0]["example_seeds"], list(range(10, 18)) if
                         packets[0]["seed_set"][0] == 10 else list(range(8)))

    def test_roi_floor_and_cap_use_distinct_seed_upper_bound(self):
        for size, roi in ((4, 4), (9, 4), (20, 10), (40, 16)):
            with self.subTest(size=size):
                packet = self.select(rows_for(range(size)))[0]
                self.assertEqual(packet["projected_upper_bound"], size)
                self.assertEqual(packet["acceptance_min_new_ordinary"], roi)

    def test_packet_limit_and_ids(self):
        rows = sum((rows_for(range(n * 10, n * 10 + 4), constructor=f"producer-{n}")
                    for n in range(5)), [])
        self.assertEqual([p["packet_id"] for p in self.select(rows)], ["R44-A", "R44-B", "R44-C"])
        self.assertEqual(len(self.select(rows, max_packets=1)), 1)
        self.assertEqual(self.select(rows, max_packets=0), [])
        for value in (-1, 4, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.select(rows, max_packets=value)

    def test_manifest_does_not_copy_prompt_action_or_scene_text(self):
        rows = rows_for(range(4))
        for row in rows:
            row["normal"]["raw_prompt"] = "SECRET_COMPLETE_PROMPT"
            row["coverage_signature"]["domains"]["action"]["text"] = "SECRET_ACTION_TEXT"
            row["scene_text"] = "SECRET_SCENE_TEXT"
        self.assertNotIn("SECRET_", json.dumps(self.select(rows)))

    def test_cli_writes_packets_and_rejects_malformed_rows(self):
        self.assertIsNotNone(self.module, "R44 packet selector has not been implemented")
        with tempfile.TemporaryDirectory() as directory:
            rows_path = Path(directory) / "rows.jsonl"
            output_path = Path(directory) / "nested" / "packets.json"
            rows = rows_for(range(4))
            rows_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            command = [sys.executable, str(SELECTOR), "--rows", str(rows_path),
                       "--output", str(output_path), "--max-packets", "3"]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), self.select(rows))
            saved = output_path.read_bytes()
            rows_path.write_text('{"run_seed":', encoding="utf-8")
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(output_path.read_bytes(), saved)


if __name__ == "__main__":
    unittest.main()
