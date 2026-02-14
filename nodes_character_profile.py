import json
import os
import json
import os
import random

try:
    from .vocab.seed_utils import mix_seed
except ImportError:
    from vocab.seed_utils import mix_seed

class CharacterProfileNode:
    def __init__(self):
        self.data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "vocab", "data", "character_profiles.json")
        self.profiles = self._load_profiles()

    def _load_profiles(self):
        if not os.path.exists(self.data_path):
            print(f"\033[93m[CharacterProfile] Warning: {self.data_path} not found.\033[0m")
            return {}
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("characters", {})
        except Exception as e:
            print(f"\033[91m[CharacterProfile] Error loading profiles: {e}\033[0m")
            return {}

    @classmethod
    def INPUT_TYPES(s):
        # Load character names for the dropdown
        data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "vocab", "data", "character_profiles.json")
        character_names = []
        if os.path.exists(data_path):
            try:
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    character_names = list(data.get("characters", {}).keys())
            except Exception as e:
                print(f"\033[91m[CharacterProfile] Error loading profiles for dropdown: {e}\033[0m")
        
        if not character_names:
            character_names = ["None"]

        return {
            "required": {
                "mode": (["random", "fixed"], {"default": "random"}),
                "character_name": (character_names, {"default": character_names[0]}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("subj_prompt", "hair_color", "eye_color", "personality", "color_palette_str")
    FUNCTION = "get_profile"
    CATEGORY = "prompt_builder"

    def get_profile(self, mode, character_name, seed):
        if not self.profiles:
            return ("", "", "", "", "")

        rng = random.Random(mix_seed(seed, "character"))
        
        selected_name = character_name
        
        if mode == "random":
            selected_name = rng.choice(list(self.profiles.keys()))
        
        # Fallback if specific name not found
        if selected_name not in self.profiles:
            # If fixed mode but name invalid, warn and pick random? Or return empty?
            # Let's pick random to avoid breakage, but print warning
            print(f"\033[93m[CharacterProfile] Warning: Character '{selected_name}' not found. Picking random.\033[0m")
            selected_name = rng.choice(list(self.profiles.keys()))

        profile = self.profiles[selected_name]
        visuals = profile.get("visual_traits", {})
        
        hair_color = visuals.get("hair_color", "")
        hair_style = visuals.get("hair_style", "")
        eye_color = visuals.get("eye_color", "")
        personality = profile.get("personality", "neutral")
        
        # Build subject string (Natural Language)
        # Ex: "A solo girl with long straight hair, black hair, and dark brown eyes"
        parts = []
        
        # Hair description
        hair_desc = ""
        if hair_style and hair_color:
            hair_desc = f"{hair_style}, {hair_color} hair"
        elif hair_style:
            hair_desc = hair_style
        elif hair_color:
            hair_desc = f"{hair_color} hair"
            
        # Eye description
        eye_desc = ""
        if eye_color:
            eye_desc = f"{eye_color} eyes"
            
        # Combine into sentence
        subj_prompt = "A solo girl"
        if hair_desc or eye_desc:
            subj_prompt += " with "
            if hair_desc and eye_desc:
                subj_prompt += f"{hair_desc} and {eye_desc}"
            elif hair_desc:
                subj_prompt += hair_desc
            elif eye_desc:
                subj_prompt += eye_desc
        
        # Ensure it ends with a punctuation if not present (though usually fine without for prompts, 
        # let's keep it clean but maybe not strict period if downstream adds more)
        # For now, simplistic approach is fine.
        
        # Color palette
        palette = profile.get("color_palette", [])
        palette_str = ", ".join(palette)

        return (subj_prompt, hair_color, eye_color, personality, palette_str)

# Node Mappings
NODE_CLASS_MAPPINGS = {
    "CharacterProfileNode": CharacterProfileNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CharacterProfileNode": "Scripted Context Generator"
}
