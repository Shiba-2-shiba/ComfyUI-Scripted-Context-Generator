# Variation Expansion Progress

Last updated: 2026-05-08

## Status Summary

Overall status: `verified`

Current phase: `complete`

Primary target:

- 日常系 location 8-10件を base variation 計測に昇格
- 昇格 location に dedicated action pool を追加
- 高カバレッジ既存 location の action を追加

## Baseline Snapshot

Measured on: 2026-05-08

```text
unique subjects: 58
unique locations: 58
base variations: 11,916
compatibility rows: 1,353
actions per location: min 4 / median 8 / mean 7.6 / max 12
missing action pools in current base set: 0
location candidates: 93
dedicated action pool missing candidates: 27
```

## Target Snapshot

Actual result:

```text
unique subjects: 58
unique locations: 68
base variations: 15,034
compatibility rows: 1,565
action pool count: 79
dedicated action pool missing candidates: 17
```

Stretch target:

```text
unique locations: 68+
base variations: 18,000+
```

## Phase Progress

| Phase | Scope | Status | Expected delta | Actual delta |
| --- | --- | --- | ---: | ---: |
| P0 | Baseline and plan docs | Done | 0 | 0 |
| P1 | Promote 8-10 daily-life locations | Done | +2,120 to +3,892 | +1,696 |
| P2 | Add dedicated action pools for promoted locations | Done | included in P1 | included in P1 |
| P3 | Add actions to high-coverage existing locations | Done | +1,298 | +1,422 |
| P4 | Full validation and final status update | Done | 0 | 0 |

## Candidate Tracking

Primary daily-life candidates:

| Location | Status | Notes |
| --- | --- | --- |
| `convenience_store` | Done | 27 rows / 8 actions |
| `bakery_shop` | Done | 27 rows / 8 actions |
| `supermarket_aisle` | Done | 27 rows / 8 actions |
| `drugstore_aisle` | Done | 27 rows / 8 actions |
| `family_restaurant` | Done | 27 rows / 8 actions |
| `cinema_lobby` | Done | 27 rows / 8 actions |
| `game_arcade` | Done | 27 rows / 8 actions |
| `bus_terminal` | Done | 11 rows / 8 actions |
| `campus_hallway` | Done | 6 rows / 8 actions |
| `campus_cafeteria` | Done | 6 rows / 8 actions |

Fallback candidates:

| Location | Status | Notes |
| --- | --- | --- |
| `food_court` | Backup | broad dining / mall |
| `coworking_space` | Backup | office / study |
| `community_center` | Backup | broad civic |
| `apartment_balcony` | Backup | home / quiet daily-life |
| `apartment_entryway` | Backup | home / transition scene |

High-coverage existing action additions:

| Location | Status | Suggested delta |
| --- | --- | ---: |
| `school_library` | Done | +3 |
| `clean_modern_kitchen` | Done | +3 |
| `cozy_living_room` | Done | +3 |
| `rainy_alley` | Done | +3 |
| `aquarium` | Done | +1 |
| `art_gallery` | Done | +1 |
| `bedroom_boudoir` | Done | +1 |
| `illuminated_park` | Done | +1 |
| `messy_kitchen` | Done | +1 |
| `museum_hall` | Done | +1 |
| `winter_street` | Done | +1 |
| `street_cafe` | Done | +1 |
| `botanical_garden` | Done | +1 |
| `cozy_bookstore` | Done | +1 |
| `picnic_park` | Done | +1 |
| `commuter_transport` | Done | +1 |
| `shopping_mall_atrium` | Done | +1 |

## Decisions

- Use data-first expansion before runtime refactor.
- Keep `vocab/data/action_pools.json` as the runtime source of truth for this wave.
- Treat `assets/compatibility_review.csv` as the base variation sizing source because `assets/calc_variations.py` reads it directly.
- Avoid schema and public node changes.

## Verification Log

| Date | Command | Result | Notes |
| --- | --- | --- | --- |
| 2026-05-08 | `python assets/calc_variations.py --json` | Pass | baseline captured |
| 2026-05-08 | `python tools/validate_prompt_data.py` | Pass | `ERROR: []`, `WARNING: []` |
| 2026-05-08 | `python -m unittest assets.test_data_consistency assets.test_location_resolution assets.test_action_generator assets.test_calc_variations` | Pass | 27 tests OK |
| 2026-05-08 | `python -m unittest assets.test_action_generator assets.test_action_diversity_audit assets.test_repetition_guard_audit` | Pass | 22 tests OK |
| 2026-05-08 | `python -m unittest discover -s assets -p "test_*.py"` | Pass | 253 tests OK |
| 2026-05-08 | `python tools/verify_full_flow.py` | Pass | OK |
| 2026-05-08 | `python tools/check_widgets_values.py` | Pass | OK |
| 2026-05-08 | `python tools/report_expansion_delta.py assets/results/variation_before.json assets/results/variation_after.json` | Pass | base variations `11,916 -> 15,034` |

## Open Risks

- Some remaining daily-life candidates still rely on compositional fallback; this is intentional for this wave.
- `vocab/data/action_pools.json` is larger after this pass; defer format splitting until review pain becomes concrete.
- Future action text must stay semantic-only and avoid object overconcentration.
