# Variation Expansion Progress

Last updated: 2026-05-08

## Status Summary

Overall status: `P12 verified; P13 planning active`

Current phase: `P13 500k target planning`

Primary target:

- variation scope を明示して、意図しない subject / location 増加を防ぐ
- `compatibility_review.csv` の scoped check-only generator で差分を固定する
- 第2波の daily-life location 追加前にデータ境界を軽くする
- P10 compatibility taxonomy expansion、P11 action authoring refactor、P12
  100k stabilization gate は完了済み。次は 500k へ向けた拡張形状を
  再設計する

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
unique locations: 76
base variations: 15,610
compatibility rows: 1,637
action pool count: 87
dedicated action pool missing candidates: 9
```

## Current Snapshot After P12

Measured on: 2026-05-08

```text
unique subjects: 120
unique locations: 91
base variations: 105,612
compatibility rows: 5,926
action pool count: 96
actions per location: min 12 / median 16 / mean 15.6 / max 20
missing action pools: 0
```

Intermediate target:

```text
base variations: 100,000
compatibility rows: 5,800-6,500
effective actions: 20+
final planning horizon: 500,000
```

## Phase Progress

| Phase | Scope | Status | Expected delta | Actual delta |
| --- | --- | --- | ---: | ---: |
| P0 | Baseline and plan docs | Done | 0 | 0 |
| P1 | Promote 8-10 daily-life locations | Done | +2,120 to +3,892 | +1,696 |
| P2 | Add dedicated action pools for promoted locations | Done | included in P1 | included in P1 |
| P3 | Add actions to high-coverage existing locations | Done | +1,298 | +1,422 |
| P4 | Full validation and final status update | Done | 0 | 0 |
| P5 | Define variation scope source of truth | Done | 0 | 0 |
| P6 | Scoped compatibility review generation | Done | 0 | 0 |
| P7 | Action pool authoring split evaluation | Done | 0 | 0 |
| P8 | Promote remaining daily-life locations | Done | +576 | +576 |
| P9 | Add 100k target modeling | Done | 0 | 0 |
| P10 | Expand compatibility taxonomy for 100k | Done | 45,000-60,000 | 52,121 |
| P11 | Refactor action authoring source for 20+ effective actions | Done | 100,000+ base | 105,612 |
| P12 | Stabilize 100k verification gate | Done | 0 | verified at 105,612 |
| P13 | Model the 500k expansion shape | Active planning | TBD | TBD |

## P13 Current Direction

The active work is 500k target planning. Before changing data, measure the
next expansion shape and decide whether the first limiter is subject count,
location count, compatibility density, or action depth.

P13 should start from:

```bash
python tools/plan_variation_target.py --target 500000
```

Record the chosen route before editing `variation_scope.json`,
`scene_compatibility.json`, `assets/compatibility_review.csv`, or
`vocab/source/action_pools/`.

## Completed 100k Direction

P8 increased `unique locations` before any subject promotion.

P8 actual outcome:

```text
unique subjects: 58 -> 58
unique locations: 68 -> 76
compatibility rows: 1,565 -> 1,637
base variations: 15,034 -> 15,610
estimated delta: +576
```

P9 added `tools/plan_variation_target.py` for read-only target modeling. The
current post-P8 compatibility surface has 33 subject candidates outside
`variation_scope.variation_subjects`, but promoting every known subject only
raises the current location surface to about `25,524` base variations. The 100k
path needs compatibility rows and action depth to increase together.

Current planning scenarios:

| Scenario | Base variations |
| --- | ---: |
| current scope | 15,610 |
| all known subjects, current locations | 25,524 |
| all known subjects, all action-backed compatible locations | 27,140 |
| all known subjects/locations, minimum 24 actions per location | 69,144 |
| all known subjects/locations, minimum 35 actions per location | 100,835 |

Preferred 100k shape:

- `105-120` subjects
- `105-115` locations
- `5,800-6,500` compatibility rows
- median `16+` actions

P10 should use the planner before changing scope or compatibility data:

```bash
python tools/plan_variation_target.py --target 100000
```

P9 rejected subject-only expansion as the next implementation step because the
best current subject candidates are mostly overlapping office / urban /
suburban archetypes and the full known subject pool still only reaches about
`25k` base variations on current locations.

P10 result:

- added mid-level tags: `retail_service`, `daily_public`, `transit`,
  `home_life`, `workplace`, `leisure`, `quiet_indoor`
- promoted compatibility subjects into variation scope and added distinct
  daily-life archetypes
- promoted existing background/action surface into scope where canonical
  generation can produce rows
- added dedicated action pools for the remaining daily-life locations
- reached `5,926` rows and `52,121` base variations

P11 target planner result before action refactor:

| Effective minimum actions | Base variations |
| --- | ---: |
| 16 | 94,816 |
| 20 | 118,520 |

P11 implemented a tiered action-depth target instead of forcing every location
to 20 actions:

| Location tier | Target actions |
| --- | ---: |
| high-row locations (`rows >= 100`) | 20 |
| medium-row locations (`rows >= 50`) | 16 |
| low-row/specialized locations | 12 |

P11 result:

- added shared semantic action families under
  `vocab/source/action_pools/_shared_families.json`
- expanded `tools/build_action_pools.py` so source files can reference shared
  families while runtime keeps the flat `vocab/data/action_pools.json` shape
- raised base variations from `52,121` to `105,612`
- current target planner reports `target_met: true` at the current surface

P12 stabilized this at `105,612` base variations. These notes are retained as
history and input for P13, not as the active next implementation plan.

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
- Treat `vocab/data/variation_scope.json` as the source of truth for the current sizing boundary.
- Do not add all `scene_compatibility.characters` entries to variation sizing unless they are promoted into scope.

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
| 2026-05-08 | `python tools/check_variation_scope.py` | Pass | `ERROR: []`; background-pack warnings recorded for 8 legacy/scoped locations |
| 2026-05-08 | `python -m unittest assets.test_variation_scope` | Pass | 2 tests OK |
| 2026-05-08 | `python tools/build_compatibility_review.py --check` | Pass | `ERROR: []`; `WARNING: []`; generated/current rows `1,565`; pair drift `0` |
| 2026-05-08 | `python -m unittest assets.test_build_compatibility_review` | Pass | 3 tests OK |
| 2026-05-08 | `python tools/check_variation_scope.py` | Pass | `ERROR: []`; `WARNING: []`; all 68 scoped locations have direct background packs |
| 2026-05-08 | `python -m unittest assets.test_asset_validator assets.test_vocab_lint assets.test_variation_scope assets.test_calc_variations assets.test_data_consistency` | Pass | 23 tests OK |
| 2026-05-08 | `python tools/build_action_pools.py --check` | Pass | `ERROR: []`; `WARNING: []`; 79 source location files match runtime JSON |
| 2026-05-08 | `python -m unittest assets.test_build_action_pools` | Pass | 2 tests OK |
| 2026-05-08 | `python tools/plan_variation_target.py --target 100000` | Pass | current base variations `105,612`; target met |
| 2026-05-08 | `python tools/build_action_pools.py --check` | Pass | `ERROR: []`; `WARNING: []`; shared family source expands to runtime JSON |
| 2026-05-08 | `python -m unittest assets.test_build_action_pools assets.test_action_generator assets.test_action_diversity_audit assets.test_repetition_guard_audit` | Pass | 26 tests OK |
| 2026-05-08 | `python -m unittest discover -s assets -p "test_*.py"` | Pass | 266 tests OK |
| 2026-05-08 | `python tools/verify_full_flow.py` | Pass | OK |

## Open Risks

- Some remaining daily-life candidates still rely on compositional fallback; this is intentional for this wave.
- `vocab/data/action_pools.json` remains the runtime file; edit `vocab/source/action_pools/*.json`
  first and verify with `python tools/build_action_pools.py --check`.
- Future action text must stay semantic-only and avoid object overconcentration.
- All current variation-scope locations now have direct background packs.
- Before subject/location promotion, keep `prompts.jsonl`, `variation_scope.json`,
  and `assets/compatibility_review.csv` aligned through
  `python tools/build_compatibility_review.py --check`.
