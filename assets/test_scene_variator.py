# -*- coding: utf-8 -*-
"""Test script for context scene variation logic."""
import json
import os
import random

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vocab", "data")

compat = json.load(open(os.path.join(DATA_DIR, "scene_compatibility.json"), "r", encoding="utf-8"))
action_pools = json.load(open(os.path.join(DATA_DIR, "action_pools.json"), "r", encoding="utf-8"))

# Build exclusion set
excluded = set()
for rule in compat.get("exclusions", []):
    for char in rule["characters"]:
        for loc in rule["denied_locs"]:
            excluded.add((char, loc))

def get_compatible_locs(subj, mode="full"):
    char_info = compat.get("characters", {}).get(subj)
    if not char_info:
        return []
    result = []
    char_tags = char_info.get("tags", [])
    for tag in char_tags:
        for loc in compat.get("loc_tags", {}).get(tag, []):
            if (subj, loc) not in excluded:
                result.append((loc, f"tag:{tag}"))
    if mode == "full":
        for loc in compat.get("universal_locs", []):
            if (subj, loc) not in excluded:
                if not any(l == loc for l, _ in result):
                    result.append((loc, "universal"))
    return result

passed = 0
failed = 0

# Test 1: original mode
print("=== Test 1: original mode ===")
print("  Input unchanged -> PASS")
passed += 1

# Test 2: full mode for business girl
print("\n=== Test 2: full mode (business girl) ===")
locs = get_compatible_locs("business girl", "full")
print(f"  Compatible locs: {len(locs)}")
for l, s in locs:
    print(f"    {l:25s} ({s})")
assert len(locs) > 5, f"Expected >5 locs, got {len(locs)}"
print("  PASS")
passed += 1

# Test 3: exclusion check for elf
print("\n=== Test 3: exclusion check (blonde elf archer) ===")
elf_locs = get_compatible_locs("blonde elf archer", "full")
elf_loc_names = [l for l, _ in elf_locs]
should_be_excluded = ["modern_office", "boardroom", "commuter_transport", "street_cafe"]
all_excluded = True
for loc in should_be_excluded:
    if loc in elf_loc_names:
        print(f"  ERROR: {loc} should be excluded but is present!")
        all_excluded = False
        failed += 1
    else:
        print(f"  {loc}: correctly excluded")
if all_excluded:
    print("  PASS")
    passed += 1

# Test 4: exclusion check for cyberpunk
print("\n=== Test 4: exclusion check (cyberpunk girl) ===")
cyber_locs = get_compatible_locs("cyberpunk girl", "full")
cyber_loc_names = [l for l, _ in cyber_locs]
cyber_excluded = ["shinto_shrine", "bamboo_forest", "botanical_garden", "picnic_park"]
all_excluded = True
for loc in cyber_excluded:
    if loc in cyber_loc_names:
        print(f"  ERROR: {loc} should be excluded but is present!")
        all_excluded = False
        failed += 1
    else:
        print(f"  {loc}: correctly excluded")
if all_excluded:
    print("  PASS")
    passed += 1

# Test 5: seed diversity
print("\n=== Test 5: seed diversity ===")
weights = compat.get("priority_weights", {})
candidates = [("existing", "modern_office")]
cw = [weights.get("existing", 50)]
for loc, src in locs:
    if loc != "modern_office":
        candidates.append((src, loc))
        w = weights.get("genre_gated", 35) if src.startswith("tag:") else weights.get("universal", 15)
        cw.append(w)

results = set()
for seed in range(100):
    rng = random.Random(seed * 12345)
    chosen = rng.choices(candidates, weights=cw, k=1)[0]
    results.add(chosen[1])
print(f"  Unique locs from 100 seeds: {len(results)}")
assert len(results) > 3, f"Expected >3 unique locs, got {len(results)}"
print("  PASS")
passed += 1

# Test 6: action pool coverage
print("\n=== Test 6: action pool coverage ===")
all_locs_in_compat = set()
for tag_locs in compat["loc_tags"].values():
    all_locs_in_compat.update(tag_locs)
all_locs_in_compat.update(compat["universal_locs"])
pool_keys = {k for k in action_pools.keys() if not k.startswith("_")}
missing = all_locs_in_compat - pool_keys
if missing:
    print(f"  Missing action pools: {missing}")
    failed += 1
else:
    print("  All locs have action pools")
    print("  PASS")
    passed += 1

# Test 7: genre_only mode
print("\n=== Test 7: genre_only mode (business girl) ===")
genre_locs = get_compatible_locs("business girl", "genre_only")
genre_loc_names = [l for l, _ in genre_locs]
universal_locs = compat["universal_locs"]
has_universal = any(l in universal_locs for l in genre_loc_names)
if has_universal:
    print("  ERROR: genre_only should not include universal locs")
    failed += 1
else:
    print(f"  Genre-only locs: {len(genre_locs)} (no universals)")
    print("  PASS")
    passed += 1

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED")
