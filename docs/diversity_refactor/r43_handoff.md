# R43-10 — Conditional formal-evaluation handoff

Historical handoff checkpoint: subsequent [AS01 development](./coverage_as01_plan.md)
changes runtime source and supplies fresh intake/review receipts at11/512. The
10/512 source-bound receipts below remain historical evidence, not authorization
for the newer source. Formal evaluation/adoption remain BLOCKED.

State: PASS (conditional handoff preparation, 2026-09-12 JST).
Formal-evaluation handoff: BLOCKED. Adoption: BLOCKED.
Candidate source: `1678a635b03d8e6e18e6a797b395511a51cc04c3f245f96c7c5a38e9ca17cf23`.

## Bounded handoff work

1. Recheck the complete current R43-09 source/receipt inventory and existing user
   changes without rerunning unchanged tests or heavy formal evaluation.
2. Verify original sealed pre-N2 V150 source/archive and historical gate/reference/
   paired2048/fixed80 files against their original receipts. Bind report metadata
   to actual source identity and preserve the distinction from stable main and
   the nine-case development baseline.
3. Compare workflow, runner/config, normalization/signature/contract identities.
   Record allowed active-family declaration changes and all unresolved comparison
   evidence. Never reuse the V150 reference cache for the changed candidate.
4. Retain the complete A1.6 lock and every applicable requirement in the handoff.
   Historical baseline integrity is not current candidate formal PASS.
5. Record NOT_RUN candidate formal gates and BLOCKED adoption. The64/5 development
   guide is unmet, so do not create a formal evaluation freeze, run heavy gates,
   merge main, or activate N2.8/D3. Identify the next bounded coverage work.

This task changes documentation and external integrity receipts only.

## Decision

R43-00..10 development work and this conditional handoff are complete.
Architecture/development remain PASS. Ordinary v2 is10/512 across3 executed
families, while all6 families have unchanged-real-graph forced proof.
The64/512 and5 ordinary-family development guide is not met. Under plan13.3,
heavy formal evaluation is not automatically started and no formal evaluation
freeze is created. The saved development source remains a reproducible checkpoint.

All current-candidate reference8192/gate2048/paired2048/fixed80/blind-review/fresh
confirmation/release8192/full-suite/frontend/browser work is NOT_RUN. This is
BLOCKED pending evidence and readiness, not measured formal REJECTED. Existing
historical rejected candidates keep their original verdicts.

## Baselines are different sources

| Source | Identity scope / SHA-256 | Role |
|---|---|---|
| Sealed original pre-N2 V150 | audit source448e4240b6f8321e1ba9332f9f624b7bf9419d255f715f438fd87b13dd556214 | Original A1.5/reference/paired/quality baseline |
| Same original V150 | prompt-quality source tree27fea03cfcc4d54c1fbed033f5a9ece9a812f2ad090b663f06745d8794412c53 | Source manifest embedded in original formal/quality receipts |
| Stable main10d7d8d | prompt-quality source tree01f94274e237597b032f708dd246066b66ee8660bb58d1dbdf7ac159c12b45ba | Stable preservation source, not the sealed original formal baseline |
| Nine-case development baseline | source tree0c8c421de459f62afa8731d60994d23a4409165b726095e5b24c13d363ebd281 | R43 development expansion/old-success/fallback comparison |
| Current R43 candidate | source tree1678a635b03d8e6e18e6a797b395511a51cc04c3f245f96c7c5a38e9ca17cf23 | Verified R43-09 development checkpoint |
| Same current R43 candidate | projected audit source08c19e3499db1af7c14dc3c92a80f66f17d0ba39a9e87794482d56497653a874 | Metadata-only audit identity; not a measured formal report |

Hash scopes are not interchangeable. The original sealed archive covers1120 files
and has content hash34f92cc23d738f564568b04a48e1019d6ee54529e1487bdfc22d8bf9a6b456af.
Its ZIP hash is45c3348563e287f5bbc2cdabcd6dbf82184c1f30cf4f7ca5849f49ada5996eec.

R43-09's adoption-preflight invocation supplied stable main through
--v150-baseline-root. Its original_v150_source_tree_hash field therefore records
the supplied stable source01f942..., not the sealed pre-N2 formal source27fea....
That receipt is preserved unchanged. This handoff independently verifies and
identifies the actual original formal baseline; neither source substitutes for
the nine-case development comparison.

## Historical evidence integrity and comparability

Fresh read-only checks pass:

- All1120 original source files match the sealed manifest; manifest/ZIP hashes
  match the archive receipt and the archive CRC check succeeds.
- Executing only the original source's capture_source metadata function in an
  isolated process reproduces its recorded448e4240... audit identity exactly.
  No original or candidate formal generation was executed.
