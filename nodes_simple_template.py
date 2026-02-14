class SimpleTemplateBuilder:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # garnishを追加し、デフォルトを自然言語構成に変更
                # デフォルト例: "A {meta_style} of {subj} wearing {costume}. She is {action}, {garnish}. The background is {loc}, with {meta_mood}."
                "template": ("STRING", {"multiline": True, "default": "A {meta_style} of {subj} wearing {costume}. She is {action}, {garnish}. The background is {loc}, with {meta_mood}."}),
                "composition_mode": ("BOOLEAN", {"default": False}), # New input
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
            "optional": {
                "subj": ("STRING", {"forceInput": True, "default": ""}),
                "costume": ("STRING", {"forceInput": True, "default": ""}),
                "loc": ("STRING", {"forceInput": True, "default": ""}),
                "action": ("STRING", {"forceInput": True, "default": ""}),
                "garnish": ("STRING", {"forceInput": True, "default": ""}), # 新規追加: ポーズや表情の微細な描写
                "meta_mood": ("STRING", {"forceInput": True, "default": ""}),
                "meta_style": ("STRING", {"forceInput": True, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("built_prompt",)
    FUNCTION = "build"
    CATEGORY = "prompt_builder"

    def build(self, template, composition_mode, seed, subj="", costume="", loc="", action="", garnish="", meta_mood="", meta_style=""):
        import os
        import random
        
        # Helper to load lines from file
        def load_lines(filename):
            path = os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        return [line.strip() for line in f if line.strip()]
                except Exception as e:
                    print(f"\033[93m[SimpleTemplateBuilder] Error loading {filename}: {e}\033[0m")
            return []

        rng = random.Random(seed)
        
        # Helper to load consistency rules
        def load_rules():
            rule_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "rules", "consistency_rules.json")
            if os.path.exists(rule_path):
                try:
                    import json
                    with open(rule_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return data.get("conflicts", [])
                except Exception as e:
                    print(f"\033[93m[SimpleTemplateBuilder] Error loading consistency_rules.json: {e}\033[0m")
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
                        return False # Conflict
            return True

        if composition_mode:
            # Composition Mode: Intro + Body + End
            intros = load_lines("vocab/templates_intro.txt")
            bodies = load_lines("vocab/templates_body.txt")
            ends = load_lines("vocab/templates_end.txt")
            
            # Context values for checking
            context_vals = [subj, costume, loc, action, garnish, meta_mood, meta_style]
            
            def select_part(candidates, default):
                if not candidates:
                    return default
                # Try up to 10 times to find a consistent part
                for _ in range(10):
                    candidate = rng.choice(candidates)
                    if is_consistent(candidate, context_vals):
                        return candidate
                # Fallback to random if no consistent part found (or all conflict)
                return rng.choice(candidates)

            p_intro = select_part(intros, "{subj} wearing {costume}.")
            p_body = select_part(bodies, "{action}, {garnish}.")
            p_end = select_part(ends, "In {loc}, {meta_mood}.")
            
            template = f"{p_intro} {p_body} {p_end}"
        else:
            # Legacy/Single Template Mode
            default_template = "A {meta_style} of {subj} wearing {costume}. She is {action}, {garnish}. The background is {loc}, with {meta_mood}."
            use_default_file = False
            
            if not template or template.strip() == "" or template == default_template:
                use_default_file = True

            if use_default_file:
                lines = load_lines("templates.txt")
                if lines:
                    template = rng.choice(lines)
        
        result = template
        # テンプレート内のプレースホルダーを順次置換
        # 入力がNoneの場合は空文字として扱う安全策
        result = result.replace("{subj}", str(subj) if subj is not None else "")
        result = result.replace("{costume}", str(costume) if costume is not None else "")
        result = result.replace("{loc}", str(loc) if loc is not None else "")
        result = result.replace("{action}", str(action) if action is not None else "")
        result = result.replace("{garnish}", str(garnish) if garnish is not None else "") # 追加
        result = result.replace("{meta_mood}", str(meta_mood) if meta_mood is not None else "")
        result = result.replace("{meta_style}", str(meta_style) if meta_style is not None else "")
        
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
