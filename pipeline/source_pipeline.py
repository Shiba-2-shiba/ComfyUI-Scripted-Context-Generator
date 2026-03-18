import json
import os
import random

try:
    from ..core.schema import PromptContext
except ImportError:
    from core.schema import PromptContext


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def load_prompt_source_payload(json_string, seed, source_mode="auto", root_dir=None):
    source_mode = str(source_mode or "auto")
    text = str(json_string or "")
    wants_default = text.strip() in ("", "{}")
    root_dir = root_dir or ROOT_DIR

    if source_mode == "json_only":
        if wants_default:
            return {}
        try:
            return json.loads(text)
        except Exception:
            return {}

    if source_mode == "prompts_only" or wants_default:
        prompts_path = os.path.join(root_dir, "prompts.jsonl")
        if os.path.exists(prompts_path):
            try:
                with open(prompts_path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
                    if lines:
                        rng = random.Random(seed)
                        return json.loads(rng.choice(lines))
            except Exception:
                return {}
        return {}

    try:
        return json.loads(text)
    except Exception:
        return {}


def parse_prompt_source_fields(json_string, seed, source_mode="auto", root_dir=None):
    payload = load_prompt_source_payload(json_string, seed, source_mode=source_mode, root_dir=root_dir)
    context = PromptContext.from_dict(payload)
    return (
        context.subj,
        context.costume,
        context.loc,
        context.action,
        context.meta.mood,
        context.meta.style,
        json.dumps(context.meta.tags, ensure_ascii=False),
    )
