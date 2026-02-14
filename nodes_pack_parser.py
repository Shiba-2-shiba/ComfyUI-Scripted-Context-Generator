import json

class PackParser:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "json_string": ("STRING", {"multiline": True, "default": "{}"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("subj", "costume", "loc", "action", "meta_mood", "meta_style", "scene_tags")
    FUNCTION = "parse"
    CATEGORY = "prompt_builder"

    def parse(self, json_string):
        data = {}
        try:
            data = json.loads(json_string)
        except Exception:
            # パース失敗時は空の辞書として扱う（エラー文字列を返す実装も可）
            pass

        meta = data.get("meta", {})
        if not isinstance(meta, dict):
            meta = {}

        return (
            str(data.get("subj", "")),
            str(data.get("costume", "")),
            str(data.get("loc", "")),
            str(data.get("action", "")),
            str(meta.get("mood", "")),
            str(meta.get("style", "")),
            json.dumps(meta.get("tags", {})),
        )