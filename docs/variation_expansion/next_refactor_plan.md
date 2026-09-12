# Completed Refactor Plan

Last updated: 2026-05-08

This file is a completed-plan record for the P5-P12 refactor lane. It is not
the active next-work entry point.

Active work has moved to **P13: 500k target planning**. Use:

- [Progress](./progress.md)
- [Task Board](./tasks.md)
- [100k Stabilization and 500k Forward Plan](./base_variations_100k_plan.md)

## Goal

Make future variation expansion predictable by separating completed expansion
history from the active expansion scope.

This completed work reduced hidden coupling around:

- which subjects count toward base variation sizing
- which locations count toward base variation sizing
- how `assets/compatibility_review.csv` is validated or regenerated
- how large action pools are authored without making runtime loading more complex

## Roadmap

### 1. Define Variation Scope

Status: `done`

Create a source-of-truth data file for current variation sizing boundaries.

Current file:

- `vocab/data/variation_scope.json`

It owns:

- `variation_subjects`
- `variation_locations`
- `expected_metrics`
- completed wave locations
- next candidate locations

Validation:

```bash
python tools/check_variation_scope.py
python -m unittest assets.test_variation_scope
```

Current state:

- Current restricted scope has 120 subjects and 90 locations.
- All current variation-scope locations have direct background packs.
- `tools/check_variation_scope.py` should stay clean (`ERROR: []`, `WARNING: []`)
  before any P13 promotion wave is accepted.

### 2. Make Compatibility Review Regenerable

Status: `done`

Add a scoped generator for `assets/compatibility_review.csv`.

Requirements:

- read `vocab/data/variation_scope.json`
- read `vocab/data/scene_compatibility.json`
- preserve stable row ordering
- fail if generation would introduce subjects or locations outside scope
- support `--check` before `--write`

Do not replace the current CSV blindly until generated rows match the intended current scope.

Current implementation:

- `tools/build_compatibility_review.py --check` generates scoped candidate rows and
  compares them to `assets/compatibility_review.csv`.
- `assets/compatibility_review.csv` has been normalized from the generator output.
- The check now reports `ERROR: []`, `WARNING: []`, and no row or pair drift.
- Current generated rows after later variation restrictions: `5,806`.
- `prompts.jsonl` rows are aligned to the current variation scope.

### 3. Split Action Pool Authoring Surface

Status: `done`

Runtime source remains stable:

- `vocab/data/action_pools.json`

Authoring source:

- `vocab/source/action_pools/_manifest.json`
- `vocab/source/action_pools/*.json`
- `tools/build_action_pools.py`

Current implementation:

- The split source has 96 location files plus `_shared_families.json`.
- `tools/build_action_pools.py --check` verifies that split source rebuilds
  `vocab/data/action_pools.json` exactly.
- Runtime loaders still read only `vocab/data/action_pools.json`.

### 4. Expand Remaining Daily-Life Candidates

Status: `done`

Candidate locations:

- `food_court`
- `coworking_space`
- `community_center`
- `apartment_balcony`
- `apartment_entryway`
- `public_library_lobby`
- `riverside_walk`
- `laundromat`

Do this after scope validation and compatibility review generation are stable.

P8 result:

- unique locations: `68 -> 76`
- compatibility rows: `1,565 -> 1,637`
- base variations: `15,034 -> 15,610`
- action pools: `79 -> 87`
- actual delta: `+576`

Detailed execution plan:

- `docs/variation_expansion/next_expansion_wave_plan.md`

### 5. Expand Subjects

Status: `superseded by 100k target planning`

Subject expansion should wait until subject promotion rules are explicit, but
the new 100k intermediate target means subject promotion alone is no longer
large enough. Use
`docs/variation_expansion/base_variations_100k_plan.md` as the current plan.

Do not add subjects only by making `scene_compatibility.characters` larger.
Promote subjects by updating `variation_scope.json` and then regenerating/checking `compatibility_review.csv`.

P8 has been measured and documented. P9 should now start by adding target
modeling and scenario measurement before any subject promotion.

### 6. Plan Toward 100k Base Variations

Status: `done; superseded by P13 500k planning`

The 100k implementation lane added a read-only target planner, then expanded
compatibility taxonomy and action authoring together.

Original planning finding:

- current scope: `15,610`
- all known subjects and compatible action-backed locations with current
  actions: `27,140`
- all known subjects and compatible action-backed locations with minimum 35
  actions: `100,835`

Because the minimum-35-actions route risks repetitive action text, the preferred
target shape is `5,800-6,500` compatibility rows with median `16+` actions.

P12 stabilized the result at:

```text
subjects: 120
locations: 91
compatibility rows: 5,926
base variations: 105,612
actions per location: min 12 / median 16 / mean 15.6 / max 20
```

Later variation restrictions reduced the active counted surface to:

```text
subjects: 120
locations: 90
compatibility rows: 5,806
base variations: 103,212
actions per location: min 12 / median 16 / mean 15.6 / max 20
```

Current successor plan:

- `docs/variation_expansion/base_variations_100k_plan.md`

## Acceptance Criteria For This Refactor Lane

This lane is complete. Continue to use these as regression checks before any
P13 implementation pass:

- `python tools/check_variation_scope.py` reports no errors
- `python tools/validate_prompt_data.py` reports no errors
- `python assets/calc_variations.py --json` remains stable unless a deliberate expansion changes expected metrics
- docs distinguish completed waves from active P13 work
