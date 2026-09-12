# Completed P8 Expansion Wave Plan

Last updated: 2026-05-08

This file records the completed P8 wave and the superseded P9 subject-only
evaluation. It is not the active next-work plan.

Active work has moved to **P13: 500k target planning**. Use:

- [Progress](./progress.md)
- [Task Board](./tasks.md)
- [100k Stabilization and 500k Forward Plan](./base_variations_100k_plan.md)

## Direction

This plan records the completed P8 wave and the original P9 subject evaluation.
The `100,000` base variation intermediate target has since been achieved and
stabilized. For the current 500k planning surface, use
`docs/variation_expansion/base_variations_100k_plan.md`.

The completed revised order was:

1. Increase `unique locations`.
2. Re-check variation balance and action quality.
3. Add target modeling for `100,000` base variations.
4. Expand compatibility taxonomy and action authoring together.

Do not promote subjects as a standalone inflation step. Subject promotion
multiplies against the current location/action surface, so future subject work
should happen inside the P13 target model.

## P8 Completion Baseline

Measured with:

```bash
python assets/calc_variations.py --json
python tools/validate_prompt_data.py
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
```

P8 completion values:

- unique subjects: `58`
- unique locations: `76`
- compatibility review rows: `1,637`
- base variations: `15,610`
- runtime action pools: `87`
- split action source location files: `87`
- location candidates: `93`
- action-generatable locations: `93`

## P8: Increase Unique Locations

Status: `done`

Goal: promote the remaining daily-life candidate locations already listed in
`vocab/data/variation_scope.json`.

All P8 candidates have background packs and dedicated action pools.

| Location | Compatibility tag | Estimated new rows | Target actions | Estimated base variation delta |
| --- | --- | ---: | ---: | ---: |
| `food_court` | `urban` | 27 | 8 | +216 |
| `coworking_space` | `office` | 6 | 8 | +48 |
| `community_center` | `suburban` | 11 | 8 | +88 |
| `apartment_balcony` | `domestic` | 2 | 8 | +16 |
| `apartment_entryway` | `domestic` | 2 | 8 | +16 |
| `public_library_lobby` | `suburban` | 11 | 8 | +88 |
| `riverside_walk` | `suburban` | 11 | 8 | +88 |
| `laundromat` | `domestic` | 2 | 8 | +16 |

P8 actual result:

- unique locations: `68 -> 76`
- compatibility review rows: `1,565 -> 1,637`
- base variations: `15,034 -> 15,610`
- action pools: `79 -> 87`
- actual base variation delta: `+576`

P8 implementation sequence:

1. Add 8 semantic actions for each candidate in
   `vocab/source/action_pools/<location>.json`.
2. Rebuild runtime actions:

```bash
python tools/build_action_pools.py --write
python tools/build_action_pools.py --check
```

3. Promote locations in `vocab/data/variation_scope.json`.
4. Regenerate scoped compatibility review:

```bash
python tools/build_compatibility_review.py --write --output assets/compatibility_review.csv
python tools/build_compatibility_review.py --check
```

5. Update expected metrics in `variation_scope.json` after measuring:

```bash
python assets/calc_variations.py --json
```

6. Run focused validation:

```bash
python tools/validate_prompt_data.py
python tools/check_variation_scope.py
python -m unittest assets.test_build_action_pools assets.test_action_generator assets.test_action_diversity_audit assets.test_repetition_guard_audit assets.test_variation_scope assets.test_build_compatibility_review
```

P8 acceptance criteria:

- `unique_locations` increases to `76`, unless a candidate is explicitly
  deferred with a reason in `progress.md`.
- `base variations` increases without increasing `unique_subjects`.
- `tools/check_variation_scope.py` reports `ERROR: []`, `WARNING: []`.
- `tools/build_compatibility_review.py --check` reports no drift.
- `tools/build_action_pools.py --check` reports no drift.
- New action text stays semantic-only and parses into action slots.

## P9: Evaluate Unique Subjects

Status: `superseded by 100k target planning`

Goal: decide whether subject expansion should start after P8. P9 is an
evaluation gate first, not an automatic subject promotion wave.

Current subject candidate pool:

- compatibility characters outside `variation_scope.variation_subjects`: `33`
- subject promotion must update `variation_scope.json`
- subject promotion must regenerate/check `assets/compatibility_review.csv`
- subject promotion should not be done only by adding entries to
  `scene_compatibility.characters`

High-impact candidates after P8:

| Subject | Tags | Costume | Estimated rows | Estimated base variation delta |
| --- | --- | --- | ---: | ---: |
| `project assistant` | `office`, `urban`, `suburban` | `office_lady` | 40 | +368 |
| `office girl` | `office`, `urban`, `suburban` | `office_lady` | 40 | +368 |
| `lunch break girl` | `office`, `urban`, `suburban` | `office_lady` | 40 | +368 |
| `commuter` | `office`, `urban`, `suburban` | `office_lady` | 40 | +368 |
| `after work shopper` | `office`, `urban`, `suburban` | `office_lady` | 40 | +368 |
| `library visitor` | `school`, `suburban`, `urban` | `cozy_cafe` | 38 | +355 |
| `weekend traveler` | `suburban`, `urban`, `resort` | `urban_shopping` | 36 | +335 |
| `food court visitor` | `urban`, `suburban`, `resort` | `urban_shopping` | 36 | +335 |
| `dancer girl` | `music`, `urban`, `resort` | `exotic_dancer` | 35 | +321 |
| `street girl` | `urban`, `suburban` | `street_casual` | 33 | +319 |

P9 evaluation sequence:

1. Recompute subject candidate deltas after P8.
2. Group candidates by role overlap and costume reuse.
3. Select a small first subject wave only if it adds meaningfully distinct
   roles, not just duplicate labels over the same tags.
4. Decide target subject count before editing `variation_scope.json`.
5. Document accepted and rejected candidates in `progress.md`.

P9 acceptance criteria before subject promotion:

- P8 is complete and verified.
- Candidate subjects have resolved costumes and compatibility tags.
- Chosen subjects add distinct prompt utility or coverage.
- Expected base variation increase is documented before writing CSV changes.
- Rejected near-duplicates are recorded so they are not re-evaluated
  repeatedly.

## P9 Replacement: Target Modeling For 100k

Status: `done; superseded by P13 500k planning`

The previous P9 subject-only gate remains useful as historical input, but it
was too small for the 100k target. The replacement P9 added a read-only target
planning tool and scenario report.

P12 later stabilized the surface at:

```text
subjects: 120
locations: 91
compatibility rows: 5,926
base variations: 105,612
```

Later variation restrictions reduced the active counted surface to:

```text
subjects: 120
locations: 90
compatibility rows: 5,806
base variations: 103,212
```

See:

- `docs/variation_expansion/base_variations_100k_plan.md`

## Guardrails

- P8 kept `unique_subjects` fixed.
- Do not use subject promotion to compensate for weak location/action coverage.
- Do not broaden `variation_scope.json` without regenerating and checking
  `assets/compatibility_review.csv`.
- Do not edit `vocab/data/action_pools.json` directly for normal authoring;
  edit `vocab/source/action_pools/*.json`, then rebuild.
- For current work, apply these guardrails through the P13 500k target model
  instead of reopening this completed P8 plan.
