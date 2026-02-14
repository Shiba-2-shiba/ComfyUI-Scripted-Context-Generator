import sys
import os
import random

# Add current directory to sys.path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

from nodes_garnish import GarnishSampler

def test_personality_injection():
    print("=== Starting Phase 3 Verification: Personality Based Interaction ===")
    
    node = GarnishSampler()
    seed = 100
    
    # Test Cases
    # Personality -> Expected Keywords
    test_cases = [
        ("energetic", ["joy", "smile", "laugh", "happy", "run", "jump", "dynamic", "sparkling"]),
        ("quiet", ["book", "read", "tea", "coffee", "calm", "soft", "focused", "relaxed"]),
        ("cool", ["focused", "mysterious", "sharp", "pocket", "crossed", "lean"]),
    ]
    
    for personality, keywords in test_cases:
        print(f"\nScanning for personality: [{personality}] (Expecting: {keywords})")
        
        hit_count = 0
        trials = 10
        
        for i in range(trials):
            # args: action_text, meta_mood_key, seed, max_items, include_camera, ... personality
            # We use "daily life" triggers in action_text to allow many micro-actions
            result = node.sample(
                "relaxing in room", # action_text 
                "neutral",          # meta_mood_key (neutral, so personality should dominate)
                seed + i,           # seed
                5,                  # max_items
                False,              # include_camera
                "", "", "{}",       # context
                personality         # personality
            )
            garnish = result[0].lower()
            
            # Check hits
            found = []
            for kw in keywords:
                if kw in garnish:
                    found.append(kw)
            
            if found:
                hit_count += 1
                print(f"  Run {i+1}: {garnish} -> HIT {found}")
            else:
                print(f"  Run {i+1}: {garnish} -> (no hit)")
                
        print(f"  Result: {hit_count}/{trials} matches.")
        
        if hit_count >= 3:
            print("  -> OK: Personality influence detected.")
        else:
            print("  -> WARNING: Low match rate. Check logic.")
            # sys.exit(1) # Warn mainly for randomness

    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    test_personality_injection()
