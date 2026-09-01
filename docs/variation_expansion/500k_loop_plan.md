# Staged 500k Variation Engineering Loop

Last updated: 2026-09-01

This is the canonical active plan for P13. It keeps
`tools/plan_variation_target.py` as the planning core and extends its capability
through verified iterations rather than replacing it or bulk-editing data first.

## Baseline

```text
subjects: 120
locations: 90 counted / 96 action-pool sources
compatibility rows: 5,806
base variations: 103,212
action depth: min 12 / median 16 / mean 15.56 / max 20
missing counted action pools: 0
```

The current `--target 500000` report is a baseline probe, not an executable
500k plan. All known subject and compatible-location candidate sets are already
exhausted, and the current uniform minimum-action scenarios reach only 203,210
at 35 actions.

## Objective

Reach 500,000 useful base variations through staged growth while preserving:

- distinct prompt utility rather than near-duplicate count inflation
- semantic-only policy and cross-domain consistency
- deterministic generation
- action-family diversity and acceptable repetition
- regenerable scope, compatibility, and action-pool artifacts
- stable public node and workflow contracts
- the currently adopted prompt-quality baseline and promotion contract under
  `docs/prompt_quality/`

Base variation count is a target metric, not sufficient promotion evidence by
itself.

## Prompt-Quality Compatibility Contract

Variation expansion must preserve the quality achieved by the prompt-quality
engineering loop. Each stage reuses, rather than weakens or replaces:

- workflow-faithful generation through `tools/workflow_prompt_runner.py`
- quality policy in `vocab/data/prompt_quality_policy.json`
- consistency rules in `rules/consistency_rules.json`
- deterministic control/exploration cohorts from `tools/prompt_quality_loop.py`
- comparison and review scope bound to the candidate and cohort hashes
- the completed release and target/guard contract identified by
  `docs/prompt_quality/README.md`

The normal evaluation cohort is the fixed 64-control + 16-exploration shape.
A promoted stage also requires the accepted three independent 256-seed
confirmation lanes for semantic consistency, naturalness, and diversity.
Existing accepted prompt-quality thresholds are a floor. A variation experiment
may make them stricter, but may not silently relax them to reach the numeric
target.

Until a newer prompt-quality receipt is completed and independently approved,
every stage pins its quality baseline to:

```text
release: G010 strict aggregate receipt
protected source tree: 40848f5c9b37ffbcc7dec0e89f60d52e59a23ec5877536b24134a19b43fc3447
verification SHA-256: 05bf5c9c7d95c11e282b401805434e23e27b38805e3b7497735045c88fd838d3
promotion SHA-256: d37b3f58df45987b6cb0165ab5d77eabee662069b9f83473e54a87690bbd552d
blind review: final-blind-review-attempt-015
```

Required guard dimensions include at least semantic consistency, naturalness,
image-prompt suitability, protagonist clarity, redundancy, and diversity. A
candidate with a material regression in a guard dimension is rejected even when
its base-variation target is met.

## Loop State Contract

Every stage and planner enhancement follows the prompt-quality lifecycle:

```text
DRAFT
  -> HYPOTHESIS_LOCKED
  -> BASELINE_READY
  -> CANDIDATE_SNAPSHOT_LOCKED
  -> GENERATED
  -> ANALYZED
  -> COMPARED
  -> REVIEWED
  -> VERIFIED
  -> PROMOTED | REJECTED
```

Any non-terminal state may become `ABORTED`. State is append-only. Rejected or
aborted attempts remain available for comparison and cannot be overwritten by a
later successful iteration.

Each experiment freezes:

- stage target and hypothesis
- target metric plus quality guard metrics
- owned data files and non-goals
- planner, scope, compatibility, action-pool, policy, and cohort hashes
- deterministic sample/review cohort
- promotion/rejection thresholds

Tracked decisions belong under
`docs/variation_expansion/experiments/<experiment-id>/`. Large generated reports
belong under `assets/results/variation_expansion/<experiment-id>/`; tracked
state references them by path and SHA-256.

## Planner Capability Roadmap

The current script remains the entry point. Capability is added in small,
test-locked passes:

Current execution state:

```text
L0: BASELINE_READY (completed 2026-09-01)
L1: PROMOTED (completed 2026-09-01; planner capability only)
L2: complete for structural selection; iteration 001 rejected, iteration 002 eligible
L3: shape iteration 004 rejected at authenticated prompt comparison
```

L0 evidence is frozen under `experiments/v150-planner-l0/`; the base L1-L3
technical plan is `planner_refactor_spec.md`, and the promoted L1 delta is
`planner_l1_contract.md`.

L1 evidence is frozen under `experiments/v150-planner-l1/`. Its synthetic
fixture proves planner behavior but is not a promotable variation-data candidate.

L2 analyzer rules are in `candidate_l2_contract.md`. Rejected attempt 001 is
frozen under `experiments/v150-candidate-l2/`; it cannot be reused as a prompt
candidate or overwritten by the next iteration.

Iteration 002 handoff is frozen under
`experiments/v150-candidate-l2-iteration-002/`. It authorizes isolated candidate
snapshot preparation only; it does not authorize active data or scope changes.

L3 snapshot rules are in `candidate_l3_contract.md`. Snapshot iteration 001 is
rejected under `experiments/v150-candidate-l3-iteration-001/` because realized
base variations were `141,984`, below V150. Prompt generation remains blocked.

