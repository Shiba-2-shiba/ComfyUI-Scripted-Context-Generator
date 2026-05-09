# 100k Stabilization and 500k Forward Plan

Last updated: 2026-05-08

## Goal

Record the completed 100k stabilization lane and define the current P13
planning surface for 500k.

Current targets:

- stabilized intermediate target: `100,000` base variations
- active planning horizon: `500,000` base variations

`base variations` currently means:

```text
sum(compatibility rows per location * action count for that location)
```

Current status for P13:

```text
100k target: achieved and stabilized
current base variations: 105,612
current surface: 120 subjects / 91 locations / 5,926 compatibility rows
current action depth: min 12 / median 16 / mean 15.6 / max 20
active planning horizon: 500,000 base variations
```

Starting baseline for this plan:

```text
unique subjects: 58
unique locations: 76
compatibility rows: 1,637
base variations: 15,610
actions per location: min 4 / median 8 / mean 8.03 / max 12
```

The earlier completed wave was:

```text
base variations: 11,916 -> 15,034
```

P8 then moved the active baseline to:

```text
base variations: 15,034 -> 15,610
```

## Re-planning Finding

The old P9 subject-promotion plan is too small for the new target.

Measured planning scenarios:

| Scenario | Subjects | Locations | Rows | Base variations |
| --- | ---: | ---: | ---: | ---: |
| current scope | 58 | 76 | 1,637 | 15,610 |
| all known subjects, current locations | 91 | 76 | 2,675 | 25,524 |
| current subjects, all action-backed compatible locations | 58 | 80 | 1,771 | 16,654 |
| all known subjects, all action-backed compatible locations | 91 | 80 | 2,881 | 27,140 |
| all known subjects/locations, minimum 24 actions per location | 91 | 80 | 2,881 | 69,144 |
| all known subjects/locations, minimum 35 actions per location | 91 | 80 | 2,881 | 100,835 |

Conclusion:

- Promoting all currently known subject candidates is useful but only reaches about `25k`.
- Existing location candidates add little unless the compatibility taxonomy is widened.
- Reaching `100k` by only raising each location to 35 actions would be possible, but it risks low-quality repetitive action pools.
- The better path is balanced expansion: increase compatibility rows and action depth together.

## Target Shape For 100k

Use this as the implementation target, not a hard schema requirement:

```text
subjects: 105-120
locations: 105-115
compatibility rows: 5,800-6,500
average actions per compatibility row: 16-18
base variations: 100,000+
```

This keeps the action count per location high enough to matter without forcing
every location to carry 35 near-duplicate actions.

## Implementation Plan

### P9: Add Target Modeling Before More Data

Status: `done`

Add a first-class planning tool so expansion work can be measured before CSV or
scope files are changed.

Proposed files:

- `tools/plan_variation_target.py`
- `assets/test_variation_target_planner.py`

Requirements:

- read `vocab/data/variation_scope.json`
- read `vocab/data/scene_compatibility.json`
- read `vocab/data/action_pools.json`
- report current metrics
- report candidate subject deltas
- report candidate location deltas
- simulate minimum action targets such as 12, 16, 20, 24, 32, 35
- optionally accept a target like `--target 100000`
- make no writes

Acceptance:

```bash
python tools/plan_variation_target.py --target 100000
python -m unittest assets.test_variation_target_planner
```

Current implementation:

- `tools/plan_variation_target.py`
- `assets/test_variation_target_planner.py`
- reports current metrics, candidate deltas, all-known-subject scenarios, and
  minimum action-depth scenarios without writing data files

### P10: Compatibility Taxonomy Expansion

Status: `done`

The compatibility graph needs more meaningful rows before action-pool growth
can pay off.

Data files:

- `vocab/data/scene_compatibility.json`
- `vocab/data/variation_scope.json`
- `assets/compatibility_review.csv` generated only through
  `tools/build_compatibility_review.py`

Work:

1. Promote distinct subject candidates from the 33 known candidates.
2. Reject near-duplicate labels in `progress.md` before editing scope.
3. Add mid-level compatibility tags instead of overusing broad `urban`:
   - `retail_service`
   - `daily_public`
   - `transit`
   - `home_life`
   - `workplace`
   - `leisure`
   - `quiet_indoor`
4. Move compatible subjects and locations onto these tags.
5. Use explicit exclusions for genuinely bad pairs.
6. Promote 25-35 new daily/common locations with background packs and source
   action pools.

Target after this phase:

```text
subjects: 120
locations: 91
compatibility rows: 5,926
base variations with current action depth: 52,121
```

