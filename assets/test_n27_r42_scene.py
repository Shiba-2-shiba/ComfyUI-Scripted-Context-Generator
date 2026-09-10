import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from pipeline.v2_scene_provenance import producer_scene_parts


CASES = json.loads((Path(__file__).parent / 'fixtures/n27_r42_real_cases.json').read_text(encoding='utf-8'))


class TestR42Scene(unittest.TestCase):
    def test_previous_real_scene_bytes_are_unchanged(self):
        previous = json.loads((Path(__file__).parent / 'fixtures/n27_r41_real_cases.json').read_text(encoding='utf-8'))
        expected = {
            190: ('in a cozy romantic bedroom', (
                'with smooth silk sheets', 'during a lazy morning',
                'featuring a wooden wardrobe with open doors and scattered soft cushions')),
            482: ('in a cozy romantic bedroom', (
                'featuring a vintage vanity mirror with lights and a canopied four-poster bed',
                'with layered background depth')),
        }
        for case in previous:
            self.assertEqual(producer_scene_parts(dict(case['replacements'])['{loc}'],
                             case['frame']['legacy_slots']['location']), expected[case['run_seed']])

    def test_original_real_scenes_keep_attached_words(self):
        expected = {
            88: ('in a grand historic opera house interior', (
                'during an evening performance', 'with gold leaf detailing')),
            234: ('in a small contemporary gallery arranged for a weekday viewing', (
                'featuring framed canvas works spaced along the wall and small title plaques mounted beside each work',
                'with a hushed viewing room atmosphere', 'with atmospheric perspective')),
        }
        for case in CASES:
            if case['run_seed'] not in expected:
                continue
            before = copy.deepcopy(case)
            self.assertEqual(producer_scene_parts(dict(case['replacements'])['{loc}'],
                             case['frame']['legacy_slots']['location']), expected[case['run_seed']])
            self.assertEqual(case, before)

    def parse_pack(self, environment, core=(), **fields):
        pack = {'environment': [environment], 'core': list(core), **fields}
        location = environment
        if core:
            location += ', featuring ' + ' and '.join(core)
        with patch('pipeline.v2_scene_provenance.load_background_packs', return_value={'test': pack}):
            return producer_scene_parts(location, 'test')

    def test_unseen_nominal_composition_is_independent_of_catalog(self):
        self.assertEqual(self.parse_pack('small historic gallery arranged for a quiet viewing', (
            'canvas works spaced along the wall', 'title plaques mounted beside each work')),
            ('in a small historic gallery arranged for a quiet viewing', (
             'featuring canvas works spaced along the wall and title plaques mounted beside each work',)))
        self.assertEqual(self.parse_pack('historic opera house interior'),
                         ('in a historic opera house interior', ()))
        self.assertIsNone(producer_scene_parts('historic opera house interior', 'opera_house'))

    def test_source_membership_does_not_prove_ownership_or_grammar(self):
        for environment in ('small gallery arranged by her', 'small gallery arranged for her',
                            'small gallery arranged for a weekday viewings',
                            'small gallery arranged for each work', 'small gallery running away',
                            'small title gallery', 'hushed viewing room gallery', 'grand opera interior'):
            self.assertIsNone(self.parse_pack(environment), environment)
        for core in (('small title plaques mounted beside each work',),
                     ('framed canvas works spaced along her',),
                     ('framed canvas works spaced along a wall',),
                     ('framed canvas work spaced along the wall',),
                     ('small title plaques spaced along the wall',),
                     ('framed canvas works mounted beside each work',),
                     ('framed canvas works spaced along the wall', 'small title plaques mounted beside each works'),
                     ('framed canvas works spaced along the wall', 'small title plaques mounted beside the work'),
                     ('framed canvas works spaced along the wall', 'small title plaques mounted beside her'),
                     ('framed canvas works spaced along the wall', 'small title plaques mounted beside each work while she moves')):
            self.assertIsNone(self.parse_pack('small contemporary gallery', core), core)

    def test_real_fields_reject_wrong_source_duplicates_and_dangling_binding(self):
        case = next(case for case in CASES if case['run_seed'] == 234)
        location = dict(case['replacements'])['{loc}']
        for mutated in (location + ', hushed viewing room atmosphere',
                        location + ', atmospheric perspective',
                        location.replace('hushed viewing room atmosphere', 'during hushed viewing room atmosphere'),
                        location.replace('featuring ', 'with '),
                        location.replace('framed canvas works spaced along the wall and ', ''),
                        location.replace('small contemporary gallery', 'cozy romantic bedroom')):
            self.assertIsNone(producer_scene_parts(mutated, 'art_gallery'), mutated)
        with patch('pipeline.v2_scene_provenance.load_json', return_value={
                'details': ['hushed viewing room atmosphere']}):
            self.assertIsNone(producer_scene_parts(location, 'art_gallery'))


if __name__ == '__main__':
    unittest.main()
