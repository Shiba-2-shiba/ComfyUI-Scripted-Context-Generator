import json
import os
import random

if __package__ and "." in __package__:
    from ..core.schema import PromptContext
else:
    from core.schema import PromptContext


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "vocab", "data")

_PREFERRED_BASE_MOODS = {
    "quiet_focused",
    "energetic_joy",
    "peaceful_relaxed",
    "whimsical_playful",
    "romantic_allure",
}
_DISCOURAGED_BASE_MOODS = {
    "melancholic_sadness",
    "intense_anger",
    "creepy_fear",
}
_RARE_WEATHER_LOC_HINTS = {
    "rainy_alley",
    "rainy_bus_stop",
    "winter_street",
    "wave_barrel",
}


def _load_daily_life_locations(root_dir):
    compatibility_path = os.path.join(root_dir, "vocab", "data", "scene_compatibility.json")
    if not os.path.exists(compatibility_path):
        return set()
    try:
        with open(compatibility_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return set()
    return {str(item).strip() for item in data.get("daily_life_locs", []) if str(item).strip()}


def _iter_prompt_payloads(prompts_path):
    payloads = []
    if not os.path.exists(prompts_path):
        return payloads
    try:
        with open(prompts_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except Exception:
                    continue
                if isinstance(payload, dict):
                    payloads.append(payload)
    except Exception:
        return []
    return payloads


def _source_payload_score(payload, daily_life_locs):
    score = 0
    loc = str(payload.get("loc", "")).strip()
    mood = str(payload.get("meta", {}).get("mood", "")).strip()
    tags = payload.get("meta", {}).get("tags", {})
    purpose = str(tags.get("purpose", "")).strip().lower() if isinstance(tags, dict) else ""

    if loc in daily_life_locs:
        score += 5
    elif loc:
        score -= 2

    if mood in _PREFERRED_BASE_MOODS:
        score += 4
    elif mood in _DISCOURAGED_BASE_MOODS:
        score -= 6

    if purpose in {"study", "rest", "shop", "work", "commute", "wait"}:
        score += 1

    if loc in _RARE_WEATHER_LOC_HINTS:
        score -= 3

    return score


def _pick_preferred_prompt_payload(payloads, seed, daily_life_locs):
    if not payloads:
        return {}

    scored = []
    for payload in payloads:
        scored.append((_source_payload_score(payload, daily_life_locs), payload))
    max_score = max(score for score, _payload in scored)
    preferred_pool = [payload for score, payload in scored if score >= max_score - 1]

    rng = random.Random(seed)
    return dict(rng.choice(preferred_pool))


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
            payloads = _iter_prompt_payloads(prompts_path)
            if payloads:
                daily_life_locs = _load_daily_life_locations(root_dir)
                return _pick_preferred_prompt_payload(payloads, seed, daily_life_locs)
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
