# Variation Candidate L2 Contract

Last updated: 2026-09-01

Status: `Analyzer promoted; iteration 001 rejected; iteration 002 structurally eligible`

L2 is a read-only structural and quality pre-screen between numerical projection
and prompt-generating data work. It is implemented by
`tools/analyze_variation_candidates.py`.

## Inputs

- hash-bound V150 scenario manifest
- reproducible L1 projection report
- explicit subject/location candidate catalog
- current scope, aliases, pool policy, compatibility tags, shared action families,
  semantic policy, and G010 protected inputs

## Structural Gates

- exact scenario/proposal ID binding
- canonical ID grammar and normalized identity collision checks
- current scope, alias, legacy, and quality-excluded location rejection
- known compatibility tags and measurable pair coverage
- explicit distinct-utility claims with visible terms and known comparators
- closed action-family schema and valid slices
- action depth allowed by the bound projection
- semantic-policy-clean prompt-bearing terms
- exact duplicate pressure and shared-family reuse limits

Passing these gates only means the candidate is reviewable. It does not prove
semantic distinctness or prompt quality.

## Prompt-Quality Boundary

L2 accepts only `prompt_quality_receipt: null` and reports `not_evaluated`.
Non-null receipts are rejected. Authenticated prompt-quality pass/fail derivation
requires the L3 state-chain and artifact validator; L2 cannot promote a candidate.

## Attempt 001 Result

`experiments/v150-candidate-l2/` records the first real 15-subject/15-location
catalog.

```text
projection: 8,646 rows / 150,436 base variations
measured candidate coverage: 7,817 rows
coverage margin: -829
candidate actions: 240
unique candidate actions: 120
exact duplicate pressure: 5,000 bp
configured duplicate limit: 1,000 bp
prompt quality: not_evaluated
verdict: REJECTED
```

Rejection reasons:

- `insufficient_candidate_coverage`
- `duplicate_pressure_exceeded`

The next iteration must be a new directory. It must not overwrite attempt 001.

## Attempt 002 Result

`experiments/v150-candidate-l2-iteration-002/` preserves the same subject/location
claims while changing only the bound scenario and action authoring plan.

```text
projection: 7,796 rows / 155,920 base variations
measured candidate coverage: 7,817 rows
coverage margin: +21
candidate actions: 300
exact candidate duplicates: 0
direct-to-existing duplicate pressure: 50 bp
policy findings: 0
prompt quality: not_evaluated
structural status: pass
eligible for prompt evaluation: true
promotion ready: false
```

Five semantically mismatched shared-family slices discovered by independent
review were replaced with location-specific direct actions before handoff.

Attempt 002 may enter L3 candidate snapshot preparation, but this receipt does
not authorize active data mutation or variation-scope promotion.
