"""Eligibility must be earned by concrete, supported syntax before selection."""

import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.schema import ActionFrame  # noqa: E402
from pipeline.prompt_realizer import build_content_plan  # noqa: E402
from pipeline import syntax_family_selector as selector  # noqa: E402
from pipeline.syntax_family_selector import eligible_syntax_families  # noqa: E402
from vocab.syntax_families import BASELINE_FAMILY  # noqa: E402


def fixture(action="checking a transit card", *, scene="at the station platform", subject="A solo girl in a navy coat",
            verb="checking", surface="gerund", primary_object="transit card"):
    frame = ActionFrame(legacy_text=action, main_verb=verb, primary_object=primary_object)
    metadata = {"surface": surface, "rendered_clause": action}
    plan = build_content_plan(seed=7, subject_clause=subject, action_clause=action, scene_clause=scene,
                              action_frame=frame, action_surface=metadata, template_roles={"body": ["focused"]})
    return plan, frame, metadata


class TestSyntaxFamilySelector(unittest.TestCase):
    def test_safe_concrete_gerund_can_use_all_six_families(self):
        keys, debug = eligible_syntax_families(*fixture(), return_debug=True)
        self.assertEqual(keys[0], BASELINE_FAMILY)
        self.assertEqual(len(keys), 6)
        self.assertEqual(debug["eligible_syntax_families"], keys)
        self.assertEqual(debug["rejected_syntax_families"], {})
        self.assertEqual(debug["syntax_fallback_reason"], "")

    def test_finite_clause_can_use_safe_families_but_not_action_lead(self):
        for action, verb, obj in (("checks a transit card", "checking", "transit card"),
                                  ("reads a book", "reading", "book"),
                                  ("holds a book", "holding", "book"),
                                  ("waits quietly", "waiting", ""),
                                  ("is checking a transit card", "checking", "transit card")):
            with self.subTest(action=action):
                keys = eligible_syntax_families(*fixture(action, verb=verb, surface="clause", primary_object=obj))
                self.assertEqual(len(keys), 5)
                self.assertNotIn("action_lead_subject_scene", keys)

    def test_baseline_is_available_for_empty_unknown_or_unmatched_inputs(self):
        for kwargs in ({"action": "", "scene": "", "subject": "", "surface": "unknown"},
                       {"surface": "nonsense"}, {"subject": ""}, {"scene": ""}):
            with self.subTest(kwargs=kwargs):
                keys, debug = eligible_syntax_families(*fixture(**kwargs), return_debug=True)
                self.assertEqual(keys, [BASELINE_FAMILY])
                self.assertEqual(debug["syntax_fallback_reason"], "baseline_only")
                self.assertEqual(len(debug["rejected_syntax_families"]), 5)
        plan, frame, surface = fixture()
        plan = replace(plan, discourse_roles=["unknown_role"])
        self.assertEqual(eligible_syntax_families(plan, frame, surface), [BASELINE_FAMILY])

    def test_rendered_surface_overrides_original_gerund_labels(self):
        for rendered in ("fragment", "framed", "clause"):
            plan, frame, surface = fixture()
            surface.update(surface=rendered, input_surface="gerund")
            with self.subTest(rendered=rendered):
                self.assertEqual(eligible_syntax_families(plan, frame, surface), [BASELINE_FAMILY])

    def test_mislabeled_body_fragment_and_noun_clause_cannot_force_gerund(self):
        for action in ("hands hovering over a transit card", "her eyes following a train", "the platform lights blink",
                       "something near a transit card", "morning at the station"):
            with self.subTest(action=action):
                self.assertEqual(eligible_syntax_families(*fixture(action)), [BASELINE_FAMILY])

    def test_independent_subject_or_unvalidated_tail_is_rejected(self):
        for action, verb in (("waiting while the train arrives", "waiting"),
                             ("checking a transit card, her hands trembling", "checking"),
                             ("checking a transit card and another girl waves", "checking"),
                             ("checking a transit card; reading a book", "checking"),
                             ("checking a transit card because it matters", "checking")):
            with self.subTest(action=action):
                self.assertEqual(eligible_syntax_families(*fixture(action, verb=verb)), [BASELINE_FAMILY])

    def test_supported_coordinated_gerunds_share_the_subject(self):
        for action in ("checking a transit card while holding a book", "checking a transit card, watching the screen"):
            with self.subTest(action=action):
                self.assertIn("action_lead_subject_scene", eligible_syntax_families(*fixture(action)))

    def test_unparsed_action_and_subject_tails_never_prove_attachment(self):
        for action in ("checking a transit card before the train arrives", "checking a transit card after rain stops",
                       "checking a transit card / the lights blink", "checking machines hum near a transit card",
                       "waiting passengers leave", "checking a transit card during the train arrival"):
            with self.subTest(action=action):
                self.assertEqual(eligible_syntax_families(*fixture(action)), [BASELINE_FAMILY])
        for subject in ("A running girl in a navy coat smiles", "A solo girl in a navy coat and a nurse",
                        "A girl with a coat smiles"):
            with self.subTest(subject=subject):
                self.assertEqual(eligible_syntax_families(*fixture(subject=subject)), [BASELINE_FAMILY])

    def test_positive_counterparts_for_each_retained_bounded_form(self):
        for action, verb, obj, subject in (
            ("waiting quietly", "waiting", "", "A girl"),
            ("checking a transit card at the tea room", "checking", "transit card", "A calm solo girl"),
            ("holding a book", "holding", "book", "The solo girl in a blue dress"),
        ):
            with self.subTest(action=action, subject=subject):
                self.assertEqual(len(eligible_syntax_families(*fixture(action, verb=verb, primary_object=obj, subject=subject))), 6)

    def test_unknown_or_nonboolean_safety_facts_cannot_authorize_a_family(self):
        _, debug = eligible_syntax_families(*fixture(), return_debug=True)
        for missing in (None, "absent"):
            facts = dict(debug["safety_facts"])
            if missing is None:
                facts["independent_action_subject"] = None
            else:
                del facts["independent_action_subject"]
            with self.subTest(missing=missing), patch.object(selector, "_facts", return_value=(facts, "gerund", [])):
                self.assertEqual(eligible_syntax_families(*fixture()), [BASELINE_FAMILY])
        facts = {**debug["safety_facts"], "same_subject_attachment_safe": 1}
        with patch.object(selector, "_facts", return_value=(facts, "gerund", [])):
            self.assertNotIn("action_lead_subject_scene", eligible_syntax_families(*fixture()))

    def test_mapping_frame_and_validated_extension_preserve_authority(self):
        plan, frame, surface = fixture("checking a transit card while holding a book")
        frame.legacy_text = "checking a transit card"
        self.assertEqual(len(eligible_syntax_families(plan, frame.to_dict(), surface)), 6)

    def test_arbitrary_object_text_and_semantic_verb_cues_are_not_noun_evidence(self):
        for action, obj in (("checking machines hum", "machines hum"),
                            ("checking a transit card while holding sipping", "transit card")):
            with self.subTest(action=action):
                self.assertEqual(eligible_syntax_families(*fixture(action, primary_object=obj)), [BASELINE_FAMILY])

    def test_stale_frame_version_verb_and_object_cannot_authorize_advanced_rendering(self):
        for update in ({"legacy_text": "reading a book"}, {"schema_version": "action-frame/v999"},
                       {"main_verb": "reading"}, {"primary_object": "book"}):
            plan, frame, surface = fixture()
            for key, value in update.items():
                setattr(frame, key, value)
            with self.subTest(update=update):
                keys = eligible_syntax_families(plan, frame, surface)
                self.assertNotIn("action_lead_subject_scene", keys)
                self.assertNotIn("subject_scene_action", keys)
                self.assertNotIn("subject_action_scene_insert", keys)

    def test_missing_frame_does_not_infer_predicate_authority_from_plan(self):
        plan, _, surface = fixture()
        keys = eligible_syntax_families(plan, None, surface)
        self.assertIn(BASELINE_FAMILY, keys)
        self.assertNotIn("subject_scene_action", keys)
        self.assertNotIn("action_lead_subject_scene", keys)

    def test_stale_surface_clause_or_missing_surface_falls_back(self):
        plan, frame, surface = fixture()
        surface["rendered_clause"] = "reading a book"
        self.assertEqual(eligible_syntax_families(plan, frame, surface), [BASELINE_FAMILY])
        self.assertEqual(eligible_syntax_families(plan, frame, None), [BASELINE_FAMILY])

    def test_unresolved_templates_and_unsupported_scenes_fall_back(self):
        for kwargs in ({"action": "checking {object}"}, {"subject": "{subject_clause}"},
                       {"scene": "{scene_clause}"}, {"scene": "the background opening into the platform"},
                       {"scene": "at"}, {"scene": "at the station; a train arrives"},
                       {"scene": "at an unrecognized imaginary place"}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(eligible_syntax_families(*fixture(**kwargs)), [BASELINE_FAMILY])

    def test_duplicate_scene_anchor_and_canonical_alias_block_insertion(self):
        for action, scene in (("waiting at the station platform", "at the station platform"),
                              ("waiting in the tea room", "inside the tea room")):
            keys, debug = eligible_syntax_families(*fixture(action, scene=scene, verb="waiting", primary_object=""), return_debug=True)
            self.assertNotIn("subject_action_scene_insert", keys)
            self.assertTrue(debug["safety_facts"]["scene_action_overlap"])

    def test_overlap_detection_respects_word_boundaries(self):
        plan, frame, surface = fixture("checking a station platformer guide", primary_object="guide")
        _, debug = eligible_syntax_families(plan, frame, surface, return_debug=True)
        self.assertFalse(debug["safety_facts"]["scene_action_overlap"])

    def test_policy_and_solo_violations_do_not_enable_alternatives(self):
        for kwargs in ({"subject": "two girls in navy coats"}, {"subject": "A solo girl and another girl"},
                       {"scene": "in a masterpiece"}, {"action": "checking a transit card with another person"}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(eligible_syntax_families(*fixture(**kwargs)), [BASELINE_FAMILY])

    def test_catalog_order_and_inputs_do_not_change_eligibility_or_mutate(self):
        catalog = json.loads((ROOT / "vocab/data/natural_language_realizer_v2.json").read_text(encoding="utf-8"))
        args = fixture()
        before = copy.deepcopy((args, catalog))
        first = eligible_syntax_families(*args, catalog=catalog, return_debug=True)
        reversed_catalog = copy.deepcopy(catalog)
        reversed_catalog["families"].reverse()
        self.assertEqual(first, eligible_syntax_families(*args, catalog=reversed_catalog, return_debug=True))
        self.assertEqual((args, catalog), before)

    def test_invalid_metadata_fails_closed_instead_of_repairing_it(self):
        with self.assertRaises(ValueError):
            eligible_syntax_families(*fixture(), catalog={})

    def test_separate_process_hash_seeds_are_deterministic(self):
        script = """
import json
from assets.test_syntax_family_selector import fixture
from pipeline.syntax_family_selector import eligible_syntax_families
print(json.dumps(eligible_syntax_families(*fixture(), return_debug=True), sort_keys=True))
"""
        results = [subprocess.check_output([sys.executable, "-c", script], cwd=ROOT,
                    env={**os.environ, "PYTHONHASHSEED": value}) for value in ("1", "999")]
        self.assertEqual(results[0], results[1])


if __name__ == "__main__":
    unittest.main()
