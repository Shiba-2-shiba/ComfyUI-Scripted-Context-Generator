"""
Garnish logic module.
Builds emotion-led physical expression tags while preserving deterministic seed behavior.
"""

import random
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

try:
    from ...core.semantic_policy import sanitize_sequence
except ImportError:
    from core.semantic_policy import sanitize_sequence

from .utils import _dedupe
from .base_vocab import (
    POSE_STANDING,
    POSE_SITTING,
    POSE_LYING,
    POSE_DYNAMIC,
    HAND_GESTURES,
    EYES_BASE,
    MOUTH_BASE,
)
from .micro_actions import MICRO_ACTION_CONCEPTS


EMOTION_CATEGORIES = [
    "joy",
    "playful",
    "anger",
    "sadness",
    "relax",
    "focus",
    "care",
    "impatience",
    "moved",
]

INTENSITIES = ["mild", "medium", "strong"]

LOAD_KEYWORDS = {
    "intimate": ["hugging", "holding hands", "kissing", "cuddling", "bed", "bedroom", "bath", "soaking"],
    "tense": ["fighting", "arguing", "hiding", "sneaking", "battle", "danger", "crying", "scared", "frustration", "rage"],
    "active": ["running", "walking", "dancing", "jumping", "flying", "playing", "cleaning", "cooking", "sweeping", "exercising", "lifting"],
    "calm": ["sitting", "standing", "lying", "reading", "sleeping", "waiting", "looking", "watching", "listening"],
}

COMPATIBILITY = {
    "calm": {"joy", "playful", "anger", "sadness", "relax", "focus", "care", "impatience", "moved"},
    "active": {"joy", "playful", "anger", "focus", "impatience", "moved"},
    "tense": {"anger", "focus", "impatience", "sadness"},
    "intimate": {"joy", "playful", "sadness", "relax", "moved", "care"},
}

LEGACY_MAP = {
    "quiet": ("focus", "mild"),
    "quiet_focused": ("focus", "medium"),
    "energetic_joy": ("joy", "strong"),
    "whimsical_playful": ("playful", "medium"),
    "intense_anger": ("anger", "strong"),
    "melancholic_sadness": ("sadness", "medium"),
    "peaceful_relaxed": ("relax", "medium"),
    "mysterious_curious": ("focus", "medium"),
    "romantic_allure": ("care", "medium"),
    "creepy_fear": ("impatience", "strong"),
    "energetic": ("joy", "medium"),
    "whimsical": ("playful", "mild"),
    "intense": ("anger", "medium"),
    "melancholic": ("sadness", "mild"),
    "peaceful": ("relax", "mild"),
}

EMOTION_NUANCE_MAP = {
    "tense": ("impatience", "strong"),
    "absorbed": ("focus", "strong"),
    "relieved": ("relax", "mild"),
    "awkward": ("impatience", "mild"),
    "content": ("joy", "mild"),
    "bored": ("sadness", "mild"),
}

PERSONALITY_GARNISH_BIAS: Dict[str, Dict[str, Any]] = {
    "shy": {
        "prefer": ["looking away", "looking down", "fidgeting with her sleeve", "holding her bag close"],
        "prefer_category": "care",
    },
    "confident": {
        "prefer": ["looking at viewer", "chin lifted slightly", "steady stance"],
        "prefer_category": "joy",
    },
    "energetic": {
        "prefer": ["bright smile", "leaning forward", "hands moving as she talks"],
        "prefer_category": "joy",
    },
    "gloomy": {
        "prefer": ["downcast eyes", "slumped shoulders", "hands tucked close"],
        "prefer_category": "sadness",
    },
    "faithful": {
        "prefer": ["warm gaze", "gentle smile", "hands held carefully together"],
        "prefer_category": "care",
    },
    "aggressive": {
        "prefer": ["sharp gaze", "clenched jaw", "fists tightening"],
        "prefer_category": "anger",
    },
    "mysterious": {
        "prefer": ["sideways glance", "half-hidden expression", "still posture"],
        "prefer_category": "focus",
    },
    "cheerful": {
        "prefer": ["wide smile", "eyes brightening", "open posture"],
        "prefer_category": "playful",
    },
    "serious": {
        "prefer": ["focused gaze", "firm mouth", "composed posture"],
        "prefer_category": "focus",
    },
    "gentle": {
        "prefer": ["soft smile", "gentle eyes", "loose hands"],
        "prefer_category": "care",
    },
    "neutral": {"prefer": [], "prefer_category": None},
    "": {"prefer": [], "prefer_category": None},
}

