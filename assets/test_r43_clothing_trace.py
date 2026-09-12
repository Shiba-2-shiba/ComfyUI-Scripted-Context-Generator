import hashlib
import json
import os
import random
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline import clothing_candidate_renderer as renderer


def digest(rows, **kwargs):
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(',', ':'), **kwargs).encode()).hexdigest()


class ClothingTraceTests(unittest.TestCase):
    def test_item_pre_extraction_baseline(self):
        rows = [(kind, key, seed, *renderer.build_item_description(random.Random(seed), pack,
                 ['violet', 'white'], loc='winter_street'))
                for kind, packs in renderer.clothing_vocab.CONCEPT_PACKS.items()
                for key, pack in packs.items() for seed in range(12)]
        self.assertEqual(len(rows), 624)
        self.assertEqual(digest(rows), 'a44dde04d5a29aec407b252681d675b7afb3926519a084197ae3f6de1d063aae')

    def test_candidate_pre_extraction_baseline(self):
        rows = [renderer.render_clothing_candidate(theme, seed, mode, .5, 'violet,white',
                 [], [], [], [], attempt_index=attempt, loc='winter_street')
                for theme in renderer.clothing_vocab.THEME_TO_PACKS for seed in range(4)
                for mode in ('auto', 'no_outerwear', 'outerwear_only') for attempt in (0, 2)]
        self.assertEqual(len(rows), 576)
        self.assertEqual(digest(rows, sort_keys=True), '159df4d998c1ae7e230ce033ca3e03bdc3dca0537b6f2b8232bc929e38780226')

    def test_item_trace_preserves_draws_and_outputs(self):
        from pipeline.realization_evidence import text_sha256
        for kind, packs in renderer.clothing_vocab.CONCEPT_PACKS.items():
            for key, pack in packs.items():
                for seed in range(12):
                    normal, traced = random.Random(seed), random.Random(seed)
                    expected = renderer.build_item_description(normal, pack, ['violet'], loc='winter_street')
                    text, signature, trace = renderer.build_item_description_with_trace(
                        traced, pack, ['violet'], loc='winter_street', catalog_key=f'{kind}:{key}')
                    self.assertEqual((text, signature), expected)
                    self.assertEqual(normal.getstate(), traced.getstate())
                    self.assertEqual(trace.raw_output_sha256, text_sha256(text))
                    self.assertEqual(trace.mode, 'exact_renderer_replay')
                    for part in trace.parts:
                        expected_key = None if part.source.field == 'character_palette.colors' else f'{kind}:{key}'
                        self.assertEqual(part.source.catalog_key, expected_key)

    def test_candidate_trace_retains_decision_and_attempt_binding(self):
        from pipeline.realization_evidence import text_sha256
        for theme in renderer.clothing_vocab.THEME_TO_PACKS:
            for mode in ('auto', 'no_outerwear', 'outerwear_only'):
                for attempt in (0, 2):
                    args = (theme, 12, mode, .9, 'violet,white', [], [], [], [])
                    expected = renderer.render_clothing_candidate(*args, attempt_index=attempt)
                    traces = []
                    actual = renderer.render_clothing_candidate(*args, attempt_index=attempt, trace_sink=traces.append)
                    self.assertEqual(actual, expected)
                    self.assertEqual(len(traces), 1)
                    self.assertEqual(traces[0].emitted_output_sha256, text_sha256(actual[0]))
                    self.assertEqual(len({p.part_id for p in traces[0].parts}), len(traces[0].parts))

    def test_suppression_origin_order_and_mutable_input_isolation(self):
        from pipeline.realization_evidence import text_sha256
        pack = {'choices': {'top': [['cotton shirt', 'fitted']]},
                'palette': {'colors': ['orange'], 'materials': ['silk'], 'patterns': ['striped'],
                            'styles': ['formal'], 'embellishments': ['ribbon']},
                'optional_details': ['buttons'], 'states': ['wet cuffs']}
        class AllDraws(random.Random):
            def random(self):
                return 0.0
            def choice(self, values):
                return values[0]
        with patch.object(renderer.clothing_vocab, 'PALETTE_DEFAULT_PROBABILITIES',
                          {'colors': 1, 'materials': 1, 'patterns': 1, 'styles': 1}):
            text, signature, trace = renderer.build_item_description_with_trace(
                AllDraws(4), pack, ['violet'], loc='cozy_living_room', catalog_key='separates:test')
        parts = {p.part_id: p for p in trace.parts}
        self.assertEqual(text, 'violet striped formal fitted cotton shirt, with ribbon, buttons')
        self.assertNotIn('silk', signature)
        self.assertNotIn('wet', signature)
        self.assertEqual(parts['color'].source.field, 'character_palette.colors')
        self.assertIsNone(parts['color'].source.catalog_key)
        self.assertEqual(parts['choice.0'].source.selected_text_sha256,
                         text_sha256('["cotton shirt","fitted"]'))
        self.assertEqual(dict(trace.omitted_parts)['material'], 'clothing.material_owned_by_garment')
        self.assertEqual(dict(trace.omitted_parts)['state'], 'clothing.state_location_disallowed:wet')
        self.assertEqual(trace.emitted_part_ids, ('color', 'pattern', 'style', 'choice.0', 'embellishment', 'optional_detail'))
        pack['choices']['top'][0][0] = 'changed'
        self.assertEqual(parts['choice.0'].text, 'fitted cotton shirt')
        from dataclasses import FrozenInstanceError
        with self.assertRaises(FrozenInstanceError):
            trace.parts = ()
        with self.assertRaises(FrozenInstanceError):
            parts['choice.0'].source.field = 'changed'

    def test_palette_origin_and_sanitized_fallback_hashes(self):
        from pipeline.realization_evidence import text_sha256
        pack = {'choices': {'top': ['shirt']}, 'palette': {'colors': ['orange']}}
        with patch.object(renderer.clothing_vocab, 'PALETTE_DEFAULT_PROBABILITIES', {'colors': 1}):
            trace = renderer.build_item_description_with_trace(random.Random(2), pack)[2]
        color = next(part for part in trace.parts if part.part_id == 'color')
        self.assertEqual(color.source.field, 'palette.colors')
        traces = []
        text, _ = renderer.render_clothing_candidate('unlisted  theme', 2, 'auto', .5, '', [], [], [], [],
                                                     trace_sink=traces.append)
        self.assertEqual(traces[0].raw_output_sha256, text_sha256('unlisted  theme layered top and practical trousers'))
        self.assertEqual(traces[0].emitted_output_sha256, text_sha256(text))
        with patch.object(renderer, 'build_item_description_with_trace', side_effect=AssertionError('trace requested')):
            renderer.render_clothing_candidate('casual', 2, 'auto', .5, '', [], [], [], [])

    def test_empty_pack_and_unknown_theme_keep_legacy_output(self):
        self.assertEqual(renderer.build_item_description_with_trace(random.Random(1), {})[:2], ('', ''))
        traces = []
        expected = renderer.render_clothing_candidate('unlisted', 2, 'auto', .5, '', [], [], [], [])
        actual = renderer.render_clothing_candidate('unlisted', 2, 'auto', .5, '', [], [], [], [], trace_sink=traces.append)
        self.assertEqual(actual, expected)
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0].constructor_id, 'clothing.candidate.fallback/v1')

    def test_unavailable_rng_state_does_not_claim_exact_replay(self):
        class NoState(random.Random):
            def getstate(self):
                raise NotImplementedError
        pack = {'choices': {'top': ['shirt']}}
        expected = renderer.build_item_description(NoState(2), pack)
        text, signature, trace = renderer.build_item_description_with_trace(NoState(2), pack)
        self.assertEqual((text, signature), expected)
        self.assertIsNone(trace)

    def test_bindings_include_rng_inputs_and_order(self):
        pack = {'choices': {'top': ['shirt'], 'bottom': ['trousers']}}
        normal = renderer.build_item_description_with_trace(random.Random(1), pack)[2]
        changed_seed = renderer.build_item_description_with_trace(random.Random(2), pack)[2]
        reversed_pack = {'choices': dict(reversed(list(pack['choices'].items())))}
        changed_order = renderer.build_item_description_with_trace(random.Random(1), reversed_pack)[2]
        self.assertNotEqual(normal.input_binding_sha256, changed_seed.input_binding_sha256)
        self.assertNotEqual(normal.input_binding_sha256, changed_order.input_binding_sha256)
        traces = []
        for attempt in (0, 1):
            renderer.render_clothing_candidate('casual', 1, 'auto', .5, '', [], [], [], [],
                                              attempt_index=attempt, trace_sink=traces.append)
        self.assertNotEqual(traces[0].input_binding_sha256, traces[1].input_binding_sha256)

    def test_candidate_rng_post_state_and_outerwear_sources(self):
        rng_factory = random.Random
        captured = []
        def capture(seed):
            rng = rng_factory(seed)
            captured.append(rng)
            return rng
        for mode in ('auto', 'no_outerwear', 'outerwear_only'):
            for seed in range(8):
                with patch.object(renderer.random, 'Random', side_effect=capture):
                    normal = renderer.render_clothing_candidate('casual', seed, mode, 1, 'violet', [], [], [], [])
                    traces = []
                    actual = renderer.render_clothing_candidate('casual', seed, mode, 1, 'violet', [], [], [], [],
                                                               trace_sink=traces.append)
                self.assertEqual(actual, normal)
                self.assertEqual(captured[-1].getstate(), captured[-2].getstate())
                if actual[1].get('outerwear_pack'):
                    outer = [part for part in traces[0].parts if part.part_id.startswith('outer.')]
                    self.assertTrue(outer)
                    for part in outer:
                        expected_key = None if part.source.field == 'character_palette.colors' else 'outerwear:' + actual[1]['outerwear_pack']
                        self.assertEqual(part.source.catalog_key, expected_key)
                    self.assertTrue(any(part.source.field == 'choices.outerwear' for part in outer))


if __name__ == '__main__':
    unittest.main()
