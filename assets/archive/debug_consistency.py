import json
import os

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

def main():
    path = "assets/results/baseline_20260215_163425.json"
    print(f"Checking {path}")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for entry in data:
        prompt = entry["output"]["final_prompt"]
        violations = check_consistency(prompt)
        if violations:
            print(f"Violation in Prompt: {prompt}")
            print(f"  --> {violations}")

if __name__ == "__main__":
    main()