EMOTION_MODEL: Dict[str, Dict[str, List[str]]] = {
    "joy": {
        "expression": ["bright smile", "eyes crinkling softly", "cheeks lifting with a smile"],
        "gaze": ["warm gaze", "eyes brightening", "looking up with expectation"],
        "mouth": ["smiling to herself", "soft grin", "slightly parted smile"],
        "posture": ["light posture", "shoulders opening up", "standing a little taller"],
        "hands": ["fingers tapping lightly", "hands moving with excitement", "one hand lifted mid-gesture"],
        "behavior": ["bouncing lightly on her heels", "leaning into the moment", "holding herself with easy energy"],
    },
    "playful": {
        "expression": ["mischievous smile", "playful expression", "suppressed laughter"],
        "gaze": ["sideways glance", "teasing look", "curious eyes"],
        "mouth": ["crooked smile", "small laugh at the corner of her mouth", "wry grin"],
        "posture": ["loose playful posture", "tilting her head", "weight shifted to one side"],
        "hands": ["finger raised as if an idea just hit", "fingers brushing her lips", "one hand swinging lightly"],
        "behavior": ["shifting in place as if ready to move", "playing with a loose strand of hair", "holding back a laugh"],
    },
    "anger": {
        "expression": ["clenched jaw", "furrowed brow", "hard stare"],
        "gaze": ["sharp gaze", "glaring straight ahead", "eyes narrowed with tension"],
        "mouth": ["lips pressed thin", "teeth set", "tight mouth"],
        "posture": ["tense posture", "shoulders held rigid", "leaning forward aggressively"],
        "hands": ["fists tightening", "hands rigid at her sides", "knuckles whitening"],
        "behavior": ["breathing hard through her nose", "holding herself ready to snap", "tension running through her arms"],
    },
    "sadness": {
        "expression": ["downcast eyes", "faint frown", "tired expression"],
        "gaze": ["distant gaze", "looking down", "eyes glossed with feeling"],
        "mouth": ["lips trembling slightly", "mouth drawn small", "quietly pressed lips"],
        "posture": ["slumped shoulders", "folded-in posture", "chin lowered"],
        "hands": ["hands held close to her chest", "fingers tightening around her sleeve", "one hand brushing at her face"],
        "behavior": ["holding herself small", "lingering in stillness", "wiping at the corner of one eye"],
    },
    "relax": {
        "expression": ["calm expression", "gentle smile", "soft eyes"],
        "gaze": ["easy gaze", "half-lidded eyes", "quiet look around her"],
        "mouth": ["relaxed lips", "faint smile", "contented mouth"],
        "posture": ["relaxed posture", "loose shoulders", "settled stance"],
        "hands": ["loose hands", "fingers resting lightly", "hands folded without tension"],
        "behavior": ["breathing evenly", "moving at an unhurried pace", "leaning back comfortably"],
    },
    "focus": {
        "expression": ["focused expression", "brows knit in concentration", "composed face"],
        "gaze": ["steady gaze", "eyes fixed on what she is doing", "attention locked forward"],
        "mouth": ["closed mouth", "lips set in concentration", "subtle pursed lips"],
        "posture": ["still posture", "upright posture", "body held carefully still"],
        "hands": ["fingers working with care", "one hand paused mid-task", "hands kept precise and controlled"],
        "behavior": ["leaning in slightly", "ignoring the rest of the room", "keeping every movement deliberate"],
    },
    "care": {
        "expression": ["gentle expression", "soft smile", "kind eyes"],
        "gaze": ["warm gaze", "attentive eyes", "looking at someone with care"],
        "mouth": ["small reassuring smile", "softened mouth", "quiet smile"],
        "posture": ["open posture", "slight forward lean", "careful stance"],
        "hands": ["hands held gently", "fingers curled around something with care", "one hand near her chest"],
        "behavior": ["moving with deliberate gentleness", "keeping close without crowding", "holding still so the moment can settle"],
    },
    "impatience": {
        "expression": ["restless expression", "strained look", "uneasy face"],
        "gaze": ["quick darting glance", "checking the room again", "eyes flicking toward the exit"],
        "mouth": ["impatient sigh", "lips pressed together", "jaw set with nerves"],
        "posture": ["restless posture", "weight shifting from foot to foot", "shoulders held tight"],
        "hands": ["fingers drumming", "gripping a strap too tightly", "hands fidgeting"],
        "behavior": ["checking the time again", "pacing in a small space", "holding tension in every small movement"],
    },
    "moved": {
        "expression": ["touched expression", "misty eyes", "softly stunned face"],
        "gaze": ["lingering gaze", "eyes shining with emotion", "looking up as if taking it in"],
        "mouth": ["teary smile", "parted lips in surprise", "breath caught in a small smile"],
        "posture": ["stilled posture", "hand drawn to her chest", "shoulders softening all at once"],
        "hands": ["fingers pressing lightly to her lips", "hand over her heart", "hands held still with feeling"],
        "behavior": ["pausing as the feeling sinks in", "breathing out slowly", "holding the moment instead of moving on"],
    },
}

