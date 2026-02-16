
import json
import os
import argparse
from typing import Dict, Any, List

# Configuration
VOCAB_DIR = os.path.join(os.path.dirname(__file__), "../vocab/data")
BACKGROUND_PACKS_PATH = os.path.join(VOCAB_DIR, "background_packs.json")
ACTION_POOLS_PATH = os.path.join(VOCAB_DIR, "action_pools.json")

# Quality Standards (Minimum counts)
STANDARDS = {
    "environment": 2,
    "core": 5,
    "texture": 3,
    "props": 4,
    "fx": 3,
    "time": 2,
    "action_count": 6
}

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def analyze_vocabulary(output_file: str = None):
    print(f"Loading data from {VOCAB_DIR}...")
    
    try:
        bg_packs = load_json(BACKGROUND_PACKS_PATH)
        action_pools = load_json(ACTION_POOLS_PATH)
    except FileNotFoundError as e:
        print(f"Error loading files: {e}")
        return

    report_lines = []
    report_lines.append("# Vocabulary Density Analysis Report")
    report_lines.append(f"Standard Criteria: {json.dumps(STANDARDS, indent=2)}")
    report_lines.append("")
    report_lines.append("| Location | Score (Fail Count) | Missing Fields | Action Count |")
    report_lines.append("|---|---|---|---|")

    stats = {
        "total_locs": 0,
        "failed_locs": 0,
        "perfect_locs": 0
    }

    results = []

    for loc_id, data in bg_packs.items():
        if loc_id.startswith("_"): continue
        
        stats["total_locs"] += 1
        
        # Analyze Background Pack Data
        failures = []
        
        for field, min_count in STANDARDS.items():
            if field == "action_count": continue # Handle separately
            
            items = data.get(field, [])
            count = len(items)
            if count < min_count:
                failures.append(f"{field}({count}/{min_count})")

        # Analyze Action Pool
        actions = action_pools.get(loc_id, [])
        # Filter comments if any
        actions = [a for a in actions if isinstance(a, str) and not a.startswith("_")]
        action_count = len(actions)
        
        if action_count < STANDARDS["action_count"]:
            failures.append(f"action_count({action_count}/{STANDARDS['action_count']})")

        # Result
        if failures:
            stats["failed_locs"] += 1
            results.append({
                "loc": loc_id,
                "score": len(failures),
                "failures": failures,
                "action_count": action_count
            })
        else:
            stats["perfect_locs"] += 1

    # Sort results by number of failures (descending)
    results.sort(key=lambda x: x["score"], reverse=True)

    for res in results:
        failures_str = ", ".join(res["failures"])
        report_lines.append(f"| {res['loc']} | {res['score']} | {failures_str} | {res['action_count']} |")

    report_lines.append("")
    report_lines.append("## Summary")
    report_lines.append(f"- Total Locations: {stats['total_locs']}")
    report_lines.append(f"- Needs Improvement: {stats['failed_locs']}")
    report_lines.append(f"- Meeting Standards: {stats['perfect_locs']}")

    report_content = "\n".join(report_lines)
    
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"Report saved to {output_file}")
    else:
        print(report_content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze vocabulary density against quality standards.")
    parser.add_argument("--output", "-o", help="Output markdown file path", default="logs/vocab_analysis.md")
    args = parser.parse_args()
    
    analyze_vocabulary(args.output)
