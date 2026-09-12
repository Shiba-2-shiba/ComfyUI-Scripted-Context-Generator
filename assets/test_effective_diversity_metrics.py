"""Numerical contracts for the read-only effective-diversity audit."""

import copy
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.effective_diversity_metrics import (  # noqa: E402
    axis_coverage,
    max_consecutive_run,
    metric_prefixes,
    normalize_prompt,
    repetition_metrics,
    semantic_uniqueness,
    syntax_entropy,
)
from tools.workflow_prompt_runner import canonical_json_bytes  # noqa: E402


class TestMetricPrefixes(unittest.TestCase):
    def test_only_available_prefixes_and_actual_sample_count_are_reported(self):
        for count, expected in (
            (0, [0]), (4, [4]), (127, [127]), (128, [128]), (129, [128, 129]),
            (2048, [128, 512, 2048]), (8192, [128, 512, 2048, 8192]),
            (8193, [128, 512, 2048, 8192, 8193]),
        ):
            with self.subTest(count=count):
                self.assertEqual(metric_prefixes(count), expected)

    def test_invalid_counts_are_rejected(self):
        for count in (-1, True, 1.5, "128"):
            with self.subTest(count=count), self.assertRaises(ValueError):
                metric_prefixes(count)


class TestPromptNormalization(unittest.TestCase):
    def test_aliases_case_punctuation_and_whitespace(self):
        self.assertEqual(normalize_prompt("A woman reads, quietly."), "a girl reads quietly")
        self.assertEqual(normalize_prompt("  a GIRL\treads\nquietly! "), "a girl reads quietly")
        for alias in ("1woman", "1lady", "1female", "1girl", "woman", "women", "lady", "female"):
            with self.subTest(alias=alias):
                self.assertEqual(normalize_prompt(f"A {alias} reads."), "a girl reads")

    def test_unicode_punctuation_and_nfc(self):
        self.assertEqual(
            normalize_prompt('A girl\u2019s \u201cCafe\u0301\u201d\u2014sign; 2:3!?'),
            'a girl\'s "caf\u00e9"-sign 2 3',
        )
        self.assertEqual(normalize_prompt("'hi' \u2018hi\u2019 - \u2013"), "'hi' 'hi' - -")

    def test_negation_word_order_and_non_alias_words_are_preserved(self):
        self.assertNotEqual(normalize_prompt("a girl doesn't read"), normalize_prompt("a girl does read"))
        self.assertNotEqual(normalize_prompt("a girl reads a book"), normalize_prompt("a book reads a girl"))
        self.assertEqual(normalize_prompt("ladybug womanhood x1girl"), "ladybug womanhood x1girl")
        self.assertEqual(normalize_prompt("well-read 24"), "well-read 24")

    def test_invalid_prompt_is_rejected(self):
        for prompt in (None, 1, "", " \n\t"):
            with self.subTest(prompt=prompt), self.assertRaises(ValueError):
                normalize_prompt(prompt)

    def test_alias_reuse_preserves_repeated_subject_words(self):
        self.assertEqual(normalize_prompt("A girl girl reads."), "a girl girl reads")
        self.assertEqual(normalize_prompt("A woman girl reads."), "a girl girl reads")
        self.assertNotEqual(normalize_prompt("A girl girl reads."), normalize_prompt("A girl reads."))


class TestSemanticUniqueness(unittest.TestCase):
    def test_empty_and_all_missing_signatures(self):
        self.assertEqual(semantic_uniqueness([]), {
            "sample_count": 0, "valid_count": 0, "missing_count": 0, "unique_count": 0, "rate": 0.0,
        })
        self.assertEqual(semantic_uniqueness([None, None]), {
            "sample_count": 2, "valid_count": 0, "missing_count": 2, "unique_count": 0, "rate": 0.0,
        })

    def test_duplicate_and_missing_signatures_use_all_samples_as_denominator(self):
        signature = {"subject": "student", "object": None}
        self.assertEqual(semantic_uniqueness([signature, dict(signature), None, None]), {
            "sample_count": 4, "valid_count": 2, "missing_count": 2, "unique_count": 1, "rate": 0.25,
        })

    def test_canonical_object_key_order_and_input_order_do_not_change_uniqueness(self):
        first = {"subject": "student", "object": "book"}
        same = {"object": "book", "subject": "student"}
        changed = {"subject": "student", "object": "phone"}
        expected = {"sample_count": 3, "valid_count": 3, "missing_count": 0, "unique_count": 2, "rate": 0.666667}
        self.assertEqual(semantic_uniqueness([first, same, changed]), expected)
        self.assertEqual(semantic_uniqueness([changed, same, first]), expected)

    def test_invalid_signature_containers_and_nonfinite_numbers_are_rejected(self):
        for signature in ("prompt prose", [], {"value": math.nan}, {"value": math.inf}):
            with self.subTest(signature=signature), self.assertRaises(ValueError):
                semantic_uniqueness([signature])

    def test_unknown_and_known_empty_signature_fields_stay_distinct(self):
        result = semantic_uniqueness([{"garnish": None}, {"garnish": []}])
        self.assertEqual(result["unique_count"], 2)


