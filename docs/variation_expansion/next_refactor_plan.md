# Next Refactor Plan

Last updated: 2026-05-08

## Goal

Make future variation expansion predictable by separating completed expansion history from the active expansion scope.

The next work should reduce hidden coupling around:

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

Current caveat:

- `tools/check_variation_scope.py` allows existing scoped locations that are present in
  compatibility/action data even when a direct background pack is still missing.
- Missing direct background packs are warnings, not errors, until the scoped generator
  makes background coverage part of the write path.

### 2. Make Compatibility Review Regenerable

Status: `next`

Add a scoped generator for `assets/compatibility_review.csv`.

Requirements:

- read `vocab/data/variation_scope.json`
- read `vocab/data/scene_compatibility.json`
- preserve stable row ordering
- fail if generation would introduce subjects or locations outside scope
- support `--check` before `--write`

Do not replace the current CSV blindly until generated rows match the intended current scope.

### 3. Split Action Pool Authoring Surface

Status: `later`

Keep runtime source stable:

- `vocab/data/action_pools.json`

Add an authoring surface only if review pain remains concrete:

- candidate path: `vocab/source/action_pools/*.json`
- candidate builder: `tools/build_action_pools.py`

The runtime loader should not change until generated output is proven stable.

### 4. Expand Remaining Daily-Life Candidates

Status: `later`

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

### 5. Expand Subjects

Status: `later`

Subject expansion should wait until subject promotion rules are explicit.

Do not add subjects only by making `scene_compatibility.characters` larger.
Promote subjects by updating `variation_scope.json` and then regenerating/checking `compatibility_review.csv`.

## Acceptance Criteria For This Refactor Lane

- `python tools/check_variation_scope.py` reports no errors
- `python tools/validate_prompt_data.py` reports no errors
- `python assets/calc_variations.py --json` remains stable unless a deliberate expansion changes expected metrics
- docs distinguish completed waves from active next work
