import json
import os
import random

if __package__ and "." in __package__:
    from ..core.context_ops import ensure_context, patch_context
else:
    from core.context_ops import ensure_context, patch_context

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
DEFAULT_STAGING_TAG_LIMIT = 2
HIGH_ENERGY_LOCATIONS = {
    "concert_stage",
    "game_arcade",
    "karaoke_bar",
    "stadium_court",
    "underground_bar",
}
QUIET_ROOM_INCOMPATIBLE_LOCATIONS = HIGH_ENERGY_LOCATIONS | {
    "commuter_transport",
    "street_cafe",
}
QUIET_ROOM_INCOMPATIBLE_LOCATION_TERMS = (
    "balcony",
    "beach",
    "courtyard",
    "garden",
    "park",
    "platform",
    "plaza",
    "rooftop",
    "station",
    "street",
    "terminal",
    "walkway",
)
WORK_FOCUSED_DESCRIPTION_MARKERS = (
    "studious pause",
    "work in front of her",
)
QUIET_ROOM_DESCRIPTION_MARKERS = ("quiet room holding around her",)


def _resolve_json_path(json_path: str) -> str:
    if not json_path or str(json_path).strip() == "":
        json_path = "mood_map.json"
    if not os.path.isabs(json_path):
        json_path = os.path.join(ROOT_DIR, json_path)
    return json_path


def _normalize_staging_tags(staging_list):
    normalized = []
    for item in staging_list or []:
        text = str(item or "").strip()
        if text:
            normalized.append(text)
    return normalized


def select_staging_tags(staging_list, seed, max_items=0):
    normalized = _normalize_staging_tags(staging_list)
    try:
        max_items = int(max_items or 0)
    except Exception:
        max_items = 0
    if max_items <= 0 or max_items >= len(normalized):
        return normalized
    rng = random.Random(int(seed))
    selected_indexes = sorted(rng.sample(range(len(normalized)), k=max_items))
    return [normalized[index] for index in selected_indexes]


def serialize_staging_tags(staging_list):
    return ", ".join(_normalize_staging_tags(staging_list))


def _resolved_action_purpose(ctx):
    frame = ctx.extras.get("action_frame", {}) if isinstance(ctx.extras, dict) else {}
    slots = frame.get("legacy_slots", {}) if isinstance(frame, dict) else {}
    purpose = slots.get("purpose") if isinstance(slots, dict) else ""
    if purpose:
        return str(purpose).strip().lower()
    tags = ctx.meta.tags if isinstance(ctx.meta.tags, dict) else {}
    return str(tags.get("purpose", "")).strip().lower()


def _mood_description_compatible(description, ctx):
    text = str(description or "").lower()
    purpose = _resolved_action_purpose(ctx)
    location = str(ctx.loc or "").strip().lower()
    if purpose not in {"study", "work"} and any(
        marker in text for marker in WORK_FOCUSED_DESCRIPTION_MARKERS
    ):
        return False
    quiet_room_incompatible = (
        location in QUIET_ROOM_INCOMPATIBLE_LOCATIONS
        or any(term in location for term in QUIET_ROOM_INCOMPATIBLE_LOCATION_TERMS)
    )
    if quiet_room_incompatible and any(marker in text for marker in QUIET_ROOM_DESCRIPTION_MARKERS):
        return False
    return True


def _select_compatible_mood_description(key, json_path, seed, ctx, current):
    if _mood_description_compatible(current, ctx):
        return current
    path = _resolve_json_path(json_path)
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return current
    value = {str(name).lower(): item for name, item in data.items()}.get(
        str(key or "").lower().strip(), {}
    )
    descriptions = value.get("description", []) if isinstance(value, dict) else []
    compatible = [
        str(item) for item in descriptions if _mood_description_compatible(item, ctx)
    ]
    if not compatible:
        return current
    return random.Random(int(seed)).choice(compatible)


def expand_dictionary_value(key, json_path, default_value, seed, staging_tag_limit=0):
    try:
        seed = int(seed)
    except Exception:
        seed = 0

    json_path = _resolve_json_path(json_path)
    data = {}
    if os.path.exists(json_path) and os.path.isfile(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
        except Exception as exc:
            print(f"\033[93m[MoodExpand] Error loading JSON: {exc}\033[0m")
    else:
        print(f"\033[93m[MoodExpand] File not found: {json_path}\033[0m")

    key_lower = str(key).lower().strip()
    data_lower = {name.lower(): value for name, value in data.items()}
    result = data_lower.get(key_lower, default_value)
    staging_text = ""

    if isinstance(result, dict):
        rng = random.Random(seed)
        desc_list = result.get("description", [])
        if isinstance(desc_list, list) and desc_list:
            description_text = rng.choice(desc_list)
        else:
            description_text = str(result.get("description", default_value))
        staging_list = result.get("staging_tags", [])
        if isinstance(staging_list, list):
            staging_text = serialize_staging_tags(
                select_staging_tags(staging_list, seed, max_items=staging_tag_limit)
            )
        return str(description_text), staging_text

    if isinstance(result, list):
        rng = random.Random(seed)
        result = rng.choice(result) if result else default_value

    return str(result), staging_text


def apply_mood_expansion(context, seed, json_path, default_value, staging_tag_limit=DEFAULT_STAGING_TAG_LIMIT):
    ctx = ensure_context(context, default_seed=int(seed))
    key = ctx.meta.mood
    expanded_text, staging_text = expand_dictionary_value(
        key,
        json_path,
        default_value,
        seed,
        staging_tag_limit=staging_tag_limit,
    )
    expanded_text = _select_compatible_mood_description(
        key, json_path, seed, ctx, expanded_text
    )
    extras = {
        "raw_mood_key": str(ctx.extras.get("raw_mood_key") or key or "").strip()
    }
    if staging_text:
        extras["staging_tags"] = staging_text
    ctx = patch_context(ctx, updates={"seed": seed}, meta={"mood": expanded_text}, extras=extras)
    return ctx, expanded_text, staging_text
