"""Structural grouping is text-free and re-proves current common inputs."""
import copy
from dataclasses import replace
import unittest

from assets.test_r43_family_capabilities import fixture_case, plan_for_inputs, replace_action
from tools.realizer_coverage_signatures import _shape, build_coverage_signature, coverage_signature_hash


FIELDS = {'subject': '{subj}', 'clothing': '{costume}', 'scene': '{loc}',
          'action': '{action}', 'garnish': '{garnish}', 'mood': '{meta_mood}'}


def snapshot_for(inputs):
    inputs = copy.deepcopy(inputs)
    inputs['composition_mode'] = True
    return {'raw_prompt': 'PRIVATE COMPLETE PROMPT', 'run_seed': 999,
            'common_evidence_inputs': copy.deepcopy(inputs),
            'finalization': {'composition_mode': True},
            'bridge': {'common_inputs': inputs, 'frame': copy.deepcopy(inputs['action_frame']),
                       'input_plan': plan_for_inputs(inputs).to_dict(),
                       'replacements': [(token, inputs[field]) for field, token in FIELDS.items()],
                       'common_proofs': [{'family': 'forged', 'eligible': True}]}}


def diagnosis():
    return {'route': 'fallback', 'domains': {}, 'families': {
        'z': {'runtime_eligible': False, 'blockers': ['scene.z', 'action.a', 'scene.z']},
        'a': {'runtime_eligible': True, 'blockers': []}}}


