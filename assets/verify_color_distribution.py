import sys
import os

# Add current directory to sys.path to ensure imports work
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

from nodes_dictionary_expand import ThemeClothingExpander

def test_color_injection():
    print("=== Starting Phase 2 Verification: Color Palette Styling ===")
    
    node = ThemeClothingExpander()
    
    # Needs actual clothing_vocab loaded, which happens in the module
    # We must ensure clothing_vocab is available
    if not os.path.exists(os.path.join(current_dir, "vocab", "data", "clothing_theme_map.json")):
        print("FAIL: vocab structure seems invalid or clothing data missing.")
        return

    test_palette = "crimson, gold, black"
    theme = "office_lady"
    seed = 42
    
    print(f"\n[Test 1] Injecting Palette: [{test_palette}] into Theme: {theme}")
    
    match_count = 0
    trials = 10
    
    for i in range(trials):
        # expand_clothing(theme_key, seed, outfit_mode, outerwear_chance, character_palette)
        # Note: arguments must match the signature
        result = node.expand_clothing(theme, seed + i, "random", 0.5, test_palette)
        prompt = result[0]
        
        # Check if any color from palette is in prompt
        # Note: "crimson" might appear as "crimson"
        found = False
        for color in ["crimson", "gold", "black"]:
            if color in prompt.lower():
                found = True
                break
        
        status = "HIT" if found else "MISS"
        if found: match_count += 1
        
        print(f"  Run {i+1}: {prompt} -> {status}")

    print(f"\nResult: {match_count}/{trials} prompts contained palette colors.")
    
    if match_count >= 3: # Expect at least 30-40% hit rate with 0.6 probability + RNG
        print("  -> OK: Color injection is verified.")
        sys.exit(0)
    else:
        print("  -> WARNING: Color injection rate seems low. (Might be bad RNG or logic bug)")
        sys.exit(1)
        
    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    test_color_injection()
