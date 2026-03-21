import json
import os
import re
import sys

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
if ASSETS_DIR not in sys.path:
    sys.path.insert(0, ASSETS_DIR)
ROOT = os.path.dirname(ASSETS_DIR)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import test_bootstrap  # noqa: F401 — パッケージコンテキストを自動解決

import background_vocab
import clothing_vocab
import improved_pose_emotion_vocab
from registry import resolve_clothing_theme, resolve_location_key

try:
    from vocab.garnish.logic import LEGACY_MAP
except ImportError:
    LEGACY_MAP = {}

def check_referential_integrity():
    print("--- Checking Referential Integrity ---")
    prompts_path = "prompts.jsonl"
    if not os.path.exists(prompts_path):
        print(f"[Skip] {prompts_path} not found.")
        return

    # Load prompts
    prompts = []
    with open(prompts_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                prompts.append(json.loads(line))

    # Check matches
    missing_locs = set()
    missing_costumes = set()

    for p in prompts:
        loc = p.get("loc_tag", "") or p.get("loc", "")
        costume = p.get("costume_key", "") or p.get("costume", "")
        
        # Loc Check
        # Normalize as the node does: lower().strip()
        raw_loc_key = loc.lower().strip()
        loc_key = resolve_location_key(raw_loc_key)
        if loc and not loc_key:
            missing_locs.add(raw_loc_key)

        # Costume Check
        # Normalize: key lookup in THEME_TO_PACKS
        theme_key = resolve_clothing_theme(costume.lower().strip())
        if costume and not theme_key:
             missing_costumes.add(costume.lower().strip())

    if missing_locs:
        print(f"[FAIL] Prompts use locations not in LOC_TAG_MAP: {missing_locs}")
    else:
        print("[PASS] All location tags in prompts are valid.")

    if missing_costumes:
        print(f"[WARN] Prompts use costumes not in THEME_TO_PACKS (might be aliases): {missing_costumes}")
    else:
        print("[PASS] All costume keys look valid.")

def check_vocab_cleanliness():
    print("\n--- Checking Vocab Cleanliness ---")
    
    banned_patterns = {
        "meta_style": re.compile(r"\bmeta_style\b"),
        "art style": re.compile(r"\bart style\b"),
        "illustration": re.compile(r"\billustration\b"),
        "oil painting": re.compile(r"\boil painting\b"),
        "digital art": re.compile(r"\bdigital art\b"),
        "film grain": re.compile(r"\bfilm grain\b"),
        "ambient occlusion": re.compile(r"\bambient occlusion\b"),
        "volumetric lighting": re.compile(r"\bvolumetric lighting\b"),
        "bloom": re.compile(r"\bbloom\b"),
        "light leaks": re.compile(r"\blight leaks\b"),
        "prismatic light leaks": re.compile(r"\bprismatic light leaks\b"),
        "chromatic aberration": re.compile(r"\bchromatic aberration\b"),
    }
    
    def check_obj(obj, name, path=""):
        violations = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                violations.extend(check_obj(v, name, path=f"{path}.{k}"))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, str):
                    # Empty check
                    if not item.strip():
                        violations.append(f"{path}[{i}] is empty/whitespace")
                    
                    # Banned check
                    item_lower = item.lower()
                    for bw, pat in banned_patterns.items():
                        if pat.search(item_lower):
                             # Exception: "art museum", "art gallery"
                             if "art" in bw and ("museum" in item_lower or "gallery" in item_lower):
                                 continue
                             violations.append(f"{path}[{i}] contains banned '{bw}': '{item}'")
                else:
                    violations.extend(check_obj(item, name, path=f"{path}[{i}]"))
        return violations

    # Check background_vocab
    v1 = check_obj(background_vocab.CONCEPT_PACKS, "background_vocab", "background_vocab.CONCEPT_PACKS")
    
    # Check improved_pose_emotion_vocab
    v2 = check_obj(improved_pose_emotion_vocab.MICRO_ACTION_CONCEPTS, "pose_vocab", "MICRO_ACTION_CONCEPTS")
    v2.extend(check_obj(improved_pose_emotion_vocab.MOOD_POOLS, "pose_vocab", "MOOD_POOLS"))
    
    all_violations = v1 + v2

    allow_dirty_packs = {
        "rainy_alley",
        "cyberpunk_street",
        "burning_battlefield",
        "alien_planet",
        "dragon_lair",
        "abandoned_shrine",
    }

    for pack_name, pack_data in background_vocab.CONCEPT_PACKS.items():
        if pack_name in allow_dirty_packs:
            continue
        for field in ("core", "props", "fx"):
            for item in pack_data.get(field, []):
                low = str(item).lower()
                if "trash" in low or "debris" in low:
                    all_violations.append(
                        f"background_vocab.CONCEPT_PACKS.{pack_name}.{field} contains unwanted noun: '{item}'"
                    )

    prompts_path = os.path.join("vocab", "data", "action_pools.json")
    if os.path.exists(prompts_path):
        with open(prompts_path, "r", encoding="utf-8") as f:
            action_pools = json.load(f)
        for loc, items in action_pools.items():
            if loc.startswith("_") or loc == "schema_version":
                continue
            for idx, item in enumerate(items):
                text = item.get("text", "") if isinstance(item, dict) else str(item)
                low = text.lower()
                if "imaginary" in low:
                    all_violations.append(
                        f"action_pools.{loc}[{idx}] contains banned 'imaginary': '{text}'"
                    )
                if loc not in allow_dirty_packs and ("trash" in low or "debris" in low):
                    all_violations.append(
                        f"action_pools.{loc}[{idx}] contains unwanted noun: '{text}'"
                    )

    if all_violations:
        print(f"[FAIL] Found {len(all_violations)} vocab violations:")
        for v in all_violations[:10]:
            print(f"  - {v}")
        if len(all_violations) > 10: print("  ... and more")
    else:
        print("[PASS] Vocab cleanliness check passed.")



