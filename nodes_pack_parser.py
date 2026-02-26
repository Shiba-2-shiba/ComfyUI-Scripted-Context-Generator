import json

class PackParser:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "json_string": ("STRING", {"multiline": True, "default": "{}"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "control_after_generate": ("STRING", {"default": "randomize"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("subj", "costume", "loc", "action", "meta_mood", "meta_style", "scene_tags")
    FUNCTION = "parse"
    CATEGORY = "prompt_builder"

    def parse(self, json_string, seed):
        import os
        import random
        # Import Schema
        try:
            from .core.schema import PromptContext
        except ImportError:
            # Fallback path if running as script from root without package context
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
            from core.schema import PromptContext
        
        # 1. Load Data Source (JSON String or File)
        data_dict = {}
        use_default_file = False
        
        if not json_string or json_string.strip() == "" or json_string.strip() == "{}":
            use_default_file = True
            
        if use_default_file:
            prompts_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "prompts.jsonl")
            if os.path.exists(prompts_path):
                try:
                    with open(prompts_path, 'r', encoding='utf-8') as f:
                        lines = [line.strip() for line in f if line.strip()]
                        if lines:
                            rng = random.Random(seed)
                            selected_line = rng.choice(lines)
                            try:
                                data_dict = json.loads(selected_line)
                            except Exception as e:
                                print(f"\033[93m[PackParser] Error parsing line from prompts.jsonl: {e}\033[0m")
                except Exception as e:
                    print(f"\033[93m[PackParser] Error loading prompts.jsonl: {e}\033[0m")
        else:
            try:
                data_dict = json.loads(json_string)
            except Exception:
                pass

        # 2. Convert to Schema
        context = PromptContext.from_dict(data_dict)

        # 3. Return (Standard ComfyUI Outputs - Flattened)
        return (
            context.subj,
            context.costume,
            context.loc,
            context.action,
            context.meta.mood,
            context.meta.style,
            json.dumps(context.meta.tags, ensure_ascii=False),
        )


