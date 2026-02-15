
import json
import pandas as pd
import os

def calc_variations():
    # Load compatibility combos
    try:
        df = pd.read_csv('assets/compatibility_review.csv')
    except Exception as e:
        print("Error loading CSV:", e)
        return

    # Load Action Pools
    try:
        with open('vocab/data/action_pools.json', 'r', encoding='utf-8') as f:
            pools = json.load(f)
    except Exception as e:
        print("Error loading action_pools:", e)
        return

    # 1. Base Combos (Char x Loc)
    base_combos = len(df)
    
    # 2. Actions per Combo
    # Map each csv row's 'canonical_loc' (or 'loc') to action pool count
    total_actions_variations = 0
    missing_pools = 0
    
    # Create alias map if needed, but CSV has canonical_loc
    # Let's check CSV columns
    use_col = 'canonical_loc' if 'canonical_loc' in df.columns else 'loc'

    for _, row in df.iterrows():
        loc = row[use_col]
        # Direct match or alias match?
        # action_pools keys are "canonical" usually.
        # But Phase 2 added aliases.
        # Let's check if loc exists in pools
        if loc in pools:
            action_count = len(pools[loc])
            total_actions_variations += action_count
        else:
            # Fallback or missing?
            # In Phase 2 we fixed aliases. But let's check.
            # Maybe it's in pools with a different name?
            # We'll assume mean(4) if missing for estimation
            missing_pools += 1
            total_actions_variations += 4

    # 3. Modifiers (Estimates based on typical prompt builder logic)
    # Lighting: Day, Night, Sunset, Morning -> 4
    # Weather: Sunny, Rainy, Cloudy, Snowy -> 4 (some constraints apply, e.g. indoor)
    # Camera: Wide, Close-up, Cowboy, etc. -> 3
    # Costume: Default + some variants? Costume is fixed per row in CSV usually? 
    # (CSV has 'costume' column). 
    # But some scripts might randomize costume colors/styles? 
    # Let's assume costume is fixed per combo for now (1).
    
    # Multipliers
    time_multiplier = 4
    weather_multiplier = 2 # Conservative (Indoor doesn't have weather, Outdoor does)
    camera_multiplier = 3 
    
    total_prompt_variations = total_actions_variations * time_multiplier * weather_multiplier * camera_multiplier

    print(f"--- Prompt Variation Estimate ---")
    print(f"Unique Characters: {df['subj'].nunique()}")
    print(f"Unique Locations: {df['loc'].nunique()}")
    print(f"Base Combinations (Char x Loc): {base_combos}")
    print(f"Total Action Variations (Char x Loc x Action): {total_actions_variations}")
    print(f"  - Missing Pools (Estimated 4 actions): {missing_pools}")
    print(f"Modifiers Estimate:")
    print(f"  - Time of Day: x{time_multiplier}")
    print(f"  - Weather (Avg): x{weather_multiplier}")
    print(f"  - Camera Angle: x{camera_multiplier}")
    print(f"===========================================")
    print(f"TOTAL ESTIMATED UNIQUE PROMPTS: {total_prompt_variations:,}")
    print(f"===========================================")

if __name__ == "__main__":
    calc_variations()
