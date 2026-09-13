from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tools.audit_realizer_capabilities import (
    _git_commit,
    occurrences_from_rows,
    rank_r46_candidates,
    summarize_occurrences,
)
from tools.realizer_capability_projection import SCHEMA_VERSION as CAPABILITY_SCHEMA
from tools.workflow_prompt_runner import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
COVERAGE_SCHEMA = "realizer-coverage-signature/v1"


def _identity(domain: str = "action", field: str = "primary_action") -> dict:
    return {
        "schema_version": CAPABILITY_SCHEMA,
        "domain": domain,
        "capability_kind": "clause_atom",
        "producer_class": "pipeline.action_renderer",
        "constructor_class": "action_slots",
        "source_field_classes": [field],
        "catalog_source_classes": ["producer"],
        "form_class": "unknown",
        "attachment_class": "unknown",
        "owner_class": "unknown",
        "grammar_state": "unknown",
        "source_bound": True,
    }


def _sha(value: dict) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _row(
    seed: int,
    capability: dict,
    family_blockers: dict[str, list[str]],
    *,
    version: str = "v1",
    route: str = "fallback",
    blockers: list[dict] | None = None,
    errors: list[dict] | None = None,
) -> dict:
    projection = {
        "schema_version": CAPABILITY_SCHEMA,
        "status": "AVAILABLE",
        "capabilities": [{"capability": capability, "capability_sha256": _sha(capability)}],
    }
    signature = {
        "schema_version": COVERAGE_SCHEMA,
        "family_blockers": family_blockers,
    }
    return {
        "run_seed": seed,
        "route": route,
        "normal": {"realizer_version": version, "syntax_family": "ordinary_family"},
        "blockers": blockers or [],
        "errors": errors or [],
        "coverage_signature": signature,
        "coverage_signature_sha256": _sha(signature),
        "capability_projection": projection,
        "capability_projection_sha256": _sha(projection),
    }


def _occurrence(
    seed: int,
    capability: dict,
    family_blockers: dict[str, list[str]],
    *,
    version: str = "v1",
    route: str = "fallback",
    hard_excluded: bool = False,
) -> dict:
    sha = _sha(capability)
    domain_ids = sorted({
        blocker
        for blockers in family_blockers.values()
        for blocker in blockers
        if blocker.startswith(capability["domain"] + ".")
    })
    return {
        "schema_version": "realizer-capability-occurrence/v1",
        "run_seed": seed,
        "domain": capability["domain"],
        "capability": capability,
        "capability_sha256": sha,
        "ordinary_realizer_version": version,
        "ordinary_syntax_family": "ordinary_family",
        "route": route,
        "target_families": sorted(family_blockers),
        "blocker_ids": domain_ids,
        "family_blockers": family_blockers,
        "hard_excluded": hard_excluded,
    }


