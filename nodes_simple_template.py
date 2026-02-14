class SimpleTemplateBuilder:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # garnishを追加し、デフォルトを自然言語構成に変更
                # デフォルト例: "A {meta_style} of {subj} wearing {costume}. She is {action}, {garnish}. The background is {loc}, with {meta_mood}."
                "template": ("STRING", {"multiline": True, "default": "A {meta_style} of {subj} wearing {costume}. She is {action}, {garnish}. The background is {loc}, with {meta_mood}."}),
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

    def build(self, template, seed, subj="", costume="", loc="", action="", garnish="", meta_mood="", meta_style=""):
        # Auto-load templates.txt if default or empty
        import os
        import random
        
        default_template = "A {meta_style} of {subj} wearing {costume}. She is {action}, {garnish}. The background is {loc}, with {meta_mood}."
        use_default_file = False
        
        if not template or template.strip() == "" or template == default_template:
            use_default_file = True

        if use_default_file:
            template_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates.txt")
            if os.path.exists(template_path):
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        lines = [line.strip() for line in f if line.strip()]
                        if lines:
                            rng = random.Random(seed)
                            template = rng.choice(lines)
                except Exception as e:
                    print(f"\033[93m[SimpleTemplateBuilder] Error loading templates.txt: {e}\033[0m")
        
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
