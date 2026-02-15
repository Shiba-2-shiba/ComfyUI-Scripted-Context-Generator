import sys
import os
import json
import subprocess
from datetime import datetime
from collections import Counter

# Import generate_baseline function
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from generate_baseline import generate_baseline

DAILY_LIFE_LOCATIONS = {
    "school_classroom",
    "modern_office",
    "street_cafe",
    "shopping_mall_atrium",
    "commuter_transport",
    "cozy_bookstore"
}

CONFLICT_RULES = [
    {"trigger": "winter", "forbidden": ["warm sun", "hot summer", "tropical"]},
    {"trigger": "night", "forbidden": ["blue sky", "sunny day", "bright sunlight"]},
    {"trigger": "rain", "forbidden": ["dry ground", "dusty air"]}
]

def check_consistency(prompt):
    prompt_lower = prompt.lower()
    violations = []
    for rule in CONFLICT_RULES:
        if rule["trigger"] in prompt_lower:
            for forbidden in rule["forbidden"]:
                if forbidden in prompt_lower:
                    violations.append(f"{rule['trigger']} <-> {forbidden}")
    return violations

def get_calc_variations_metrics(project_root):
    # Run calc_variations.py --json
    cmd = [sys.executable, os.path.join(project_root, "assets", "calc_variations.py"), "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
    if result.returncode != 0:
        print("Error running calc_variations.py:", result.stderr)
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Error decoding calc_variations.py output")
        return None

def main():
    print("=== Starting Phase 0 Baseline & KPI Setup ===")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Get Variation Metrics
    print("Step 1: Calculating Variation Metrics...")
    var_metrics = get_calc_variations_metrics(project_root)
    base_variations = var_metrics["base"]["total_base_variations"]
    location_stats = var_metrics["base"]["location_stats"]
    
    # Daily Life Location Share (Variation Contribution)
    daily_life_vars = 0
    total_vars = 0 # Re-sum from stats to be safe
    for stat in location_stats:
        if stat["location"] in DAILY_LIFE_LOCATIONS:
            daily_life_vars += stat["contribution"]
        total_vars += stat["contribution"]
        
    daily_life_var_share = daily_life_vars / total_vars if total_vars > 0 else 0
    
    # 2. Generate Prompt Baseline
    print("Step 2: Generating Prompt Baseline...")
    baseline_file = generate_baseline() # Returns path
    
    # 3. Analyze Prompts for Distribution & Consistency
    print("Step 3: Analyzing Prompts...")
    with open(baseline_file, 'r', encoding='utf-8') as f:
        prompts_data = json.load(f)
        
    total_prompts = len(prompts_data)
    daily_life_prompts = 0
    consistency_violations = 0
    
    for entry in prompts_data:
        output = entry["output"]
        loc = output["loc"]
        final_prompt = output["final_prompt"]
        
        # Check Distribution
        # Use simple string matching for location as it might be localized or modified? 
        # Actually the 'loc' output from parser is the canonical key usually.
        # But let's check if the 'loc' variable matches our keys
        if loc in DAILY_LIFE_LOCATIONS:
            daily_life_prompts += 1
            
        # Check Consistency
        violations = check_consistency(final_prompt)
        if violations:
            consistency_violations += 1
            
    daily_life_prompt_share = daily_life_prompts / total_prompts if total_prompts > 0 else 0
    consistency_violation_rate = consistency_violations / total_prompts if total_prompts > 0 else 0
    
    # 4. Consolidate Report
    report = {
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "total_base_variations": base_variations,
            "daily_life_var_share": daily_life_var_share,
            "daily_life_prompt_share": daily_life_prompt_share,
            "consistency_violation_rate": consistency_violation_rate
        },
        "details": {
            "total_prompts": total_prompts,
            "daily_life_prompts_count": daily_life_prompts,
            "consistency_violations_count": consistency_violations,
            "baseline_file": baseline_file
        }
    }
    
    report_path = os.path.join(os.path.dirname(baseline_file), "baseline_full_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        
    print("\n=== Phase 0 Baseline Report ===")
    print(f"Total Base Variations: {base_variations:,}")
    print(f"Daily Life Variation Share: {daily_life_var_share:.2%} (Target: Maintain)")
    print(f"Daily Life Prompt Share:    {daily_life_prompt_share:.2%} (Target: Maintain/-2%)")
    print(f"Consistency Violation Rate: {consistency_violation_rate:.2%} (Target: +0.5%)")
    print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    main()
