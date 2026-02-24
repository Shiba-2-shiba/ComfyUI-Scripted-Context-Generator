"""
Garnish logic module (v2.0).
Implements Action-consistent sampling with 9 emotion categories and intensity levels.
"""
import random
import re
from typing import List, Dict, Optional, Any, Set, Tuple

from .utils import normalize, _dedupe, _merge_unique
from .base_vocab import (
    MOOD_POOLS,
    VIEW_ANGLES,
    VIEW_FRAMING,
    POSE_STANDING,
    POSE_SITTING,
    POSE_LYING,
    POSE_DYNAMIC,
    HAND_POSITIONS,
    HAND_GESTURES,
    EYES_BASE,
    MOUTH_BASE,
    EFFECTS_UNIVERSAL,
    EFFECTS_BRIGHT,
    EFFECTS_DARK,
    EFFECTS_DYNAMIC,
)
from .micro_actions import MICRO_ACTION_CONCEPTS, EXCLUSIVE_TAG_GROUPS

# -------------------------------------------------------------------------
# Constants & Configuration
# -------------------------------------------------------------------------

EMOTION_CATEGORIES = [
    "joy", "playful", "anger", "sadness", "relax", "focus", "care", "impatience", "moved"
]

INTENSITIES = ["mild", "medium", "strong"]

# Action Load Keywords
LOAD_KEYWORDS = {
    "intimate": ["hugging", "holding hands", "kissing", "cuddling", "bed", "bedroom", "bath", "soaking"],
    "tense": ["fighting", "arguing", "hiding", "sneaking", "battle", "danger", "crying", "scared", "frustration", "rage"],
    "active": ["running", "walking", "dancing", "jumping", "flying", "playing", "cleaning", "cooking", "sweeping", "exercising", "lifting"],
    "calm": ["sitting", "standing", "lying", "reading", "sleeping", "waiting", "looking", "watching", "listening"] # Fallback
}

# Compatibility Matrix (Emotion vs Load)
# True = Allowed, False = Forbidden (simplified from O/△/X for logic)
# We can restrain intensity separately if needed.
COMPATIBILITY = {
    "calm":       {"joy","playful","anger","sadness","relax","focus","care","impatience","moved"},
    "active":     {"joy","playful","anger","focus","impatience"}, # sadness/relax/care/moved restricted
    "tense":      {"anger","focus","impatience"}, # joy/playful/relax/care/moved/sadness restricted (sadness maybe ok but let's restrict for consistency)
    "intimate":   {"joy","playful","sadness","relax","moved","care"} # anger/focus/impatience restricted
}

# Legacy Mapping
LEGACY_MAP = {
    "energetic_joy": ("joy", "strong"),
    "whimsical_playful": ("playful", "medium"),
    "intense_anger": ("anger", "strong"),
    "melancholic_sadness": ("sadness", "medium"),
    "peaceful_relaxed": ("relax", "medium"),
    # "neutral": ("relax", "mild"), # Removed to allow auto-sampling
    "energetic": ("joy", "medium"),
    "whimsical": ("playful", "mild"),
    "intense": ("anger", "medium"),
    "melancholic": ("sadness", "mild"),
    "peaceful": ("relax", "mild"),
}

# Personality -> Garnish Bias Mapping
# prefer: tags added first (random selection if multiple)
# avoid_pools: pool names to exclude one tag from
# prefer_category: emotion category bias if no specific meta_mood
PERSONALITY_GARNISH_BIAS: Dict[str, Dict] = {
    "shy": {
        "prefer": ["looking away", "looking down", "downcast eyes",
                   "fidgeting", "cheeks flushed"],
        "avoid_pools": ["POSE_DYNAMIC", "EFFECTS_BRIGHT"],
        "prefer_category": "care",
    },
    "confident": {
        "prefer": ["looking at viewer", "chin up", "hands on hips"],
        "avoid_pools": [],
        "prefer_category": "joy",
    },
    "energetic": {
        "prefer": ["dynamic pose", "bright smile", "pumping fist"],
        "avoid_pools": [],
        "prefer_category": "joy",
    },
    "gloomy": {
        "prefer": ["downcast eyes", "distant gaze", "slouched"],
        "avoid_pools": ["EFFECTS_BRIGHT"],
        "prefer_category": "sadness",
    },
    "faithful": {
        "prefer": ["gentle smile", "clasped hands", "warm gaze"],
        "avoid_pools": [],
        "prefer_category": "care",
    },
    "aggressive": {
        "prefer": ["sharp gaze", "clenched fists", "glaring"],
        "avoid_pools": ["EFFECTS_BRIGHT"],
        "prefer_category": "anger",
    },
    "mysterious": {
        "prefer": ["sideways glance", "half-turned", "shadowed face"],
        "avoid_pools": ["EFFECTS_BRIGHT"],
        "prefer_category": "focus",
    },
    "cheerful": {
        "prefer": ["beaming smile", "eyes closed happy", "hands waving"],
        "avoid_pools": ["EFFECTS_DARK"],
        "prefer_category": "playful",
    },
    "serious": {
        "prefer": ["focused gaze", "firm expression", "arms crossed"],
        "avoid_pools": [],
        "prefer_category": "focus",
    },
    "gentle": {
        "prefer": ["soft smile", "gentle eyes", "open palms"],
        "avoid_pools": ["POSE_DYNAMIC", "EFFECTS_DARK"],
        "prefer_category": "care",
    },
    "neutral": {
        "prefer": [],
        "avoid_pools": [],
        "prefer_category": None,
    },
    "": {
        "prefer": [],
        "avoid_pools": [],
        "prefer_category": None,
    },
}

