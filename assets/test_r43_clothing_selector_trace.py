"""Selected-attempt traces preserve Clothing selection and public output."""
import copy
import random
import unittest
from unittest.mock import patch

from pipeline import clothing_candidate_selector as selector
from pipeline.clothing_semantics import build_clothing_target_vector
from pipeline.realization_evidence import ProducerTrace, text_sha256


def select_kwargs(**overrides):
    kwargs = dict(
        theme_key='casual', seed=23, outfit_mode='auto', outerwear_chance=0,
        character_palette='', loc='', recent_packs=[], recent_types=[],
        recent_outerwear=[], recent_signatures=[], clothing_tpo_enabled=False,
        clothing_tpo_active=False, clothing_target_vector={},
    )
    kwargs.update(overrides)
    return kwargs


def fixture_trace(attempt):
    return ProducerTrace(
        mode='exact_renderer_replay', producer='fixture',
        source_identity_sha256='a' * 64, input_binding_sha256=str(attempt) * 64,
        raw_output_sha256='b' * 64, emitted_output_sha256='b' * 64,
        parts=(), emitted_part_ids=(), omitted_parts=(), constructor_id='fixture',
    )


class TestR43ClothingSelectorTrace(unittest.TestCase):
    CASES = (
        # name, repeats, semantic penalties, enabled, active, selected, count, baseline
        ('later_best', (8, 7, 2, 4, 5), (0,) * 5, False, False, 2, 5, 0),
        ('tie_keeps_first', (2,) * 5, (0,) * 5, False, False, 0, 5, 0),
        ('later_zero_breaks', (7, 4, 0, 2, 1), (0,) * 5, False, False, 2, 3, 0),
        ('initial_zero_does_not_break', (0, 4, 0, 2, 1), (0,) * 5, False, False, 0, 5, 0),
        ('inactive_tpo', (8, 6, 2, 5, 7), (0, 0, 9, 0, 0), True, False, 2, 5, 2),
        ('active_tpo_baseline_differs', (8, 2, 4, 1, 7), (0, 9, 0, 9, 0), True, True, 2, 5, 3),
        ('active_tpo_break', (8, 2, 0, 1, 7), (0, 9, 0, 9, 0), True, True, 2, 3, 2),
    )

    def run_case(self, case, *, traced=False):
        _name, repeats, penalties, enabled, active, selected, count, baseline = case
        attempts, callbacks, emitted = [], [], []

        def render(*args, **kwargs):
            attempt = kwargs['attempt_index']
            attempts.append(attempt)
            callback = kwargs.get('trace_sink')
            callbacks.append('trace_sink' in kwargs)
            if callback is not None:
                callback(fixture_trace(attempt))
            return f'garment {attempt}', {'attempt_index': attempt, 'repeat_guard_penalty': repeats[attempt]}

        def score(decision, prompt, target):
            attempt = decision['attempt_index']
            return {'score': 100 - penalties[attempt], 'distance': attempt, 'semantic_penalty': penalties[attempt]}

        def sink(trace):
            # The selected trace must be emitted only after all candidate work.
            self.assertEqual(len(attempts), count)
            emitted.append(trace)

        kwargs = select_kwargs(clothing_tpo_enabled=enabled, clothing_tpo_active=active)
        if traced:
            kwargs['trace_sink'] = sink
        with patch.object(selector, 'render_clothing_candidate', render), patch.object(selector, 'score_clothing_decision', score):
            result = selector.select_clothing_candidate(**kwargs)
        self.assertEqual(attempts, list(range(count)))
        self.assertEqual(callbacks, [traced] * count)
        self.assertEqual(result[0], f'garment {selected}')
        expected_decision = {'attempt_index': selected, 'repeat_guard_penalty': repeats[selected]}
        expected_scores = []
        if enabled:
            expected_decision.update(
                semantic_tpo_score=100 - penalties[selected], semantic_tpo_penalty=penalties[selected],
                semantic_tpo_distance=selected,
                semantic_tpo_final_penalty=repeats[selected] + (penalties[selected] if active else 0),
            )
            expected_scores = [dict(
                attempt_index=i, score=100 - penalties[i], distance=i,
                semantic_penalty=penalties[i], repeat_penalty=repeats[i],
                final_penalty=repeats[i] + (penalties[i] if active else 0),
            ) for i in range(count)]
        self.assertEqual(result, (f'garment {selected}', expected_decision, expected_scores, baseline))
        self.assertEqual(emitted, [fixture_trace(selected)] if traced else [])
        return result

    def test_existing_selection_contract(self):
        for case in self.CASES:
            with self.subTest(case=case[0]):
                self.run_case(case)

    def test_sink_receives_only_selected_attempt_and_preserves_output(self):
        for case in self.CASES:
            with self.subTest(case=case[0]):
                baseline = self.run_case(case)
                self.assertEqual(self.run_case(case, traced=True), baseline)

    def test_none_sink_does_not_request_renderer_trace(self):
        def render(*args, **kwargs):
            self.assertNotIn('trace_sink', kwargs)
            return 'garment', {'attempt_index': kwargs['attempt_index']}

        with patch.object(selector, 'render_clothing_candidate', render):
            selector.select_clothing_candidate(**select_kwargs(), trace_sink=None)

    def test_real_renderer_semantic_modes_preserve_output_and_selected_trace(self):
        for theme, mode, loc in (
            ('casual', 'no_outerwear', 'cozy_living_room'),
            ('office_lady', 'auto', 'winter_street'),
            ('rainy_day', 'outerwear_only', 'rainy_bus_stop'),
        ):
            for seed in (23, 51):
                for enabled, active in ((False, False), (True, False), (True, True)):
                    with self.subTest(theme=theme, seed=seed, enabled=enabled, active=active):
                        kwargs = select_kwargs(
                            theme_key=theme, seed=seed, outfit_mode=mode, loc=loc,
                            outerwear_chance=1, character_palette='navy, cream',
                            recent_types=['dresses', 'separates'],
                            clothing_tpo_enabled=enabled, clothing_tpo_active=active,
                            clothing_target_vector=build_clothing_target_vector(loc, 'commuting', theme),
                        )
                        before, rng_before = copy.deepcopy(kwargs), random.getstate()
                        baseline = selector.select_clothing_candidate(**kwargs)
                        emitted = []
                        observed = selector.select_clothing_candidate(**kwargs, trace_sink=emitted.append)
                        self.assertEqual(observed, baseline)
                        self.assertEqual(kwargs, before)
                        self.assertEqual(random.getstate(), rng_before)
                        self.assertEqual(len(emitted), 1)
                        self.assertIsInstance(emitted[0], ProducerTrace)
                        self.assertEqual(emitted[0].emitted_output_sha256, text_sha256(observed[0]))
                        renderer_kwargs = {key: value for key, value in kwargs.items()
                                           if not key.startswith('clothing_')}
                        direct_traces = []
                        direct_prompt, direct_decision = selector.render_clothing_candidate(
                            **renderer_kwargs, attempt_index=observed[1].get('attempt_index', 0),
                            trace_sink=direct_traces.append,
                        )
                        self.assertEqual(emitted, direct_traces)
                        self.assertEqual(direct_prompt, observed[0])
                        if enabled:
                            selector.annotate_clothing_candidate(
                                direct_decision, direct_prompt, kwargs['clothing_target_vector'], active,
                            )
                        self.assertEqual(direct_decision, observed[1])


if __name__ == '__main__':
    unittest.main()
