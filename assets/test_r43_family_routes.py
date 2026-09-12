"""Opt-in selector and realizer share authority and reject mixed proof inputs."""
from dataclasses import replace
from unittest import mock

import pytest

from assets.test_r43_family_capabilities import fixture_case
from pipeline import syntax_family_selector as selector
from pipeline.family_capabilities import prove_all_families
from pipeline.prompt_realizer import realize_content_plan


def test_common_selector_has_no_unconditional_baseline_or_legacy_family_ceiling():
    inputs, plan, evidence = fixture_case()
    with mock.patch.object(selector, 'direct_binding_families', side_effect=AssertionError('legacy ceiling')):
        selected, debug = selector.eligible_syntax_families(
            plan, None, None, realization_evidence=evidence, builder_inputs=inputs, return_debug=True)
    expected = prove_all_families(plan, evidence, builder_inputs=inputs)
    assert selected == [proof.family for proof in expected if proof.eligible]
    assert len(selected) == 6 and len(debug['family_proofs']) == 6
    invalid = replace(evidence, schema_version='unrecognized')
    assert selector.eligible_syntax_families(
        plan, None, None, realization_evidence=invalid, builder_inputs=inputs) == []
    text, rejected = realize_content_plan(plan, realization_evidence=invalid, builder_inputs=inputs, return_debug=True)
    assert rejected['realizer_version'] == 'v1' and rejected['eligible_syntax_families'] == []
    assert text == '{subject_clause}, {action_clause}, {scene_clause}.'


@pytest.mark.parametrize('name', ['action_frame', 'action_surface', 'direct_provenance', 'structural_evidence'])
def test_common_route_does_not_silently_ignore_conflicting_legacy_authorization(name):
    inputs, plan, evidence = fixture_case()
    mixed = {name: {}}
    with pytest.raises(ValueError, match='mix'):
        realize_content_plan(plan, realization_evidence=evidence, builder_inputs=inputs, **mixed)
    frame, surface = mixed.pop('action_frame', None), mixed.pop('action_surface', None)
    with pytest.raises(ValueError, match='mix'):
        selector.eligible_syntax_families(plan, frame, surface,
            realization_evidence=evidence, builder_inputs=inputs, **mixed)