# Pool name -> actual list (for avoid_pools lookup)
_POOL_NAME_MAP: Dict[str, str] = {
    "POSE_DYNAMIC":   "POSE_DYNAMIC",
    "EFFECTS_BRIGHT": "EFFECTS_BRIGHT",
    "EFFECTS_DARK":   "EFFECTS_DARK",
    "EFFECTS_DYNAMIC": "EFFECTS_DYNAMIC",
    "EYES_BASE":      "EYES_BASE",
    "HAND_GESTURES":  "HAND_GESTURES",
}


# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------

def _guess_action_load(action_text: str) -> str:
    """Determine the emotional load of an action."""
    if not action_text:
        return "calm"
    
    text = action_text.lower()
    
    for k in LOAD_KEYWORDS["intimate"]:
        if k in text: return "intimate"
    for k in LOAD_KEYWORDS["tense"]:
        if k in text: return "tense"
    for k in LOAD_KEYWORDS["active"]:
        if k in text: return "active"
    
    return "calm"

def _is_compatible(category: str, load: str) -> bool:
    """Check if category is allowed for the load."""
    allowed = COMPATIBILITY.get(load, COMPATIBILITY["calm"])
    return category in allowed

def _select_category_weighted(load: str, rng: random.Random) -> str:
    """
    Select an emotion category based on load and weights.
    Goal: Joy/Playful dominance where possible.
    """
    allowed = COMPATIBILITY.get(load, COMPATIBILITY["calm"])
    
    # Custom weights logic
    weights = {}
    
    if load == "tense":
        # Tense situation: Anger/Focus/Impatience dominance
        weights = {"anger": 40, "focus": 30, "impatience": 30}
    else:
        # Balanced dominance for Positive/Neutral (Total ~90%)
        # Joy, Playful, Relax, Focus, Care, Moved -> ~15% each
        weights["joy"] = 15
        weights["playful"] = 15
        weights["relax"] = 15
        weights["focus"] = 15
        weights["care"] = 15
        weights["moved"] = 15
        
        # Low frequency for Negative (Total ~10%)
        # Anger, Sadness, Impatience -> ~3-4% each
        weights["anger"] = 3
        weights["sadness"] = 3
        weights["impatience"] = 4

    # Filter by allowed and flatten
    valid_cats = []
    valid_weights = []
    
    for cat, w in weights.items():
        if cat in allowed:
            valid_cats.append(cat)
            valid_weights.append(w)
            
    if not valid_cats:
        return "focus" # Fallback
        
    return rng.choices(valid_cats, weights=valid_weights, k=1)[0]

