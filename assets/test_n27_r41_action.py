"""Producer role and bounded valency proofs for new complete intake actions."""
import json
from pathlib import Path
import unittest

from pipeline.action_renderer import RenderedActionPart, render_action_slots
from pipeline.v2_leaf_grammar import action_part_facts, derive_action_grammar, predicate
from pipeline.v2_structural_evidence import build_structural_evidence
from core.schema import ActionFrame


class TestR41Action(unittest.TestCase):
    def test_original_intake_frames_preserve_ambiguous_place(self):
        cases = json.loads((Path(__file__).parent / 'fixtures/n27_r41_real_cases.json').read_text())
        for case in cases:
            frame = case['frame']
            before = json.dumps(frame, sort_keys=True)
            grammar = derive_action_grammar(build_structural_evidence(frame, frame['legacy_text']))
            self.assertIs(grammar.frame_predicate_safe, True, case['run_seed'])
            self.assertIs(grammar.same_subject_attachment_safe, True)
            self.assertIs(grammar.independent_action_subject, False)
            self.assertIsNone(grammar.no_place_reference)
            self.assertEqual(json.dumps(frame, sort_keys=True), before)

    def test_reviewed_legacy_leaves_require_source_roles(self):
        for slot, value in [('gaze_target', 'looking off for a quiet second'),
                            ('purpose_clause', 'letting the pause settle properly'),
                            ('optional_micro_action', 'letting the pause settle properly'),
                            ('social_clause', 'meeting the viewer with a quiet look')]:
            self.assertTrue(action_part_facts(RenderedActionPart(slot, value)).known)
            self.assertFalse(action_part_facts(RenderedActionPart('hand_action', value)).known)
        self.assertFalse(action_part_facts(RenderedActionPart(
            'purpose_clause', 'letting the pause settle properly and the viewer waits')).known)

    def test_unseen_bounded_compositions(self):
        for slot, value in [('purpose_clause', 'holding onto her place a bit longer'),
                            ('purpose_clause', 'while holding onto her place a little longer'),
                            ('purpose_clause', 'before she holds onto her place longer'),
                            ('optional_micro_action', 'holding onto her place longer'),
                            ('social_clause', 'as if responding to the viewer'),
                            ('social_clause', 'as if responding quietly to the viewer'),
                            ('social_clause', 'as if she responds directly to the viewer')]:
            facts = action_part_facts(RenderedActionPart(slot, value))
            self.assertTrue(facts.known, value)
            self.assertIs(facts.same_subject, True)
            self.assertEqual(facts.owner_kind, 'protagonist')
            if 'her place' in value:
                self.assertIsNone(facts.no_place_reference)
            self.assertFalse(predicate(value), 'Legacy predicate API must remain unchanged')

    def test_adversarial_roles_subjects_ownership_and_consumption(self):
        cases = [('purpose_clause', 'holding onto his place a little longer'),
                 ('purpose_clause', 'holding onto their place a little longer'),
                 ('purpose_clause', 'holding onto her home a little longer'),
                 ('purpose_clause', 'holding onto her place a little longer and someone waits'),
                 ('purpose_clause', 'while he holds onto her place longer'),
                 ('purpose_clause', 'without she holds onto her place longer'),
                 ('purpose_clause', 'holding onto her place a little longer mysteriously'),
                 ('gaze_target', 'holding onto her place a little longer'),
                 ('hand_action', 'her hands holding onto her place a little longer'),
                 ('purpose_clause', 'as if responding directly to the viewer'),
                 ('social_clause', 'as if he responds directly to the viewer'),
                 ('social_clause', 'as if the viewer responds directly to her'),
                 ('social_clause', 'as if responding directly to someone'),
                 ('social_clause', 'as if responding directly to the viewer and her friend'),
                 ('social_clause', 'as responding directly to the viewer'),
                 ('social_clause', 'as if if responding directly to the viewer'),
                 ('social_clause', 'as if responds directly to the viewer'),
                 ('social_clause', 'as if responding directly to the viewer suddenly'),
                 ('social_clause', 'as if while responding directly to the viewer')]
        for slot, value in cases:
            with self.subTest(slot=slot, value=value):
                facts = action_part_facts(RenderedActionPart(slot, value))
                self.assertFalse(facts.known)
                self.assertIsNone(facts.same_subject)
        for value in ('holding onto her place longer', 'as if responding to the viewer'):
            self.assertFalse(action_part_facts(RenderedActionPart('primary_action', value), primary=True).known)

    def test_one_unknown_leaf_keeps_whole_action_unknown(self):
        slots = {'primary_action': 'holding the clipboard',
                 'purpose_clause': 'holding onto her place a little longer',
                 'social_clause': 'as if responding directly to the viewer inexplicably'}
        action = render_action_slots(slots, activity_first=True)
        facts = derive_action_grammar(build_structural_evidence(
            ActionFrame.from_slots(slots, legacy_text=action), action))
        self.assertIsNone(facts.frame_predicate_safe)
        self.assertIsNone(facts.same_subject_attachment_safe)
        self.assertIsNone(facts.independent_action_subject)
        self.assertIsNone(facts.no_place_reference)


if __name__ == '__main__':
    unittest.main()
