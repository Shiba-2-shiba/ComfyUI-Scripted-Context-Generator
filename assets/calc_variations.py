import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

# ------------------------------------------------------------------------------
# Helpers (Zero Dependency)
# ------------------------------------------------------------------------------
def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {path}", file=sys.stderr)
        return {}
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON {path}: {e}", file=sys.stderr)
        return {}

def load_csv(path):
    rows = []
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except FileNotFoundError:
        print(f"Error: File not found: {path}", file=sys.stderr)
    return rows

def get_unique_tags_recursive(data, collected=None):
    if collected is None:
        collected = set()
    
    if isinstance(data, str):
        collected.add(data)
    elif isinstance(data, list):
        for item in data:
            get_unique_tags_recursive(item, collected)
    elif isinstance(data, dict):
        for value in data.values():
            get_unique_tags_recursive(value, collected)
    
    return collected

# ------------------------------------------------------------------------------
# Metrics Calculations
# ------------------------------------------------------------------------------
def calc_base_metrics(project_root, subject_filter=None):
    csv_path = project_root / 'assets/compatibility_review.csv'
    action_pools_path = project_root / 'vocab/data/action_pools.json'
    
    rows = load_csv(csv_path)
    action_pools = load_json(action_pools_path)
    
    # Filter by subject if requested
    if subject_filter:
        original_count = len(rows)
        rows = [r for r in rows if r.get('subj') == subject_filter]
        if not rows and original_count > 0:
            print(f"Warning: No rows found for subject '{subject_filter}'", file=sys.stderr)
            sys.exit(1)

    unique_subjects = set()
    unique_locs = set()
    total_actions = 0
    missing_pools = set()
    loc_action_counts = {}

    for row in rows:
        subj = row.get('subj') # Reverted to 'subj' based on error
        loc = row.get('canonical_loc') or row.get('loc') # Fallback if canonical_loc missing
        
        if subj: unique_subjects.add(subj)
        if loc:
            unique_locs.add(loc)
            
            # Count actions
            if loc in action_pools:
                count = len(action_pools[loc])
                total_actions += count
                loc_action_counts[loc] = count
            else:
                missing_pools.add(loc)
                # Do not add to total_actions (Strict mode)

    return {
        "unique_subjects": len(unique_subjects),
        "unique_locations": len(unique_locs),
        "total_base_variations": total_actions, # This is effectively Char x Loc x Action since we iterate rows
        "missing_pools_count": len(missing_pools),
        "missing_pools_list": list(missing_pools),
        "row_count": len(rows)
    }

def calc_garnish_metrics(project_root):
    # Load separate vocabulary files
    vocab_dir = project_root / 'vocab/data'
    
    garnish_base = load_json(vocab_dir / 'garnish_base_vocab.json')
    micro_actions = load_json(vocab_dir / 'garnish_micro_actions.json')
    # Background packs (for details/textures)
    bg_packs = load_json(vocab_dir / 'background_packs.json') # or background_loc_tag_map?
    # Actually background details come from packs
    
    # 1. Camera
    angles = len(garnish_base.get('VIEW_ANGLES', []))
    framing = len(garnish_base.get('VIEW_FRAMING', []))
    camera_configs = angles * framing
    
    # 2. Moods
    mood_pools = garnish_base.get('MOOD_POOLS', {})
    mood_keys_count = len(mood_pools)
    total_mood_tags = len(get_unique_tags_recursive(list(mood_pools.values())))

    # 3. Micro Actions
    # Structure: Key -> { triggers, specific, generic, roulette }
    # We want unique output tags
    ma_tags = set()
    for cat_data in micro_actions.values():
        # Specific
        if 'specific' in cat_data:
            get_unique_tags_recursive(cat_data['specific'], ma_tags)
        # Generic
        if 'generic' in cat_data:
            get_unique_tags_recursive(cat_data['generic'], ma_tags)
        # Roulette options
        if 'roulette' in cat_data and 'options' in cat_data['roulette']:
             get_unique_tags_recursive(cat_data['roulette']['options'], ma_tags)

    # 4. Effects
    effects_tags = set()
    for key in ['EFFECTS_UNIVERSAL', 'EFFECTS_BRIGHT', 'EFFECTS_DARK', 'EFFECTS_DYNAMIC']:
        if key in garnish_base:
            effects_tags.update(garnish_base[key])
            
    # 5. Background Details (Estimate from likely largest pack)
    # We just want a sense of "Detail" variation. 
    # Let's count unique strings in all 'props', 'texture', 'environment' of bg packs
    bg_tags = set()
    for pack in bg_packs.values():
        for sub_key in ['props', 'texture', 'environment', 'core']:
            if sub_key in pack:
                get_unique_tags_recursive(pack[sub_key], bg_tags)

    return {
        "camera_configs": camera_configs,
        "mood_keys": mood_keys_count,
        "mood_tags_unique": total_mood_tags,
        "micro_actions_unique": len(ma_tags),
        "effects_unique": len(effects_tags),
        "background_details_unique": len(bg_tags)
    }

