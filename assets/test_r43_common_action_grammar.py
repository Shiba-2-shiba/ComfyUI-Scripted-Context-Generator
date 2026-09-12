"""Common-only productive Action rules preserve bytes and fail closed."""
import copy
from dataclasses import replace
import unittest
from unittest.mock import patch

from core.schema import ActionFrame, PromptContext
from object_focus_service import load_object_relation_profiles
from pipeline.action_renderer import render_action_slots
from pipeline.v2_leaf_grammar import (
    derive_action_grammar, materialize_action_parts, materialize_proved_action_parts,
)
from pipeline.v2_structural_evidence import build_structural_evidence
from pipeline.v2_common_action_grammar import (
    derive_common_action_grammar, materialize_common_action_parts,
)


def fixture(*, posture='lying down', activity='reading a book', **extra):
    slots = dict(primary_action=posture + ' ' + activity, posture=posture,
                 hand_action=activity, **extra)
    text = render_action_slots(slots, activity_first=True)
    frame = ActionFrame.from_slots(slots, legacy_text=text,
                                   main_verb=posture.split()[0], primary_object='book')
    structural = build_structural_evidence(frame, text)
    profile = load_object_relation_profiles()['relations']['book:reading']
    relation = dict(mode='active', relation_key='book:reading',
                    required_roles=copy.deepcopy(profile['required_roles']),
                    applied_slots={'object_state': extra.get('object_state', '')})
    context = dict(action=text, history=[dict(node='ContextSceneVariator',
                  decision=dict(semantic_epig=dict(object_relation=relation)))])
    return structural, frame, context


