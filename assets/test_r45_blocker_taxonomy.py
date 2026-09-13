"""Diagnostic blocker normalization and R44 selector compatibility contracts."""
from copy import deepcopy
import unittest

from assets.test_r44_packet_selection import rows_for
from tools.realizer_blocker_taxonomy import (
    blocker_domain, canonical_blocker_id, is_hard_excluded, is_repairable_blocker,
)
from tools.select_r44_coverage_packets import select_packets


class TestBlockerTaxonomy(unittest.TestCase):
    def test_canonicalizes_legacy_family_delimiters(self):
        pairs = {
            'family.required_fact_not_true.scene_lead_safe':
                'family.required_fact_not_true:scene_lead_safe',
            'family.forbidden_fact_not_false.scene_action_overlap':
                'family.forbidden_fact_not_false:scene_action_overlap',
            'family.missing_slot.scene': 'family.missing_slot:scene',
        }
        for source, expected in pairs.items():
            with self.subTest(source=source):
                self.assertEqual(canonical_blocker_id(source), expected)
                self.assertEqual(canonical_blocker_id(expected), expected)
                self.assertEqual(blocker_domain(source), blocker_domain(expected))
                self.assertTrue(is_repairable_blocker(source))

    def test_native_colon_family_ids_are_repairable(self):
        ids = (
            'family.required_fact_not_true:scene_lead_safe',
            'family.forbidden_fact_not_false:scene_action_overlap',
            'family.missing_slot:scene',
        )
        self.assertTrue(all(is_repairable_blocker(value) for value in ids))

    def test_hard_binding_and_policy_failures_remain_excluded(self):
        ids = (
            'policy.conflict', 'binding.current_input_mismatch',
            'binding.replay_mismatch', 'binding.history_stale',
            'transport.runtime_inputs_missing', 'render.proof_constructor_mismatch',
            'action.binding_mismatch', 'scene.stale_source',
        )
        for value in ids:
            with self.subTest(value=value):
                self.assertTrue(is_hard_excluded(value))
                self.assertFalse(is_repairable_blocker(value))

    def test_domain_mapping_is_explicit(self):
        expected = {
            'action.leaf_grammar_unknown': 'action',
            'scene.source_or_grammar_unknown': 'scene',
            'family.required_fact_not_true:same_subject_attachment_safe': 'action',
            'family.required_fact_not_true:scene_lead_safe': 'scene',
            'family.forbidden_fact_not_false:scene_action_overlap': 'action',
            'family.required_fact_not_true:scene_action_nonduplicative': 'action',
            'family.scene_overlap_unknown': 'action',
            'family.action_lead_subject_unknown': 'action',
            'family.frame_unproved': 'action',
            'family.independent_subject': 'action',
            'family.missing_slot:subject': 'subject',
            'family.missing_slot:adjunct': 'action',
            'family.missing_slot:predicate': 'action',
            'family.missing_slot:scene': 'scene',
            'policy.conflict': None,
            'family.required_fact_not_true:unrecognized_fact': None,
            'family.missing_slot:unrecognized_slot': None,
            'family.unrecognized': None,
        }
        for identifier, domain in expected.items():
            with self.subTest(identifier=identifier):
                self.assertEqual(blocker_domain(identifier), domain)
                if domain is None:
                    self.assertFalse(is_repairable_blocker(identifier))

    def test_rejects_empty_and_nonstring_identifiers(self):
        for value in ('', None, 1, []):
            with self.subTest(value=value), self.assertRaises(ValueError):
                canonical_blocker_id(value)


class TestR44SelectorCanonicalTaxonomy(unittest.TestCase):
    def test_colon_family_blocker_can_participate_in_repairable_packet(self):
        rows = rows_for(
            range(4),
            blockers=(
                'scene.placement_constructor_unknown',
                'family.required_fact_not_true:scene_lead_safe',
            ),
            domains=('scene',),
        )
        packets = select_packets(rows)
        self.assertEqual(len(packets), 1)
        self.assertIn('family.required_fact_not_true:scene_lead_safe',
                      packets[0]['repairable_blocker_ids'])

    def test_mixed_delimiters_deduplicate_without_mutating_forensic_rows(self):
        rows = rows_for(range(4), blockers=(
            'family.required_fact_not_true.scene_lead_safe',
            'family.required_fact_not_true:scene_lead_safe',
        ), domains=('scene',))
        saved = deepcopy(rows)
        packets = select_packets(rows)
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0]['repairable_blocker_ids'],
                         ['family.required_fact_not_true:scene_lead_safe'])
        self.assertEqual(rows, saved)


if __name__ == '__main__':
    unittest.main()
