import hashlib
import json
import os
import random
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline import location_builder as renderer


class AllDraws(random.Random):
    """Select every optional branch and the last eligible candidate."""
    def random(self):
        return 0.0

    def choice(self, values):
        return values[-1]

    def choices(self, values, weights=None, *, cum_weights=None, k=1):
        return [values[-1]] * k

    def shuffle(self, values):
        values.reverse()


class SceneTraceTests(unittest.TestCase):
    def test_pre_refactor_output_debug_and_rng_baseline(self):
        factory = random.Random
        rows = []
        for key in renderer.background_vocab.CONCEPT_PACKS:
            for seed in range(6):
                for mode in ('simple', 'detailed'):
                    for lighting in ('auto', 'off'):
                        captured = []
                        def capture(seed):
                            rng = factory(seed)
                            captured.append(rng)
                            return rng
                        with patch.object(renderer.random, 'Random', side_effect=capture):
                            result = renderer.expand_location_prompt(key, seed, mode, lighting,
                                return_debug=True, action_text='looking around', mood_text='calm',
                                recent_objects=['book'])
                        rows.append((key, seed, mode, lighting, result, captured[-1].getstate()))
        self.assertEqual(len(rows), 2736)
        digest = hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False,
            separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(digest, '430bb5e5df41fb4524e0e26f1674a0895e84906a198b5a352c66abc80a3a593e')

    def test_trace_preserves_outputs_debug_and_rng(self):
        from pipeline.realization_evidence import text_sha256
        factory = random.Random
        for key in renderer.background_vocab.CONCEPT_PACKS:
            for mode in ('simple', 'detailed'):
                for lighting in ('auto', 'off'):
                    captured = []
                    def capture(seed):
                        rng = factory(seed)
                        captured.append(rng)
                        return rng
                    traces = []
                    with patch.object(renderer.random, 'Random', side_effect=capture):
                        expected = renderer.expand_location_prompt(key, 17, mode, lighting, return_debug=True)
                        actual = renderer.expand_location_prompt(key, 17, mode, lighting,
                            return_debug=True, trace_sink=traces.append)
                    self.assertEqual(actual, expected)
                    self.assertEqual(captured[0].getstate(), captured[1].getstate())
                    self.assertEqual(len(traces), 1)
                    self.assertEqual(traces[0].mode, 'exact_renderer_replay')
                    self.assertEqual(traces[0].emitted_output_sha256, text_sha256(actual[0]))
                    self.assert_plain_json(actual)

    def assert_plain_json(self, value):
        if isinstance(value, str):
            self.assertIs(type(value), str)
        elif isinstance(value, dict):
            for key, child in value.items():
                self.assert_plain_json(key)
                self.assert_plain_json(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                self.assert_plain_json(child)

    def test_semantic_modes_preserve_draws_and_plain_debug(self):
        from pipeline import semantic_epig
        factory = random.Random
        bindings = []
        for semantic in ('off', 'passive', 'active'):
            with patch.object(semantic_epig, 'semantic_mode', return_value=semantic), \
                 patch.object(renderer, 'semantic_mode', return_value=semantic):
                for lighting in ('auto', 'off'):
                    for seed in range(12):
                        captured = []
                        def capture(seed):
                            rng = factory(seed)
                            captured.append(rng)
                            return rng
                        traces = []
                        with patch.object(renderer.random, 'Random', side_effect=capture):
                            expected = renderer.expand_location_prompt('art_gallery', seed, 'detailed',
                                lighting, return_debug=True)
                            actual = renderer.expand_location_prompt('art_gallery', seed, 'detailed',
                                lighting, return_debug=True, trace_sink=traces.append)
                        self.assertEqual(actual, expected)
                        self.assertEqual(captured[0].getstate(), captured[1].getstate())
                        self.assert_plain_json(actual)
                        if seed == 0 and lighting == 'auto':
                            bindings.append(traces[0].input_binding_sha256)
        self.assertEqual(len(set(bindings)), 3)

    def test_atomic_fields_defaults_shuffle_and_text_dedupe(self):
        from dataclasses import FrozenInstanceError
        from pipeline.realization_evidence import text_sha256
        pack = {'environment': ['a gallery'], 'core': ['arched walls and carved trim', 'wide halls'],
            'props': ['plain pedestals', 'framed displays'], 'texture': ['shared surface'],
            'time': ['morning'], 'weather': ['clear skies'], 'crowd': ['quiet air'], 'fx': ['soft haze']}
        defaults = {'texture': ['shared surface'], 'details': ['shared surface'], 'fx': ['soft haze']}
        traces = []
        with patch.dict(renderer.background_vocab.CONCEPT_PACKS, {'trace_test': pack}), \
             patch.object(renderer.background_vocab, 'GENERAL_DEFAULTS', defaults), \
             patch.object(renderer.random, 'Random', AllDraws):
            expected = renderer.expand_location_prompt('trace_test', 8, 'detailed', return_debug=True)
            actual = renderer.expand_location_prompt('trace_test', 8, 'detailed', return_debug=True,
                trace_sink=traces.append)
        self.assertEqual(actual, expected)
        self.assert_plain_json(actual)
        trace = traces[0]
        parts = {part.part_id: part for part in trace.parts}
        self.assertEqual({part.source.field for part in trace.parts},
            {'environment', 'core', 'props', 'texture', 'details', 'time', 'weather', 'crowd', 'fx'})
        self.assertEqual(parts['texture'].source.catalog_key, 'background_defaults')
        self.assertEqual(parts['details'].source.catalog_key, 'background_defaults')
        self.assertEqual(parts['fx'].source.catalog_key, 'background_defaults')
        self.assertEqual(parts['core.1'].text, 'arched walls and carved trim')
        self.assertEqual(parts['core.1'].source.selected_text_sha256, text_sha256('arched walls and carved trim'))
        self.assertEqual(parts['environment'].source.catalog_key, 'trace_test')
        self.assertEqual(trace.emitted_part_ids,
            ('environment', 'fx', 'crowd', 'weather', 'time', 'details', 'props.0', 'props.1', 'core.0', 'core.1'))
        self.assertEqual(trace.omitted_parts, (('texture', 'scene.duplicate_segment_text'),))
        self.assertEqual(actual[0].count('shared surface'), 1)
        self.assertIn('featuring wide halls and arched walls and carved trim', actual[0])
        pack['core'][1] = 'changed'
        defaults['texture'][0] = 'changed'
        self.assertEqual(parts['core.0'].text, 'wide halls')
        self.assertEqual(parts['texture'].text, 'shared surface')
        with self.assertRaises(FrozenInstanceError):
            trace.parts = ()
        with self.assertRaises(FrozenInstanceError):
            parts['texture'].source.field = 'changed'

    def test_duplicate_candidate_origin_tracks_selected_instance(self):
        class FirstDraws(AllDraws):
            def choice(self, values):
                return values[0]
            def choices(self, values, weights=None, *, cum_weights=None, k=1):
                return [values[0]] * k
        pack = {'environment': ['a gallery'], 'texture': ['woven surfaces'], 'fx': ['soft haze']}
        defaults = {'texture': ['woven surfaces'], 'fx': ['soft haze']}
        for factory, origin in ((AllDraws, 'background_defaults'), (FirstDraws, 'trace_test')):
            with patch.dict(renderer.background_vocab.CONCEPT_PACKS, {'trace_test': pack}), \
                 patch.object(renderer.background_vocab, 'GENERAL_DEFAULTS', defaults), \
                 patch.object(renderer.random, 'Random', factory):
                traces = []
                renderer.expand_location_prompt('trace_test', 8, 'detailed', trace_sink=traces.append)
            selected = {part.source.field: part for part in traces[0].parts}
            self.assertEqual(selected['texture'].source.catalog_key, origin)
            self.assertEqual(selected['fx'].source.catalog_key, origin)

    def test_raw_source_hashes_survive_normalization_collisions(self):
        from pipeline.realization_evidence import text_sha256
        raw_fields = {'environment': 'a gallery', 'core': 'arched walls',
            'props': 'plain pedestals', 'texture': 'woven surfaces',
            'time': 'morning', 'weather': 'clear skies', 'crowd': 'quiet air'}
        pack = {field: [text, '  ' + text + '  '] for field, text in raw_fields.items()}
        # Unlike other fields, the existing FX filter removes duplicates before
        # selection, retaining the first raw occurrence in each origin's list.
        pack['fx'] = ['  soft haze  ', 'soft haze']
        defaults = {'details': ['subtle contours', '  subtle contours  '],
            'texture': ['woven surfaces', '  woven surfaces  '],
            'fx': ['  soft haze  ', 'soft haze']}
        traces = []
        with patch.dict(renderer.background_vocab.CONCEPT_PACKS, {'trace_test': pack}), \
             patch.object(renderer.background_vocab, 'GENERAL_DEFAULTS', defaults), \
             patch.object(renderer.random, 'Random', AllDraws):
            expected = renderer.expand_location_prompt('trace_test', 8, 'detailed', return_debug=True)
            actual = renderer.expand_location_prompt('trace_test', 8, 'detailed', return_debug=True,
                trace_sink=traces.append)
        self.assertEqual(actual, expected)
        self.assert_plain_json(actual)
        for part in traces[0].parts:
            field = part.source.field
            text = raw_fields.get(field, 'subtle contours' if field == 'details' else 'soft haze')
            self.assertEqual(part.text, text)
            self.assertEqual(part.source.selected_text_sha256, text_sha256('  ' + text + '  '))
            self.assertNotEqual(part.source.selected_text_sha256, text_sha256(text))
            self.assertEqual(part.source.catalog_key,
                'background_defaults' if field in ('texture', 'details', 'fx') else 'trace_test')

    def test_selected_core_rejected_by_repeat_budget_keeps_raw_source(self):
        from pipeline.realization_evidence import text_sha256
        pack = {'environment': ['a gallery'], 'core': ['  decorative plant  ', 'framed poster']}
        self.assertTrue(renderer.background_repeat_risk_flags('decorative plant'))
        self.assertTrue(renderer.background_repeat_risk_flags('framed poster'))
        traces = []
        captured = []
        def capture(seed):
            rng = AllDraws(seed)
            captured.append(rng)
            return rng
        with patch.dict(renderer.background_vocab.CONCEPT_PACKS, {'trace_test': pack}), \
             patch.object(renderer.background_vocab, 'GENERAL_DEFAULTS', {}), \
             patch.object(renderer.random, 'Random', side_effect=capture):
            expected = renderer.expand_location_prompt('trace_test', 8, 'detailed', return_debug=True)
            actual = renderer.expand_location_prompt('trace_test', 8, 'detailed', return_debug=True,
                trace_sink=traces.append)
        self.assertEqual(actual, expected)
        self.assertEqual(captured[0].getstate(), captured[1].getstate())
        self.assertEqual(actual[0], 'a gallery, featuring framed poster')
        trace = traces[0]
        self.assertEqual(trace.emitted_part_ids, ('environment', 'core.0'))
        self.assertEqual(trace.omitted_parts, (('core.suppressed.1', 'scene.repeat_risk_budget'),))
        rejected = next(part for part in trace.parts if part.part_id == 'core.suppressed.1')
        self.assertEqual(rejected.text, 'decorative plant')
        self.assertEqual(rejected.source.field, 'core')
        self.assertEqual(rejected.source.catalog_key, 'trace_test')
        self.assertEqual(rejected.source.selected_text_sha256, text_sha256('  decorative plant  '))

    def test_equal_text_core_suppression_retains_drawn_raw_instance(self):
        from pipeline.realization_evidence import text_sha256
        class FirstDraws(AllDraws):
            def choices(self, values, weights=None, *, cum_weights=None, k=1):
                return [values[0]] * k
        pack = {'environment': ['a gallery'], 'core': ['decorative plant', '  decorative plant  ']}
        traces = []
        with patch.dict(renderer.background_vocab.CONCEPT_PACKS, {'trace_test': pack}), \
             patch.object(renderer.background_vocab, 'GENERAL_DEFAULTS', {}), \
             patch.object(renderer.random, 'Random', FirstDraws):
            expected = renderer.expand_location_prompt('trace_test', 8, 'detailed', return_debug=True)
            actual = renderer.expand_location_prompt('trace_test', 8, 'detailed', return_debug=True,
                trace_sink=traces.append)
        self.assertEqual(actual, expected)
        trace = traces[0]
        parts = {part.part_id: part for part in trace.parts}
        self.assertEqual(trace.emitted_part_ids, ('environment', 'core.0'))
        self.assertEqual(trace.omitted_parts, (('core.suppressed.1', 'scene.repeat_risk_budget'),))
        self.assertEqual(parts['core.0'].text, parts['core.suppressed.1'].text)
        self.assertEqual(parts['core.0'].source.selected_text_sha256, text_sha256('decorative plant'))
        self.assertEqual(parts['core.suppressed.1'].source.selected_text_sha256,
            text_sha256('  decorative plant  '))

    def test_fallback_origins_and_shared_assembly(self):
        from pipeline.realization_evidence import text_sha256
        for tag, pack, constructor in (('no such  location', None, 'scene.fallback/v1'),
                                      ('trace_test', {'core': ['walls']}, 'scene.simple/v1')):
            traces = []
            with patch.dict(renderer.background_vocab.CONCEPT_PACKS, {tag: pack}):
                prompt = renderer.expand_location_prompt(tag, 8, 'simple', trace_sink=traces.append)
            self.assertEqual(traces[0].constructor_id, constructor)
            self.assertIsNone(traces[0].parts[0].source.catalog_key)
            self.assertEqual(traces[0].parts[0].source.field, 'loc_tag')
            self.assertEqual(traces[0].emitted_output_sha256, text_sha256(prompt))
        self.assertEqual(renderer._assemble_location_prompt('a  gallery', ['quiet air']),
            ('a  gallery, quiet air', 'a gallery, quiet air'))

    def test_binding_covers_renderer_inputs_and_catalog(self):
        base = {'loc_tag': 'art_gallery', 'seed': 1, 'mode': 'detailed'}
        variations = ({'seed': 2}, {'mode': 'simple'}, {'lighting_mode': 'off'},
                      {'action_text': 'walking'}, {'mood_text': 'calm'}, {'recent_objects': ['book']})
        traces = []
        renderer.expand_location_prompt(**base, trace_sink=traces.append)
        for change in variations:
            renderer.expand_location_prompt(**(base | change), trace_sink=traces.append)
        self.assertEqual(len({trace.input_binding_sha256 for trace in traces}), len(traces))
        with patch.object(renderer.background_vocab, 'GENERAL_DEFAULTS', {'details': ['changed']}):
            renderer.expand_location_prompt(**base, trace_sink=traces.append)
        self.assertNotEqual(traces[0].input_binding_sha256, traces[-1].input_binding_sha256)


if __name__ == '__main__':
    unittest.main()
