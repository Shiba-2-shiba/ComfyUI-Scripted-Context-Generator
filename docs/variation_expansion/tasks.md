# Variation Expansion Task Board

Last updated: 2026-05-09

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

P6-era generator state:

- generated rows: `1,637`
- current rows: `1,637`
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

Current generator state after P11/P12:

- generated rows: `5,926`
- current rows: `5,926`
- missing current pairs: `0`
- extra generated pairs: `0`
- `python tools/build_compatibility_review.py --check` reports `ERROR: []`, `WARNING: []`

## P7: Action Pool Authoring Split Evaluation

- [x] VE-701 Measure review pain after P6
- [x] VE-702 Add `vocab/source/action_pools/*.json` authoring source
- [x] VE-703 Keep runtime loader unchanged while source check proves generated output
- [x] VE-704 Add `tools/build_action_pools.py --check`
- [x] VE-705 Add regression test for exact source/runtime rebuild

P7-era action pool source state:

- runtime file: `vocab/data/action_pools.json`
- source dir: `vocab/source/action_pools/`
- source location files: `79`
- runtime/source drift: `0`

Commands:

```bash
python tools/build_action_pools.py --check
python -m unittest assets.test_build_action_pools
```

Current action pool source state after P11/P12:

- runtime file: `vocab/data/action_pools.json`
- source dir: `vocab/source/action_pools/`
- source location files: `96`
- shared family source: `vocab/source/action_pools/_shared_families.json`
- runtime/source drift: `0`

## P8: Remaining Daily-Life Location Promotion

- [x] VE-801 Add 8 semantic actions for `food_court`
- [x] VE-802 Add 8 semantic actions for `coworking_space`
- [x] VE-803 Add 8 semantic actions for `community_center`
- [x] VE-804 Add 8 semantic actions for `apartment_balcony`
- [x] VE-805 Add 8 semantic actions for `apartment_entryway`
- [x] VE-806 Add 8 semantic actions for `public_library_lobby`
- [x] VE-807 Add 8 semantic actions for `riverside_walk`
- [x] VE-808 Add 8 semantic actions for `laundromat`
- [x] VE-809 Rebuild runtime action pools from split source
- [x] VE-810 Promote the 8 locations in `variation_scope.json`
- [x] VE-811 Regenerate `assets/compatibility_review.csv`
- [x] VE-812 Update expected metrics in `variation_scope.json`
- [x] VE-813 Run focused expansion checks
- [x] VE-814 Update docs with actual measured delta

P8 actual outcome:

- unique locations: `68 -> 76`
- compatibility rows: `1,565 -> 1,637`
- base variations: `15,034 -> 15,610`
- estimated delta: `+576`

Commands:

```bash
python tools/build_action_pools.py --write
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --write --output assets/compatibility_review.csv
python tools/build_compatibility_review.py --check
python tools/validate_prompt_data.py
python tools/check_variation_scope.py
python assets/calc_variations.py --json
python -m unittest assets.test_build_action_pools assets.test_action_generator assets.test_action_diversity_audit assets.test_repetition_guard_audit assets.test_variation_scope assets.test_build_compatibility_review
```

## P9: 100k Target Modeling

- [x] VE-901 Add read-only `tools/plan_variation_target.py`
- [x] VE-902 Add regression tests for target scenario calculations
- [x] VE-903 Report subject candidate deltas after P8
- [x] VE-904 Report location candidate deltas after P8
- [x] VE-905 Report minimum action-depth scenarios for `--target 100000`
- [x] VE-906 Record accepted/rejected subject clusters in `progress.md`

Current post-P8 planning facts:

- compatibility characters outside current variation scope: `33`
- all known subjects with current locations: about `25,524` base variations
- all known subjects and all action-backed compatible locations: about `27,140`
- minimum 35 actions across that known surface reaches about `100,835`, but this is not the preferred route because it risks repetitive action text
- generated by `python tools/plan_variation_target.py --target 100000`

## P10: Compatibility Taxonomy Expansion For 100k

