"""Candidate boundary tests built from a captured R3 real-workflow record."""
import copy
from dataclasses import replace
import unittest

from assets.test_n27_direct_provenance import render
from assets.test_n27_productive_grammar import CASES, rebound
from pipeline.action_renderer import render_action_slots
from pipeline.prompt_realizer import ContentPlan, realize_content_plan
from pipeline.v2_direct_provenance import materialize_direct
from pipeline.v2_structural_evidence import build_structural_evidence


def subordinate_case():
    case = copy.deepcopy(CASES[0])
    slots = case['frame']['legacy_slots']
    # A source-slot recombination, not an invented real-graph seed claim.
    slots['purpose_clause'] = 'without checking the bolt'
    slots['gaze_target'] = 'looking directly ahead'
    slots['social_clause'] = ''
    return rebound(case, action=render_action_slots(slots, activity_first=True))


def proof(case):
    return {'slots': case['slots']['semantic_slots'], 'surface': case['surface'],
            'replacements': case['replacements']}


class TestStructuralIntegration(unittest.TestCase):
    def test_new_source_bound_subordinate_applies_without_serializing_evidence(self):
        case = subordinate_case()
        before = copy.deepcopy(case)
        text, plan, debug = render(case)
        self.assertTrue(debug['candidate_v2_applied'])
        self.assertIn('without checking the bolt', text)
        self.assertEqual(case, before)
        self.assertEqual(set(plan.to_dict()), set(case['slots']))
        self.assertNotIn('producer_trace', repr(plan.to_dict()))
        self.assertEqual((text, plan, debug), render(case))

    def test_stale_replay_keeps_original_v1_bytes(self):
        case = subordinate_case()
        case['frame']['legacy_slots']['purpose_clause'] = 'checking the bolt'
        text, _, debug = render(case)
        self.assertFalse(debug['candidate_v2_applied'])
        self.assertEqual(text, realize_content_plan(ContentPlan(**case['slots'])))

    def test_finite_main_preserves_surface_and_canonical_verb_binding(self):
        case = subordinate_case()
        slots = case['frame']['legacy_slots']
        slots['primary_action'] = 'checks the bolt'
        case = rebound(case, action=render_action_slots(slots, activity_first=True))
        case['frame']['main_verb'] = 'checking'
        case['slots']['semantic_slots']['predicate'] = 'checking'
        case['slots']['lexical_choice'] = 'clause'
        case['surface'].update(surface='clause', input_surface='clause', verb='checking', first_token='checks')
        text, _, debug = render(case)
        self.assertTrue(debug['candidate_v2_applied'])
        self.assertIn(' checks the bolt', text)
        self.assertNotIn('is checks', text)

    def test_ephemeral_proof_is_revalidated_at_realizer_boundary(self):
        case = subordinate_case()
        provenance = proof(case)
        evidence = build_structural_evidence(case['frame'], dict(case['replacements'])['{action}'])
        self.assertIsNotNone(evidence)
        slots = materialize_direct(provenance, case['frame'], structural_evidence=evidence)
        self.assertIsNotNone(slots)
        plan = replace(ContentPlan(**case['slots']), semantic_slots=slots,
                       syntax_family='subject_action__scene_tail')
        surface = {**case['surface'], 'rendered_clause': slots['adjunct']}
        for forged in ({'exact_replay': True}, replace(evidence, primary_slot='gaze_target')):
            _, debug = realize_content_plan(plan, action_frame=case['frame'], action_surface=surface,
                direct_provenance=provenance, structural_evidence=forged, return_debug=True)
            self.assertEqual(debug['realizer_version'], 'v1')
        _, debug = realize_content_plan(plan, return_debug=True, structural_evidence=evidence)
        self.assertEqual(debug['realizer_version'], 'v1')

    def test_unknown_and_ownership_tails_do_not_enter_new_lane(self):
        for tail in ('without checking an unfamiliar gadget', 'the lights are moving',
                     'her eyes are checking the bolt', 'someone checks the bolt',
                     'she checks the bolt', 'checks the bolt',
                     'never checking an unfamiliar gadget'):
            case = subordinate_case()
            case['frame']['legacy_slots']['purpose_clause'] = tail
            case = rebound(case, action=render_action_slots(case['frame']['legacy_slots'], activity_first=True))
            text, _, debug = render(case)
            self.assertFalse(debug['candidate_v2_applied'])
            self.assertEqual(text, realize_content_plan(ContentPlan(**case['slots'])))


if __name__ == '__main__':
    unittest.main()
