"""R3 real inputs must become supported without seed/whole-action acceptance."""
import copy
import json
from pathlib import Path
import unittest

from assets.test_n27_direct_provenance import render
from pipeline.prompt_realizer import ContentPlan, realize_content_plan
from pipeline.v2_leaf_grammar import background_modifiers, nominal, place_phrase, predicate, gaze, temporal, simple_clothes
from pipeline.v2_direct_provenance import materialize_direct


CASES = json.loads((Path(__file__).parent / 'fixtures' / 'n27_r3_productive_cases.json').read_text())


def rebound(original, **changes):
    case = copy.deepcopy(original)
    values = dict(case['replacements'])
    values.update({'{' + key + '}': value for key, value in changes.items()})
    values['{subject_clause}'] = values['{subj}'] + ' in ' + values['{costume}']
    values['{action_clause}'] = values['{action}'] + (', ' + values['{garnish}'] if values['{garnish}'] else '')
    values['{scene_clause}'] = 'in ' + values['{loc}'] + ', ' + values['{meta_mood}']
    values['{scene_anchor_clause}'] = values['{scene_clause}'][3:]
    case['frame']['legacy_text'] = values['{action}']
    verb = values['{action}'].split()[0]
    case['frame']['main_verb'] = verb
    case['slots']['semantic_slots']['predicate'] = verb
    case['surface'].update(rendered_clause=values['{action_clause}'], first_token=verb, verb=verb)
    case['replacements'] = list(values.items())
    return case


