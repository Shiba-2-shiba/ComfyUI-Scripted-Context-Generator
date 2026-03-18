import unittest
import json
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from core.schema import CONTEXT_VERSION, DebugInfo, PromptContext, MetaInfo, default_extras

class TestSchema(unittest.TestCase):
    
    def test_metainfo_defaults(self):
        meta = MetaInfo()
        self.assertEqual(meta.mood, "")
        self.assertEqual(meta.style, "")
        self.assertEqual(meta.tags, {})

    def test_promptcontext_defaults(self):
        ctx = PromptContext()
        self.assertEqual(ctx.context_version, CONTEXT_VERSION)
        self.assertEqual(ctx.seed, 0)
        self.assertEqual(ctx.subj, "")
        self.assertEqual(ctx.costume, "")
        self.assertIsInstance(ctx.meta, MetaInfo)
        self.assertEqual(ctx.warnings, [])
        self.assertEqual(ctx.extras["garnish"], "")

    def test_from_dict_lenient(self):
        data = {
            "subj": "girl",
            "meta": {
                "mood": "happy"
            },
            "unknown_field": "ignore_me"
        }
        ctx = PromptContext.from_dict(data)
        self.assertEqual(ctx.subj, "girl")
        self.assertEqual(ctx.meta.mood, "happy")
        self.assertEqual(ctx.costume, "") # Default
        self.assertEqual(ctx.context_version, CONTEXT_VERSION)
        self.assertEqual(ctx.extras["location_prompt"], "")

    def test_json_serialization(self):
        ctx = PromptContext(subj="boy", action="run")
        ctx.meta.mood = "excited"
        ctx.seed = 11
        ctx.warnings.append("test-warning")
        
        json_str = ctx.to_json()
        loaded_ctx = PromptContext.from_json(json_str)
        
        self.assertEqual(loaded_ctx.context_version, CONTEXT_VERSION)
        self.assertEqual(loaded_ctx.seed, 11)
        self.assertEqual(loaded_ctx.subj, "boy")
        self.assertEqual(loaded_ctx.action, "run")
        self.assertEqual(loaded_ctx.meta.mood, "excited")
        self.assertEqual(loaded_ctx.warnings, ["test-warning"])

    def test_nested_tags(self):
        data = {
            "meta": {
                "tags": {
                    "place": "school",
                    "time": "day"
                }
            }
        }
        ctx = PromptContext.from_dict(data)
        self.assertEqual(ctx.meta.tags["place"], "school")

    def test_extras_defaults_are_merged(self):
        ctx = PromptContext.from_dict({
            "extras": {
                "garnish": "soft smile",
                "custom_key": "keep_me",
            }
        })
        self.assertEqual(ctx.extras["garnish"], "soft smile")
        self.assertEqual(ctx.extras["raw_loc_tag"], "")
        self.assertEqual(ctx.extras["custom_key"], "keep_me")

    def test_invalid_json_returns_warning(self):
        ctx = PromptContext.from_json("{not-json")
        self.assertEqual(ctx.subj, "")
        self.assertTrue(ctx.warnings)

    def test_debuginfo_from_dict(self):
        info = DebugInfo.from_dict({
            "node": "ContextSceneVariator",
            "seed": "9",
            "decision": {"mode": "full"},
            "warnings": [1, "warn"],
        })
        self.assertEqual(info.node, "ContextSceneVariator")
        self.assertEqual(info.seed, 9)
        self.assertEqual(info.decision["mode"], "full")
        self.assertEqual(info.warnings, ["1", "warn"])

    def test_default_extras_shape(self):
        extras = default_extras()
        self.assertEqual(extras["character_name"], "")
        self.assertEqual(extras["color_palette"], [])

if __name__ == '__main__':
    unittest.main()
