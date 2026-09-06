"""N2.1–N2.6 contracts for candidate realization and actual Builder metadata.

These tests exercise production APIs; all original expected failures are resolved.
Current v1 behavior remains distinct from the explicit internal v2 candidate path.
"""

import copy
from dataclasses import replace
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.context_ops import patch_context  # noqa: E402
from core.schema import ActionFrame, PromptContext  # noqa: E402
from core.semantic_policy import find_banned_terms  # noqa: E402
from core.solo_safety import is_solo_safe_text  # noqa: E402
from pipeline.prompt_orchestrator import build_prompt_from_context, build_prompt_text  # noqa: E402
from pipeline.prompt_realizer import build_content_plan, realize_content_plan  # noqa: E402
from tools.effective_diversity_signatures import build_semantic_signatures  # noqa: E402
from tools.workflow_prompt_runner import canonical_json_bytes  # noqa: E402


FAMILIES = (
    "subject_action_scene", "subject_action__scene_tail", "scene_lead_subject_action",
    "action_lead_subject_scene", "subject_scene_action", "subject_action_scene_insert",
)
SUBJECT = "A calm solo girl in a navy coat"
ACTION = "checks a transit card"
SCENE = "at the station platform"


def fixture(family="subject_action_scene", *, seed=7, subject=SUBJECT, action=ACTION,
            scene=SCENE, surface="clause", verb="checking", primary_object="transit card"):
    frame = ActionFrame(legacy_text=action, main_verb=verb, primary_object=primary_object)
    plan = build_content_plan(
        seed=seed, subject_clause=subject, action_clause=action, scene_clause=scene,
        action_frame=frame, action_surface={"surface": surface}, syntax_family=family,
        template_roles={"body": ["focused"]},
    )
    return plan, frame


def render_plan(plan, frame, **kwargs):
    return realize_content_plan(
        plan, action_frame=frame,
        action_surface={"surface": plan.lexical_choice, "rendered_clause": plan.semantic_slots["adjunct"]},
        **kwargs,
    )


class FactAssertions(unittest.TestCase):
    def assert_fixture_facts(self, text):
        """A bounded lexical oracle for this fixture, not general English NLP."""
        lowered = text.lower()
        for fact in ("calm", "solo girl", "navy coat", "transit card", "station platform"):
            self.assertEqual(lowered.count(fact), 1, (fact, text))
        self.assertEqual(len(re.findall(r"\bgirl\b", lowered)), 1)
        self.assertEqual(len(re.findall(r"\b(?:checks|checking)\b", lowered)), 1)
        self.assertFalse(find_banned_terms(text), text)
        self.assertTrue(is_solo_safe_text(text), text)
        # Only fixture facts and small grammatical connectives may appear.
        words = set(re.findall(r"\b[a-z]+\b", lowered))
        allowed = set(re.findall(r"\b[a-z]+\b", (SUBJECT + " " + ACTION + " " + SCENE).lower()))
        allowed.update({"checking", "is", "she", "her", "and", "with", "while", "scene", "set"})
        self.assertFalse(words - allowed, (words - allowed, text))


