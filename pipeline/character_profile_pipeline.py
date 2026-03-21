import json
import os
import random

if __package__ and "." in __package__:
    from ..character_service import resolve_character
    from ..vocab.seed_utils import mix_seed
else:
    from character_service import resolve_character
    from vocab.seed_utils import mix_seed


def character_profiles_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
        "vocab",
        "data",
        "character_profiles.json",
    )


def load_character_profiles(data_path=None):
    data_path = data_path or character_profiles_path()
    if not os.path.exists(data_path):
        print(f"\033[93m[CharacterProfile] Warning: {data_path} not found.\033[0m")
        return {}

    try:
        with open(data_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as error:
        print(f"\033[91m[CharacterProfile] Error loading profiles: {error}\033[0m")
        return {}

    return data.get("characters", {})


def list_character_profile_names(profiles=None, data_path=None):
    profile_map = profiles if profiles is not None else load_character_profiles(data_path)
    names = list(profile_map.keys())
    return names or ["None"]


def character_profile_input_types(profiles=None, data_path=None):
    names = list_character_profile_names(profiles=profiles, data_path=data_path)
    return {
        "required": {
            "mode": (["random", "fixed"], {"default": "random"}),
            "character_name": (names, {"default": names[0]}),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
        }
    }


def _select_character_profile_name(profiles, mode, character_name, seed):
    if not profiles:
        return None

    rng = random.Random(mix_seed(int(seed), "character"))
    selected_name = character_name
    if mode == "random":
        selected_name = rng.choice(list(profiles.keys()))

    if selected_name not in profiles:
        print(
            f"\033[93m[CharacterProfile] Warning: Character '{selected_name}' not found. "
            "Picking random.\033[0m"
        )
        selected_name = rng.choice(list(profiles.keys()))

    return selected_name


def build_character_profile(seed, mode, character_name, profiles):
    selected_name = _select_character_profile_name(profiles, mode, character_name, seed)
    if not selected_name:
        return {
            "selected_name": None,
            "character_id": "",
            "compatibility_key": "",
            "compatibility_tags": [],
            "default_costume": "",
            "subj_prompt": "",
            "hair_color": "",
            "eye_color": "",
            "personality": "",
            "color_palette_str": "",
            "color_palette": [],
            "warnings": [],
        }

    resolved = resolve_character(selected_name, character_name=selected_name)
    hair_color = resolved.get("hair_color", "")
    hair_style = resolved.get("hair_style", "")
    eye_color = resolved.get("eye_color", "")
    personality = resolved.get("personality", "neutral")

    hair_desc = ""
    if hair_style and hair_color:
        hair_desc = f"{hair_style}, {hair_color} hair"
    elif hair_style:
        hair_desc = hair_style
    elif hair_color:
        hair_desc = f"{hair_color} hair"

    eye_desc = f"{eye_color} eyes" if eye_color else ""
    subj_prompt = "A solo girl"
    if hair_desc or eye_desc:
        subj_prompt += " with "
        if hair_desc and eye_desc:
            subj_prompt += f"{hair_desc} and {eye_desc}"
        elif hair_desc:
            subj_prompt += hair_desc
        else:
            subj_prompt += eye_desc

    color_palette = list(resolved.get("palette", []))
    return {
        "selected_name": selected_name,
        "character_id": str(resolved.get("character_id", "")),
        "compatibility_key": str(resolved.get("compatibility_key", "")),
        "compatibility_tags": list(resolved.get("compatibility_tags", [])),
        "default_costume": str(resolved.get("default_costume", "")),
        "subj_prompt": subj_prompt,
        "hair_color": hair_color,
        "eye_color": eye_color,
        "personality": personality,
        "color_palette_str": ", ".join(color_palette),
        "color_palette": color_palette,
        "warnings": list(resolved.get("warnings", [])),
    }
