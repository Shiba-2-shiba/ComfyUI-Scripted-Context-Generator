import json
import os
import re
import sys

def verify_locations():
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vocab/data/background_packs.json")
    if not os.path.exists(data_path):
        print("FAIL: background_packs.json not found.")
        return

    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} locations.")

    # Specific keys to check for "Richness"
    keys_to_check = ["school_classroom", "school_rooftop", "modern_office", "cyberpunk_street", "abandoned_shrine", "rainy_bus_stop"]
    
    score_total = 0
    
    for key in data:
        loc = data[key]
        label = loc.get("label", key)
        
        # Check environment richness
        envs = loc.get("environment", [])
        env_score = 0
        for e in envs:
            # Simple heuristic: lengthy descriptions with adjectives often have more spaces/words
            if len(e.split()) >= 4: 
                env_score += 1
            if any(adj in e for adj in ["sun-drenched", "windswept", "ancient", "neon", "dilapidated", "lonely", "opulent", "massive"]):
                env_score += 1
        
        # Check core richness
        cores = loc.get("core", [])
        core_score = 0
        for c in cores:
             if len(c.split()) >= 3:
                 core_score += 1

        print(f"[{key}] EnvScore={env_score}, CoreScore={core_score}")
        
        if key in keys_to_check:
            if env_score < 2 or core_score < 3:
                 print(f"  -> WARNING: {key} might need more detail.")
                 # Not strictly failing for quality warning
            else:
                 print(f"  -> OK: {key} seems rich.")

    # Check for new keys
    if "abandoned_shrine" in data:
        print("-> OK: New location 'abandoned_shrine' found.")
    else:
        print("-> FAIL: 'abandoned_shrine' missing.")

    if "rainy_bus_stop" in data:
         print("-> OK: New location 'rainy_bus_stop' found.")
    else:
         print("-> FAIL: 'rainy_bus_stop' missing.")

    new_keys = ["clean_modern_kitchen", "elegant_dining_room", "luxury_bathroom", "japanese_bath", "cozy_living_room",
                "rural_town_street", "suburban_neighborhood", "mountain_resort"]
    
    for nk in new_keys:
        if nk in data:
            print(f"-> OK: Requested location '{nk}' found.")
        else:
            print(f"-> FAIL: Requested location '{nk}' missing.")
            sys.exit(1)

if __name__ == "__main__":
    verify_locations()