Runtime-equivalent contribution modeling selected a four-location addition shape
estimated at `150,184`. Hash-bound review authorized and iteration 004 completed
isolated authoring of 80 actions, then materialized and compared that shape on the fixed 64+16
cohort. It met quantity and improved location entropy, but was rejected because
8 locations and 13 actual location-action pools were unseen and repeated-ngram
plus context-size guards regressed. Active data remains unchanged; blind review
and confirmation were not run.

Coverage schedule iteration 005 kept the same 64+16 cohort and established a
non-circular contract/schedule/snapshot/experiment evidence chain. Its 19-row
source schedule was fully reachable, but the complete workflow reached only 12
candidate locations and 9 exact final location-action witnesses because
`ContextSceneVariator` full mode can replace the source scene. The attempt is
terminally rejected and cannot change the parent quality verdict. The next
planner capability must model complete-workflow witness reachability.

Iteration 006 completed that capability. A fixed80-only row/slot matrix and
deterministic assignment reproduced 19/19 final locations, 15/15 subjects, and
19/19 exact raw pool-action witnesses in the formal auto workflow. This closes
the coverage-planning gap but does not change quality authority. Semantic-family
repetition and context p95/max still regress, so the candidate remains rejected
and the next loop is quality remediation with the coverage schedule frozen.

Iteration 007 completed that remediation diagnostically. The frozen coverage
surface retained 19/19 witnesses and zero extra seeds, cleaned prompts were
byte-stable, semantic-family repetition returned to baseline, and context p95
and maximum became non-regressing. Because the surface was selected for
coverage, the fixed quality rejection remains authoritative. A separate
non-selected quality validation is required before review or confirmation.

### L0: Reproducible Baseline

- preserve current 100k behavior and `assets.test_variation_target_planner`
- record the 500k baseline report and input hashes
- classify the six out-of-scope action pools as `runtime_alias_compatible`,
  `legacy_only`, `quality_excluded`, or a reviewed future `staged` candidate

Result: complete. The six pools are not staged candidates: four are runtime
alias-compatible, one is legacy-only, and `messy_kitchen` is quality-excluded.

### L1: Hypothetical Shape Modeling

- accept hypothetical subject and location counts without requiring data edits
- model compatibility density independently from raw scope size
- model action-depth distributions, not only a uniform minimum
- emit mixed scenarios and contribution breakdowns

### L2: Quality-Aware Candidate Analysis

- attach distinct-utility/category metadata to subject and location proposals
- estimate shared-family reuse and duplicate-action pressure
- run repetition, semantic-policy, and compatibility guardrails
- generate baseline/candidate prompts with the workflow-faithful runner on the
  locked prompt-quality cohort
- compare target and guard dimensions using the current prompt-quality policy
- reject scenarios that reach the count primarily through duplication

### L3: Stage Execution Support

- emit a frozen candidate manifest for the selected stage
- compare expected and realized metrics after data edits
- fail closed on scope/CSV/action-pool/source-hash drift
- produce a promotion verdict without mutating source automatically

## Stage Gates

| Stage | Target | Purpose | Promotion requirement |
|---|---:|---|---|
| V150 | 150,000 | Prove mixed-scenario planner and staged-pool policy | Quantity target plus all guard metrics pass |
| V250 | 250,000 | Expand distinct subject/location utility and compatibility density | V150 remains reproducible; prompt-quality target/guard dimensions do not regress |
| V350 | 350,000 | Validate scalable action-family reuse and distribution modeling | Diversity, naturalness, and semantic review pass on fixed and exploration cohorts |
| V500 | 500,000 | Final scale gate | Fresh full verification, blind review, confirmation cohort, and exact evidence-bound promotion verdict |

Targets are sequential gates, not permission to fill the gap by action count.
A stage may be split into multiple iterations; only a promoted stage becomes the
baseline for the next stage.

## Per-Stage Evidence

Required evidence:

1. locked hypothesis and source/data manifest
2. baseline planner report
3. candidate scenario manifest
4. generated compatibility/action contribution report
5. quantitative comparison
6. prompt-quality analysis for the locked control/exploration cohort
7. blind review bound to the comparison and review contract
8. three independent 256-seed confirmation results
9. verification receipt
10. terminal promote/reject verdict

Minimum verification remains:

```bash
python -m unittest assets.test_calc_variations assets.test_variation_target_planner assets.test_variation_scope assets.test_build_compatibility_review assets.test_build_action_pools
python tools/validate_prompt_data.py
python tools/check_variation_scope.py
python tools/build_compatibility_review.py --check
python tools/build_action_pools.py --check
python assets/calc_variations.py --json
python tools/verify_full_flow.py
```

Prompt-level generation, analysis, comparison, review, and confirmation through
the `docs/prompt_quality/` contract are mandatory before a data candidate can be
promoted. The tracked variation verdict must reference the prompt-quality
comparison, review, confirmation, and verification hashes.

## Stop Conditions

- Do not bulk-edit variation data before L1 has produced reviewable mixed scenarios.
- Do not promote a stage when only the base-variation count passes.
- Do not continue an iteration after source, policy, cohort, or candidate hashes drift.
- Do not delete rejected or aborted evidence.
- Stop P13 planning when L0-L3 are specified, tested, and a V150 candidate has a
  reviewable locked manifest. Data expansion begins in a separate promoted wave.
