"""Producer membership and grammar jointly prove garment attachments."""
import copy
from collections import Counter
import json
from pathlib import Path
import random
import re
import unittest
from unittest.mock import patch

from pipeline.v2_clothing_provenance import materialize_clothes
from pipeline.clothing_candidate_renderer import build_item_description
from vocab import clothing


class TestClothingProducerEvidence(unittest.TestCase):
    def test_verbatim_intake_costumes_preserve_every_fact_word(self):
        cases = json.loads((Path(__file__).parent / 'fixtures' / 'n27_r41_real_cases.json').read_text())
        for case in cases:
            value = dict(case['replacements'])['{costume}']
            palette = case['producer_context']['character_palette']
            rendered = materialize_clothes(value, character_palette=palette)
            self.assertIsNotNone(rendered, case['run_seed'])
            tokens = lambda text: Counter(re.findall(r'[a-z]+(?:-[a-z]+)*', text))
            self.assertFalse(tokens(value) - tokens(rendered))
            self.assertLessEqual(set(tokens(rendered) - tokens(value)), {'a', 'an', 'and'})
            self.assertNotIn(', with ', rendered)

    def test_actual_producer_palette_and_detail_combinations(self):
        pack = next(pack for groups in clothing.CONCEPT_PACKS.values() for pack in groups.values()
                    if 'knit belt' in pack.get('palette', {}).get('embellishments', []))
        for seed in range(64):
            raw, _ = build_item_description(random.Random(seed), pack, loc='bedroom_boudoir')
            self.assertIsNotNone(materialize_clothes(raw), raw)

    def test_real190_palette_and_nominal_style(self):
        value = ('charcoal grey cashmere soft knit silhouette warm turtleneck sweater dress, '
                 'with knit belt, fuzzy leg warmers')
        self.assertIsNone(materialize_clothes(value))
        self.assertEqual(
            materialize_clothes(value, character_palette=('charcoal grey',)),
            'a charcoal grey cashmere warm turtleneck sweater dress with '
            'a soft knit silhouette, a knit belt and fuzzy leg warmers')

    def test_productive_choices_palette_and_detail_subsets(self):
        for garment in ('cozy sweater dress', 'warm turtleneck sweater dress'):
            for prefix in ('', 'cream ', 'beige solid wool knee-length '):
                for raw, expected in (
                    ('', ''), ('knit belt', 'a knit belt'),
                    ('ribbed texture', 'a ribbed texture'),
                    ('fuzzy leg warmers', 'fuzzy leg warmers'),
                    ('knit belt, cozy scarf', 'a knit belt and a cozy scarf'),
                    ('ribbed texture, fuzzy leg warmers', 'a ribbed texture and fuzzy leg warmers'),
                ):
                    value = prefix + garment + (', with ' + raw if raw else '')
                    with self.subTest(value=value):
                        self.assertEqual(materialize_clothes(value),
                                         'a ' + prefix + garment + (' with ' + expected if raw else ''))

    def test_unknown_reordered_repeated_or_independent_details_fail(self):
        for suffix in ('knit belt, ribbed texture', 'fuzzy leg warmers, knit belt',
                       'knit belt, knit belt', 'knit belt, the stranger waves',
                       'knit belt and cozy scarf', 'covered in snow',
                       'knit belt, fuzzy leg warmers, covered in snow', 'a knit belt', ''):
            self.assertIsNone(materialize_clothes('cozy sweater dress, with ' + suffix), suffix)
        for value in ('cream wool solid cozy sweater dress', 'cozy sweater dress, wearing a coat',
                      'unknown cozy sweater dress', 'cozy sweater dress ',
                      'cozy sweater dress\n', 'cozy sweater dress, with cozy scarf, ribbed texture'):
            self.assertIsNone(materialize_clothes(value), value)

    def test_source_membership_cannot_establish_grammar_or_ownership(self):
        packs = copy.deepcopy(clothing.CONCEPT_PACKS)
        pack = next(pack for groups in packs.values() for pack in groups.values()
                    if 'knit belt' in pack.get('palette', {}).get('embellishments', []))
        pack['palette']['embellishments'].append('the stranger waves')
        pack['optional_details'].append('knit belt')
        pack['states'].append('ribbed texture')
        pack['choices']['dresses'].append(['dress', 'she wears'])
        pack['palette']['colors'].append('she waves')
        with patch.object(clothing, 'CONCEPT_PACKS', packs):
            for value in ('cozy sweater dress, with the stranger waves',
                          'cozy sweater dress, with ribbed texture, knit belt',
                          'cozy sweater dress, with cozy scarf, ribbed texture',
                          'she wears dress, with knit belt',
                          'she waves cozy sweater dress, with knit belt'):
                self.assertIsNone(materialize_clothes(value), value)

    def test_overrides_require_bounded_color_grammar(self):
        for color in ('chartreuse', 'she waves', 'charcoal grey, the stranger waves'):
            self.assertIsNone(materialize_clothes(color + ' cozy sweater dress',
                                                 character_palette=(color,)))

    def test_ambiguous_pack_owner_fails(self):
        packs = copy.deepcopy(clothing.CONCEPT_PACKS)
        original = next(pack for groups in packs.values() for pack in groups.values()
                        if 'knit belt' in pack.get('palette', {}).get('embellishments', []))
        packs['dresses']['ambiguous_copy'] = copy.deepcopy(original)
        with patch.object(clothing, 'CONCEPT_PACKS', packs):
            self.assertIsNone(materialize_clothes('cozy sweater dress, with knit belt'))


if __name__ == '__main__':
    unittest.main()
