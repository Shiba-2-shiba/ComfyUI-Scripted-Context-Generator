import json
import os
import random

try:
    from .core.context_codec import context_from_json, context_to_json
    from .core.context_ops import add_warning, patch_context
    from .pipeline.character_profile_pipeline import (
        build_character_profile,
        character_profile_input_types,
        load_character_profiles,
    )
    from .pipeline.context_pipeline import apply_garnish, apply_scene_variation
    from .pipeline.clothing_builder import apply_clothing_expansion
    from .pipeline.location_builder import apply_location_expansion
    from .pipeline.mood_builder import apply_mood_expansion
    from .pipeline.prompt_orchestrator import build_prompt_from_context
    from .pipeline.source_pipeline import load_prompt_source_payload
except ImportError:
    from core.context_codec import context_from_json, context_to_json
    from core.context_ops import add_warning, patch_context
    from pipeline.character_profile_pipeline import (
        build_character_profile,
        character_profile_input_types,
        load_character_profiles,
    )
    from pipeline.context_pipeline import apply_garnish, apply_scene_variation
    from pipeline.clothing_builder import apply_clothing_expansion
    from pipeline.location_builder import apply_location_expansion
    from pipeline.mood_builder import apply_mood_expansion
    from pipeline.prompt_orchestrator import build_prompt_from_context
    from pipeline.source_pipeline import load_prompt_source_payload


ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
CONTEXT_CATEGORY = "prompt_builder/context"


def _seed_input():
    return ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True})


def _context_json_input(default=""):
    return ("STRING", {"multiline": True, "default": default})


def _context_stage_input_types(extra_required, context_optional=True):
    required = {
        "seed": _seed_input(),
    }
    required.update(extra_required)
    if context_optional:
        return {
            "required": required,
            "optional": {
                "context_json": _context_json_input(),
            },
        }
    required["context_json"] = _context_json_input()
    return {"required": required}


def _run_context_stage(context_json, seed, apply_fn, *args, **kwargs):
    ctx = context_from_json(context_json, default_seed=int(seed))
    result = apply_fn(ctx, int(seed), *args, **kwargs)
    updated_ctx = result[0] if isinstance(result, tuple) else result
    return (context_to_json(updated_ctx),)


