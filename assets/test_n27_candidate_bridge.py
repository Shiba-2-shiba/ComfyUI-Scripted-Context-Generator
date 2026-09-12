import copy
import unittest
from dataclasses import replace
from assets.test_syntax_family_selector import fixture
from pipeline.prompt_realizer import realize_content_plan
from pipeline.v2_candidate_bridge import FAMILIES, render_candidate


class TestCandidateBridge(unittest.TestCase):
    def test_builder_integration_appends_staging_once_and_replays(self):
        from prompt_renderer import build_prompt_text
        plan, frame, surface = fixture(scene="in the tea room")
        parts = {"intro": "{subject_clause}", "body": "{action_clause}", "end": "{scene_clause}"}
        kwargs = dict(template="", composition_mode=True, seed=3, subj="a solo girl", costume="a navy coat",
                      loc="the tea room", action=frame.legacy_text, garnish="", meta_mood="",
                      staging_tags="calm expression", action_frame=frame.to_dict(),
                      template_entries_fn=lambda part: [{"key": part + "_fixture", "text": parts[part], "roles": ["focused", "neutral"]}])
        text, debug = build_prompt_text(**kwargs, return_debug=True)
        self.assertTrue(debug["candidate_v2_applied"])
        self.assertEqual(text.count("calm expression"), 1)
        self.assertEqual(text, build_prompt_text(**kwargs))
        self.assertEqual(debug["syntax_family"], debug["content_plan"]["syntax_family"])
        self.assertEqual(debug["clause_order"], debug["content_plan"]["clause_order"])
        self.assertEqual(debug["intro_key"], "intro_fixture")

    def test_supported_fixture_exercises_six_with_actual_metadata(self):
        plan, frame, surface = fixture()
        original = copy.deepcopy((plan, frame, surface))
        seen = set()
        for seed in range(128):
            legacy = replace(plan, syntax_family="single-sentence-scene-tail")
            text, debug = realize_content_plan(legacy, return_debug=True)
            result, actual, candidate = render_candidate(plan, text, debug, frame, surface, [], seed)
            again = render_candidate(plan, text, debug, frame, surface, [], seed)
            self.assertEqual((result, actual, candidate), again)
            self.assertTrue(candidate["candidate_v2_applied"])
            self.assertEqual(candidate["syntax_family"], actual.syntax_family)
            self.assertEqual(candidate["clause_order"], list(actual.clause_order))
            self.assertEqual(result.lower().count("transit card"), 1)
            seen.add(candidate["syntax_family"])
        self.assertEqual(seen, set(FAMILIES))
        self.assertEqual((plan, frame, surface), original)

    def test_ineligible_plan_preserves_exact_v1_for_both_structures(self):
        for family in ("single-sentence-scene-tail", "two-sentence-scene-tail"):
            plan, frame, surface = fixture(subject="A solo girl with long curly hair and green eyes")
            plan = replace(plan, syntax_family=family)
            before, debug = realize_content_plan(plan, return_debug=True)
            result, actual, candidate = render_candidate(plan, before, debug, frame, surface, [], 3)
            self.assertEqual(result, before)
            self.assertFalse(candidate["candidate_v2_applied"])
            self.assertEqual(candidate["realizer_version"], "v1")
            self.assertEqual(candidate["fallback_origin_syntax_family"], family)
            self.assertEqual(candidate["syntax_family"], actual.syntax_family)

    def test_placeholders_resolve_exactly_and_unsupported_surface_never_relabels(self):
        plan, frame, surface = fixture()
        symbolic = replace(plan, semantic_slots={**plan.semantic_slots, "subject": "{subject_clause}", "adjunct": "{action_clause}", "scene": "{scene_clause}"})
        replacements = [("{subject_clause}", plan.semantic_slots["subject"]), ("{action_clause}", plan.semantic_slots["adjunct"]), ("{scene_clause}", plan.semantic_slots["scene"])]
        legacy = replace(symbolic, syntax_family="two-sentence-scene-tail")
        before, debug = realize_content_plan(legacy, return_debug=True)
        text, _, candidate = render_candidate(symbolic, before, debug, frame, surface, replacements, 0)
        self.assertTrue(candidate["candidate_v2_applied"])
        self.assertNotIn("{", text)
        for bad in ({"surface": "framed"}, {"surface": "fragment"}):
            text, _, candidate = render_candidate(symbolic, before, debug, frame, bad, replacements, 0)
            self.assertFalse(candidate["candidate_v2_applied"])
            self.assertEqual(text, before)

if __name__ == "__main__":
    unittest.main()
