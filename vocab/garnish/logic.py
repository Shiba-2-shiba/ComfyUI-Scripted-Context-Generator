"""
Garnish logic module.
Re-implements the core logic for sampling garnish tags based on mood, action, and context.
"""
import random
import re
from typing import List, Dict, Optional, Any, Set

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

def _is_out_of_context(tag: str, context_loc: str, context_costume: str) -> bool:
    """
    Check if a tag conflicts with the current location or costume context.
    Placeholder implementation - can be expanded with specific rules.
    """
    return False

def _get_action_anchors(action_text: str) -> List[str]:
    """
    Identify micro-action concepts present in the action text.
    Returns a list of concept keys (e.g. 'read', 'drink').
    """
    if not action_text:
        return []
    
    found_concepts = []
    text_lower = action_text.lower()
    
    # Try to match concepts
    if isinstance(MICRO_ACTION_CONCEPTS, dict):
        for concept_key, data in MICRO_ACTION_CONCEPTS.items():
            if isinstance(data, dict):
                triggers = data.get("triggers", [])
                for trigger in triggers:
                    if trigger in text_lower:
                        found_concepts.append(concept_key)
                        break
            # Handle if MICRO_ACTION_CONCEPTS is simple dict or list (unlikely based on usage but safe)
    
    return found_concepts

def _resolve_micro_actions(concepts: List[str], mood: str, rng: random.Random) -> List[str]:
    """
    Resolve concept keys into specific tags suitable for the given mood.
    """
    tags = []
    if not isinstance(MICRO_ACTION_CONCEPTS, dict):
        return tags

    for concept in concepts:
        concept_data = MICRO_ACTION_CONCEPTS.get(concept)
        if not concept_data or not isinstance(concept_data, dict):
            continue
            
        variants = concept_data.get("variants", {})
        
        # 1. Try mood-specific variants
        candidates = variants.get(mood, [])
        
        # 2. Fallback to 'default' or 'neutral'
        if not candidates:
            candidates = variants.get("default", []) or variants.get("neutral", [])
            
        # 3. If still nothing, check if there's a generic list in 'tags' (if schema differs)
        if not candidates:
             candidates = concept_data.get("tags", [])

        if candidates and isinstance(candidates, list):
            tags.append(rng.choice(candidates))
            
    return tags

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
    debug_log: Dict = None
) -> List[str]:
    """
    Main entry point for generating garnish tags.
    """
    if debug_log is None:
        debug_log = {} # Mutating local ref only
        
    rng = random.Random(seed)
    
    mood_key = meta_mood.split("_")[0] if "_" in meta_mood else meta_mood
    
    # Validation of mood_key against MOOD_POOLS
    # If MOOD_POOLS doesn't have it, fallback
    if isinstance(MOOD_POOLS, dict) and mood_key not in MOOD_POOLS:
         mood_key = "neutral" 
         if "neutral" not in MOOD_POOLS and MOOD_POOLS: 
             mood_key = next(iter(MOOD_POOLS)) # Ultimate fallback
        
    debug_log["mood_resolved"] = mood_key
    
    garnish_pool = []
    
    # 1. Micro-Actions
    action_concepts = _get_action_anchors(action_text)
    # debug_log["action_concepts"] = action_concepts # caller might check this dict
    micro_action_tags = _resolve_micro_actions(action_concepts, mood_key, rng)
    garnish_pool.extend(micro_action_tags)
    
    # 2. Mood-based Atmosphere
    if isinstance(MOOD_POOLS, dict):
        mood_data = MOOD_POOLS.get(mood_key, {})
        if isinstance(mood_data, list):
             garnish_pool.extend(rng.sample(mood_data, min(len(mood_data), 2)))
        elif isinstance(mood_data, dict):
            emotions = mood_data.get("emotions", [])
            if emotions: garnish_pool.append(rng.choice(emotions))
            
            effects = mood_data.get("effects", [])
            if effects: garnish_pool.append(rng.choice(effects))
    
    # 3. Camera (Optional)
    if include_camera:
        if VIEW_FRAMING and isinstance(VIEW_FRAMING, list) and rng.random() > 0.5:
            garnish_pool.append(rng.choice(VIEW_FRAMING))
        if VIEW_ANGLES and isinstance(VIEW_ANGLES, list) and rng.random() > 0.5:
            garnish_pool.append(rng.choice(VIEW_ANGLES))

    # 4. Global Effects
    if mood_key in ["energetic", "joyful", "happy"]:
         if EFFECTS_BRIGHT and isinstance(EFFECTS_BRIGHT, list): garnish_pool.append(rng.choice(EFFECTS_BRIGHT))
    elif mood_key in ["dark", "gloom", "sad"]:
         if EFFECTS_DARK and isinstance(EFFECTS_DARK, list): garnish_pool.append(rng.choice(EFFECTS_DARK))
    else:
         if EFFECTS_UNIVERSAL and isinstance(EFFECTS_UNIVERSAL, list) and rng.random() > 0.7:
             garnish_pool.append(rng.choice(EFFECTS_UNIVERSAL))

    # 5. Pose Adjustments
    if not action_text:
        # Pick a base pose
        all_poses = []
        if isinstance(POSE_STANDING, list): all_poses.extend(POSE_STANDING)
        if isinstance(POSE_SITTING, list): all_poses.extend(POSE_SITTING)
        if isinstance(POSE_LYING, list): all_poses.extend(POSE_LYING)
        
        if all_poses:
            garnish_pool.append(rng.choice(all_poses))
            
    if rng.random() > 0.7 and HAND_GESTURES and isinstance(HAND_GESTURES, list):
         garnish_pool.append(rng.choice(HAND_GESTURES))
    if rng.random() > 0.8 and EYES_BASE and isinstance(EYES_BASE, list):
         garnish_pool.append(rng.choice(EYES_BASE))

    rng.shuffle(garnish_pool)
    final_tags = _dedupe(garnish_pool)
    
    # ensure max_items
    if len(final_tags) > max_items:
        final_tags = final_tags[:max_items]

    # debug_log["final_tags"] = final_tags
    return final_tags