class ContextSource:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "json_string": ("STRING", {"multiline": True, "default": "{}"}),
                "seed": _seed_input(),
                "source_mode": (["auto", "json_only", "prompts_only"], {"default": "auto"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("context_json",)
    FUNCTION = "build_context"
    CATEGORY = CONTEXT_CATEGORY

    def build_context(self, json_string, seed, source_mode="auto"):
        payload = load_prompt_source_payload(
            json_string,
            int(seed),
            source_mode=source_mode,
            root_dir=ROOT_DIR,
        )
        ctx = patch_context(payload, updates={"seed": seed})
        if not ctx.extras.get("source_subj_key") and ctx.subj:
            ctx.extras["source_subj_key"] = ctx.subj
        if not ctx.extras.get("raw_costume_key") and ctx.costume:
            ctx.extras["raw_costume_key"] = ctx.costume
        if not ctx.extras.get("raw_loc_tag") and ctx.loc:
            ctx.extras["raw_loc_tag"] = ctx.loc
        return (context_to_json(ctx),)


class ContextCharacterProfile:
    def __init__(self):
        self.data_path = os.path.join(ROOT_DIR, "vocab", "data", "character_profiles.json")
        self.profiles = load_character_profiles(self.data_path)

    @classmethod
    def INPUT_TYPES(s):
        base = character_profile_input_types(
            data_path=os.path.join(ROOT_DIR, "vocab", "data", "character_profiles.json")
        )
        return {
            "required": base["required"],
            "optional": {
                "context_json": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("context_json",)
    FUNCTION = "apply_profile"
    CATEGORY = CONTEXT_CATEGORY

    def apply_profile(self, mode, character_name, seed, context_json=""):
        ctx = context_from_json(context_json, default_seed=int(seed))
        if not self.profiles:
            return (context_to_json(ctx),)

        result = build_character_profile(int(seed), mode, character_name, self.profiles)
        extras = {
            "character_name": result["selected_name"] or "",
            "character_id": result.get("character_id", ""),
            "hair_color": result["hair_color"],
            "eye_color": result["eye_color"],
            "personality": result["personality"],
            "character_palette_str": result["color_palette_str"],
            "color_palette": result["color_palette"],
        }
        if not ctx.extras.get("source_subj_key") and result.get("compatibility_key"):
            extras["source_subj_key"] = result["compatibility_key"]
        if not ctx.extras.get("raw_costume_key") and result.get("default_costume"):
            extras["raw_costume_key"] = result["default_costume"]
        ctx = patch_context(
            ctx,
            updates={"subj": result["subj_prompt"], "seed": seed},
            extras=extras,
        )
        for warning in result.get("warnings", []):
            ctx = add_warning(ctx, warning)
        return (context_to_json(ctx),)


class ContextSceneVariator:
    @classmethod
    def INPUT_TYPES(s):
        return _context_stage_input_types({
            "variation_mode": (["original", "genre_only", "full"], {"default": "full"}),
        })

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("context_json",)
    FUNCTION = "variate_context"
    CATEGORY = CONTEXT_CATEGORY

    def variate_context(self, seed, variation_mode, context_json=""):
        return _run_context_stage(context_json, seed, apply_scene_variation, variation_mode)


class ContextClothingExpander:
    @classmethod
    def INPUT_TYPES(s):
        return _context_stage_input_types({
            "outfit_mode": (["random", "dresses", "separates", "outerwear_only", "no_outerwear"], {"default": "random"}),
            "outerwear_chance": ("FLOAT", {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.05}),
        })

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("context_json",)
    FUNCTION = "expand_clothing_context"
    CATEGORY = CONTEXT_CATEGORY

    def expand_clothing_context(self, seed, outfit_mode, outerwear_chance, context_json=""):
        return _run_context_stage(context_json, seed, apply_clothing_expansion, outfit_mode, outerwear_chance)


class ContextLocationExpander:
    @classmethod
    def INPUT_TYPES(s):
        return _context_stage_input_types({
            "mode": (["detailed", "simple"], {"default": "detailed"}),
            "lighting_mode": (["auto", "off"], {"default": "off"}),
        })

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("context_json",)
    FUNCTION = "expand_location_context"
    CATEGORY = CONTEXT_CATEGORY

    def expand_location_context(self, seed, mode, lighting_mode="auto", context_json=""):
        return _run_context_stage(context_json, seed, apply_location_expansion, mode, lighting_mode)


class ContextMoodExpander:
    @classmethod
    def INPUT_TYPES(s):
        return _context_stage_input_types({
            "json_path": ("STRING", {"multiline": False, "default": "mood_map.json"}),
            "default_value": ("STRING", {"multiline": False, "default": ""}),
        })

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("context_json",)
    FUNCTION = "expand_mood_context"
    CATEGORY = CONTEXT_CATEGORY

    def expand_mood_context(self, seed, json_path, default_value, context_json=""):
        return _run_context_stage(context_json, seed, apply_mood_expansion, json_path, default_value)


class ContextGarnish:
    @classmethod
    def INPUT_TYPES(s):
        return _context_stage_input_types({
            "max_items": ("INT", {"default": 3, "min": 1, "max": 10}),
            "emotion_nuance": ("STRING", {
                "default": "random",
                "choices": ["random", "tense", "absorbed", "relieved", "awkward", "content", "bored"]
            }),
        })

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("context_json",)
    FUNCTION = "garnish_context"
    CATEGORY = CONTEXT_CATEGORY

    def garnish_context(self, seed, max_items, emotion_nuance="random", context_json="", include_camera=False):
        # `include_camera` stays as a hidden legacy argument so old workflows can
        # still deserialize, but the public node UI no longer advertises it.
        return _run_context_stage(
            context_json,
            seed,
            apply_garnish,
            int(max_items),
            bool(include_camera),
            emotion_nuance=emotion_nuance,
        )


class ContextPromptBuilder:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "template": ("STRING", {"multiline": True, "default": ""}),
                "composition_mode": ("BOOLEAN", {"default": False}),
                "seed": _seed_input(),
            },
            "optional": {
                "context_json": _context_json_input(),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt_text",)
    FUNCTION = "build_prompt_context"
    CATEGORY = CONTEXT_CATEGORY

    def build_prompt_context(self, template, composition_mode, seed, context_json=""):
        ctx = context_from_json(context_json, default_seed=int(seed))
        _updated_ctx, prompt = build_prompt_from_context(ctx, template, composition_mode, int(seed))
        return (prompt,)


class ContextInspector:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "optional": {
                "context_json": _context_json_input(),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("pretty_json", "summary_text")
    FUNCTION = "inspect_context"
    CATEGORY = CONTEXT_CATEGORY

    def inspect_context(self, context_json=""):
        ctx = context_from_json(context_json)
        pretty = json.dumps(ctx.to_dict(), ensure_ascii=False, indent=2)
        summary = "; ".join([
            f"subj={ctx.subj or '-'}",
            f"costume={ctx.costume or '-'}",
            f"loc={ctx.loc or '-'}",
            f"action={ctx.action or '-'}",
            f"mood={ctx.meta.mood or '-'}",
            f"style(legacy-read-only)={ctx.meta.style or '-'}",
            "include_camera=no-op(deprecated)",
            f"notes={len(ctx.notes)}",
            f"warnings={len(ctx.warnings)}",
            f"history={len(ctx.history)}",
        ])
        return (pretty, summary)


NODE_CLASS_MAPPINGS = {
    "ContextSource": ContextSource,
    "ContextCharacterProfile": ContextCharacterProfile,
    "ContextSceneVariator": ContextSceneVariator,
    "ContextClothingExpander": ContextClothingExpander,
    "ContextLocationExpander": ContextLocationExpander,
    "ContextMoodExpander": ContextMoodExpander,
    "ContextGarnish": ContextGarnish,
    "ContextPromptBuilder": ContextPromptBuilder,
    "ContextInspector": ContextInspector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ContextSource": "Context Source",
    "ContextCharacterProfile": "Context Character Profile",
    "ContextSceneVariator": "Context Scene Variator",
    "ContextClothingExpander": "Context Clothing Expander",
    "ContextLocationExpander": "Context Location Expander",
    "ContextMoodExpander": "Context Mood Expander",
    "ContextGarnish": "Context Garnish",
    "ContextPromptBuilder": "Context Prompt Builder",
    "ContextInspector": "Context Inspector",
}