class TestRealizerSemanticGuards(FactAssertions):
    def test_all_requested_families_preserve_fixture_facts(self):
        for family in FAMILIES:
            with self.subTest(family=family):
                plan, frame = fixture(family)
                self.assert_fixture_facts(render_plan(plan, frame))

    def test_fact_oracle_rejects_loss_invention_and_duplicate_protagonist(self):
        plan, frame = fixture()
        text = render_plan(plan, frame)
        for broken in (
            text.replace("transit card", "phone"), text.replace("station platform", "beach"),
            text.replace("calm ", ""), text + " A second girl arrives.",
            text + " A bicycle is nearby.", text + " She dances.", text + " masterpiece",
        ):
            with self.subTest(broken=broken), self.assertRaises(AssertionError):
                self.assert_fixture_facts(broken)

    def test_object_and_location_changes_survive_rendering(self):
        for family in FAMILIES:
            with self.subTest(family=family):
                plan, frame = fixture(family, action="checks a ticket", primary_object="ticket", scene="at the bus shelter")
                text = render_plan(plan, frame).lower()
                self.assertEqual(text.count("ticket"), 1)
                self.assertEqual(text.count("bus shelter"), 1)
                self.assertNotIn("transit card", text)
                self.assertNotIn("station platform", text)

    def test_secondary_object_is_not_lost_when_primary_object_is_known(self):
        action = "checking a transit card while holding a ticket"
        for family in FAMILIES:
            with self.subTest(family=family):
                plan, frame = fixture(family, action=action, surface="gerund")
                text = render_plan(plan, frame).lower()
                self.assertEqual(text.count("transit card"), 1)
                self.assertEqual(text.count("ticket"), 1)
                self.assertIn("holding", text)

    def test_no_object_or_scene_is_invented_for_absent_slots(self):
        plan, frame = fixture(action="waiting quietly", verb="waiting", primary_object="", scene="")
        text = render_plan(plan, frame).lower()
        self.assertIn("waiting quietly", text)
        self.assertNotIn("transit card", text)
        self.assertNotIn("station", text)
        self.assertFalse(find_banned_terms(text))
        self.assertTrue(is_solo_safe_text(text))

    def test_missing_subject_does_not_invent_a_protagonist(self):
        plan, frame = fixture(subject="", action="checking a transit card", surface="gerund")
        text = render_plan(plan, frame).lower()
        self.assertNotIn("girl", text)
        self.assertIn("transit card", text)

    def test_same_seed_is_deterministic_and_inputs_are_not_mutated(self):
        for seed in (0, 7, 999):
            for family in FAMILIES:
                with self.subTest(seed=seed, family=family):
                    plan, frame = fixture(family, seed=seed)
                    before = copy.deepcopy((plan.to_dict(), frame.to_dict()))
                    text = render_plan(plan, frame)
                    repeat, repeat_frame = fixture(family, seed=seed)
                    self.assertEqual(text, render_plan(repeat, repeat_frame))
                    self.assertEqual(plan.to_dict(), repeat.to_dict())
                    self.assertEqual((plan.to_dict(), frame.to_dict()), before)
                    self.assertEqual(set(plan.named_seed_streams), {"lexical", "syntax", "template"})

    def test_fragment_and_independent_subject_clause_do_not_force_action_lead(self):
        for action, surface in (("hands hovering over a transit card", "fragment"),
                                ("the platform lights blink", "clause"),
                                ("in the middle of checking a transit card", "framed")):
            # Even a gerund main_verb must not override the actual rendered surface.
            with self.subTest(surface=surface):
                baseline, baseline_frame = fixture(action=action, surface=surface)
                unsafe, unsafe_frame = fixture("action_lead_subject_scene", action=action, surface=surface)
                self.assertEqual(render_plan(unsafe, unsafe_frame), render_plan(baseline, baseline_frame))

    def test_missing_scene_and_unknown_family_fall_back(self):
        baseline, baseline_frame = fixture(scene="")
        scene_lead, scene_lead_frame = fixture("scene_lead_subject_action", scene="")
        self.assertEqual(render_plan(scene_lead, scene_lead_frame), render_plan(baseline, baseline_frame))
        baseline, baseline_frame = fixture()
        unknown, unknown_frame = fixture("unknown_syntax_family")
        self.assertEqual(render_plan(unknown, unknown_frame), render_plan(baseline, baseline_frame))

    def test_negated_action_is_not_rewritten_as_positive(self):
        for family in FAMILIES:
            with self.subTest(family=family):
                plan, frame = fixture(family, action="does not check a transit card", surface="clause")
                self.assertIn("does not check a transit card", render_plan(plan, frame).lower())

    def test_placeholder_substitution_path_preserves_real_facts(self):
        for composition_mode in (False, True):
            text = build_prompt_text(
                template="{subject_clause} {action_clause} {scene_clause}", composition_mode=composition_mode,
                seed=7, subj="a solo girl", costume="navy coat", loc="station platform",
                action="checking a transit card", garnish="", meta_mood="", staging_tags="",
            )
            with self.subTest(composition_mode=composition_mode):
                self.assertIn("transit card", text.lower())
                self.assertIn("station platform", text.lower())
                self.assertEqual(len(re.findall(r"\bgirl\b", text.lower())), 1)
                self.assertNotIn("{", text)
                self.assertFalse(find_banned_terms(text))
                self.assertTrue(is_solo_safe_text(text))

    def test_public_builder_keeps_semantic_only_policy_with_banned_garnish_input(self):
        for composition_mode in (False, True):
            with self.subTest(composition_mode=composition_mode):
                text = build_prompt_text(
                    template="{subject_clause} {action_clause} {scene_clause}", composition_mode=composition_mode,
                    seed=7, subj="a solo girl", costume="navy coat", loc="station platform",
                    action="checking a transit card", garnish="masterpiece, 8k, cinematic lighting",
                    meta_mood="", staging_tags="",
                )
                self.assertFalse(find_banned_terms(text))
                self.assertIn("transit card", text.lower())
                self.assertIn("station platform", text.lower())
                self.assertTrue(is_solo_safe_text(text))