class TestProductiveGrammar(unittest.TestCase):
    def test_new_real_cases_apply_replay_and_preserve_actions(self):
        for case in CASES:
            with self.subTest(seed=case['run_seed']):
                before = copy.deepcopy(case)
                text, plan, debug = render(case)
                self.assertTrue(debug['candidate_v2_applied'])
                self.assertEqual((text, plan, debug), render(case))
                self.assertIn(dict(case['replacements'])['{action}'], text)
                self.assertEqual(case, before)
                self.assertNotIn('with looking', text)
                if case['run_seed'] == 41:
                    self.assertEqual(debug['syntax_family'], 'subject_action__scene_tail')
                    self.assertIn('looking directly ahead', text)
                    self.assertIn('during a late-afternoon maintenance shift', text)
                else:
                    self.assertIn('in a beige belted fitted knit top and a high-waist pencil skirt', text)
                    self.assertIn('on a nostalgic countryside village road', text)
                    self.assertTrue(plan.semantic_slots['scene'].startswith('on a nostalgic countryside village road'))
                    self.assertTrue(dict(case['replacements'])['{scene_clause}'].startswith('in nostalgic'))

    def test_unseen_nominal_valency_and_spatial_combinations(self):
        for action in ('adjusting a nut beside the open hood', 'holding the bolt near a marked tool cabinet',
                       'checking the machine beneath the hood', 'waiting by a rolling tool cabinet',
                       'pausing to inspect the bolt', 'keeping herself still while she waits',
                       'measuring one detail instead of rushing it'):
            with self.subTest(action=action):
                self.assertTrue(predicate(action))
                case = rebound(CASES[0], action=action + ', after the next task', garnish='looking away')
                text, _, debug = render(case)
                self.assertTrue(debug['candidate_v2_applied'])
                self.assertIn(action, text)
        for phrase in ('before one inspection', 'after the next errand', 'during the quiet shift'):
            self.assertTrue(temporal(phrase))
        for phrase in ('looking directly away', 'looking toward the thing she checks', 'looking at the hood'):
            self.assertTrue(gaze(phrase))

    def test_unknown_tails_independent_subjects_and_places_fail_fully_consumed_grammar(self):
        for action in ('tightening a bolt while a stranger waits', 'tightening a bolt because she hurries',
                       'holding the bolt and she smiles', 'tightening a strange widget',
                       'standing by the garage', 'waiting near the road', 'checking the workshop',
                       'tightening a bolt beneath the vehicle repair garage',
                       'looking toward the village road', 'looking toward the thing he needs',
                       'pausing to inspect the road', 'measuring the pause instead of rushing her'):
            with self.subTest(action=action):
                self.assertFalse(predicate(action))
                case = rebound(CASES[0], action=action)
                text, _, debug = render(case)
                self.assertFalse(debug['candidate_v2_applied'])
                self.assertEqual(text, realize_content_plan(ContentPlan(**case['slots'])))
        self.assertIsNone(nominal('the open garage', {'artifact'}, determined=True))
        self.assertIsNotNone(nominal('the open garage', {'place'}, determined=True))
        self.assertFalse(temporal('before the next inspection begins'))

    def test_nominal_order_and_articles_are_grammatical(self):
        for action in ('tightening an bolt', 'tightening a open bolt', 'tightening a repair next bolt',
                       'tightening a repair open bolt', 'holding a tool marked clipboard'):
            with self.subTest(action=action):
                self.assertFalse(predicate(action))
        for value in ('a trousers', 'an trousers', 'one trousers', 'a pressed trousers'):
            self.assertIsNone(nominal(value, {'garment'}))
        for action in ('tightening an open bolt', 'tightening a marked repair bolt',
                       'holding a marked tool clipboard'):
            self.assertTrue(predicate(action))
        self.assertIsNotNone(nominal('the pressed trousers', {'garment'}))

    def test_place_heads_require_their_explicit_locative_preposition(self):
        for head in ('road', 'street'):
            self.assertEqual(place_phrase('quiet ' + head), 'on a quiet ' + head)
        for head in ('garage', 'workshop', 'shop', 'bay', 'station'):
            self.assertEqual(place_phrase('modern ' + head), 'in a modern ' + head)
        for value in ('quiet room', 'modern machine', 'unknown garage'):
            self.assertIsNone(place_phrase(value))

    def test_new_scene_fields_require_membership_in_the_bound_producer_field(self):
        root = 'modern vehicle repair garage'
        for location in (root + ', with marked service bay',
                         root + ', featuring rolling tool cabinet',
                         root + ', during the next inspection',
                         root + ', featuring hydraulic vehicle lift and hydraulic vehicle lift',
                         'nostalgic countryside village road, featuring narrow paved road',
                         root + ', featuring hydraulic vehicle lift while she works'):
            with self.subTest(location=location):
                case = rebound(CASES[0], loc=location)
                _, _, debug = render(case)
                self.assertFalse(debug['candidate_v2_applied'])
        for location in (root + ', featuring marked service bay and hydraulic vehicle lift',
                         root + ', adorned with rolling tool cabinet'):
            case = rebound(CASES[0], loc=location)
            _, _, debug = render(case)
            self.assertTrue(debug['candidate_v2_applied'])

    def test_background_sequence_cannot_repeat_producer_fields(self):
        anchor = 'modern vehicle repair garage'
        for suffix in (
            'featuring hydraulic vehicle lift, featuring hydraulic vehicle lift',
            'featuring hydraulic vehicle lift, featuring marked service bay',
            'with rolling tool cabinet, adorned with rolling tool cabinet',
            'during late-afternoon maintenance shift, during late-afternoon maintenance shift',
        ):
            case = rebound(CASES[0], loc=anchor + ', ' + suffix)
            _, _, debug = render(case)
            self.assertFalse(debug['candidate_v2_applied'])
        segments = ['featuring hydraulic vehicle lift and marked service bay',
                    'adorned with rolling tool cabinet', 'during late-afternoon maintenance shift']
        for order in (segments, list(reversed(segments)), [segments[1], segments[0], segments[2]]):
            case = rebound(CASES[0], loc=anchor + ', ' + ', '.join(order))
            _, _, debug = render(case)
            self.assertTrue(debug['candidate_v2_applied'])
        # Isolate the sequence rule from unknown-word rejection: both distinct
        # event NPs are individually grammatical and producer-bound here.
        times = ['early maintenance shift', 'late-afternoon maintenance shift']
        pack = {'time': times}
        for time in times:
            self.assertIsNotNone(background_modifiers(['during ' + time], pack))
        self.assertIsNone(background_modifiers(['during ' + time for time in times], pack))

    def test_simple_garments_require_actual_choices_and_palette_order(self):
        for clothes in ('ivory structured fitted knit top and pressed tailored trousers',
                        'charcoal solid belted fitted knit top and high-waist pencil skirt',
                        'beige long-sleeve silk blouse and pressed tailored trousers'):
            with self.subTest(clothes=clothes):
                self.assertIsNotNone(simple_clothes(clothes))
                _, _, debug = render(rebound(CASES[1], costume=clothes))
                self.assertTrue(debug['candidate_v2_applied'])
        for clothes in ('beige belted fitted knit top and fitted pencil skirt',
                        'belted beige fitted knit top and high-waist pencil skirt',
                        'beige wool fitted knit top and high-waist pencil skirt',
                        'beige belted fitted knit top and high-waist pencil skirt, with a scarf',
                        'beige belted fitted knit top and high-waist pencil skirt wearing a coat'):
            with self.subTest(clothes=clothes):
                self.assertIsNone(simple_clothes(clothes))

    def test_new_fixtures_keep_frame_surface_and_slot_bindings(self):
        for original in CASES:
            variants = []
            for field, value in (('main_verb', 'reading'), ('primary_object', 'book'), ('legacy_text', 'reading a book')):
                case = copy.deepcopy(original)
                case['frame'][field] = value
                variants.append(case)
            for field, value in (('surface', 'clause'), ('rendered_clause', 'reading a book'),
                                 ('first_token', 'reading'), ('verb', 'reading')):
                case = copy.deepcopy(original)
                case['surface'][field] = value
                variants.append(case)
            case = copy.deepcopy(original)
            case['slots']['semantic_slots']['adjunct'] = '{action_clause}, she pauses'
            variants.append(case)
            for case in variants:
                text, _, debug = render(case)
                self.assertFalse(debug['candidate_v2_applied'])
                self.assertEqual(text, realize_content_plan(ContentPlan(**case['slots'])))

    def test_gaze_garnish_is_a_predicate_and_unknown_gaze_fails(self):
        for original in CASES:
            case = rebound(original, garnish='looking at the hood, brows knit in concentration')
            text, _, debug = render(case)
            self.assertTrue(debug['candidate_v2_applied'])
            self.assertIn(', looking at the hood, with brows knit', text)
            self.assertNotIn('with looking', text)
            case = rebound(original, garnish='looking directly ahead while he waits')
            _, _, debug = render(case)
            self.assertFalse(debug['candidate_v2_applied'])


if __name__ == '__main__':
    unittest.main()
