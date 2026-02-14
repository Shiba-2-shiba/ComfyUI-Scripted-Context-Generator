import json
import os
import sys

import test_bootstrap  # noqa: F401 — パッケージコンテキストを自動解決

import background_vocab
import clothing_vocab
import improved_pose_emotion_vocab

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
        loc_key = loc.lower().strip()
        if loc_key and loc_key not in background_vocab.LOC_TAG_MAP:
            missing_locs.add(loc_key)

        # Costume Check
        # Normalize: key lookup in THEME_TO_PACKS
        theme_key = costume.lower().strip()
        # The node has an alias_map, but we should check if the key translates to a valid pack map
        # Ideally, we check if it is in THEME_TO_PACKS directly or via alias
        # For this lint, let's check basic existence in THEME_TO_PACKS
        if theme_key and theme_key not in clothing_vocab.THEME_TO_PACKS:
             # Basic check failed, but maybe it's in the alias map inside the node?
             # Since we can't easily access the internal alias_map of the class instance without instantiating,
             # we will just warn for now.
             missing_costumes.add(theme_key)

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
    
    banned_words = ["meta_style", "art style", "illustration", "oil painting", "digital art"]
    
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
                    for bw in banned_words:
                        if bw in item.lower():
                             # Exception: "art museum", "art gallery"
                             if "art" in bw and ("museum" in item.lower() or "gallery" in item.lower()):
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
    def emotion_token(mood_key: str) -> str:
        parts = mood_key.lower().split("_")
        return parts[-1] if parts else mood_key.lower()

    emotion_tokens = sorted({emotion_token(m) for m in moods if m})
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
    anchor_words = ["sitting","standing","walking","running","lying","sleeping","holding", "wearing", "carrying"] # Expanded slightly? No keep original for fidelity
    # Original: ["sitting","standing","walking","running","lying","sleeping","holding"]
    anchor_words = ["sitting","standing","walking","running","lying","sleeping","holding"]
    
    actions = [p.get("action", "") for p in prompts]
    anchor_missing = []
    for a in actions:
        if not a: continue
        t = a.lower()
        if not any(w in t for w in anchor_words):
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