def check_extended_rules():
    print("\n--- Checking Extended Rules (Merged from test.py) ---")
    
    # Setup paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mood_map_path = os.path.join(base_dir, "mood_map.json")
    prompts_path = os.path.join(base_dir, "prompts.jsonl")

    if not os.path.exists(mood_map_path):
        print(f"[Skip] {mood_map_path} not found.")
        return
        
    # Load Data
    with open(mood_map_path, "r", encoding="utf-8") as f:
        mood_map = json.load(f)
        
    prompts = []
    if os.path.exists(prompts_path):
        with open(prompts_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        prompts.append(json.loads(line))
                    except json.JSONDecodeError:
                        print(f"[WARN] Failed to parse JSON line in prompts.jsonl: {line[:50]}...")
    
    # 1. Mood Map Consistency
    moods = sorted({p.get("meta", {}).get("mood", "") for p in prompts if p.get("meta")})
    missing_mood = [m for m in moods if m and m not in mood_map]
    
    if missing_mood:
        print(f"[FAIL] Prompts use moods not in mood_map.json: {missing_mood}")
    else:
        print("[PASS] All prompt moods exist in mood_map.json")

    # 2. Emotion Pool Coverage
    # Check if the 'emotion' part of the mood tag (e.g. 'surreal_dream_blue' -> 'blue'?? No, logic was split('_')[-1])
    # test.py logic: parts = mood_key.lower().split("_"); return parts[-1]
    def normalize_emotion_token(mood_key: str) -> str:
        key = mood_key.lower().strip()
        if key in LEGACY_MAP:
            return LEGACY_MAP[key][0]
        parts = [part for part in key.split("_") if part]
        if parts and parts[0] in getattr(improved_pose_emotion_vocab, "MOOD_POOLS", {}):
            return parts[0]
        return key

    emotion_tokens = sorted({normalize_emotion_token(m) for m in moods if m})
    # MOOD_POOLS is in improved_pose_emotion_vocab
    # We need to access MOOD_POOLS. In test.py it was import improved_pose_emotion_vocab as garnish_vocab
    # In this file it is imported as improved_pose_emotion_vocab
    
    # Note: improved_pose_emotion_vocab might not expose MOOD_POOLS directly if not in __all__? 
    # Let's check imports. test_vocab_lint imports it as improved_pose_emotion_vocab.
    
    if hasattr(improved_pose_emotion_vocab, 'MOOD_POOLS'):
        pools = improved_pose_emotion_vocab.MOOD_POOLS
        missing_emotion_pool = [e for e in emotion_tokens if e not in pools]
        
        if missing_emotion_pool:
            # This is often strict, maybe just WARN
            print(f"[WARN] Mood suffixes (emotions) not found in MOOD_POOLS: {missing_emotion_pool}")
        else:
            print("[PASS] All mood suffixes map to an Emotion Pool")
    else:
        print("[SKIP] improved_pose_emotion_vocab.MOOD_POOLS not found")

    # 3. Anchor Check
    anchor_words = {
        "browsing",
        "checking",
        "comparing",
        "dancing",
        "gripping",
        "holding",
        "kneeling",
        "leaning",
        "lying",
        "moving",
        "organizing",
        "pausing",
        "pinning",
        "resting",
        "reviewing",
        "running",
        "settling",
        "singing",
        "sitting",
        "slipping",
        "sorting",
        "staying",
        "standing",
        "stretching",
        "walking",
        "watching",
        "working",
    }
    
    actions = [p.get("action", "") for p in prompts]
    anchor_missing = []
    for a in actions:
        if not a: continue
        words = re.findall(r"[A-Za-z']+", a.lower())
        first_word = words[0] if words else ""
        if first_word not in anchor_words:
            anchor_missing.append(a)
            
    if anchor_missing:
        print(f"[INFO] {len(anchor_missing)} actions do not contain basic anchors (sitting/standing/etc). Examples:")
        for m in anchor_missing[:5]:
            print(f"  - {m}")
    else:
        print("[PASS] All actions contain basic anchor verbs")

if __name__ == "__main__":
    check_referential_integrity()

    check_vocab_cleanliness()
    check_extended_rules()
