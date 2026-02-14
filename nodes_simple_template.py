class SimpleTemplateBuilder:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # garnishを追加し、デフォルトを自然言語構成に変更
                # デフォルト例: "A {meta_style} of {subj} wearing {costume}. She is {action}, {garnish}. The background is {loc}, with {meta_mood}."
                "template": ("STRING", {"multiline": True, "default": "A of {subj} wearing {costume}. She is {action}, {garnish}. The background is {loc}, with {meta_mood}."}),
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

    def build(self, template, subj="", costume="", loc="", action="", garnish="", meta_mood="", meta_style=""):
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