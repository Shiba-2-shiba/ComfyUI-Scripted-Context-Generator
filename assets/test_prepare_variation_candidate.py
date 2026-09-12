import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import build_compatibility_review as compatibility
from tools import materialize_variation_candidate_snapshot as materializer
from tools import prepare_variation_candidate as preparation
from tools.workflow_prompt_runner import WorkflowValidationError


class CandidateCompatibilitySeedTests(unittest.TestCase):
    def test_bound_baseline_prompt_only_pair_survives_cohort_replacement(self):
        scope = {
            "variation_subjects": ["hacker"], "variation_locations": ["surveillance_room"],
            "compatibility_review_generation": {"existing_prompt_rows": [
                {"subj": "hacker", "loc": "surveillance_room", "costume": "workwear"}
            ]},
        }
        scene = {"characters": {"hacker": {"tags": [], "default_costume": "workwear"}}}
        with patch.object(compatibility, "load_scene_compatibility", return_value=scene), \
             patch.object(compatibility, "resolve_location_alias_map", return_value={}), \
             patch.object(compatibility, "_load_prompt_rows", return_value=[]):
            rows = compatibility.build_generated_rows(scope)
        self.assertEqual([(row["subj"], row["canonical_loc"]) for row in rows], [("hacker", "surveillance_room")])
        self.assertEqual(rows[0]["source"], "existing")

    def test_live_cohort_metadata_wins_and_seed_still_obeys_exclusions(self):
        scope = {
            "variation_subjects": ["hacker"], "variation_locations": ["surveillance_room"],
            "compatibility_review_generation": {"existing_prompt_rows": [
                {"subj": "hacker", "loc": "surveillance_room", "costume": "old"}
            ]},
        }
        scene = {"characters": {"hacker": {"tags": [], "default_costume": "workwear"}}}
        with patch.object(compatibility, "load_scene_compatibility", return_value=scene), \
             patch.object(compatibility, "resolve_location_alias_map", return_value={}), \
             patch.object(compatibility, "_load_prompt_rows", return_value=[
                 {"subj": "hacker", "loc": "surveillance_room", "costume": "new"}
             ]):
            self.assertEqual(compatibility.build_generated_rows(scope)[0]["costume"], "new")
            scope["compatibility_review_generation"]["excluded_pairs"] = [
                {"subj": "hacker", "canonical_loc": "surveillance_room"}
            ]
            self.assertEqual(compatibility.build_generated_rows(scope), [])

    def test_materializer_captures_only_original_prompt_compatibility_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, value in {
                "vocab/data/scene_compatibility.json": {}, "vocab/data/background_packs.json": {},
                "vocab/data/location_axis_profiles.json": {}, "vocab/source/action_pools/_manifest.json": {},
                "vocab/data/variation_scope.json": {"variation_subjects": [], "variation_locations": []},
            }.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding="utf-8")
            (root / "prompts.jsonl").write_text(json.dumps({"subj": "hacker", "loc": "room", "costume": "coat", "action": "working"}) + "\n", encoding="utf-8")
            materializer._materialize_candidate_data(root, {"subjects": [], "locations": []})
            scope = json.loads((root / "vocab/data/variation_scope.json").read_text())
            self.assertEqual(scope["compatibility_review_generation"]["existing_prompt_rows"], [
                {"subj": "hacker", "loc": "room", "costume": "coat"}
            ])


class CandidatePreparationTests(unittest.TestCase):
    def test_existing_experiment_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(preparation, "ROOT", Path(directory)):
            destination = Path(directory) / "docs/variation_expansion/experiments/existing"
            destination.mkdir(parents=True)
            sentinel = destination / "candidate-iteration.json"
            sentinel.write_text("untouched", encoding="utf-8")
            with self.assertRaises(WorkflowValidationError) as raised:
                preparation.prepare_candidate(iteration=sentinel, destination=destination,
                                              experiment_id="should-not-overwrite")
            self.assertEqual(sentinel.read_text(), "untouched")
        self.assertEqual(raised.exception.code, "candidate_preparation_exists")

    def test_destination_cannot_escape_experiment_tree(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(preparation, "ROOT", Path(directory)):
            with self.assertRaises(WorkflowValidationError) as raised:
                preparation.prepare_candidate(iteration=Path(directory) / "missing.json",
                                              destination=Path(directory) / "elsewhere", experiment_id="bad")
            self.assertEqual(raised.exception.code, "candidate_preparation_destination")


if __name__ == "__main__":
    unittest.main()
