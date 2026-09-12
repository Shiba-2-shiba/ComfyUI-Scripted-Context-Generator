import json
from pathlib import Path
import unittest

from pipeline.v2_scene_provenance import producer_scene_parts

CASES = json.loads((Path(__file__).parent / 'fixtures/n27_r41_real_cases.json').read_text(encoding='utf-8'))


class TestProducerScene(unittest.TestCase):
    def test_original_workflow_scene_constituents(self):
        for case in CASES:
            value = dict(case['replacements'])['{loc}']
            parsed = producer_scene_parts(value, case['frame']['legacy_slots']['location'])
            self.assertIsNotNone(parsed, case['run_seed'])
            anchor, modifiers = parsed
            self.assertEqual(anchor, 'in a cozy romantic bedroom')
            self.assertIn('with smooth silk sheets' if case['run_seed'] == 190 else
                          'with layered background depth', modifiers)

    def test_source_field_order_uniqueness_and_ownership(self):
        for tail in ('with canopied four-poster bed', 'featuring smooth silk sheets',
                     'featuring canopied four-poster bed and canopied four-poster bed',
                     'smooth silk sheets, fluffy thick rug',
                     'layered background depth, layered background depth',
                     'featuring wooden wardrobe with her eyes',
                     'with the lights go out', 'during lazy morning while she works'):
            self.assertIsNone(producer_scene_parts('cozy romantic bedroom, ' + tail, 'bedroom_boudoir'), tail)
        self.assertIsNone(producer_scene_parts('cozy romantic bedroom', 'antique_shop'))

    def test_new_field_combinations_preserve_noun_owners(self):
        parsed = producer_scene_parts('gothic victorian boudoir, featuring wooden wardrobe with open doors, '
                                      'fluffy thick rug, during quiet night', 'bedroom_boudoir')
        self.assertEqual(parsed, ('in a gothic victorian boudoir', (
            'featuring a wooden wardrobe with open doors', 'with a fluffy thick rug', 'during a quiet night')))


if __name__ == '__main__':
    unittest.main()