class TestRealizerV2InitialSyntax(FactAssertions):
    def test_natural_text_snapshots_and_selected_family(self):
        snapshots = {
            "subject_action_scene": "A calm solo girl in a navy coat checks a transit card at the station platform.",
            "subject_action__scene_tail": "A calm solo girl in a navy coat checks a transit card. The scene is set at the station platform.",
            "scene_lead_subject_action": "At the station platform, a calm solo girl in a navy coat checks a transit card.",
        }
        for family, expected in snapshots.items():
            with self.subTest(family=family):
                plan, frame = fixture(family)
                text, debug = render_plan(plan, frame, return_debug=True)
                self.assertEqual(text, expected)
                self.assert_fixture_facts(text)
                self.assertEqual(debug["realizer_version"], "v2")
                self.assertEqual(debug["syntax_family"], family)
                self.assertEqual(debug["syntax_fallback_reason"], "")
                self.assertEqual(len(debug["eligible_syntax_families"]), 5)
                self.assertEqual(debug["clause_order"], ["scene", "subject", "action"] if family == "scene_lead_subject_action" else ["subject", "action", "scene"])

    def test_gerund_and_existing_copula_preserve_whole_predicate(self):
        for action, surface in (("checking a transit card while holding a ticket", "gerund"),
                                ("is checking a transit card", "clause")):
            plan, frame = fixture(action=action, surface=surface)
            text = render_plan(plan, frame)
            self.assertIn("is checking a transit card", text)
            self.assertNotIn("is is", text)
            if "ticket" in action:
                self.assertIn("while holding a ticket", text)

    def test_boundary_punctuation_and_initial_case_normalize_without_lowering_facts(self):
        plan, frame = fixture("scene_lead_subject_action", subject="A calm solo girl in a NAVY coat,",
                              action="CHECKS a transit card.", scene="AT the station platform.")
        text = render_plan(plan, frame)
        self.assertEqual(text, "At the station platform, a calm solo girl in a NAVY coat checks a transit card.")
        self.assertNotIn(".,", text)

    def test_unknown_requests_report_actual_baseline_fallback(self):
        for family in ("unknown_family", "unimplemented_optional_family"):
            with self.subTest(family=family):
                plan, frame = fixture(family)
                text, debug = render_plan(plan, frame, return_debug=True)
                baseline, baseline_frame = fixture()
                self.assertEqual(text, render_plan(baseline, baseline_frame))
                self.assertEqual(debug["syntax_family"], "subject_action_scene")
                self.assertTrue(debug["syntax_fallback_reason"])

    def test_unsafe_or_missing_frame_does_not_use_baseline_membership_as_safety_proof(self):
        for frame_change in (None, {"schema_version": "action-frame/v999"}, {"legacy_text": "reading a book"}):
            plan, frame = fixture("scene_lead_subject_action")
            if frame_change is None:
                frame = None
            else:
                for key, value in frame_change.items():
                    setattr(frame, key, value)
            text, debug = render_plan(plan, frame, return_debug=True)
            legacy = realize_content_plan(replace(plan, syntax_family="single-sentence-scene-tail"))
            self.assertEqual(text, legacy)
            self.assertEqual(debug["realizer_version"], "v1")
            self.assertEqual(debug["syntax_family"], "subject_action_scene")
            self.assertEqual(debug["syntax_fallback_reason"], "unsafe_for_v2")

    def test_stale_rendered_surface_and_scene_overlap_retain_v1_fallback(self):
        for action, surface in (("checks a transit card", {"surface": "clause", "rendered_clause": "reads a book"}),
                                ("checks a transit card at the station platform", {"surface": "clause"})):
            plan, frame = fixture("scene_lead_subject_action", action=action)
            text, debug = realize_content_plan(plan, action_frame=frame, action_surface=surface, return_debug=True)
            self.assertEqual(debug["realizer_version"], "v1")
            self.assertTrue(debug["syntax_fallback_reason"])
            self.assertEqual(text, realize_content_plan(replace(plan, syntax_family="single-sentence-scene-tail")))

    def test_malformed_v2_clause_order_cannot_drop_or_duplicate_slots(self):
        plan, frame = fixture()
        for order in (("subject", "scene"), ("subject", "subject", "scene"), ("subject", "action", "unknown")):
            with self.subTest(order=order), self.assertRaises(ValueError):
                render_plan(replace(plan, clause_order=order), frame)

    def test_original_plan_only_call_keeps_legacy_custom_order_and_unknown_labels(self):
        plan, _ = fixture("custom-old-label")
        plan = replace(plan, clause_order=("scene", "subject", "action"))
        self.assertEqual(realize_content_plan(plan), "at the station platform, A calm solo girl in a navy coat, checks a transit card.")

    def test_frame_only_surface_is_validated_and_empty_surface_does_not_authorize_v2(self):
        plan, frame = fixture()
        self.assertEqual(realize_content_plan(plan, action_frame=frame), render_plan(plan, frame))
        for surface in ({}, {"surface": "unknown"}, {"surface": "gerund"}):
            with self.subTest(surface=surface):
                _, debug = realize_content_plan(plan, action_frame=frame, action_surface=surface, return_debug=True)
                self.assertEqual(debug["realizer_version"], "v1")
        _, debug = realize_content_plan(replace(plan, lexical_choice="unknown"), action_frame=frame, return_debug=True)
        self.assertEqual(debug["realizer_version"], "v1")

    def test_subject_action_scene_does_not_separate_subject_from_finite_predicate(self):
        plan, frame = fixture("subject_action_scene")
        text = render_plan(plan, frame)
        self.assert_fixture_facts(text)
        self.assertRegex(text.lower(), r"navy coat (?:checks|is checking) a transit card")

    def test_subject_action_scene_tail_has_two_sentences(self):
        plan, frame = fixture("subject_action__scene_tail")
        text = render_plan(plan, frame)
        self.assert_fixture_facts(text)
        sentences = [part for part in re.split(r"[.!?]+", text) if part.strip()]
        self.assertEqual(len(sentences), 2)
        self.assertIn("transit card", sentences[0].lower())
        self.assertIn("station platform", sentences[1].lower())

    def test_scene_lead_precedes_subject_and_action(self):
        plan, frame = fixture("scene_lead_subject_action")
        text = render_plan(plan, frame)
        self.assert_fixture_facts(text)
        self.assertLess(text.index("station platform"), text.index("solo girl"))



