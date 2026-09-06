# Semantic Diversity / Natural Language Refactor Progress

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
仕様: [`docs/diversity_refactor/spec.md`](./spec.md)
タスク: [`docs/diversity_refactor/tasks.md`](./tasks.md)
作成日: 2026-09-06

---

## 1. Wave Status

```text
Wave: Semantic Diversity / Natural Language Refactor
State: IN_PROGRESS
Current task: N2.7-R3 complete (candidate REJECTED); next N2.7-R4
Next task: candidate-02 evaluation; N2.8 stays blocked until eligible
Baseline: V150
Active quantity target: NONE
V250/V350/V500: DEFERRED
```

### Decision

V150 を semantic-base の一旦の完成版として扱う。

この wave では:
- base variation 数を success metric としない
- effective diversity を測る
- Natural Language Realizer v2 を作る
- Deterministic Diversity Scheduler を作る

---

## 2. Current Known V150 Reference

2026-09-06 repository documentation reference:

```text
unique subjects: 135
unique locations: 109
base variations: 150,184
compatibility rows: 8,227
actions/location: min 12 / median 16 / mean 16.33 / max 20
mood tags: 172
micro actions: 280
background context tags: 1,028
semantic units: 1,480
```

**F0.2: 2026-09-06 の main から再計測し、上記すべての計数一致を確認済み。**

Baseline HEAD:

```text
1b159bf66fa5202d27908ed63fe7d5fe4cb590f3
```

Baseline date:

```text
2026-09-05T23:39:41.425908+00:00
```

---

## 3. Protected V150 Surfaces

Feature expansion 目的の変更禁止:

```text
vocab/data/variation_scope.json
assets/compatibility_review.csv
vocab/source/action_pools/*.json
vocab/source/action_pools/_shared_families.json
vocab/data/action_pools.json
```

Approved exception tasks:

```text
none
```

---

## 4. Task Board

Status values:

```text
TODO
IN_PROGRESS
BLOCKED
ELIGIBLE
PROMOTED
REJECTED
SKIPPED
```

| ID | Task | Status | Owner files / note |
|---|---|---|---|
| F0.1 | Add canonical wave docs | PROMOTED | `docs/diversity_refactor/*` |
| F0.2 | Capture exact V150 baseline | PROMOTED | read-only + progress; assets/results/diversity_refactor/f0-baseline/ |
| F0.3 | Mark V250/V350/V500 deferred | PROMOTED | README, CURRENT_STATUS, REPO_STRUCTURE, variation_expansion entrypoints, intake README, progress |
| F0.4 | Add V150 freeze regression guard | PROMOTED | assets/test_v150_freeze_contract.py; progress |
| A1.1 | Lock metric schema | PROMOTED | spec.md sections 6.2–6.6; tasks/progress |
| A1.2 | Implement pure diversity metrics | PROMOTED | tools/effective_diversity_metrics.py; assets/test_effective_diversity_metrics.py; tasks/progress |
| A1.3 | Implement semantic signature builder | PROMOTED | tools/effective_diversity_signatures.py; assets/test_effective_diversity_signatures.py; tasks/progress |
| A1.4 | Implement Effective Diversity Audit CLI | PROMOTED | tools/audit_effective_diversity.py; assets/test_effective_diversity_audit.py; tasks/progress |
| A1.5 | Capture V150 diversity baseline | PROMOTED | assets/results/effective_diversity/v150_baseline_gate.json; reference; tasks/progress |
| A1.6 | Lock target/guard thresholds | PROMOTED | progress section 7; tasks; status pointers |
| N2.1 | Add Realizer v2 contract tests | PROMOTED | assets/test_prompt_realizer_v2.py; baseline snapshot; tasks/progress |
| N2.2 | Extend syntax-family metadata | PROMOTED | vocab/data/natural_language_realizer_v2.json; schema validator; assets tests; asset_validator |
| N2.3 | Implement eligibility engine | PROMOTED | pipeline/syntax_family_selector.py; assets/test_syntax_family_selector.py; tasks/progress |
| N2.4 | Implement first 3 syntax families | PROMOTED | pipeline/prompt_realizer.py; assets/test_prompt_realizer_v2.py; tasks/progress |
| N2.5 | Implement remaining required families | PROMOTED | pipeline/prompt_realizer.py; assets/test_prompt_realizer_v2.py; tasks/progress |
| N2.6 | Add v2 debug payload | PROMOTED | prompt_renderer.py; pipeline/prompt_realizer.py; realizer tests; tasks/progress |
| N2.7 | Run Realizer v2 candidate gate | REJECTED | isolated n27-candidate-01; fixed gates/cohort; tasks/progress |
| N2.7-R1 | Repair real-workflow clause eligibility and re-evaluate | REJECTED | candidate-02 repair/evaluation complete; 3/2048 v2; automatic preservation PASS |
| N2.7-R2 | Extend structural coverage beyond bounded direct templates | REJECTED | candidate03 repair/evaluation complete; observed4; actual v2 3/2048 |
| N2.7-R3 | Broaden verified clause coverage beyond three measured seeds | REJECTED | candidate04 evaluation complete; actual v2 3→5/2048; preservation PASS |
| N2.7-R4 | Expand productive action and subordinate-clause grammar | NOT_STARTED | coverage diagnosis; identity/ownership/overlap proof; fixed gates |
| N2.8 | Activate v2 for composition mode | BLOCKED | candidate-01 rejected; only after a later eligible gate |
| D3.1 | Implement scheduler primitive | TODO | new module + tests |
| D3.2 | Add generic spread-group selector | TODO | scheduler |
| D3.3 | Integrate syntax scheduler | TODO | realizer/scheduler |
| D3.4 | Audit action-family bias | TODO | read-only evaluation |
| D3.5 | Integrate action scheduler | TODO | action generator |
| D3.6 | Optional extra scheduler axes | TODO | only with evidence |
| R4.1 | Combined final gate | TODO | verification |
| R4.2 | Final before/after table | TODO | progress |
| R4.3 | Update canonical docs | TODO | docs |
| R4.4 | Close wave | TODO | progress |

---

## 5. Baseline Command Receipt

### F0.2

Status:

```text
PASS
```

Commands:

```bash
git status --short --branch
git rev-parse HEAD
python assets/calc_variations.py --json
python tools/validate_prompt_data.py
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --check
python tools/verify_full_flow.py
```

Results:

- All 8 prescribed commands: exit 0 (Git status/head, sizing, 4 validators, full flow).
- Validators: ERROR=[] / WARNING=[]; full flow: OK.
- Existing focused regressions: 40 tests OK (variation calculation/scope/builds; public nodes/workflows/snapshots/context/determinism).
- Missing action pools: 0; source/runtime pool locations: 115 / 115.
- Semantic garnish universe: 13,320; theoretical upper bound: 2,000,450,880 (not a diversity claim).
- Receipt: `assets/results/diversity_refactor/f0-baseline/receipt.json` (ignored generated evidence).
- Receipt SHA256: `35fffa0e2e880177c9728003fc7cad202aa9b1d80d82b595afbccd6c44abb439`.
- Protected-file manifest SHA256: `35e289a07a28062334556508f7c917a82a48409cb940d7836736385cbf0c2def`; 120 files.
- Hash scope: protected variation files only, not a whole-candidate source hash or reusable adoption receipt.


---

## 6. Effective Diversity Baseline

### Metric schema

