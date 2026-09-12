import json
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(ROOT)

from nodes_context import ContextLocationExpander, ContextPromptBuilder, ContextSource


class TestLocationAliasWorkflowCompatibility(unittest.TestCase):
    def setUp(self):
        self.source = ContextSource()
        self.location = ContextLocationExpander()
        self.builder = ContextPromptBuilder()

    def _build_source_context(self, seed, loc):
        payload = {
            "subj": "compat subject",
            "costume": "urban_shopping",
            "loc": loc,
            "action": "walking and checking the surroundings",
            "meta": {"mood": "quiet_focused"},
        }
        return self.source.build_context(json.dumps(payload), seed, "json_only")[0]

    def test_legacy_alias_inputs_still_load_through_context_workflow(self):
        expected = {
            "shopping_mall": "shopping_mall_atrium",
            "spaceship": "spaceship_bridge",
            "workshop": "clockwork_workshop",
        }

        for raw_loc, resolved_loc in expected.items():
            with self.subTest(raw_loc=raw_loc):
                context_json = self._build_source_context(77, raw_loc)
                source_payload = json.loads(context_json)
                self.assertEqual(source_payload["loc"], raw_loc)
                self.assertEqual(source_payload["extras"]["raw_loc_tag"], raw_loc)

                expanded_json = self.location.expand_location_context(77, "detailed", "off", context_json)[0]
                expanded_payload = json.loads(expanded_json)
                self.assertEqual(expanded_payload["loc"], resolved_loc)
                self.assertEqual(expanded_payload["extras"]["raw_loc_tag"], raw_loc)
                self.assertTrue(expanded_payload["extras"]["location_prompt"])

                prompt = self.builder.build_prompt_context("", False, 77, expanded_json)[0]
                self.assertIsInstance(prompt, str)
                self.assertTrue(prompt.strip())

    def test_existing_scene_keys_are_not_downgraded_to_fallback_targets(self):
        for raw_loc in ("rainy_bus_stop", "elegant_dining_room", "suburban_neighborhood"):
            with self.subTest(raw_loc=raw_loc):
                context_json = self._build_source_context(91, raw_loc)
                expanded_json = self.location.expand_location_context(91, "detailed", "off", context_json)[0]
                expanded_payload = json.loads(expanded_json)

                self.assertEqual(expanded_payload["loc"], raw_loc)
                self.assertEqual(expanded_payload["extras"]["raw_loc_tag"], raw_loc)


if __name__ == "__main__":
    unittest.main()
