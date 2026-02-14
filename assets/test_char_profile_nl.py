import os
import sys

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from nodes_character_profile import CharacterProfileNode
except ImportError:
    print("Could not import CharacterProfileNode. Make sure you are running this from the correct directory.")
    sys.exit(1)

def test_character_profile_nl():
    node = CharacterProfileNode()
    
    # Test specific characters to see NL output
    characters_to_test = ["Aiko (Thinking)", "Akane (Warrior)", "Sarah (Sunny)"] # Aiko (Thinking) might not exist, will fallback to random
    
    print("--- Testing Character Profile Natural Language Output ---")
    
    # Test 1: Random Mode
    print("\n[Test 1] Random Mode")
    result = node.get_profile("random", "", 123)
    print(f"Output: {result[0]}")
    
    # Test 2: Fixed Mode (Known Character)
    print("\n[Test 2] Fixed Mode: Akane (Warrior)")
    result = node.get_profile("fixed", "Akane (Warrior)", 0)
    print(f"Output: {result[0]}")
    expected_part = "A solo girl with high ponytail, red hair, and green eyes" # Based on code logic
    # Logic: "A solo girl with [high ponytail], [red hair] hair, and [green eyes] eyes" actually...
    # Let's check the code logic again:
    # hair_desc = f"{hair_style}, {hair_color} hair" -> "high ponytail, red hair"
    # eye_desc = f"{eye_color} eyes" -> "green eyes"
    # "A solo girl with " + hair_desc + " and " + eye_desc
    # "A solo girl with high ponytail, red hair and green eyes"
    
    if "A solo girl" in result[0] and "with" in result[0]:
        print("SUCCESS: Output format looks like a sentence.")
    else:
        print("FAILURE: Output format does not look like a sentence.")

    # Test 3: Fixed Mode (Another Character)
    print("\n[Test 3] Fixed Mode: Sarah (Sunny)")
    result = node.get_profile("fixed", "Sarah (Sunny)", 0)
    print(f"Output: {result[0]}")

if __name__ == "__main__":
    test_character_profile_nl()
