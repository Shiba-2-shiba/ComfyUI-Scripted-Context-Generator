import logging
import os
import random
import json
import re

# Logging Setup
logger = logging.getLogger("SimpleTemplateBuilder")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(os.path.join(os.path.dirname(os.path.realpath(__file__)), "simple_template_debug.log"), encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

DEFAULT_GENERATION_MODE = "scene_emotion_priority"
DEFAULT_TEMPLATE = "{subject_clause}, {action_clause}, {scene_clause}."
DEFAULT_END_TEMPLATE = "{scene_clause}"

class SimpleTemplateBuilder:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # garnishを追加し、デフォルトを自然言語構成に変更
                # 既定モードは style 任意・scene/emotion 優先
                "template": ("STRING", {"multiline": True, "default": DEFAULT_TEMPLATE}),
                "composition_mode": ("BOOLEAN", {"default": False}), # New input
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
            },
            "optional": {
                "subj": ("STRING", {"forceInput": True, "default": ""}),
                "costume": ("STRING", {"forceInput": True, "default": ""}),
                "loc": ("STRING", {"forceInput": True, "default": ""}),
                "action": ("STRING", {"forceInput": True, "default": ""}),
                "garnish": ("STRING", {"forceInput": True, "default": ""}), # 新規追加: ポーズや表情の微細な描写
                "meta_mood": ("STRING", {"forceInput": True, "default": ""}),
                "meta_style": ("STRING", {"forceInput": True, "default": ""}),
                "staging_tags": ("STRING", {"forceInput": True, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("built_prompt",)
    FUNCTION = "build"
    CATEGORY = "prompt_builder"

    def build(self, template, composition_mode, seed, subj="", costume="", loc="", action="", garnish="", meta_mood="", meta_style="", staging_tags=""):
        logger.info(f"--- SimpleTemplateBuilder Build Start (Seed: {seed}) ---")
        logger.debug(f"Generation Mode: {DEFAULT_GENERATION_MODE}")
        logger.debug(f"Inputs - Subj: {subj}, Costume: {costume}, Loc: {loc}, Action: {action}, Garnish: {garnish}, Mood: {meta_mood}, Style: {meta_style}, Staging: {staging_tags}")
        logger.debug(f"Composition Mode: {composition_mode}")

        # Helper to load lines from file
        def load_lines(filename):
            path = os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = [line.strip() for line in f if line.strip()]
                        logger.debug(f"Loaded {len(lines)} lines from {filename}")
                        return lines
                except Exception as e:
                    logger.error(f"Error loading {filename}: {e}")
                    print(f"\033[93m[SimpleTemplateBuilder] Error loading {filename}: {e}\033[0m")
            else:
                 logger.warning(f"File not found: {filename}")
            return []

        rng = random.Random(seed)

        def join_nonempty(parts, sep=", "):
            cleaned = []
            for part in parts:
                if part is None:
                    continue
                text = str(part).strip().strip(",")
                if text:
                    cleaned.append(text)
            return sep.join(cleaned)

        def strip_clause_punctuation(text):
            if text is None:
                return ""
            return re.sub(r"[\s,.;:]+$", "", str(text).strip())

        def compose_visual_sentence(*parts):
            clauses = []
            for part in parts:
                clean = strip_clause_punctuation(part)
                if clean:
                    clauses.append(clean)
            if not clauses:
                return ""
            return ", ".join(clauses) + "."

        def normalize_prompt(text):
            if text is None:
                return ""
            text = str(text)
            text = re.sub(r"\s+", " ", text)
            text = re.sub(r"\s+([,.;:])", r"\1", text)
            text = re.sub(r",\s*,+", ", ", text)
            text = re.sub(r"\.\s*\.+", ".", text)
            text = re.sub(r",\s*\.", ".", text)
            text = re.sub(r"\s+", " ", text).strip()
            return text

        subject_clause = join_nonempty([
            subj,
            f"in {costume}" if costume else "",
        ], " ")
        action_clause = join_nonempty([action, garnish])
        scene_clause = join_nonempty([
            f"in {loc}" if loc else "",
            meta_mood,
        ])
        
        # Helper to load consistency rules
        def load_rules():
            rule_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "rules", "consistency_rules.json")
            if os.path.exists(rule_path):
                try:
                    with open(rule_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        rules = data.get("conflicts", [])
                        logger.debug(f"Loaded {len(rules)} consistency rules.")
                        return rules
                except Exception as e:
                    logger.error(f"Error loading consistency_rules.json: {e}")
                    print(f"\033[93m[SimpleTemplateBuilder] Error loading consistency_rules.json: {e}\033[0m")
            else:
                logger.warning("consistency_rules.json not found.")
            return []

        rules = load_rules()
        
        # Helper to check consistency
        def is_consistent(template_part, context_values):
            for rule in rules:
                input_term = rule.get("input_term", "").lower()
                template_term = rule.get("template_term", "").lower()
                
                if not input_term or not template_term:
                    continue
                
                # Check if any input triggers the rule
                triggered = False
                for val in context_values:
                    if val and input_term in str(val).lower():
                        triggered = True
                        break
                
                if triggered:
                    if template_term in template_part.lower():
                        logger.debug(f"Conflict detected: input '{input_term}' conflicts with template '{template_term}' in part '{template_part}'")
                        return False # Conflict
            return True

        # --------------------------------------------------------------------------------
        # Location Expansion (Phase 1) - MOVED TO TOP
        # --------------------------------------------------------------------------------
        # Load background packs to expand 'loc' key into descriptive text
        bg_packs_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "vocab", "data", "background_packs.json")
        if loc and isinstance(loc, str) and os.path.exists(bg_packs_path):
            try:
                with open(bg_packs_path, 'r', encoding='utf-8') as f:
                    bg_packs = json.load(f)
                
                if loc in bg_packs:
                    logger.info(f"Expanding location: {loc}")
                    pack = bg_packs[loc]
                    parts = []
                    
                    # Define context values for consistency check
                    # Note: We use the original 'loc' key in context_vals which is fine for now,
                    # but we also want to ensure the expanded parts are consistent with EACH OTHER and INPUTS.
                    context_vals = [subj, costume, loc, action, garnish, meta_mood, meta_style, staging_tags]

                    def pick_consistent(candidates):
                        if not candidates: return None
                        # Try up to 10 times to find a consistent candidate
                        for i in range(10):
                            candidate = rng.choice(candidates)
                            if is_consistent(str(candidate), context_vals):
                                return candidate
                        
                        logger.debug("Failed to find consistent candidate after 10 attempts.")
                        # If no consistent candidate found, return None (omit this details)
                        return None
                    
                    # 1. Environment (Base)
                    envs = pack.get("environment", [])
                    if envs:
                        e = pick_consistent(envs)
                        if e:
                            parts.append(e)
                        else:
                            parts.append(pack.get("label", loc))
                    else:
                        parts.append(pack.get("label", loc))
                    
                    # 2. Time
                    times = pack.get("time", [])
                    if times:
                        t = pick_consistent(times)
                        if t:
                            parts.append(f"during {t}")

                    # 3. Weather (New Axis)
                    weathers = pack.get("weather", [])
                    if weathers:
                        w = pick_consistent(weathers)
                        if w:
                            parts.append(w)
                        
                    # 4. Crowd (New Axis)
                    crowds = pack.get("crowd", [])
                    if crowds:
                        c = pick_consistent(crowds)
                        if c:
                            parts.append(c)
                    
                    # Replace loc key with expanded description
                    new_loc = ", ".join(parts)
                    logger.debug(f"Expanded loc '{loc}' to '{new_loc}'")
                    loc = new_loc
            except Exception as e:
                logger.error(f"Error expanding location: {e}")
                print(f"[SimpleTemplateBuilder] Error expanding location: {e}")

        if composition_mode:
            logger.info("Using Composition Mode")
            # Composition Mode: Intro + Body + End
            intros = load_lines("vocab/templates_intro.txt")
            bodies = load_lines("vocab/templates_body.txt")
            ends = load_lines("vocab/templates_end.txt")
            
            # Context values for checking - NOW INCLUDES EXPANDED LOC
            context_vals = [subj, costume, loc, action, garnish, meta_mood, meta_style, staging_tags]
            
            def select_part(candidates, default, part_name="part"):
                if not candidates:
                    return default
                # Try up to 10 times to find a consistent part
                for i in range(10):
                    candidate = rng.choice(candidates)
                    if is_consistent(candidate, context_vals):
                        return candidate
                
                logger.debug(f"Failed to find consistent {part_name} after 10 attempts. Falling back to random.")
                # Fallback to random if no consistent part found (or all conflict)
                return rng.choice(candidates)

            p_intro = select_part(intros, "{subject_clause}", "intro")
            p_body = select_part(bodies, "{action_clause}", "body")
            p_end = select_part(ends, DEFAULT_END_TEMPLATE, "end")

            template = compose_visual_sentence(p_intro, p_body, p_end)
            logger.debug(f"Composed Template: {template}")
        else:
            # Legacy/Single Template Mode
            logger.info("Using Legacy/Single Template Mode")
            default_template = DEFAULT_TEMPLATE
            use_default_file = False
            
            if not template or template.strip() == "" or template == default_template:
                use_default_file = True
                logger.debug("Template is empty or default, using templates.txt")

            if use_default_file:
                lines = load_lines("templates.txt")
                if lines:
                    template = rng.choice(lines)
        
        result = template
        result = result.replace("{subject_clause}", subject_clause)
        result = result.replace("{action_clause}", action_clause)
        result = result.replace("{scene_clause}", scene_clause)
        # テンプレート内のプレースホルダーを順次置換
        # 入力がNoneの場合は空文字として扱う安全策
        result = result.replace("{subj}", str(subj) if subj is not None else "")
        result = result.replace("{costume}", str(costume) if costume is not None else "")
        result = result.replace("{loc}", str(loc) if loc is not None else "")
        result = result.replace("{action}", str(action) if action is not None else "")
        result = result.replace("{garnish}", str(garnish) if garnish is not None else "") # 追加
        result = result.replace("{meta_mood}", str(meta_mood) if meta_mood is not None else "")
        result = result.replace("{meta_style}", str(meta_style) if meta_style is not None else "")
        
        # Append staging_tags at the end if present, since template might not have a placeholder for it
        if staging_tags and isinstance(staging_tags, str) and staging_tags.strip():
            # Only append if it wasn't replaced by a placeholder
            if "{staging_tags}" in result:
                result = result.replace("{staging_tags}", staging_tags)
            else:
                # Add to the very end
                result = f"{result}, {staging_tags}"
        else:
             result = result.replace("{staging_tags}", "") # clean up unused placeholders

        result = normalize_prompt(result)
        logger.info(f"Final Prompt: {result}")
        return (result,)

# --------------------------------------------------------------------------------
# Node Mappings
# --------------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "SimpleTemplateBuilder": SimpleTemplateBuilder
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SimpleTemplateBuilder": "Simple Template Builder"
}
