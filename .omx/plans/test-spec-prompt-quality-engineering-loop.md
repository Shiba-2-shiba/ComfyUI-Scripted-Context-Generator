# Test Specification: Prompt Quality Engineering Loop

## Runner contract

- Executes supported node classes from a validated workflow profile in topological dependency order, using workflow order only as a stable tie-break.
- Resolves links, widget values, optional inputs and randomized seed controls exactly as the current workflow validator does.
- Same workflow hash, config hash and run seeds produce byte-identical records.
- A fixture run matches the current `analyze_context_workflow_diversity.py` output and direct node-chain output.
- Missing node output, malformed workflow, unsupported node and execution exception produce stable error records and non-zero CLI status.
- Unknown nodes are never silently skipped; cycles, ambiguous output selectors, duplicate same-type nodes and missing upstream slots have explicit fixtures.
- Final context/raw/cleaned outputs are selected by configured node-id/slot, not last node-by-type.
- Only configured outputs' ancestor closure executes; profile-declared external terminals such as `PreviewAny` are recorded as excluded, while unknown nodes inside the closure fail.
- Immutable node-id/input-name overrides support natural mode; base workflow hash plus override hash forms the effective workflow hash.

## Cohort contract

- Default run contains exactly 80 prompts: 64 fixed control + 16 deterministic rotating exploration.
- Promotion cannot run with fewer than 80 records.
- Duplicate seeds, missing seeds and cohort drift are rejected.
- Objective completion additionally requires the versioned 256-seed confirmation cohort.
- Incumbent and candidate use the same per-iteration 64+16 cohort.
- Control, all exploration and confirmation seeds are pairwise disjoint.
- Confirmation compares objective-start baseline to final candidate; holdout failure stops the objective.

## Analyzer tests

Versioned synthetic fixtures must prove detection and non-detection for:

- male pronoun, other person, subject drift, duplicate protagonist
- location/action/object, clothing/TPO/weather and mood/action/garnish conflicts
- fragments, dangling modifiers, duplicate subject, punctuation anomalies
- exact and normalized duplicates, repeated n-grams and semantic family duplication
- entropy, coverage, concentration, fallback and survivor metrics
- deterministic replay, warnings and context size

Every emitted issue must include issue code, severity, confidence, affected seeds, evidence and suspected owner/test surface.

## Comparison tests

- Seed-paired comparison rejects different control cohorts or workflow hashes.
- Hard-gate failure always overrides target-metric improvement.
- Behavior target promotes at >=2 fewer defects or >=10% relative rate improvement.
- Diversity target promotes at >=5% relative entropy/coverage improvement.
- Guard regression >2 percentage points rejects.
- Exact duplicate or fallback regression rejects.
- Context p95 >110% baseline or max >125% baseline rejects.
- Metrics at boundary values have explicit inclusive/exclusive tests.

## Experiment-state tests

- Experiment hypothesis/metric/ownership manifest is immutable from `HYPOTHESIS_LOCKED` onward.
- One iteration declares exactly one primary hypothesis and target metric.
- Candidate artifacts reference baseline source tree hash and candidate patch hash.
- Rejected iterations cannot become the next baseline.
- Promoted iteration becomes baseline only after regression and review evidence are present.
- State transitions are append-only and validate previous state plus source/policy/analyzer/cohort/artifact hashes.
- Candidate patch drift after `CANDIDATE_SNAPSHOT_LOCKED` aborts the iteration.
- Promoted verdict does not mutate git/source.
- Rejected source snapshots cannot be selected as incumbent.
- Dirty source lacking a complete content-addressed snapshot manifest cannot start an objective.

## Artifact determinism and write-scope

- Canonical records/metrics are byte-identical for identical source/workflow/config/seeds.
- Run id, timestamp, host and dirty marker exist only in run-manifest.
- Duration/resource values exist only in telemetry and are excluded from byte-identity.
- CLI writes only beneath the experiment artifact root.
- Protected source-root hashes are identical before and after every loop CLI command.
- CLI does not invoke git mutation, formatters, data builders, agents or source editors.

## Integration tests

- Baseline → analyze → candidate generate → compare → promote-check happy path.
- Candidate with identity regression is rejected despite diversity improvement.
- Candidate with metric improvement but qualitative-review regression is rejected.
- Source action-pool change fails until generated runtime JSON is synchronized.
- Legacy `composition_mode=False` remains valid during natural-mode experiments.
- Control=0/exploration>0/confirmation=0 deterministic defect promotes only through a locked repro fixture and `rare_deterministic` verdict.
- Statistical rare issue requires >=5 baseline events in a pre-registered <=128-record repro cohort and >=50% candidate reduction.

## Qualitative review contract

- Exactly 20 stratified seed-paired prompt pairs per candidate; both independent lanes evaluate all 20.
- Two independent review lanes do not see implementation details or which side is candidate; side order is independently randomized per lane.
- Each pair is scored for protagonist clarity, consistency, naturalness, redundancy, diversity and image-prompt suitability.
- Consistency and naturalness each require >=65% improvement support among non-abstain votes and <=10% regression among valid votes.
- Protagonist clarity and image-prompt suitability each require <=10% regression and zero hard defect.
- Ties/abstentions are excluded, but each required dimension needs >=36 valid votes out of 40.
- Opposite lane-majority directions, insufficient votes, missing reviewer/rubric/prompt/model hashes or invalid votes fail review.
- Review disagreement, side assignment, raw votes and reviewer identities/types are recorded.

## Transaction crash/recovery tests

- Concurrent writer cannot acquire the experiment lock.
- Crash before artifact atomic rename leaves no committed artifact.
- Crash after artifact rename but before state commit produces an orphan recovered as ABORTED/quarantined.
- Duplicate transition id with identical payload is idempotent; different payload is rejected.
- Corrupt transition JSON, sequence gap and hash mismatch stop automatic resume.
- Policy/runner/analyzer/profile drift rejects comparison and requires rebaseline.
- Source manifest inclusion/exclusion rules and their version hash are fixture-tested.

## Full verification

- Targeted unit tests pass before candidate generation.
- Full Python unittest discovery passes before promotion.
- Prompt data, full flow, widget values, compatibility CSV and action-pool synchronization checks pass.
- L6 requires pinned ComfyUI/frontend environment, Vitest round-trip and Playwright import/save/reload; missing execution is failure.
- A test-only verification sink obtains raw prompt, cleaned prompt and final context from real ComfyUI for an 8-seed sentinel cohort.
- External execution parity is required at L0, before first promotion and at L6.

## Stop conditions

- Maximum six iterations per objective.
- Two consecutive sub-threshold improvements stop the objective.
- Repeated hard regression stops and escalates the design hypothesis.
- Public contract or dependency expansion exits the normal loop.
- Final 256-record confirmation failure cancels completion.
