"""R2 proves placement of the whole scene; it does not broaden lexical support."""
from collections import Counter
from dataclasses import replace
import copy
import hashlib
import re
import unittest

from assets.test_n27_direct_provenance import CASES, render
from pipeline.prompt_realizer import ContentPlan, realize_content_plan
from pipeline.syntax_family_selector import eligible_syntax_families
from pipeline.v2_direct_provenance import materialize_direct


SUPPORTED = {'subject_action__scene_tail', 'scene_lead_subject_action', 'subject_scene_action'}


def concrete(case, family):
    proof = {'slots': case['slots']['semantic_slots'], 'surface': case['surface'],
             'replacements': case['replacements']}
    slots = materialize_direct(proof, case['frame'], syntax_family=family)
    plan = replace(ContentPlan(**case['slots']), semantic_slots=slots, syntax_family=family)
    return plan, {**case['surface'], 'rendered_clause': slots['adjunct']}, proof


class TestSceneConstituents(unittest.TestCase):
    def test_moved_modifiers_have_explicit_location_owner(self):
        relative_predicates = {
            9: ('has old mechanical clocks and ornate gold-framed mirrors, '
                'features vintage curved glass display cabinets during the evening, '
                'and has a quiet timeless atmosphere'),
            40: ('is adorned with canvas backpacks resting on benches '
                 'and features a wide stone path between lawns'),
            51: ('has a polished finish during a deep moonless night, '
                 'has layered background depth, features a large equatorial telescope '
                 'and a curved rotating dome track, and has a weather monitor'),
        }
        for case in CASES:
            for family in ('scene_lead_subject_action', 'subject_scene_action'):
                plan, _, _ = concrete(case, family)
                scene = plan.semantic_slots['scene']
                self.assertIn(', which ' + relative_predicates[case['run_seed']] + ', with ', scene)
                self.assertNotIn(', featuring ', scene)
                self.assertNotIn(', adorned with ', scene)

    def test_real_scenes_remain_whole_and_delimited_in_new_orders(self):
        for case in CASES:
            for family in ('scene_lead_subject_action', 'subject_scene_action'):
                with self.subTest(seed=case['run_seed'], family=family):
                    plan, surface, proof = concrete(case, family)
                    kwargs = dict(action_frame=case['frame'], action_surface=surface,
                                  direct_provenance=proof, return_debug=True)
                    text, debug = realize_content_plan(plan, **kwargs)
                    self.assertEqual(debug['realizer_version'], 'v2')
                    self.assertEqual(debug['syntax_family'], family)
                    self.assertEqual(text.count('.'), 1)
                    self.assertEqual((text, debug), realize_content_plan(plan, **kwargs))
                    subject, action, scene = (plan.semantic_slots[k].lower()
                                              for k in ('subject', 'adjunct', 'scene'))
                    lowered = text.lower()
                    if family == 'scene_lead_subject_action':
                        self.assertEqual(lowered, scene + ', ' + subject + ' is ' + action + '.')
                        self.assertEqual(debug['clause_order'], ['scene', 'subject', 'action'])
                    else:
                        self.assertEqual(lowered, subject + ', ' + scene + ', is ' + action + '.')
                        self.assertEqual(debug['clause_order'], ['subject', 'scene', 'action'])
                    self.assertEqual(lowered.count(scene), 1)
                    # Only connector removal and the approved features inflection
                    # are normalized; every noun/adjective/adverb still counts.
                    tokens = lambda value: Counter('featuring' if word == 'features' else word for word in
                        re.findall(r"[a-z]+(?:-[a-z]+)*", value.lower()) if word != 'with')
                    values = dict(case['replacements'])
                    self.assertIn(values['{action}'], text)
                    self.assertIn(values['{meta_mood}'], text)
                    for garnish in values['{garnish}'].split(', '):
                        self.assertIn(garnish, text)
                    original = tokens(' '.join(values[key] for key in
                                               ('{subject_clause}', '{action_clause}', '{scene_clause}')))
                    self.assertFalse(original - tokens(text))
                    self.assertLessEqual(set(tokens(text) - original), {'a', 'an', 'the', 'is', 'which', 'has', 'and'})

    def test_scope_proof_filters_insert_without_falsifying_shared_scene_fact(self):
        plan, surface, proof = concrete(CASES[0], 'subject_scene_action')
        eligible, debug = eligible_syntax_families(plan, CASES[0]['frame'], surface,
                                                  direct_provenance=proof, return_debug=True)
        self.assertEqual(set(eligible), {'subject_action_scene', *SUPPORTED})
        self.assertEqual(set(debug['direct_supported_families']), SUPPORTED)
        self.assertTrue(debug['safety_facts']['scene_lead_safe'])
        self.assertTrue(debug['safety_facts']['scene_adjunct_safe'])
        self.assertIsNone(debug['safety_facts']['same_subject_attachment_safe'])
        self.assertIn('direct_scene_scope_not_proven',
                      debug['rejected_syntax_families']['subject_action_scene_insert'])
        for family in ('subject_action_scene', 'subject_action_scene_insert', 'action_lead_subject_scene'):
            _, rendered = realize_content_plan(replace(plan, syntax_family=family),
                                               action_frame=CASES[0]['frame'], action_surface=surface,
                                               direct_provenance=proof, return_debug=True)
            self.assertEqual(rendered['realizer_version'], 'v1')

    def test_named_seed_selection_replays_and_exercises_all_proved_placements(self):
        observed = set()
        case = copy.deepcopy(CASES[0])
        for seed in range(64):
            case['builder_seed'] = seed
            actual = render(case)
            self.assertEqual(actual, render(case))
            self.assertTrue(actual[2]['candidate_v2_applied'])
            observed.add(actual[2]['syntax_family'])
        self.assertEqual(observed, SUPPORTED)

    def test_mutated_scene_parts_and_fabricated_parse_flags_never_authorize_placement(self):
        case = CASES[0]
        for family in ('scene_lead_subject_action', 'subject_scene_action'):
            plan, surface, proof = concrete(case, family)
            for old, new in (('mysterious curio store filled with history', 'unknown studio'),
                             ('old mechanical clocks', 'a stranger waiting'),
                             ('the scene narrowing', 'her friend waving')):
                bad = copy.deepcopy(proof)
                bad['replacements'] = [(key, value.replace(old, new)) for key, value in bad['replacements']]
                bad.update(scene_lead_safe=True, scene_adjunct_safe=True, validated_scene_parts=True)
                self.assertIsNone(materialize_direct(bad, case['frame']))
                _, debug = realize_content_plan(plan, action_frame=case['frame'], action_surface=surface,
                                                direct_provenance=bad, return_debug=True)
                self.assertEqual(debug['realizer_version'], 'v1')

    def test_mood_internal_comma_stays_inside_whole_scene(self):
        case = copy.deepcopy(CASES[0])
        values = dict(case['replacements'])
        values['{meta_mood}'] = ('the moment kept deliberate rather than urgent, '
                                 'with everything else held at the edge')
        values['{scene_clause}'] = 'in ' + values['{loc}'] + ', ' + values['{meta_mood}']
        values['{scene_anchor_clause}'] = values['{scene_clause}'][3:]
        case['replacements'] = list(values.items())
        for family in ('scene_lead_subject_action', 'subject_scene_action'):
            plan, surface, proof = concrete(case, family)
            text, debug = realize_content_plan(plan, action_frame=case['frame'], action_surface=surface,
                                               direct_provenance=proof, return_debug=True)
            self.assertEqual(debug['realizer_version'], 'v2')
            self.assertIn('with ' + values['{meta_mood}'] + ', ', text)
            self.assertIn(plan.semantic_slots['scene'], text.lower())
            self.assertEqual(text.count('.'), 1)

    def test_unmatched_roles_leave_no_selectable_constructor_and_preserve_v1(self):
        case = copy.deepcopy(CASES[0])
        case['slots']['discourse_roles'] = ['unsupported-role']
        text, _, debug = render(case)
        self.assertFalse(debug['candidate_v2_applied'])
        self.assertEqual(text, realize_content_plan(ContentPlan(**case['slots'])))

    def test_r1_two_sentence_outputs_remain_byte_identical(self):
        before_hashes = {
            9: 'f6a7c9cf3e1fea99bb304bb94b6ba896d67b2225b8f437b8300b5767bf118317',
            40: 'f6e99ef676ab3e39cc4eac8e09f7e0826718a0a40b9cec8a533246b59efe3d7b',
            51: '0230762bf7a5215725bcc7f05d51f9efdbd180f36a61dba2b6013df50e27078b',
        }
        for case in CASES:
            plan, surface, proof = concrete(case, 'subject_action__scene_tail')
            text = realize_content_plan(plan, action_frame=case['frame'], action_surface=surface,
                                        direct_provenance=proof)
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), before_hashes[case['run_seed']])

    def test_time_first_scene_retains_r1_but_cannot_move(self):
        case = copy.deepcopy(CASES[0])
        values = dict(case['replacements'])
        location = values['{loc}'].split(', ')
        time = next(part for part in location if part.startswith('during '))
        location.remove(time)
        location.insert(1, time)
        values['{loc}'] = ', '.join(location)
        values['{scene_clause}'] = 'in ' + values['{loc}'] + ', ' + values['{meta_mood}']
        values['{scene_anchor_clause}'] = values['{scene_clause}'][3:]
        case['replacements'] = list(values.items())
        plan, surface, proof = concrete(case, 'subject_action__scene_tail')
        expected, metadata = realize_content_plan(plan, action_frame=case['frame'], action_surface=surface,
                                                  direct_provenance=proof, return_debug=True)
        self.assertEqual(metadata['realizer_version'], 'v2')
        self.assertIn('history, during the evening, with old mechanical clocks', expected)
        for family in ('scene_lead_subject_action', 'subject_scene_action'):
            self.assertIsNone(materialize_direct(proof, case['frame'], syntax_family=family))
        for seed in range(8):
            case['builder_seed'] = seed
            text, actual, debug = render(case)
            self.assertEqual(text, expected)
            self.assertEqual(actual.syntax_family, 'subject_action__scene_tail')
            self.assertEqual(debug['candidate_eligibility']['direct_supported_families'],
                             ['subject_action__scene_tail'])
            self.assertIsNone(debug['candidate_eligibility']['safety_facts']['scene_adjunct_safe'])

    def test_family_relabel_without_actual_scene_conversion_is_rejected(self):
        case = CASES[0]
        for old, new in (('subject_action__scene_tail', 'scene_lead_subject_action'),
                         ('subject_scene_action', 'subject_action__scene_tail')):
            plan, surface, proof = concrete(case, old)
            _, debug = realize_content_plan(replace(plan, syntax_family=new),
                                            action_frame=case['frame'], action_surface=surface,
                                            direct_provenance=proof, return_debug=True)
            self.assertEqual(debug['realizer_version'], 'v1')

    def test_bridge_content_plan_records_exact_family_specific_scene(self):
        for case in CASES:
            text, actual, debug = render(case)
            expected, _, _ = concrete(case, actual.syntax_family)
            self.assertEqual(dict(actual.semantic_slots), dict(expected.semantic_slots))
            self.assertIn(actual.semantic_slots['scene'], text.lower())


if __name__ == '__main__':
    unittest.main()