class TestRealizerV2RemainingSyntax(FactAssertions):
    def test_all_six_families_have_distinct_selected_text_for_the_same_gerund_facts(self):
        snapshots = {
            "subject_action_scene": "A calm solo girl in a navy coat is checking a transit card at the station platform.",
            "subject_action__scene_tail": "A calm solo girl in a navy coat is checking a transit card. The scene is set at the station platform.",
            "scene_lead_subject_action": "At the station platform, a calm solo girl in a navy coat is checking a transit card.",
            "action_lead_subject_scene": "Checking a transit card, a calm solo girl in a navy coat is at the station platform.",
            "subject_scene_action": "A calm solo girl in a navy coat, at the station platform, is checking a transit card.",
            "subject_action_scene_insert": "A calm solo girl in a navy coat is checking a transit card, at the station platform.",
        }
        observed = []
        for family, expected in snapshots.items():
            with self.subTest(family=family):
                plan, frame = fixture(family, action="checking a transit card", surface="gerund")
                text, debug = render_plan(plan, frame, return_debug=True)
                self.assertEqual(text, expected)
                self.assertEqual(debug["syntax_family"], family)
                self.assertEqual(debug["realizer_version"], "v2")
                self.assertEqual(set(debug["eligible_syntax_families"]), set(FAMILIES))
                self.assert_fixture_facts(text)
                order = {"scene_lead_subject_action": ["scene", "subject", "action"],
                         "action_lead_subject_scene": ["action", "subject", "scene"],
                         "subject_scene_action": ["subject", "scene", "action"]}.get(family, ["subject", "action", "scene"])
                self.assertEqual(debug["clause_order"], order)
                self.assertEqual(debug["syntax_fallback_reason"], "")
                observed.append(text)
        self.assertEqual(len(set(observed)), 6)

    def test_action_lead_rejects_finite_copula_and_fragment_surfaces(self):
        for action, surface in (("checks a transit card", "clause"), ("is checking a transit card", "clause"),
                                ("hands hovering over a transit card", "fragment"),
                                ("in the middle of checking a transit card", "framed")):
            with self.subTest(action=action):
                plan, frame = fixture("action_lead_subject_scene", action=action, surface=surface)
                text, debug = render_plan(plan, frame, return_debug=True)
                baseline, base_frame = fixture(action=action, surface=surface)
                self.assertEqual(text, render_plan(baseline, base_frame))
                self.assertEqual(debug["syntax_family"], "subject_action_scene")
                self.assertTrue(debug["syntax_fallback_reason"])

    def test_compound_predicate_and_secondary_object_survive_each_new_family(self):
        for family in FAMILIES[3:]:
            for action, surface in (("checking a transit card while holding a ticket", "gerund"),
                                    ("checks a transit card and holds a book", "clause"),
                                    ("is checking a transit card", "clause")):
                with self.subTest(family=family, action=action):
                    plan, frame = fixture(family, action=action, surface=surface)
                    text, debug = render_plan(plan, frame, return_debug=True)
                    self.assertIn(action.lower(), text.lower())
                    self.assertEqual(text.lower().count("transit card"), 1)
                    self.assertEqual(text.lower().count("station platform"), 1)
                    self.assertNotIn("is is", text.lower())
                    self.assertFalse(find_banned_terms(text))
                    self.assertTrue(is_solo_safe_text(text))
                    if family == "action_lead_subject_scene" and surface == "clause":
                        self.assertEqual(debug["syntax_family"], "subject_action_scene")
                    else:
                        self.assertEqual(debug["syntax_family"], family)

    def test_new_families_fall_back_when_scene_or_frame_is_unsafe(self):
        for family in FAMILIES[3:]:
            for action, scene in (("checking a transit card at the station platform", SCENE),
                                  ("checking a transit card", ""),
                                  ("checking a transit card before the train arrives", SCENE)):
                with self.subTest(family=family, action=action, scene=scene):
                    plan, frame = fixture(family, action=action, scene=scene, surface="gerund")
                    text, debug = render_plan(plan, frame, return_debug=True)
                    self.assertEqual(debug["realizer_version"], "v1")
                    self.assertEqual(debug["syntax_family"], "subject_action_scene")
                    self.assertEqual(text, realize_content_plan(replace(plan, syntax_family="single-sentence-scene-tail")))

    def test_gerund_action_lead_attaches_to_the_existing_subject(self):
        plan, frame = fixture("action_lead_subject_scene", action="checking a transit card", surface="gerund")
        text = render_plan(plan, frame)
        self.assert_fixture_facts(text)
        self.assertTrue(text.lower().startswith("checking a transit card"), text)
        self.assertLess(text.index("transit card"), text.index("solo girl"))

    def test_subject_scene_action_places_scene_before_action(self):
        plan, frame = fixture("subject_scene_action")
        text = render_plan(plan, frame)
        self.assert_fixture_facts(text)
        self.assertLess(text.index("solo girl"), text.index("station platform"))
        self.assertLess(text.index("station platform"), text.index("transit card"))

    def test_scene_insert_keeps_a_connected_predicate_and_single_scene(self):
        plan, frame = fixture("subject_action_scene_insert")
        text, debug = render_plan(plan, frame, return_debug=True)
        self.assertEqual(debug["syntax_family"], "subject_action_scene_insert")
        self.assert_fixture_facts(text)
        predicate = re.search(r"\b(?:checks|checking)\b", text.lower())
        self.assertIsNotNone(predicate)
        self.assertLess(predicate.start(), text.index("station platform"))
        self.assertRegex(text.lower(), r"navy coat (?:checks|is checking)\b")


