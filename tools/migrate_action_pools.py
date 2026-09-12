import json
import os
import sys

# Schema Design (v1.0) definitions
# Calm: Passive, low energy (sitting, reading, sleeping, waiting).
# Active: Physical movement, high energy (running, dancing, fighting, sports).
# Tense: Stressful, serious context (fighting, arguing, sneaking).
# Intimate: Personal, close proximity (hugging, holding hands, bedroom contexts).

def guess_load(action_text):
    text = action_text.lower()
    
    # Intimate keywords
    if any(w in text for w in ["hugging", "holding hands", "kissing", "cuddling", "bed", "bedroom", "bath", "soaking"]):
        return "intimate"
        
    # Tense keywords
    if any(w in text for w in ["fighting", "arguing", "hiding", "sneaking", "battle", "danger", "crying", "scared", "frustration", "rage"]):
        return "tense"
        
    # Active keywords
    if any(w in text for w in ["running", "walking", "dancing", "jumping", "flying", "playing", "cleaning", "cooking", "sweeping", "exercising", "lifting"]):
        return "active"
        
    # Calm triggers (default fallback is also calm)
    if any(w in text for w in ["sitting", "standing", "lying", "reading", "sleeping", "waiting", "looking", "watching", "listening"]):
        return "calm"
        
    return "calm" # Default

def migrate():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_file = os.path.join(base_dir, "vocab", "data", "action_pools.json")
    
    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    new_data = {"_comment": data.get("_comment", ""), "schema_version": "2.0"}
    
    for key, actions in data.items():
        if key.startswith("_") or key == "schema_version":
            continue
            
        new_actions = []
        for action in actions:
            if isinstance(action, dict):
                # Already migrated or manually set
                new_actions.append(action)
            elif isinstance(action, str):
                load = guess_load(action)
                new_actions.append({
                    "text": action,
                    "load": load
                })
        
        new_data[key] = new_actions
        
    # Write back
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=4, ensure_ascii=False)
        
    print(f"Migrated action_pools.json to schema 2.0. Saved to {target_file}")

if __name__ == "__main__":
    migrate()
