import os
import sys
import json
import time
from collections import Counter
import random

# Add parent directory to path to allow importing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from vocab.garnish import logic as garnish_logic
except ImportError:
    print("Could not import vocab.garnish.logic. Trying simple import...")
    try:
        import improved_pose_emotion_vocab as garnish_logic
    except ImportError:
        print("Failed to import garnish logic.")
        sys.exit(1)

# Baseline Configuration
SEEDS = [123, 456, 789, 101112, 131415, 999, 888, 777, 666, 555]
MOODS = [
    "energetic_joy",
    "whimsical_playful",
    "intense_anger",
    "melancholic_sadness",
    "peaceful_relaxed"
]

# Representative actions
ACTIONS = [
    "standing",  # Neutral/Passive
    "sitting",   # Neutral/Passive
    "fighting",  # Active/Tense (Simulated, might not be in pools but good for test)
    "dancing",   # Active/Joyful
    "eating"     # Daily/Relaxed
]

NEUTRAL_KEYWORDS = [
    "neutral", "stoic", "calm", "composed", "expressionless", "looking straight ahead"
]

def run_baseline():
    results = {
        "timestamp": time.strftime("%Y%m%d-%H%M%S"),
        "config": {
            "moods": MOODS,
            "actions": ACTIONS,
            "seed_count": len(SEEDS)
        },
        "data": {},
        "summary": {}
    }

    all_tags = []
    neutral_count = 0
    total_tags_count = 0

    for mood_key in MOODS:
        results["data"][mood_key] = {}
        
        for action in ACTIONS:
            action_key = action.replace(" ", "_").lower()
            results["data"][mood_key][action_key] = {
                "tags": [],
                "seeds": {}
            }
            
            for seed in SEEDS:
                # Call sample_garnish
                tags = garnish_logic.sample_garnish(
                    seed=seed,
                    meta_mood=mood_key,
                    action_text=action,
                    max_items=3,
                    include_camera=False
                )
                
                results["data"][mood_key][action_key]["seeds"][seed] = tags
                results["data"][mood_key][action_key]["tags"].extend(tags)
                all_tags.extend(tags)
                
                # Check for neutral keywords
                for tag in tags:
                    tag_lower = tag.lower()
                    if any(nk in tag_lower for nk in NEUTRAL_KEYWORDS):
                        neutral_count += 1
                    total_tags_count += 1

    # Frequency analysis
    results["summary"]["tag_frequency"] = dict(Counter(all_tags).most_common(50))
    results["summary"]["total_samples"] = len(MOODS) * len(ACTIONS) * len(SEEDS)
    results["summary"]["total_tags_generated"] = total_tags_count
    results["summary"]["neutral_ratio"] = neutral_count / total_tags_count if total_tags_count > 0 else 0
    
    # Save results
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "results")
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"baseline_{results['timestamp']}.json"
    output_path = os.path.join(output_dir, filename)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Baseline measurement complete. Saved to {output_path}")
    print(f"Neutral Ratio: {results['summary']['neutral_ratio']:.2%}")
    print(f"Top 5 Tags: {dict(Counter(all_tags).most_common(5))}")

    return output_path

if __name__ == "__main__":
    run_baseline()
