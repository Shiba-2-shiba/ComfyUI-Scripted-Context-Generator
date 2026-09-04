# Variation Expansion Handoff — 2026-09-02

## Stop point

Work is intentionally paused after closing blind-review attempt 002 and
preparing the next automatic-validation cycle. Nothing in this working tree is
committed or pushed yet.

## Completed result

- Fixed the five attempt-001 conflict seeds in the prompt pipeline:
  - seed `1`: concert-stage quiet-room conflict
  - seed `2`: calm reading versus high-arousal obstacle/garnish
  - seed `9435136036924046218`: mixed bus/train wording
  - seed `1149853648275787818`: karaoke versus work/study wording
  - seed `16086608232758145338`: street-café versus retail action
- Preserved the locked L0 compiled action-pool hash:
  `c50bb7dbea2726d43e84007cb46f629d9423aa7e83702d0dd9a3ac494c850b98`.
- Street café now performs one-to-one runtime replacements, preserving 20
  unique reachable actions. Do not restore the earlier 12-action filter.
- Commuter transport is rendered with mode-neutral public-transit wording.
- q23 automatic validation passed, then blind-review attempt 002 ran with new
  records, selection hash, assignments, lanes, and independent reviewers.
- Attempt 002 aggregate hash validation passed, but the verdict was `reject`:
  8 candidate-only hard-defect observations across 5 seeds. VE-1318 and
  VE-1319 remain blocked.

Attempt-002 evidence is immutable under:

- `docs/variation_expansion/experiments/v150-candidate-shape-iteration-009/`
- `blind-review-attempt-002/review.json`
- `blind-review-attempt-002/rejection-receipt.json`

## Current next-cycle state

An independent review found that the first q23 snapshot preceded restoration
of two protected authoring files and that the initial street-café filter
reduced runtime cardinality. Both issues have been repaired.

The final current source has already passed a new scheduled coverage snapshot:

- snapshot: `assets/results/vfc/q24-current-source-refresh`
- baseline source tree: `3a3c135c6804d3f2a025326bc5cdf5744f3f76a4d0dc51a9c3fbac69b586663b`
- candidate source tree: `f7902e0b69f1e3a200fc324007db1c5cd45661c9e95b0262e06d8fcbf35434c9`
- candidate metrics: 135 subjects, 109 locations, 8,227 rows, 150,184 base variations
- coverage replay: 19/19, fixed 80 seeds, extra 0, active source unchanged

New tracked inputs are ready:

- `docs/variation_expansion/experiments/v150-candidate-shape-iteration-010/current-source-coverage-refresh.json`
- `docs/variation_expansion/experiments/v150-candidate-shape-iteration-010/nonselected-quality-contract.json`
- contract validation: pass
- contract hash: `75519cadc7ee55534822e6f14a99ffd26cbbd7ec2baade41ffebef045510bdb0`

## Exact resume sequence

1. Materialize a fresh default80 snapshot. Do not reuse q23 runs.

```powershell
python tools/materialize_variation_candidate_snapshot.py `
  --candidate-iteration docs/variation_expansion/experiments/v150-candidate-shape-iteration-004/candidate-iteration.json `
  --scenario-file docs/variation_expansion/experiments/v150-candidate-shape-iteration-004/scenario-manifest.json `
  --projection-report docs/variation_expansion/experiments/v150-candidate-shape-iteration-004/projection-report.json `
  --analysis-report docs/variation_expansion/experiments/v150-candidate-shape-iteration-004/analysis-report.json `
  --quality-contract docs/variation_expansion/experiments/v150-candidate-shape-iteration-010/nonselected-quality-contract.json `
  --output-root assets/results/vfc/q25-default-quality
```

2. In q25 `baseline-root`, run fresh baseline generation and analysis with
   run id `v150-i10q25-baseline`. In `candidate-root`, use `generate` and run id
   `v150-i10q25-candidate`. Preserve experiment seed `9472026`, iteration id
   `v150-i4q2`, the fixed control-seed fixture, and exactly 80 samples.

3. Create iteration-010 `quality-experiment.json` bound to the q25 snapshot and
   contract, then run `tools/compare_variation_prompt_pair.py`. Required result:
   exit 0, `failures=[]`, quality/validation `pass`, `review_ready=true`,
   `promotion_ready=false`.

4. Record iteration-010 `quality-comparison.json` and
   `quality-validation-receipt.json`. Update progress/tasks to state that this
   is post-attempt-002 remediation and that attempt 003 is still pending.

5. Run a new independent review of the final diff. Only after approval should
   the changes be committed and pushed.

6. Do not start attempt 003, VE-1318, or VE-1319 in the resumed turn unless
   explicitly continuing beyond this handoff.

## Verification already completed

- focused remediation/planner suite: 87/87 pass
- variation contract/snapshot/pair/review-scope suite: 69/69 pass
- action-pool generation check: pass
- prompt-data validation: pass; active variation row count remains 5,806
- attempt-002 aggregate reproduction: byte-equivalent JSON result, verdict
  `reject`, hash validation `pass`
- attempt-002 rejection-receipt hash bindings: pass
- full assets suite: 688 tests, 3 failures unrelated to this diff:
  prompt-quality ledger attestation, existing office prompt snapshot, and an
  existing semantic-EPIG audit fixture

## Working-tree safety

- Do not stage `.omx/state/` or `.omx/tmux-hook.json`.
- `vocab/data/action_pools.json` is intentionally unchanged and protected.
- `vocab/source/action_pools/commuter_transport.json` and
  `vocab/source/action_pools/street_cafe.json` are also intentionally unchanged;
  compatibility repair lives in runtime normalization.
- Local q20–q23 result directories are superseded/diagnostic. The resume path
  starts from q24 coverage and creates q25 default-quality artifacts.
