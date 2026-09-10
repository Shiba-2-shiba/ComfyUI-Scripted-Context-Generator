import copy
from dataclasses import replace
import json
from pathlib import Path
import unittest

from pipeline.prompt_realizer import ContentPlan, realize_content_plan
from pipeline.v2_candidate_bridge import render_candidate
from pipeline.v2_direct_provenance import materialize_direct
from pipeline.v2_structural_evidence import build_structural_evidence
from pipeline.syntax_family_selector import eligible_syntax_families

CASES = json.loads((Path(__file__).parent / 'fixtures/n27_r41_real_cases.json').read_text(encoding='utf-8'))


def render(case):
    plan = ContentPlan(**case['slots'])
    text, debug = realize_content_plan(plan, return_debug=True)
    return render_candidate(plan, text, debug, case['frame'], case['surface'], case['replacements'],
                            case['builder_seed'], producer_context=case.get('producer_context'))


class TestCompleteRealCases(unittest.TestCase):
    def test_new_real_cases_preserve_action_and_unknown_overlap(self):
        for case in CASES:
            before = copy.deepcopy(case)
            text, plan, debug = render(case)
            self.assertTrue(debug['candidate_v2_applied'], case['run_seed'])
            self.assertEqual(debug['syntax_family'], 'subject_action__scene_tail')
            self.assertIn(dict(case['replacements'])['{action}'], text)
            facts = debug['candidate_eligibility']['safety_facts']
            self.assertIsNone(facts['scene_action_overlap'])
            self.assertIsNone(facts['scene_action_nonduplicative'])
            self.assertEqual(debug['candidate_eligibility']['direct_supported_families'], ['subject_action__scene_tail'])
            self.assertEqual(set(plan.to_dict()), set(case['slots']))
            self.assertEqual(case, before)
            self.assertEqual((text, plan, debug), render(case))

    def test_stale_frame_or_unknown_required_grammar_falls_back_exactly(self):
        for original in CASES:
            case = copy.deepcopy(original)
            case['frame']['legacy_slots']['purpose_clause'] = 'someone waves'
            text, _, debug = render(case)
            self.assertFalse(debug['candidate_v2_applied'])
            self.assertEqual(text, realize_content_plan(ContentPlan(**case['slots'])))

    def test_unknown_overlap_never_grants_other_placements(self):
        for case in CASES:
            proof = {'slots': case['slots']['semantic_slots'], 'surface': case['surface'],
                     'replacements': case['replacements'], **case.get('producer_context', {})}
            trace = build_structural_evidence(case['frame'], dict(case['replacements'])['{action}'])
            concrete = materialize_direct(proof, case['frame'], structural_evidence=trace)
            self.assertIsNotNone(concrete)
            plan = replace(ContentPlan(**case['slots']), semantic_slots=concrete,
                           syntax_family='subject_action__scene_tail')
            surface = {**case['surface'], 'rendered_clause': concrete['adjunct']}
            for family in ('action_lead_subject_scene', 'subject_action_scene_insert', 'scene_lead_subject_action'):
                _, debug = realize_content_plan(replace(plan, syntax_family=family), action_frame=case['frame'],
                    action_surface=surface, direct_provenance=proof, structural_evidence=trace, return_debug=True)
                self.assertEqual(debug['realizer_version'], 'v1')


if __name__ == '__main__':
    unittest.main()
