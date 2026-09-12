"""Semantic identity comes from selected context metadata, never final prose."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.schema import ActionFrame, PromptContext  # noqa: E402
from tools.effective_diversity_metrics import semantic_uniqueness  # noqa: E402
from tools.effective_diversity_signatures import build_semantic_signatures  # noqa: E402
from tools.workflow_prompt_runner import canonical_json_bytes  # noqa: E402


def context_fixture():
    action = "reading a book by the window"
    slots = {
        "primary_action": action, "purpose": "study", "posture": "sitting beside the window",
        "hand_action": "fingers gripping the book", "gaze_target": "watching a book and a phone",
        "progress_state": "midway", "obstacle_or_trigger": "wind", "social_distance": "viewer",
    }
    return {
        "subj": "student", "loc": "tea_room", "costume": "school_uniform", "action": action,
        "meta": {"mood": "a quiet moment of concentration"},
        "extras": {
            "source_subj_key": "student", "raw_mood_key": "quiet_focused",
            "action_frame": ActionFrame.from_slots(slots, legacy_text=action, main_verb="reading", primary_object="book").to_dict(),
        },
        "history": [
            {"node": "ContextClothingExpander", "decision": {"chosen_type": "separates", "theme": "school_uniform"}},
            {"node": "ContextGarnish", "decision": {"final_tags": ["soft breath", "quiet gaze", "clasped hands", "quiet gaze"]}},
        ],
    }


def scene_entry(ctx, **overrides):
    decision = {
        "action": ctx["action"], "selected_loc": ctx["loc"],
        "action_frame": copy.deepcopy(ctx["extras"]["action_frame"]),
        "slots": copy.deepcopy(ctx["extras"]["action_frame"]["legacy_slots"]),
    }
    decision.update(overrides)
    return {"node": "ContextSceneVariator", "decision": decision}


class TestEffectiveDiversitySignatures(unittest.TestCase):
    def test_all_signature_fields_and_axes_match_selected_metadata(self):
        result = build_semantic_signatures(context_fixture())
        core = {
            "canonical_subject": "student", "canonical_location": "tea_room",
            "action_family_or_main_verb": "verb:reading", "primary_object_or_object_family": "book",
        }
        self.assertEqual(result["core"], core)
        self.assertEqual(result["frame"], {
            **core, "posture": "sitting", "hand_action_family": ["hands"],
            "gaze_target_family": ["book", "phone"], "progress": "midway",
            "stimulus_or_obstacle": "wind", "social_relation": "viewer", "mood": "quiet_focused",
            "clothing_family": "separates", "garnish_family": ["breath", "gaze", "hands"],
        })
        self.assertTrue(result["valid"])
        self.assertEqual(result["axes"], {
            "subject": "student", "location": "tea_room", "action_family": "verb:reading",
            "primary_object_family": "book", "mood": "quiet_focused", "clothing_family": "separates",
            "garnish_family": ["breath", "gaze", "hands"], "syntax_family": None,
        })

    def test_final_prose_template_and_seed_cannot_change_signatures(self):
        first = {"final_context": context_fixture(), "raw_prompt": "A girl reads.", "cleaned_prompt": "A girl reads."}
        second = copy.deepcopy(first)
        second.update(raw_prompt="A man drives a truck.", cleaned_prompt="At home, a woman is resting.", run_seed=999)
        second["final_context"]["history"].append({"node": "ContextPromptBuilder", "decision": {
            "content_plan": {"semantic_slots": {"subject": "invented", "object": "truck"}, "syntax_family": "invented"},
        }})
        a, b = build_semantic_signatures(first), build_semantic_signatures(second)
        self.assertEqual(a["core"], b["core"])
        self.assertEqual(a["frame"], b["frame"])
        self.assertIsNone(b["axes"]["syntax_family"])

    def test_canonical_aliases_and_profile_identity(self):
        ctx = context_fixture()
        ctx["loc"] = "tea room"
        ctx["subj"] = "a girl with curly hair"
        ctx["extras"].update(source_subj_key=" Student ", character_name="FIONA (NATURE)")
        result = build_semantic_signatures(ctx)
        self.assertEqual(result["core"]["canonical_subject"], "fiona (nature)")
        self.assertEqual(result["core"]["canonical_location"], "tea_room")
        ctx["extras"].pop("character_name")
        self.assertEqual(build_semantic_signatures(ctx)["core"]["canonical_subject"], "student")

    def test_location_fallback_and_unresolved_identity(self):
        ctx = context_fixture()
        ctx["loc"] = "not-a-known-location"
        ctx["extras"]["raw_loc_tag"] = "spaceship"
        self.assertEqual(build_semantic_signatures(ctx)["core"]["canonical_location"], "spaceship_bridge")
        result = build_semantic_signatures({"subj": "never-known-subject", "loc": "never-known-location"})
        self.assertFalse(result["valid"])
        self.assertTrue(all(value is None for value in result["core"].values()))
        self.assertIn("canonical_subject", result["diagnostics"]["missing_fields"]["core"])
        self.assertEqual(semantic_uniqueness([result["core"] if result["valid"] else None])["valid_count"], 0)

    def test_object_and_verb_changes_create_different_core(self):
        baseline = build_semantic_signatures(context_fixture())["core"]
        for field, value in (("main_verb", "writing"), ("primary_object", "phone")):
            ctx = context_fixture()
            ctx["extras"]["action_frame"][field] = value
            with self.subTest(field=field):
                self.assertNotEqual(build_semantic_signatures(ctx)["core"], baseline)

    def test_missing_frame_uses_action_field_and_unique_object_only(self):
        ctx = context_fixture()
        del ctx["extras"]["action_frame"]
        result = build_semantic_signatures(ctx)
        self.assertEqual(result["core"]["action_family_or_main_verb"], "verb:reading")
        self.assertEqual(result["core"]["primary_object_or_object_family"], "book")
        self.assertIsNone(result["frame"]["posture"])
        ctx["action"] = "holding a phone beside a book"
        self.assertIsNone(build_semantic_signatures(ctx)["core"]["primary_object_or_object_family"])

    def test_stale_and_unsupported_frames_cannot_restore_old_slots(self):
        for change in ({"legacy_text": "writing with a pen"}, {"schema_version": "action-frame/v999"}):
            ctx = context_fixture()
            ctx["extras"]["action_frame"].update(change)
            with self.subTest(change=change):
                result = build_semantic_signatures(ctx)
                self.assertIsNone(result["frame"]["progress"])
                self.assertTrue(result["diagnostics"]["rejected_sources"])

    def test_latest_scene_frame_or_slots_can_supply_missing_frame(self):
        for frame_available in (True, False):
            ctx = context_fixture()
            entry = scene_entry(ctx)
            if not frame_available:
                del entry["decision"]["action_frame"]
            ctx["history"].append(entry)
            del ctx["extras"]["action_frame"]
            with self.subTest(frame_available=frame_available):
                result = build_semantic_signatures(ctx)
                self.assertEqual(result["frame"]["progress"], "midway")
                self.assertEqual(result["frame"]["posture"], "sitting")

    def test_refreshed_action_does_not_match_incoming_action(self):
        ctx = context_fixture()
        entry = scene_entry(ctx, action="old incoming action", new_action=ctx["action"], action_updated=True)
        ctx["history"].append(entry)
        del ctx["extras"]["action_frame"]
        self.assertEqual(build_semantic_signatures(ctx)["frame"]["progress"], "midway")

    def test_invalid_latest_history_never_searches_older_matching_entry(self):
        for changes in (
            {"new_action": "a different action"}, {"new_action": ""},
            {"selected_loc": "modern_office"}, {"action_updated": True},
        ):
            ctx = context_fixture()
            ctx["history"].extend([scene_entry(ctx), scene_entry(ctx, **changes)])
            del ctx["extras"]["action_frame"]
            with self.subTest(changes=changes):
                self.assertIsNone(build_semantic_signatures(ctx)["frame"]["progress"])

    def test_stale_history_frame_is_rejected_even_when_decision_action_matches(self):
        ctx = context_fixture()
        entry = scene_entry(ctx)
        entry["decision"]["action_frame"]["legacy_text"] = "previous action"
        del entry["decision"]["slots"]
        ctx["history"].append(entry)
        del ctx["extras"]["action_frame"]
        self.assertIsNone(build_semantic_signatures(ctx)["frame"]["posture"])

    def test_invalid_frame_category_can_fall_back_to_valid_legacy_enum(self):
        ctx = context_fixture()
        ctx["extras"]["action_frame"]["progress"] = "a long descriptive sentence"
        self.assertEqual(build_semantic_signatures(ctx)["frame"]["progress"], "midway")
        ctx["extras"]["action_frame"]["legacy_slots"]["progress_state"] = "also not an enum"
        self.assertIsNone(build_semantic_signatures(ctx)["frame"]["progress"])

    def test_unknown_fields_do_not_become_novel_categories(self):
        ctx = context_fixture()
        ctx["extras"]["action_frame"].update(primary_object="unknown", posture="sittingly", hand_action="unclassified motion")
        result = build_semantic_signatures(ctx)
        self.assertEqual(result["core"]["primary_object_or_object_family"], "book")
        self.assertIsNone(result["frame"]["posture"])
        self.assertIsNone(result["frame"]["hand_action_family"])

    def test_garnish_known_empty_unknown_and_fallback_are_distinct(self):
        ctx = context_fixture()
        ctx["history"][-1]["decision"]["final_tags"] = []
        self.assertEqual(build_semantic_signatures(ctx)["frame"]["garnish_family"], [])
        ctx["history"][-1]["decision"]["final_tags"] = ["unclassified detail"]
        self.assertIsNone(build_semantic_signatures(ctx)["frame"]["garnish_family"])
        ctx["history"][-1]["decision"] = {}
        ctx["extras"]["garnish"] = "clasped hands"
        self.assertIsNone(build_semantic_signatures(ctx)["frame"]["garnish_family"])
        ctx["history"].pop()
        self.assertEqual(build_semantic_signatures(ctx)["frame"]["garnish_family"], ["hands"])

    def test_missing_frame_slots_are_not_reported_as_known_empty(self):
        ctx = context_fixture()
        for field in ("hand_action", "gaze_target"):
            del ctx["extras"]["action_frame"][field]
        result = build_semantic_signatures(ctx)
        self.assertIsNone(result["frame"]["hand_action_family"])
        self.assertIsNone(result["frame"]["gaze_target_family"])
        ctx["extras"]["action_frame"].update(hand_action="", gaze_target="")
        result = build_semantic_signatures(ctx)
        self.assertEqual(result["frame"]["hand_action_family"], [])
        self.assertEqual(result["frame"]["gaze_target_family"], [])

    def test_surface_paraphrase_with_same_frame_keeps_semantic_identity(self):
        first = context_fixture()
        second = copy.deepcopy(first)
        second["action"] = "quietly reading a book near the window"
        second["extras"]["action_frame"]["legacy_text"] = second["action"]
        second["extras"]["action_frame"]["legacy_slots"]["primary_action"] = second["action"]
        second["extras"]["action_frame"]["hand_action"] = "hands carefully gripping the book"
        a, b = build_semantic_signatures(first), build_semantic_signatures(second)
        self.assertEqual(a["core"], b["core"])
        self.assertEqual(a["frame"], b["frame"])

    def test_purpose_fallback_can_describe_a_selected_frame_without_a_verb(self):
        ctx = context_fixture()
        ctx["action"] = ""
        ctx["extras"]["action_frame"] = ActionFrame.from_slots({"purpose": "study"}, legacy_text="").to_dict()
        self.assertEqual(build_semantic_signatures(ctx)["core"]["action_family_or_main_verb"], "purpose:study")

    def test_mood_and_clothing_fallbacks_do_not_use_expanded_prose(self):
        ctx = context_fixture()
        ctx["history"] = []
        ctx["extras"]["raw_mood_key"] = "not-known"
        ctx["meta"]["mood"] = "PEACEFUL_RELAXED"
        ctx["costume"] = "student"
        result = build_semantic_signatures(ctx)
        self.assertEqual(result["frame"]["mood"], "peaceful_relaxed")
        self.assertEqual(result["frame"]["clothing_family"], "school_uniform")
        ctx["meta"]["mood"] = "a very calm feeling"
        self.assertIsNone(build_semantic_signatures(ctx)["frame"]["mood"])

    def test_builder_metadata_requires_prompt_parity_and_syntax_agreement(self):
        record = {"final_context": context_fixture(), "raw_prompt": "A girl reads."}
        decision = {"prompt": record["raw_prompt"], "syntax_family": "family_a", "content_plan": {"syntax_family": "family_a"}}
        result = build_semantic_signatures(record, builder_decision=decision)
        self.assertEqual(result["axes"]["syntax_family"], "family_a")
        self.assertNotIn("syntax_family", result["frame"])
        for changes in ({"prompt": "different"}, {"content_plan": {"syntax_family": "family_b"}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                build_semantic_signatures(record, builder_decision={**decision, **changes})
        with self.assertRaises(ValueError):
            build_semantic_signatures(record, builder_decision={"syntax_family": "family_a"})

    def test_verified_builder_frame_precedes_context_frame(self):
        record = {"final_context": context_fixture(), "raw_prompt": "A girl reads."}
        frame = copy.deepcopy(record["final_context"]["extras"]["action_frame"])
        frame["main_verb"] = "studying"
        result = build_semantic_signatures(record, builder_decision={"prompt": record["raw_prompt"], "action_frame": frame})
        self.assertEqual(result["core"]["action_family_or_main_verb"], "verb:studying")

    def test_deterministic_non_mutating_output_and_typed_context_support(self):
        ctx = context_fixture()
        before = copy.deepcopy(ctx)
        first = build_semantic_signatures(ctx)
        reordered = json.loads(json.dumps(ctx, sort_keys=True))
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(build_semantic_signatures(reordered)))
        self.assertEqual(first, build_semantic_signatures(PromptContext.from_dict(ctx)))
        self.assertEqual(ctx, before)

    def test_invalid_record_context_is_not_silently_accepted(self):
        for value in (None, "{}", {"final_context": None}, {"final_context": []}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_semantic_signatures(value)

    def test_process_hash_seed_does_not_change_projection(self):
        script = """