INTENSITY_INDEX = {"mild": 0, "medium": 1, "strong": 2}
PHYSICAL_TAG_HINTS = (
    "eyes",
    "gaze",
    "smile",
    "mouth",
    "jaw",
    "brow",
    "shoulders",
    "hands",
    "fingers",
    "posture",
    "stance",
    "breathing",
    "leaning",
    "glance",
    "lips",
)
GAZE_CONFLICTS = {
    "looking at viewer": {"looking down", "looking away", "looking aside"},
    "looking down": {"looking at viewer", "looking up"},
    "looking up": {"looking down"},
    "sideways glance": {"looking straight ahead"},
    "steady gaze": {"eyes flicking toward the exit"},
}


def _guess_action_load(action_text: str) -> str:
    if not action_text:
        return "calm"
    text = action_text.lower()
    for keyword in LOAD_KEYWORDS["intimate"]:
        if keyword in text:
            return "intimate"
    for keyword in LOAD_KEYWORDS["tense"]:
        if keyword in text:
            return "tense"
    for keyword in LOAD_KEYWORDS["active"]:
        if keyword in text:
            return "active"
    return "calm"


def _is_compatible(category: str, load: str) -> bool:
    return category in COMPATIBILITY.get(load, COMPATIBILITY["calm"])


def _select_category_weighted(load: str, rng: random.Random, prefer_category: Optional[str] = None) -> str:
    allowed = COMPATIBILITY.get(load, COMPATIBILITY["calm"])
    weights = {
        "joy": 16,
        "playful": 15,
        "relax": 15,
        "focus": 17,
        "care": 11,
        "moved": 8,
        "anger": 6 if load != "tense" else 28,
        "sadness": 4 if load not in {"tense", "active"} else 8,
        "impatience": 8 if load != "tense" else 24,
    }
    if prefer_category in allowed:
        weights[prefer_category] = weights.get(prefer_category, 10) + 12
    valid_categories = [cat for cat in EMOTION_CATEGORIES if cat in allowed]
    valid_weights = [weights.get(cat, 1) for cat in valid_categories]
    return rng.choices(valid_categories, weights=valid_weights, k=1)[0]


