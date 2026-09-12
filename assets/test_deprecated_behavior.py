import json
import os
import sys
import unittest


sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from core.context_ops import patch_context
from core.schema import LEGACY_STYLE_NOTE
from nodes_context import ContextGarnish, ContextInspector
from pipeline import content_pipeline
from pipeline.clothing_builder import apply_clothing_expansion as direct_apply_clothing_expansion
from pipeline.clothing_builder import expand_clothing_prompt as direct_expand_clothing_prompt
from pipeline.context_pipeline import apply_garnish
from pipeline.location_builder import apply_location_expansion as direct_apply_location_expansion
from pipeline.location_builder import expand_location_prompt as direct_expand_location_prompt
from pipeline.mood_builder import apply_mood_expansion as direct_apply_mood_expansion
from pipeline.mood_builder import expand_dictionary_value as direct_expand_dictionary_value
from pipeline.prompt_orchestrator import _derive_template_roles as direct_derive_template_roles
from pipeline.prompt_orchestrator import _template_entries as direct_template_entries
from pipeline.prompt_orchestrator import build_prompt_from_context
from pipeline.prompt_orchestrator import build_prompt_from_context as direct_build_prompt_from_context
from pipeline.prompt_orchestrator import build_prompt_text as direct_build_prompt_text


class TestDeprecatedBehavior(unittest.TestCase):
    def test_content_pipeline_facade_reexports_expected_compatibility_surface(self):
        expected = {
            "apply_clothing_expansion": direct_apply_clothing_expansion,
            "expand_clothing_prompt": direct_expand_clothing_prompt,
            "apply_location_expansion": direct_apply_location_expansion,
            "expand_location_prompt": direct_expand_location_prompt,
            "apply_mood_expansion": direct_apply_mood_expansion,
            "expand_dictionary_value": direct_expand_dictionary_value,
            "_derive_template_roles": direct_derive_template_roles,
            "_template_entries": direct_template_entries,
            "build_prompt_from_context": direct_build_prompt_from_context,
            "build_prompt_text": direct_build_prompt_text,
        }

        self.assertEqual(set(content_pipeline.__all__), set(expected))
        for name, direct_callable in expected.items():
            with self.subTest(name=name):
                self.assertIs(getattr(content_pipeline, name), direct_callable)

    def test_meta_style_is_legacy_read_only_and_ignored_by_prompt_builder(self):
        ctx = patch_context(
            {},
            updates={
                "subj": "A solo girl",
                "costume": "office_lady",
                "loc": "classroom",
                "action": "reading",
                "seed": 13,
            },
            meta={"mood": "quiet", "style": "photo"},
            extras={
                "clothing_prompt": "white blouse and navy skirt",
                "location_prompt": "sunlit classroom",
                "garnish": "soft smile",
            },
        )
        inspector = ContextInspector()
        _pretty, summary = inspector.inspect_context(ctx.to_json())
        _updated, prompt = build_prompt_from_context(ctx, "", False, 13)

        self.assertIn(LEGACY_STYLE_NOTE, ctx.notes)
        self.assertIn("style(legacy-read-only)=photo", summary)
        self.assertIn("notes=1", summary)
        self.assertIn("include_camera=no-op(deprecated)", summary)
        self.assertNotIn("photo", prompt.lower())

    def test_include_camera_is_no_op_but_warns(self):
        ctx = patch_context(
            {},
            updates={
                "action": "walking through a hallway",
                "loc": "school hallway",
                "costume": "school_uniform",
                "seed": 111,
            },
            meta={"mood": "quiet", "tags": {"time": "morning"}},
            extras={"personality": "shy"},
        )

        updated_false, garnish_false, _debug_false = apply_garnish(ctx, 111, 3, False, personality="shy")
        updated_true, garnish_true, _debug_true = apply_garnish(ctx, 111, 3, True, personality="shy")

        self.assertEqual(garnish_false, garnish_true)
        self.assertNotIn("include_camera is deprecated", " ".join(updated_false.warnings))
        self.assertIn(
            "include_camera is deprecated and ignored by semantic-only garnish generation",
            updated_true.warnings,
        )

    def test_context_garnish_node_hides_deprecated_widget_but_accepts_legacy_argument(self):
        specs = ContextGarnish.INPUT_TYPES()
        self.assertNotIn("include_camera", specs["required"])

        node = ContextGarnish()
        payload = patch_context(
            {},
            updates={"action": "walking through a hallway", "loc": "school hallway", "costume": "school_uniform", "seed": 11},
            meta={"mood": "quiet"},
        ).to_json()
        updated_json = node.garnish_context(11, 3, "random", payload, include_camera=True)[0]
        updated = json.loads(updated_json)

        self.assertIn(
            "include_camera is deprecated and ignored by semantic-only garnish generation",
            updated["warnings"],
        )


if __name__ == "__main__":
    unittest.main()
