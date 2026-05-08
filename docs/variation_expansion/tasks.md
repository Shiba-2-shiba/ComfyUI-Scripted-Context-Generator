# Variation Expansion Task Board

Last updated: 2026-05-08

Legend:

- `[ ]` not started
- `[~]` in progress
- `[x]` done
- `[!]` blocked or needs decision

## P0: Setup

- [x] VE-000 Record baseline metrics in `progress.md`
- [x] VE-001 Create refactor plan, progress tracker, and task board
- [x] VE-002 Save before metrics to `assets/results/variation_before.json`

Command:

```bash
python assets/calc_variations.py --json > assets/results/variation_before.json
```

## P1: Daily-Life Location Promotion

- [x] VE-101 Confirm each primary candidate has a canonical background pack
- [x] VE-102 Confirm aliases are deterministic for primary candidates
- [x] VE-103 Confirm intended `scene_compatibility` tags include primary candidates
- [x] VE-104 Update or regenerate `assets/compatibility_review.csv` so promoted locations affect base metrics
- [x] VE-105 Re-run focused location/data tests

Primary candidates:

- [x] `convenience_store`
- [x] `bakery_shop`
- [x] `supermarket_aisle`
- [x] `drugstore_aisle`
- [x] `family_restaurant`
- [x] `cinema_lobby`
- [x] `game_arcade`
- [x] `bus_terminal`
- [x] `campus_hallway`
- [x] `campus_cafeteria`

Fallback candidates:

- [ ] `food_court`
- [ ] `coworking_space`
- [ ] `community_center`
- [ ] `apartment_balcony`
- [ ] `apartment_entryway`

## P2: Dedicated Action Pools

- [x] VE-201 Add 8 semantic actions for `convenience_store`
- [x] VE-202 Add 8 semantic actions for `bakery_shop`
- [x] VE-203 Add 8 semantic actions for `supermarket_aisle`
- [x] VE-204 Add 8 semantic actions for `drugstore_aisle`
- [x] VE-205 Add 8 semantic actions for `family_restaurant`
- [x] VE-206 Add 8 semantic actions for `cinema_lobby`
- [x] VE-207 Add 8 semantic actions for `game_arcade`
- [x] VE-208 Add 8 semantic actions for `bus_terminal`
- [x] VE-209 Add 8 semantic actions for `campus_hallway`
- [x] VE-210 Add 8 semantic actions for `campus_cafeteria`
- [x] VE-211 Run action diversity / semantic policy checks

Focused checks:

```bash
python -m unittest assets.test_action_generator assets.test_action_diversity_audit assets.test_repetition_guard_audit
python tools/validate_prompt_data.py
```

## P3: High-Coverage Existing Action Additions

- [x] VE-301 Add 3 actions to `school_library`
- [x] VE-302 Add 3 actions to `clean_modern_kitchen`
- [x] VE-303 Add 3 actions to `cozy_living_room`
- [x] VE-304 Add 3 actions to `rainy_alley`
- [x] VE-305 Add 1 action to `aquarium`
- [x] VE-306 Add 1 action to `art_gallery`
- [x] VE-307 Add 1 action to `bedroom_boudoir`
- [x] VE-308 Add 1 action to `illuminated_park`
- [x] VE-309 Add 1 action to `messy_kitchen`
- [x] VE-310 Add 1 action to `museum_hall`
- [x] VE-311 Add 1 action to `winter_street`
- [x] VE-312 Add 1 action to `street_cafe`
- [x] VE-313 Add 1 action to `botanical_garden`
- [x] VE-314 Add 1 action to `cozy_bookstore`
- [x] VE-315 Add 1 action to `picnic_park`
- [x] VE-316 Add 1 action to `commuter_transport`
- [x] VE-317 Add 1 action to `shopping_mall_atrium`
- [x] VE-318 Re-run `python assets/calc_variations.py --json`

## P4: Verification and Documentation

- [x] VE-401 Run focused expansion tests
- [x] VE-402 Run full asset unittest discovery
- [x] VE-403 Run full flow verification
- [x] VE-404 Run workflow widget validation
- [x] VE-405 Save after metrics to `assets/results/variation_after.json`
- [x] VE-406 Compare before/after metrics
- [x] VE-407 Update `progress.md` with actual deltas
- [x] VE-408 Update `CURRENT_STATUS.md` if final metrics changed

Commands:

```bash
python -m unittest assets.test_data_consistency assets.test_location_resolution assets.test_action_generator assets.test_calc_variations
python tools/validate_prompt_data.py
python assets/calc_variations.py --json
python -m unittest discover -s assets -p "test_*.py"
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python assets/calc_variations.py --json > assets/results/variation_after.json
python tools/report_expansion_delta.py assets/results/variation_before.json assets/results/variation_after.json
```

## P5: Variation Scope Source Of Truth

- [x] VE-501 Add `vocab/data/variation_scope.json`
- [x] VE-502 Add `tools/check_variation_scope.py`
- [x] VE-503 Add regression tests for variation scope
- [x] VE-504 Run focused scope checks
- [x] VE-505 Update `progress.md` verification log

Commands:

```bash
python tools/check_variation_scope.py
python -m unittest assets.test_variation_scope
```

## P6: Scoped Compatibility Review Generation

- [x] VE-601 Add scoped generator with `--check`
- [x] VE-602 Compare generated rows against current `assets/compatibility_review.csv`
- [x] VE-603 Enable overwrite only after check mode has no drift
- [x] VE-604 Document generation workflow in `EXPANSION_GUIDE.md`
- [x] VE-605 Add direct background packs for all current scoped locations

Current generator state:

- generated rows: `1,565`
- current rows: `1,565`
- missing current pairs: `0`
- extra generated pairs: `0`
- row metadata drift: `0`
- prompt source scope warnings: `0`
- scope background-pack warnings: `0`

Commands:

```bash
python tools/build_compatibility_review.py --check
python -m unittest assets.test_build_compatibility_review
```

## P7: Action Pool Authoring Split Evaluation

- [ ] VE-701 Measure review pain after P6
- [ ] VE-702 Decide whether `vocab/source/action_pools/*.json` is justified
- [ ] VE-703 Keep runtime loader unchanged unless generated output is proven stable
