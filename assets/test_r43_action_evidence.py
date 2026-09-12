"""The common Action adapter preserves legacy facts and exact source bytes."""
import copy
import json
from pathlib import Path
import unittest

from core.schema import ActionFrame
from pipeline.action_renderer import render_action_slots
from pipeline.realization_evidence import Truth, text_sha256, truth_from_optional
from pipeline.v2_leaf_grammar import derive_action_grammar
from pipeline.v2_structural_evidence import adapt_action_component, build_structural_evidence


def component_for(slots, *, activity_first=True):
    text = render_action_slots(slots, activity_first=activity_first)
    frame = ActionFrame.from_slots(slots, legacy_text=text)
    return adapt(frame, text)


def adapt(frame, text):
    return adapt_action_component(frame, text, input_binding_sha256='a' * 64,
                                  source_identity_sha256='b' * 64)


class TestR43ActionEvidence(unittest.TestCase):
    def test_real_body_ownership_and_semantic_head_are_preserved(self):
        cases = json.loads((Path(__file__).parent / 'fixtures/n27_r42_real_cases.json').read_text())
        for case in cases:
            frame = case['frame']
            before = copy.deepcopy(frame)
            component = adapt(frame, frame['legacy_text'])
            self.assertTrue(component.runtime_available)
            self.assertEqual(frame, before)
            legacy = derive_action_grammar(build_structural_evidence(frame, frame['legacy_text']))
            self.assertEqual(dict(component.facts), {
                name: truth_from_optional(getattr(legacy, name))
                for name in ('frame_predicate_safe', 'same_subject_attachment_safe',
                             'independent_action_subject', 'no_place_reference')
            })
            if case['run_seed'] == 88:
                eyes = next(atom for atom in component.atoms if atom.form == 'body_state')
                self.assertEqual(eyes.grammatical_subject_id, 'body:eyes')
                self.assertEqual(eyes.owner_id, 'protagonist')
                self.assertIs(eyes.same_subject, Truth.FALSE)
                self.assertEqual(eyes.attachment, 'with_absolute')
                self.assertEqual(eyes.place_refs, ())
                self.assertIsNone(eyes.antecedent_ids)
            if case['run_seed'] in {94, 338}:
                self.assertEqual(frame['main_verb'], 'tidying')
                self.assertEqual(component.atoms[0].grammatical_head, 'standing')

    def test_owned_body_and_external_event_do_not_share_actor_subject(self):
        for field, value, subject in (
                ('gaze_target', 'her eyes following the detail', 'body:eyes'),
                ('hand_action', 'her hands holding the clipboard', 'body:hands'),
                ('hand_action', 'her fingers holding the clipboard', 'body:fingers'),
                ('obstacle_clause', 'while the inspection ends', None)):
            slots = {'purpose_clause': 'standing', field: value}
            component = component_for(slots, activity_first=False)
            atom = component.atoms[1]
            self.assertIs(atom.grammar_known, Truth.TRUE)
            self.assertIs(atom.same_subject, Truth.FALSE)
            if subject:
                self.assertEqual(atom.grammatical_subject_id, subject)
                self.assertEqual(atom.owner_id, 'protagonist')
            else:
                self.assertEqual(atom.grammatical_subject_id, 'event:' + atom.source_part_ids[0])
                self.assertIsNone(atom.owner_id)

    def test_unknown_references_and_leaf_identity_are_not_positive_evidence(self):
        for primary, known, places in (
                ('sitting in the audience seats', Truth.TRUE, None),
                ('holding the clipboard', Truth.TRUE, ()),
                ('unrecognized action with it', Truth.UNKNOWN, None)):
            component = component_for({'primary_action': primary})
            atom = component.atoms[0]
            self.assertIs(atom.grammar_known, known)
            self.assertEqual(atom.place_refs, places)
            self.assertIsNone(atom.antecedent_ids)
            if known is Truth.UNKNOWN:
                self.assertIsNone(atom.grammatical_subject_id)
                self.assertIsNone(atom.owner_id)
                self.assertIs(atom.same_subject, Truth.UNKNOWN)
                self.assertTrue(all(fact is Truth.UNKNOWN for _, fact in component.facts))
            else:
                self.assertEqual(atom.grammatical_subject_id, 'protagonist')
                self.assertEqual(atom.owner_id, 'protagonist')

    def test_trace_uses_original_source_bytes_and_only_emitted_parts(self):
        slots = {'primary_action': '  holding the clipboard  ',
                 'posture': 'holding the clipboard', 'hand_action': 'ignored legacy hand action'}
        component = component_for(slots)
        trace = component.trace
        self.assertEqual(len(trace.parts), 1)
        part = trace.parts[0]
        self.assertEqual(part.source.field, 'primary_action')
        self.assertEqual(part.source.selected_text_sha256, text_sha256(slots['primary_action']))
        self.assertEqual(part.text, 'holding the clipboard')
        self.assertEqual(trace.emitted_part_ids, (part.part_id,))
        self.assertIsNone(trace.omitted_parts)
        self.assertIsNone(part.source.catalog_key)
        self.assertEqual(trace.input_binding_sha256, 'a' * 64)
        self.assertEqual(trace.source_identity_sha256, 'b' * 64)
        self.assertEqual(trace.raw_output_sha256, text_sha256(part.text))
        self.assertEqual(trace.emitted_output_sha256, text_sha256(part.text))
        self.assertEqual(component, component_for(slots))

    def test_constructor_distinguishes_known_modes_and_same_trace(self):
        same = component_for({'purpose_clause': 'holding the clipboard'})
        slots = {'primary_action': 'holding the clipboard', 'purpose_clause': 'standing'}
        first = component_for(slots)
        last = component_for(slots, activity_first=False)
        self.assertEqual(len({item.trace.constructor_id for item in (same, first, last)}), 3)
        ambiguous = component_for({'primary_action': 'standing', 'purpose_clause': 'standing'})
        self.assertFalse(ambiguous.runtime_available)

    def test_malformed_version_stale_and_nonexact_text_cannot_supply_trace(self):
        slots = {'primary_action': 'holding the clipboard'}
        text = render_action_slots(slots, activity_first=True)
        frame = ActionFrame.from_slots(slots, legacy_text=text).to_dict()
        invalid = [None, [], {}, {**frame, 'schema_version': 'action-frame/v2'},
                   ActionFrame(schema_version='action-frame/v2', legacy_text=text, legacy_slots=slots),
                   {**frame, 'legacy_slots': None}, {**frame, 'legacy_slots': []},
                   {**frame, 'legacy_slots': {'primary_action': 123}},
                   {**frame, 'legacy_text': ['holding the clipboard']}]
        for value in invalid:
            with self.subTest(frame=value):
                component = adapt(value, text)
                self.assertFalse(component.runtime_available)
                self.assertIsNone(component.trace)
                self.assertEqual(component.atoms, ())
        for changed in (None, [], text + ' now', text.upper(), '  ' + text, text.replace(' ', '  ')):
            self.assertIsNone(adapt(frame, changed).trace)
        spaced = {**frame, 'legacy_text': '  ' + text}
        self.assertIsNotNone(build_structural_evidence(spaced, spaced['legacy_text']))
        self.assertIsNone(adapt(spaced, spaced['legacy_text']).trace)
        self.assertIsNotNone(build_structural_evidence(frame, '  ' + text))
        self.assertIsNone(adapt(frame, '  ' + text).trace)

    def test_default_and_composite_renderer_labels_do_not_become_known_sources(self):
        for slots in ({}, {'purpose_clause': 'standing', 'anchor': 'in the garage'}):
            self.assertIsNone(component_for(slots, activity_first=False).trace)


if __name__ == '__main__':
    unittest.main()