def _resolve_target_emotion(meta_mood: str, load: str, rng: random.Random, log: Dict) -> Tuple[str, str]:
    """
    Resolve (Category, Intensity).
    Honors meta_mood if compatible, else samples new.
    """
    category = "relax"
    intensity = "mild"
    
    # 1. Parse Input
    req_cat = None
    req_int = None
    
    # Normalize input
    m = meta_mood.lower().replace(" ", "_")
    
    # Check legacy
    if m in LEGACY_MAP:
        req_cat, req_int = LEGACY_MAP[m]
    elif "_" in m:
        # Try to parse "joy_strong"
        parts = m.split("_")
        if parts[0] in EMOTION_CATEGORIES:
            req_cat = parts[0]
            if len(parts) > 1 and parts[1] in INTENSITIES:
                req_int = parts[1]
    elif m in EMOTION_CATEGORIES:
        req_cat = m
        
    # 2. Compatibility Check
    is_valid_request = False
    if req_cat:
        if _is_compatible(req_cat, load):
            is_valid_request = True
            category = req_cat
            # If intensity not specified, sample?
            if not req_int:
               req_int = rng.choice(INTENSITIES)
            intensity = req_int
        else:
            log["mood_conflict"] = f"Requested {req_cat} incompatible with {load}"
            
    # 3. Sampling (if no valid request)
    if not is_valid_request:
        if req_cat and not _is_compatible(req_cat, load):
             # Was specific but forbidden -> Sampling new
             pass 
        elif m in ["neutral", "random", "", "auto"]:
             # Explicitly asking for auto
             pass
        else:
             # Unknown key, treat as auto
             pass
             
        category = _select_category_weighted(load, rng)
        intensity = rng.choice(INTENSITIES) # Random intensity for now
        
        # Adjustment for Joy/Playful: bias towards mild/medium for calm actions?
        # Let's keep it simple random for intensity for now, ensuring variety.
        
    # 4. Final adjustments
    # If intensity missing in data, fallback will happen in sampling phrase
    
    log["res_category"] = category
    log["res_intensity"] = intensity
    return category, intensity

# -------------------------------------------------------------------------
# Main Logic
# -------------------------------------------------------------------------

def _get_action_anchors(action_text: str) -> List[str]:
    """Identify micro-action concepts."""
    if not action_text:
        return []
    found = []
    text_lower = action_text.lower()
    if isinstance(MICRO_ACTION_CONCEPTS, dict):
        for k, data in MICRO_ACTION_CONCEPTS.items():
            if isinstance(data, dict):
                for trig in data.get("triggers", []):
                    if trig in text_lower:
                        found.append(k); break
    return found

def _resolve_micro_actions(concepts: List[str], mood: str, rng: random.Random) -> List[str]:
    """Resolve micro-action tags."""
    tags = []
    if not isinstance(MICRO_ACTION_CONCEPTS, dict): return tags
    for concept in concepts:
        c_data = MICRO_ACTION_CONCEPTS.get(concept)
        if not c_data or not isinstance(c_data, dict): continue
        variants = c_data.get("variants", {})
        cand = variants.get(mood, []) or variants.get("default", []) or variants.get("neutral", []) or c_data.get("tags", [])
        if cand and isinstance(cand, list): tags.append(rng.choice(cand))
    return tags

def _is_out_of_context(tag: str, context_loc: str, context_costume: str) -> bool:
    """
    Check if a tag conflicts with the current location or costume context.
    Placeholder implementation - can be expanded with specific rules.
    """
    return False

