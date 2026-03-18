import json
import sys
import os

# Add parent dir to path
# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.content_pipeline import build_prompt_text

def load_inputs(path):
    with open(path, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f]

def load_rules():
    # rules/ is in root, so go up one level from assets/
    rule_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rules", "consistency_rules.json")
    with open(rule_path, 'r', encoding='utf-8') as f:
        return json.load(f).get("conflicts", [])

def check_conflict(prompt, rules, inputs):
    # This check is slightly different from the builder's check.
    # The builder checks if the *template part* conflicts with input.
    # Here we check if the *final prompt* contains conflicting terms given the input.
    
    # We reconstruct the context values from inputs
    context_vals = list(inputs.values())
    
    for rule in rules:
        input_term = rule.get("input_term", "").lower()
        template_term = rule.get("template_term", "").lower() # This is the "bad" term
        
        # Check if input triggers rule
        input_triggered = False
        for val in context_vals:
            if val and isinstance(val, str) and input_term in val.lower():
                input_triggered = True
                break
        
        if input_triggered:
            if template_term in prompt.lower():
                return f"Conflict: Input '{input_term}' vs Prompt '{template_term}'"
    return None

def run():
    print("Running Phase 4 Verification...")
    # Update path to point to assets/fixtures/benchmark_inputs.jsonl if running from root
    # Or calculate absolute path relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    inputs_path = os.path.join(script_dir, "fixtures", "benchmark_inputs.jsonl")
    inputs = load_inputs(inputs_path)
    rules = load_rules()
    
    errors = 0
    total = 0
    
    for i, item in enumerate(inputs):
        data = item # Input is flat
        seed = item.get("seed", i)
        
        # Flatten input for builder
        subj = data.get("subj", "")
        costume = data.get("costume", "")
        loc = data.get("loc", "")
        action = data.get("action", "")
        # garnish and meta are deeper or need unpacking, here simplifying
        meta = data.get("meta", {})
        meta_mood = meta.get("mood", "")
        meta_style = meta.get("style", "")
        
        # Run builder in composition mode
        try:
            prompt = build_prompt_text(
                template="", 
                composition_mode=True,
                seed=seed,
                subj=subj,
                costume=costume,
                loc=loc,
                action=action,
                garnish="", # skipping for this test
                meta_mood=meta_mood, 
                meta_style=meta_style
            )
            
            conflict = check_conflict(prompt, rules, {"subj": subj, "loc": loc, "meta_mood": meta_mood})
            if conflict:
                print(f"Index {i}: {conflict}")
                print(f"  Input: loc={loc}, mood={meta_mood}")
                print(f"  Prompt: {prompt}")
                errors += 1
            total += 1
            
        except Exception as e:
            print(f"Error at index {i}: {e}")
            errors += 1
            
    print(f"Total: {total}, Errors: {errors}")
    if errors == 0:
        print("SUCCESS: No conflicts found.")
    else:
        print("FAILURE: Conflicts found.")

if __name__ == "__main__":
    run()
