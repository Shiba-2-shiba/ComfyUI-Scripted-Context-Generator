import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from pipeline.v2_template_provenance import materialize_scene_template, scene_template_kind
from vocab.loader import load_json


CASES = json.loads((Path(__file__).parent / 'fixtures/n27_r42_real_cases.json').read_text(encoding='utf-8'))
DIRECT = {'subject': '{subject_clause}', 'adjunct': '{action_clause}', 'scene': '{scene_clause}'}


class TestR42Template(unittest.TestCase):
    def test_original234_binds_catalog_and_retains_scene_owner(self):
        case = next(case for case in CASES if case['run_seed'] == 234)
        slots = case['slots']['semantic_slots']
        before = copy.deepcopy(slots)
        scene = ('in a small contemporary gallery arranged for a weekday viewing, '
                 'featuring framed canvas works spaced along the wall and small title plaques mounted beside each work, '
                 'with a hushed viewing room atmosphere, with atmospheric perspective')
        self.assertEqual(scene_template_kind(slots), 'owned_finite')
        self.assertEqual(materialize_scene_template(slots, scene), 'the room around her stays ' + scene)
        self.assertEqual(slots, before)

    def test_direct_and_other_actual_owned_template(self):
        self.assertEqual(scene_template_kind(DIRECT), 'direct')
        self.assertEqual(materialize_scene_template(DIRECT, 'in a gallery'), 'in a gallery')
        slots = {**DIRECT, 'scene': 'with the scene around her staying in {scene_anchor_clause}'}
        self.assertEqual(scene_template_kind(slots), 'owned_finite')
        self.assertEqual(materialize_scene_template(slots, 'in a gallery, with quiet light'),
                         'the scene around her stays in a gallery, with quiet light')

    def test_unknown_or_duplicate_placeholder_and_independent_owner_reject(self):
        unknown = (
            'and the room around her staying in {scene_clause}',
            'and the room around her staying in {scene_anchor_clause} {scene_anchor_clause}',
            'and the room around her staying in {scene_anchor_clause}, {action_clause}',
            'and the stranger around her staying in {scene_anchor_clause}',
            'and the room around someone staying in {scene_anchor_clause}',
            'and the room around her running in {scene_anchor_clause}',
            'and the room around her staying beside {scene_anchor_clause}',
            'and the room around her staying in {scene_anchor_clause} while someone watches',
            'the room around her staying in {scene_anchor_clause}',
        )
        for scene in unknown:
            with self.subTest(scene=scene):
                slots = {**DIRECT, 'scene': scene}
                self.assertIsNone(scene_template_kind(slots))
                catalog = copy.deepcopy(load_json('template_catalog.json'))
                catalog['end'].append({'key': 'end_scene_room', 'text': scene, 'roles': ['focused']})
                with patch('pipeline.v2_template_provenance.load_json', return_value=catalog):
                    self.assertIsNone(scene_template_kind(slots))
                    self.assertIsNone(materialize_scene_template(slots, 'in a gallery'))

    def test_membership_requires_actual_text_in_correct_field(self):
        for field in ('intro', 'body', 'end'):
            catalog = copy.deepcopy(load_json('template_catalog.json'))
            catalog[field] = [{'key': 'intro_plain_subject', 'text': 'unknown', 'roles': ['focused']}]
            with patch('pipeline.v2_template_provenance.load_json', return_value=catalog):
                self.assertIsNone(scene_template_kind(DIRECT))
        catalog = copy.deepcopy(load_json('template_catalog.json'))
        catalog['end'] = catalog['intro']
        with patch('pipeline.v2_template_provenance.load_json', return_value=catalog):
            self.assertIsNone(scene_template_kind(DIRECT))

    def test_non_direct_subject_or_action_cannot_lose_wrapper_content(self):
        for field, value in (('subject', '{subject_clause}, caught in a brief pause'),
                             ('adjunct', '{action_clause}, the moment staying with her')):
            self.assertIsNone(scene_template_kind({**DIRECT, field: value}))

    def test_locative_prefix_is_required_and_never_stripped_arbitrarily(self):
        self.assertEqual(materialize_scene_template(DIRECT, 'on a village road'), 'on a village road')
        owned = {**DIRECT, 'scene': 'and the room around her staying in {scene_anchor_clause}'}
        for slots in (DIRECT, owned):
            for value in (None, '', 'in ', 'in  a gallery', 'at a gallery', 'inside a gallery',
                          'within a gallery', 'In a gallery', ' in a gallery',
                          'in a gallery\nwith light', 'in {loc}', 'in a gallery. Someone moves'):
                self.assertIsNone(materialize_scene_template(slots, value), repr(value))


if __name__ == '__main__':
    unittest.main()