P10 used the existing background/action surface instead of inventing new
locations solely to hit the original 105-115 location shape. The row/base target
was reached by adding mid-level tags, promoting all current compatibility
subjects into scope, adding distinct daily-life subjects, and adding missing
daily-life action pools.

Validation:

```bash
python tools/build_compatibility_review.py --write --output assets/compatibility_review.csv
python tools/build_compatibility_review.py --check
python tools/check_variation_scope.py
python tools/validate_prompt_data.py
python assets/calc_variations.py --json
```

### P11: Scalable Action Authoring Refactor

Status: `done`

Keep runtime stable:

- runtime source remains `vocab/data/action_pools.json`

Refactor only authoring:

- current source remains `vocab/source/action_pools/*.json`
- add shared authoring data only if it reduces duplication:
  - `vocab/source/action_pools/_shared_families.json`
  - optional per-location family references inside split source files
- `tools/build_action_pools.py` expands shared families into the runtime flat
  list

Do not add new dependencies.

Action depth targets:

```text
high-row locations: 20 actions
medium-row locations: 16 actions
low-row/specialized locations: 12 actions
actual result: 105,612 base variations on the P10 row surface
```

Authoring rules:

- actions stay semantic-only
- no object overconcentration
- no repeated phrasing with only prop swaps
- no location file should grow by copy-paste when a shared family can express
  the repeated pattern

Acceptance:

```bash
python tools/build_action_pools.py --write
python tools/build_action_pools.py --check
python -m unittest assets.test_build_action_pools assets.test_action_generator assets.test_action_diversity_audit assets.test_repetition_guard_audit
python assets/calc_variations.py --json
```

Target after this phase:

```text
compatibility rows: 5,926
actions per location: min 12 / median 16 / mean 15.6 / max 20
base variations: 105,612
```

Implementation result:

- added `vocab/source/action_pools/_shared_families.json`
- added per-location `families` refs to source action-pool files
- kept runtime loading stable by expanding refs into `vocab/data/action_pools.json`
- added regression coverage for shared family expansion

### P12: 100k Stabilization Gate

Status: `done`

Lock the new scale before moving toward 500k.

Acceptance:

```bash
python tools/plan_variation_target.py --target 100000
python tools/check_variation_scope.py
python tools/build_compatibility_review.py --check
python tools/build_action_pools.py --check
python tools/validate_prompt_data.py
python -m unittest discover -s assets -p "test_*.py"
python tools/verify_full_flow.py
```

Docs to update:

- `docs/variation_expansion/progress.md`
- `docs/variation_expansion/tasks.md`
- `docs/variation_expansion/README.md`

Verification result:

- current measured base variations: `105,612`
- target planner: target met for `100000`
- scoped compatibility review, action-pool source rebuild, prompt data
  validation, full asset unittest discovery, and full flow verification passed

### P13: 500k Target Planning

Status: `active planning`

Before adding more data, model the next shape with the same discipline used for
the 100k lane. The likely variables are:

- subject count
- location count
- compatibility density
- median action depth
- action-family reuse quality

Do not begin by bulk-adding subjects or actions. First measure what combination
can reach `500,000` without weakening semantic quality or making action text
feel repetitive.

P13 should produce a scenario note before implementation. At minimum, record:

- current `--target 500000` planner output
- subject-only, location-only, compatibility-density, and action-depth scenarios
- the first limiter to address
- rejected inflation routes, especially near-duplicate subjects or action-only growth
- verification commands that will prove the selected route did not drift from
  the P12 clean baseline

## 500k Forward Constraint

Do not solve 500k by making the 100k implementation noisy.

The likely 500k shape is:

```text
subjects: 150-180
locations: 150-180
compatibility density: 60-75%
median actions: 24-32
base variations: 500,000+
```

That requires the 100k work to leave these foundations in place:

- scenario planning tool
- explicit variation scope
- regenerable compatibility review
- scalable action authoring source
- strong diversity/repetition audits

## P13 Acceptance Criteria

Planning is complete when:

- `python tools/plan_variation_target.py --target 500000` has been run and summarized
- the chosen 500k route identifies which files will change first
- compatibility density and action-depth tradeoffs are explicit
- subject/location candidates are grouped by distinct prompt utility, not only
  by metric impact
- guardrails for action-family reuse are written before expanding pools again
- P12 checks remain the baseline for any later implementation pass

## Guardrails

- Do not edit `assets/compatibility_review.csv` by hand.
- Do not edit `vocab/data/action_pools.json` by hand for normal authoring.
- Do not broaden `variation_scope.json` without measuring expected metrics.
- Do not use near-duplicate subjects just to inflate row count.
- Do not use action count alone as the primary route to 100k.
- Keep public node/runtime behavior unchanged unless a separate task explicitly
  asks for runtime changes.