from assets.test_effective_diversity_signatures import context_fixture
from tools.effective_diversity_signatures import build_semantic_signatures
from tools.workflow_prompt_runner import canonical_json_bytes
ctx = context_fixture()
ctx['history'][-1]['decision']['final_tags'] = list({'quiet gaze', 'soft breath', 'clasped hands'})
print(canonical_json_bytes(build_semantic_signatures(ctx)).decode('utf-8'), end='')
"""
        outputs = [subprocess.check_output([sys.executable, "-c", script], cwd=ROOT,
                    env={**os.environ, "PYTHONHASHSEED": seed}) for seed in ("1", "999")]
        self.assertEqual(outputs[0], outputs[1])

    def test_real_workflow_record_and_builder_replay_integrate_with_metrics(self):
        from core.context_codec import context_from_json
        from pipeline.prompt_orchestrator import build_prompt_from_context
        from tools.workflow_prompt_runner import build_canonical_record

        workflow = json.loads((ROOT / "ComfyUI-workflow-context.json").read_text(encoding="utf-8"))
        record = build_canonical_record(workflow, 0)
        before = copy.deepcopy(record)
        builder_id = record["output_selectors"]["raw_prompt"]["node_id"]
        inputs = next(t["inputs"] for t in record["execution_trace"] if t["node_id"] == builder_id)
        context, prompt = build_prompt_from_context(
            context_from_json(inputs["context_json"], default_seed=inputs["seed"]),
            inputs["template"], inputs["composition_mode"], inputs["seed"],
        )
        self.assertEqual(prompt, record["raw_prompt"])
        projected = build_semantic_signatures(record, builder_decision=context.history[-1].decision)
        self.assertTrue(projected["valid"])
        self.assertIn(projected["axes"]["syntax_family"], {"single-sentence-scene-tail", "two-sentence-scene-tail"})
        self.assertEqual(semantic_uniqueness([projected["core"]])["rate"], 1.0)
        self.assertEqual(record, before)


if __name__ == "__main__":
    unittest.main()