class TestAxisCoverage(unittest.TestCase):
    def test_empty_reference_is_unmeasured(self):
        self.assertEqual(axis_coverage([], []), {
            "observed_unique_count": 0, "covered_unique_count": 0, "reference_count": 0,
            "missing_count": 0, "out_of_reference_values": [], "rate": None,
        })
        self.assertEqual(axis_coverage([], ["a"])["rate"], 0.0)
        self.assertIsNone(axis_coverage(["a"], [])["rate"])

    def test_reference_intersection_and_missingness_are_explicit(self):
        self.assertEqual(axis_coverage(["a", "a", "b", "x", None], ["a", "b", "c", "d"]), {
            "observed_unique_count": 3, "covered_unique_count": 2, "reference_count": 4,
            "missing_count": 1, "out_of_reference_values": ["x"], "rate": 0.5,
        })

    def test_multivalue_duplicates_known_empty_and_unknown(self):
        self.assertEqual(axis_coverage([["hands", "hands", "gaze"], [], None], ["gaze", "hands", "breath"]), {
            "observed_unique_count": 2, "covered_unique_count": 2, "reference_count": 3,
            "missing_count": 1, "out_of_reference_values": [], "rate": 0.666667,
        })

    def test_reference_and_observation_order_have_canonical_output(self):
        first = axis_coverage([["z", "b"], "a"], ["c", "a", "c"])
        second = axis_coverage(["a", ["b", "z"]], ["a", "c"])
        self.assertEqual(first["out_of_reference_values"], ["b", "z"])
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))

    def test_invalid_categories_are_not_counted_as_missing_or_novel_values(self):
        for value in ("", " ", 4, [None], [""], {"a": "b"}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                axis_coverage([value], ["a"])
        for value in (None, "", 1):
            with self.subTest(reference=value), self.assertRaises(ValueError):
                axis_coverage([], [value])


class TestSyntaxMetrics(unittest.TestCase):
    def test_empty_input_and_zero_bins(self):
        self.assertEqual(syntax_entropy([], []), {
            "sample_count": 0, "valid_count": 0, "missing_count": 0, "active_family_count": 0,
            "family_counts": {}, "raw_entropy": 0.0, "normalized_entropy": 0.0, "dominant_family_share": 0.0,
        })
        result = syntax_entropy([None, None], ["b", "a"])
        self.assertEqual(result["family_counts"], {"a": 0, "b": 0})
        self.assertEqual(result["missing_count"], 2)
        self.assertEqual(result["raw_entropy"], 0.0)

    def test_single_family_and_unobserved_active_family(self):
        for active in (["a"], ["b", "a"]):
            result = syntax_entropy(["a"] * 4, active)
            self.assertEqual(result["raw_entropy"], 0.0)
            self.assertEqual(result["normalized_entropy"], 0.0)
            self.assertEqual(result["dominant_family_share"], 1.0)

    def test_balanced_skewed_and_declared_denominator(self):
        balanced = syntax_entropy(["a", "b", "a", "b"], ["a", "b"])
        self.assertEqual(balanced["raw_entropy"], 1.0)
        self.assertEqual(balanced["normalized_entropy"], 1.0)
        self.assertEqual(balanced["dominant_family_share"], 0.5)
        skewed = syntax_entropy(["a", "a", "a", "b"], ["a", "b"])
        self.assertEqual(skewed["raw_entropy"], 0.811278)
        self.assertEqual(skewed["normalized_entropy"], 0.811278)
        self.assertEqual(skewed["dominant_family_share"], 0.75)
        larger = syntax_entropy(["a", "b"], ["a", "b", "c", "d"])
        self.assertEqual(larger["active_family_count"], 4)
        self.assertEqual(larger["normalized_entropy"], 0.5)

    def test_missing_values_do_not_enter_entropy_denominator(self):
        result = syntax_entropy(["a", "a", None, "a"], ["a", "b"])
        self.assertEqual(result["valid_count"], 3)
        self.assertEqual(result["missing_count"], 1)
        self.assertEqual(result["dominant_family_share"], 1.0)

    def test_deterministic_family_order(self):
        first = syntax_entropy(["b", "a", "a"], ["c", "b", "a"])
        second = syntax_entropy(["a", "a", "b"], ["b", "a", "c", "a"])
        self.assertEqual(list(first["family_counts"]), ["a", "b", "c"])
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))

    def test_unknown_and_invalid_families_are_rejected(self):
        for families, active in ((["b"], ["a"]), (["a"], []), ([""], ["a"]), ([1], ["a"]), ([], [None])):
            with self.subTest(families=families, active=active), self.assertRaises(ValueError):
                syntax_entropy(families, active)

    def test_consecutive_runs_preserve_sequence_and_break_at_null(self):
        for values, expected in (([], 0), ([None, None], 0), (["a"], 1), (["a"] * 4, 4),
                                 (["a", "b", "a", "b"], 1), (["a", "a", None, "a"], 2)):
            with self.subTest(values=values):
                self.assertEqual(max_consecutive_run(values), expected)
        with self.assertRaises(ValueError):
            max_consecutive_run([""])