- A1.5 gate and repeat match6c6bef1911ba9b9921f62b0f64adf4172ced2f9e32b0e4922cdd226e6267f733.
  Reference8192 matches6de5aa646d40882ff52291d2b1b9ad86ef94785353001da9943928b21d4cd207.
  Their source/config identities and embedded reference agree.
- Historical paired2048 observations and eight fixed80/quality files match their
  reuse/run manifests. The2048 observation seeds and80 unique quality records are
  validated; these are historical source-bound data, not fresh candidate scores.
- Public source files core/schema.py, nodes_context.py, nodes_prompt_cleaner.py
  and __init__.py are byte-identical between original V150 and current candidate.
  All120 protected V150 files match. The only vocab/data JSON addition is the
  previously implemented natural_language_realizer_v2.json syntax metadata.
- Workflow, effective workflow and runner/config identity match the historical
  comparison. Metrics and signature-extraction source files are byte-identical.
  Audit AST differs only in the allowed ACTIVE_V1_FAMILIES declaration.

The candidate's projected audit configuration changes only active_syntax_families:
the2 legacy aliases become the6 required structural families. Runner config,
signature versions, normalization version and contract hash remain unchanged.
Projected candidate config hash:
05f8d34938ef99842791f630ec151bf30bf110525596717bf7ad0447f8bcc993.
This is an identity projection based on current source and verified runner
records, not a gate result or formal evaluation freeze.

Passing the V150 reference to the candidate identity is correctly rejected with
reference_identity_mismatch. This checks cache isolation; it does not mark the
candidate adoption REJECTED. The candidate needs its own reference when evaluation
readiness is established.

Comparability status: METADATA_COMPATIBLE_FORMAL_NOT_RUN. A new original-V150 versus
candidate paired2048/quality comparison remains NOT_RUN. The retained observations
contain projections and prompt/context hashes; full prose comparison may require
regeneration from the preserved source. Historical fixed80 records retain text and
context but do not supply new blind-review votes or current candidate quality scores.
An original source-bound release-profile8192 baseline has not been established for
this handoff; reference-only8192 is not a substitute.

## Complete A1.6 obligation inventory

