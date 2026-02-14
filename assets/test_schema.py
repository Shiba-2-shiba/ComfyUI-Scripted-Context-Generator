import unittest
import json
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from core.schema import PromptContext, MetaInfo

class TestSchema(unittest.TestCase):
    
    def test_metainfo_defaults(self):
        meta = MetaInfo()
        self.assertEqual(meta.mood, "")
        self.assertEqual(meta.style, "")
        self.assertEqual(meta.tags, {})

    def test_promptcontext_defaults(self):
        ctx = PromptContext()
        self.assertEqual(ctx.subj, "")
        self.assertEqual(ctx.costume, "")
        self.assertIsInstance(ctx.meta, MetaInfo)

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
        
    def test_json_serialization(self):
        ctx = PromptContext(subj="boy", action="run")
        ctx.meta.mood = "excited"
        
        json_str = ctx.to_json()
        loaded_ctx = PromptContext.from_json(json_str)
        
        self.assertEqual(loaded_ctx.subj, "boy")
        self.assertEqual(loaded_ctx.action, "run")
        self.assertEqual(loaded_ctx.meta.mood, "excited")

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

if __name__ == '__main__':
    unittest.main()