class TestCommonActionGrammar(unittest.TestCase):
    def test_productive_stance_activity_and_semantic_head(self):
        for posture in ('lying down', 'standing', 'standing quietly', 'leaning closer'):
            for activity in ('reading a book', 'reviewing the book', 'studying her book',
                             'reading a phone'):
                with self.subTest(posture=posture, activity=activity):
                    structural, frame, context = fixture(posture=posture, activity=activity)
                    facts = derive_common_action_grammar(structural, frame, context)
                    self.assertTrue(facts.frame_predicate_safe)
                    self.assertEqual(facts.main_verb, posture.split()[0])
                    self.assertEqual(materialize_common_action_parts(structural, frame), frame.legacy_text)
                    self.assertIsNone(materialize_action_parts(structural))

    def test_primary_malformed_and_unbound_fail_closed(self):
        for activity in ('reading', 'reading a book badly', 'reading her book and leaving',
                         'not reading a book', 'she is reading a book', 'reading a unicorn',
                         'reading an book', 'reading a book near the garage'):
            with self.subTest(activity=activity):
                structural, frame, context = fixture(activity=activity)
                self.assertIsNone(derive_common_action_grammar(structural, frame, context).frame_predicate_safe)
        for field, value in (('main_verb', 'reading'), ('posture', 'standing'),
                             ('hand_action', 'reading the book'), ('schema_version', 'bad')):
            structural, frame, context = fixture()
            setattr(frame, field, value)
            self.assertIsNone(derive_common_action_grammar(structural, frame, context).frame_predicate_safe)
        structural, frame, context = fixture()
        frame.legacy_slots['posture'] = 'standing'
        self.assertIsNone(derive_common_action_grammar(structural, frame, context).frame_predicate_safe)

    def test_rechecking_reuses_known_checking_valency(self):
        for obj in ('the detail', 'a small detail', 'the bolt', 'the machine'):
            structural, frame, _ = fixture(purpose_clause='rechecking ' + obj)
            self.assertTrue(derive_common_action_grammar(structural, frame).parts[-1].known)
        for value in ('rechecking the detail badly', 'rechecking a phone', 'not rechecking the detail',
                      'she is rechecking the detail', 'rechecking his detail'):
            structural, frame, _ = fixture(purpose_clause=value)
            self.assertFalse(derive_common_action_grammar(structural, frame).parts[-1].known)

    def test_eyes_relative_is_owned_absolute_preserving_words(self):
        for obj in ('the detail', 'a quiet thing', 'the small pause'):
            text = 'eyes following ' + obj + ' she is working through'
            structural, frame, _ = fixture(gaze_target=text)
            facts = derive_common_action_grammar(structural, frame)
            leaf = facts.parts[-1]
            self.assertEqual((leaf.owner_kind, leaf.same_subject, leaf.attachment_kind),
                             ('protagonist_body_part', False, 'with_absolute'))
            self.assertFalse(facts.independent_action_subject)
            self.assertEqual(materialize_common_action_parts(structural, frame),
                             frame.legacy_slots['primary_action'] + ', with ' + text)
        for text in ('eyes following the detail he is working through',
                     'his eyes following the detail she is working through',
                     'eyes following the book she is working through',
                     'eyes following the detail she is working through quietly',
                     'eyes not following the detail she is working through'):
            structural, frame, _ = fixture(gaze_target=text)
            self.assertFalse(derive_common_action_grammar(structural, frame).parts[-1].known)
        for slot in ('object_state', 'purpose_clause'):
            structural, frame, _ = fixture(**{slot: 'eyes following the detail she is working through'})
            self.assertFalse(derive_common_action_grammar(structural, frame).parts[-1].known)

    def test_pages_require_exact_active_received_relation(self):
        structural, frame, context = fixture(object_state='open pages visible')
        before = copy.deepcopy((frame.to_dict(), context))
        facts = derive_common_action_grammar(structural, frame, context)
        leaf = facts.parts[-1]
        self.assertEqual((leaf.owner_kind, leaf.surface_kind, leaf.same_subject,
                          leaf.main_verb, leaf.attachment_kind),
                         ('primary_object_part', 'object_part_state', False, '', 'with_absolute'))
        self.assertEqual(materialize_common_action_parts(structural, frame, context),
                         frame.legacy_slots['primary_action'] + ', with open pages visible')
        self.assertEqual(before, (frame.to_dict(), context))
        self.assertEqual(facts, derive_common_action_grammar(structural, frame.to_dict(),
                                                          PromptContext.from_dict(context)))
        self.assertIsNone(materialize_common_action_parts(structural, frame))
        for key, value in (('mode', 'passive'), ('relation_key', 'phone:checking'),
                           ('required_roles', {}), ('applied_slots', {})):
            changed = copy.deepcopy(context)
            changed['history'][0]['decision']['semantic_epig']['object_relation'][key] = value
            self.assertFalse(derive_common_action_grammar(structural, frame, changed).parts[-1].known)
        for obj in ('phone', '', 'book:pages'):
            altered = copy.deepcopy(frame)
            altered.primary_object = obj
            self.assertFalse(derive_common_action_grammar(structural, altered, context).parts[-1].known)
        changed = copy.deepcopy(context)
        changed['action'] += ' altered'
        self.assertFalse(derive_common_action_grammar(structural, frame, changed).parts[-1].known)
        changed = copy.deepcopy(context)
        changed['history'].append(dict(node='ContextSceneVariator', decision={}))
        self.assertFalse(derive_common_action_grammar(structural, frame, changed).parts[-1].known)
        for field, value in (('action_frame', {}), ('new_action', 'reading a different book'),
                             ('slots', {})):
            changed = copy.deepcopy(context)
            changed['history'][0]['decision'][field] = value
            self.assertFalse(derive_common_action_grammar(structural, frame, changed).parts[-1].known)
        for field, value in (('relation_key', []), ('detected_objects', ['phone']),
                             ('detected_objects', ['book', 'phone']),
                             ('applied_slots', {'object_state': 'open pages visible',
                                                'gaze_target': 'eyes lowered toward the pages'})):
            changed = copy.deepcopy(context)
            changed['history'][0]['decision']['semantic_epig']['object_relation'][field] = value
            self.assertFalse(derive_common_action_grammar(structural, frame, changed).parts[-1].known)

    def test_object_profile_membership_does_not_prove_grammar(self):
        for state, allowed in (('closed pages visible', True), ('open pages visible trailing', False),
                               ('her eyes visible', False), ('not open pages visible', False),
                               ('open book visible', False)):
            profiles = copy.deepcopy(load_object_relation_profiles())
            profiles['relations']['book:reading']['required_roles']['object_state'] = [state]
            with patch('pipeline.v2_common_action_grammar.load_object_relation_profiles', return_value=profiles):
                structural, frame, context = fixture(object_state=state)
                context['history'][0]['decision']['semantic_epig']['object_relation']['required_roles'] = copy.deepcopy(
                    profiles['relations']['book:reading']['required_roles'])
                self.assertEqual(derive_common_action_grammar(structural, frame, context).parts[-1].known, allowed)
        structural, frame, context = fixture(activity='reading a phone', object_state='open pages visible')
        self.assertFalse(derive_common_action_grammar(structural, frame, context).parts[-1].known)
        for role in ('gaze_target', 'purpose_clause'):
            structural, frame, context = fixture(**{role: 'open pages visible'})
            self.assertFalse(derive_common_action_grammar(structural, frame, context).parts[-1].known)

    def test_hidden_reading_and_primary_body_roles_cannot_authorize_pages(self):
        structural, frame, context = fixture(object_state='open pages visible')
        frame.legacy_slots['primary_action'] = 'holding the clipboard'
        frame.legacy_text = render_action_slots(frame.legacy_slots, activity_first=True)
        context['action'] = frame.legacy_text
        structural = build_structural_evidence(frame, frame.legacy_text)
        facts = derive_common_action_grammar(structural, frame, context)
        page_index = next(i for i, part in enumerate(structural.emitted_parts) if part.slot_key == 'object_state')
        self.assertFalse(facts.parts[page_index].known)
        for text in ('eyes following the detail she is working through', 'open pages visible'):
            for role in ('primary_action', 'gaze_target', 'object_state'):
                slots = {role: text}
                raw = render_action_slots(slots, activity_first=True)
                current = ActionFrame.from_slots(slots, legacy_text=raw)
                proof = build_structural_evidence(current, raw)
                self.assertIsNone(derive_common_action_grammar(proof, current).frame_predicate_safe)

    def test_existing_rules_and_legacy_materialization_unchanged(self):
        slots = dict(primary_action='holding the clipboard', gaze_target='eyes following the detail')
        text = render_action_slots(slots, activity_first=True)
        frame = ActionFrame.from_slots(slots, legacy_text=text)
        structural = build_structural_evidence(frame, text)
        self.assertEqual(derive_common_action_grammar(structural, frame), derive_action_grammar(structural))
        self.assertEqual(materialize_common_action_parts(structural, frame), materialize_action_parts(structural))

    def test_materialization_rejects_truncated_or_surplus_leaf_proofs(self):
        structural, frame, context = fixture(object_state='open pages visible')
        facts = derive_common_action_grammar(structural, frame, context)
        self.assertIsNotNone(materialize_proved_action_parts(structural, facts))
        for parts in (facts.parts[:-1], (), facts.parts + facts.parts[-1:]):
            with self.subTest(proof_count=len(parts)):
                self.assertIsNone(materialize_proved_action_parts(structural, replace(facts, parts=parts)))


if __name__ == '__main__':
    unittest.main()