class TestCoverageSignature(unittest.TestCase):
    def signature(self, inputs):
        return build_coverage_signature(snapshot_for(inputs), diagnosis())

    def test_same_structure_different_text_has_same_signature(self):
        inputs, _, _ = fixture_case()
        before = self.signature(inputs)
        replace_action(inputs, {'primary_action': 'holding the bolt', 'location': 'opera_house'})
        self.assertEqual(before, self.signature(inputs))

    def test_clothing_fields_follow_emitted_order_not_selection_order(self):
        inputs, _, _ = fixture_case()
        self.assertEqual(self.signature(inputs)['domains']['clothing']['source_fields'],
                         ['palette.colors', 'choices.dresses'])

    def test_different_action_slot_sequence_changes_signature(self):
        inputs, _, _ = fixture_case()
        before = self.signature(inputs)
        replace_action(inputs, {'primary_action': 'holding the clipboard', 'posture': 'standing still',
                                'location': 'opera_house'})
        after = self.signature(inputs)
        self.assertEqual(after['domains']['action']['source_fields'], ['primary_action', 'posture'])
        self.assertNotEqual(coverage_signature_hash(before), coverage_signature_hash(after))

    def test_different_scene_source_fields_changes_signature(self):
        inputs, _, _ = fixture_case()
        before = self.signature(inputs)
        inputs['scene'] = inputs['context']['extras']['location_prompt'] = (
            'small contemporary gallery arranged for a weekday viewing, featuring '
            'framed canvas works spaced along the wall and small title plaques mounted beside each work')
        inputs['context']['loc'] = inputs['context']['extras']['raw_loc_tag'] = 'art_gallery'
        history = next(item for item in inputs['context']['history'] if item['node'] == 'ContextLocationExpander')
        history['decision'].update(pack_key='art_gallery', template_key='detailed')
        replace_action(inputs, {'primary_action': 'holding the clipboard', 'location': 'art_gallery'})
        after = self.signature(inputs)
        self.assertNotEqual(before['domains']['scene']['source_fields'], after['domains']['scene']['source_fields'])
        self.assertNotEqual(coverage_signature_hash(before), coverage_signature_hash(after))

    def test_signature_contains_no_full_prompt_or_seed(self):
        inputs, _, _ = fixture_case()
        forbidden_keys = {'raw_prompt', 'cleaned_prompt', 'legacy_text', 'source_text', 'run_seed'}
        forbidden_values = {inputs['action'], inputs['scene'], 'PRIVATE COMPLETE PROMPT', 'opera_house',
                            'dresses:winter_knit_dress', 'intro_plain_subject'}
        def check(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden_keys.intersection(value))
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
            elif isinstance(value, str):
                self.assertNotIn(value, forbidden_values)
        check(self.signature(inputs))

    def test_family_blockers_are_sorted_and_canonical(self):
        result = build_coverage_signature({'bridge': None}, diagnosis())
        self.assertEqual(result['proof_basis'], 'legacy_diagnostic')
        self.assertEqual(result['eligible_families'], ['a'])
        self.assertEqual(result['family_blockers'], {'a': [], 'z': ['action.a', 'scene.z']})

    def test_signature_is_identical_across_dict_insertion_order(self):
        inputs, _, _ = fixture_case()
        snapshot = snapshot_for(inputs)
        def reverse(value):
            if isinstance(value, dict):
                return {key: reverse(child) for key, child in reversed(list(value.items()))}
            if isinstance(value, list):
                return [reverse(child) for child in value]
            return value
        before = build_coverage_signature(snapshot, diagnosis())
        after = build_coverage_signature(reverse(snapshot), reverse(diagnosis()))
        self.assertEqual(before, after)
        self.assertEqual(coverage_signature_hash(before), coverage_signature_hash(after))

    def test_unknown_owner_stays_unknown(self):
        inputs, _, _ = fixture_case()
        replace_action(inputs, {'primary_action': 'contemplating the unsaid', 'location': 'opera_house'},
                       verb='contemplating')
        result = self.signature(inputs)
        self.assertEqual(result['domains']['action']['owners'], ['unknown'])
        self.assertEqual(result['domains']['scene']['owners'], ['unknown'])

    def test_body_and_event_subjects_have_coarse_owner_classes(self):
        inputs, _, _ = fixture_case()
        replace_action(inputs, {'primary_action': 'holding the clipboard', 'location': 'opera_house',
            'gaze_target': 'her eyes following the detail', 'obstacle_clause': 'while the inspection ends'})
        owners = self.signature(inputs)['domains']['action']['owners']
        self.assertIn('protagonist_body_part', owners)
        self.assertIn('scene_event', owners)

    def test_object_part_owner_uses_the_received_object_relation(self):
        from assets.test_r43_common_action_grammar import fixture

        inputs, _, _ = fixture_case()
        _, frame, context = fixture(object_state='open pages visible')
        inputs['action'] = inputs['context']['action'] = frame.legacy_text
        inputs['action_frame'] = frame.to_dict()
        inputs['context']['history'].extend(context['history'])
        self.assertIn('primary_object_part', self.signature(inputs)['domains']['action']['owners'])

    def test_outer_common_input_comparison_distinguishes_boolean_and_integer(self):
        inputs, _, _ = fixture_case()
        inputs['seed'] = 1
        snapshot = snapshot_for(inputs)
        snapshot['common_evidence_inputs']['seed'] = True
        result = build_coverage_signature(snapshot, diagnosis())
        self.assertEqual(result['proof_basis'], 'invalid_common_inputs')
        self.assertEqual(result['eligible_families'], [])

    def test_current_finalization_and_producer_context_must_match_common_inputs(self):
        from assets.test_r43_real_graph_placement import real_snapshot

        original = real_snapshot()
        self.assertEqual(build_coverage_signature(original, diagnosis())['proof_basis'],
                         'common_reconstructed')
        for mutation in ('final_action', 'final_replacements', 'producer_context', 'producer_palette'):
            with self.subTest(mutation=mutation):
                snapshot = copy.deepcopy(original)
                if mutation == 'final_action':
                    snapshot['finalization']['action'] = 'different current action'
                elif mutation == 'final_replacements':
                    replacements = snapshot['finalization']['replacements']
                    next(pair for pair in replacements if pair[0] == '{action}')[1] = 'different current action'
                elif mutation == 'producer_context':
                    snapshot['bridge']['producer_context']['context']['extras']['raw_mood_key'] = 'different'
                else:
                    snapshot['bridge']['producer_context']['character_palette'] = ['different']
                result = build_coverage_signature(snapshot, diagnosis())
                self.assertEqual(result['proof_basis'], 'invalid_common_inputs')
                self.assertEqual(result['eligible_families'], [])
                self.assertTrue(all('binding.current_input_mismatch' in ids
                                    for ids in result['family_blockers'].values()))

    def test_catalog_categories_preserve_bounded_source_origins(self):
        from assets.test_r43_real_graph_placement import real_snapshot

        result = build_coverage_signature(real_snapshot(), diagnosis())
        self.assertEqual(result['domains']['scene']['catalog_sources'], [
            'location_pack', 'background_defaults', 'location_pack', 'background_defaults',
            'location_pack', 'location_pack', 'location_pack'])
        inputs, _, _ = fixture_case()
        domains = self.signature(inputs)['domains']
        self.assertEqual(domains['clothing']['catalog_sources'], ['selected_clothing_pack'] * 2)
        self.assertEqual(domains['subject']['catalog_sources'], ['character_profile'] * 3)
        self.assertEqual(domains['template']['catalog_sources'], ['template_catalog'] * 3)
        self.assertEqual(domains['mood']['catalog_sources'], ['mood_catalog'])

    def test_projection_distinguishes_texture_origin_but_ignores_within_category_text(self):
        from assets.test_r43_real_graph_placement import real_snapshot
        from pipeline.realization_evidence import build_realization_evidence

        evidence = build_realization_evidence(real_snapshot()['bridge']['common_inputs'])
        component = next(item for item in evidence.components if item.domain == 'scene')
        index = next(i for i, part in enumerate(component.trace.parts) if part.source.field == 'texture')
        def project(catalog_key, text):
            parts = list(component.trace.parts)
            part = parts[index]
            parts[index] = replace(part, text=text, source=replace(part.source, catalog_key=catalog_key,
                                  selected_text_sha256='not-part-of-the-signature'))
            return _shape(replace(component, trace=replace(component.trace, parts=tuple(parts))))
        defaults = project('background_defaults', 'one diagnostic texture surface')
        first_pack = project('a_location_pack', 'another diagnostic texture surface')
        second_pack = project('another_location_pack', 'a third diagnostic texture surface')
        self.assertNotEqual(defaults, first_pack)
        self.assertEqual(first_pack, second_pack)
        self.assertEqual(first_pack['catalog_sources'][index], 'location_pack')

    def test_character_palette_source_is_not_a_selected_clothing_pack(self):
        _, _, evidence = fixture_case()
        component = next(item for item in evidence.components if item.domain == 'clothing')
        parts = tuple(replace(part, source=replace(part.source, field='character_palette.colors',
                      catalog_key=None)) if part.source.field == 'palette.colors' else part
                      for part in component.trace.parts)
        result = _shape(replace(component, trace=replace(component.trace, parts=parts)))
        self.assertEqual(result['catalog_sources'], ['character_palette', 'selected_clothing_pack'])

    def test_fallback_with_common_inputs_rebuilds_common_family_blockers(self):
        inputs, _, _ = fixture_case()
        result = self.signature(inputs)
        self.assertEqual(result['route'], 'fallback')
        self.assertEqual(result['proof_basis'], 'common_reconstructed')
        self.assertEqual(len(result['eligible_families']), 6)
        self.assertNotIn('forged', result['family_blockers'])
        replace_action(inputs, {'primary_action': 'contemplating the unsaid', 'location': 'opera_house'},
                       verb='contemplating')
        result = self.signature(inputs)
        self.assertEqual(result['eligible_families'], [])
        self.assertIn('action', result['blocked_domains'])
        self.assertTrue(all('action.leaf_grammar_unknown' in blockers
                            for blockers in result['family_blockers'].values()))

    def test_stale_common_inputs_do_not_grant_diagnostic_eligibility(self):
        inputs, _, _ = fixture_case()
        for mutation in ('replacement', 'frame', 'mode', 'outer', 'bool_int'):
            with self.subTest(mutation=mutation):
                snapshot = snapshot_for(inputs)
                if mutation == 'replacement':
                    snapshot['bridge']['replacements'][3] = ('{action}', 'different current action')
                elif mutation == 'frame':
                    snapshot['bridge']['frame']['main_verb'] = 'destroying'
                elif mutation == 'mode':
                    snapshot['finalization']['composition_mode'] = False
                elif mutation == 'outer':
                    snapshot['common_evidence_inputs']['seed'] += 1
                else:
                    snapshot['bridge']['common_inputs']['composition_mode'] = 1
                result = build_coverage_signature(snapshot, diagnosis())
                self.assertEqual(result['proof_basis'], 'invalid_common_inputs')
                self.assertEqual(result['eligible_families'], [])
                self.assertTrue(all('binding.current_input_mismatch' in ids
                                    for ids in result['family_blockers'].values()))


if __name__ == '__main__':
    unittest.main()
