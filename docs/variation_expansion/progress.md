# Variation Expansion Progress

Last updated: 2026-09-01

## Status Summary

Overall status: `P12 verified; P13 staged loop planning active`

Current phase: `P13 V150 blind review remediation after attempt 001 rejection`

Active sidecar cleanup: `P14 clothing state location gate` - verified

Primary target:

- variation scope を明示して、意図しない subject / location 増加を防ぐ
- `compatibility_review.csv` の scoped check-only generator で差分を固定する
- 第2波の daily-life location 追加前にデータ境界を軽くする
- P10 compatibility taxonomy expansion、P11 action authoring refactor、P12
  100k stabilization gate は完了済み。次は現行 planner を基準に
  V150/V250/V350/V500 の段階拡張を設計する

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

## Current Snapshot After Later Variation Restrictions

Measured on: 2026-06-19

```text
unique subjects: 120
unique locations: 90
base variations: 103,212
compatibility rows: 5,806
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
| P13 | Staged 500k loop planning | Active: L3 post-rejection loop | Planner L0-L3 + V150/V250/V350/V500 gates | Iteration 004 reached 150,184 and improved entropy, then failed coverage/repetition/context guards |
| P14 | Gate clothing state details by Location | Done | 0 | 0 |
| P15 | Apply variation restrictions and refresh current baseline | Done | -2,400 | 103,212 |

## P13 Current Direction

The active work is the staged 500k engineering loop defined in
`500k_loop_plan.md`. Before changing data, preserve the current planner behavior,
freeze the baseline inputs, add mixed hypothetical modeling in tested passes,
and decide whether the first limiter is subject count, location count,
compatibility density, or action depth.

P13 should start from:

```bash
python tools/plan_variation_target.py --target 500000
```

Record the chosen route before editing `variation_scope.json`,
`scene_compatibility.json`, `assets/compatibility_review.csv`, or
`vocab/source/action_pools/`.

Every stage must also preserve the accepted prompt-quality baseline under
`docs/prompt_quality/`. Quantity-only promotion is prohibited. Control and
exploration cohorts, blind review, confirmation, and the final verdict must be
bound to the candidate and evidence hashes.

L0 completed on 2026-09-01:

- Captured the current 500k planner probe at `103,212` base variations.
- Locked planner, scope, compatibility, action-pool, policy, cohort, and G010
  receipt hashes in `experiments/v150-planner-l0/manifest.json`.
- Classified all six non-counted runtime pools: four runtime alias-compatible,
  one legacy-only, and one quality-excluded. No staged candidate remains.
- Added `planner_refactor_spec.md` for the backward-compatible L1-L3 boundary,
  deterministic projection math, validation, tests, and prompt-quality handoff.

L1 completed on 2026-09-01:

- Added optional `--scenario-file` without changing the default report.
- Added integer-only mixed projection math and deterministic largest-remainder
  allocation.
- Added explicit proposed subject/location identities, exact delta binding,
  current-scope checks, and non-counted pool rejection.
- Added V150/150000 stage binding, L0 manifest and protected-input hash checks,
  stable CLI errors, and source non-mutation tests.
- Passed 21 focused planner tests, 33 related tests, data checks, full-flow,
  independent code review, and independent verification.
- Promoted only the planner capability. No V150 variation-data candidate was
  selected or promoted.

Evidence:

- `experiments/v150-planner-l1/verification.json`
- `experiments/v150-planner-l1/receipt.json`
- `planner_l1_contract.md`

Next action: L2 quality-aware analysis of real canonical subject/location
proposals. A synthetic projection fixture is not a data candidate.

L2 analyzer completed on 2026-09-01:

- Added read-only candidate catalog analysis with scenario/hash binding.
- Added canonical/scope/alias/pool collision gates, compatibility coverage,
  utility claims, shared-family validation, policy scan, duplicate pressure, and
  strict `not_evaluated` prompt-quality state.
- Passed 18 focused analyzer tests and 41 combined L1/L2 tests after independent
  code review and verification.

L2 candidate iteration 001 result:

- Numerical projection reached `150,436` base variations.
- Candidate metadata supported only `7,817 / 8,646` projected rows.
- Exact action duplicate pressure was `5,000 bp` against a `1,000 bp` limit.
- Prompt quality remained `not_evaluated`; no candidate data was generated.
- Terminal verdict: `REJECTED`.

Evidence:

- `candidate_l2_contract.md`
- `experiments/v150-candidate-l2/analysis-report.json`
- `experiments/v150-candidate-l2/rejection-receipt.json`

L2 candidate iteration 002 result:

- Kept the same 15 subject and 15 location utility claims.
- Adjusted projected density to the measured compatibility surface.
- Authored `300` candidate actions: `200` direct and `100` bounded shared-family
  actions.
- Structural coverage passed at `7,817 / 7,796` rows (`+21`).
- Exact candidate duplicates: `0`; direct-to-existing pressure: `50 bp`.
- Replaced five mismatched shared-family slices after independent semantic review.
- Structural status: `pass`; eligible for prompt evaluation: `true`.
- Prompt quality remains `not_evaluated`; promotion ready remains `false`.

Evidence:

- `experiments/v150-candidate-l2-iteration-002/analysis-report.json`
- `experiments/v150-candidate-l2-iteration-002/handoff-receipt.json`

L3 snapshot iteration 001 result:

- Built separate filtered baseline and candidate runnable roots under ignored
  `assets/results/` without modifying active source.
- Materialized all 15 subjects, 15 locations, and 15 × 20 action pools.
- Rebuilt compatibility CSV and action runtime inside the candidate root.
- Realized `7,817` rows and `141,984` base variations.
- L2 projection was `155,920`; realized delta was `-13,936`.
- V150 target gap was `8,016`, so state is `REJECTED` and
  `prompt_generation_allowed=false`.
- No 64+16 prompt artifacts were generated.
- Added a contribution model that reproduces the isolated snapshot by separating
  new-subject/current-location and new-location action depths.
- Hardened plan/manifest authentication against derived-field, decision-field,
  allowlist, and runtime-extra drift.

Evidence:

- `candidate_l3_contract.md`
- `experiments/v150-candidate-l3-iteration-001/rejection-receipt.json`

L3 shape iteration 003:

- Added an exact contribution planner that separates existing-location and
  candidate-location action depths.
- Selected four new locations contributing `410` rows and `8,200` variations.
- Estimated result: `150,184`, overshoot `184`.
- Adds no subjects and no racial/skin-color descriptors.
- Exact artifact and receipt hash tests passed; independent review and
  verification approved isolated action authoring.

Evidence:

- `experiments/v150-candidate-shape-iteration-003/location-addition-report.json`
- `experiments/v150-candidate-shape-iteration-003/handoff-receipt.json`

L3 shape iteration 004:

- Authored the approved `4 × 20` location-specific actions and composed a
  15-subject / 19-location candidate with zero exact candidate duplicates.
- Materialized an authenticated q5 snapshot at `150,184` base variations.
- Re-ran the fixed 64-control + 16-exploration cohort with exact replay and
  authenticated workflow/profile/override/source/artifact bindings.
- Improved location entropy by `+0.411080`, with zero unseen candidate subjects
  and no identity, demographic, consistency, policy, replay, or fallback issue.
- Rejected at `COMPARED`: 8 candidate locations and 13 actual location-action
  pools were unseen; repeated n-grams increased `12 -> 16`; context max and p95
  increased by `1,336` and `605.35` bytes.
- Blind review and confirmation were not run. Active variation data was not
  changed or promoted.

Evidence:

- `experiments/v150-candidate-shape-iteration-004/prompt-pair-comparison.json`
- `experiments/v150-candidate-shape-iteration-004/rejection-receipt.json`

Next action: design a deterministic coverage supplement and reduce repetition
and context size in a new isolated iteration before repeating the 64+16 gate.

L3 coverage schedule iteration 005:

- Rejected selected-seed search to avoid coverage-selection bias.
- Added an immutable pre-snapshot coverage contract and a one-way
  `contract -> schedule -> snapshot -> experiment` hash chain.
- Deterministically matched all 15 subjects to 19 locations and selected 19
  unique direct actions without changing the fixed 64+16 cohort.
- Added schedule-aware snapshot materialization, raw prompt JSONL validation,
  exact final location-action comparison, and fixed-reject authority separation.
- Source-selector preflight reached 19/19 rows, but the actual full workflow
  reached only 12/19 candidate locations and 9/19 exact scheduled pairs.
- Coverage verdict and fixed quality verdict are both `reject`; active data and
  promotion remain unchanged.
- Repeated n-grams improved `12 -> 9`, while context max/p95 still regressed.
- A post-snapshot CLI hardening now makes process exit status follow the fixed
  quality verdict rather than the diagnostic coverage verdict. The next
  snapshot must bind this hardened comparator before another scheduled run.

Evidence:

- `experiments/v150-candidate-shape-iteration-005/coverage-contract.json`
- `experiments/v150-candidate-shape-iteration-005/coverage-plan.json`
- `experiments/v150-candidate-shape-iteration-005/coverage-comparison.json`
- `experiments/v150-candidate-shape-iteration-005/rejection-receipt.json`

Next action: plan final witness coverage through the complete workflow,
including `ContextSceneVariator` full-mode location/action resolution.

L3 full-workflow coverage iteration 006:

- Corrected action-pool evidence to use the final SceneVariator decision and
  require raw `base_action` after an action refresh.
- Probed 13,760 fixed-cohort row/slot combinations and stored a compact,
  hash-bound witness matrix with 2,801 valid edges.
- Found a deterministic assignment covering all 19 final candidate locations,
  all 15 subjects, and all 19 exact final location-action witnesses with zero
  extra seeds.
- Materialized q9 under current source and replayed the 19-witness certificate.
- Formal fixed 64+16 comparison passed all subject/location/action coverage
  gates and kept `coverage_is_quality_evidence=false`.
- Quality remains rejected: semantic-family repetition `3 -> 5`, context max
  `29,094 -> 30,570`, and context p95 `28,692.15 -> 28,922.05`.

Evidence:

- `experiments/v150-candidate-shape-iteration-006/full-workflow-coverage-contract.json`
- `experiments/v150-candidate-shape-iteration-006/witness-matrix.json`
- `experiments/v150-candidate-shape-iteration-006/full-workflow-schedule.json`
- `experiments/v150-candidate-shape-iteration-006/coverage-comparison.json`
- `experiments/v150-candidate-shape-iteration-006/rejection-receipt.json`

Next action: freeze the coverage schedule and remediate semantic-family
repetition plus context p95/max under a new quality hypothesis.

L3 guard remediation iteration 007:

- Preserved the frozen 19/19 coverage schedule and exact fixed64+16 cohort.
- Corrected semantic-family substring false positives without changing prompts.
- Bounded SceneVariator candidate preview and compacted redundant clothing
  history/debug fields while preserving selection and repetition signatures.
- q13 changed zero cleaned prompts versus q9 on both baseline and candidate.
- Coverage remained 19/19 with zero extra seeds and replay mismatch zero.
- All diagnostic target/guard comparisons passed; context max and p95 are now
  below baseline and semantic-family repetition is equal to baseline.
- Fixed quality verdict remains `reject` because this is a selected coverage
  surface, not promotion evidence.

Evidence:

- `experiments/v150-candidate-shape-iteration-007/prompt-quality-experiment.json`
- `experiments/v150-candidate-shape-iteration-007/guard-comparison.json`
- `experiments/v150-candidate-shape-iteration-007/guard-remediation-receipt.json`

Next action: run a separately declared non-selected quality validation surface
before any blind review or confirmation decision.

L3 non-selected quality validation iteration 008:

- Refreshed the 19/19 coverage certificate against current source and bound the
  exact candidate source tree into a closed quality contract.
- Materialized default 80-row baseline/candidate inputs with no prompt schedule.
- Generated and replayed the unchanged fixed 64+16 cohort while recomputing
  automatic quality metrics from control64 only.
- Kept current-run partial coverage informational and used the separate 19/19
  certificate solely as eligibility evidence.
- Passed target and all quality guards; automatic quality and combined
  validation verdicts are `pass`, and the comparison is review-ready.
- Promotion remains false; no blind review or confirmation has run.

Evidence:

- `experiments/v150-candidate-shape-iteration-008/current-source-coverage-refresh.json`
- `experiments/v150-candidate-shape-iteration-008/nonselected-quality-contract.json`
- `experiments/v150-candidate-shape-iteration-008/quality-experiment.json`
- `experiments/v150-candidate-shape-iteration-008/quality-comparison.json`
- `experiments/v150-candidate-shape-iteration-008/quality-validation-receipt.json`

Next action: freeze q19 and run comparison-bound blind review, fresh 3x256
confirmation lanes, and full verification before a V150 promotion decision.

After VE-1317 and VE-1318 both pass, VE-1319 performs the actual active-data
promotion. It is the task that changes the repository from the current active
`103,212` surface to the verified V150 candidate (`150,184`). VE-1319 remains
blocked until both prerequisite receipts are present and valid.

VE-1317 blind review attempt 001:

- Built two independent blinded 20-pair lanes bound to the q19 comparison.
- Aggregate hash validation passed, but the review verdict was `reject`.
- Candidate-only hard defects: 8 observations across 5 seeds; 3
  location/action/object conflicts and 5 mood/action/garnish conflicts.
- Naturalness, redundancy, protagonist clarity, and image-prompt suitability
  did not meet the qualitative thresholds.
- VE-1318 and VE-1319 remain blocked. The next loop remediates the five seeds,
  reruns automatic validation, and creates blind-review attempt 002.

## P14 Clothing State Location Gate

Status: `verified`

This is a prompt-quality cleanup lane, not a variation-sizing expansion lane.
It should keep public node behavior and data schemas stable while preventing
environment-specific clothing `states` from appearing in incompatible
Locations.

Completed result:

- `covered in snow` has already been identified as unsafe for indoor Locations.
- Similar risks exist for `rain-soaked` / `wet`, `sun-kissed glow`, `sweaty`,
  `battle-worn` / `blood-stained`, and `grease stained`.
- Added a shared state-family location gate in `pipeline/clothing_builder.py`.
- Added negative and positive regression tests for snow, wet, sun/beach,
  exertion, battle damage, and workshop dirt state families.
- Updated prompt snapshots only where incompatible state text was intentionally
  removed.

Plan:

- [Clothing State Location Gate Refactor Plan](./clothing_state_location_gate_plan.md)

Verified behavior:

- incompatible indoor prompts do not receive snow/wet/sun/sweaty/battle/grease
  state details
- compatible Locations still allow the relevant state family
- `assets/compatibility_review.csv`, `variation_scope.json`, and action-pool
  data remain unchanged

Remaining compatibility-level risk:

- State gating does not change broad costume/location compatibility. A costume
  family such as `fantasy_battle`, `beach_resort`, or `gym_workout` can still
  appear in broadly compatible daily-public Locations; only the most
  environment-specific `states` are suppressed.

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

Later variation restrictions intentionally reduced the current counted surface
to `103,212` base variations while keeping the 100k target satisfied.

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
| 2026-06-19 | `python tools/check_variation_scope.py` | Pass | `ERROR: []`, `WARNING: []`; base variations `103,212` |
| 2026-06-19 | `python tools/build_compatibility_review.py --check` | Pass | generated/current rows `5,806`; pair drift `0` |
| 2026-06-19 | `python assets/calc_variations.py --json` | Pass | current restricted surface: 120 subjects / 90 locations / 103,212 base variations |
| 2026-06-19 | `python -m unittest assets.test_calc_variations assets.test_variation_target_planner assets.test_variation_scope assets.test_build_compatibility_review assets.test_build_action_pools` | Pass | 15 tests OK |
| 2026-05-08 | `python assets/calc_variations.py --json` | Pass | baseline captured |
| 2026-05-08 | `python tools/validate_prompt_data.py` | Pass | `ERROR: []`, `WARNING: []` |
| 2026-05-08 | `python -m unittest assets.test_data_consistency assets.test_location_resolution assets.test_action_generator assets.test_calc_variations` | Pass | 27 tests OK |
| 2026-05-08 | `python -m unittest assets.test_action_generator assets.test_action_diversity_audit assets.test_repetition_guard_audit` | Pass | 22 tests OK |
| 2026-05-08 | `python -m unittest discover -s assets -p "test_*.py"` | Pass | 253 tests OK |
| 2026-05-08 | `python tools/verify_full_flow.py` | Pass | OK |
| 2026-05-09 | `python -m unittest assets.test_context_content_pipeline` | Pass | 23 tests OK; state-family gates covered |
| 2026-05-09 | `python -m unittest assets.test_prompt_snapshots` | Pass | snapshots updated for removed incompatible state details |
| 2026-05-09 | `python -m unittest assets.test_determinism assets.test_registry` | Pass | 10 tests OK |
| 2026-05-09 | `python tools/validate_prompt_data.py` | Pass | `ERROR: []`, `WARNING: []` |
| 2026-05-09 | `python tools/check_variation_scope.py` | Pass | `ERROR: []`, `WARNING: []`; base variations `105,612` |
| 2026-05-09 | `python tools/build_compatibility_review.py --check` | Pass | generated/current rows `5,926`; pair drift `0` |
| 2026-05-09 | `python tools/build_action_pools.py --check` | Pass | runtime/source location count `96` |
| 2026-05-09 | `python assets/calc_variations.py --json` | Pass | base variations unchanged at `105,612` |
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
