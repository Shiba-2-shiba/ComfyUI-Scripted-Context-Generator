# Completed Wave: Daily-Life Location Expansion

Completed: 2026-05-08

## Summary

The first variation expansion wave is complete.

Results:

```text
unique subjects: 58 -> 58
unique locations: 58 -> 68
base variations: 11,916 -> 15,034
compatibility rows: 1,353 -> 1,565
action pool count: 69 -> 79
dedicated action pool missing candidates: 27 -> 17
```

## Added Locations

These locations were promoted into base variation sizing and received dedicated action pools:

- `convenience_store`
- `bakery_shop`
- `supermarket_aisle`
- `drugstore_aisle`
- `family_restaurant`
- `cinema_lobby`
- `game_arcade`
- `bus_terminal`
- `campus_hallway`
- `campus_cafeteria`

## Additional Existing-Location Actions

High-coverage existing locations also received semantic action additions.

Priority locations included:

- `school_library`
- `clean_modern_kitchen`
- `cozy_living_room`
- `rainy_alley`
- `aquarium`
- `art_gallery`
- `bedroom_boudoir`
- `illuminated_park`
- `messy_kitchen`
- `museum_hall`
- `winter_street`
- `street_cafe`
- `botanical_garden`
- `cozy_bookstore`
- `picnic_park`
- `commuter_transport`
- `shopping_mall_atrium`

## Decision Notes

- The implementation kept `unique subjects` stable at 58.
- `scene_compatibility.characters` contains more entries than the current variation sizing surface.
- Pulling all compatibility characters into `assets/compatibility_review.csv` would inflate subject count outside this wave's scope.
- `assets/compatibility_review.csv` remains the sizing input for `assets/calc_variations.py`.
- The follow-up refactor is to make that sizing scope explicit in `vocab/data/variation_scope.json`.

## Verification

Commands run:

```bash
python -m unittest assets.test_data_consistency assets.test_location_resolution assets.test_action_generator assets.test_calc_variations
python -m unittest assets.test_action_generator assets.test_action_diversity_audit assets.test_repetition_guard_audit
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python tools/report_expansion_delta.py assets/results/variation_before.json assets/results/variation_after.json
```

All checks passed at completion.
