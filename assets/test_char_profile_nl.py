import os
import sys

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.character_profile_pipeline import build_character_profile, load_character_profiles

def test_character_profile_nl():
    profiles = load_character_profiles()
    
    # Test specific characters to see NL output
    characters_to_test = ["Aiko (Thinking)", "Akane (Warrior)", "Sarah (Sunny)"] # Aiko (Thinking) might not exist, will fallback to random
    
    print("--- Testing Character Profile Natural Language Output ---")
    
    # Test 1: Random Mode
    print("\n[Test 1] Random Mode")
    result = build_character_profile(123, "random", "", profiles)
    print(f"Output: {result['subj_prompt']}")
    
    # Test 2: Fixed Mode (Known Character)
    print("\n[Test 2] Fixed Mode: Akane (Warrior)")
    result = build_character_profile(0, "fixed", "Akane (Warrior)", profiles)
    print(f"Output: {result['subj_prompt']}")
    expected_part = "A solo girl with high ponytail, red hair, and green eyes" # Based on code logic
    # Logic: "A solo girl with [high ponytail], [red hair] hair, and [green eyes] eyes" actually...
    # Let's check the code logic again:
    # hair_desc = f"{hair_style}, {hair_color} hair" -> "high ponytail, red hair"
    # eye_desc = f"{eye_color} eyes" -> "green eyes"
    # "A solo girl with " + hair_desc + " and " + eye_desc
    # "A solo girl with high ponytail, red hair and green eyes"
    
    if "A solo girl" in result["subj_prompt"] and "with" in result["subj_prompt"]:
        print("SUCCESS: Output format looks like a sentence.")
    else:
        print("FAILURE: Output format does not look like a sentence.")

    # Test 3: Fixed Mode (Another Character)
    print("\n[Test 3] Fixed Mode: Sarah (Sunny)")
    result = build_character_profile(0, "fixed", "Sarah (Sunny)", profiles)
    print(f"Output: {result['subj_prompt']}")

if __name__ == "__main__":
    test_character_profile_nl()
