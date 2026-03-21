import json
import os
import random

if __package__ and "." in __package__:
    from ..core.context_ops import ensure_context, patch_context
else:
    from core.context_ops import ensure_context, patch_context

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def _resolve_json_path(json_path: str) -> str:
    if not json_path or str(json_path).strip() == "":
        json_path = "mood_map.json"
    if not os.path.isabs(json_path):
        json_path = os.path.join(ROOT_DIR, json_path)
    return json_path


def expand_dictionary_value(key, json_path, default_value, seed):
    try:
        seed = int(seed)
    except Exception:
        seed = 0

    json_path = _resolve_json_path(json_path)
    data = {}
    if os.path.exists(json_path) and os.path.isfile(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
        except Exception as exc:
            print(f"\033[93m[MoodExpand] Error loading JSON: {exc}\033[0m")
    else:
        print(f"\033[93m[MoodExpand] File not found: {json_path}\033[0m")

    key_lower = str(key).lower().strip()
    data_lower = {name.lower(): value for name, value in data.items()}
    result = data_lower.get(key_lower, default_value)
    staging_text = ""

    if isinstance(result, dict):
        rng = random.Random(seed)
        desc_list = result.get("description", [])
        if isinstance(desc_list, list) and desc_list:
            description_text = rng.choice(desc_list)
        else:
            description_text = str(result.get("description", default_value))
        staging_list = result.get("staging_tags", [])
        if isinstance(staging_list, list):
            staging_text = ", ".join(staging_list)
        return str(description_text), staging_text

    if isinstance(result, list):
        rng = random.Random(seed)
        result = rng.choice(result) if result else default_value

    return str(result), staging_text


def apply_mood_expansion(context, seed, json_path, default_value):
    ctx = ensure_context(context, default_seed=int(seed))
    key = ctx.meta.mood
    expanded_text, staging_text = expand_dictionary_value(key, json_path, default_value, seed)
    extras = {}
    if staging_text:
        extras["staging_tags"] = staging_text
    ctx = patch_context(ctx, updates={"seed": seed}, meta={"mood": expanded_text}, extras=extras)
    return ctx, expanded_text, staging_text
