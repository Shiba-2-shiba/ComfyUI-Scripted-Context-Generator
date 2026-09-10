"""Bounded action grammar and owned body-state realization regressions."""
from dataclasses import replace
import json
from pathlib import Path
import unittest

from core.schema import ActionFrame
from pipeline.action_renderer import RenderedActionPart, render_action_slots
from pipeline import v2_leaf_grammar as grammar
from pipeline.v2_structural_evidence import build_structural_evidence


def evidence_for(primary, **slots):
    slots = {'primary_action': primary, **slots}
    action = render_action_slots(slots, activity_first=True)
    return build_structural_evidence(ActionFrame.from_slots(slots, legacy_text=action), action)


class TestR42Action(unittest.TestCase):
    def test_original_frames_and_materialized_words(self):
        cases = json.loads((Path(__file__).parent / 'fixtures/n27_r42_real_cases.json').read_text())
        for case in cases:
            frame = case['frame']
            before = json.dumps(frame, sort_keys=True)
            evidence = build_structural_evidence(frame, frame['legacy_text'])
            facts = grammar.derive_action_grammar(evidence)
            self.assertIs(facts.frame_predicate_safe, True, case['run_seed'])
            self.assertIs(facts.independent_action_subject, False)
            if case['run_seed'] == 88:
                self.assertIs(facts.same_subject_attachment_safe, False)
                self.assertIsNone(facts.no_place_reference)
                self.assertEqual(grammar.materialize_action_parts(evidence),
                                 frame['legacy_text'].replace(', eyes fixed ', ', with eyes fixed '))
            else:
                self.assertIs(facts.same_subject_attachment_safe, True)
                self.assertEqual(grammar.materialize_action_parts(evidence), frame['legacy_text'])
            if case['run_seed'] == 234:
                self.assertIs(facts.no_place_reference, True)
            if case['run_seed'] in {94, 338}:
                self.assertEqual(facts.main_verb, 'standing')
                self.assertEqual(frame['main_verb'], 'tidying')
                self.assertEqual(grammar.verified_primary_verbs(evidence), ('standing', 'tidying'))
            self.assertEqual(json.dumps(frame, sort_keys=True), before)

    def test_seated_locative_and_reading_purpose(self):
        for value in ('sitting in the audience seats', 'sitting in the seats'):
            facts = grammar.action_part_facts(RenderedActionPart('primary_action', value), primary=True)
            self.assertTrue(facts.known, value)
            self.assertIsNone(facts.no_place_reference)
        for value in ('leaning in to read a tiny label', 'leaning closer to read the small label'):
            facts = grammar.action_part_facts(RenderedActionPart('primary_action', value), primary=True)
            self.assertTrue(facts.known, value)
            self.assertIs(facts.no_place_reference, True)

    def test_body_subject_is_owned_but_not_actor_subject(self):
        for value in ('eyes fixed on what needs to happen next', 'her eyes fixed on what needs to happen next'):
            leaf = grammar.action_part_facts(RenderedActionPart('gaze_target', value))
            self.assertTrue(leaf.known)
            self.assertEqual(leaf.owner_kind, 'protagonist_body_part')
            self.assertEqual(leaf.attachment_kind, 'with_absolute')
            self.assertIs(leaf.same_subject, False)
            evidence = evidence_for('holding the clipboard', gaze_target=value)
            facts = grammar.derive_action_grammar(evidence)
            self.assertIs(facts.frame_predicate_safe, True)
            self.assertIs(facts.same_subject_attachment_safe, False)
            self.assertIs(facts.independent_action_subject, False)
            self.assertEqual(grammar.materialize_action_parts(evidence), 'holding the clipboard, with ' + value)

    def test_unknown_foreign_subject_negation_and_dangling_reference(self):
        cases = [
            ('gaze_target', 'his eyes fixed on what needs to happen next'),
            ('gaze_target', 'the viewer eyes fixed on what needs to happen next'),
            ('gaze_target', 'eyes not fixed on what needs to happen next'),
            ('gaze_target', 'eyes fixed on it'),
            ('gaze_target', 'eyes fixed on what she needs to happen next'),
            ('gaze_target', 'eyes fixed on what needs to happen next unexpectedly'),
            ('gaze_target', 'eyes fixed on what needs to happen next and she waits'),
            ('gaze_target', 'eyes fixed on what needs to happen next, she waits'),
            ('gaze_target', 'with eyes fixed on what needs to happen next'),
            ('hand_action', 'eyes fixed on what needs to happen next'),
            ('posture', 'eyes fixed on what needs to happen next'),
            ('foreign_slot', 'eyes fixed on what needs to happen next'),
            ('primary_action', 'leaning in to read it'),
            ('primary_action', 'leaning in to read a tiny label for him'),
            ('primary_action', 'leaning in to not read a tiny label'),
            ('primary_action', 'sitting in the audience seats beside him'),
            ('primary_action', 'sitting in her seats'),
            ('primary_action', 'she sits in the audience seats'),
            ('gaze_target', 'she checks the clipboard'),
        ]
        for slot, value in cases:
            with self.subTest(slot=slot, value=value):
                self.assertFalse(grammar.action_part_facts(
                    RenderedActionPart(slot, value), primary=slot == 'primary_action').known)
        self.assertIsNone(grammar.materialize_action_parts(evidence_for(
            'holding the clipboard', gaze_target='eyes fixed on it')))

    def test_existing_body_clause_is_not_licensed_absolute(self):
        evidence = evidence_for('holding the clipboard', gaze_target='eyes following the next thing')
        facts = grammar.derive_action_grammar(evidence)
        self.assertIs(facts.independent_action_subject, True)
        self.assertIs(facts.same_subject_attachment_safe, False)
        self.assertIsNone(grammar.materialize_action_parts(evidence))

    def test_compound_predicates_require_complete_known_heads(self):
        evidence = evidence_for('standing and tidying the small area around her')
        self.assertEqual(grammar.verified_primary_verbs(evidence), ('standing', 'tidying'))
        self.assertEqual(grammar.verified_primary_verbs(evidence_for('holding the clipboard')), ('holding',))
        for value in ('standing and doing something unknown', 'standing and not tidying the small area around her',
                      'standing and she tidies the small area around her', 'standing and tidying it',
                      'standing and tidying the small area around her, she waits'):
            self.assertEqual(grammar.verified_primary_verbs(evidence_for(value)), (), value)
        self.assertEqual(grammar.verified_primary_verbs(replace(evidence, exact_replay=False)), ())
        self.assertIsNone(grammar.materialize_action_parts(replace(evidence, exact_replay=False)))
        self.assertEqual(grammar.verified_primary_verbs(None), ())
        self.assertIsNone(grammar.materialize_action_parts(None))


if __name__ == '__main__':
    unittest.main()
