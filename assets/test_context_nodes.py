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
        ctx = scene.variate_context(ctx, seed, "full")[0]
        ctx = cloth.expand_clothing_context(ctx, seed, "random", 0.3)[0]
        ctx = loc.expand_location_context(ctx, seed, "detailed", "auto")[0]
        ctx = mood.expand_mood_context(ctx, seed, "mood_map.json", "")[0]
        ctx = garnish.garnish_context(ctx, seed, 3, False, "random")[0]
        prompt = build.build_prompt_context(ctx, "", False, seed)[0]

        self.assertIsInstance(prompt, str)
        self.assertTrue(prompt.strip())


if __name__ == "__main__":
    unittest.main()
