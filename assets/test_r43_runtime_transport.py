"""Diagnostic transport must leave ordinary Builder behavior untouched."""
import copy
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import prompt_renderer
from core.schema import PromptContext
from pipeline.prompt_orchestrator import build_prompt_from_context
from pipeline.prompt_realizer import build_content_plan, realize_content_plan
from pipeline.v2_candidate_bridge import render_candidate


class TestR43RuntimeTransport(unittest.TestCase):
    def test_existing_prompt_baselines(self):
        self.assertEqual(prompt_renderer.build_prompt_text(
            '{subj}, {action}, {loc}. {staging_tags}', False, 7,
            subj='a solo woman', action='walking, standing still',
            loc='station platform', staging_tags='solo'),
            'a solo girl, walking, standing still, covered station platform with route signs, '
            'during morning commute, bright overcast sky beyond the tracks. solo')
        self.assertEqual(prompt_renderer.build_prompt_text(
            '', True, 7, subj='a solo girl', costume='a navy coat',
            loc='station platform', action='checking a transit card'),
            'a solo girl in a navy coat, checking a transit card, and the room around her '
            'staying in covered station platform with route signs, during morning commute, '
            'bright overcast sky beyond the tracks')

    def test_sink_parity_context_history_rng_and_rollback(self):
        context = PromptContext.from_dict({'subj': 'a solo girl', 'loc': 'station platform',
                                          'action': 'checking a transit card'})
        for mode in (True, False):
            for seed in range(16):
                with self.subTest(mode=mode, seed=seed):
                    original = copy.deepcopy(context.to_dict())
                    rng_state = random.getstate()
                    plain, text = build_prompt_from_context(context, '', mode, seed)
                    snapshots = []
                    observed, actual = build_prompt_from_context(
                        context, '', mode, seed, audit_sink=snapshots.append)
                    self.assertEqual(actual, text)
                    self.assertEqual(observed.to_dict(), plain.to_dict())
                    self.assertEqual(context.to_dict(), original)
                    self.assertEqual(random.getstate(), rng_state)
                    self.assertEqual(len(snapshots), 1)
                    snapshot = snapshots[0]
                    self.assertEqual(json.loads(json.dumps(snapshot)), snapshot)
                    self.assertEqual(snapshot['raw_prompt'], text)
                    if mode:
                        bridge = snapshot['bridge']
                        self.assertEqual(bridge['selectable'], sorted(bridge['selectable']))
                        self.assertEqual(prompt_renderer._finalize_prompt(
                            bridge['output_template'], **snapshot['finalization']), text)
                    else:
                        self.assertIsNone(snapshot['bridge'])
        # The audit remains detached when the next Builder receives existing history.
        snapshots = []
        replay, replay_text = build_prompt_from_context(plain, '', True, 22)
        observed, actual = build_prompt_from_context(plain, '', True, 22, audit_sink=snapshots.append)
        self.assertEqual((observed.to_dict(), actual), (replay.to_dict(), replay_text))

    def test_callback_mutation_does_not_reach_outputs_or_inputs(self):
        context = PromptContext.from_dict({'subj': 'a solo girl', 'action': 'reading a book'})
        original = copy.deepcopy(context.to_dict())
        expected, text = build_prompt_from_context(context, '', True, 7)
        def mutate(snapshot):
            snapshot['bridge']['eligibility'].clear()
            snapshot['bridge']['output_debug'].clear()
            snapshot['bridge']['input_plan'].clear()
            snapshot['finalization']['replacements'].clear()
            snapshot.clear()
        actual, actual_text = build_prompt_from_context(context, '', True, 7, audit_sink=mutate)
        self.assertEqual((actual.to_dict(), actual_text), (expected.to_dict(), text))
        self.assertEqual(context.to_dict(), original)

    def test_direct_bridge_snapshot_and_attempted_selection_on_fallback(self):
        plan = build_content_plan(seed=7, subject_clause='a solo girl',
                                  action_clause='checks a transit card', scene_clause='at a station',
                                  action_frame=None, syntax_family='single-sentence-scene-tail')
        template, debug = realize_content_plan(plan, return_debug=True)
        surface = {'surface': 'clause'}
        snapshots = []
        def mutate(snapshot):
            snapshots.append(copy.deepcopy(snapshot))
            snapshot['output_debug'].clear()
            snapshot['source_surface'].clear()
        eligible = {'direct_provenance_valid': False, 'direct_supported_families': []}
        with patch('pipeline.v2_candidate_bridge.eligible_syntax_families',
                   return_value=(['subject_action_scene'], eligible)), \
             patch('pipeline.v2_candidate_bridge.candidate_family_safe', return_value=True), \
             patch('pipeline.v2_candidate_bridge.realize_content_plan', return_value=(template, debug)):
            actual, _, result_debug = render_candidate(
                plan, template, debug, {}, surface, [], 7, audit_sink=mutate)
        self.assertEqual(actual, template)
        self.assertFalse(result_debug['candidate_v2_applied'])
        self.assertEqual(snapshots[0]['selected'], 'subject_action_scene')
        self.assertEqual(snapshots[0]['output_debug'], result_debug)
        self.assertEqual(surface, {'surface': 'clause'})
        self.assertEqual(snapshots[0], json.loads(json.dumps(snapshots[0])))

    def test_sink_free_does_not_materialize_snapshot(self):
        with patch('pipeline.v2_candidate_bridge.deepcopy', side_effect=AssertionError('snapshot allocated')):
            prompt_renderer.build_prompt_text('', True, 7, subj='a solo girl', action='reading a book')

    def test_package_sink_in_fresh_process(self):
        code = '''
import importlib.util, json, sys
from pathlib import Path
root = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('scg_sink', root / '__init__.py', submodule_search_locations=[str(root)])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
from scg_sink.core.schema import PromptContext
from scg_sink.pipeline.prompt_orchestrator import build_prompt_from_context
context = PromptContext.from_dict({'subj': 'a solo girl', 'action': 'reading a book'})
plain, text = build_prompt_from_context(context, '', True, 7)
snapshots = []
observed, actual = build_prompt_from_context(context, '', True, 7, audit_sink=snapshots.append)
assert (observed.to_dict(), actual) == (plain.to_dict(), text)
assert len(snapshots) == 1 and snapshots[0]['raw_prompt'] == text
assert snapshots == json.loads(json.dumps(snapshots))
assert 'prompt_renderer' not in sys.modules
print(json.dumps(snapshots[0], sort_keys=True))
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(ROOT)],
                                capture_output=True, text=True, encoding='utf-8', check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        snapshots = []
        context = PromptContext.from_dict({'subj': 'a solo girl', 'action': 'reading a book'})
        build_prompt_from_context(context, '', True, 7, audit_sink=snapshots.append)
        self.assertEqual(json.loads(result.stdout), snapshots[0])


if __name__ == '__main__':
    unittest.main()
