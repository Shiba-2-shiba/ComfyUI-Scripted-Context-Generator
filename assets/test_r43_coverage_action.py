"""AS01 Action extensions require complete source-bound constituent proofs."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import unittest

from core.schema import ActionFrame
from pipeline.action_renderer import render_action_slots
from pipeline.v2_common_action_grammar import (
    derive_common_action_grammar, materialize_common_action_parts,
)
from pipeline.v2_leaf_grammar import (
    aggregate_action_parts, derive_action_grammar, materialize_action_parts,
    materialize_proved_action_parts,
)
from pipeline.v2_structural_evidence import build_structural_evidence


def fixture(primary='holding the clipboard', **extra):
    slots = dict(primary_action=primary, **extra)
    raw = render_action_slots(slots, activity_first=True)
    frame = ActionFrame.from_slots(slots, legacy_text=raw, main_verb=primary.split()[0])
    structural = build_structural_evidence(frame, raw)
    return structural, frame


class TestCoverageAction(unittest.TestCase):
    def test_received_recording_booth_action_and_source_preservation(self):
        pair = json.loads((Path(__file__).parent / 'fixtures/r43_coverage_as01_pair.json').read_text(encoding='utf-8'))
        context = pair['builder_context']
        frame = ActionFrame.from_dict(context['extras']['action_frame'])
        structural = build_structural_evidence(frame, context['action'])
        original = copy.deepcopy((context, frame.to_dict(), structural))
        facts = derive_common_action_grammar(structural, frame, context)
        self.assertTrue(facts.frame_predicate_safe)
        self.assertFalse(facts.independent_action_subject)
        self.assertFalse(facts.same_subject_attachment_safe)
        self.assertEqual(materialize_common_action_parts(structural, frame, context),
                         context['action'].replace('clicking pen', 'clicking a pen'))
        self.assertIsNone(materialize_action_parts(structural))
        self.assertEqual(original, (context, frame.to_dict(), structural))

    def test_turning_and_leaning_productive_manner_combinations(self):
        for manner in ('composure', 'quiet purpose', 'steady purpose'):
            for pose in ('leaning in', 'leaning closer'):
                with self.subTest(manner=manner, pose=pose):
                    structural, frame = fixture('turning toward the center of attention with ' + manner,
                                                posture=pose + ' with ' + manner)
                    facts = derive_common_action_grammar(structural, frame)
                    self.assertTrue(facts.frame_predicate_safe)
                    self.assertTrue(facts.same_subject_attachment_safe)
                    self.assertEqual(facts.main_verb, 'turning')
                    self.assertEqual(materialize_common_action_parts(structural, frame), frame.legacy_text)
                    self.assertIsNone(materialize_action_parts(structural))

    def test_manner_grammar_rejects_extra_words_and_wrong_roles(self):
        for value in ('turning toward the garage with composure',
                      'turning toward the center of attention with composure badly',
                      'turning toward the center of attention with his composure',
                      'turning toward the center of attention without composure',
                      'she is turning toward the center of attention with composure',
                      'not turning toward the center of attention with composure'):
            with self.subTest(value=value):
                structural, frame = fixture(value)
                self.assertIsNone(derive_common_action_grammar(structural, frame).frame_predicate_safe)
        for value in ('leaning in with quiet purpose badly', 'leaning in with his purpose',
                      'leaning into the garage with quiet purpose'):
            structural, frame = fixture(posture=value)
            self.assertFalse(derive_common_action_grammar(structural, frame).parts[-1].known)
        for slot, text in (('gaze_target', 'leaning in with quiet purpose'),
                           ('social_clause', 'turning toward the center of attention with composure')):
            structural, frame = fixture(**{slot: text})
            self.assertFalse(derive_common_action_grammar(structural, frame).parts[-1].known)

    def test_count_noun_article_is_explicit_and_common_only(self):
        structural, frame = fixture(purpose_clause='clicking pen')
        facts = derive_common_action_grammar(structural, frame)
        leaf = facts.parts[-1]
        self.assertEqual(leaf.surface_kind, 'count_noun_gerund')
        self.assertEqual(leaf.main_verb, 'clicking')
        self.assertEqual(materialize_common_action_parts(structural, frame),
                         frame.legacy_text.replace('clicking pen', 'clicking a pen'))
        self.assertIsNone(materialize_action_parts(structural))
        self.assertIsNone(materialize_proved_action_parts(structural, facts))
        for value in ('clicking pen badly', 'clicking pens', 'clicking a button',
                      'clicking his pen', 'clicking pen and leaving'):
            structural, frame = fixture(purpose_clause=value)
            self.assertFalse(derive_common_action_grammar(structural, frame).parts[-1].known)
        structural, frame = fixture(gaze_target='clicking pen')
        self.assertFalse(derive_common_action_grammar(structural, frame).parts[-1].known)
        structural, frame = fixture('clicking pen')
        self.assertIsNone(materialize_common_action_parts(structural, frame))

    def test_dependent_event_keeps_its_subject_and_blocks_action_leading(self):
        for event in ('session', 'task'):
            structural, frame = fixture(time_or_weather='as the ' + event + ' wraps up')
            facts = derive_common_action_grammar(structural, frame)
            leaf = facts.parts[-1]
            self.assertEqual((leaf.surface_kind, leaf.attachment_kind, leaf.owner_kind,
                              leaf.same_subject, leaf.no_place_reference),
                             ('finite', 'dependent_temporal_event', 'scene_event', False, True))
            self.assertTrue(facts.frame_predicate_safe)
            self.assertFalse(facts.independent_action_subject)
            self.assertFalse(facts.same_subject_attachment_safe)
            self.assertEqual(materialize_common_action_parts(structural, frame), frame.legacy_text)
            self.assertIsNone(materialize_action_parts(structural))
            self.assertIsNone(materialize_proved_action_parts(structural, facts))
            self.assertTrue(aggregate_action_parts(facts.parts).independent_action_subject)

    def test_event_opt_in_does_not_exempt_different_owners_or_attachments(self):
        structural, frame = fixture(time_or_weather='as the task wraps up')
        facts = derive_common_action_grammar(structural, frame)
        for changes in (dict(owner_kind='protagonist'), dict(owner_kind='unknown'),
                        dict(attachment_kind='subordinate_temporal'),
                        dict(surface_kind='gerund'), dict(main_verb='wrapping')):
            leaf = replace(facts.parts[-1], **changes)
            altered = aggregate_action_parts((*facts.parts[:-1], leaf), allow_dependent_events=True)
            self.assertTrue(altered.independent_action_subject)
            self.assertIsNone(materialize_proved_action_parts(structural, altered, allow_common_parts=True))

    def test_event_marker_requires_nonprimary_time_role_and_complete_grammar(self):
        for role in ('primary_action', 'purpose_clause', 'posture', 'obstacle_clause', 'social_clause'):
            structural, frame = (fixture('as the session wraps up') if role == 'primary_action'
                                 else fixture(**{role: 'as the session wraps up'}))
            self.assertIsNone(materialize_common_action_parts(structural, frame))
        for value in ('as she wraps up', 'as the sessions wraps up', 'as the session wrap up',
                      'as the man wraps up', 'as the session wraps up badly',
                      'as the session wraps up and she leaves', 'because the task wraps up',
                      'the session wraps up', 'as a session wraps up'):
            with self.subTest(value=value):
                structural, frame = fixture(time_or_weather=value)
                self.assertIsNone(materialize_common_action_parts(structural, frame))

    def test_generic_external_events_remain_independent_in_every_role(self):
        for role in ('time_or_weather', 'obstacle_clause', 'purpose_clause'):
            for value in ('as the task ends', 'because the task begins', 'while the lights change'):
                with self.subTest(role=role, value=value):
                    structural, frame = fixture(**{role: value})
                    facts = derive_common_action_grammar(structural, frame)
                    self.assertEqual(facts, derive_action_grammar(structural))
                    self.assertTrue(facts.independent_action_subject)
                    self.assertIsNone(materialize_common_action_parts(structural, frame))

    def test_stale_source_or_role_cannot_reuse_proof(self):
        structural, frame = fixture(purpose_clause='clicking pen', time_or_weather='as the task wraps up')
        self.assertIsNotNone(materialize_common_action_parts(structural, frame))
        for changed in (dict(purpose_clause='clicking pens'), dict(time_or_weather='as the man wraps up')):
            current = copy.deepcopy(frame)
            current.legacy_slots.update(changed)
            self.assertIsNone(materialize_common_action_parts(structural, current))


if __name__ == '__main__':
    unittest.main()
