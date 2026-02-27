import importlib
import random
import os

# --------------------------------------------------------------------------------
# Module Import Logic
# --------------------------------------------------------------------------------
# improved_pose_emotion_vocab.py を読み込みます
vocab_module = None
try:
    from . import improved_pose_emotion_vocab as vocab_module
    importlib.reload(vocab_module)
except ImportError:
    try:
        import improved_pose_emotion_vocab as vocab_module
        importlib.reload(vocab_module)
    except ImportError:
        vocab_module = None
        print("\033[93m[GarnishNodes] Warning: improved_pose_emotion_vocab.py not found.\033[0m")

# --------------------------------------------------------------------------------
# Node: GarnishSampler
# --------------------------------------------------------------------------------
class GarnishSampler:
    """
    ActionとMoodに基づいて、ポーズや表情の「添え物(Garnish)」を生成するノード。
    improved_pose_emotion_vocab.py の sample_garnish APIを使用します。
    """
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # Actionテキスト: 矛盾検知（座ってるのに立ちポーズ等）およびMicro-action生成に使用
                "action_text": ("STRING", {"multiline": False, "default": "", "forceInput": True}),
                
                # Mood Key: "quiet", "energetic" などのキー（展開前の短い文字列）
                "meta_mood_key": ("STRING", {"multiline": False, "default": "neutral", "forceInput": True}),
                
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
                "max_items": ("INT", {"default": 3, "min": 1, "max": 10}),
                "include_camera": ("BOOLEAN", {"default": False, "label_on": "Enable", "label_off": "Disable"}),
                "emotion_nuance": ("STRING", {
                    "default": "random",
                    "choices": ["random", "tense", "absorbed", "relieved", "awkward", "content", "bored"]
                }),
                # Context info (Optional) for filtering out-of-place items
                "context_loc": ("STRING", {"multiline": False, "default": "", "forceInput": True}),
                "context_costume": ("STRING", {"multiline": False, "default": "", "forceInput": True}),
            },
            "optional": {
                "scene_tags": ("STRING", {"multiline": False, "default": "{}", "forceInput": True}),
                "personality": ("STRING", {"multiline": False, "default": "", "forceInput": True}),
            }
        }

    RETURN_TYPES = ("STRING", "DICT")
    RETURN_NAMES = ("garnish_string", "debug_info")
    FUNCTION = "sample"
    CATEGORY = "prompt_builder/garnish"

    def sample(self, action_text, meta_mood_key, seed, max_items, include_camera, emotion_nuance="random", context_loc="", context_costume="", scene_tags="{}", personality=""):
        if not vocab_module:
            return ("", {})

        # Import Schema
        try:
            from .core.schema import PromptContext, MetaInfo, DebugInfo
        except ImportError:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
            from core.schema import PromptContext, MetaInfo, DebugInfo
        
        # Parse scene_tags JSON string to dict
        import json
        try:
            parsed_tags = json.loads(scene_tags) if scene_tags else {}
        except (json.JSONDecodeError, TypeError):
            parsed_tags = {}

        # Construct Context
        # Note: action_text is main input here, but strictly it belongs to context.action
        # We build a context representing the state *before* garnish
        ctx = PromptContext(
            action=action_text,
            loc=context_loc,
            costume=context_costume,
            meta=MetaInfo(
                mood=meta_mood_key,
                tags=parsed_tags
            )
        )
        
        local_debug = {}
        
        try:
            # Call Vocab Module with debug_log
            if not emotion_nuance or str(emotion_nuance).strip().lower() in {"random", "none"}:
                emotion_nuance = ""
            tags = vocab_module.sample_garnish(
                seed=seed,
                meta_mood=ctx.meta.mood,
                action_text=ctx.action,
                max_items=max_items,
                include_camera=include_camera,
                context_loc=ctx.loc,
                context_costume=ctx.costume,
                scene_tags=ctx.meta.tags,
                personality=personality,
                emotion_nuance=emotion_nuance,
                debug_log=local_debug
            )
            
            debug_info = DebugInfo(
                node="GarnishSampler",
                seed=seed,
                decision=local_debug
            )
            
            return (", ".join(tags), debug_info.to_dict())

        except TypeError:
            # 旧APIへのフォールバック（引数が違う場合など）
            print("\033[93m[GarnishSampler] Warning: Falling back to legacy API signature.\033[0m")
            try:
                # 旧シグネチャを想定: sample_garnish(seed, meta_mood, action_text, max_items)
                tags = vocab_module.sample_garnish(
                    seed=seed, 
                    meta_mood=ctx.meta.mood, 
                    action_text=ctx.action, 
                    max_items=max_items
                )
                return (", ".join(tags), {})
            except Exception as e:
                print(f"\033[91m[GarnishSampler] Error calling vocab module: {e}\033[0m")
                return ("", {"error": str(e)})
        except Exception as e:
            print(f"\033[91m[GarnishSampler] Error calling vocab module: {e}\033[0m")
            return ("", {"error": str(e)})


# --------------------------------------------------------------------------------
# Node: ActionMerge
# --------------------------------------------------------------------------------
class ActionMerge:
    """
    元のActionテキストと、生成されたGarnishを結合するシンプルなノード。
    テンプレートに入れる前にここで一本化します。
    """
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "original_action": ("STRING", {"multiline": False, "default": "", "forceInput": True}),
                "garnish": ("STRING", {"multiline": False, "default": "", "forceInput": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("merged_action",)
    FUNCTION = "merge"
    CATEGORY = "prompt_builder/garnish"

    def merge(self, original_action, garnish):
        parts = []
        if original_action:
            parts.append(original_action)
        if garnish:
            parts.append(garnish)
        
        return (", ".join(parts),)

# ノード登録
NODE_CLASS_MAPPINGS = {
    "GarnishSampler": GarnishSampler
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GarnishSampler": "Garnish Sampler (Improved)"
}
