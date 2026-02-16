import json
import os
import argparse
from typing import Dict, List, Set

# Configuration
VOCAB_DIR = os.path.join(os.path.dirname(__file__), "../vocab/data")
BACKGROUND_PACKS_PATH = os.path.join(VOCAB_DIR, "background_packs.json")

def load_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: Dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def analyze_aliases(fix: bool = False, output_file: str = None):
    print(f"Loading data from {BACKGROUND_PACKS_PATH}...")
    try:
        bg_packs = load_json(BACKGROUND_PACKS_PATH)
    except FileNotFoundError as e:
        print(f"Error loading file: {e}")
        return

    alias_map: Dict[str, List[str]] = {} # alias -> [loc_ids]
    locs_without_aliases = []
    locs_with_few_aliases = []
    
    modified = False

    for loc_id, data in bg_packs.items():
        if loc_id.startswith("_"): continue
        
        aliases = data.get("aliases", [])
        
        # specific fix: ensure aliases is a list
        if not isinstance(aliases, list):
            aliases = []
            data["aliases"] = aliases
            modified = True

        # Normalization: Lowercase and strip
        normalized_aliases = []
        seen_current = set()
        
        for a in aliases:
            norm_a = a.strip().lower()
            if norm_a and norm_a not in seen_current:
                normalized_aliases.append(norm_a)
                seen_current.add(norm_a)
        
        if len(normalized_aliases) != len(aliases) or set(normalized_aliases) != set(aliases):
            if fix:
                data["aliases"] = normalized_aliases
                modified = True
            else:
                pass # Just analyzing for now

        current_aliases = data.get("aliases", []) # Reload if modified or not
        
        if len(current_aliases) == 0:
            locs_without_aliases.append(loc_id)
        elif len(current_aliases) < 2:
            locs_with_few_aliases.append(loc_id)

        for a in current_aliases:
            if a not in alias_map:
                alias_map[a] = []
            alias_map[a].append(loc_id)

    # Report generation
    lines = []
    lines.append("--- Analysis Report ---")
    lines.append(f"Locations with NO aliases: {len(locs_without_aliases)}")
    for loc in locs_without_aliases:
        lines.append(f"  - {loc}")
        
    lines.append(f"\nLocations with fewer than 2 aliases: {len(locs_with_few_aliases)}")
    for loc in locs_with_few_aliases:
        lines.append(f"  - {loc}: {bg_packs[loc].get('aliases')}")

    lines.append("\nDuplicate Aliases (Collision Check):")
    collisions = {k: v for k, v in alias_map.items() if len(v) > 1}
    if collisions:
        for alias, locs in collisions.items():
            lines.append(f"  - '{alias}' is used by: {', '.join(locs)}")
    else:
        lines.append("  None")

    report_text = "\n".join(lines)
    print(report_text)
    
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"\nReport saved to {output_file}")

    if fix and modified:
        save_json(BACKGROUND_PACKS_PATH, bg_packs)
        print(f"\nSaved normalized data to {BACKGROUND_PACKS_PATH}")
    elif fix:
        print("\nNo changes needed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze and normalize aliases.")
    parser.add_argument("--fix", action="store_true", help="Apply normalization fixes (lowercase, dedup within loc)")
    parser.add_argument("--output", "-o", help="Output report file path")
    args = parser.parse_args()
    
    analyze_aliases(args.fix, args.output)