def sample_garnish(
    seed: int,
    meta_mood: str,
    action_text: str = "",
    max_items: int = 3,
    include_camera: bool = False,
    context_loc: str = "",
    context_costume: str = "",
    scene_tags: Dict = None,
    personality: str = "",
    emotion_nuance: str = "",
    debug_log: Dict = None
) -> List[str]:
    
    if debug_log is None: debug_log = {}
    rng = random.Random(seed)
    
    # 1. Determine Context
    action_load = _guess_action_load(action_text)
    debug_log["action_load"] = action_load
    
    # 2. Resolve Emotion
    category, intensity = _resolve_target_emotion(meta_mood, action_load, rng, debug_log)
    
    garnish_pool = []

    # 2a. Emotion Nuance Bias (from scene_axis.json)
    # Load emotion_nuance data lazily to avoid circular imports
    if emotion_nuance:
        import os as _os, json as _json
        _data_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(
            _os.path.abspath(__file__)))), "vocab", "data")
        _scene_axis_path = _os.path.join(_data_dir, "scene_axis.json")
        try:
            with open(_scene_axis_path, encoding="utf-8") as _f:
                _axis = _json.load(_f)
            _en_data = _axis.get("emotion_nuance", {}).get(emotion_nuance.lower(), {})
            _en_bias = _en_data.get("garnish_bias", [])
            if _en_bias:
                chosen_en = rng.choice(_en_bias)
                garnish_pool.append(chosen_en)
                debug_log["emotion_nuance_tag"] = chosen_en
        except Exception as _e:
            debug_log["emotion_nuance_error"] = str(_e)

    # 3. Fetch Emotion Tags
    # Verify structure of MOOD_POOLS
    if isinstance(MOOD_POOLS, dict):
        cat_data = MOOD_POOLS.get(category)
        if isinstance(cat_data, dict):
            # New Schema: dict of intensities
            int_tags = cat_data.get(intensity, [])
            if not int_tags:
                # Fallback to any intensity
                all_tags = []
                for v in cat_data.values():
                    if isinstance(v, list): all_tags.extend(v)
                if all_tags: garnish_pool.extend(rng.sample(all_tags, min(len(all_tags), 2)))
            else:
                garnish_pool.extend(rng.sample(int_tags, min(len(int_tags), 2)))
        elif isinstance(cat_data, list):
            # Legacy Schema support (should not happen if migrated, but safe)
            garnish_pool.extend(rng.sample(cat_data, min(len(cat_data), 2)))
            
    # 4. Micro Actions
    anchors = _get_action_anchors(action_text)
    ma_tags = _resolve_micro_actions(anchors, category, rng) # Use category as mood key
    garnish_pool.extend(ma_tags)
    
    # 5. Global Effects (Simplified)
    # Bright: joy, playful, care, moved
    # Dark: anger, sadness, impatience
    # Neutral: relax, focus
    if category in ["joy", "playful", "care", "moved"]:
        if EFFECTS_BRIGHT and isinstance(EFFECTS_BRIGHT, list): garnish_pool.append(rng.choice(EFFECTS_BRIGHT))
    elif category in ["anger", "sadness", "impatience"]:
        if EFFECTS_DARK and isinstance(EFFECTS_DARK, list): garnish_pool.append(rng.choice(EFFECTS_DARK))
    else:
        if EFFECTS_UNIVERSAL and isinstance(EFFECTS_UNIVERSAL, list) and rng.random() > 0.7:
             garnish_pool.append(rng.choice(EFFECTS_UNIVERSAL))

    # 6. Camera
    if include_camera:
        if VIEW_FRAMING and isinstance(VIEW_FRAMING, list) and rng.random() > 0.5:
            garnish_pool.append(rng.choice(VIEW_FRAMING))
        if VIEW_ANGLES and isinstance(VIEW_ANGLES, list) and rng.random() > 0.5:
             garnish_pool.append(rng.choice(VIEW_ANGLES))
             
    # 7. Pose (if no action text)
    if not action_text:
        all_poses = []
        if isinstance(POSE_STANDING, list): all_poses.extend(POSE_STANDING)
        if isinstance(POSE_SITTING, list): all_poses.extend(POSE_SITTING)
        if all_poses: garnish_pool.append(rng.choice(all_poses))
        
    # 8. Extra (Eyes/Hands) - Only if pool is small
    if len(garnish_pool) < max_items:
         if rng.random() > 0.7 and HAND_GESTURES: garnish_pool.append(rng.choice(HAND_GESTURES))
         if rng.random() > 0.8 and EYES_BASE: garnish_pool.append(rng.choice(EYES_BASE))

    rng.shuffle(garnish_pool)
    final_tags = _dedupe(garnish_pool)

    # 9. Personality Bias
    if personality:
        p_key = personality.lower().strip()
        bias = PERSONALITY_GARNISH_BIAS.get(p_key)
        if bias is None:
            # Unknown personality: no-op
            bias = PERSONALITY_GARNISH_BIAS[""]

        # 9a. Remove tags from avoid_pools
        if bias.get("avoid_pools"):
            pool_map = {
                "POSE_DYNAMIC":   POSE_DYNAMIC,
                "EFFECTS_BRIGHT": EFFECTS_BRIGHT,
                "EFFECTS_DARK":   EFFECTS_DARK,
                "EFFECTS_DYNAMIC": EFFECTS_DYNAMIC,
                "EYES_BASE":      EYES_BASE,
                "HAND_GESTURES":  HAND_GESTURES,
            }
            avoid_tags: Set[str] = set()
            for pool_name in bias["avoid_pools"]:
                pool = pool_map.get(pool_name, [])
                if isinstance(pool, list):
                    avoid_tags.update(pool)
            final_tags = [t for t in final_tags if t not in avoid_tags]

        # 9b. Prepend prefer tags (pick 1 randomly)
        prefer = bias.get("prefer", [])
        if prefer and len(final_tags) < max_items:
            chosen = rng.choice(prefer)
            if chosen not in final_tags:
                final_tags.insert(0, chosen)

    if len(final_tags) > max_items:
        final_tags = final_tags[:max_items]

    return final_tags