A1.1: LOCKED — [normative contract](./spec.md#62-locked-signature-model--a11-2026-09-06) (sections 6.2–6.6).

```text
schema_version: effective-diversity-audit/v1
semantic signature:
  - semantic_signature_v1/core
  - semantic_signature_v1/frame
```

Status:

```text
PURE METRIC HELPERS IMPLEMENTED (A1.2)
SEMANTIC SIGNATURE EXTRACTION IMPLEMENTED (A1.3)
AUDIT CLI IMPLEMENTED (A1.4)
FORMAL GATE BASELINE CAPTURED / VERIFIED (A1.5)
RELEASE @8192 NOT MEASURED
PHASE A COMPLETE: AUDIT / BASELINE / ACCEPTANCE LOCK
```

### Baseline metrics

Formal gate: measured seeds **0–2047** (2,048 records), reference probe **0–8191** (8,192 records).
Ratios below use final six-decimal rounding; counts show the actual numerator/denominator.
@8192 is **not measured** as a release profile; generating reference records alone does not claim release metrics.

| Metric | @128 | @512 | @2048 | @8192 |
|---|---:|---:|---:|---:|
| semantic_core_unique | 1.000000 (128/128) | 0.992188 (508/512) | 0.958496 (1963/2048) | not measured |
| semantic_frame_unique | 1.000000 (128/128) | 0.998047 (511/512) | 0.997070 (2042/2048) | not measured |
| subject_coverage | 1.000000 (28/28) | 1.000000 (28/28) | 1.000000 (28/28) | not measured |
| location_coverage | 0.598131 (64/107) | 0.934579 (100/107) | 1.000000 (107/107) | not measured |
| action_family_coverage | 0.272189 (46/169) | 0.544379 (92/169) | 0.863905 (146/169) | not measured |
| primary_object_family_coverage | 0.411765 (7/17) | 0.823529 (14/17) | 0.941176 (16/17) | not measured |
| mood_coverage | 1.000000 (1/1) | 1.000000 (1/1) | 1.000000 (1/1) | not measured |
| clothing_family_coverage | 1.000000 (3/3) | 1.000000 (3/3) | 1.000000 (3/3) | not measured |
| garnish_family_coverage | 1.000000 (4/4) | 1.000000 (4/4) | 1.000000 (4/4) | not measured |
| syntax_family_coverage | 1.000000 (2/2) | 1.000000 (2/2) | 1.000000 (2/2) | not measured |

Coverage denominator is the source/config-bound finite reference universe, not V150 dictionary size.
The current workflow/probe observes 28 canonical subjects, 107 locations, 169 action keys, 17 object families,
1 mood key, 3 clothing types, 4 garnish families and 2 syntax families.
100% subject/mood/etc. coverage does not mean all 135 V150 subjects or all 9 mood dictionary keys were exercised.
No out-of-reference values were observed in the measured prefixes (they are subsets of the locked probe).

### Repetition and syntax baseline

| Metric | @128 | @512 | @2048 |
|---|---:|---:|---:|
| exact_prompt_duplicate_rate | 0.000000 | 0.000000 | 0.000000 |
| normalized_prompt_duplicate_rate | 0.000000 | 0.000000 | 0.000000 |
| semantic_core_duplicate_rate | 0.000000 | 0.007812 | 0.041504 |
| semantic_frame_duplicate_rate | 0.000000 | 0.001953 | 0.002930 |
| max_consecutive_same_action_family | 2 | 4 | 5 |
| max_consecutive_same_syntax_family | 11 | 11 | 16 |
| syntax_raw_entropy | 0.743271 | 0.814359 | 0.814359 |
| syntax_normalized_entropy | 0.743271 | 0.814359 | 0.814359 |
| syntax_dominant_family_share | 0.789062 | 0.748047 | 0.748047 |
| single-sentence-scene-tail count | 101 | 383 | 1532 |
| two-sentence-scene-tail count | 27 | 129 | 516 |

K=2 declared active syntax families. No missing syntax metadata; builder replay checked 2,048 measured records,
with zero prompt mismatch. Core and frame validity counts are 2,048/2,048, but validity does not imply all
optional semantic fields are known.

### Missingness / interpretation limits (@2048)

| Signature field | Missing count | Missing rate |
|---|---:|---:|
| gaze_target_family | 1977/2048 | 0.965332 |
| hand_action_family | 1329/2048 | 0.648926 |
| posture | 1231/2048 | 0.601074 |
| primary_object_or_object_family | 1769/2048 | 0.863770 |
| progress | 66/2048 | 0.032227 |
| social_relation | 71/2048 | 0.034668 |
| stimulus_or_obstacle | 1551/2048 | 0.757324 |

The 1,769 unknown primary objects are neither new unique object categories nor proven object-free scenes.
High frame uniqueness is for the locked coarse projection, with the missingness above, not a human
semantic-equivalence judgment. No naturalness/consistency/image-suitability promotion claim follows from this audit.
Targets were not selected during A1.5; the subsequently locked A1.6 criteria are in section 7.

### Baseline artifacts

```text
path: assets/results/effective_diversity/v150_baseline_gate.json
sha256: 6c6bef1911ba9b9921f62b0f64adf4172ced2f9e32b0e4922cdd226e6267f733
source_hash: 448e4240b6f8321e1ba9332f9f624b7bf9419d255f715f438fd87b13dd556214
workflow_hash: 91c4baa1455799d9c50519c605241058897d6cc66ae83a4eeef1cef0fab4ce18
effective_workflow_hash: 79049275427be45dd325e6503f50d7b6ca500d17929e28b9dad63f15f823c62a
config_hash: bc395ff85f40f9f344c65275c806481e7e1503332b2f5b313ab133d2aeec16d1
records_sha256: 2b2da8e403da7b97c15f60bc79a0aa428c866fc10472e8123066f62e81f2073a
contract_sha256: a0dec4bb3f4bbfd5759e596c3baa3bcced827a0298e603fa52f481f1824123ab
reference_path: assets/results/effective_diversity/v150_reference_8192.json
reference_file_sha256: 6de5aa646d40882ff52291d2b1b9ad86ef94785353001da9943928b21d4cd207
reference_hash: 805920e90e669644ad8fec58492c5d68a5148422b096399f4c57f46bb675eda1
reference_records_sha256: 116206100694e185742ca3b58dc2210b6d5aba15abd1d4eca47c0c906a299537
```

Generated artifacts remain under ignored `assets/results/`; this document is the durable summary and hash receipt.

---

## 7. Locked Target / Guard Metrics

Lock ID: **A1.6-2026-09-06/v1**. Status: **LOCKED before N2 implementation/comparison**.
These are acceptance criteria, not measured improvements or permission to activate a candidate.
Changing this lock after seeing candidate outcomes requires a separately logged prospective decision;
do not retrospectively relax thresholds or reuse a rejected result under new rules.

### Evidence and comparison boundary

- Baseline: A1.5 gate, seeds 0–2047, prefixes 128/512/2048, reference seeds 0–8191.
  Report SHA256: `6c6bef1911ba9b9921f62b0f64adf4172ced2f9e32b0e4922cdd226e6267f733`.
- Extraction/normalization contract SHA256:
  `a0dec4bb3f4bbfd5759e596c3baa3bcced827a0298e603fa52f481f1824123ab`.
  The spec itself is unchanged, preserving A1.5 report identity.
- Preserve workflow, runner profile/overrides, seed range and initial history/context. No cohort substitutions.
  Each candidate report/reference must bind its own actual source/config; never pass the V150 reference cache
  into a changed candidate to make its source/config check pass.
- Source hashes are expected to differ after implementation. For Realizer v2, audit_config.active_syntax_families
  may also change to the implemented/enabled families. Other audit_config fields (runner_config_hash,
  signature_versions, normalization_version and contract_sha256) must match. Log the specific allowed config delta.
  A config hash difference alone is not a regression, and a config hash equality is not evidence of matching semantics.
- Comparison metric definitions and extraction rules stay fixed. Do not change family mappings, missing-value
  treatment or normalizer alongside the candidate to improve its score.
- N2 preparation must preserve an immutable baseline source snapshot, including the currently uncommitted audit
  implementation, before runtime edits. For per-seed checks, regenerate/retain baseline and candidate observations
  from their bound snapshots. A1.5's compact aggregate report alone does not prove per-seed slot equality.

### Targets — Realizer v2 (N2.7 / N2.8)

| Target at gate @2048 | A1.5 baseline | Locked acceptance | Rationale |
|---|---:|---|---|
| Active and observed syntax families | 2 | At least the 6 required spec families are enabled and observed; all have safe eligibility/semantic fixtures | Explicit spec 7.3 / 10.2 requirement; planned or unused keys do not count |
| Normalized syntax entropy | 0.814359 (K=2) | **>= 0.855077** | ceil-to-6-decimals(0.814359 × 1.05); 5% is the existing prompt-quality diversity effect-size precedent, not an invented aggressive target |
| Raw syntax entropy | 0.814359 bits | **> 0.814359**, with K and counts reported | Prevent a normalized score claim from hiding a changed denominator |
| Same-syntax maximum run | 16 | **<= 16** during Realizer-only evaluation | Non-regression here; strict reduction is the scheduler target below |

The 5% precedent is `vocab/data/prompt_quality_policy.json` →
`comparison.effect_sizes.diversity_min_relative_improvement=0.05`.
Applying it to the new audit is an explicit engineering choice, not an assertion that the existing comparator
already calculates this metric or that 5% proves statistical significance.
Syntax dominant-family share must also remain <= **0.748047**; report all family counts.
At @128/@512, normalized entropy must remain >= **0.743271 / 0.814359** and maximum syntax run <= **11 / 11**.
All common guards below must pass. No favorable syntax score excuses lost semantic slots or unnatural English.

### Targets — Scheduler (D3.3 / D3.5 / combined candidate)

- Before each integration, freeze the immediate pre-integration gate report and observations.
  Stage-relative comparisons use that exact report, in addition to the V150 floors/ceilings below.
  Comparator rules are locked now; do not choose a favorable stage baseline after candidate generation.
- **Syntax axis:** at @2048, maximum same-syntax run must be <= **15** (minimum integer improvement from V150's16)
  and, when the immediate pre-integration run is >=2, at most **pre-run minus1**. If pre-run is already1,
  preserve1 and do not claim a further run reduction. Normalized entropy, raw entropy and dominant share must
  not regress from the immediate pre-integration report (same active family set) and must satisfy the N2 targets.
- If syntax coverage is unsaturated at any of the locked prefixes 128/512/2048, improve it at at least one
  of those prefixes with an unchanged comparison universe and preserve the other prefixes. If all are1.0,
  coverage is a saturation guard, not an achievable increase target. Do not claim 1.0→1.0 as improvement.
- **Action axis:** use the fixed V150 action-key universe R from A1.5 (169 keys) for comparison.
  At @2048 require **at least154 covered V150 action keys** (154/169 = **0.911243**), versus146/169 =0.863905.
  This is ceil(146×1.05); whole-key rounding gives an8-key minimum increase.
  Also exceed the immediate pre-action-scheduler covered-key count by at least1 unless it is already169;
  an already saturated stage cannot earn an action-coverage improvement verdict.
  At @128/@512 preserve at least **46 / 92** covered V150 keys, and do not regress the immediate stage's counts.
  Maximum same-action run at @128/@512/@2048 must stay <= **2 / 4 / 5**, and no worse than the stage baseline.
- Candidate report coverage uses its own source-bound probe. When its axis values differ from V150 R,
  derive the comparison numerator as `len(candidate_observed_values_at_N ∩ R)` in a **separate hash-bound
  comparison receipt**. Retain observed value sets per prefix from the actual candidate records; bind their hash,
  candidate report/source/config hashes and the A1.5 reference hash. Report new/outside-R values separately.
  Aggregate counts alone cannot reconstruct this intersection. Missing observation evidence means BLOCKED,
  not permission to divide candidate-local counts by169 or forge a cross-source reference cache.
- The action key in this audit is the locked verb/purpose projection. D3.4 still selects the scheduler's internal
  diversity key from measured bias; this lock does not choose score bands, flatten weights or bypass EPIG/safety.
- Spec 10.3 still requires coverage improvement on a targeted axis for **scheduler promotion**. Syntax-run
  improvement alone is not a standalone promotion when syntax coverage is saturated. The combined candidate
  must then demonstrate the action coverage improvement above. If no axis can safely improve, reject/defer
  that scheduler integration; do not weaken the definition of improvement or add speculative axes.

### Common numerical guards — no regression allowance

Compare integer counts before rounded ratios. Missing or incompatible evidence is BLOCKED; a measured threshold
failure is REJECTED. Equal scores satisfy guards, never improvement targets.

| Guard | @128 | @512 | @2048 |
|---|---:|---:|---:|
| valid core / frame count | 128 | 512 | 2048 |
| minimum core unique count | 128 | 508 | 1963 |
| minimum frame unique count | 128 | 511 | 2042 |
| maximum semantic core duplicate count | 0 | 4 | 85 |
| maximum semantic frame duplicate count | 0 | 1 | 6 |
| maximum exact prompt duplicates | 0 | 0 | 0 |
| maximum normalized prompt duplicates | 0 | 0 | 0 |
| maximum syntax metadata missing count | 0 | 0 | 0 |
| maximum primary-object missing count | 116 | 452 | 1769 |

At @2048, other optional-frame missing counts must not exceed the A1.5 measured ceilings:
posture **1231**, hand_action_family **1329**, gaze_target_family **1977**, progress **66**,
social_relation **71**, stimulus_or_obstacle **1551**. Subject/location/action/mood/clothing/garnish missing counts stay0.
These ceilings prevent hiding information loss in a higher uniqueness rate; they do not endorse existing
86.377% object missingness as complete semantic recognition.

For unchanged semantic axes, retain V150 covered-key counts at all prefixes using the same comparison receipt
rule if reference values differ: subject **28/28/28**, location **64/100/107**, object family **7/14/16**,
mood **1/1/1**, clothing **3/3/3**, garnish **4/4/4**. Scope is this workflow's observed universe, not the full dictionary.
Stage-relative guards must also preserve the immediately accepted baseline; V150 floors cannot excuse regressions
against an improved intermediate version.

- **N2 per-seed semantic preservation:** core/frame projections and upstream selected semantic facts must match
  the frozen baseline for each paired seed. Aggregate uniqueness cannot substitute for this check.
  Syntax and prompt surface may change; no new action/object/subject/location may be invented by realization.
- **D3 selection changes:** per-seed action choices may change within eligible sets, but count/missingness/quality
  guards remain. Safety/compatibility/EPIG and history penalties take precedence over diversity scheduling.
- **Determinism:** same source/config/workflow/seed/history produces byte-identical canonical report and prompt
  replay; mismatch count **0**. Baseline-to-candidate prompt equality is not required.
- **V150 freeze:** subjects **135**, locations **109**, compatibility rows **8227**, base variations **150184**,
  missing action pools **0**. Dedicated bugfix exception rules in spec2.2 remain unchanged.
- Public node I/O and context_json contract/version unchanged; composition_mode=false rollback maintained.

### Prompt-quality and promotion guards

The Effective Diversity gate supplements existing quality contracts; it does not supersede them.
A1.5 did not measure naturalness/consistency/image suitability, so their baselines must be obtained from the
same frozen source on the existing fixed **64 control +16 exploration** cohort. Do not fill unknown scores with zero.

- Preserve the stricter V150 automatic non-regression rules: zero increase in punctuation anomalies,
  repeated n-grams, semantic-family repetitions, identity defects, hard conflicts, fallback rate, replay mismatch,
  context bytes p95/max and policy issues; no decrease in exact-unique ratio. Policy hard gates for conflicts,
  identity violations, runtime/record errors and determinism stay **0**; banned-domain leakage stays **0**.
- `tools/compare_prompt_quality.py` generic guard tolerance0.02 and context ratios1.10/1.25 are **not** permission
  to relax those V150 guards. Apply the stricter preservation checks to comparison metrics as well.
- `tools/compare_variation_prompt_pair.py` has a quantity-expansion target (`location_signature_entropy` increase).
  This deferred expansion target is not a renderer/scheduler target. Do not repurpose its pass/reject result as
  implementation of the new Effective Diversity criteria. Use the existing rendering comparison path plus this
  lock's explicit checks; preserve the applicable existing quality effect-size/guard/review conditions.
- Current V150 v7 qualitative requirements remain: targets naturalness/image_prompt_suitability,
  guards consistency/protagonist_clarity/redundancy, and diversity through current-source corpus confirmation.
  Two independent lanes ×20 predeclared pairs; each pairwise dimension requires at least36 non-abstain votes
  (better+worse+equal). Targets additionally require at least20 directional votes (better+worse),
  improvement support=better/(better+worse)>=0.65 and lane direction agreement.
  For both targets and pairwise guards, regression=worse/(better+worse+equal)<=0.10;
  guards do not require directional improvement or lane agreement. Candidate-only hard defects **0**. Do not recycle historical votes.
- Prompt-changing activation milestones still require comparison-bound blind review, fresh three ×256-seed
  confirmations (consistency/naturalness/diversity), applicable full tests/data/full-flow/widgets/frontend/browser
  gates and release audit. Do not reuse V150's already used confirmation holdouts as fresh holdouts.
- The @2048 thresholds must still pass on matching prefixes in the final release report. @8192 guards compare
  against a source-bound **V150 release-profile** baseline obtained before final adoption evaluation;
  the reference-only8192 records from A1.5 do not supply measured @8192 rates. No fabricated release threshold.

Authority: `docs/prompt_quality/README.md`, V150 completed handoff, and the unchanged contracts below.

| Contract | SHA256 |
|---|---|
| vocab/data/prompt_quality_policy.json | 2a58867b85ba6827cea848623f6214b767dea147265e155ea5110ab6ef31fae7 |
| vocab/data/variation_semantic_review_policy_v4.json | 270a3e523a57c1c3e730a0cc5aa13729aefc166de70cacd6ff0989d8f3e15024 |
| tools/compare_prompt_quality.py | 6655a5d3eb6361401948ab5d66c096c5f7940bb5c147fa922508402555fc1cae |
| tools/compare_variation_prompt_pair.py | 97602da28cf4729925ce4581b142181f1797d1698abf06cd0dd498c3605f8080 |
| tools/semantic_review_contract.py | b70184a8464c06799d279606dabf8070442d1e7b966c3d981a87550d037f7ba7 |

### Lock boundary examples (for downstream gate checks)

- Normalized entropy0.855076 fails the N2 target;0.855077 passes that target only (other guards still required).
- Covered V150 action keys153 fail;154 pass the absolute action target if stage-relative improvement also holds.
- Core uniqueness1962 fails at@2048;1963 satisfies that floor. One exact/normalized duplicate fails.
- Run16 satisfies the N2-only ceiling but fails the scheduler <=15 target; a missing comparison receipt blocks
  coverage evaluation even if the candidate's own report displays a higher ratio.
- A larger declared K, missing metadata or a smaller reference set cannot establish improvement by itself.

Acceptance of the document lock does not certify a candidate or implement an automatic comparator.
Downstream milestone tasks must produce explicit target/guard verdicts bound to this section's lock ID/hash.

---

## 8. Natural Language Realizer v2 State

```text
State: CANDIDATE-01 REJECTED; INTERNAL FIXTURES READY; NOT ACTIVE
Metadata: vocab/data/natural_language_realizer_v2.json (validated, not active)
Current realizer tests: 37 pass / 0 expected failures
Required active families: 6
Optional families: up to 2
Active default: no
Legacy rollback: composition_mode=false
```

Family status:

| Family | Implemented | Eligible tests | Active |
|---|---|---|---|
| subject_action_scene | v2 internal candidate | PASS (bounded fixtures) | no |
| subject_action__scene_tail | v2 internal candidate | PASS (bounded fixtures) | no |
| scene_lead_subject_action | v2 internal candidate | PASS (bounded fixtures) | no |
| action_lead_subject_scene | v2 internal candidate | PASS (bounded fixtures) | no |
| subject_scene_action | v2 internal candidate | PASS (bounded fixtures) | no |
| subject_action_scene_insert | v2 internal candidate | PASS (bounded fixtures) | no |
| scene_sentence__subject_action | optional | pending | no |
| subject_action_progress__scene | optional | pending | no |

Candidate receipt:

```text
candidate HEAD: 1b159bf66fa5202d27908ed63fe7d5fe4cb590f3 + isolated allowlisted bridge
candidate source tree: 75ec250c162a51106aad1fce3c597d564e35c15314e27cc587922e771ecfb31f
effective-diversity report: assets/results/diversity_refactor/n27-candidate-01/candidate-root/assets/results/v2-gate.json
prompt-quality comparison: assets/results/diversity_refactor/n27-candidate-01/quality-comparison.json
verdict: REJECTED
v2 applied: 0 / 2048
active apply: not performed
```

---

## 9. Deterministic Diversity Scheduler State

```text
State: NOT STARTED
Core primitive: pending
Syntax integration: pending
Action integration: pending
Optional axes: none approved
```

Targeted axes:

| Axis | Baseline bias measured | Scheduler integrated | Verdict |
|---|---|---|---|
| syntax_family | no | no | pending |
| action_family | no | no | pending |
| garnish_family | no | no | not authorized |
| clothing_family | no | no | not authorized |

---

## 10. Before / After Comparison

Fill only with hash-bound reports. Realizer v2 column below is **candidate-01 / REJECTED**, not an adopted release.
The two observed candidate structures are retained v1 fallbacks; no actual v2 rendering occurred in2048 records.

| Metric | V150 baseline | Realizer v2 | Realizer v2 + Scheduler |
|---|---:|---:|---:|
| semantic_core_unique@2048 | 0.958496 (1963/2048) | 0.958496 (1963/2048) | pending |
| semantic_frame_unique@2048 | 0.997070 (2042/2048) | 0.997070 (2042/2048) | pending |
| action_family_coverage@2048 | 0.863905 (146/169) | 0.863905 (146/169) | pending |
| syntax_family_coverage@2048 | 1.000000 (2/2) | 1.000000 (2/2 fallback shapes) | pending |
| normalized_prompt_duplicate_rate | 0.000000 | 0.000000 | pending |
| syntax_entropy_normalized | 0.814359 (K=2) | 0.315037 (declared K=6) | pending |
| max_same_syntax_run | 16 | 16 | pending |
| max_same_action_run | 5 | 5 | pending |
| semantic consistency | pending | pending | pending |
| naturalness | pending | pending | pending |

---

## 11. Work Log

Codex は各 task 後に追記する。

Template:

```text
### YYYY-MM-DD — TASK-ID — TITLE

State: PROMOTED | ELIGIBLE | REJECTED | BLOCKED

Baseline HEAD:
Candidate HEAD:

Owned files:
- ...

Changes:
- ...

Commands:
- `...`

Results:
- ...

Metrics:
- target:
- guards:

Decision:
- ...

Follow-up:
- ...

Evidence:
- artifact path:
- sha256:
```

---

## 12. Decision Log

### D-001 — Freeze V150

Date: 2026-09-06
Status: ACCEPTED

Decision:

```text
V150 is the semantic-base reference for this wave.
V250/V350/V500 are deferred.
Base variation count is not the optimization target.
```

Reason:

```text
Further quantity expansion has high authoring/review/Codex cost.
The repository already has a substantial semantic-only base and existing
ActionFrame/ContentPlan structures that can create more effective diversity
through better realization and deterministic selection.
```

### D-002 — No LLM in runtime

Date: 2026-09-06
Status: ACCEPTED

```text
Effective diversity, realization, and scheduling remain pure rule-based.
LLM comparison may be external research only, not runtime dependency.
```

### D-003 — Measure before tuning

Date: 2026-09-06
Status: ACCEPTED

```text
Do not lock numeric Realizer/Scheduler improvement thresholds until
A1 Effective Diversity baseline has been measured.
```

---

## 13. Blockers

Initial wave-setup status: none.

Current:

```text
N2.8 BLOCKED: candidate-04 rejected (N2.7-R3); normalized entropy and six observed families unmet.
Next actionable task: N2.7-R4 productive action and common subordinate-clause coverage.
No active application; numerical/policy thresholds unchanged.
```

Add blockers without deleting previous entries.

---

## 14. Final Receipt

State:

```text
NOT READY
```

Final HEAD:

```text
pending
```

Final verification:

```text
pending
```

Final wave verdict:

```text
pending
```

Promoted features:

```text
pending
```

Rejected/deferred features:

```text
V250/V350/V500: deferred before wave start
others: pending
```

## 15. Initial implementation scope / cleanup plan

2026-09-06: ユーザーの新方針による開始依頼に基づき、今回は F0.1–F0.4 を順次実装する。
全 wave の完了や Realizer/Scheduler の採用をこの初期変更では宣言しない。
元資料は `docs/scg_diversity_refactor_docs/docs/diversity_refactor/` に保持し、
進捗更新の正本はこのディレクトリとする。

1. F0.1: 仕様・タスク・進捗を正本へ配置し、相互リンクと実行契約を確認する。
2. F0.2: 現行 main の HEAD・計数・validator・full flow と既存回帰の証拠を取得する。
3. F0.3: README / CURRENT_STATUS / REPO_STRUCTURE と旧計画入口の古い active roadmap 表示を修正する。
   V150 の履歴・証拠と将来の数量拡張計画を保存する。
4. F0.4: 既存テストが同じ可変 expected_metrics を読むだけでは防げない数量拡張を、
   独立した V150 計数契約テストで検出する。正常なデータ修正のため全 byte の固定はしない。

Smells: stale documentation / competing roadmap entrypoints; missing independent freeze regression.
Behavior lock: existing variation, generation determinism, prompt snapshots, public node/workflow tests before new guard.
Quality gates: F0.2 prescribed commands; focused unittest; Python syntax check; diff whitespace check.
Runtime/API/data changes: none. Dependencies: none. Numeric diversity thresholds: deferred until A1.6.
Independent review: native subagent reads plan and existing metric tests; implementation stays single-owner and sequential.

### 2026-09-06 — F0.1 — Canonical wave docs

State: PROMOTED
Owned files: `docs/diversity_refactor/spec.md`, `tasks.md`, `progress.md`.
Changes: supplied docs installed; relative cross-links added; sequential F0 cleanup plan recorded.
Verification: three files listed by `git ls-files`; all cross-links present; execution contract and V150 freeze retained.
Independent review: APPROVE; use independent count expectations, retain deferred planner tests.
Git: new canonical docs staged to satisfy tracked acceptance; no commit created.
Next: F0.2 baseline capture (read-only runtime/data).

### 2026-09-06 — F0.2 — Exact V150 baseline

State: PROMOTED
Baseline HEAD: `1b159bf66fa5202d27908ed63fe7d5fe4cb590f3` (main).
Candidate: same runtime/data; uncommitted documentation changes.
Owned files: progress + ignored `assets/results/diversity_refactor/f0-baseline/` receipts/logs.
Commands: section 5 commands and `python -m unittest assets.test_calc_variations assets.test_variation_scope assets.test_build_compatibility_review assets.test_build_action_pools assets.test_context_nodes assets.test_workflow_samples assets.test_prompt_snapshots assets.test_context_pipeline assets.test_context_state_adapter assets.test_determinism`.
Results: all exit 0; validators clean; full flow passes; 40 regression tests pass.
Decision: measured baseline matches supplied V150 reference; F0.3 may begin.
Evidence: receipt SHA256 `35fffa0e2e880177c9728003fc7cad202aa9b1d80d82b595afbccd6c44abb439`.
Commit: none created.

### 2026-09-06 — F0.3 — Roadmap switch

State: PROMOTED
Owned files: README.md, CURRENT_STATUS.md, REPO_STRUCTURE.md,
`docs/variation_expansion/README.md`, `docs/variation_expansion/500k_loop_plan.md`,
`docs/scg_diversity_refactor_docs/README.md`, progress.
Changes: active roadmap points to diversity refactor; V250/V350/V500 explicitly deferred;
old 100k verification/expansion history labeled historical; current metrics updated from F0.2.
Verification: all new local diversity-doc links resolve; all 120 protected-file SHA256 values unchanged.
Decision: preserve V150 evidence and 500k roadmap; do not apply retired stage instructions.
Commit: none created. Next: F0.4 independent freeze regression.

### 2026-09-06 — F0.4 — Independent V150 freeze contract

State: PROMOTED
Baseline HEAD: `1b159bf66fa5202d27908ed63fe7d5fe4cb590f3`.
Candidate HEAD: unchanged; working-tree documentation/test changes only; no commit created.
Owned files: `assets/test_v150_freeze_contract.py`, tasks/progress.
Changes: two tests compare measured data and scope expectations to independent V150 metrics
(135 subjects / 109 locations / 150,184 variations / 8,227 rows), with missing-pool and scope-cardinality guards.
Existing validators retain source-generation and membership checks; no byte-lock or doc-wording assertions added.

Commands:
- `python -m unittest assets.test_v150_freeze_contract assets.test_calc_variations assets.test_variation_scope assets.test_build_compatibility_review assets.test_build_action_pools assets.test_context_nodes assets.test_workflow_samples assets.test_prompt_snapshots assets.test_context_pipeline assets.test_context_state_adapter assets.test_determinism`
- `python -m py_compile assets/test_v150_freeze_contract.py`
- `git diff --check` / `git diff --cached --check`
- In-memory mutation probe of the real unittest cases: each of four measured counts incremented;
  subject/location scope and matching expected count expanded together; descriptive metadata corrected separately.

Results:
- 42 focused tests OK; Python syntax check PASS.
- All six intentional expansion mutations fail with assertions; non-count metadata correction passes.
- All 120 protected-file hashes match F0.2.
- No new dependency; no configured/installed ruff, mypy or pyright found. Separate lint/typecheck tools not run;
  syntax and whitespace checks plus existing data validators supply the applicable static checks for this test/docs change.
- Full unittest/frontend/browser/blind-review/release audits were not rerun: no runtime/data/UI changes;
  milestone gates remain required before any prompt-surface adoption.

Decision: F0.1–F0.4 complete; next task A1.1 locks the metric schema before audit implementation.
Remaining risk: aggregate counts do not detect equal-count semantic replacements; source/data validators and
explicit protected-surface review remain required. Legitimate count-changing bug fixes require a dedicated
exception task and an intentional baseline update with before/after prompt-quality evidence (spec 2.2).
Evidence:
- `assets/results/diversity_refactor/f0-baseline/freeze-regression.log`; SHA256 `3ff9423862db95b484b72e93214df54ed6e444dabfe10eb3d830a6cc870b165e`.
- `assets/results/diversity_refactor/f0-baseline/freeze-mutation-checks.json`; SHA256 `e7d486bd892740e2f82f3997764ff766ffd0d48417f54d2480d65860b353194d`.

Independent final review: PASS (canonical roadmap, historical labels, and freeze guard).
Canonical-copy Markdown trailing whitespace normalized for diff checks; intake source files retained unchanged.

### 2026-09-06 — A1.1 — Metric schema lock (start)

State: IN_PROGRESS
Owned files: `docs/diversity_refactor/spec.md`, `tasks.md`, `progress.md`.
Plan: inspect existing runner/ActionFrame/ContentPlan metadata and canonical report utilities;
resolve missing-value, reference-universe, prefix denominator and syntax metadata ambiguities;
write the v1 contract with calculable examples; independently review; verify docs and unchanged runtime/data.
This task only specifies the audit. A1.2 metric code and A1.3 extraction remain separate sequential tasks.
No numeric promotion threshold is locked before A1.6.

### 2026-09-06 — A1.1 — Metric schema locked

State: PROMOTED
Baseline/Candidate HEAD: `1b159bf66fa5202d27908ed63fe7d5fe4cb590f3`; documentation-only working-tree update; no commit.
Owned files: `docs/diversity_refactor/spec.md`, `tasks.md`, `progress.md`.

Changes:
- Locked metric names and payload fields; canonical signature fields/sources; missing-value and array rules;
  ordered prefixes 128/512/2048/8192; exact/normalized duplication and safe text normalization.
- Coverage now explicitly means observed reference coverage, separate from legacy unique/sample metrics.
  Missing/reference-outside values cannot silently inflate coverage. Empty reference is unmeasured (null).
- Locked entropy denominator to declared active families, zero-bin handling, final six-decimal rounding,
  source/workflow/config/reference hashes and canonical output representation.
- Defined limited smoke reference and reusable 8192-probe gate/release references. Finite probe coverage
  is not claimed to exhaust the theoretical semantic space. Numeric adoption targets remain PENDING until A1.6.
- Established builder-debug observation through exact-parity replay of the existing builder with trace-resolved
  inputs; no public node output changes or final-prose syntax inference are required.

Checks:
- `python assets/results/diversity_refactor/a11-schema/verify_contract.py`: PASS.
- Four seeds (0–3): standard runner record replay byte-stable; builder replay matches raw_prompt exactly;
  ContentPlan.syntax_family and ActionFrame available after replay.
- Published arithmetic examples independently calculated (entropy/duplicates/coverage/multi-valued sets)
  and subject-alias normalization example confirmed.
- source_tree_hash stable across probes; 120 protected variation files still match F0.2.
- `git diff --check`: PASS. No runtime/test/data implementation changed in A1.1, so no repeat full test,
  frontend/browser, lint/typecheck or release gate. Probe is feasibility evidence, not an implemented audit test.

Investigation correction:
- An exploratory replay passing context_json directly as a string failed parity because the internal builder
  expects a decoded context. Using the public node's context_from_json conversion resolved the mismatch;
  the required decoding and exact parity check are now part of the contract.
- Review corrections: explicit 0*log2(0) convention and coverage-null type exception; verified real scene_axis
  keys progress/obstacle instead of the differently named legacy slot keys.

Decision: A1.1 Acceptance satisfied; proceed next to A1.2 pure metric helpers with regression fixtures first.
Remaining limits: signatures use finite/coarse existing classifiers; missingness remains visible;
reference denominator changes cannot establish improvement by ratio alone. Audit CLI/metrics implementation,
V150 diversity measurement and adoption thresholds are still pending.
Evidence:
- Contract SHA256: `a0dec4bb3f4bbfd5759e596c3baa3bcced827a0298e603fa52f481f1824123ab` (`docs/diversity_refactor/spec.md`).
- Receipt: `assets/results/diversity_refactor/a11-schema/receipt.json`; SHA256 `b7a693b1fadcaaeae95bb1047a6aa3c60c951370e2527925797796a15dde26d1`.
- Source tree before/after: `63ebeded51a2e5c050acc52f87c60afc2ddc1a38f6e0a3df491412d0f93103b6` (supplemental inputs are specified for the future audit envelope, not mislabeled as included in this existing manifest hash).

Independent final review: PASS — both formula/type corrections and scene-axis/clothing sources verified; no unresolved A1.1 blocker.

### 2026-09-06 — A1.2 — Pure metric helpers (start / implementation plan)

State: IN_PROGRESS
Owned files: `tools/effective_diversity_metrics.py`, `assets/test_effective_diversity_metrics.py`, tasks/progress.
Plan before code:
1. Add numerical regression fixtures for sections 6.3/6.6: empty/single/balanced/skewed inputs,
   incomplete signatures, reference misses, duplicate prompts and null-separated runs.
2. Implement small pure helpers accepting already extracted canonical signatures/categories; reuse
   canonical_json_bytes and normalize_subject_to_girl. No runner execution, file reads, selection or new dependency.
3. Test deterministic ordering, unchanged inputs, output rounding and invalid-input rejection.
4. Run focused and related regression tests, syntax/diff checks and independent review.
Boundary: semantic extraction remains A1.3; workflow/config validation, report assembly and CLI remain A1.4.
Smells avoided: duplicated canonicalization/alias rules; mixing extraction, generation and aggregation.

### 2026-09-06 — A1.2 — Pure metric helpers complete

State: PROMOTED
Baseline/Candidate HEAD: `1b159bf66fa5202d27908ed63fe7d5fe4cb590f3`; uncommitted tools/tests/docs changes.
Owned files: `tools/effective_diversity_metrics.py`, `assets/test_effective_diversity_metrics.py`, tasks/progress.

Changes:
- Added metric_prefixes, normalize_prompt, semantic_uniqueness, axis_coverage,
  max_consecutive_run, syntax_entropy and repetition_metrics.
- Reused existing canonical JSON and subject-alias utilities. Alias normalization operates per token,
  avoiding the runtime helper's repeated-girl deletion; tests preserve word multiplicity, negation and word order.
- Semantic helpers receive prevalidated canonical mappings or None for invalid signatures. They do not
  parse prompts, generate context, read data, choose candidates or mutate caller inputs.
- Kept seed/workflow validation and sorting outside these helpers (A1.4); run length preserves supplied order.
- No new dependency or runtime/data modification. Metric schema/spec hash unchanged.

Behavior lock / verification:
- Added tests before implementation; initial run failed as expected with ModuleNotFoundError for the new module.
- `python -m unittest assets.test_effective_diversity_metrics`: 31 tests OK.
- `python -m unittest assets.test_effective_diversity_metrics assets.test_v150_freeze_contract assets.test_action_frame_realizer assets.test_prompt_quality_analyzer assets.test_prompt_quality_runner assets.test_determinism`: 83 tests OK.
- Cases cover empty/single/balanced/skewed distributions, declared versus observed K, missing versus empty,
  canonical key order, unobserved/out-of-reference categories, duplicate rates, null-separated runs,
  non-finite values, invalid prompts/categories/counts and misaligned inputs.
- Independent Python processes with PYTHONHASHSEED=1/999 produce identical canonical aggregate bytes.
- `python -m py_compile tools/effective_diversity_metrics.py assets/test_effective_diversity_metrics.py`: PASS.
- Both staged/unstaged diff whitespace checks and new-file whitespace check: PASS.
- Independent review: PASS; reviewer also ran the 31 focused tests successfully.
- All 120 protected-file SHA256 values still match F0.2; A1.1 contract hash unchanged.
- Separate lint/typecheck tooling remains unconfigured/uninstalled; no package added for this task.
  Full release/frontend/browser gates were not rerun for standalone pure helper additions.

Decision: A1.2 Acceptance satisfied. Next A1.3 builds canonical semantic signatures from actual runner
context/ActionFrame/debug metadata; A1.4 connects the audit CLI. No diversity improvement claim or threshold yet.
Remaining boundary: caller must supply canonical validated signatures and correctly ordered aligned observations.
The test fixtures establish calculations, not real-world semantic extraction quality or full audit operation.
Evidence:
- `assets/results/diversity_refactor/a12-metrics/receipt.json`; SHA256 `d0b8eda5474d8387d4f379a37a164d704ce0688c61a828688b909a07246b13dc`.
- `assets/results/diversity_refactor/a12-metrics/regression.log`; SHA256 `fd21b6cb0feeb55eabe7d47db004372c9cc6b608ad5736383e9b75cdfdf5ad32`.
- New helpers/tests change source manifests; earlier A1.1 feasibility receipt is historical evidence, not a new candidate source receipt.

### 2026-09-06 — A1.3 — Signature extraction (start / implementation plan)

State: IN_PROGRESS
Owned files: `tools/effective_diversity_signatures.py`, `assets/test_effective_diversity_signatures.py`, tasks/progress.
Plan before code:
1. Add regression fixtures for canonical aliases, surface-only changes, object/verb changes, missing/stale frames,
   latest-history matching, null versus known-empty families, and deterministic output without input mutation.
2. Keep resolver/data-backed extraction in a sibling module so A1.2's arithmetic helpers remain pure.
   Reuse existing character/location/clothing resolvers, ActionFrame validation, classifiers and scene/mood data.
3. Return all core/frame keys plus validity, coverage axes and separate missing/source diagnostics.
   Accept builder metadata only when its prompt matches the record raw_prompt; replay itself remains A1.4.
4. Run focused/related regression, read-only real-runner probes, static checks and independent review.
Smells avoided: reimplementing existing semantic classifiers; unvalidated history reuse; prose-derived signature inflation.
No runtime/data/public node changes, vocabulary expansion or dependency additions are planned.

### 2026-09-06 — A1.3 — Semantic signature extraction complete

State: PROMOTED
Baseline/Candidate HEAD: `1b159bf66fa5202d27908ed63fe7d5fe4cb590f3`; uncommitted tools/tests/docs changes.
Owned files: `tools/effective_diversity_signatures.py`, `assets/test_effective_diversity_signatures.py`, tasks/progress.

Changes:
- Added build_semantic_signatures(record_or_context, builder_decision=None, mood_keys=None).
  Output: fixed core/frame objects, valid flag, eight coverage axes and separate source/missing/rejection diagnostics.
  A1.2 callers use projection.core/frame when valid, otherwise None; partial fields remain visible for diagnostics.
- Reused existing character/location/clothing resolvers, ActionFrame authority checks, scene-axis loader,
  object/family classifiers and mood dictionary. Kept data-backed extraction outside the pure arithmetic module.
- Builder decisions require exact stored prompt/raw_prompt equality; syntax stays outside semantic signatures.
  Actual replay remains A1.4 responsibility. ContentPlan placeholders/final prose never supply semantic identity.
- Frame authority order: builder → current extras → latest matching SceneVariator frame/slots.
  History new_action is authoritative when present, even empty; action_updated without new_action is rejected.
  Action/location mismatch cannot fall back to an older history entry.
- Preserve null versus explicitly empty family observations through original raw frame/slot fields;
  ActionFrame default empty strings do not hide missing metadata.

Verification:
- Tests first: expected missing-module failure before implementation.
- New raw-slot regression initially reproduced [] instead of null; original source field presence now preserved.
- `python -m unittest assets.test_effective_diversity_signatures assets.test_effective_diversity_metrics`: 55 tests OK (24 signatures + 31 arithmetic).
- `python -m unittest assets.test_effective_diversity_signatures assets.test_effective_diversity_metrics assets.test_v150_freeze_contract assets.test_action_frame_realizer assets.test_character_resolution assets.test_location_resolution assets.test_context_state_adapter assets.test_prompt_quality_runner assets.test_determinism`: 115 tests OK.
- Signature tests cover aliases, named identity, surface paraphrases, object/verb changes, missing/stale/unsupported
  frames, refreshed history, null/empty/unclassified families, enum fallback, builder parity and syntax disagreement.
- Cross-process PYTHONHASHSEED=1/999 projection bytes identical; input immutability and typed context supported.
- Read-only 128-seed runner smoke: all 128 builder prompt replays match, all 128 signature replays byte-equal,
  all 128 have valid subject/location/action core. Syntax observations: single-sentence 101, two-sentence 27.
- Important measured limitation: primary_object_or_object_family is null in 116/128 samples under the existing
  finite classifier/unique-primary rule. These are unknown objects, not 116 novel values or proven object-free scenes.
  A1.5 must retain missing counts; this probe is not evidence of complete object coverage or improved diversity.
- `python -m py_compile tools/effective_diversity_signatures.py assets/test_effective_diversity_signatures.py`: PASS.
- Diff checks/new-file whitespace: PASS; independent review and independent 24-test rerun: PASS.
- All 120 protected variation files unchanged; A1.1 spec hash unchanged; source tree stable during smoke.
- No new dependencies, runtime/data/public I/O changes. Separate lint/typecheck tools remain unavailable;
  release/frontend/browser gates were not rerun for this read-only audit helper.

Decision: A1.3 Acceptance satisfied. Next A1.4 connects the existing runner, metadata replay,
reference universe and metrics into the deterministic audit CLI. No numeric adoption threshold or improvement claim.
Evidence:
- `assets/results/diversity_refactor/a13-signatures/receipt.json`; SHA256 `27b3dc2f9ff3bea1fd8d4682c3ed14d1029b126b88d044ab303b966434c1794b`.
- `assets/results/diversity_refactor/a13-signatures/signatures.jsonl`; SHA256 `2fca4fbde67eca386fe49f84f66026f1306e90bc5758b25d8157d1298e0f92c3`.
- `assets/results/diversity_refactor/a13-signatures/regression.log`; SHA256 `f0241072a8bc6daba086ba1708c0ad3935257ba8513d747c8290571f78a50373`.
- Current source_tree_hash during smoke: `f0d82ec23bf28995070372353a8fb2dc49d84ad59f3b6e27d9a7273ef87515bf`; older task receipts remain historical.

### 2026-09-06 — A1.4 — Audit CLI (start / implementation plan)

State: IN_PROGRESS
Owned files: `tools/audit_effective_diversity.py`, `assets/test_effective_diversity_audit.py`, tasks/progress.
Plan before code:
1. Add small integration fixtures for report determinism, fixed reference counts, overlap reuse,
   cache identity/shape rejection, source drift, builder parity, invalid arguments and safe output paths.
2. Connect existing runner → exact builder replay → A1.3 signatures → A1.2 metrics.
   Use bundled workflow/default runner profile; no custom graph interpreter or public node edits.
3. Bind existing source manifest plus supplemental inputs, workflow/config/contract and reference hashes;
   cache only explicit matching reference artifacts, never silently repair stale evidence.
4. Canonical JSON to stdout or --output; optional --reference / --write-reference for reuse.
   Validate file inputs before execution and output scope before any writes; atomically replace generated files.
5. Verify small tests, separate 128-seed smoke reruns/cache equality, related regression and independent review.
Boundary: formal 2048/8192 baseline and numeric target selection remain A1.5/A1.6.

### 2026-09-06 — A1.4 — Deterministic audit CLI complete

State: PROMOTED
Baseline/Candidate HEAD: `1b159bf66fa5202d27908ed63fe7d5fe4cb590f3`; uncommitted tools/tests/docs changes.
Owned files: `tools/audit_effective_diversity.py`, `assets/test_effective_diversity_audit.py`, tasks/progress.
Documentation after verification: README.md, CURRENT_STATUS.md, REPO_STRUCTURE.md now expose the CLI and actual next task.

Changes:
- Existing workflow runner → exact builder/context replay → signature extraction → per-prefix metrics.
  No graph interpreter, semantic classifier, arithmetic or canonical JSON implementation duplicated.
- CLI targets the bundled workflow/default supported runner profile; --profile smoke/gate/release,
  --seed-start, --sample-count, --output, --reference, --write-reference.
- Source manifest plus root supplemental files, exact file-input resolution, workflow/contract/config,
  raw ordered records and fixed reference hash are recorded. Source identity checked before/after generation.
- Reference probes fixed to 0..127 (smoke) or 0..8191 (gate/release); overlap generated once,
  explicit matching cached reference can be reused. Raw record hashes are streamed rather than retaining
  every large execution trace in memory. Missing and out-of-reference categories remain visible.
- Report bytes exclude timestamps, host, output paths and telemetry. Errors are structured JSON/nonzero exits.
- Output scope: repository writes only under assets/results; explicitly chosen external files subject to sandbox.
  Reject output/cache/export collisions and source destinations before work; publish reference before success report,
  using same-directory temporary files and atomic replacement. Failed generation/export preserves existing report.

Verification:
- Tests written first: expected module import failure before implementation.
- New regressions reproduced and then fixed: probe-only empty prompt accepted; loaded graph vs source snapshot mismatch;
  malformed node triggered AttributeError; reference-write failure left a success report.
- Review fix: preserve whitespace in nonblank mood json_path exactly as runtime does; do not bind a trimmed alternate path.
- `python -m unittest assets.test_effective_diversity_audit`: 19 tests OK; independent rerun/review PASS.
- `python -m unittest assets.test_effective_diversity_audit assets.test_effective_diversity_signatures assets.test_effective_diversity_metrics assets.test_v150_freeze_contract assets.test_action_frame_realizer assets.test_character_resolution assets.test_location_resolution assets.test_context_state_adapter assets.test_prompt_quality_runner assets.test_determinism`: 134 tests OK.
- Small gate/release profile probe confirmed shared fixed reference with distinct measurement sizes (2/3 test samples).
  Actual 2048/8192 measurement is deferred to A1.5; unit tests keep small probe counts.
- `python -m py_compile tools/audit_effective_diversity.py assets/test_effective_diversity_audit.py`,
  staged/unstaged diff checks and new-file whitespace: PASS. Separate lint/typecheck tooling remains unavailable.
- Three independent-process smoke runs (ordinary, ordinary repeat, cached reference) yield identical report bytes;
  standard 128 samples, 128 builder replays with zero mismatch. Canonical stdout checked separately on two samples.
- Current source manifest and contract hashes match reports; all 120 protected variation files unchanged.
- No runtime/data/public I/O/dependency changes. GUI/frontend/blind-review/release gates not rerun for audit-only CLI.

Reproduction (from repository root):

```bash
python tools/audit_effective_diversity.py --profile smoke --output assets/results/diversity_refactor/a14-cli/smoke-first.json --write-reference assets/results/diversity_refactor/a14-cli/reference.json
python tools/audit_effective_diversity.py --profile smoke --output assets/results/diversity_refactor/a14-cli/smoke-repeat.json
python tools/audit_effective_diversity.py --profile smoke --reference assets/results/diversity_refactor/a14-cli/reference.json --output assets/results/diversity_refactor/a14-cli/smoke-cached.json
```

Decision: A1.4 Acceptance satisfied. A1.5 will capture the formal V150 effective-diversity gate baseline;
no improvement thresholds selected. Smoke coverage uses its own finite reference and is not adoption evidence.
Existing coarse object recognition/missingness limitations remain; no vocabulary added to inflate results.
Run a fresh CLI process for each source snapshot; loaded Python modules/resolver caches are not hot-reloaded.

Error-code vocabulary (v1 implementation):

```text
artifact_path_collision
builder_context_mismatch
builder_replay_mismatch
inputs_changed
invalid_arguments
invalid_builder_trace
invalid_cleaned_prompt
invalid_input_or_io
invalid_or_duplicate_seed
invalid_profile
invalid_record_identity
invalid_reference
invalid_reference_axes
invalid_sample_range
missing_builder_metadata
mixed_record_identity
record_seed_mismatch
reference_hash_mismatch
reference_identity_mismatch
reference_probe_mismatch
unknown_syntax_family
unsafe_output_path
unsupported_dynamic_input
unsupported_file_input
unsupported_workflow
workflow_validation_error
```

Evidence:
- `assets/results/diversity_refactor/a14-cli/receipt.json`; SHA256 `2f2e638e2588d87649c8275126be48e014b212f6159750460d2413cc3b642d99`.
- All three smoke report SHA256: `b0a617969e2d95341a5441270565b51f1e4279867686d5849bf2a844352473c1`.
- Source hash: `448e4240b6f8321e1ba9332f9f624b7bf9419d255f715f438fd87b13dd556214`.
- Regression log SHA256: `05b9b13dabb8a446992c57ce66f80a2d4c1f8eab61c9f046c241de54a10a29f2`.

### 2026-09-06 — A1.5 — Formal V150 diversity baseline (start)

State: IN_PROGRESS
Owned files: generated gate/reference/receipt artifacts, tasks/progress; README/CURRENT_STATUS pointers after verification.
Plan: bind current source/config/contract; generate fixed 8192 reference and measure first 2048 records;
validate all prefix metrics/reference/hash invariants; record measured baseline without selecting thresholds.
Prior focused 134-test evidence may be reused only if current source identity matches A1.4.
No runtime/data/test changes planned. A1.6 threshold selection remains separate.

### 2026-09-06 — A1.5 — Formal V150 diversity baseline captured

State: PROMOTED
Baseline/Candidate HEAD: `1b159bf66fa5202d27908ed63fe7d5fe4cb590f3`; current uncommitted audit implementation bound by source hash.
Owned files: tasks/progress, generated gate/reference/replay/receipts; README/CURRENT_STATUS updated to measured status.
Runtime/data/test implementation changes: none.

Commands:

```bash
python tools/audit_effective_diversity.py --profile gate --output assets/results/effective_diversity/v150_baseline_gate.json --write-reference assets/results/effective_diversity/v150_reference_8192.json
python assets/results/diversity_refactor/a15-baseline/verify_baseline.py
python tools/audit_effective_diversity.py --profile gate --reference assets/results/effective_diversity/v150_reference_8192.json --output assets/results/effective_diversity/v150_baseline_gate_replay.json
```

Results:
- All commands exit 0. Fixed 8192-seed probe; 2048 measured records with prefixes 128/512/2048.
- Formal report and fresh-process cached-reference replay are byte-identical.
- Source identity matches A1.4 and remains unchanged; the existing 134-test log hash was verified and reused.
  No unnecessary repeat full tests, release/GUI/blind review, or second 8192 probe.
- Independent checks: report/reference canonical bytes and hashes, source/config/contract identity,
  prefix counts, uniqueness/semantic-duplicate arithmetic, coverage denominators, syntax counts/entropy/dominance,
  2048 builder replays with mismatch 0, and 120 protected-file content hashes.
- Independent evidence review: PASS. Report arithmetic/identity checks are separate from the tested CLI's
  record hash/text-duplicate/run-length calculations; raw records are not saved in the compact report.
- §6 stores the complete measured table, observed reference sizes and missingness. §10 baseline column populated
  only from this hash-bound report; candidate, naturalness and semantic-consistency cells remain unmeasured.

Interpretation:
- @2048: core 1963 distinct (0.958496), frame 2042 distinct (0.997070); no exact/normalized prompt duplicates.
- Syntax: 1532 single-sentence / 516 two-sentence; normalized entropy 0.814359; maximum same-family run 16.
- Action coverage 146/169; maximum same-action-family run 5.
- Object identity unknown in 1769/2048 (86.377%). This remains visible and limits claims about semantic resolution.
- Subject/location/mood coverage is relative to observed 28/107/1 values for this workflow/probe,
  not V150's full dictionary. Reference generation does not count as release@8192 measurement.

Decision: A1.5 Acceptance satisfied. Next A1.6 locks targets/guards based on these measurements;
no threshold chosen and no new runtime feature promoted in this task.
Evidence:
- `assets/results/diversity_refactor/a15-baseline/receipt.json`; SHA256 `738d171ead9672946d35f5888de0bb6dd0e096fd474d480a41318cffeeae3d72`.
- Formal/replay report SHA256: `6c6bef1911ba9b9921f62b0f64adf4172ced2f9e32b0e4922cdd226e6267f733`.
- Source hash: `448e4240b6f8321e1ba9332f9f624b7bf9419d255f715f438fd87b13dd556214`.
- Generated artifacts remain ignored; tracked docs retain metric values and immutable hash bindings.

### 2026-09-06 — A1.6 — Target / guard lock (start)

State: IN_PROGRESS
Owned files: progress section 7, task acceptance, README/CURRENT_STATUS pointers; generated verification receipt.
Plan: derive numerical thresholds from A1.5 counts and existing diversity effect-size policy;
separate targets from strict guards; handle changed reference denominators and saturated axes;
preserve existing promotion/review authority; independently review the written contract and validate arithmetic.
No runtime/data/policy/comparator code edits; no new baseline generation or N2 implementation.

### 2026-09-06 — A1.6 — Targets / guards locked; Phase A complete

State: PROMOTED
Baseline/Candidate HEAD: `1b159bf66fa5202d27908ed63fe7d5fe4cb590f3`; docs-only update in this task.
Owned files: progress section 7 and task board, README/CURRENT_STATUS pointers; generated receipt/full-flow log.
Planning handoff: N2.1 now explicitly requires preservation of the baseline source snapshot before runtime edits.

Changes:
- Locked A1.6-2026-09-06/v1 against the A1.5 report: Realizer normalized syntax entropy>=0.855077,
  at least6 enabled/observed required families; scheduler syntax run<=15 and stage-relative improvement;
  action coverage>=154/169 baseline keys with explicit comparison-observation evidence.
- Derived the effect-size choice from the existing0.05 diversity policy. Preserved whole-count precision,
  baseline/stage-relative uniqueness, missingness, duplicates, quality, determinism and V150 guards.
- Defined saturated-axis behavior, candidate-local versus comparison reference identity,
  missing-evidence/failed-threshold verdicts and immutable baseline/per-seed evidence prerequisites.
- Preserved stricter V150 quality gates and current v7 voting/confirmation authority; no policy/code edits.
  Quantity-expansion location-entropy target is distinguished from rendering/scheduler targets.

Verification:
- Decimal-derived entropy0.855077 and action154 thresholds verified against A1.5 and policy0.05.
  Boundary checks distinguish0.855076/0.855077,153/154 and baseline unique-count floors.
- Guard table counts checked against baseline JSON; all cited policy/comparator SHA256 values verified.
- Independent review: PASS after clarifying v7 non-abstain/directional vote counts and support/regression denominators.
- `python tools/verify_full_flow.py`: PASS. Phase A gate/report evidence is A1.5; relevant134-test evidence from
  A1.4 remains valid under the unchanged source hash. No redundant full audit or Python test rerun.
- Source/spec contract and all120 protected variation-file hashes unchanged; staged/unstaged diff checks PASS.
- No runtime/data/dependency changes. Lint/typecheck not rerun for documentation-only changes.

Decision: A1.6 Acceptance satisfied; Phase A audit/baseline/criteria complete. Next N2.1 begins contract tests,
not runtime activation. This document lock is not an implemented target comparator or a measured candidate gain.
Remaining risks/limits: coarse object/frame observation, saturated reference axes, eligibility/naturalness constraints;
future evidence must satisfy the locked comparisons and applicable heavy promotion gates. No threshold relaxation
is implied if a candidate cannot safely meet the target.
Evidence:
- `assets/results/diversity_refactor/a16-thresholds/receipt.json`; SHA256 `33b6cc1112165fc93326bff1997db0ce42dd54cfd0addff8ab84259b26def8e3`.
- Section 7 lock SHA256 (UTF-8 text from its heading through the next separator): `6742b1b735de2e3ef9b53b732e51d54d260434a500ab84f32249334c24cfb7bd`.
- `assets/results/diversity_refactor/a16-thresholds/full-flow.log`; SHA256 `4e7024bbab9109cc83d937b39b25c4d869bce0b79243b3386352a5b1dc06feda`.

### 2026-09-06 — N2.1 — Realizer v2 contract tests (start / plan)

State: IN_PROGRESS
Owned files: `assets/test_prompt_realizer_v2.py`, tasks/progress, immutable baseline artifacts; status pointers after verification.
Plan before test edits:
1. Copy the source tree using the existing filtered snapshot copier, including uncommitted audit modules/tests,
   supplemental runtime files and contract docs. Hash all snapshot content and verify A1.5 source identity.
2. Add passing semantic/policy/determinism/fallback contracts plus explicit future syntax/debug contracts.
   Exercise existing ContentPlan/build/realize APIs so future failures describe behavior, not missing function imports.
3. Keep deferred N2.3–N2.6 requirements visible as unittest.expectedFailure; verify their undecorated bodies
   fail with intentional assertions, never import/type errors. Do not claim these requirements are implemented.
4. Run related regressions and independent review. Preserve runtime/public nodes/data unchanged.
Expected-failure markers are temporary test-first debt and must be removed in the owning implementation task;
unexpected success must fail the suite rather than silently retaining a marker.

### 2026-09-06 — N2.1 — Test-first Realizer v2 contracts ready

State: PROMOTED (contract-test task only; runtime v2 not implemented/activated)
Baseline/Candidate HEAD: `1b159bf66fa5202d27908ed63fe7d5fe4cb590f3`; new test file plus documentation changes.
Owned files: `assets/test_prompt_realizer_v2.py`, tasks/progress; CURRENT_STATUS/REPO_STRUCTURE status pointers.

Baseline preservation before test edits:
- Used existing `_copy_filtered_source` helper; no quantity-expansion materialization or data builders.
- 1120 source/support files copied, including uncommitted audit implementation and A1.6 contract docs.
- `assets/results/diversity_refactor/v150-before-n2/baseline-root` is the sealed baseline execution root.
- Source/support files and ZIP are read-only. Do not edit baseline-root; verify the manifest before reuse.
- Snapshot source hash matches A1.5. A cloned-CLI two-sample gate probe accepted the original8192 reference
  and matched the pre-N2 record hash. The archive preserves source independently of Git staging/commits.

Tests:
- 12 active passing contracts: fixed semantic facts, oracle negative controls (loss/invention/extra protagonist),
  changed objects/locations, secondary object, missing slots, determinism/immutability/named streams,
  fragment/clause/framed fallback, unknown family/missing scene, negation, real placeholder substitution,
  and public builder policy with banned garnish input.
- Seven future behavior tests exercise existing ContentPlan APIs; none depends on an absent v2 function.
  Six assert required sentence structures; one asserts additive builder debug. They currently fail as intended.
- Read-only independent review: PASS after replacing the fragment metadata label with actual surface `fragment`
  and removing an overrestrictive scene-before-object requirement. Scene insertion can occur within/after action.

Temporary expected-failure debt (must remove marker when implementing):

| Owner task | Pending test suffix | Current assertion failure |
|---|---|---|
| N2.4 | subject_action_scene_does_not_separate_subject_from_finite_predicate | finite predicate disconnected by comma |
| N2.4 | subject_action_scene_tail_has_two_sentences | 1 sentence instead of2 |
| N2.4 | scene_lead_precedes_subject_and_action | scene follows subject |
| N2.5 | gerund_action_lead_attaches_to_the_existing_subject | subject leads instead of gerund |
| N2.5 | subject_scene_action_places_scene_before_action | scene follows action |
| N2.5 | scene_insert_keeps_a_connected_predicate_and_single_scene | finite predicate disconnected by comma |
| N2.6 | builder_decision_exposes_rendering_and_fallback_metadata | missing realizer_version/debug fields |

Unittest.expectedFailure is deliberate test-first status, not a skip or an implementation pass.
Unexpected success must fail the suite until its marker is removed. After changes affecting pending tests,
run their bodies without unittest's expected-failure handling to distinguish intended assertions from errors.
Fixture semantics are bounded lexical checks, not a general NLP proof. Appropriate eligibility fixtures and
real workflow gates must establish family distinctions and broader preservation in N2.3–N2.7.

Verification:
- `python -m unittest assets.test_prompt_realizer_v2`: 19 total, 12 pass +7 expected failures.
- `python assets/results/diversity_refactor/n21-contracts/verify_pending_contracts.py`: PASS;
  all7 direct method invocations fail with the intended AssertionError reason, no import/type errors.
- `python -m unittest assets.test_prompt_realizer_v2 assets.test_action_frame_realizer assets.test_prompt_renderer assets.test_prompt_snapshots assets.test_solo_safety assets.test_semantic_policy assets.test_workflow_samples assets.test_context_nodes assets.test_v150_freeze_contract assets.test_determinism`:
  59 total, 52 pass +7 expected failures, 0 errors/unexpected successes.
- `python -m py_compile assets/test_prompt_realizer_v2.py`; staged/unstaged diff/new-file whitespace: PASS.
- Snapshot ZIP, all1120 copied-file hashes and all120 protected variation files verified unchanged.
- Current source-manifest delta from sealed baseline is exactly the new test file. No runtime/public-node/data changes.
- Separate lint/typecheck tooling remains unavailable. No full release/GUI/blind review for this test-only task.

Decision: N2.1 Acceptance satisfied; next N2.2 adds validated syntax-family metadata. Test-first debt remains explicit,
so this task does not claim seven pending requirements are working. N2.8 activation and final promotion gates remain required.
Evidence:
- `assets/results/diversity_refactor/n21-contracts/receipt.json`; SHA256 `6dfe7516418725d31ff3741a171f862de5f14c9fd787b7f43a5c9a419dac131a`.
- Baseline archive: `assets/results/diversity_refactor/v150-before-n2/baseline-source.zip`; SHA256 `45c3348563e287f5bbc2cdabcd6dbf82184c1f30cf4f7ca5849f49ada5996eec`.
- Snapshot content hash: `34f92cc23d738f564568b04a48e1019d6ee54529e1487bdfc22d8bf9a6b456af`; manifest/ZIP receipt alongside archive.
- Pending assertion receipt SHA256: `99d920248994cf57e939c1711925b52af4b2dd185ecfe283a0c8db1d659ba0bc`.
- Regression log SHA256: `09e694e63f3e505ccd6c107fd33cb88cb8ec32739c6503a5d46b72534a7081f5`.

### 2026-09-06 — N2.2 — Syntax-family metadata (start / plan)

State: IN_PROGRESS
Owned files: `vocab/data/natural_language_realizer_v2.json`, `vocab/syntax_families.py`,
`assets/test_syntax_family_catalog.py`, `asset_validator.py`, tasks/progress and status pointers.
Plan before edits: add malformed-schema/mutation tests first; define six structural candidate families;
validate shape, enums, positive safety prerequisites and direct baseline fallbacks; connect asset validation;
run data/regression/prompt-parity checks and independent review.
Standalone config avoids silently ignored fields in the active text-template catalog. It adds no semantic text
vocabulary and is not read by active selection/rendering. Baseline is unconditional; other families require
positive safety facts evaluated against the rendered action surface in N2.3.
No new dependencies or changes to protected expansion data, public nodes, or active syntax declarations.

### 2026-09-06 — N2.2 — Six syntax-family definitions validated

State: PROMOTED (metadata task only; runtime v2 remains inactive)
Baseline/Candidate HEAD: `1b159bf66fa5202d27908ed63fe7d5fe4cb590f3`; uncommitted metadata/validator/test/docs changes.
Owned files: `vocab/data/natural_language_realizer_v2.json`, `vocab/syntax_families.py`,
`assets/test_syntax_family_catalog.py`, `asset_validator.py`; tasks/progress and CURRENT_STATUS/REPO_STRUCTURE pointers.

Changes:
- Six required candidate family definitions under syntax-family-catalog/v1. No optional family/vocabulary bulk list.
- Metadata: key, roles, ContentPlan required_slots, allowed/avoided rendered action surfaces, positive/negative
  safety facts, nominal sentence_count/clause_order, direct fallback_family and finite positive weight.
- Baseline has wildcard roles/surfaces and no constraints, with null terminal fallback. Conditional families fall
  directly to it; unknown/missing rendered surfaces cannot pass restrictive family allowlists.
- Schema validator rejects malformed shape, missing/duplicate/unknown fields/keys/enums, contradictory conditions,
  unsafe relaxed prerequisites, wrong layouts, bad fallback targets and nonfinite/bool/nonpositive weights.
- Reusable pure validation lives beside vocabulary; asset_validator.validate_assets checks the new config.
  Current template_catalog.json and active selector/renderer/audit active-family declarations are unchanged.

N2.3 handoff semantics:
- For each nonbaseline family, required safety facts must be exactly True and forbidden facts explicitly False.
  Missing/None is unknown and excludes the family; absence of a known hazard is not proof of safety.
- Interpret ContentPlan slots by their actual names (adjunct is the full action slot). Conditions inspect the
  rendered action surface, not input_surface or a gerund main_verb. Positive scene/attachment checks still need implementation.
- sentence_count/clause_order describe the nominal eligible layout. The unconditional baseline may receive
  missing slots and emit fewer clauses/empty text. Scene-insert macro order permits insertion within/after action.
- Optional families require an explicit schema/validation update. Data definitions alone never enlarge active K.

Verification:
- Mutation tests written first; initial import failure established the missing implementation.
- `python -m unittest assets.test_syntax_family_catalog assets.test_asset_validator`: 35 tests OK (14 new +21 existing);
  independent reviewer repeated the same35 tests and approved.
- `python -m unittest assets.test_syntax_family_catalog assets.test_asset_validator assets.test_prompt_realizer_v2 assets.test_action_frame_realizer assets.test_prompt_renderer assets.test_prompt_snapshots assets.test_solo_safety assets.test_semantic_policy assets.test_workflow_samples assets.test_context_nodes assets.test_v150_freeze_contract assets.test_determinism`:
  94 total,87 pass +7 previously declared expected failures, no errors/unexpected successes.
- Direct N2.1 pending-body verification still finds the same7 intended behavior assertions.
- `python tools/validate_prompt_data.py`: ERROR=[] / WARNING=[]; validate_assets():0 issues.
- `python tools/audit_effective_diversity.py --profile smoke --output assets/results/diversity_refactor/n22-metadata/smoke.json`:
  128 records hash, all metrics, reference axis values and audit_config equal the pre-N2 baseline; active K remains2.
- Python compile and staged/unstaged/new-file whitespace checks PASS. Lint/typecheck tooling remains unavailable.
- All120 protected variation files and all1120 sealed snapshot files unchanged. Active template catalog bytes unchanged.
- Source hash changes for new metadata/validation/tests are recorded; old source-bound reference caches are not reused
  as evidence for the new source. No prompt behavior/public-node/dependency changes or full release/GUI/blind review.

Decision: N2.2 Acceptance satisfied. Next N2.3 implements the eligibility engine against this validated metadata.
Seven N2.4–N2.6 expected-failure contracts remain pending; six definitions are not six implemented active renderers.
Evidence:
- `assets/results/diversity_refactor/n22-metadata/receipt.json`; SHA256 `a07178f0ef4eac562a8c1a1d35d612d2387c357c55e1bd8b509c6a49215e17a6`.
- Smoke report SHA256: `d81fb4547159a3996781a365540aeee93022f61d96cdb1996eb46be4419a37f1`.
- Baseline/current records SHA256: `aeab689d817b3f835bf7fd91b491a761f139f3a6a70088db17843da0930893ed`.
- Current source hash: `98aee6edd2f5d89ed44258a959072b680e57e577313d811e1a64b2993fd8cacf`.
- Regression log SHA256: `48d5beb7cd58ed76bffc592095b0cd1054ea1be85d7df574c31338c589cf7fbf`.

### 2026-09-06 — N2.3 — Eligibility engine (start / plan)

State: IN_PROGRESS
Owned files: `pipeline/syntax_family_selector.py`, `assets/test_syntax_family_selector.py`, tasks/progress/status pointers.
Plan before code: failing safety/eligibility fixtures; conservative fact derivation on concrete ContentPlan slots;
validated metadata filtering with baseline always available; deterministic debug/rejection reasons;
focused regression, unchanged current prompt smoke and independent review.
A separate selector keeps grammar/eligibility out of prompt_realizer's planning/normalization responsibilities.
Reuse existing gerund-head constants, ActionFrame, phrase normalization, location resolver, solo/policy checks;
only a small explicitly tested finite-form set. Unknown input must fall back instead of general NLP repair.
No runtime routing/rendering activation or predicate generation in this task; N2.4–N2.6 expected failures stay pending.

### 2026-09-06 — N2.3 — Conservative eligibility engine ready

State: PROMOTED (eligibility task only; active generator routing unchanged)
Baseline/Candidate HEAD: `1b159bf66fa5202d27908ed63fe7d5fe4cb590f3`; uncommitted selector/test/docs changes.
Owned files: `pipeline/syntax_family_selector.py`, `assets/test_syntax_family_selector.py`, tasks/progress,
CURRENT_STATUS/REPO_STRUCTURE status pointers.

API / behavior:
- eligible_syntax_families(plan, action_frame, action_surface, catalog=None, return_debug=False) returns ordered
  candidate keys; baseline first, other eligible keys sorted. Debug returns eligible keys, per-family rejection
  reasons, baseline_only fallback reason and True/False/None safety facts. No random selection is performed.
- Reuses validated six-family metadata, existing ActionFrame/action constants/phrase normalization,
  location aliases and policy/solo checks. Unconditional baseline is a fallback marker, not permission to bypass upstream safety.
- Filter by roles, concrete required slots, actual rendered surface and positive/negative facts before any selection.
  Requires must be True, forbids must be explicitly False; missing/None/nonboolean values cannot authorize a family.
- Bind rendered_clause to plan.adjunct and frame legacy text/verb/object to the actual action. Unknown versions,
  stale/mismatched frames, independent subjects, unparsed appended clauses and unresolved placeholders cannot
  authorize advanced attachment/predicate transformations.

Bounded grammar and later integration constraints:
- Recognized gerund heads reuse existing action-parser constants. Finite forms are checks/reads/holds/waits and
  is + supported gerund; no general conjugation engine. Entire tails must match canonical nominal object names
  (plus transit card/ticket), a known locative alias, one of the four supported adverbs, or validated coordinated segments.
- Subject recognition is intentionally limited to explicit simple girl noun-phrase forms/basic garment tails.
  Rich character descriptions, free-form scenes/objects, other finite verbs and unresolved template plans fall back.
  This is not evidence of corpus-wide six-family eligibility or broad natural-language understanding.
- Do not treat ActionFrame text itself or action semantic regex matches as grammatical proof: semantic patterns
  can classify a verb cue such as sipping as drink. Nominal validation uses independent canonical noun forms.
- Scene lead requires a concrete recognized locative alias; overlap uses word-boundary phrase/alias matching.
  The current renderer builds placeholder plans, so N2.4 integration must supply concrete clauses explicitly,
  not silently hydrate unknown placeholders or infer safety from the original verb label.
- Broader coverage must be added with corresponding positive/negative grammar fixtures before promotion.
  N2.4–N2.6 realization/debug expected-failure contracts and N2.7 quality gates remain outstanding.

Verification / fixes:
- Tests written first: missing module failure. One implementation syntax typo was corrected before functional testing.
- Tests exposed a missing-scene leak into action-lead; all advanced families now require a supported scene anchor.
- Independent review reproduced before/after/during clauses, slash-separated clauses, participial noun subjects
  and subject-suffix predicates that the initial head-only check accepted. Added failing fixtures, then replaced
  arbitrary-tail acceptance with whole-tail positive recognition.
- Further review reproduced arbitrary object text (machines hum) and semantic verb cue (holding sipping)
  bypasses; both are now rejected. No changes to existing semantic vocabulary/patterns were made.
- `python -m unittest assets.test_syntax_family_selector`: 22 tests OK, including separate-process hash-seed
  determinism, catalog order/input immutability, unknown safety facts, stale metadata and positive counterparts.
- Independent final review: PASS for the bounded concrete-plan API; reviewer independently reran22 tests.
- Related suite (selector/catalog/asset validator, realizer contracts, renderers/snapshots, solo/policy,
  workflow/public nodes/freeze/determinism): 116 total,109 pass +7 declared expected failures, no errors.
- Direct pending-contract verification confirms all7 still fail for their intended behavior assertions.
- `python tools/audit_effective_diversity.py --profile smoke --output assets/results/diversity_refactor/n23-eligibility/smoke.json`:
  128 records hash, metrics and audit_config exactly match the pre-N2 baseline; active syntax K remains2.
- Python compile, staged/unstaged/new-file whitespace checks PASS; separate lint/typecheck tooling unavailable.
- All120 protected variation files and all1120 sealed baseline files unchanged. No data/public-node/active rendering
  changes or dependencies; no full release/GUI/blind review for an unconnected selector module.

Decision: N2.3 Acceptance satisfied. Next N2.4 implements the first3 v2 realization families behind the internal
candidate path; no activation or diversity improvement is claimed here.
Evidence:
- `assets/results/diversity_refactor/n23-eligibility/receipt.json`; SHA256 `3662d180507432f40883c2e94f59ebb5f9356c85681265f037fac028e9214cff`.
- Smoke report SHA256: `8a92b7e62b823d5a4ce5ec62b56901b7380838ce0966c4610b9726f10542cdb9`.
- Baseline/current records SHA256: `aeab689d817b3f835bf7fd91b491a761f139f3a6a70088db17843da0930893ed`.
- Current source hash: `b49aa22913e6ae7a3440f41519b6488311952fd16664a47e3c5a8bdc0daebb16`.
- Regression log SHA256: `75e764fe62680df6b769968938c9310648fd3bdb9617cd958ddb908e721b5e6a`.

### 2026-09-06 — N2.4 — First three v2 realizations (start / plan)

State: IN_PROGRESS
Owned files: `pipeline/prompt_realizer.py`, `assets/test_prompt_realizer_v2.py`, tasks/progress/status pointers.
Plan before implementation:
1. Unmask the three N2.4 syntax assertions and add exact natural-text/metadata snapshots plus unsafe fallback,
   punctuation/capitalization/secondary-action tests using original frames and concrete plans.
2. Extend internal realize_content_plan with optional frame/surface/debug arguments. Keep legacy family dispatch
   unchanged; explicit v2 requests use eligible + implemented families only, with affirmative frame safety.
3. Preserve whole clauses, add only the gerund copula and safe scene sentence/ordering; retain v1 fallback.
   Unimplemented/unknown requests cannot masquerade as the selected family. No active node/default routing changes.
4. Verify remaining expected-failure debt, regressions, current-workflow smoke equality and independent review.
No general verb conjugator, vocabulary expansion, public I/O change or baseline snapshot modification.

### 2026-09-06 — N2.4 — First three candidate realizations implemented

State: PROMOTED (implementation task only; no default activation)
Baseline/Candidate HEAD: `1b159bf66fa5202d27908ed63fe7d5fe4cb590f3`; uncommitted realizer/test/docs changes.
Owned files: `pipeline/prompt_realizer.py`, `assets/test_prompt_realizer_v2.py`, tasks/progress;
CURRENT_STATUS/REPO_STRUCTURE/README status pointers.

Changes:
- Implemented subject_action_scene, subject_action__scene_tail and scene_lead_subject_action on the internal
  candidate path. Existing plan-only calls and legacy family labels continue through the original v1 behavior.
- realize_content_plan now optionally accepts action_frame, action_surface and return_debug. A supplied frame
  can use the surface recorded in plan.lexical_choice, but all surface/frame evidence is validated.
- Only structurally eligible AND implemented families can be selected. Positive frame_predicate_safe and
  non-overlapping scene evidence are required even for v2 baseline grammar. Unsafe input uses the v1 fallback.
- Preserve whole action/scene clauses and secondary objects; use finite predicates unchanged except their initial
  case, or add only is before a supported gerund. Scene-tail adds the safe 'The scene is set' connective.
- Normalize boundary punctuation, preserve interior capitalization, and retain the raw realizer's final period
  after shared punctuation cleanup. No new conjugation framework, semantic vocabulary or policy weakening.
- Debug identifies actual selected family/version, structural versus implemented eligibility, fallback reason
  and actual clause order. Builder-wide debug integration remains N2.6; current public outputs/default routing unchanged.

Test-first changes and verification:
- Removed the three N2.4 expectedFailure markers and moved them into the initial-syntax test class.
  Expanded tests pass original frames/surfaces into the opt-in candidate path while preserving their fact assertions.
- Added exact natural-text snapshots for all three families, copula/secondary-action preservation, initial-case
  and punctuation checks, safe baseline/v1 fallbacks, malformed clause-order rejection and original-call compatibility.
- The pending N2.5 scene-insert test now asserts actual selected-family metadata so a baseline fallback cannot
  accidentally satisfy it. This strengthens the unresolved requirement instead of falsely claiming implementation.
- Initial new-argument TypeErrors disappeared after API implementation; snapshot tests exposed shared sanitizer
  trimming final periods, resolved by retaining the lower-level v1 realizer's sentence-ending contract.
- `python -m unittest assets.test_prompt_realizer_v2`:28 total,24 pass +4 expected failures.
- Related realizer/eligibility/catalog/asset/render/snapshot/safety/policy/workflow/node/freeze/determinism suite:
  125 total,121 pass +4 expected failures; no errors/unexpected successes.
- `python assets/results/diversity_refactor/n24-realization/verify_pending_contracts.py` confirms remaining4
  bodies fail at intended N2.5/N2.6 assertions. The historical N2.1 seven-failure checker is no longer current.
- Independent implementation review PASS; reviewer ran27 tests (23 pass +4 expected failures), followed by
  the final surface-default/fallback regression and clarified docstring (final28-test suite above).
- `python tools/audit_effective_diversity.py --profile smoke --output assets/results/diversity_refactor/n24-realization/smoke.json`:
  128 current-workflow record bytes, metrics and audit_config equal the pre-N2 baseline; active syntax K remains2.
- Python compile, staged/unstaged/new-file whitespace PASS. Separate lint/typecheck tooling unavailable.
- All120 protected variation files and all1120 sealed baseline files unchanged. No public-node/data/dependency changes.

Candidate examples (same fixture facts):

```text
A calm solo girl in a navy coat checks a transit card at the station platform.
A calm solo girl in a navy coat checks a transit card. The scene is set at the station platform.
At the station platform, a calm solo girl in a navy coat checks a transit card.
```

Decision: N2.4 Acceptance satisfied. Next N2.5 implements action lead, subject-scene-action and scene insertion.
Four declared expected failures remain: three N2.5 syntax contracts plus the N2.6 Builder debug contract.
Bounded eligibility still excludes richer unsupported grammar; there is no corpus-wide six-family/quality/adoption
claim. Final renderer integration must supply concrete clauses and pass A1.6/N2.7 quality gates before N2.8 activation.
Evidence:
- `assets/results/diversity_refactor/n24-realization/receipt.json`; SHA256 `6e921e132f1f04f5e5a2d7483a5ee026f2079cc2c7d772fe15b3417f17257209`.
- Candidate example artifact SHA256: `eb79354281261bf1322c2d0ae427bb2f2d475ea514ef242313f2cc0b5340f1a3`.
- Baseline/current records SHA256: `aeab689d817b3f835bf7fd91b491a761f139f3a6a70088db17843da0930893ed`.
- Current source hash: `5ab41b5fa30366eb4186d7ea612db0c31c32e007466739cb101f674707a332b1`.
- Pending assertion receipt SHA256: `1709e7245a9815d158ed1b60403da9aac672d85a54d865cf4a8760b84f95f782`.
- Regression log SHA256: `2fe0ffb7f3a4eae13e52f87b46764b77380a2f19b579d96c45db9fa652d83e98`.

### 2026-09-06 — N2.5 — Remaining three realizations (start / plan)

State: IN_PROGRESS
Owned files: `pipeline/prompt_realizer.py`, `assets/test_prompt_realizer_v2.py`, tasks/progress/status pointers.
Plan: unmask three syntax contracts; add six-family same-facts snapshots/selection checks and unsafe lead,
whole-predicate/copula regressions; implement branches after existing eligibility/safety gates; verify prior
v1 workflow equality and independent review. No new morphology/semantic vocabulary or active routing changes.
Scene insertion uses a comma-separated post-action adjunct, permitted by spec7.3, keeping verb/object connected
without adding parentheses that could carry downstream prompt-weighting semantics. No optional7–8 families.

### 2026-09-06 — N2.5 — Required six internal realizations complete

State: PROMOTED (implementation task only; no active-default adoption)
Baseline/Candidate HEAD: `1b159bf66fa5202d27908ed63fe7d5fe4cb590f3`; uncommitted realizer/test/docs changes.
Owned files: `pipeline/prompt_realizer.py`, `assets/test_prompt_realizer_v2.py`, tasks/progress;
CURRENT_STATUS/REPO_STRUCTURE status pointers.

Changes:
- Added gerund action lead, subject-scene-action and comma-separated post-action scene insertion after
  the existing eligibility/positive frame/non-overlap gates. Actual clause-order debug matches each construction.
- Action lead preserves the gerund action verbatim and uses the existing protagonist as main-clause subject;
  finite/copular/framed/fragment inputs fall back. Other branches preserve the whole finite/copular predicate.
- Scene insertion keeps verb/object connected and adds no parentheses, new action, object or lexical dictionary.
- Implemented-family cap now contains all six required names; optional7–8 remain unimplemented.
  Existing v1 plan-only calls, legacy family labels, public nodes and active selection remain unchanged.

Test-first and verification:
- Unmasked all three N2.5 expectedFailure contracts. Their initial failures showed unimplemented selected keys,
  wrong clause order and missing gerund lead before adding the render branches.
- Added exact same-gerund six-family snapshots: six distinct texts, all selected-family identities, correct clause
  orders, preserved fixture facts/policy/solo safety and six eligible candidates under supported inputs.
- Tests cover finite/is-checking/fragment/framed action-lead rejection, whole coordinated predicates/secondary objects,
  scene overlap and missing/unsafe inputs. No duplicate copula or lost input clause.
- Dedicated realizer suite:32 total,31 pass +1 expected failure. Related suite:129 total,128 pass +1 expected failure,
  no errors/unexpected successes. The only remaining pending contract is N2.6 Builder decision/debug.
- `python assets/results/diversity_refactor/n25-realization/verify_pending_contract.py` confirms that remaining
  body fails for missing realizer_version (AssertionError, not an import/type error).
- Independent static implementation/test review PASS; test execution was performed by the parent agent.
- `python tools/audit_effective_diversity.py --profile smoke --output assets/results/diversity_refactor/n25-realization/smoke.json`:
  128 current-workflow record bytes, metrics and audit_config equal the pre-N2 baseline; active K remains2.
- Python compile, staged/unstaged/new-file whitespace PASS. Separate lint/typecheck tooling remains unavailable.
- All120 protected variation files/all1120 sealed baseline files unchanged; eligibility implementation unchanged.
  No data/public-I/O/dependency changes or full release/GUI/blind review for the inactive candidate renderer.

New candidate example forms (same gerund fixture):

```text
Checking a transit card, a calm solo girl in a navy coat is at the station platform.
A calm solo girl in a navy coat, at the station platform, is checking a transit card.
A calm solo girl in a navy coat is checking a transit card, at the station platform.
```

Decision: N2.5 Acceptance satisfied. Next N2.6 exposes consistent Builder decision/debug metadata.
Six distinct fixture texts are not a claim of six-family corpus coverage or improved semantic diversity;
scene-insert intentionally differs through supplementary punctuation. Bounded grammar and fallback limitations
remain, and N2.7/A1.6 quality evaluation is required before N2.8 activation.
Evidence:
- `assets/results/diversity_refactor/n25-realization/receipt.json`; SHA256 `20e30fef17ef8bc62a72183abe1e079095798eb3d572f3116995273ff2dd79e8`.
- Six-family example artifact SHA256: `90a67c3152e9c50a9dc9e51d21688b09985921028450a01e8c46463febeb9c9d`.
- Baseline/current records SHA256: `aeab689d817b3f835bf7fd91b491a761f139f3a6a70088db17843da0930893ed`.
- Current source hash: `9767ed77a4610ef3fcd6c3cda3079cd17ed27f06ea0c342cefb1f36d34990201`.
- Pending assertion receipt SHA256: `b08409f96336f725b13508e8473f33e214ce1122ec8198e45dcc5565e2e976bb`.
- Regression log SHA256: `0d421e6a1069dc290723adb6562a7e5850faf316ecc9931c8d962c2a9c7085e4`.

### 2026-09-06 — N2.6 — Builder decision/debug (start / plan)

State: IN_PROGRESS
Owned files: `prompt_renderer.py`, `pipeline/prompt_realizer.py`, `assets/test_prompt_realizer_v2.py`, tasks/progress/status.
Plan before edits: unmask final Builder contract; test actual metadata propagation, both current v1 families,
legacy-template null metadata, JSON roundtrip, audit extraction and prompt/debug parity; then pass rendering
metadata through the builder. No prose-based reconstruction, v2 activation or public node I/O change.
Active v1 composed eligibility lists both actually selectable families; arbitrary legacy templates use null/[]
and an explicit no-structural-metadata reason. Existing context/debug schema remains extensible and unchanged.

### 2026-09-06 — N2.6 — Actual Builder rendering metadata ready

State: PROMOTED (debug/compatibility task only; v2 default not activated)
Baseline/Candidate HEAD: `1b159bf66fa5202d27908ed63fe7d5fe4cb590f3`; uncommitted renderer/debug/test/docs changes.
Owned files: `prompt_renderer.py`, `pipeline/prompt_realizer.py`, `assets/test_prompt_realizer_v2.py`,
`assets/test_action_frame_realizer.py` (existing mock adaptation), tasks/progress and status pointers.

Changes:
- Composition-mode Builder captures and passes through actual realize_content_plan debug:
  realizer_version, syntax_family, eligible_syntax_families, syntax_fallback_reason and clause_order.
  Existing template/intro/body/end keys and ContentPlan remain intact; no prose-based family reconstruction.
- Current v1 debug truthfully lists both selectable composed families, in stable order, rather than only the selected key.
- composition_mode=false emits v1/null/[]/legacy_template_no_structural_metadata/[] for arbitrary templates;
  sentence punctuation is not treated as structural evidence. No context_json/schema/public-I/O change.
- Audit already supports the authoritative Builder field, so no signature/audit inference code was added.
  Candidate rendering/default routing are unchanged; current version stays v1 until evaluated adoption.

Test-first / verification:
- Unmasked the final N2.6 expectedFailure and added5 metadata tests for16-seed replay/both v1 families,
  legacy null structure, JSON roundtrip, debug/plain prompt parity and authoritative audit extraction.
- New tests initially reproduced missing Builder fields. After implementation, a broader existing mock returned
  the old string shape and caused one unpack error. Updated that mock to preserve actual debug and strengthened
  assertions that both its marker template and metadata reach Builder; initial failure log retained.
- Dedicated realizer tests:37 passed; related tests:188 passed, no expected failures/errors/skips.
- Independent review PASS, with61 realizer/signature and7 renderer/snapshot tests independently run;
  the existing-mock adaptation was separately reviewed. Parent reran the full related188 after that change.
- All N2.1–N2.6 expected-failure markers are resolved; historical pending-failure checkers are not current checks.
- `python tools/verify_full_flow.py`:PASS. Python compile and staged/unstaged/new-file whitespace:PASS.
  Separate lint/typecheck tooling remains unavailable.
- Current smoke and cached-reference repeat are byte-identical. All128 syntax values are read from
  builder.syntax_family; raw prompt/record hashes, metric values and active K=2 remain equal to pre-N2 baseline.
  Diagnostic extraction_sources intentionally moves from ContentPlan fallback to the direct Builder field.
- Tests-only mock correction changed source hash; source-bound smoke/reference artifacts were regenerated afterward.
- All120 protected variation files and all1120 sealed baseline files unchanged. No data/public-node/dependency changes.

Reproduction:

```bash
python -m unittest assets.test_prompt_realizer_v2 assets.test_effective_diversity_signatures assets.test_effective_diversity_audit assets.test_context_codec assets.test_context_state_adapter assets.test_syntax_family_selector assets.test_syntax_family_catalog assets.test_asset_validator assets.test_action_frame_realizer assets.test_prompt_renderer assets.test_prompt_snapshots assets.test_solo_safety assets.test_semantic_policy assets.test_workflow_samples assets.test_context_nodes assets.test_v150_freeze_contract assets.test_determinism
python tools/audit_effective_diversity.py --profile smoke --output assets/results/diversity_refactor/n26-debug/smoke-first.json --write-reference assets/results/diversity_refactor/n26-debug/reference.json
python tools/audit_effective_diversity.py --profile smoke --reference assets/results/diversity_refactor/n26-debug/reference.json --output assets/results/diversity_refactor/n26-debug/smoke-repeat.json
```

Decision: N2.6 Acceptance satisfied. Next N2.7 evaluates an isolated v2 candidate against A1.5/A1.6 and
current prompt-quality contracts before any N2.8 activation. Current Builder still uses plan-only v1 rendering;
connecting the explicit v2 candidate path to concrete workflow clauses remains part of candidate preparation.
On candidate fallback, actual ContentPlan family/order and top-level decision must agree; the existing audit
rejects disagreement and must not be weakened. Bounded grammar/corpus coverage limitations remain unmeasured.
Evidence:
- `assets/results/diversity_refactor/n26-debug/receipt.json`; SHA256 `afa73cd728d87ae6ea924b2a9e4fc22064707ec819c6a358c4ece74ae52678f0`.
- Smoke/repeat report SHA256: `da7aaab8b4b26831881e1961a829c7412af020d5eb5a95f890fd29a9b0cacbc9`.
- Baseline/current records SHA256: `aeab689d817b3f835bf7fd91b491a761f139f3a6a70088db17843da0930893ed`.
- Current source hash: `0fef67db1f5b8f23021c1b9a652300db6959ee75453c93d81da0f5d5d287e8e4`.
- Regression log SHA256: `24b687c84695ac1133e707d60c275d263dbf7bda49f1de96e5e767e8d9f6a231`.
- Actual v1/legacy metadata examples: `assets/results/diversity_refactor/n26-debug/builder-debug-examples.json`.

### 2026-09-06 — N2.7 — Isolated candidate evaluation (start / plan)

State: IN_PROGRESS
Owned scope: ignored `assets/results/diversity_refactor/n27-candidate-01/` candidate source/tests/evidence;
active repository changes limited to task/progress/status documentation.
Plan: clone current source; connect v2 only in clone using exact concrete template substitutions and stable named-seed
selection; preserve exact v1 fallback/template RNG/staging; validate bridge integrity then freeze candidate.
Run focused realizer/snapshot/full-flow gates, Effective Diversity2048/8192-reference and fixed64+16 quality comparison.
Keep baseline observations from sealed pre-N2 source, verify per-seed semantic/upstream equivalence and source hashes.
No policy/threshold/eligibility loosening, baseline edits, active application or promotion-only blind/confirmation
runs for a candidate that fails automatic targets. Record measured ELIGIBLE/REJECTED/BLOCKED outcome explicitly.

### 2026-09-06 — N2.7 — Candidate-01 evaluation: REJECTED

State: REJECTED (evaluation task complete; N2.8 activation blocked)
Candidate ID: n27-candidate-01.
Active source was not modified or applied. All candidate source/evaluation artifacts live under
`assets/results/diversity_refactor/n27-candidate-01/`; document/status updates are the only active-tree edits.

Candidate preparation / integrity:
- Copied current N2.6 source using the existing filtered copier; retained the sealed pre-N2 V150 baseline.
- Four candidate-only source deltas: prompt_renderer.py, tools/audit_effective_diversity.py,
  pipeline/v2_candidate_bridge.py, assets/test_n27_candidate_bridge.py.
- Bridge resolves exact selected template parts in the existing replacement order, preserves template RNG/staging,
  and uses a separate deterministic named stream inside eligible v2 families. It never loosens grammar or data.
- On ineligibility, exact original v1 template output is retained (including the preselected two-sentence form).
  Version remains v1; old single/two-sentence structure names map to the two corresponding new baseline shapes,
  with fallback_origin_syntax_family recorded. Six declared keys do not mean six observed/applied v2 families.
- Candidate source frozen before formal measurement; source hashes verified before/after. Baseline/current extractor,
  normalizer, workflow, runner config and locked A1.6 thresholds unchanged. Only active family declaration differs in audit_config.

Verification performed:
- 64 focused bridge/semantic/realizer/selector/renderer/snapshot tests PASS; candidate full flow PASS.
  Focused suite is explicitly scoped; active-v1-only metadata-name assertions are not a candidate activation gate.
- Candidate Effective Diversity gate:2048 measured records against its own8192 reference; canonical artifacts/hash validation PASS.
- Independent source runs produced2048 paired observations: core, frame, full upstream context, raw prompt and cleaned
  prompt hashes all match per seed (0 mismatches). Candidate actual v2 application: **0/2048**, v1 fallback: **2048/2048**.
- Unsupported subject, unsupported scene anchor and unsupported/mismatched rendered action surface each occurred in
  2048/2048 candidate eligibility traces. The bounded fixture grammar does not handle the actual rich composed clauses.
- Existing fixed64 control (0–63) +16 exploration cohort was declared before candidate bridge preparation. Both source
  runs generated/replayed/analyzed80 records; record files byte-identical, all numeric analyzer metrics equal.
- Rendering automatic comparison on control64: syntax-entropy target1.083012→1.083012, improvement0, verdict reject;
  hard gates and comparison guards pass. Separate strict zero-regression check also passes, policy issues0.
- Evaluation policy retains all base numeric settings and uses the accepted v7 review section verbatim (validated),
  with originals/effective-policy hashes retained. This is evaluation orchestration, not a new policy or completed blind review.
- Independent final evidence review PASS: candidate manifest/allowlist, report/reference/source/config hashes,
  fixed cohort, paired observations and REJECTED rationale independently confirmed.

Locked diversity result:

| Metric | Baseline | Candidate-01 | Required / verdict |
|---|---:|---:|---|
| observed required syntax families @2048 | 2 v1 | 2 retained v1 shapes; 0 actual v2 applied | six required; FAIL |
| normalized entropy @128 | 0.743271 (K=2) | 0.287536 (K=6) | >=0.743271; FAIL |
| normalized entropy @512 | 0.814359 (K=2) | 0.315037 (K=6) | >=0.814359; FAIL |
| normalized entropy @2048 | 0.814359 (K=2) | 0.315037 (K=6) | >=0.855077; FAIL |
| raw entropy @2048 | 0.814359 | 0.814359 | strict improvement; FAIL |
| same-syntax max run @2048 | 16 | 16 | <=16 Realizer guard; PASS |
| core / frame unique @2048 | 1963 /2042 | 1963 /2042 | non-regression; PASS |
| exact / normalized duplicate rates | 0 /0 | 0 /0 | zero; PASS |

The normalized entropy decrease reflects unused declared families, not worse prompt text: raw outputs and raw entropy
are unchanged. Syntax coverage1.0 means2/2 observed reference categories, not coverage of all six candidate branches.
Generic prompt-quality analyzer entropy1.083012 uses a different metric definition from Effective Diversity entropy;
these values are not interchangeable. No new human naturalness/image-suitability scores are claimed.

Not performed / limitations:
- No active apply, blind review,3×256 fresh confirmations, frontend/browser activation checks or release@8192 audit.
  Candidate already fails automatic targets; those promotion-only checks are not recorded as passing.
- Candidate bridge is scoped to standalone evaluation imports; ComfyUI package-import activation compatibility remains unvalidated.
- Stored observations bind full per-seed semantic/input/output hashes; no claim that the coarse object classifier's
  existing missingness is repaired. Existing limitations and A1.6 guard thresholds remain unchanged.

Decision / next work:
- **REJECTED**. Do not activate N2.8. Add N2.7-R1 to repair concrete workflow/template integration and positive
  safety evidence using actual failing clauses, while preserving all facts, existing negative fixtures and thresholds.
- Do not shorten/drop the rich subject/scene facts merely to fit the toy grammar, mark missing safety facts false,
  or count unused family declarations as successful realization. Freeze a new candidate and rerun the same gates.
- This evaluation is complete; the overall refactor is not complete or promoted.

Evidence:
- `assets/results/diversity_refactor/n27-candidate-01/verdict.json`; SHA256 `b774c549116876a8ad644291d20bfb13dd8712762f48a08247a967f7c5f15a2b`.
- Candidate gate SHA256: `aea25bf99359f40831cc2556e6e1b2dbc3171a6c5fd20965b563efdb53e4aa46`.
- Candidate reference file SHA256: `5221c5a4257e23aa507037b8e69f3467367ff2da0ca9133d5468da787bdb0e1e`.
- Candidate source/config hashes: `e15265f3e666be77edb352cb6ce80101997a12d452cde650048e5ae1170f0136` / `05f8d34938ef99842791f630ec151bf30bf110525596717bf7ad0447f8bcc993`.
- quality-comparison.json, strict-quality-guards.json, semantic-pair-comparison.json, observation receipts and source manifests are bound in verdict.json.

### 2026-09-06 — N2.7-R1 — Real-workflow repair (start)

State: IN_PROGRESS
Scope: isolated candidate-02 repair/tests/evaluation plus durable active-tree documentation;
no active generation change before an eligible gate.
Intake: inspect exact rejected template components, lock bounded provenance-based repair plan and regression
fixtures before editing candidate code; retain arbitrary-text negative tests, all facts and A1.6 thresholds.
Do not use template keys, caller safety booleans or catalog membership alone as grammar proof.

### 2026-09-06 — N2.7-R1 — Bounded repair complete; candidate-02 REJECTED

State: REJECTED (repair/evaluation task complete; N2.8 remains blocked).
Next actionable task: N2.7-R2, reusable structural coverage beyond the direct-template lane.

Changes and simplification:
- All implementation remains in `assets/results/diversity_refactor/n27-candidate-02/candidate-root/`.
  Active generation, sealed baseline and frozen candidate-01 source are unchanged.
- Six source deltas relative to candidate-01: pipeline/v2_direct_provenance.py,
  pipeline/v2_candidate_bridge.py, pipeline/syntax_family_selector.py, pipeline/prompt_realizer.py,
  assets/test_n27_direct_provenance.py and assets/fixtures/n27_r1_direct_cases.json.
- Replaced the unsupported rich-clause boundary with a bounded direct-template constructor path:
  exact template text, slot substitutions, frame and complete rendered surface are checked together.
  Reviewed components generalize profile/clothing/scene/action combinations; seed IDs are never eligibility inputs.
- Adds only articles and grammatical links while retaining source fact words. Unknown components, changed bindings
  and arbitrary safety flags preserve exact v1 output. Unproved attachment facts remain None.
- Rich scene/mood clauses authorize only the two-sentence family. Other orders require their own positive evidence;
  declaring six available families does not make this limited path support or observe all six.

Verification:
- Real seeds9/40/51 failed the initial new tests before implementation; revised tests cover replay, word preservation,
  reusable constructor combinations, self-consistent unknown tails, forged proof, template/frame/surface mismatches.
- 111 tests +304 subtests PASS, including vocabulary lint; asset validation0 issues, five changed Python files parse,
  full flow PASS. One active-v1-only metadata-name assertion is explicitly deselected: it fails identically in
  candidate-01; bridge tests instead verify actual version/family/order. No type checker is configured/installed.
- Independent bounded code review PASS after correcting unknown safety facts and temporal determiners.
- Candidate frozen before formal measurement. Own8192 reference +2048 gate completed and canonical hashes validated.
- Fresh sealed-baseline and candidate runs:2048 paired core/frame/upstream context comparisons all match.
  Actual v2 applications **3/2048**, exactly seeds9/40/51; raw/cleaned prompts change only at those seeds.
  Remaining2045 prompts preserve v1. Observed structural counts: subject_action_scene1529,
  subject_action__scene_tail519; the other four declared families each have0 occurrences.
- Same fixed64 control +16 exploration cohort. Control64 generic quality syntax entropy1.083012→1.150187
  (+6.202609%), automatic target PASS, hard gates PASS. Strict V150 zero-regression checks PASS, policy issues0.
  All80 punctuation anomalies0→0, repeated n-grams1→1, semantic-family repetitions6→6;
  context p95/max unchanged. Word-length p50/p95107/129.05→107.5/130; grammatical insertions are reported, not hidden.
- All120 protected files, all1120 sealed snapshot files, baseline ZIP, active source and candidate source hashes match.
  Spec/section7, numeric policy, workflow, audit formulas/extraction/normalization unchanged. Candidate audit config
  retains the same permitted six-family declaration as candidate-01; other config fields match V150.
- Independent final evidence review PASS. Zero-count syntax bins are excluded from observed-family counts.

Locked Effective Diversity comparison:

| Metric | V150 baseline | Candidate-01 | Candidate-02 | Required / result |
|---|---:|---:|---:|---|
| actual v2 applications @2048 | 0 | 0 | 3 | connection repaired; limited coverage |
| observed structural families @2048 | 2 | 2 | 2 | six required; FAIL |
| normalized entropy @128 | 0.743271 (K2) | 0.287536 (K6) | 0.303896 (K6) | >=0.743271; FAIL |
| normalized entropy @512 | 0.814359 (K2) | 0.315037 (K6) | 0.318545 (K6) | >=0.814359; FAIL |
| normalized entropy @2048 | 0.814359 (K2) | 0.315037 (K6) | 0.315924 (K6) | >=0.855077; FAIL |
| raw entropy @2048 | 0.814359 | 0.814359 | 0.816651 | strict improvement; PASS |
| dominant family share @2048 | 0.748047 | 0.748047 | 0.746582 | <=0.748047; PASS |
| maximum syntax run @128/512/2048 | 11/11/16 | 11/11/16 | 11/11/16 | non-regression; PASS |
| core/frame unique @2048 | 1963/2042 | 1963/2042 | 1963/2042 | preservation; PASS |
| exact/normalized duplicates | 0/0 | 0/0 | 0/0 | zero; PASS |

Decision / limitations:
- **REJECTED** on exactly four criteria: three normalized-entropy prefixes and six observed families.
  The generic quality analyzer's entropy is a different metric and does not override these failures.
- No active apply, new blind/human ratings, fresh3×256 confirmations, frontend/browser adoption checks or release8192
  measurement. Automatic rejection precedes those promotion-only stages. Standalone bridge package-import adoption
  remains unvalidated. Existing rich wording is retained; broad English/naturalness improvement is not claimed.
- The finite reviewed components support only3 measured seeds and one v2 order; simply adding more seed-specific
  phrases is not the next design. N2.7-R2 should extend reusable constructor/template proof without relaxing gates.

Evidence root: `assets/results/diversity_refactor/n27-candidate-02/`.
- verdict.json SHA256: `39d2313749e7cb3e56b627bda4628d29e927dfbc052c21249fedfbc98cbdd6cb`.
- Gate SHA256: `88d3703b9f71f5e112006dafe31d60f20837d07ad41e6e87a08d09b3ba665736`.
- Reference SHA256: `05cda6d449a8415070185b5fedf7315c5d2e54b1a5455dd823b9bc4e745cebf8`.
- Source tree: `e128d20339c3927befb2ff4f577407c3335c07a6a76cc53d71db876c78c1235a`.
- Source/config: `0086ef406118e5d7b0178790c2196ff23d4ca497bf965ecaa4cd4792fd9113a3` /
  `05f8d34938ef99842791f630ec151bf30bf110525596717bf7ad0447f8bcc993`.
- Reproducible evaluation harnesses, paired receipts, strict guards, code/evidence reviews and all examples are hash-bound
  in verdict.json. Repair/evaluation complete; overall refactor remains in progress and unpromoted.

### 2026-09-06 — N2.7-R2 — Scene constituent placement (start / plan)

State: IN_PROGRESS. Isolated candidate03; active generation stays v1.
Read-only intake512: existing subject/clothing/scene constructors accept264/23/3 cases;
all raw components validate only seeds9/40/51, even if end-template matching is removed.
Extending end-wrapper names alone would not increase measured coverage.

Bounded plan (written before source edits in candidate03/repair-plan.md): preserve the complete
validated locative block as anchor + ordered modifiers + with-absolute mood; prove scene-leading
and parenthetical subject-scene placements with explicit closing commas and fixed sentence counts.
Retain raw evidence revalidation and a constructor-derived supported family set. No new lexical
table entries, unknown-fact coercion, source data changes, extra sentences or threshold changes.
Independent design review excludes late scene insertion after multiple action garnishes, action lead
and undelimited tail pending their own attachment proof. Test new placements RED before implementation.
Freeze after code/test review; rerun own8192-reference/2048 gate and fixed80 comparison against the
unchanged, hash-bound V150 baseline retained from candidate02. Report seed and family coverage separately.

Pre-freeze review correction: bare featuring/adorned modifiers could still attach to the girl after relocation.
The revised constructor explicitly anchors them under a location-relative clause (has/features/is adorned with),
with documented connector/inflection changes and family-specific slot revalidation. R1 two-sentence hashes remain
unchanged; time-first inputs retain only that form. Independent code review43 tests PASS; root122 tests +310 subtests
PASS, full flow/asset/static checks PASS. Candidate source frozen at
`3df6c15e19f9527bc48227f41a7db11c5ff3510298d5b4dfb5e8022d9d05cbaf`.
Measured2048 paired core/frame/upstream differences0; actual v2 seeds9/40/51 use scene-lead/two-sentence/subject-scene.
Four observed structures (1529/517/1/1); fixed80 quality comparison and strict defect metrics pass.
Formal8192 reference/gate publication and terminal receipt follow before closing this task.

### 2026-09-06 — N2.7-R2 — Scene placement repair complete; candidate03 REJECTED

State: REJECTED (bounded repair/evaluation task complete; N2.8 stays blocked).
Next actionable task: N2.7-R3, broader verified clause coverage beyond the three measured seeds.

Changes / simplification:
- Isolated source: `assets/results/diversity_refactor/n27-candidate-03/candidate-root/`.
  Six deltas from candidate02: pipeline/v2_direct_provenance.py, pipeline/v2_candidate_bridge.py,
  pipeline/syntax_family_selector.py, pipeline/prompt_realizer.py, assets/test_n27_direct_provenance.py,
  assets/test_n27_scene_constituents.py. Active generation and prior candidate sources are unchanged.
- Factored scene construction into anchor, ordered modifiers and whole mood. New preposed/parenthetical forms
  use one location-owned relative clause; with/detail becomes has, featuring becomes features, and adorned with
  becomes is adorned with. These documented grammatical changes preserve semantic content and modifier order.
- Removed the hardcoded two-sentence selection in favor of constructor-derived supported families intersected
  with catalog eligibility. Same named seed stream; family-specific scene and ContentPlan are revalidated together.
- Bare modifier movement was rejected during review and corrected before freezing. Word retention alone was not
  accepted as attachment proof. Existing two-sentence output hashes are unchanged for all three real fixtures.
- Time-first scenes remain two-sentence only; unsupported roles/labels/slots/grammar preserve v1. Action lead,
  late scene insertion and undelimited tail remain outside this constructor's proof. Unknown facts stay None.
- No new lexical acceptance: all13 existing lexical/template tables match candidate02. Intake512 shows that
  only3 scene constructors pass (versus264 subject and23 clothing); wrapper-only expansion was not pursued.

Verification / evidence integrity:
- New placement and owner-scope tests failed before their fixes. Final suite:122 tests +310 subtests PASS;
  independent final code review43 tests PASS. Vocabulary lint, full flow, six-file AST and asset validation PASS.
  One known active-v1-only metadata-name test remains explicitly deselected as in prior isolated candidates;
  candidate metadata has direct tests. No type checker configured; no new dependencies.
- Candidate frozen before measurement. Own8192 reference +2048 gate completed; report/reference canonical bytes,
  internal hashes, source/config and observation/quality run bindings verified. Only the allowed six-family
  declaration differs from V150 audit config; metric/extractor/normalizer/threshold code is unchanged.
- Reused the exact source-bound V150 baseline observations and fixed80 run from candidate02, with all8 files
  hash-inventoried in baseline-reuse.json. Candidate03 generation/replay is fresh; baseline reuse is explicit.
- Per-seed2048 core/frame/upstream mismatches0. Actual v2 remains3/2048: seed9 scene_lead_subject_action,
  seed40 subject_action__scene_tail, seed51 subject_scene_action. Remaining2045 prompts retain exact v1.
  Total observed structures4: subject_action_scene1529, two-sentence517, scene-lead1, subject-scene1;
  action-lead and late scene-insert each0. Actual v2 orders3 are distinct from four combined observed labels.
- Fixed64 control +16 exploration quality: control entropy1.083012→1.215391 (+12.223226%), automatic PASS.
  Strict V150 zero-regression PASS, policy issues0; identity/consistency/runtime metrics match on all80.
  Punctuation anomalies0→0, repeated n-grams1→1, semantic-family repetitions6→6. High comma density78→76;
  word length p50/p95107/129.05→107.5/129.05. No new human naturalness/image-suitability result is claimed.
- All120 protected files,1120 sealed baseline files/ZIP, active source, candidate02 source,557 candidate03 source
  entries, spec and locked section7 match their hashes. Independent final evidence review PASS.

Locked Effective Diversity comparison:

| Metric | V150 baseline | Candidate02 | Candidate03 | Required / result |
|---|---:|---:|---:|---|
| actual v2 applications / orders @2048 | 0/0 | 3/1 | 3/3 | structural coverage improved; seed coverage unchanged |
| observed structural families @2048 | 2 | 2 | 4 | six required; FAIL |
| normalized entropy @128 | 0.743271 (K2) | 0.303896 (K6) | 0.341979 (K6) | >=0.743271; FAIL |
| normalized entropy @512 | 0.814359 (K2) | 0.318545 (K6) | 0.331354 (K6) | >=0.814359; FAIL |
| normalized entropy @2048 | 0.814359 (K2) | 0.315924 (K6) | 0.319875 (K6) | >=0.855077; FAIL |
| raw entropy @2048 | 0.814359 | 0.816651 | 0.826865 | strict improvement; PASS |
| dominant family share @2048 | 0.748047 | 0.746582 | 0.746582 | <=0.748047; PASS |
| maximum syntax run @128/512/2048 | 11/11/16 | 11/11/16 | 11/11/16 | non-regression; PASS |
| core/frame unique @2048 | 1963/2042 | 1963/2042 | 1963/2042 | preservation; PASS |
| exact/normalized duplicates | 0/0 | 0/0 | 0/0 | zero; PASS |

Decision / remaining scope:
- **REJECTED**, exactly four failures: normalized entropy at all three prefixes and six observed families.
  Generic analyzer entropy is a separate definition and does not override Effective Diversity adoption criteria.
- N2.7-R2 is complete; no active apply, blind review, fresh3×256 confirmation, frontend/browser adoption check,
  or release8192 measurement. Standalone package-import adoption remains unvalidated. Overall refactor unpromoted.
- The next bottleneck is verified leaf/producer coverage. R3 must handle additional real clauses without adding
  seed/whole-action allowlists, losing selected facts, treating heuristic metadata as grammar, or weakening gates.

Evidence root: `assets/results/diversity_refactor/n27-candidate-03/`.
- verdict.json SHA256: `845cfa312bbb9495ef5b103b1a48e7b7a396e9b87afd58a2ccd6ef63e372ac92`.
- Gate SHA256: `f0f712b41191575b4f3660a82c1f654ee3529de80536e1b518257cb1cfefa950`.
- Reference SHA256: `77f2fead57091c02538cdd99daff690807156741ad98a8610b15c5d130a31f74`.
- Source tree: `3df6c15e19f9527bc48227f41a7db11c5ff3510298d5b4dfb5e8022d9d05cbaf`.
- Source/config: `7ecf76844551802e4fc835f86baa92b3d68b3efbe0e0f7537c028f9327dba161` /
  `05f8d34938ef99842791f630ec151bf30bf110525596717bf7ad0447f8bcc993`.
- Plans, tests, baseline reuse, source/observation receipts, examples, strict guards, review results and evaluation
  harnesses are linked by hashes in verdict.json; all adoption limitations remain explicit.

### 2026-09-06 — N2.7-R3 — Productive leaf grammar (start / plan)

State: IN_PROGRESS. Isolated candidate04; no active apply.
Intake512 found only5 accepted actions and no supported subject/action/garnish/direct intersection
beyond9/40/51. Background/clothing changes alone would not broaden measured application.
Plan written before source edits: finite productive nominal/verb-valency/shared-clause grammar;
new background must match both producer fields and grammatical forms; simple clothing must match
producer choices/palette order and nominal grammar. No new complete action/seed allowlists or upstream fields.
Real41 (garage/bolt/hood) and458 (road/vending-machine/separates) locked RED before implementation.
Existing R1/R2 phrase compatibility, owner-relative clauses, time-first fallback and fixed A1.6 gates remain.

Pre-freeze review strengthens NP ordering/articles, one-core/props/time producer sequence validation,
and an explicit new place-head locative map (road/street→on, other supported place heads→in).
Missing mappings/unknown grammar/independent subjects/scene-place arguments fail closed; artifact and
place noun-head classes are disjoint, preserving positive non-overlap evidence. Plan and review refinements
are in `assets/results/diversity_refactor/n27-candidate-04/repair-plan.md`.

### 2026-09-06 — N2.7-R3 — Productive grammar repair complete; candidate04 REJECTED

State: REJECTED (R3 repair/evaluation complete; N2.8 remains blocked).
Next actionable task: N2.7-R4, productive action and common subordinate-clause coverage.

Changes / simplification:
- All source changes are isolated under `assets/results/diversity_refactor/n27-candidate-04/candidate-root/`.
  Five deltas from candidate03: pipeline/v2_leaf_grammar.py, pipeline/v2_direct_provenance.py,
  pipeline/syntax_family_selector.py, assets/test_n27_productive_grammar.py,
  assets/fixtures/n27_r3_productive_cases.json. Active source and prior candidates remain unchanged.
- Shared finite nominal/valency constructors replace the need to register each new action string. New clauses
  must fully parse, including NP order/articles, spatial artifact arguments, limited subordinate/event/gaze forms.
  Existing complete-phrase compatibility tables are unchanged; new code uses no runtime seed allowlist.
- New scene support requires exact source pack/field membership AND grammar, with producer field counts and
  deduplication. Simple garment support also binds actual choice/palette order. Unknown detail/outerwear forms
  remain rejected. The new head/preposition map emits on-road/on-street and in for supported indoor heads;
  missing mappings fail closed. Raw input proof and actual family-specific ContentPlan remain bound.
- Artifact and place heads are disjoint; new action spatial/gaze arguments cannot repeat the scene place head.
  Unknown facts, location-owned relatives, time-first two-sentence fallback and R1 output hashes are preserved.
- Pre-freeze review corrected unordered nominal tokens, wrong articles/plural forms, duplicate producer fields,
  and the inherited in-road wording. Every correction has negative/positive regression coverage.

Verification / integrity:
- New actual41/458 fixtures failed before implementation. Unseen verb/NP/preposition/garment combinations,
  wrong producer fields/order/counts, independent subjects, unknown tails, place overlaps, frame/surface/slot
  mismatches and old behavior are tested. Final132 tests +350 subtests PASS; independent code review53 PASS.
  Vocabulary lint, full flow, four-file AST and asset validation PASS (0 issues). One known active-v1-only
  metadata-name assertion remains explicitly deselected as before; candidate metadata has direct coverage.
  No configured type checker or new dependency. Real-graph smoke for9/40/41/51/458 passed before source freeze.
- Frozen560-entry candidate source generated its own8192 reference,2048 gate, fixed64+16 quality run and2048
  observations. Baseline8 files are explicitly reused from candidate03 (originally generated in candidate02),
  with unchanged source/cohort/policy and byte hashes. No new baseline measurement is claimed for this reuse.
- Per-seed2048 core/frame/upstream mismatches0. Actual v2 **3→5/2048**, adding41 and458; no earlier case is lost.
 9=scene-lead;40/41/458=two-sentence;51=subject-scene. Remaining2043 outputs preserve exact v1.
  Observed structural counts: single1527, two-sentence519, scene-lead1, subject-scene1, other two families0.
- Fixed80 has4 changed prompts;458 is outside that cohort. Control64 quality entropy1.083012→1.237246
  (+14.241209%), automatic PASS. Strict V150 zero-regression PASS, policy issues0; identity/consistency/runtime
  unchanged on all80. Punctuation0→0, repeated n-grams1→1, semantic-family repetitions6→6;
  high-comma-density78→76, word length p50/p95107/129.05→108/129.05. No new human-quality scores are claimed.
- Canonical/internal report/reference/source/config/observation/quality hashes verified. All120 protected files,
 1120 sealed baseline files/ZIP, active source, candidate03 source, spec and locked section7 are unchanged.
  Audit/extractor/normalizer/policy/threshold code is unchanged; only the already allowed six-family declaration
  differs from V150 config. Independent final evidence review PASS.

Locked Effective Diversity comparison:

| Metric | V150 baseline | Candidate03 | Candidate04 | Required / result |
|---|---:|---:|---:|---|
| actual v2 applications / orders @2048 | 0/0 | 3/3 | 5/3 | broader application demonstrated |
| observed structural families @2048 | 2 | 4 | 4 | six required; FAIL |
| normalized entropy @128 | 0.743271 (K2) | 0.341979 (K6) | 0.347342 (K6) | >=0.743271; FAIL |
| normalized entropy @512 | 0.814359 (K2) | 0.331354 (K6) | 0.333670 (K6) | >=0.814359; FAIL |
| normalized entropy @2048 | 0.814359 (K2) | 0.319875 (K6) | 0.320465 (K6) | >=0.855077; FAIL |
| raw entropy @2048 | 0.814359 | 0.826865 | 0.828389 | strict improvement; PASS |
| dominant family share @2048 | 0.748047 | 0.746582 | 0.745605 | <=0.748047; PASS |
| maximum syntax run @128/512/2048 | 11/11/16 | 11/11/16 | 11/11/16 | non-regression; PASS |
| core/frame unique @2048 | 1963/2042 | 1963/2042 | 1963/2042 | preservation; PASS |
| exact/normalized duplicates | 0/0 | 0/0 | 0/0 | zero; PASS |

Decision / remaining scope:
- **REJECTED** on exactly four criteria: normalized entropy at all three prefixes and six observed families.
  R3 broader-application requirement passes. Generic quality entropy does not substitute for the locked audit.
- Descriptive intake512 diagnosis: subject264, clothing24 (was23), scene6 (was3), primary action8,
  complete action tails26, garnish369, direct templates98. All components together match only9/40/41/51/458
  even when template matching is ignored. These are diagnostics, not new adoption thresholds or broad English proof.
- R4 should extend recurring action/subordinate constructions using the shared grammar and measured gaps,
  preserving actor/ownership/overlap evidence. End-wrapper-only changes cannot solve this measured intersection.
- No active apply, blind review, fresh3×256 confirmations, frontend/browser adoption checks or release8192
  measurement. Standalone package-import adoption remains unvalidated. Overall refactor remains unpromoted.

Evidence root: `assets/results/diversity_refactor/n27-candidate-04/`.
- verdict.json SHA256: `4c71ef803b79aa2335f99de36a027bf997d7795c9f23628dd9375e8a072cd57b`.
- Gate SHA256: `d242cd26a5468a66764f5fb245779c451f1eddf819a4e8ea8a37e0f201fb9126`.
- Reference SHA256: `166679e2de1823b63f1cdfe29ea73b028e5ff822d5605d3a7ee9fafd54f57587`.
- Source tree: `001339a08ef35518a9f2267ab5eda751318ac4ada4013099526b266b6649d4b1`.
- Source/config: `b8e7813e56d1776451ec7969a1f3b38d53192dc87bf4b79d666a60553d498367` /
  `05f8d34938ef99842791f630ec151bf30bf110525596717bf7ad0447f8bcc993`.
- Plans, source/observation/quality receipts, examples, real-graph smoke, coverage diagnosis, strict guards,
  independent reviews and reproducible evaluation harnesses are hash-bound in verdict.json.
