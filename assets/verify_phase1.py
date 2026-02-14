import sys
import os

# Add current directory to sys.path to ensure imports work
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

from nodes_character_profile import CharacterProfileNode

def test_character_profile():
    print("=== Starting Phase 1 Verification: Character Profile Node ===")
    
    node = CharacterProfileNode()
    
    # 1. Test specific character loading
    print("\n[Test 1] Fixed Mode (Aiko (Quiet))...")
    result = node.get_profile("fixed", "Aiko (Quiet)", 123)
    subj, hair, eye, personality, palette = result
    
    print(f"  Input: Aiko (Quiet)")
    print(f"  Output Subj: {subj}")
    print(f"  Output Visuals: Hair={hair}, Eye={eye}")
    print(f"  Output Personality: {personality}")
    print(f"  Output Palette: {palette}")
    
    if "long straight hair" in subj and "black hair" in subj:
        print("  -> OK: Visual traits matches Aiko data.")
    else:
        print("  -> FAIL: Visual traits do not match Aiko data.")

    # 2. Test Body Type Exclusion
    print("\n[Test 2] Body Type Exclusion Check...")
    # Body types checks
    forbidden_terms = ["breasts", "body type", "plump", "slender", "curvy", "athletic body", "small breasts", "large breasts"]
    
    found_forbidden = False
    for term in forbidden_terms:
        if term in subj.lower():
            found_forbidden = True
            print(f"  -> FAIL: Found forbidden term '{term}' in prompt.")
            break
    
    if not found_forbidden:
        print("  -> OK: No body type terms found.")

    # 3. Test Random Generation
    print("\n[Test 3] Random Mode (Seed Variation)...")
    
    results = set()
    for i in range(5):
        res = node.get_profile("random", "", i)
        results.add(res[0]) # Add subj string
        
    print(f"  Generated {len(results)} unique profiles in 5 runs with different seeds.")
    if len(results) > 1:
        print("  -> OK: Random generation is working.")
    else:
        print("  -> FAIL: Random generation produced identical results (sample size might be too small if only 1 char exists, but we added 4).")
        sys.exit(1)

    # 4. Test Schema Consistency
    print("\n[Test 4] Output Schema consistency...")
    if len(result) == 5:
        print("  -> OK: Returns 5 elements as expected.")
    else:
        print(f"  -> FAIL: Expected 5 return values, got {len(result)}.")

    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    test_character_profile()
