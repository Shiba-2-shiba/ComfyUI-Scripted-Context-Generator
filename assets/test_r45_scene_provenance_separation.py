"""Exact Scene origin survives unproved grammar without granting permission."""
import copy
from contextlib import ExitStack
from dataclasses import asdict, replace
import hashlib
import json
import unittest
from unittest.mock import patch

from assets.test_r43_family_capabilities import fixture_case, engine, plan_for_inputs
from assets.test_r43_scene_binding import context as known_context
from pipeline.realization_evidence import Truth, build_realization_evidence
from pipeline import v2_scene_provenance as scene


PACKS = {'test_room': {
    'environment': ['radiant observatory'], 'core': ['telescopes beneath the dome'],
    'props': [], 'time': [], 'texture': [], 'fx': [], 'weather': [], 'crowd': [],
}}
DEFAULTS = {'details': [], 'texture': [], 'fx': []}


def unknown_grammar_scene_context():
    value = 'radiant observatory, featuring telescopes beneath the dome'
    return {'loc': 'test_room', 'extras': {'raw_loc_tag': 'test_room', 'location_prompt': value},
            'history': [{'node': 'ContextLocationExpander', 'seed': 7, 'decision': {
                'pack_key': 'test_room', 'template_key': 'detailed', 'selected_props': [],
                'semantic_epig': {'location_scene': {'section_changes': {
                    'core': {'semantic': ['telescopes beneath the dome']}}}},
            }}]}, value


class SceneSeparationTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(scene, 'load_background_packs', return_value=copy.deepcopy(PACKS)))
        original = scene.load_json
        self.stack.enter_context(patch.object(scene, 'load_json', side_effect=lambda name:
            DEFAULTS if name == 'background_defaults.json' else original(name)))

    def adapt(self, ctx=None):
        ctx = unknown_grammar_scene_context()[0] if ctx is None else ctx
        return scene.adapt_scene_component(ctx, frame_value=None,
            input_binding_sha256='input', source_identity_sha256='source')

    def family_case(self):
        inputs, _, _ = fixture_case()
        ctx, value = unknown_grammar_scene_context()
        inputs['scene'] = inputs['context']['extras']['location_prompt'] = value
        inputs['context']['loc'] = inputs['context']['extras']['raw_loc_tag'] = 'test_room'
        inputs['context']['history'] = [row for row in inputs['context']['history']
            if row['node'] != 'ContextLocationExpander'] + ctx['history']
        inputs['action_frame']['legacy_slots']['location'] = 'test_room'
        evidence = build_realization_evidence(inputs)
        recovered = scene.adapt_scene_component(inputs['context'], inputs['scene'], inputs['action_frame'],
            input_binding_sha256=evidence.input_binding_sha256,
            source_identity_sha256=evidence.source_identity_sha256)
        evidence = replace(evidence, components=tuple(recovered if c.domain == 'scene' else c
            for c in evidence.components))
        return recovered, engine().prove_all_families(plan_for_inputs(inputs), evidence, builder_inputs=inputs)

    def test_exact_source_survives_unknown_grammar(self):
        component = self.adapt()
        self.assertIsNotNone(component.trace)
        self.assertTrue(component.runtime_available)
        self.assertTrue(component.atoms)
        self.assertTrue(all(atom.grammar_known is Truth.UNKNOWN for atom in component.atoms))
        self.assertIn('scene.grammar_unknown', component.blockers)
        self.assertIn('scene.r45_source_only_permission_deferred', component.blockers)
        self.assertNotIn('scene.source_unavailable', component.blockers)
        self.assertEqual(component.trace.constructor_id, 'scene.r45_source_bound_unproved/v1')
        self.assertEqual(dict(component.facts), {'source_order_known': Truth.TRUE,
            'ownership_known': Truth.UNKNOWN, 'frame_location_matches': Truth.UNKNOWN})
        for atom in component.atoms:
            self.assertEqual((atom.grammatical_subject_id, atom.owner_id, atom.form,
                atom.attachment, atom.same_subject, atom.place_refs, atom.antecedent_ids,
                atom.rule_ids, atom.grammatical_head),
                (None, None, 'unknown', 'unknown', Truth.UNKNOWN, None, None, (), None))

    def test_missing_source_stays_unavailable(self):
        ctx, _ = unknown_grammar_scene_context()
        ctx['extras']['location_prompt'] = 'unlisted observatory'
        component = self.adapt(ctx)
        self.assertIsNone(component.trace)
        self.assertFalse(component.runtime_available)
        self.assertIn('scene.source_unavailable', component.blockers)

    def test_unknown_scene_blocks_all_real_family_proofs(self):
        component, proofs = self.family_case()
        self.assertIsNotNone(component.trace)
        self.assertEqual(len(proofs), 6)
        for proof in proofs:
            self.assertFalse(proof.eligible)
            self.assertIn('scene.grammar_unknown', proof.blocker_ids)

    def test_source_only_route_defers_even_when_all_atoms_are_known(self):
        with patch.object(scene, '_producer_scene_components', return_value=None), patch.object(
                scene, '_classify_bound_scene_part', create=True, return_value=('a gallery', 'gallery', None)):
            component, proofs = self.family_case()
            self.assertIsNotNone(component.trace)
            self.assertTrue(all(atom.grammar_known is Truth.TRUE for atom in component.atoms))
            self.assertIn('scene.r45_source_only_permission_deferred', component.blockers)
            self.assertEqual(dict(component.facts)['ownership_known'], Truth.TRUE)
            for proof in proofs:
                self.assertFalse(proof.eligible)
                self.assertIn('scene.r45_source_only_permission_deferred', proof.blocker_ids)

    def test_source_binding_never_calls_grammar(self):
        with ExitStack() as stack:
            for name in ('_common_scene_nominal', '_scene_nominal', '_nominal'):
                stack.enter_context(patch.object(scene, name, side_effect=AssertionError('grammar called')))
            ctx, value = unknown_grammar_scene_context()
            bound = scene._bind_scene_source_parts(value, ctx['loc'])
        self.assertEqual([(p.field, p.raw, p.source_key) for p in bound[0]], [
            ('environment', 'radiant observatory', 'test_room'),
            ('core', 'telescopes beneath the dome', 'test_room')])

    def test_recovered_known_part_retains_common_grammar_rule(self):
        packs = copy.deepcopy(PACKS)
        packs['test_room']['environment'] = ['professional recording booth']
        ctx, _ = unknown_grammar_scene_context()
        ctx['extras']['location_prompt'] = 'professional recording booth, featuring telescopes beneath the dome'
        with patch.object(scene, 'load_background_packs', return_value=packs):
            component = self.adapt(ctx)
        self.assertEqual(component.atoms[0].grammar_known, Truth.TRUE)
        self.assertEqual(component.atoms[0].rule_ids, ('v2_scene_provenance.common_nominal:environment/v1',))
        self.assertEqual(component.atoms[1].grammar_known, Truth.UNKNOWN)
        self.assertIn('scene.r45_source_only_permission_deferred', component.blockers)

    def test_recovered_nominal_part_retains_nominal_grammar_rule(self):
        packs = copy.deepcopy(PACKS)
        packs['test_room']['environment'] = ['cozy bedroom']
        ctx, _ = unknown_grammar_scene_context()
        ctx['extras']['location_prompt'] = 'cozy bedroom, featuring telescopes beneath the dome'
        with patch.object(scene, 'load_background_packs', return_value=packs):
            component = self.adapt(ctx)
        self.assertEqual(component.atoms[0].rule_ids, ('v2_scene_provenance.nominal:environment/v1',))

    def test_rendering_still_requires_grammar(self):
        _, value = unknown_grammar_scene_context()
        for constructor in (scene.producer_owned_scene, scene.common_scene_parts, scene.common_standalone_scene_parts):
            self.assertIsNone(constructor(value, 'test_room'))


def test_known_scene_matches_pre_refactor_complete_evidence_snapshot():
    component = scene.adapt_scene_component(known_context(),
        input_binding_sha256='input', source_identity_sha256='source')
    data = json.dumps(asdict(component), default=lambda value: value.value,
        sort_keys=True, separators=(',', ':')).encode()
    # Captured before R45-03: trace, source parts, every atom/fact and blocker.
    assert hashlib.sha256(data).hexdigest() == 'd626b92d8e5faaa6bf348f8530d8516d746d3cf496d61ae0900b112104b99f94'
