import copy
import json
from collections import Counter
from dataclasses import replace
from pathlib import Path
import re
import unittest

from pipeline.prompt_realizer import ContentPlan, realize_content_plan
from pipeline.v2_candidate_bridge import render_candidate
from pipeline.v2_direct_provenance import materialize_direct
from pipeline.syntax_family_selector import eligible_syntax_families


CASES = json.loads((Path(__file__).parent / 'fixtures' / 'n27_r1_direct_cases.json').read_text())


def render(case):
    plan = ContentPlan(**case['slots'])
    legacy, debug = realize_content_plan(plan, return_debug=True)
    return render_candidate(plan, legacy, debug, case['frame'], case['surface'],
                            case['replacements'], case['builder_seed'])


class TestDirectProvenance(unittest.TestCase):
    def test_real_cases_preserve_fact_words_and_replay(self):
        for case in CASES:
            with self.subTest(seed=case['run_seed']):
                before = copy.deepcopy(case)
                text, plan, debug = render(case)
                self.assertTrue(debug['candidate_v2_applied'])
                self.assertIn(debug['syntax_family'], {'subject_action__scene_tail',
                                                      'scene_lead_subject_action', 'subject_scene_action'})
                self.assertEqual(text.count('.'), 2 if debug['syntax_family'] == 'subject_action__scene_tail' else 1)
                self.assertEqual((text, plan, debug), render(case))
                original = dict(case['replacements'])
                # R2 permits with -> has and featuring -> features only within
                # the explicitly location-owned relative clause.
                tokens = lambda value: Counter('featuring' if word == 'features' else word for word in
                    re.findall(r"[a-z]+(?:-[a-z]+)*", value.lower()) if word != 'with')
                source = tokens(' '.join(original[k] for k in
                                        ('{subject_clause}', '{action_clause}', '{scene_clause}')))
                extra = tokens(text) - source
                self.assertFalse(source - tokens(text))
                self.assertLessEqual(set(extra), {'a', 'an', 'is', 'the', 'scene', 'set', 'which', 'has', 'and'})
                self.assertEqual(case, before)
                if case['run_seed'] == 9:
                    self.assertIn('during the evening', text)
                elif case['run_seed'] == 51:
                    self.assertIn('during a deep moonless night', text)

    def test_unknown_tails_and_inconsistent_bindings_preserve_exact_legacy(self):
        for original in CASES:
            variants = []
            for token in ('{subj}', '{costume}', '{loc}', '{action}', '{garnish}',
                          '{meta_mood}', '{subject_clause}', '{action_clause}', '{scene_clause}'):
                case = copy.deepcopy(original)
                for pair in case['replacements']:
                    if pair[0] == token:
                        pair[1] += ', the stranger waves'
                variants.append(case)
            for key in ('subject', 'adjunct', 'scene'):
                case = copy.deepcopy(original)
                case['slots']['semantic_slots'][key] += ', watching her'
                variants.append(case)
            for key, value in (('main_verb', 'reading'), ('legacy_text', 'reading a book'),
                               ('primary_object', 'book')):
                case = copy.deepcopy(original)
                case['frame'][key] = value
                variants.append(case)
            for key, value in (('surface', 'framed'), ('rendered_clause', 'reading a book'),
                               ('verb', 'reading'), ('first_token', 'reading'), ('input_surface', 'clause')):
                case = copy.deepcopy(original)
                case['surface'][key] = value
                variants.append(case)
            for case in variants:
                with self.subTest(seed=case['run_seed'], mutation=case):
                    result, _, debug = render(case)
                    self.assertFalse(debug['candidate_v2_applied'])
                    self.assertEqual(result, realize_content_plan(ContentPlan(**case['slots'])))

    def test_raw_proof_is_rechecked_and_cannot_authorize_other_orders(self):
        case = CASES[0]
        evidence = {'slots': case['slots']['semantic_slots'], 'surface': case['surface'],
                    'replacements': case['replacements']}
        slots = materialize_direct(evidence, case['frame'])
        plan = replace(ContentPlan(**case['slots']), semantic_slots=slots,
                       syntax_family='subject_action__scene_tail')
        surface = {**case['surface'], 'rendered_clause': slots['adjunct']}
        families, debug = eligible_syntax_families(plan, case['frame'], surface,
                                                   direct_provenance=evidence, return_debug=True)
        self.assertEqual(families, ['subject_action_scene', 'scene_lead_subject_action',
                                    'subject_action__scene_tail', 'subject_scene_action'])
        self.assertTrue(debug['direct_provenance_valid'])
        for key in ('scene_lead_safe', 'scene_adjunct_safe'):
            self.assertTrue(debug['safety_facts'][key])
        self.assertIsNone(debug['safety_facts']['same_subject_attachment_safe'])
        for family in ('subject_action_scene', 'action_lead_subject_scene', 'subject_action_scene_insert'):
            _, realized = realize_content_plan(replace(plan, syntax_family=family),
                                               action_frame=case['frame'], action_surface=surface,
                                               direct_provenance=evidence, return_debug=True)
            self.assertEqual(realized['realizer_version'], 'v1')
        for bad in ({'trusted': True}, {**evidence, 'slots': {**evidence['slots'], 'scene': 'in a room'}},
                    {**evidence, 'replacements': case['replacements'] + [case['replacements'][0]]}):
            _, realized = realize_content_plan(plan, action_frame=case['frame'], action_surface=surface,
                                               direct_provenance=bad, return_debug=True)
            self.assertEqual(realized['realizer_version'], 'v1')
        for key in ('subject', 'adjunct', 'scene', 'predicate', 'object'):
            altered = replace(plan, semantic_slots={**slots, key: slots[key] + ' another clause'})
            _, realized = realize_content_plan(altered, action_frame=case['frame'], action_surface=surface,
                                               direct_provenance=evidence, return_debug=True)
            self.assertEqual(realized['realizer_version'], 'v1')

    def test_profile_and_clothing_constructors_are_combinatorial(self):
        case = copy.deepcopy(CASES[0])
        values = dict(case['replacements'])
        values['{subj}'] = 'A solo girl with messy bun, red hair and amber eyes'
        values['{costume}'] = 'cream solid wool knee-length cozy sweater dress'
        values['{subject_clause}'] = values['{subj}'] + ' in ' + values['{costume}']
        case['replacements'] = list(values.items())
        text, _, debug = render(case)
        self.assertTrue(debug['candidate_v2_applied'])
        self.assertIn('with a messy bun, red hair and amber eyes', text)
        self.assertIn('in a cream solid wool knee-length cozy sweater dress', text)

    def test_self_consistent_unknown_components_still_fail_closed(self):
        for token, tail in (('{subj}', ', her sister nearby'), ('{costume}', ', with unfamiliar draping'),
                            ('{action}', ', checking an unfamiliar gadget'),
                            ('{garnish}', ', curious eyes'), ('{loc}', ', lights turning off'),
                            ('{meta_mood}', ', she smiles')):
            case = copy.deepcopy(CASES[0])
            values = dict(case['replacements'])
            values[token] += tail
            values['{subject_clause}'] = values['{subj}'] + ' in ' + values['{costume}']
            values['{action_clause}'] = values['{action}'] + ', ' + values['{garnish}']
            values['{scene_clause}'] = 'in ' + values['{loc}'] + ', ' + values['{meta_mood}']
            values['{scene_anchor_clause}'] = values['{scene_clause}'][3:]
            case['surface']['rendered_clause'] = values['{action_clause}']
            case['frame']['legacy_text'] = values['{action}']
            case['replacements'] = list(values.items())
            with self.subTest(component=token):
                text, _, debug = render(case)
                self.assertFalse(debug['candidate_v2_applied'])
                self.assertEqual(text, realize_content_plan(ContentPlan(**case['slots'])))

    def test_missing_and_malformed_provenance_is_not_evidence(self):
        case = CASES[0]
        for evidence in (None, True, {}, {'slots': {}, 'surface': {}, 'replacements': []},
                         {'slots': case['slots']['semantic_slots'], 'surface': [],
                          'replacements': case['replacements']},
                         {'slots': case['slots']['semantic_slots'], 'surface': case['surface'],
                          'replacements': [['{subject_clause}', ['not text']]]}):
            self.assertIsNone(materialize_direct(evidence, case['frame']))


if __name__ == '__main__':
    unittest.main()
