"""Signature accounting must not alter ordinary runtime or count seeds as rescues."""
import copy
import random
import unittest

from assets.test_r43_reachability_audit import row
from assets.test_r43_real_graph_placement import real_snapshot
from core.schema import PromptContext
from pipeline.prompt_orchestrator import build_prompt_from_context
from tools.audit_realizer_reachability import summarize
from tools.realizer_coverage_signatures import coverage_signature_hash
from tools.realizer_reachability_diagnostics import diagnose_snapshot


class TestReachabilityAccounting(unittest.TestCase):
    def test_diagnosis_keeps_prompt_context_family_and_rng_unchanged(self):
        context = PromptContext.from_dict({'subj': 'a solo girl', 'loc': 'station platform',
                                          'action': 'checking a transit card'})
        for mode in (True, False):
            for seed in (0, 3, 7, 15):
                with self.subTest(mode=mode, seed=seed):
                    before_context, before_prompt = build_prompt_from_context(context, '', mode, seed)
                    captured = []
                    after_context, after_prompt = build_prompt_from_context(
                        context, '', mode, seed, audit_sink=captured.append)
                    snapshot = captured[0]
                    before_snapshot = copy.deepcopy(snapshot)
                    before_selected_family = (snapshot['bridge'] or {}).get('selected')
                    before_rng_state = random.getstate()
                    result = diagnose_snapshot(snapshot)
                    self.assertEqual(before_prompt, after_prompt)
                    self.assertEqual(before_context.to_dict(), after_context.to_dict())
                    self.assertEqual(before_selected_family, (snapshot['bridge'] or {}).get('selected'))
                    self.assertEqual(before_rng_state, random.getstate())
                    self.assertEqual(before_snapshot, snapshot)
                    self.assertIn('coverage_signature', result)
                    self.assertEqual(result['coverage_signature_sha256'],
                                     coverage_signature_hash(result['coverage_signature']))

    def test_real_graph_signature_reproves_six_families_without_changing_ordinary_family(self):
        snapshot = real_snapshot()
        before, rng = copy.deepcopy(snapshot), random.getstate()
        result = diagnose_snapshot(snapshot)
        self.assertEqual(result['coverage_signature']['proof_basis'], 'common_reconstructed')
        self.assertEqual(len(result['coverage_signature']['eligible_families']), 6)
        self.assertEqual(snapshot, before)
        self.assertEqual(random.getstate(), rng)

    def test_signature_counts_are_seed_family_rows_with_sorted_capped_examples(self):
        rows = []
        signature = {'schema_version': 'realizer-coverage-signature/v1', 'blocked_domains': ['action']}
        other = {**signature, 'blocked_domains': ['scene']}
        for seed in range(6):
            value = row(seed, ['action.unknown'])
            value['families']['action_lead_subject_scene'] = copy.deepcopy(value['families']['subject_action_scene'])
            value['coverage_signature'] = signature if seed < 5 else other
            value['coverage_signature_sha256'] = coverage_signature_hash(value['coverage_signature'])
            rows.append(value)
        before = copy.deepcopy(rows)
        result = summarize(rows)
        self.assertEqual(rows, before)
        self.assertEqual(summarize(list(reversed(rows))), result)
        groups = result['coverage_signatures']
        self.assertEqual([group['count'] for group in groups], [10, 2])
        self.assertEqual(groups[0]['blocked_domains'], ['action'])
        self.assertEqual(groups[0]['example_seed_family_rows'], [
            {'run_seed': seed, 'family': family} for seed in range(4)
            for family in ('action_lead_subject_scene', 'subject_action_scene')])

    def test_equal_signature_counts_use_hash_tiebreak(self):
        rows = [row(2, []), row(1, [])]
        for value, blocked in zip(rows, (['scene'], ['action'])):
            value['coverage_signature'] = {'blocked_domains': blocked}
            value['coverage_signature_sha256'] = coverage_signature_hash(value['coverage_signature'])
        groups = summarize(rows)['coverage_signatures']
        self.assertEqual([group['sha256'] for group in groups],
                         sorted(value['coverage_signature_sha256'] for value in rows))

    def test_examples_sort_family_names_across_rows_with_the_same_seed(self):
        rows = [row(1, []), row(1, [])]
        rows[1]['families']['action_lead_subject_scene'] = rows[1]['families'].pop('subject_action_scene')
        for value in rows:
            value['coverage_signature'] = {'blocked_domains': []}
            value['coverage_signature_sha256'] = coverage_signature_hash(value['coverage_signature'])
        result = summarize(rows)['coverage_signatures']
        self.assertEqual(result, summarize(list(reversed(rows)))['coverage_signatures'])
        self.assertEqual(result[0]['example_seed_family_rows'], [
            {'run_seed': 1, 'family': 'action_lead_subject_scene'},
            {'run_seed': 1, 'family': 'subject_action_scene'}])


if __name__ == '__main__':
    unittest.main()