def _resolve_target_emotion(
    meta_mood: str,
    load: str,
    rng: random.Random,
    log: Dict[str, Any],
    prefer_category: Optional[str] = None,
    emotion_nuance: str = "",
) -> Tuple[str, str]:
    category = None
    intensity = None
    mood_key = (meta_mood or "").strip().lower().replace(" ", "_")
    nuance_key = (emotion_nuance or "").strip().lower()

    if mood_key in LEGACY_MAP:
        category, intensity = LEGACY_MAP[mood_key]
    elif mood_key in EMOTION_CATEGORIES:
        category = mood_key
        intensity = "medium"
    elif "_" in mood_key:
        parts = [part for part in mood_key.split("_") if part]
        if parts and parts[0] in EMOTION_CATEGORIES:
            category = parts[0]
            if len(parts) > 1 and parts[1] in INTENSITIES:
                intensity = parts[1]

    if nuance_key in EMOTION_NUANCE_MAP and category is None:
        category, intensity = EMOTION_NUANCE_MAP[nuance_key]

    if category and not _is_compatible(category, load):
        log["mood_conflict"] = f"requested={category} load={load}"
        category = None
        intensity = None

    if category is None:
        category = _select_category_weighted(load, rng, prefer_category=prefer_category)

    if intensity is None:
        if nuance_key in EMOTION_NUANCE_MAP and EMOTION_NUANCE_MAP[nuance_key][0] == category:
            intensity = EMOTION_NUANCE_MAP[nuance_key][1]
        elif load == "tense":
            intensity = rng.choices(INTENSITIES, weights=[1, 3, 4], k=1)[0]
        elif load == "calm":
            intensity = rng.choices(INTENSITIES, weights=[4, 4, 1], k=1)[0]
        else:
            intensity = rng.choices(INTENSITIES, weights=[2, 4, 2], k=1)[0]

    log["emotion_core"] = category
    log["emotion_intensity"] = intensity
    return category, intensity


def _get_action_anchors(action_text: str) -> List[str]:
    if not action_text:
        return []
    text_lower = action_text.lower()
    found: List[str] = []
    for concept, data in MICRO_ACTION_CONCEPTS.items():
        if not isinstance(data, dict):
            continue
        for trigger in data.get("triggers", []):
            if trigger in text_lower:
                found.append(concept)
                break
    return found


def _resolve_micro_actions(concepts: List[str], mood: str, rng: random.Random) -> List[str]:
    tags: List[str] = []
    for concept in concepts:
        concept_data = MICRO_ACTION_CONCEPTS.get(concept)
        if not isinstance(concept_data, dict):
            continue
        variants = concept_data.get("variants", {})
        candidates = (
            variants.get(mood, [])
            or variants.get("default", [])
            or variants.get("neutral", [])
            or concept_data.get("tags", [])
        )
        if candidates:
            tags.append(rng.choice(candidates))
    return tags