class TestRealizerBuilderDebug(unittest.TestCase):
    def test_actual_v1_family_metadata_and_seed_replay(self):
        context = patch_context({}, updates={"subj": "a solo girl", "loc": "station platform", "action": "checking a transit card"})
        before = copy.deepcopy(context.to_dict())
        observed = set()
        for seed in range(16):
            updated, prompt = build_prompt_from_context(context, "", True, seed)
            repeated, repeated_prompt = build_prompt_from_context(context, "", True, seed)
            decision = updated.history[-1].decision
            self.assertEqual(prompt, repeated_prompt)
            self.assertEqual(canonical_json_bytes(updated.to_dict()), canonical_json_bytes(repeated.to_dict()))
            self.assertEqual(decision["realizer_version"], "v1")
            self.assertEqual(decision["eligible_syntax_families"], ["single-sentence-scene-tail", "two-sentence-scene-tail"])
            self.assertEqual(decision["syntax_family"], decision["content_plan"]["syntax_family"])
            self.assertEqual(decision["syntax_fallback_reason"], "")
            self.assertEqual(decision["clause_order"], ["subject", "action", "scene"])
            for key in ("template_key", "intro_key", "body_key", "end_key"):
                self.assertTrue(decision[key])
            observed.add(decision["syntax_family"])
        self.assertEqual(observed, {"single-sentence-scene-tail", "two-sentence-scene-tail"})
        self.assertEqual(context.to_dict(), before)

    def test_legacy_template_reports_unknown_structure_without_parsing_its_sentences(self):
        context = patch_context({}, updates={"subj": "a solo girl", "loc": "station platform", "action": "checking a transit card"})
        for template in ("", "{subject_clause}. {action_clause}. {scene_clause}."):
            updated, prompt = build_prompt_from_context(context, template, False, 7)
            decision = updated.history[-1].decision
            self.assertTrue(prompt)
            self.assertEqual(decision["realizer_version"], "v1")
            self.assertIsNone(decision["syntax_family"])
            self.assertEqual(decision["eligible_syntax_families"], [])
            self.assertEqual(decision["clause_order"], [])
            self.assertEqual(decision["syntax_fallback_reason"], "legacy_template_no_structural_metadata")
            self.assertNotIn("content_plan", decision)

    def test_decision_roundtrips_in_context_without_version_change(self):
        context = patch_context({}, updates={"subj": "a solo girl", "loc": "tea room", "action": "reading a book"})
        for composition_mode in (False, True):
            updated, _ = build_prompt_from_context(context, "", composition_mode, 7)
            restored = PromptContext.from_dict(json.loads(updated.to_json()))
            self.assertEqual(restored.context_version, context.context_version)
            self.assertEqual(restored.history[-1].decision, updated.history[-1].decision)

    def test_debug_flag_does_not_change_prompt(self):
        for composition_mode in (False, True):
            kwargs = dict(template="", composition_mode=composition_mode, seed=7, subj="a solo girl",
                          costume="navy coat", loc="station platform", action="checking a transit card")
            plain = build_prompt_text(**kwargs)
            text, decision = build_prompt_text(**kwargs, return_debug=True)
            self.assertEqual(plain, text)
            self.assertIn("realizer_version", decision)
            self.assertIn("clause_order", decision)

    def test_audit_consumes_authoritative_metadata_not_changed_prose(self):
        context = patch_context({}, updates={"subj": "student", "loc": "tea room", "action": "reading a book"})
        for composition_mode in (False, True):
            updated, prompt = build_prompt_from_context(context, "", composition_mode, 7)
            decision = updated.history[-1].decision
            record = {"final_context": context.to_dict(), "raw_prompt": prompt}
            projected = build_semantic_signatures(record, builder_decision=decision)
            self.assertEqual(projected["axes"]["syntax_family"], decision["syntax_family"])
            expected_source = "builder.syntax_family" if composition_mode else "missing"
            self.assertEqual(projected["diagnostics"]["extraction_sources"]["syntax_family"], expected_source)
            changed = {**decision, "prompt": "Unrelated sentences. With different punctuation!"}
            changed_record = {**record, "raw_prompt": changed["prompt"]}
            again = build_semantic_signatures(changed_record, builder_decision=changed)
            self.assertEqual(projected["core"], again["core"])
            self.assertEqual(projected["axes"], again["axes"])

    def test_builder_decision_exposes_rendering_and_fallback_metadata(self):
        context = patch_context({}, updates={"subj": "a solo girl", "loc": "station platform",
                                            "action": "checking a transit card"})
        updated, _ = build_prompt_from_context(context, "", True, 7)
        decision = updated.history[-1].decision
        for field in ("realizer_version", "syntax_family", "eligible_syntax_families", "syntax_fallback_reason", "clause_order"):
            self.assertIn(field, decision)
        self.assertTrue(decision["realizer_version"])
        self.assertIn(decision["syntax_family"], decision["eligible_syntax_families"])
        self.assertIsInstance(decision["syntax_fallback_reason"], str)
        self.assertEqual(decision["clause_order"], decision["content_plan"]["clause_order"])


if __name__ == "__main__":
    unittest.main()
