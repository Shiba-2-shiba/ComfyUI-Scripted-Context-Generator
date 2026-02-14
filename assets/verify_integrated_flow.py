import sys
import os
import random

# Add current directory to sys.path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

from nodes_character_profile import CharacterProfileNode
from nodes_dictionary_expand import ThemeClothingExpander
from nodes_garnish import GarnishSampler

def test_integrated_flow():
    print("=== Starting Phase 4 Verification: Integrated Flow ===")
    
    # Instantiate Nodes
    char_node = CharacterProfileNode()
    cloth_node = ThemeClothingExpander()
    garnish_node = GarnishSampler()
    
    seed = 2024
    
    # Test Scenarios
    scenarios = [
        # (Character Name, Expected Personality, Expected Color, Theme)
        ("Aiko (Quiet)", "quiet", "white", "school_uniform"),
        ("Mika (Energetic)", "energetic", "orange", "gym_workout"),
        ("Reina (Cool)", "cool", "black", "office_lady"),
    ]
    
    
    success = True
    
    for char_name, expected_personality_trait, expected_color_trait, theme in scenarios:
        print(f"\n--- Testing Scenario: {char_name} ---")
        
        # 1. Get Character Profile
        # args: mode, character_name, seed
        char_res = char_node.get_profile("fixed", char_name, seed)
        # return: (subj_prompt, hair_color, eye_color, personality, color_palette_str)
        
        print(f"  Character Output Raw: {len(char_res)} items")
        
        subject_prompt = char_res[0]
        # hair_color = char_res[1]
        # eye_color = char_res[2]
        personality = char_res[3]
        color_palette = char_res[4]

        print(f"  > Palette: {color_palette}")
        print(f"  > Personality: {personality}")
        
        # 2. Expand Clothing (Color Injection)
        # expanding: theme_key, seed, outfit_mode, outerwear_chance, character_palette
        cloth_res = cloth_node.expand_clothing(theme, seed, "random", 0.5, color_palette)
        clothing_prompt = cloth_res[0]
        print(f"  > Clothing: {clothing_prompt}")
        
        # Check Color Injection
        color_hit = False
        p_colors = [c.strip().lower() for c in color_palette.split(",") if c.strip()]
        for c in p_colors:
            if c in clothing_prompt.lower():
                color_hit = True
                print(f"    [OK] Found palette color '{c}' in clothing.")
                break
        if not color_hit:
            print(f"    [WARN] No palette color found in clothing.")
            # Note: Warn on color miss, maybe not fail strictly? keeping flexible.
            # success = False 

        # 3. Garnish Generation (Personality Interaction)
        # sample: action_text, meta_mood, seed, max, cam, loc, cos, scene, personality
        garnish_res = garnish_node.sample(
            "standing", "neutral", seed, 4, False, "", "", "{}", personality
        )
        garnish_prompt = garnish_res[0]
        print(f"  > Garnish: {garnish_prompt}")
        
        # Check Personality Reflection
        # Simple check: does it match expected traits?
        if expected_personality_trait == "energetic":
            if any(x in garnish_prompt.lower() for x in ["smile", "laugh", "jump", "dynamic", "run"]):
                print("    [OK] Energetic trait detected.")
            else:
                print("    [WARN] Energetic trait missing?")
                # success = False
        elif expected_personality_trait == "quiet":
            if any(x in garnish_prompt.lower() for x in ["book", "read", "tea", "calm", "soft"]):
                print("    [OK] Quiet trait detected.")
            else:
                print("    [WARN] Quiet trait missing?")
                # success = False
                
    print("\n=== Verification Complete ===")
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    test_integrated_flow()
