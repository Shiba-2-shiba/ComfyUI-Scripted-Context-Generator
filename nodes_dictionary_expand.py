import json
import os
import random
import re
try:
    from .vocab.seed_utils import mix_seed
except ImportError:
    from vocab.seed_utils import mix_seed

# --------------------------------------------------------------------------------
# Module Import Logic (Robust & Hot Reload)
# --------------------------------------------------------------------------------
# これにより、ComfyUIを再起動せずに vocab ファイルの変更を反映できます。
# また、フォルダ構成（パッケージ型/フラット型）の両方に対応します。

try:
    from . import clothing_vocab
except ImportError:
    try:
        import clothing_vocab
    except ImportError:
        clothing_vocab = None
        print("\033[93m[ThemeExpander] Warning: clothing_vocab.py not found.\033[0m")

try:
    from . import background_vocab
except ImportError:
    try:
        import background_vocab
    except ImportError:
        background_vocab = None
        print("\033[93m[ThemeExpander] Warning: background_vocab.py not found.\033[0m")

# --------------------------------------------------------------------------------
# Nodes
# --------------------------------------------------------------------------------

class DictionaryExpand:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "key": ("STRING", {"multiline": False, "default": "", "forceInput": True}),
                "json_path": ("STRING", {"multiline": False, "default": "mood_map.json"}),
                "default_value": ("STRING", {"multiline": False, "default": ""}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("expanded_text", "staging_tags")
    FUNCTION = "expand"
    CATEGORY = "prompt_builder"

    def expand(self, key, json_path, default_value, seed):
        # Defensive coercions to avoid UI/widget misalignment issues
        try:
            seed = int(seed)
        except Exception:
            seed = 0

        # Default to mood_map.json if path is empty
        if not json_path or json_path.strip() == "":
            json_path = "mood_map.json"

        # Handle relative path resolution
        if not os.path.isabs(json_path):
            base_dir = os.path.dirname(os.path.realpath(__file__))
            json_path = os.path.join(base_dir, json_path)

        data = {}
        if os.path.exists(json_path) and os.path.isfile(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                print(f"\033[93m[DictionaryExpand] Error loading JSON: {e}\033[0m")
        else:
            print(f"\033[93m[DictionaryExpand] File not found: {json_path}\033[0m")

        key_lower = key.lower().strip()
        data_lower = {k.lower(): v for k, v in data.items()}
        
        result = data_lower.get(key_lower, default_value)

        staging_text = ""

        # New format: dict with 'description' and 'staging_tags' fields
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
            return (description_text, staging_text)

        # Legacy format: list of strings
        if isinstance(result, list):
            rng = random.Random(seed)
            if len(result) > 0:
                result = rng.choice(result)
            else:
                result = default_value

        return (str(result), staging_text)


class ThemeClothingExpander:
    @classmethod
    def INPUT_TYPES(s):
        outfit_modes = ["random", "dresses", "separates", "outerwear_only", "no_outerwear"]
        
        return {
            "required": {
                "theme_key": ("STRING", {"multiline": False, "default": "office_lady", "forceInput": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
                "outfit_mode": (outfit_modes, {"default": "random"}),
                "outerwear_chance": ("FLOAT", {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.05}),
            },
            "optional": {
                "character_palette": ("STRING", {"multiline": False, "default": "", "forceInput": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("clothing_prompt",)
    FUNCTION = "expand_clothing"
    CATEGORY = "prompt_builder"

    def expand_clothing(self, theme_key, seed, outfit_mode, outerwear_chance, character_palette=""):
        try:
            seed = int(seed)
        except Exception:
            seed = 0

        if outfit_mode not in [
            "random",
            "dresses",
            "separates",
            "outerwear_only",
            "no_outerwear",
        ]:
            outfit_mode = "random"

        if not clothing_vocab:
            return ("[ERR: clothing_vocab.py not found]",)

        rng = random.Random(mix_seed(seed, "cloth"))
        raw_key = theme_key.lower().strip()
        
        # Parse character palette if provided
        char_colors = []
        if character_palette:
            char_colors = [c.strip() for c in character_palette.split(",") if c.strip()]

        # Alias map for clothing prompts
        alias_map = {
            "business girl": "office_lady",
            "ceo": "office_lady",
            "student": "school_uniform",
            "runner": "gym_workout",
            "fitness model": "gym_workout",
            "vacationer": "beach_resort",
            "winter traveler": "winter_date",
            "japanese shrine maiden": "traditional_japanese",
            "geisha": "traditional_japanese",
            "spy agent": "secret_agent",
            "detective": "secret_agent",
            "rock star": "rock_concert",
            "guitarist": "rock_concert",
            "gothic girl": "gothic_lolita",
            "doll-like girl": "gothic_lolita",
            "sorceress": "fantasy_battle",
            "blonde elf archer": "fantasy_battle",
            "cyberpunk warrior": "cyberpunk_night",
            "street dancer": "cyberpunk_night",
        }
        
        theme = alias_map.get(raw_key, raw_key)
        packs_map = clothing_vocab.THEME_TO_PACKS.get(theme)

        # Fallback if theme not found
        if not packs_map:
             return (f"{theme_key}, (generic outfit)",)

        final_parts = []
        
        # 1. Main Outfit (Dress or Separates)
        if outfit_mode != "outerwear_only":
            available_types = [k for k in packs_map.keys() if k in ["dresses", "separates"]]
            
            chosen_type = None
            if available_types:
                if outfit_mode in available_types:
                    chosen_type = outfit_mode
                else:
                    chosen_type = rng.choice(available_types)

            if chosen_type:
                pack_names = packs_map[chosen_type]
                chosen_pack_name = rng.choice(pack_names)
                concept_data = clothing_vocab.CONCEPT_PACKS[chosen_type].get(chosen_pack_name)

                if concept_data:
                    base_desc = self._build_item_description(rng, concept_data, char_colors)
                    final_parts.append(base_desc)

        # 2. Outerwear Logic
        has_outer = "outerwear" in packs_map and packs_map["outerwear"]
        should_add_outer = False

        if has_outer:
            if outfit_mode == "outerwear_only":
                should_add_outer = True
            elif outfit_mode == "no_outerwear":
                should_add_outer = False
            else:
                should_add_outer = rng.random() < outerwear_chance

        if should_add_outer:
            outer_pack_names = packs_map["outerwear"]
            outer_name = rng.choice(outer_pack_names)
            outer_data = clothing_vocab.CONCEPT_PACKS["outerwear"].get(outer_name)
            
            if outer_data:
                o_palette = outer_data.get("palette", {})
                o_colors = o_palette.get("colors", [])
                o_choices = outer_data.get("choices", {}).get("outerwear", [])
                
                # Logic for outerwear colors: prioritize character palette too
                o_desc = ""
                chosen_color = ""
                if char_colors and rng.random() < 0.7:
                     chosen_color = rng.choice(char_colors)
                elif o_colors:
                     chosen_color = rng.choice(o_colors)
                
                if chosen_color: o_desc += f"{chosen_color} "
                if o_choices: o_desc += f"{rng.choice(o_choices)}"
                
                if outfit_mode == "outerwear_only":
                    final_parts.append(o_desc)
                else:
                    final_parts.append(f"wearing a {o_desc} over it")

        return (", ".join(final_parts),)

    def _build_item_description(self, rng, concept_data, char_colors=None):
        selected_items = []
        choices_dict = concept_data.get("choices", {})
        for _, options in choices_dict.items():
            choice = rng.choice(options)
            if isinstance(choice, list):
                if len(choice) > 1:
                    item_str = f"{choice[1]} {choice[0]}"
                elif len(choice) == 1:
                    item_str = choice[0]
                else:
                    item_str = ""
            else:
                item_str = choice
            
            if item_str:
                selected_items.append(item_str)

        palette = concept_data.get("palette", {})
        
        def pick_palette(key):
            # Special logic for colors if character palette is provided
            if key == "colors" and char_colors:
                # 60% chance to force character palette color
                if rng.random() < 0.60:
                    return rng.choice(char_colors)
            
            default_prob = clothing_vocab.PALETTE_DEFAULT_PROBABILITIES.get(key, 0.5)
            if key in palette and palette[key]:
                if rng.random() < default_prob:
                    return rng.choice(palette[key])
            return ""

        color = pick_palette("colors")
        material = pick_palette("materials")
        pattern = pick_palette("patterns")
        style = pick_palette("styles")

        embellishments = palette.get("embellishments", [])
        opt_details = concept_data.get("optional_details", [])
        
        details_list = []
        if embellishments and rng.random() < 0.55:
            details_list.append(rng.choice(embellishments))
        if opt_details and rng.random() < 0.45:
            details_list.append(rng.choice(opt_details))
            
        states = concept_data.get("states", [])
        if states and rng.random() < 0.3:
             details_list.append(rng.choice(states))

        adjectives = [x for x in [color, pattern, material, style] if x]
        adj_str = " ".join(adjectives)
        items_str = " and ".join(selected_items)
        
        main_part = f"{adj_str} {items_str}" if adj_str else items_str
        
        if details_list:
            return f"{main_part}, with {', '.join(details_list)}"
        return main_part


class ThemeLocationExpander:
    _BIAS_OBJECT_HINTS = (
        "surfboard",
        " board",
        "book",
        "phone",
        "coffee",
        "drink",
        "microphone",
        "screen",
    )
    _TEXTURE_DEFAULT_BLEND_PROB = 0.25
    _TEXTURE_SEGMENT_SELECT_PROB = 0.55
    _FX_DEFAULT_BLEND_PROB = 0.10
    _FX_SEGMENT_SELECT_PROB = 0.20
    _MAX_FX_SEGMENTS = 1
    _FX_DENY_PATTERNS = (
        re.compile(r"\bconfetti\b", re.IGNORECASE),
        re.compile(r"\bfloating dust particles?\b", re.IGNORECASE),
        re.compile(r"\bsparkling air\b", re.IGNORECASE),
        re.compile(r"\bsparkles?\b", re.IGNORECASE),
        re.compile(r"\bglittering air\b", re.IGNORECASE),
        re.compile(r"\bbokeh\b", re.IGNORECASE),
        re.compile(r"\blens flares?\b", re.IGNORECASE),
        re.compile(r"\bdust motes?\b", re.IGNORECASE),
        re.compile(r"\bdust particles?\b", re.IGNORECASE),
        re.compile(r"\bfloating dust\b", re.IGNORECASE),
        re.compile(r"\bsparkling(?!\s+eyes\b)\w*\b", re.IGNORECASE),
    )

    def _is_symbolic_prop(self, text):
        low = str(text).lower()
        return any(token in low for token in self._BIAS_OBJECT_HINTS)

    def _props_sampling_policy(self, props_opts):
        include_prob = 0.8
        second_prop_prob = 0.45
        if len(props_opts) <= 3:
            include_prob = 0.62
            second_prop_prob = 0.20
        if any(self._is_symbolic_prop(p) for p in props_opts):
            include_prob = max(0.50, include_prob - 0.12)
            second_prop_prob = max(0.10, second_prop_prob - 0.10)
        return include_prob, second_prop_prob

    def _is_disallowed_fx_segment(self, text):
        low = str(text).lower()
        # Keep explicit allowlist exceptions.
        if "snowflake" in low:
            return False
        if "sparkling eyes" in low:
            return False
        return any(p.search(low) for p in self._FX_DENY_PATTERNS)

    def _filter_fx_candidates(self, options):
        if not options:
            return []
        filtered = []
        seen = set()
        for item in options:
            if not item:
                continue
            item_text = str(item)
            if self._is_disallowed_fx_segment(item_text):
                continue
            if item_text in seen:
                continue
            filtered.append(item_text)
            seen.add(item_text)
        return filtered

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "loc_tag": ("STRING", {"multiline": False, "default": "classroom", "forceInput": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
                "mode": (["detailed", "simple"], {"default": "detailed"}),
                "lighting_mode": (["auto", "off"], {"default": "auto"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("location_prompt",)
    FUNCTION = "expand_location"
    CATEGORY = "prompt_builder"

    def expand_location(self, loc_tag, seed, mode, lighting_mode="auto"):
        try:
            seed = int(seed)
        except Exception:
            seed = 0

        if mode not in ["detailed", "simple"]:
            mode = "detailed"

        if not background_vocab:
            return ("[ERR: background_vocab.py not found]",)

        rng = random.Random(mix_seed(seed, "loc"))
        cleaned_tag = loc_tag.lower().strip()
        
        # Resolve mapping from background_vocab
        pack_candidates = background_vocab.LOC_TAG_MAP.get(cleaned_tag)
        
        # Fallback if mapping not found
        if not pack_candidates:
            return (loc_tag,)

        # Select a concept pack
        selected_pack_key = rng.choice(pack_candidates)
        pack_data = background_vocab.CONCEPT_PACKS.get(selected_pack_key)

        if not pack_data:
            return (loc_tag,)

        # Phase1: バリエーション増強のための改修
        # 1. 基本環境
        env_options = pack_data.get("environment", [])
        env_part = rng.choice(env_options) if env_options else cleaned_tag
        
        if mode == "simple":
            return (env_part,)

        segments = []

        # 2. Core: 1〜2個選択し、and/plus で繋ぐ
        core_opts = pack_data.get("core", [])
        if core_opts and rng.random() < 0.95: 
            num_core = 1
            if len(core_opts) > 1 and rng.random() < 0.50: # Increased from 0.40
                num_core = 2
            
            chosen_core = rng.sample(core_opts, k=min(num_core, len(core_opts)))
            
            if len(chosen_core) == 1:
                segments.append(f"featuring {chosen_core[0]}")
            else:
                connector = rng.choice(["and", "plus", "featuring"])
                segments.append(f"featuring {chosen_core[0]} {connector} {chosen_core[1]}")

        # 3. Props: 1〜2個選択し、接続詞を工夫
        props_opts = pack_data.get("props", [])
        include_prob, second_prop_prob = self._props_sampling_policy(props_opts)
        if props_opts and rng.random() < include_prob:
            num_props = 1
            if len(props_opts) > 1 and rng.random() < second_prop_prob:
                num_props = 2
            if num_props == 2 and all(self._is_symbolic_prop(p) for p in props_opts):
                num_props = 1
            
            chosen_props = rng.sample(props_opts, k=min(num_props, len(props_opts)))
            connector_word = rng.choice(["with", "scattered with", "filled with", "adorned with"])
            
            if len(chosen_props) == 1:
                segments.append(f"{connector_word} {chosen_props[0]}")
            else:
                joiner = rng.choice(["and", "plus", "as well as"])
                segments.append(f"{connector_word} {chosen_props[0]} {joiner} {chosen_props[1]}")

        # 4. Texture: blend defaults conservatively to reduce repetitive defaults.
        texture_opts = pack_data.get("texture", []) or []
        texture_candidates = list(texture_opts)
        
        general_defaults = getattr(background_vocab, "GENERAL_DEFAULTS", {})
        
        if rng.random() < self._TEXTURE_DEFAULT_BLEND_PROB:
            texture_candidates.extend(general_defaults.get("texture", []))
            
        if texture_candidates and rng.random() < self._TEXTURE_SEGMENT_SELECT_PROB:
            segments.append(rng.choice(texture_candidates))

        # 5. ディテール: GENERAL_DEFAULTS から追加
        if rng.random() < 0.35:
            details_defaults = general_defaults.get("details", [])
            if details_defaults:
                segments.append(rng.choice(details_defaults))

        # 6. 時間帯: オリジナルと同様
        time_opts = pack_data.get("time", [])
        if time_opts and rng.random() < 0.5:
            segments.append(f"during {rng.choice(time_opts)}")
            
        # 7. FX: strict cap and denylist filtering to avoid particle overuse.
        fx_opts = pack_data.get("fx", []) or []
        fx_candidates = self._filter_fx_candidates(fx_opts)

        if rng.random() < self._FX_DEFAULT_BLEND_PROB:
            fx_candidates.extend(
                self._filter_fx_candidates(general_defaults.get("fx", []))
            )

        fx_segments_added = 0
        if (
            fx_candidates
            and fx_segments_added < self._MAX_FX_SEGMENTS
            and rng.random() < self._FX_SEGMENT_SELECT_PROB
        ):
            segments.append(rng.choice(fx_candidates))
            fx_segments_added += 1

        # 8. 順序をランダムシャッフル
        rng.shuffle(segments)
        deduped_segments = []
        seen_segments = set()
        for seg in segments:
            if seg not in seen_segments:
                deduped_segments.append(seg)
                seen_segments.add(seg)
        
        # 9. 光源タグ (lighting_mode)
        if lighting_mode == "auto":
            lighting_opts = pack_data.get("lighting", [])
            if lighting_opts:
                deduped_segments.append(rng.choice(lighting_opts))
        
        # 10. 最終的な文字列を生成
        final_prompt = ", ".join([env_part] + deduped_segments) if deduped_segments else env_part
        return (final_prompt,)

# Mappings
NODE_CLASS_MAPPINGS = {
    "DictionaryExpand": DictionaryExpand,
    "ThemeClothingExpander": ThemeClothingExpander,
    "ThemeLocationExpander": ThemeLocationExpander
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DictionaryExpand": "Dictionary Expand",
    "ThemeClothingExpander": "Theme Clothing Expander",
    "ThemeLocationExpander": "Theme Location Expander"
}