class CapabilityAuditTests(unittest.TestCase):
    def test_distinct_seed_count_does_not_count_seed_family_rows(self):
        capability = _identity()
        sha = _sha(capability)
        occurrences = [
            _occurrence(1, capability, {"family_a": ["action.leaf_grammar_unknown"],
                                        "family_b": ["action.leaf_grammar_unknown"]}),
            _occurrence(2, capability, {"family_a": ["action.leaf_grammar_unknown"]}),
            copy.deepcopy(_occurrence(1, capability, {"family_a": ["action.leaf_grammar_unknown"]})),
        ]

        summary = summarize_occurrences(occurrences)

        self.assertEqual(summary["capabilities"][sha]["distinct_seed_count"], 2)
        self.assertEqual(summary["capabilities"][sha]["seed_family_row_count"], 3)

    def test_occurrences_preserve_typed_identity_and_add_context_only(self):
        capability = _identity("clothing", "palette.colors")
        capability["source_field_classes"] = ["palette.colors", "choices.dresses"]
        capability["catalog_source_classes"] = ["character_palette", "selected_clothing_pack"]
        row = _row(9, capability, {
            "subject_action_scene": [
                "clothing.owner_unknown",
                "family.required_fact_not_true.frame_predicate_safe",
            ]
        })

        occurrence = occurrences_from_rows([row])[0]

        self.assertEqual(occurrence["capability"], capability)
        self.assertEqual(occurrence["run_seed"], 9)
        self.assertEqual(occurrence["target_families"], ["subject_action_scene"])
        self.assertEqual(occurrence["blocker_ids"], ["clothing.owner_unknown"])
        self.assertEqual(occurrence["family_blockers"], {
            "subject_action_scene": [
                "clothing.owner_unknown",
                "family.required_fact_not_true:frame_predicate_safe",
            ]
        })

    def test_occurrence_order_is_independent_of_input_row_order(self):
        capability_a = _identity(field="primary_action")
        capability_b = _identity(field="gaze_target")
        rows = [
            _row(5, capability_a, {"family_b": ["action.grammar_unknown"]}),
            _row(2, capability_b, {"family_a": ["action.grammar_unknown"]}),
        ]

        self.assertEqual(occurrences_from_rows(rows), occurrences_from_rows(list(reversed(rows))))

    def test_intersections_dedupe_seeds_and_cap_examples(self):
        capability_a = _identity(field="primary_action")
        capability_b = _identity(field="gaze_target")
        sha_a = _sha(capability_a)
        occurrences = []
        for seed in range(12):
            blockers = {
                "subject_action_scene": [
                    "action.leaf_grammar_unknown",
                    "scene.grammar_unknown",
                ]
            }
            occurrences.append(_occurrence(seed, capability_a, blockers))
            occurrences.append(copy.deepcopy(_occurrence(seed, capability_a, blockers)))
        occurrences.append(_occurrence(0, capability_b, {
            "subject_action_scene": ["scene.grammar_unknown"]
        }))

        summary = summarize_occurrences(occurrences)
        cap_blocker = {(row["capability_sha256"], row["blocker_id"]): row
                       for row in summary["capability_blocker_intersections"]}
        cap_family = {(row["capability_sha256"], row["family"]): row
                      for row in summary["capability_family_intersections"]}
        pairs = {tuple(row["blocker_ids"]): row for row in summary["blocker_pairs"]}

        self.assertEqual(cap_blocker[(sha_a, "action.leaf_grammar_unknown")]["distinct_seed_count"], 12)
        self.assertEqual(cap_family[(sha_a, "subject_action_scene")]["distinct_seed_count"], 12)
        self.assertEqual(
            pairs[("action.leaf_grammar_unknown", "scene.grammar_unknown")]["distinct_seed_count"],
            12,
        )
        self.assertEqual(cap_blocker[(sha_a, "action.leaf_grammar_unknown")]["example_seeds"], list(range(8)))

    def test_rows_without_projected_capabilities_remain_in_descriptive_blocker_counts(self):
        signature = {
            "schema_version": COVERAGE_SCHEMA,
            "family_blockers": {"family_a": ["scene.grammar_unknown", "action.grammar_unknown"]},
        }
        row = {
            "run_seed": 22,
            "normal": {"realizer_version": "v1", "syntax_family": "ordinary_family"},
            "blockers": [{"id": "clothing.owner_unknown"}],
            "errors": [],
            "coverage_signature": signature,
            "capability_projection": {
                "schema_version": CAPABILITY_SCHEMA,
                "status": "NOT_AVAILABLE",
                "capabilities": [],
            },
        }

        summary = summarize_occurrences([], rows=[row])

        self.assertEqual(summary["blockers"]["scene.grammar_unknown"]["distinct_seed_count"], 1)
        self.assertEqual(summary["blockers"]["clothing.owner_unknown"]["distinct_seed_count"], 1)
        self.assertEqual(summary["blocker_pairs"][0]["distinct_seed_count"], 1)

    def test_candidate_ranking_uses_qualifying_fallback_seed_union_and_family_breadth(self):
        capability_a = _identity(field="a")
        capability_b = _identity(field="b")
        capability_c = _identity(field="c")
        occurrences = []
        for seed in range(12):
            occurrences.append(_occurrence(seed, capability_a, {
                "family_a": ["action.leaf_grammar_unknown", "scene.grammar_unknown"],
                "family_b": ["action.leaf_grammar_unknown", "scene.grammar_unknown"],
            }))
            occurrences.append(_occurrence(seed + 20, capability_b, {
                "family_a": ["action.leaf_grammar_unknown"]
            }))
        for seed in range(8):
            occurrences.append(_occurrence(seed + 40, capability_c, {
                "family_a": ["action.leaf_grammar_unknown"]
            }))

        candidates = rank_r46_candidates(occurrences, summarize_occurrences(occurrences))

        self.assertEqual([row["capability_sha256"] for row in candidates[:3]], [
            _sha(capability_a), _sha(capability_b), _sha(capability_c)
        ])
        self.assertEqual(candidates[0]["distinct_seed_count"], 12)
        self.assertEqual(candidates[0]["affected_seed_count"], 12)
        self.assertEqual(candidates[0]["affected_family_keys"], ["family_a", "family_b"])

    def test_candidate_floor_excludes_nonfallback_nonrepairable_and_hard_families(self):
        capability = _identity()
        occurrences = [
            _occurrence(1, capability, {"family_a": ["action.grammar_unknown"]}),
            _occurrence(2, capability, {"family_a": ["action.grammar_unknown"]}),
            _occurrence(3, capability, {"family_a": ["action.grammar_unknown"]}),
            _occurrence(4, capability, {"family_a": ["action.grammar_unknown"]}, version="v2", route="v2"),
            _occurrence(5, capability, {"family_a": ["family.role_mismatch"]}),
            _occurrence(6, capability, {
                "family_a": ["action.grammar_unknown", "binding.current_input_mismatch"]
            }),
        ]

        self.assertEqual(rank_r46_candidates(occurrences, summarize_occurrences(occurrences)), [])

    def test_candidate_accepts_ordinary_v1_occurrences_without_route_metadata(self):
        capability = _identity()
        occurrences = [
            _occurrence(seed, capability, {"family_a": ["action.grammar_unknown"]})
            for seed in range(4)
        ]
        for item in occurrences:
            item.pop("route")

        candidates = rank_r46_candidates(occurrences, summarize_occurrences(occurrences))

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["affected_seed_count"], 4)

    def test_hard_blocker_in_sibling_family_excludes_the_whole_row(self):
        capability = _identity()
        rows = [
            _row(seed, capability, {
                "family_clean": ["action.grammar_unknown"],
                "family_hard": ["binding.current_input_mismatch"],
            })
            for seed in range(4)
        ]

        occurrences = occurrences_from_rows(rows)

        self.assertTrue(all(item["hard_excluded"] for item in occurrences))
        self.assertEqual(
            rank_r46_candidates(occurrences, summarize_occurrences(occurrences)),
            [],
        )

    def test_hard_row_blocker_is_descriptive_but_never_a_candidate(self):
        capability = _identity()
        rows = [
            _row(seed, capability, {"family_a": ["action.grammar_unknown"]},
                 blockers=[{"id": "binding.current_input_mismatch"}])
            for seed in range(4)
        ]

        occurrences = occurrences_from_rows(rows)
        summary = summarize_occurrences(occurrences, rows=rows)

        self.assertTrue(all(item["hard_excluded"] for item in occurrences))
        self.assertEqual(summary["capabilities"][_sha(capability)]["distinct_seed_count"], 4)
        self.assertEqual(rank_r46_candidates(occurrences, summary), [])

    def test_candidate_hash_breaks_an_exact_ranking_tie(self):
        capabilities = [_identity(field="tie_a"), _identity(field="tie_b")]
        occurrences = [
            _occurrence(seed, capability, {"family_a": ["action.grammar_unknown"]})
            for capability in capabilities for seed in range(4)
        ]

        ranked = rank_r46_candidates(occurrences, summarize_occurrences(occurrences))

        self.assertEqual(
            [row["capability_sha256"] for row in ranked],
            sorted(_sha(capability) for capability in capabilities),
        )

    def test_ranking_counts_all_co_blocker_classes_before_top_eight_cap(self):
        capability_eight = _identity(field="eight")
        capability_nine = _identity(field="nine")
        occurrences = []
        for capability, count in ((capability_eight, 8), (capability_nine, 9)):
            co_blockers = [f"other.blocker_{index}" for index in range(count)]
            for seed in range(4):
                occurrences.append(_occurrence(seed, capability, {
                    "family_a": ["action.grammar_unknown", *co_blockers]
                }))

        ranked = rank_r46_candidates(occurrences, summarize_occurrences(occurrences))

        self.assertEqual(ranked[0]["capability_sha256"], _sha(capability_eight))
        self.assertEqual(ranked[0]["co_blocker_class_count"], 8)
        self.assertEqual(ranked[1]["co_blocker_class_count"], 9)
        self.assertEqual(len(ranked[1]["top_co_blockers"]), 8)

    def test_occurrence_rejects_changed_identity_hash_and_unsupported_schema(self):
        capability = _identity()
        row = _row(1, capability, {"family_a": ["action.grammar_unknown"]})
        row["capability_projection"]["capabilities"][0]["capability_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "capability hash mismatch"):
            occurrences_from_rows([row])

        row = _row(1, capability, {"family_a": ["action.grammar_unknown"]})
        row["coverage_signature"]["schema_version"] = "future/v2"
        with self.assertRaisesRegex(ValueError, "coverage signature schema"):
            occurrences_from_rows([row])

    def test_cli_rejects_conflicting_outputs_with_exit_two(self):
        capability = _identity()
        row = _row(1, capability, {"family_a": ["action.grammar_unknown"]})
        with tempfile.TemporaryDirectory(dir=ROOT / "assets" / "results") as temporary:
            temporary_path = Path(temporary)
            rows_path = temporary_path / "rows.jsonl"
            rows_path.write_bytes(canonical_json_bytes(row))
            output = temporary_path / "output"
            output.mkdir()
            (output / "capability-summary.json").write_text("conflict", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "audit_realizer_capabilities.py"),
                 "--rows", str(rows_path), "--output-dir", str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_git_commit_is_unavailable_when_checkout_root_is_not_audit_root(self):
        foreign_checkout = "C:/" + "x" * 37
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=foreign_checkout + "\n", stderr=""
        )

        with mock.patch("tools.audit_realizer_capabilities.subprocess.run", return_value=completed):
            self.assertIsNone(_git_commit())


if __name__ == "__main__":
    unittest.main()
