# Location / Action Expansion Refactor Plan

Last updated: 2026-05-08

## Purpose

日常系 location と action pool を増やし、base variations を安全に増加させる。
実装は data-first で進め、公開 node surface と runtime schema は変更しない。

## Non-Goals

- `Context*` node の public input / output を変更しない
- `PromptContext` schema を変更しない
- camera、render quality、style、body-shape 系の語を active prompt output に入れない
- 新規 dependency を追加しない
- 大きな runtime rewrite を先行しない

## Baseline Metrics

取得コマンド:

```bash
python assets/calc_variations.py --json
python tools/validate_prompt_data.py
```

開始時点:

```text
unique subjects: 58
unique locations: 58
base variations: 11,916
compatibility rows: 1,353
actions per location: min 4 / median 8 / mean 7.6 / max 12
location candidates: 93
action pool count: 69
action generatable count: 93
dedicated action pool missing count: 27
```

## Expansion Formula

`assets/calc_variations.py` は `assets/compatibility_review.csv` の行を基準にする。
base variations は概ね次で増える。

```text
new base variations = sum(compatibility rows per location * action count per location)
```

目安:

- 58 subjects に接続される location に action を1つ追加: `+58`
- 52 subjects に接続される location に action を1つ追加: `+52`
- 新規 broad location 1件を 58 rows / 8 actions で昇格: `+464`
- 新規 daily-life location 1件を 30-45 rows / 8 actions で昇格: `+240-360`

## Phase 1: Daily-Life Location Promotion

Primary 10 candidates:

| Location | Reason | Target actions | Estimated rows | Estimated increase |
| --- | --- | ---: | ---: | ---: |
| `convenience_store` | broad daily-life, urban/suburban | 8 | 35-58 | +280-464 |
| `bakery_shop` | daily-life, food/shop | 8 | 25-45 | +200-360 |
| `supermarket_aisle` | broad daily-life errands | 8 | 35-58 | +280-464 |
| `drugstore_aisle` | daily-life errands | 8 | 30-50 | +240-400 |
| `family_restaurant` | broad casual dining | 8 | 35-58 | +280-464 |
| `cinema_lobby` | leisure / public interior | 8 | 25-45 | +200-360 |
| `game_arcade` | leisure / youth / city | 8 | 20-40 | +160-320 |
| `bus_terminal` | transit daily-life | 8 | 30-50 | +240-400 |
| `campus_hallway` | school / student daily-life | 8 | 15-35 | +120-280 |
| `campus_cafeteria` | school / casual dining | 8 | 15-35 | +120-280 |

Expected Phase 1 increase: `+2,120` to `+3,892`.

Fallback candidates if one primary candidate does not fit:

- `food_court`
- `coworking_space`
- `community_center`
- `apartment_balcony`
- `apartment_entryway`

Required data checks:

- canonical key exists in `vocab/data/background_packs.json`
- alias resolution is deterministic through alias files
- location appears in the intended `scene_compatibility` tags
- location is counted in `assets/compatibility_review.csv` or the metric source is regenerated
- action generation is covered by `vocab/data/action_pools.json` or intentional compositional fallback

## Phase 2: Dedicated Action Pools

Add dedicated pools for all promoted locations unless fallback output is demonstrably better.
Each pool should start with 8 semantic actions.

Action authoring rules:

- Describe observable activity/state only
- Avoid camera, rendering, quality, body-shape, and style terms
- Avoid object overconcentration by varying focal objects
- Keep actions reusable across compatible subject types
- Prefer small daily-life behaviors over rare dramatic events

Example shape:

```json
"convenience_store": [
  { "text": "checking items near a shelf of daily goods", "load": "calm" }
]
```

Expected Phase 2 effect is included in Phase 1 because promoted location count depends on action count.

## Phase 3: Existing High-Coverage Action Additions

Start with high-row locations where each new action has immediate impact.

Priority group:

| Location | Rows | Current actions | Suggested delta | Estimated increase |
| --- | ---: | ---: | ---: | ---: |
| `school_library` | 58 | 7 | +3 | +174 |
| `clean_modern_kitchen` | 58 | 8 | +2 | +116 |
| `cozy_living_room` | 58 | 8 | +2 | +116 |
| `rainy_alley` | 58 | 8 | +2 | +116 |
| `aquarium` | 58 | 10 | +1 | +58 |
| `art_gallery` | 58 | 10 | +1 | +58 |
| `bedroom_boudoir` | 58 | 10 | +1 | +58 |
| `illuminated_park` | 58 | 10 | +1 | +58 |
| `messy_kitchen` | 58 | 10 | +1 | +58 |
| `museum_hall` | 58 | 10 | +1 | +58 |
| `winter_street` | 58 | 10 | +1 | +58 |
| `street_cafe` | 54 | 11 | +1 | +54 |
| `botanical_garden` | 54 | 10 | +1 | +54 |
| `cozy_bookstore` | 54 | 10 | +1 | +54 |
| `picnic_park` | 54 | 10 | +1 | +54 |
| `commuter_transport` | 52 | 10 | +1 | +52 |
| `shopping_mall_atrium` | 52 | 10 | +1 | +52 |

Expected Phase 3 increase: `+1,298`.

## Combined Target

Conservative target:

```text
current base variations: 11,916
Phase 1 + 2: +2,120 to +3,892
Phase 3: +1,298
target base variations: 15,334 to 17,106
```

Actual implementation result:

```text
current base variations: 11,916
daily-life location promotion: +1,696
high-coverage action additions: +1,422
actual base variations: 15,034
```

The actual location promotion delta is lower than the initial estimate because
the implementation intentionally kept `unique subjects` stable at 58 instead of
pulling every `scene_compatibility.characters` entry into the variation CSV.

Stretch target:

```text
Daily-life candidates reach broader rows and some high-coverage locations receive +2 actions.
target base variations: 18,000+
```

## Refactor Boundaries

The likely heavy surface is `vocab/data/action_pools.json`.
For this wave, keep runtime code stable and make data-only changes first.

If the JSON becomes hard to review after this wave, split authoring in a later pass:

1. Add a generated or checked source format only if review pain is proven.
2. Keep `vocab/data/action_pools.json` as the runtime source unless tests are updated.
3. Do not introduce new runtime loaders before data-only expansion proves insufficient.

## Verification

Focused checks after each data batch:

```bash
python -m unittest assets.test_data_consistency assets.test_location_resolution assets.test_action_generator assets.test_calc_variations
python tools/validate_prompt_data.py
python assets/calc_variations.py --json
```

Broader checks before commit:

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/verify_full_flow.py
python tools/check_widgets_values.py
```

Optional before/after delta:

```bash
python assets/calc_variations.py --json > assets/results/variation_after.json
python tools/report_expansion_delta.py assets/results/variation_before.json assets/results/variation_after.json
```

## Acceptance Criteria

- `unique_locations` increases by 8-10 or the deviation is explained in `progress.md`
- `base variations` reaches at least `15,000`
- promoted locations have semantic action coverage
- validator reports no errors or warnings
- no public workflow/node socket changes
