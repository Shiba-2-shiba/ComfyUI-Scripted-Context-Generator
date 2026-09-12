"""Unchanged real-graph six-family evidence, separate from recombination tests."""
import json
from dataclasses import replace
from pathlib import Path

import pytest

from core.context_codec import context_from_json
from pipeline.prompt_orchestrator import build_prompt_from_context
from pipeline.prompt_realizer import ContentPlan, realize_content_plan
from pipeline.realization_evidence import build_realization_evidence
from pipeline.family_capabilities import prove_family
from nodes_prompt_cleaner import PromptCleaner
from assets.test_r43_family_capabilities import FAMILIES
import prompt_renderer


def real_snapshot():
    receipt = json.loads((Path(__file__).parent / 'fixtures/r43_real_graph_cases.json').read_text(encoding='utf-8'))
    case = next(item for item in receipt['cases'] if item['run_seed'] == 51)
    assert case['classification'] == 'REAL_GRAPH'
    inputs = case['builder_inputs']
    snapshots = []
    updated, ordinary = build_prompt_from_context(
        context_from_json(inputs['context_json'], default_seed=inputs['seed']),
        inputs['template'], inputs['composition_mode'], inputs['seed'], audit_sink=snapshots.append)
    assert ordinary == case['raw'] and updated.to_dict() == case['builder_context']
    return snapshots[0]


@pytest.mark.parametrize('family', FAMILIES)
def test_each_family_reaches_unchanged_real_graph_and_preserves_emitted_parts(family):
    snapshot = real_snapshot()
    inputs = snapshot['common_evidence_inputs']
    evidence = build_realization_evidence(inputs)
    plan = replace(ContentPlan(**snapshot['bridge']['input_plan']), syntax_family=family)
    proof = prove_family(family, plan, evidence, builder_inputs=inputs)
    assert proof.eligible, proof.blocker_ids
    surface, debug = realize_content_plan(plan, realization_evidence=evidence,
        builder_inputs=inputs, family_proof=proof, return_debug=True)
    raw = prompt_renderer._finalize_prompt(surface, **snapshot['finalization'])
    cleaned = PromptCleaner().clean(text=raw)[0]
    assert debug['realizer_version'] == 'v2' and debug['syntax_family'] == family
    for component in evidence.components:
        if component.domain in {'template', 'clothing'}:
            continue
        parts = {part.part_id: part for part in component.trace.parts}
        for part_id in component.trace.emitted_part_ids:
            original = parts[part_id].text.lower()
            if component.domain == 'subject':
                field = parts[part_id].source.field
                if field == 'visual_traits.hair_color':
                    original += ' hair'
                elif field == 'visual_traits.eye_color':
                    original += ' eyes'
            assert raw.lower().count(original) == 1, (component.domain, original, raw)
            assert cleaned.lower().count(original) == 1, (component.domain, original, cleaned)
    if family == 'action_lead_subject_scene':
        assert raw.startswith('Securing the telescope cover, ')
        assert ', with brows knit in concentration, is in a circular telescope chamber' in raw
        assert all(slot == 'subject' for atom, slot in proof.source_atom_map if atom.startswith('garnish:'))
    if family != 'subject_action__scene_tail':
        assert 'which has a polished finish during a deep moonless night' in raw
        assert 'scene.reviewed_legacy_relative/v1' in proof.transform_rule_ids
    assert 'warm turtleneck sweater dress' in raw


def test_reviewed_scene_leading_temporal_still_does_not_grant_relocation():
    snapshot = real_snapshot()
    inputs = snapshot['common_evidence_inputs']
    segments = inputs['scene'].split(', ')
    time = next(part for part in segments if part.startswith('during '))
    parts = [segments[0], time, *(part for part in segments[1:] if part != time)]
    inputs['scene'] = inputs['context']['extras']['location_prompt'] = ', '.join(parts)
    evidence = build_realization_evidence(inputs)
    plan = ContentPlan(**snapshot['bridge']['input_plan'])
    # This altered-order negative is a recombination, not a real-graph positive.
    proof = prove_family('scene_lead_subject_action', plan, evidence, builder_inputs=inputs)
    assert not proof.eligible and 'scene.placement_constructor_unknown' in proof.blocker_ids
