"""Bounded leaf proofs preserve subjects, polarity and source ownership."""
import unittest

from assets.test_n27_r4_structural_evidence import CASES
from pipeline.action_renderer import RenderedActionPart, render_action_slots
from pipeline.v2_leaf_grammar import action_part_facts, derive_action_grammar
from pipeline.v2_structural_evidence import build_structural_evidence
from core.schema import ActionFrame


class TestSubordinateGrammar(unittest.TestCase):
    def test_real_workflow_leaf_fixtures(self):
        for case in CASES:
            for expected in case['leaf_expectations']:
                part = RenderedActionPart(expected['slot'], case['frame']['legacy_slots'][expected['slot']])
                fact = action_part_facts(part, primary=expected.get('primary', False))
                self.assertTrue(fact.known, (case['run_seed'], part))
                self.assertEqual(fact.owner_kind, expected['owner'])

    def test_productive_shared_subordinate_and_finite(self):
        for text in ('while holding the clipboard', 'without checking the bolt',
                     'after adjusting a nut', 'before standing beside the hood',
                     'while she checks the bolt', 'before the next task',
                     'walking slowly', 'leaning closer', 'keeping herself steady',
                     'not checking the bolt', 'never checking the bolt'):
            fact = action_part_facts(RenderedActionPart('progress_clause', text))
            self.assertTrue(fact.known, text)
            self.assertTrue(fact.same_subject, text)
        fact = action_part_facts(RenderedActionPart('primary_action', 'checks the bolt'), primary=True)
        self.assertTrue(fact.known)
        self.assertEqual(fact.surface_kind, 'clause')
        self.assertEqual(fact.main_verb, 'checking')

    def test_external_and_body_subjects_are_not_shared(self):
        for text in ('her eyes following the detail', 'her hands holding the clipboard',
                     'her fingers holding the bolt', 'eyes following the detail'):
            fact = action_part_facts(RenderedActionPart('gaze_target', text))
            self.assertTrue(fact.known, text)
            self.assertEqual(fact.owner_kind, 'protagonist_body_part')
            self.assertFalse(fact.same_subject)
        for text in ('because the lights change', 'as the task ends', 'after the shift ends'):
            fact = action_part_facts(RenderedActionPart('time_or_weather', text))
            self.assertTrue(fact.known, text)
            self.assertEqual(fact.owner_kind, 'scene_event')
            self.assertFalse(fact.same_subject)

    def test_unknowns_do_not_become_positive_evidence(self):
        for slot, text in [('posture', 'another person waits'), ('posture', 'someone waits'),
                           ('gaze_target', 'the crowd watches'), ('object_state', 'holding the clipboard'),
                           ('primary_action', 'inventing a zorb'), ('progress_clause', 'while he checks the bolt'),
                           ('primary_action', 'checking the bolt and someone smiles'),
                           ('primary_action', 'she checks the bolt'),
                           ('progress_clause', 'without she checks the bolt'),
                           ('progress_clause', 'without after checking the bolt'),
                           ('progress_clause', 'without the lights change'),
                           ('progress_clause', 'before checks the bolt'),
                           ('purpose_clause', 'she checks the bolt'),
                           ('purpose_clause', 'checks the bolt'),
                           ('hand_action', 'her hands holding herself steady'),
                           ('hand_action', 'her fingers holding herself ready'),
                           ('primary_action', 'standing and she checks the bolt'),
                           ('primary_action', 'standing and checks the bolt'),
                           ('primary_action', 'standing and someone checks the bolt'),
                           ('primary_action', 'checking what still needs dancing'),
                           ('primary_action', 'adjusting someone out of place'),
                           ('primary_action', 'keeping their movements composed'),
                           ('purpose_clause+anchor', 'checking the bolt'), ('default_purpose', 'holding the clipboard')]:
            fact = action_part_facts(RenderedActionPart(slot, text), primary=slot == 'primary_action')
            self.assertFalse(fact.known, (slot, text))
            self.assertIsNone(fact.same_subject)

    def test_productive_coordination_and_bounded_complements(self):
        for value in ('standing and tidying the small area around her',
                      'leaning closer while adjusting something out of place',
                      'walking slowly while checking what still needs doing',
                      'walking slowly while keeping her movements composed',
                      'leaning in and checking what needs adjusting',
                      'moving carefully while keeping her posture steady',
                      'holding the clipboard and adjusting something out of place'):
            facts = action_part_facts(RenderedActionPart('primary_action', value), primary=True)
            self.assertTrue(facts.known, value)
            self.assertTrue(facts.same_subject, value)
        facts = action_part_facts(RenderedActionPart('primary_action',
            'standing and tidying the small area around her'), primary=True)
        self.assertIsNone(facts.no_place_reference)

    def test_body_reflexive_and_bare_finite_attachment_regressions(self):
        for slot, value in [('hand_action', 'her hands holding herself steady'),
                            ('hand_action', 'her fingers holding herself ready'),
                            ('purpose_clause', 'she checks the bolt'),
                            ('purpose_clause', 'checks the bolt')]:
            with self.subTest(slot=slot, value=value):
                self.assertFalse(action_part_facts(RenderedActionPart(slot, value)).known)

    def test_unconnected_finite_modifiers_keep_v1_integration_bytes(self):
        from assets.test_n27_r4_integration import subordinate_case
        from assets.test_n27_productive_grammar import rebound
        from assets.test_n27_direct_provenance import render
        from pipeline.prompt_realizer import ContentPlan, realize_content_plan
        for value in ('checks the bolt', 'she checks the bolt'):
            case = subordinate_case()
            slots = case['frame']['legacy_slots']
            slots['purpose_clause'] = value
            case = rebound(case, action=render_action_slots(slots, activity_first=True))
            text, _, debug = render(case)
            self.assertFalse(debug['candidate_v2_applied'])
            self.assertEqual(text, realize_content_plan(ContentPlan(**case['slots'])))

    def test_aggregate_no_place_reference_and_unknown_propagation(self):
        for tail, expected in [('without checking the bolt', True), ('inventing a zorb', None),
                               ('because the lights change', False)]:
            slots = {'primary_action': 'holding the clipboard', 'purpose_clause': tail}
            action = render_action_slots(slots, activity_first=True)
            frame = ActionFrame.from_slots(slots, legacy_text=action)
            facts = derive_action_grammar(build_structural_evidence(frame, action))
            self.assertEqual(facts.frame_predicate_safe, True if expected is not None else None)
            self.assertEqual(facts.same_subject_attachment_safe, expected)
            if expected is True:
                self.assertTrue(facts.no_place_reference)
        slots = {'primary_action': 'standing near the garage', 'purpose_clause': ''}
        action = render_action_slots(slots, activity_first=True)
        facts = derive_action_grammar(build_structural_evidence(ActionFrame.from_slots(slots, legacy_text=action), action))
        self.assertIsNot(facts.no_place_reference, True)
        for destination in ('before heading to bed', 'after finally coming home'):
            fact = action_part_facts(RenderedActionPart('time_or_weather', destination))
            self.assertTrue(fact.known)
            self.assertIsNone(fact.no_place_reference)


if __name__ == '__main__':
    unittest.main()
