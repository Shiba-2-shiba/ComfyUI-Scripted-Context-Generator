import json


class PromptQualityVerificationSink:
    """Verification-only terminal used to observe the real ComfyUI execution path."""

    CATEGORY = "testing/prompt_quality"
    FUNCTION = "capture"
    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("canonical_outputs",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "final_context": ("STRING", {"forceInput": True}),
                "raw_prompt": ("STRING", {"forceInput": True}),
                "cleaned_prompt": ("STRING", {"forceInput": True}),
            }
        }

    def capture(self, final_context, raw_prompt, cleaned_prompt):
        context = json.loads(final_context)
        payload = {
            "cleaned_prompt": cleaned_prompt,
            "final_context": context,
            "raw_prompt": raw_prompt,
        }
        canonical_outputs = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return {
            "ui": {"canonical_outputs": [canonical_outputs]},
            "result": (canonical_outputs,),
        }


NODE_CLASS_MAPPINGS = {"PromptQualityVerificationSink": PromptQualityVerificationSink}
NODE_DISPLAY_NAME_MAPPINGS = {"PromptQualityVerificationSink": "Prompt Quality Verification Sink"}