- [x] VE-1001 Add mid-level compatibility tags such as `retail_service`, `daily_public`, `transit`, `home_life`, `workplace`, `leisure`, and `quiet_indoor`
- [x] VE-1002 Promote distinct subject candidates in `variation_scope.json`
- [x] VE-1003 Promote available daily/common locations with background packs and action pools
- [x] VE-1004 Regenerate `assets/compatibility_review.csv`
- [x] VE-1005 Update expected metrics in `variation_scope.json`
- [x] VE-1006 Verify compatibility rows are within `5,800-6,500`

P10 result:

- unique subjects: `120`
- unique locations: `91`
- compatibility rows: `5,926`
- base variations: `52,121`
- missing action pools: `0`

## P11: Action Authoring Refactor For 20+ Effective Actions

- [x] VE-1101 Design shared action family source without changing runtime loading
- [x] VE-1102 Update `tools/build_action_pools.py` to expand shared authoring data if needed
- [x] VE-1103 Raise high-row locations to 20-24 semantic actions
- [x] VE-1104 Raise medium-row locations to 16-20 semantic actions
- [x] VE-1105 Keep low-row/specialized locations at 12-16 semantic actions
- [x] VE-1106 Verify `base variations >= 100,000`

P11 result:

- high-row locations: `20` actions
- medium-row locations: `16` actions
- low-row/specialized locations: `12` actions
- base variations: `52,121 -> 105,612`
- action count summary: `min 12 / median 16 / mean 15.6 / max 20`
- authoring source: `vocab/source/action_pools/_shared_families.json` plus per-location `families` refs

## P12: 100k Stabilization Gate

- [x] VE-1201 Run target planner for `100000`
- [x] VE-1202 Run scope and compatibility checks
- [x] VE-1203 Run action pool source/runtime check
- [x] VE-1204 Run prompt data validation
- [x] VE-1205 Run full asset unittest discovery
- [x] VE-1206 Run full flow verification

P12 result:

- `python tools/plan_variation_target.py --target 100000`: target met at `105,612`
- `python tools/check_variation_scope.py`: `ERROR: []`
- `python tools/build_compatibility_review.py --check`: `ERROR: []`, `WARNING: []`
- `python tools/build_action_pools.py --check`: `ERROR: []`, `WARNING: []`
- `python tools/validate_prompt_data.py`: `ERROR: []`, `WARNING: []`
- `python -m unittest discover -s assets -p "test_*.py"`: `266 tests OK`
- `python tools/verify_full_flow.py`: `OK`

## P13: 500k Target Planning

Active phase. Do not begin bulk subject, location, compatibility, or action-pool
edits until this planning gate is recorded.

- [ ] VE-1301 Run and summarize `python tools/plan_variation_target.py --target 500000`
- [ ] VE-1302 Model subject/location/compatibility-density/action-depth shapes for `500000`
- [ ] VE-1303 Identify whether compatibility density, location count, subject count, or action depth is the next limiter
- [ ] VE-1304 Define guardrails for expanding beyond the 100k stabilized surface
- [ ] VE-1305 Record rejected inflation routes before implementation starts

## P14: Clothing State Location Gate

Prompt-quality cleanup lane. This should not change variation sizing,
compatibility rows, public node sockets, or data schemas.

Plan:

- `docs/variation_expansion/clothing_state_location_gate_plan.md`

Tasks:

- [x] VE-1401 Identify snow state mismatch from generated prompt samples
- [x] VE-1402 Survey other clothing `states` that can conflict with Location
- [x] VE-1403 Replace snow-only gating with shared state-family location gate
- [x] VE-1404 Add negative regression tests for indoor-incompatible states
- [x] VE-1405 Add positive regression tests for compatible state Locations
- [x] VE-1406 Update prompt snapshots only where incompatible state text is intentionally removed
- [x] VE-1407 Run targeted verification for clothing, snapshots, prompt data, and variation scope
- [x] VE-1408 Record remaining compatibility-level risks after state gating

State families to gate:

- snow: `covered in snow`
- wet: `rain-soaked`, `wet`
- sun/beach: `sun-kissed glow`
- exertion: `sweaty`
- battle damage: `battle-worn`, `blood-stained`
- workshop dirt: `grease stained`

Focused commands:

```bash
python -m unittest assets.test_context_content_pipeline
python -m unittest assets.test_prompt_snapshots
python -m unittest assets.test_determinism assets.test_registry
python tools/validate_prompt_data.py
python tools/check_variation_scope.py
```