class TestRepetitionMetrics(unittest.TestCase):
    def test_empty_sequences(self):
        self.assertEqual(repetition_metrics([], [], [], [], []), {
            "sample_count": 0, "exact_prompt_duplicate_rate": 0.0, "normalized_prompt_duplicate_rate": 0.0,
            "semantic_core_duplicate_rate": 0.0, "semantic_frame_duplicate_rate": 0.0,
            "max_consecutive_same_action_family": 0, "max_consecutive_same_syntax_family": 0,
        })

    def test_surface_and_semantic_duplicates_have_separate_denominators(self):
        core = {"subject": "student", "verb": "reading"}
        frame = {**core, "mood": "focused"}
        result = repetition_metrics(
            ["A woman reads, quietly.", "a girl reads quietly!", "a girl reads quietly!", "A girl writes."],
            [core, core, None, None], [frame, {**frame, "mood": "relaxed"}, None, None],
            ["reading", "reading", None, "writing"], ["a", "a", None, "a"],
        )
        self.assertEqual(result, {
            "sample_count": 4, "exact_prompt_duplicate_rate": 0.25, "normalized_prompt_duplicate_rate": 0.5,
            "semantic_core_duplicate_rate": 0.25, "semantic_frame_duplicate_rate": 0.0,
            "max_consecutive_same_action_family": 2, "max_consecutive_same_syntax_family": 2,
        })

    def test_all_identical_and_all_missing_semantics(self):
        for signatures, expected in (([{"x": "a"}] * 4, 0.75), ([None] * 4, 0.0)):
            result = repetition_metrics(["a"] * 4, signatures, signatures, ["a"] * 4, ["a"] * 4)
            self.assertEqual(result["exact_prompt_duplicate_rate"], 0.75)
            self.assertEqual(result["semantic_core_duplicate_rate"], expected)
            self.assertEqual(result["semantic_frame_duplicate_rate"], expected)

    def test_misaligned_input_lengths_are_rejected(self):
        for index in range(5):
            values = [["a"], [{"x": "a"}], [{"x": "a"}], ["a"], ["a"]]
            values[index] = []
            with self.subTest(index=index), self.assertRaises(ValueError):
                repetition_metrics(*values)

    def test_inputs_are_not_mutated(self):
        values = [["A woman reads."], [{"x": "a"}], [{"families": ["gaze", "hands"]}], ["a"], ["a"]]
        before = copy.deepcopy(values)
        first = repetition_metrics(*values)
        self.assertEqual(repetition_metrics(*values), first)
        self.assertEqual(values, before)
        axis_values, reference = [["b", "a", "b"], None], ["b", "a", "b"]
        before = copy.deepcopy((axis_values, reference))
        axis_coverage(axis_values, reference)
        self.assertEqual((axis_values, reference), before)

    def test_empty_prompts_cannot_pass_as_valid_duplicates(self):
        for prompt in (None, 3, "", " \t"):
            with self.subTest(prompt=prompt), self.assertRaises(ValueError):
                repetition_metrics([prompt], [None], [None], [None], [None])

    def test_process_hash_seed_does_not_change_canonical_aggregation(self):
        script = """
from tools.effective_diversity_metrics import axis_coverage, semantic_uniqueness, syntax_entropy
from tools.workflow_prompt_runner import canonical_json_bytes
result = {
    'coverage': axis_coverage([list({'gaze', 'hands', 'breath'})], list({'gaze', 'hands'})),
    'unique': semantic_uniqueness([dict.fromkeys({'subject', 'location'}, 'a')]),
    'syntax': syntax_entropy(['a', 'a', 'b'], list({'a', 'b', 'c'})),
}
print(canonical_json_bytes(result).decode('utf-8'), end='')
"""
        outputs = [
            subprocess.check_output(
                [sys.executable, "-c", script], cwd=ROOT,
                env={**os.environ, "PYTHONHASHSEED": hash_seed},
            )
            for hash_seed in ("1", "999")
        ]
        self.assertEqual(outputs[0], outputs[1])


if __name__ == "__main__":
    unittest.main()
