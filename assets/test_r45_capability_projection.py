"""Typed, text-free capability projection contracts for R45 diagnostics."""
import copy
from dataclasses import replace
import unittest

from assets.test_r43_family_capabilities import fixture_case
from assets.test_r43_real_graph_placement import real_snapshot
from tools.realizer_capability_projection import (
    build_capability_projection, capability_sha256, project_evidence_capabilities,
)


def by_domain(items, domain):
    return [item for item in items if item['capability']['domain'] == domain]


class TestTypedCapabilityProjection(unittest.TestCase):
    def test_action_identity_ignores_source_text_and_selected_text_hash(self):
        _, _, evidence = fixture_case()
        before = by_domain(project_evidence_capabilities(evidence), 'action')
        components = list(evidence.components)
        index = next(i for i, component in enumerate(components) if component.domain == 'action')
        component = components[index]
        parts = tuple(
            replace(part, text='different diagnostic text',
                    source=replace(part.source, selected_text_sha256='different-hash'))
            for part in component.trace.parts
        )
        atoms = tuple(replace(atom, source_text='different diagnostic text') for atom in component.atoms)
        components[index] = replace(component, trace=replace(component.trace, parts=parts), atoms=atoms)
        mutated = replace(evidence, components=tuple(components))
        after = by_domain(project_evidence_capabilities(mutated), 'action')
        self.assertEqual(before, after)

    def test_action_source_field_change_changes_identity(self):
        _, _, evidence = fixture_case()
        before = by_domain(project_evidence_capabilities(evidence), 'action')
        components = list(evidence.components)
        index = next(i for i, component in enumerate(components) if component.domain == 'action')
        component = components[index]
        parts = list(component.trace.parts)
        parts[0] = replace(parts[0], source=replace(parts[0].source, field='posture'))
        components[index] = replace(component, trace=replace(component.trace, parts=tuple(parts)))
        after = by_domain(project_evidence_capabilities(replace(evidence, components=tuple(components))), 'action')
        self.assertNotEqual(before[0]['capability_sha256'], after[0]['capability_sha256'])

    def test_clothing_atom_uses_all_referenced_source_parts(self):
        _, _, evidence = fixture_case()
        items = by_domain(project_evidence_capabilities(evidence), 'clothing')
        self.assertEqual(len(items), 1)
        capability = items[0]['capability']
        self.assertEqual(capability['capability_kind'], 'clause_atom')
        self.assertEqual(capability['source_field_classes'], ['palette.colors', 'choices.dresses'])
        self.assertEqual(capability['form_class'], 'noun_phrase')
        self.assertEqual(capability['owner_class'], 'protagonist')

    def test_unrelated_scene_changes_do_not_change_action_capabilities(self):
        _, _, evidence = fixture_case()
        before = by_domain(project_evidence_capabilities(evidence), 'action')
        components = list(evidence.components)
        index = next(i for i, component in enumerate(components) if component.domain == 'scene')
        component = components[index]
        parts = tuple(replace(part, source=replace(part.source, field='details'))
                      for part in component.trace.parts)
        components[index] = replace(
            component,
            trace=replace(component.trace, constructor_id='different_scene_constructor/v1', parts=parts),
        )
        after = by_domain(
            project_evidence_capabilities(replace(evidence, components=tuple(components))), 'action')
        self.assertEqual(before, after)

    def test_invalid_source_part_reference_fails_closed(self):
        _, _, evidence = fixture_case()
        components = list(evidence.components)
        index = next(i for i, component in enumerate(components) if component.domain == 'action')
        component = components[index]
        atoms = list(component.atoms)
        atoms[0] = replace(atoms[0], source_part_ids=('missing:part',))
        components[index] = replace(component, atoms=tuple(atoms))
        with self.assertRaisesRegex(
                ValueError, '^capability atom references an unknown producer part$'):
            project_evidence_capabilities(replace(evidence, components=tuple(components)))

    def test_exact_catalog_key_and_evidence_binding_are_not_identity_fields(self):
        _, _, evidence = fixture_case()
        before = by_domain(project_evidence_capabilities(evidence), 'clothing')
        components = list(evidence.components)
        index = next(i for i, component in enumerate(components) if component.domain == 'clothing')
        component = components[index]
        parts = tuple(replace(part, source=replace(part.source, catalog_key='different:selected:key'))
                      for part in component.trace.parts)
        components[index] = replace(
            component,
            trace=replace(component.trace, input_binding_sha256='different-binding', parts=parts),
        )
        mutated = replace(
            evidence, input_binding_sha256='different-binding', components=tuple(components))
        after = by_domain(project_evidence_capabilities(mutated), 'clothing')
        self.assertEqual(before, after)

    def test_capability_hash_is_canonical_for_mapping_order(self):
        identity = {'domain': 'action', 'form_class': 'gerund'}
        self.assertEqual(capability_sha256(identity), capability_sha256(dict(reversed(tuple(identity.items())))))

    def test_snapshot_wrapper_rebuilds_current_available_evidence(self):
        snapshot = real_snapshot()
        projection = build_capability_projection(snapshot, {'proof_basis': 'common_reconstructed'})
        self.assertEqual(projection['schema_version'], 'realizer-capability-projection/v1')
        self.assertEqual(projection['status'], 'AVAILABLE')
        self.assertTrue(projection['capabilities'])

        unavailable = build_capability_projection(snapshot, {'proof_basis': 'invalid_common_inputs'})
        self.assertEqual(unavailable, {
            'schema_version': 'realizer-capability-projection/v1',
            'status': 'NOT_AVAILABLE',
            'capabilities': [],
        })

    def test_snapshot_wrapper_fails_on_inconsistent_common_proof_basis(self):
        snapshot = copy.deepcopy(real_snapshot())
        del snapshot['bridge']['common_inputs']
        with self.assertRaisesRegex(
                ValueError, '^common reconstructed projection is missing current inputs$'):
            build_capability_projection(snapshot, {'proof_basis': 'common_reconstructed'})


if __name__ == '__main__':
    unittest.main()