Authority: [progress section7](./progress.md#7-locked-target--guard-metrics),
lock A1.6-2026-09-06/v1, SHA-256
6742b1b735de2e3ef9b53b732e51d54d260434a500ab84f32249334c24cfb7bd.
The exact complete lock is also copied in the integrity receipts as
complete-a16-lock.md. Plan13.4 is only an excerpt. None of these candidate formal
requirements has been passed by extrapolating512 development data.

Numbers below are @128 / @512 / @2048 unless otherwise specified:

| Requirement | Locked criterion |
|---|---|
| Normalized syntax entropy | >=0.743271 /0.814359 /0.855077 |
| Maximum same-syntax run | <=11 /11 /16 |
| Required families at2048 | All6 enabled and ordinarily observed; safe fixtures |
| Raw entropy / dominant share at2048 | >0.814359 bits; <=0.748047 share; report K and counts |
| Valid core/frame counts | 128 /512 /2048 |
| Minimum unique core | 128 /508 /1963 |
| Minimum unique frame | 128 /511 /2042 |
| Maximum semantic-core duplicates | 0 /4 /85 |
| Maximum semantic-frame duplicates | 0 /1 /6 |
| Exact and normalized prompt duplicates | 0 /0 /0 each |
| Syntax metadata missing | 0 /0 /0 |
| Primary-object missing ceiling | 116 /452 /1769 |
| Other optional missing ceilings at2048 | posture1231; hand_action1329; gaze_target1977; progress66; social_relation71; stimulus/obstacle1551 |
| Mandatory semantic-axis missingness | subject/location/action/mood/clothing/garnish0 |
| Covered-key minima | subject28/28/28; location64/100/107; object7/14/16; mood1/1/1; clothing3/3/3; garnish4/4/4 |

Compare integer counts before rounded ratios and preserve improvements in an
accepted intermediate baseline too. If reference universes differ, retain actual
per-prefix observed sets and hash-bound intersections with the original universe;
report outside-universe values separately. Do not change denominator/missingness/
normalization/family mapping to obtain a favorable result.

Additional mandatory groups:

1. Preserve original workflow/profile/overrides, seed0..2047 and prefixes,
   reference0..8191, initial history/context. Each source owns its reference.
2. Per-seed semantic core/frame and upstream selected facts must match. No invented
   action/object/person/location, lost owner/reference/polarity, or unsupported
   surface authorization. Force/recombination cannot count as ordinary observation.
3. Same source/config/workflow/seed/history gives identical canonical reports and
   prompt replay, mismatch0. Public I/O/context_json/version and composition=false
   rollback remain unchanged.
4. V150 stays135 subjects,109 locations,8227 rows,150184 variations,0 missing pools;
   preserve semantic-only, compatibility, solo safety, EPIG and history precedence.
5. Fixed quality cohort is64 control+16 exploration from the original frozen source.
   Strict automatic non-regression: no increase in punctuation anomalies, repeated
   n-grams, semantic-family repetition, identity defects, conflicts, fallback rate,
   replay mismatch, context bytes p95/max or policy issues; no loss of exact uniqueness.
   Runtime/record/conflict/identity/determinism/banned-leakage hard defects stay0.
   Generic0.02 or1.10/1.25 tolerances do not relax V150 constraints. Quantity-expansion
   location entropy is not a substitute Realizer criterion.
   Applicable existing rendering-comparison effect sizes, guards and review
   requirements remain binding.
6. Fresh comparison-bound blind review:2 independent lanes x20 predeclared pairs,
   >=36 non-abstain votes per dimension. Naturalness/image-suitability targets also
   need>=20 directional votes, support>=0.65 and lane agreement. Every dimension's
   worse/non-abstain<=0.10; consistency/protagonist-clarity/redundancy guards need
   no directional improvement. Candidate-only hard defects0; no recycled votes.
7. Fresh3x256 confirmations for consistency/naturalness/diversity; do not reuse
   V150's consumed holdouts. Apply full test/data/action-pool/compatibility/full-flow/
   widget/frontend/browser/comparison/review/confirmation/release requirements.
   Frontend/browser must load the actual candidate, not another installed plugin.
8. Final release preserves matching2048-prefix thresholds and uses a separately
   source-bound V150 release-profile baseline for8192 guards. No invented8192 threshold.

Scheduler obligations remain recorded but DEFERRED, not current N2 acceptance:
freeze the immediate stage baseline; syntax run<=15 and stage-minus1 unless already1;
improve unsaturated targeted coverage and preserve other prefixes. The original
169-action-key universe requires46/92/154 covered keys and runs<=2/4/5 plus stage
non-regression. Action coverage at2048 must additionally exceed the immediate
stage by at least1 key unless already saturated. Syntax normalized/raw entropy
and dominant share must not regress from that stage and must meet N2 targets.
Saturation is not improvement; preserve exact set-intersection
receipts and eligibility/semantic weighting. No D3 activation is authorized.

The five policy/comparator hashes recorded in the complete lock were freshly
verified. The current scoped development review is not the required formal blind review.

## Conditional execution handoff

Before heavy evaluation, improve coverage through a bounded source/grammar task
and rerun portable intake. Recheck current review/source/cohort receipts. Only a
sufficiently ready candidate receives an explicit formal source/config freeze.
Then use the existing source-bound audit/quality paths for its own reference/gate,
paired semantic observations, fixed80 automatic comparison, fresh independent
reviews/confirmations and final release/frontend/browser evidence.

Missing or incompatible evidence is BLOCKED. Unrun gates are NOT_RUN. Only a
measured formal threshold failure is REJECTED. This packet grants no merge/push,
promotion, N2.8 or scheduler permission.

The remaining502 fallback inputs have no single-domain-only case. Five inputs
have2 blocked domains: four Action+Scene and one Action+Clothing. Larger groups
commonly combine Action/Clothing/Scene with Template or Subject. The next useful
work is an Action+Scene constructor/grammar plan using those intersections and
reusable source categories. Diagnostic example IDs are not runtime allowlists or
promised rescue counts. See next-coverage-evidence.json in the receipt inventory.

## Evidence and completion

[r43_handoff_summary.json](./r43_handoff_summary.json) records source identities,
availability, comparison boundaries and artifact hashes. Evidence relative to the
original main checkout:
`assets/results/diversity_refactor/r43/handoff-20260912-01/`.

Retain the sealed v150-before-n2 archive/manifest/source, original effective-diversity
reports/reference, n27-candidate-02 baseline observations/quality records, the
R43 development baseline and R43-09 intake/review receipts when transferring work.
Restore exact hashes before reuse on another machine. An isolated candidate ZIP
alone is not the complete formal baseline.

All integrity and identity checks passed. Candidate source/guard and prior user
files remained unchanged. R43-09's492 focused/87 regression test evidence remains
current; those tests were not rerun for this documentation-only task.
Conditional handoff preparation is complete; evaluation handoff and adoption
remain BLOCKED. No new formal measurement, candidate evaluation freeze, main
change, N2.8 or D3 activation occurred.
