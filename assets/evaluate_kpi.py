
import os
import json
import argparse
import sys
from collections import Counter
from statistics import mean

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_ngrams(text, n):
    tokens = text.lower().replace(",", "").replace(".", "").split()
    if len(tokens) < n:
        return []
    return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]

def calculate_uniqueness(entries):
    all_2grams = []
    all_3grams = []
    
    for entry in entries:
        prompt = entry.get("output", {}).get("final_prompt", "")
        all_2grams.extend(get_ngrams(prompt, 2))
        all_3grams.extend(get_ngrams(prompt, 3))
        
    unique_2 = len(set(all_2grams)) / len(all_2grams) if all_2grams else 0.0
    unique_3 = len(set(all_3grams)) / len(all_3grams) if all_3grams else 0.0
    
    return unique_2, unique_3

def calculate_error_rate(entries):
    errors = 0
    total = len(entries)
    
    for entry in entries:
        out = entry.get("output", {})
        prompt = out.get("final_prompt", "")
        if not prompt or prompt.strip() == "":
            errors += 1
            continue
            
        # Check for error placeholders if any (e.g., "ERR:")
        if "ERR:" in prompt or "[ERROR]" in prompt:
            errors += 1
            
    return errors / total if total > 0 else 0.0

def calculate_reproducibility(current_entries, ref_entries):
    # Map index to entry
    ref_map = {e["index"]: e for e in ref_entries}
    
    matches = 0
    comparable = 0
    
    for cur in current_entries:
        idx = cur["index"]
        if idx in ref_map:
            comparable += 1
            ref = ref_map[idx]
            
            # Compare output details
            # We compare the dictionary content of 'output', ignoring 'debug_info'
            out_cur = cur.get("output", {}).copy()
            out_ref = ref.get("output", {}).copy()
            
            out_cur.pop("debug_info", None)
            out_ref.pop("debug_info", None)
            
            if out_cur == out_ref:
                matches += 1
                
    return matches / comparable if comparable > 0 else 0.0

def evaluate(current_path, ref_path=None):
    print(f"Evaluating: {current_path}")
    current_data = load_json(current_path)
    
    # 1. Basic Stats
    total = len(current_data)
    print(f"Total Samples: {total}")
    
    # 2. Error Rate
    err_rate = calculate_error_rate(current_data)
    print(f"Error Rate: {err_rate:.2%}")
    
    # 3. Uniqueness
    u2, u3 = calculate_uniqueness(current_data)
    print(f"Uniqueness (2-grams): {u2:.2%}")
    print(f"Uniqueness (3-grams): {u3:.2%}")
    
    # 4. Reproducibility (if ref provided)
    if ref_path and os.path.exists(ref_path):
        print(f"Comparing against: {ref_path}")
        ref_data = load_json(ref_path)
        repo_score = calculate_reproducibility(current_data, ref_data)
        print(f"Reproducibility: {repo_score:.2%}")
        
    # Validating Phase 0 success criteria
    # Just outputting the report is sufficient for now.
    
    # Return metrics dict for potential automated checks
    return {
        "count": total,
        "error_rate": err_rate,
        "uniqueness_2gram": u2,
        "uniqueness_3gram": u3
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate KPI for PromptBuilder outputs")
    parser.add_argument("current", help="Path to current results JSON")
    parser.add_argument("--ref", help="Path to reference results JSON", default=None)
    
    args = parser.parse_args()
    
    if os.path.exists(args.current):
        evaluate(args.current, args.ref)
    else:
        print(f"File not found: {args.current}")
        sys.exit(1)
