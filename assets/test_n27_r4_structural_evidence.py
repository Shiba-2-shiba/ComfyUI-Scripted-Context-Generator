"""Exact producer replay is runtime evidence, never a serialized promise."""
import copy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import unittest

from core.schema import ActionFrame
from pipeline.action_renderer import render_action_slots
from pipeline.v2_structural_evidence import build_structural_evidence

CASES = json.loads((Path(__file__).parent / 'fixtures/n27_r4_productive_cases.json').read_text())


class TestStructuralEvidence(unittest.TestCase):
    def test_real_workflow_exact_replay_and_no_mutation(self):
        for case in CASES:
            frame = ActionFrame.from_dict(case['frame'])
            before = frame.to_dict()
            evidence = build_structural_evidence(frame, frame.legacy_text)
            self.assertIsNotNone(evidence, case['run_seed'])
            self.assertTrue(evidence.exact_replay)
            self.assertEqual(', '.join(p.text for p in evidence.emitted_parts), frame.legacy_text)
            self.assertEqual(frame.to_dict(), before)
            with self.assertRaises(FrozenInstanceError):
                evidence.exact_replay = False

    def test_stale_current_slots_version_and_missing_source(self):
        case = CASES[0]
        self.assertIsNone(build_structural_evidence(case['frame'], case['frame']['legacy_text'] + ' now'))
        for key, value in [('schema_version', 'action-frame/v2'), ('legacy_slots', {}), ('legacy_slots', None)]:
            frame = {**case['frame'], key: value}
            self.assertIsNone(build_structural_evidence(frame, case['frame']['legacy_text']))
        frame = copy.deepcopy(case['frame'])
        frame['legacy_slots']['primary_action'] = 'holding the clipboard'
        self.assertIsNone(build_structural_evidence(frame, frame['legacy_text']))

    def test_modes_same_trace_or_conflicting_ownership(self):
        slots = {'purpose_clause': 'holding the clipboard'}
        frame = ActionFrame.from_slots(slots, legacy_text=render_action_slots(slots))
        self.assertIsNone(build_structural_evidence(frame, frame.legacy_text).activity_first)
        slots['primary_action'] = slots['purpose_clause']
        frame = ActionFrame.from_slots(slots, legacy_text=render_action_slots(slots))
        self.assertIsNone(build_structural_evidence(frame, frame.legacy_text))

    def test_whitespace_only_normalization_preserves_case_and_negation(self):
        frame = copy.deepcopy(CASES[0]['frame'])
        self.assertIsNotNone(build_structural_evidence(frame, '  ' + frame['legacy_text'].replace(' ', '  ') + '  '))
        self.assertIsNone(build_structural_evidence(frame, frame['legacy_text'].upper()))
        self.assertIsNone(build_structural_evidence(frame, 'not ' + frame['legacy_text']))


if __name__ == '__main__':
    unittest.main()
