import json
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from nodes_context import (
    ContextCharacterProfile,
    ContextClothingExpander,
    ContextGarnish,
    ContextInspector,
    ContextLocationExpander,
    ContextMoodExpander,
    ContextPromptBuilder,
    ContextSceneVariator,
    ContextSource,
)


class TestContextNodes(unittest.TestCase):
    def test_downstream_context_input_is_optional_for_layout_stability(self):
        downstream = (
            ContextSceneVariator,
            ContextClothingExpander,
            ContextLocationExpander,
            ContextMoodExpander,
            ContextGarnish,
            ContextPromptBuilder,
            ContextInspector,
        )

        for node_cls in downstream:
            with self.subTest(node=node_cls.__name__):
                specs = node_cls.INPUT_TYPES()
                self.assertNotIn("context_json", specs.get("required", {}))
                self.assertIn("context_json", specs.get("optional", {}))

    def test_context_source_builds_context(self):
        node = ContextSource()
        context_json = node.build_context('{"subj":"girl","costume":"office_lady","loc":"classroom","action":"reading","meta":{"mood":"quiet"}}', 1, 'auto')[0]
        payload = json.loads(context_json)
        self.assertEqual(payload["subj"], "girl")
        self.assertEqual(payload["seed"], 1)

    def test_context_inspector_outputs_strings(self):
        node = ContextInspector()
        pretty, summary = node.inspect_context('{"subj":"girl"}')
        self.assertIn('"subj": "girl"', pretty)
        self.assertIsInstance(summary, str)

    def test_full_context_flow_smoke(self):
        seed = 2026
        source = ContextSource()
        profile = ContextCharacterProfile()
        scene = ContextSceneVariator()
        cloth = ContextClothingExpander()
        loc = ContextLocationExpander()
        mood = ContextMoodExpander()
        garnish = ContextGarnish()
        build = ContextPromptBuilder()

        ctx = source.build_context("{}", seed, "auto")[0]
        ctx = profile.apply_profile("random", "None", seed, ctx)[0]
        ctx = scene.variate_context(seed, "full", ctx)[0]
        ctx = cloth.expand_clothing_context(seed, "random", 0.3, ctx)[0]
        ctx = loc.expand_location_context(seed, "detailed", "auto", ctx)[0]
        ctx = mood.expand_mood_context(seed, "mood_map.json", "", ctx)[0]
        ctx = garnish.garnish_context(seed, 3, False, "random", ctx)[0]
        prompt = build.build_prompt_context("", False, seed, ctx)[0]

        self.assertIsInstance(prompt, str)
        self.assertTrue(prompt.strip())


if __name__ == "__main__":
    unittest.main()
