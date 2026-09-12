"""Structural/safety metadata must be valid before v2 selection is connected."""

import copy
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import asset_validator  # noqa: E402
from vocab.syntax_families import validate_syntax_family_catalog  # noqa: E402


class TestSyntaxFamilyCatalog(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((ROOT / "vocab/data/natural_language_realizer_v2.json").read_text(encoding="utf-8"))

    def family(self, key, catalog=None):
        return next(item for item in (self.catalog if catalog is None else catalog)["families"] if item["key"] == key)

    def test_six_required_families_are_valid_and_have_no_prose_templates(self):
        self.assertEqual(validate_syntax_family_catalog(self.catalog), [])
        self.assertEqual({item["key"] for item in self.catalog["families"]}, {
            "subject_action_scene", "subject_action__scene_tail", "scene_lead_subject_action",
            "action_lead_subject_scene", "subject_scene_action", "subject_action_scene_insert",
        })
        self.assertTrue(all("text" not in item for item in self.catalog["families"]))

    def test_baseline_is_unconditional_and_other_fallbacks_are_direct(self):
        base = self.family("subject_action_scene")
        self.assertEqual(base["roles"], ["*"])
        self.assertEqual(base["allowed_action_surfaces"], ["*"])
        self.assertIsNone(base["fallback_family"])
        for field in ("required_slots", "requires", "forbids", "avoid_action_surfaces"):
            self.assertEqual(base[field], [])
        for item in self.catalog["families"][1:]:
            self.assertEqual(item["fallback_family"], "subject_action_scene")

    def test_action_lead_requires_actual_gerund_and_same_subject(self):
        item = self.family("action_lead_subject_scene")
        self.assertEqual(item["allowed_action_surfaces"], ["gerund"])
        self.assertIn("same_subject_attachment_safe", item["requires"])
        self.assertIn("independent_action_subject", item["forbids"])
        self.assertTrue({"fragment", "clause", "framed"} <= set(item["avoid_action_surfaces"]))

    def test_invalid_root_and_family_shapes_are_rejected_without_crashing(self):
        for payload in (None, [], "catalog", {}, {**self.catalog, "families": None},
                        {**self.catalog, "families": [None]}, {**self.catalog, "schema_version": "future"}):
            with self.subTest(payload=payload):
                self.assertTrue(validate_syntax_family_catalog(payload))

    def test_missing_duplicate_and_unknown_keys_are_rejected(self):
        for mutation in ("missing", "duplicate", "unknown", "unhashable"):
            data = copy.deepcopy(self.catalog)
            if mutation == "missing":
                data["families"].pop()
            elif mutation == "duplicate":
                data["families"].append(copy.deepcopy(data["families"][0]))
            else:
                data["families"][0]["key"] = "unimplemented_family" if mutation == "unknown" else []
            with self.subTest(mutation=mutation):
                self.assertTrue(validate_syntax_family_catalog(data))

    def test_unknown_fields_do_not_smuggle_semantic_text_or_typos(self):
        for mutation in ("root", "family", "missing_field"):
            data = copy.deepcopy(self.catalog)
            if mutation == "root":
                data["templates"] = ["cinematic lighting"]
            elif mutation == "family":
                data["families"][0]["text"] = "with a new object"
            else:
                del data["families"][0]["roles"]
            with self.subTest(mutation=mutation):
                self.assertTrue(validate_syntax_family_catalog(data))

    def test_unknown_duplicate_or_wrong_type_list_members_are_rejected(self):
        for field, value in (("roles", ["camera"]), ("roles", ["focused", "focused"]),
                             ("required_slots", ["action"]), ("requires", ["unknown_condition"]),
                             ("forbids", ["unknown_condition"]), ("allowed_action_surfaces", ["fragment_subject_action"]),
                             ("allowed_action_surfaces", "gerund"), ("avoid_action_surfaces", [[]])):
            data = copy.deepcopy(self.catalog)
            data["families"][1][field] = value
            with self.subTest(field=field, value=value):
                self.assertTrue(validate_syntax_family_catalog(data))

    def test_baseline_cannot_be_restricted_or_have_a_fallback_cycle(self):
        for field, value in (("required_slots", ["subject"]), ("roles", ["focused"]),
                             ("requires", ["scene_lead_safe"]), ("forbids", ["independent_action_subject"]),
                             ("avoid_action_surfaces", ["fragment"]), ("allowed_action_surfaces", ["clause"]),
                             ("fallback_family", "subject_action_scene")):
            data = copy.deepcopy(self.catalog)
            self.family("subject_action_scene", data)[field] = value
            with self.subTest(field=field):
                self.assertTrue(validate_syntax_family_catalog(data))

    def test_fallback_target_must_be_baseline_not_missing_or_chained(self):
        for value in (None, "missing", "scene_lead_subject_action"):
            data = copy.deepcopy(self.catalog)
            data["families"][1]["fallback_family"] = value
            with self.subTest(value=value):
                self.assertTrue(validate_syntax_family_catalog(data))

    def test_conditional_family_cannot_drop_required_safety_facts(self):
        for key in ("subject_action__scene_tail", "scene_lead_subject_action", "action_lead_subject_scene",
                    "subject_scene_action", "subject_action_scene_insert"):
            for field in ("required_slots", "requires", "forbids"):
                data = copy.deepcopy(self.catalog)
                self.family(key, data)[field] = []
                with self.subTest(key=key, field=field):
                    self.assertTrue(validate_syntax_family_catalog(data))

    def test_incompatible_surface_and_contradictory_constraints_are_rejected(self):
        for field, value in (("allowed_action_surfaces", ["gerund", "framed"]),
                             ("avoid_action_surfaces", ["gerund"]),
                             ("forbids", ["same_subject_attachment_safe", "independent_action_subject"]),
                             ("allowed_action_surfaces", ["*"])):
            data = copy.deepcopy(self.catalog)
            self.family("action_lead_subject_scene", data)[field] = value
            with self.subTest(field=field, value=value):
                self.assertTrue(validate_syntax_family_catalog(data))

    def test_bad_sentence_counts_orders_and_weights_are_rejected(self):
        for field, value in (("sentence_count", True), ("sentence_count", 3), ("sentence_count", 1.0),
                             ("clause_order", ["subject", "subject", "scene"]), ("clause_order", ["action", "scene", "subject"]),
                             ("weight", True), ("weight", 0), ("weight", -1), ("weight", "1"),
                             ("weight", math.nan), ("weight", math.inf)):
            data = copy.deepcopy(self.catalog)
            self.family("scene_lead_subject_action", data)[field] = value
            with self.subTest(field=field, value=value):
                self.assertTrue(validate_syntax_family_catalog(data))

    def test_validator_is_deterministic_and_does_not_modify_input(self):
        data = copy.deepcopy(self.catalog)
        data["families"][0]["roles"] = ["unknown"]
        before = copy.deepcopy(data)
        self.assertEqual(validate_syntax_family_catalog(data), validate_syntax_family_catalog(data))
        self.assertEqual(data, before)

    def test_asset_validation_checks_catalog(self):
        original = asset_validator._read_json_asset
        malformed = copy.deepcopy(self.catalog)
        malformed["families"][0]["weight"] = 0

        def load(name):
            return malformed if name == "natural_language_realizer_v2.json" else original(name)

        with patch.object(asset_validator, "_read_json_asset", side_effect=load):
            self.assertTrue(any("natural_language_realizer_v2.json" in issue for issue in asset_validator.validate_assets()))


if __name__ == "__main__":
    unittest.main()
