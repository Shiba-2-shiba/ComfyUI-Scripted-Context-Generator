import copy
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import re
import unittest

from pipeline.prompt_realizer import ContentPlan, realize_content_plan
from pipeline.v2_candidate_bridge import render_candidate
from pipeline.v2_direct_provenance import materialize_direct
from pipeline.v2_structural_evidence import build_structural_evidence

CASES = json.loads((Path(__file__).parent / 'fixtures/n27_r42_real_cases.json').read_text(encoding='utf-8'))
TARGETS = [case for case in CASES if case['run_seed'] in (88, 234)]


def render(case):
    plan = ContentPlan(**case['slots'])
    legacy, debug = realize_content_plan(plan, return_debug=True)
    return render_candidate(plan, legacy, debug, case['frame'], case['surface'],
                            case['replacements'], case['builder_seed'], producer_context=case['producer_context'])


class TestR42Integration(unittest.TestCase):
    def test_new_real_cases_preserve_words_and_distinct_owners(self):
        for case in TARGETS:
            original = copy.deepcopy(case)
            text, plan, debug = render(case)
            self.assertTrue(debug['candidate_v2_applied'], case['run_seed'])
            self.assertEqual(debug['syntax_family'], 'subject_action__scene_tail')
            self.assertEqual(case, original)
            self.assertEqual((text, plan, debug), render(case))
            self.assertEqual(set(plan.to_dict()), set(case['slots']))
            values = dict(case['replacements'])
            words = lambda value: Counter('featuring' if word == 'features' else word
                for word in re.findall(r"[a-z]+(?:-[a-z]+)*", value.lower()))
            source = ' '.join(values[key] for key in ('{subject_clause}', '{action_clause}', '{scene_clause}'))
            self.assertFalse(words(source) - words(text))
            if case['run_seed'] == 88:
                self.assertIn(', with eyes fixed on what needs to happen next,', text)
                facts = debug['candidate_eligibility']['safety_facts']
                self.assertFalse(facts['same_subject_attachment_safe'])
                self.assertFalse(facts['independent_action_subject'])
            else:
                self.assertIn('. The room around her stays in ', text)
                self.assertIn('gallery that is arranged for a weekday viewing and that features ', text)
                self.assertNotIn('weekday viewing, which', text)
                self.assertNotIn('weekday viewing, featuring', text)
                self.assertNotIn('The scene is set the room', text)

    def test_new_owners_never_grant_unproved_other_families(self):
        for case in TARGETS:
            proof = {'slots': case['slots']['semantic_slots'], 'surface': case['surface'],
                     'replacements': case['replacements'], **case['producer_context']}
            evidence = build_structural_evidence(case['frame'], dict(case['replacements'])['{action}'])
            concrete = materialize_direct(proof, case['frame'], structural_evidence=evidence)
            self.assertIsNotNone(concrete)
            for family in ('subject_action_scene_insert', 'action_lead_subject_scene', 'scene_lead_subject_action'):
                plan = replace(ContentPlan(**case['slots']), syntax_family=family, semantic_slots=concrete)
                _, debug = realize_content_plan(plan, action_frame=case['frame'],
                    action_surface={**case['surface'], 'rendered_clause': concrete['adjunct']},
                    structural_evidence=evidence, direct_provenance=proof, return_debug=True)
                self.assertEqual(debug['realizer_version'], 'v1')

    def test_stale_source_and_unknown_wrapper_retain_v1_bytes(self):
        for original in TARGETS:
            for mutation in ('frame', 'template'):
                case = copy.deepcopy(original)
                if mutation == 'frame':
                    case['frame']['legacy_slots']['primary_action'] = 'someone smiles'
                else:
                    case['slots']['semantic_slots']['scene'] = 'another person stays in {scene_anchor_clause}'
                text, _, debug = render(case)
                self.assertFalse(debug['candidate_v2_applied'])
                self.assertEqual(text, realize_content_plan(ContentPlan(**case['slots'])))

    def test_compound_semantic_identity_is_not_the_first_surface_token(self):
        # Use a real compound frame with simple proved surrounding clauses to
        # isolate binding. This is a recombination, not an extra real-graph claim.
        from assets.test_n27_productive_grammar import CASES as OLD_CASES, rebound
        from pipeline.action_renderer import render_action_slots
        case = copy.deepcopy(OLD_CASES[0])
        slots = {'primary_action': 'standing and tidying the small area around her',
                 'location': case['frame']['legacy_slots']['location']}
        case['frame']['legacy_slots'] = slots
        case = rebound(case, action=render_action_slots(slots, activity_first=True))
        case['frame']['main_verb'] = 'tidying'
        case['slots']['semantic_slots']['predicate'] = 'tidying'
        case['surface'].update(verb='tidying', first_token='standing')
        case['producer_context'] = {}
        text, _, debug = render(case)
        self.assertTrue(debug['candidate_v2_applied'])
        self.assertIn('is standing and tidying', text)
        for wrong in ('standing', 'checking'):
            bad = copy.deepcopy(case)
            bad['frame']['main_verb'] = wrong
            bad['slots']['semantic_slots']['predicate'] = wrong
            bad['surface']['verb'] = wrong
            self.assertFalse(render(bad)[2]['candidate_v2_applied'])
        for negation in ('not ', 'never '):
            bad = copy.deepcopy(case)
            bad['frame']['legacy_slots']['primary_action'] = 'standing and ' + negation + 'tidying the small area around her'
            bad = rebound(bad, action=render_action_slots(bad['frame']['legacy_slots'], activity_first=True))
            bad['producer_context'] = {}
            text, _, debug = render(bad)
            self.assertFalse(debug['candidate_v2_applied'])
            self.assertEqual(text, realize_content_plan(ContentPlan(**bad['slots'])))


if __name__ == '__main__':
    unittest.main()
