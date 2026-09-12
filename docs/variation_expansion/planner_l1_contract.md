# Variation Target Planner L1 Contract

Last updated: 2026-09-01

Status: `PROMOTED`

This document is the reviewed L1 delta over `planner_refactor_spec.md`. The base
spec remains the immutable L0 planning artifact. Where this contract is stricter,
this contract governs the promoted V150 implementation.

## Scope

L1 adds an optional pure projection path to `tools/plan_variation_target.py`:

```bash
python tools/plan_variation_target.py --target 150000 --scenario-file <scenario.json>
```

Without `--scenario-file`, the existing report and default `100000` target are
unchanged. L1 does not mutate variation or prompt data.

## Stage Boundary

L1 accepts only:

```text
stage_id: V150
target: 150000
schema_version: variation-target-scenarios/v1
```

V250 and later stages remain disabled until L3 can bind them to a promoted
predecessor receipt. Unknown stages and V150 target mismatches fail closed.

## Explicit Proposal Identities

Each scenario adds:

```json
{
  "proposed_subject_ids": ["<new-canonical-subject-id>"],
  "proposed_location_ids": ["<new-canonical-location-id>"]
}
```

The ID counts must exactly equal the subject/location increase over the locked
baseline. IDs must be unique and absent from the current counted scope. Proposed
locations are checked against the hash-bound L0 pool policy; alias-compatible,
legacy-only, and quality-excluded pools cannot be counted as distinct growth.
Abstract utility-group labels cannot substitute for proposal identities.

## Drift And Input Validation

Before projection, L1 verifies:

- the V150 baseline manifest SHA-256
- every protected L0 scope, compatibility, action-pool, prompt-quality policy,
  cohort algorithm, final-review contract, and G010 receipt input hash
- the L0 pool-policy artifact hash
- the scenario manifest schema and closed field set
- positive target and legacy minimum-action CLI values

Content drift fails even when counts and shapes remain unchanged.

## Projection Contract

- integer basis points only
- `floor(eligible_pairs * density / 10,000)` row calculation
- largest-remainder row allocation
- ascending action depth as the deterministic tie-break
- canonical order-independent scenario and bucket output
- explicit proposal IDs included in the projection result
- no automatic data write or promotion

## Regression Contract

The promoted L1 suite covers:

1. unchanged 103,212 legacy baseline and report surface
2. valid CLI projection without legacy-field replacement
3. exact mixed projection and contribution sums
4. largest-remainder tie behavior
5. manifest/scenario/bucket order invariance
6. repeated canonical byte equivalence
7. numeric, duplicate, bounds, and unknown-field rejection
8. baseline and protected-input hash drift
9. exact proposal-ID delta and current-scope rejection
10. alias/legacy/quality-excluded location rejection
11. untrusted future stage and target mismatch rejection
12. valid and invalid CLI source non-mutation
13. stable JSON CLI error envelopes

## Evidence

- `experiments/v150-planner-l1/verification.json`
- `experiments/v150-planner-l1/receipt.json`

Only the planner capability is promoted. The synthetic fixture is not a V150
variation-data candidate. L2 must select or reject real canonical proposals
under the G010 prompt-quality baseline.