def main():
    parser = argparse.ArgumentParser(description="Calculate prompt variations metrics.")
    parser.add_argument("--project_root", default=".", help="Path to project root (default: current dir)")
    parser.add_argument("--subject", help="Filter analysis to a specific character subject")
    parser.add_argument("--json", action="store_true", help="Output metrics in JSON format")
    args = parser.parse_args()

    # Resolve project root
    root = Path(args.project_root).resolve()
    if not (root / 'assets').exists():
        # Try parent if running from assets dir
        if (root.parent / 'assets').exists():
            root = root.parent
            
    base = calc_base_metrics(root, args.subject)
    garnish = calc_garnish_metrics(root)

    # Combined Indices
    # Conservative Garnish Factor: 
    # Assume 1 Camera * 1 Mood * 1 MicroAction * 1 Effect * 1 BG Detail is possible?
    # Actually, let's just use the product of the counts as a "Theoretical Upper Bound Garnish Multiplier"
    # But that's too huge.
    # Let's define "Active Garnish Factor" as:
    # Camera (N) * Moods (N) * (MicroActions + Effects + BGDetails) (since they are often optional or exclusive-ish)
    
    # A cleaner metric might be: "Garnish Universe Size"
    # Camera * Moods * (Micro + Effects)
    garnish_universe = garnish['camera_configs'] * garnish['mood_keys'] * (
        garnish['micro_actions_unique'] + garnish['effects_unique']
    )
    
    combined_upper_bound = base['total_base_variations'] * garnish_universe

    metrics = {
        "base": base,
        "garnish": garnish,
        "combined": {
            "garnish_universe_size": garnish_universe,
            "theoretical_upper_bound": combined_upper_bound
        }
    }

    if args.json:
        print(json.dumps(metrics, indent=2))
    else:
        print("="*60)
        print(f"PROMPT VARIATION METRICS REPORT")
        print("="*60)
        
        if args.subject:
             print(f"Subject Filter: {args.subject}")
        
        print("\n--- [1] BASE METRICS (Strict) ---")
        print(f"  Rows Processed:      {base['row_count']}")
        print(f"  Unique Subjects:     {base['unique_subjects']}")
        print(f"  Unique Locations:    {base['unique_locations']}")
        print(f"  Action Variations:   {base['total_base_variations']:,} (Char x Loc x Action)")
        
        if base['missing_pools_count'] > 0:
            print(f"  \033[91mMISSING ACTION POOLS: {base['missing_pools_count']}\033[0m")
            print(f"  (Locations: {', '.join(base['missing_pools_list'][:5])}...)")
        else:
            print(f"  Missing Action Pools: 0 (OK)")

        print("\n--- [2] GARNISH METRICS (Vocabulary Data) ---")
        print(f"  Camera Configs:      {garnish['camera_configs']} (Angles x Framing)")
        print(f"  Mood Keys:           {garnish['mood_keys']} (Unique Moods)")
        print(f"  Micro-Actions:       {garnish['micro_actions_unique']} (Unique Tags)")
        print(f"  Effects:             {garnish['effects_unique']} (Unique Tags)")
        print(f"  Background Details:  {garnish['background_details_unique']} (Unique Tags)")
        
        print("\n--- [3] COMBINED INDICES ---")
        print(f"  Garnish Universe:    {garnish_universe:,}")
        print(f"  Theoretical Max:     {combined_upper_bound:,} (Base x Garnish Universe)")
        print("="*60)

if __name__ == "__main__":
    main()