def _contains_any(text: str, keywords: Sequence[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _is_out_of_context(
    tag: str,
    context_loc: str,
    context_costume: str,
    action_text: str = "",
    existing_tags: Optional[Sequence[str]] = None,
) -> bool:
    tag_lower = (tag or "").lower()
    loc_lower = (context_loc or "").lower()
    costume_lower = (context_costume or "").lower()
    action_lower = (action_text or "").lower()
    existing_lower = [item.lower() for item in existing_tags or []]

    if not tag_lower:
        return True

    if _contains_any(action_lower, ["sleep", "lying", "lying on", "nap", "bed", "sofa"]) and _contains_any(
        tag_lower, ["standing", "leaning forward aggressively", "pacing", "bouncing", "on her heels"]
    ):
        return True

    if _contains_any(action_lower, ["sitting", "seated", "desk", "chair", "bench", "train seat"]) and _contains_any(
        tag_lower, ["standing a little taller", "steady stance", "standing tall"]
    ):
        return True

    if _contains_any(action_lower, ["running", "sprinting", "jumping", "dancing"]) and _contains_any(
        tag_lower, ["relaxed posture", "leaning back comfortably", "settled stance"]
    ):
        return True

    if _contains_any(action_lower, ["reading", "typing", "writing", "holding", "carrying", "using", "playing", "sweeping", "checking"]) and _contains_any(
        tag_lower, ["hands on hips", "arms crossed", "hands behind back", "hands held carefully together"]
    ):
        return True

    if _contains_any(action_lower, ["looking down"]) and _contains_any(tag_lower, ["looking up", "looking at viewer"]):
        return True
    if _contains_any(action_lower, ["looking up"]) and "looking down" in tag_lower:
        return True
    if _contains_any(action_lower, ["looking away", "looking aside"]) and "looking at viewer" in tag_lower:
        return True

    if _contains_any(loc_lower, ["train", "bus", "commuter", "elevator", "crowd"]) and _contains_any(
        tag_lower, ["arms spread", "wide gesture", "pacing in a small space"]
    ):
        return True

    if _contains_any(loc_lower, ["classroom", "library", "office", "study"]) and _contains_any(
        tag_lower, ["furious scream", "shouting", "ready to snap"]
    ):
        return True

    if "kimono" in costume_lower and "hands in pockets" in tag_lower:
        return True

    for existing in existing_lower:
        conflicts = GAZE_CONFLICTS.get(existing)
        if conflicts and tag_lower in conflicts:
            return True
        conflicts = GAZE_CONFLICTS.get(tag_lower)
        if conflicts and existing in conflicts:
            return True

    return False


def _pick_first_valid(
    candidates: Sequence[str],
    rng: random.Random,
    context_loc: str,
    context_costume: str,
    action_text: str,
    existing_tags: Sequence[str],
) -> Optional[str]:
    items = [candidate for candidate in candidates if candidate]
    if not items:
        return None
    ordered = list(items)
    rng.shuffle(ordered)
    for candidate in ordered:
        if not _is_out_of_context(candidate, context_loc, context_costume, action_text, existing_tags):
            return candidate
    return None


def _emotion_profile_tags(
    category: str,
    intensity: str,
    rng: random.Random,
    context_loc: str,
    context_costume: str,
    action_text: str,
    debug_log: Dict[str, Any],
) -> List[str]:
    model = EMOTION_MODEL.get(category, EMOTION_MODEL["focus"])
    chosen: List[str] = []
    expression = _pick_first_valid(model["expression"], rng, context_loc, context_costume, action_text, chosen)
    if expression:
        chosen.append(expression)

    gaze = _pick_first_valid(model["gaze"], rng, context_loc, context_costume, action_text, chosen)
    if gaze:
        chosen.append(gaze)

    behavior_candidates = list(model["posture"]) + list(model["hands"]) + list(model["behavior"])
    rng.shuffle(behavior_candidates)
    behavior = _pick_first_valid(behavior_candidates, rng, context_loc, context_costume, action_text, chosen)
    if behavior:
        chosen.append(behavior)

    if intensity == "strong":
        extra_candidates = list(model["mouth"]) + list(model["hands"]) + list(model["behavior"])
        extra = _pick_first_valid(extra_candidates, rng, context_loc, context_costume, action_text, chosen)
        if extra:
            chosen.append(extra)
    elif intensity == "mild":
        soft_candidates = list(model["mouth"]) + list(model["posture"])
        soft = _pick_first_valid(soft_candidates, rng, context_loc, context_costume, action_text, chosen)
        if soft and len(chosen) < 3:
            chosen.append(soft)

    debug_log["emotion_expression"] = expression or ""
    debug_log["emotion_behavior"] = [tag for tag in chosen if tag != expression]
    return chosen


def _has_physical_expression(tags: Sequence[str]) -> bool:
    return any(any(hint in tag.lower() for hint in PHYSICAL_TAG_HINTS) for tag in tags)


def _fallback_physical_tag(category: str, rng: random.Random) -> str:
    model = EMOTION_MODEL.get(category, EMOTION_MODEL["focus"])
    fallback_pool = model["expression"] + model["gaze"] + model["posture"] + model["hands"]
    return rng.choice(fallback_pool)


def sample_garnish(
    seed: int,
    meta_mood: str,
    action_text: str = "",
    max_items: int = 3,
    include_camera: bool = False,
    context_loc: str = "",
    context_costume: str = "",
    scene_tags: Dict[str, Any] = None,
    personality: str = "",
    emotion_nuance: str = "",
    debug_log: Dict[str, Any] = None,
) -> List[str]:
    if debug_log is None:
        debug_log = {}

    rng = random.Random(seed)
    scene_tags = scene_tags or {}
    personality_key = (personality or "").lower().strip()
    personality_bias = PERSONALITY_GARNISH_BIAS.get(personality_key, PERSONALITY_GARNISH_BIAS[""])

    action_load = _guess_action_load(action_text)
    debug_log["action_load"] = action_load
    debug_log["generation_mode"] = "scene_emotion_priority"

    category, intensity = _resolve_target_emotion(
        meta_mood=meta_mood,
        load=action_load,
        rng=rng,
        log=debug_log,
        prefer_category=personality_bias.get("prefer_category"),
        emotion_nuance=emotion_nuance,
    )

    garnish_pool: List[str] = []

    prefer_tags = personality_bias.get("prefer", [])
    preferred = _pick_first_valid(prefer_tags, rng, context_loc, context_costume, action_text, garnish_pool)
    if preferred:
        garnish_pool.append(preferred)
        debug_log["personality_preferred"] = preferred

    emotion_tags = _emotion_profile_tags(
        category=category,
        intensity=intensity,
        rng=rng,
        context_loc=context_loc,
        context_costume=context_costume,
        action_text=action_text,
        debug_log=debug_log,
    )
    garnish_pool.extend(emotion_tags)

    anchors = _get_action_anchors(action_text)
    debug_log["action_anchors"] = anchors
    micro_tags = _resolve_micro_actions(anchors, category, rng)
    for tag in micro_tags:
        if not _is_out_of_context(tag, context_loc, context_costume, action_text, garnish_pool):
            garnish_pool.append(tag)

    nuance_key = (emotion_nuance or "").strip().lower()
    nuance_bias = scene_tags.get("emotion_nuance") or nuance_key
    if nuance_bias and nuance_bias in EMOTION_NUANCE_MAP:
        nuance_cat = EMOTION_NUANCE_MAP[nuance_bias][0]
        nuance_model = EMOTION_MODEL.get(nuance_cat, {})
        nuance_tag = _pick_first_valid(
            nuance_model.get("behavior", []),
            rng,
            context_loc,
            context_costume,
            action_text,
            garnish_pool,
        )
        if nuance_tag:
            garnish_pool.append(nuance_tag)
            debug_log["emotion_nuance_tag"] = nuance_tag

    if not action_text:
        pose_pool = list(POSE_STANDING) + list(POSE_SITTING) + list(POSE_LYING)
        pose = _pick_first_valid(pose_pool, rng, context_loc, context_costume, action_text, garnish_pool)
        if pose:
            garnish_pool.append(pose)

    if include_camera:
        debug_log["include_camera_ignored"] = True

    if len(garnish_pool) < max_items and rng.random() < 0.20:
        fallback_detail = _pick_first_valid(
            list(EYES_BASE) + list(MOUTH_BASE) + list(HAND_GESTURES) + list(POSE_DYNAMIC),
            rng,
            context_loc,
            context_costume,
            action_text,
            garnish_pool,
        )
        if fallback_detail:
            garnish_pool.append(fallback_detail)

    final_tags = sanitize_sequence(_dedupe(garnish_pool))
    filtered_tags: List[str] = []
    for tag in final_tags:
        if not _is_out_of_context(tag, context_loc, context_costume, action_text, filtered_tags):
            filtered_tags.append(tag)

    if not _has_physical_expression(filtered_tags):
        filtered_tags.insert(0, _fallback_physical_tag(category, rng))

    if len(filtered_tags) > max_items:
        filtered_tags = filtered_tags[:max_items]

    debug_log["final_tags"] = filtered_tags
    return filtered_tags
