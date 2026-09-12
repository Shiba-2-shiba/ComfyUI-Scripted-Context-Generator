# Semantic Diversity / Natural Language Refactor Tasks

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
関連仕様: [`docs/diversity_refactor/spec.md`](./spec.md)
進捗正本: [`docs/diversity_refactor/progress.md`](./progress.md)

## N2.7-R4.3 implementation sequence

Execution contract: [R4.3 implementation plan](./r43_implementation_plan.md).
Keep one active task and satisfy its acceptance before starting the next.
This sequence is distinct from the final documentation task named R4.3 below.

- [x] R43-00 Intake/source preservation — PASS, 2026-09-11;
  [report](./r43_intake.md), [receipt inventory](./r43_intake_summary.json).
  No runtime changes. Fresh focused result:151 passed,1 known alias failure,
  1,888 subtests;29 related regressions passed. Adoption remains BLOCKED.
- [x] R43-01 Import and metadata contracts — PASS, 2026-09-11;
  [result](./r43_import_plan.md), [receipts](./r43_import_summary.json).
  No exclusions:175 focused tests/1,888 subtests;87 regression tests/33 subtests.
  Paired512 and package replay match baseline; public I/O/mapping/V150 unchanged.
- [x] R43-02 Reachability audit and candidate07 parity — PASS, 2026-09-11;
  [result](./r43_audit_plan.md), [receipts](./r43_audit_summary.json).
  Fixed512 x6 measured; ordinary9 v2 cases/3 families,17 forced constructors,
  9 exact output matches/8 changed outputs with unknown semantics. Paired/repeat
  parity passes;202 focused tests/1,922 subtests and87 regressions/33 subtests pass.
- [x] R43-03 Common runtime evidence and input binding — PASS, 2026-09-11;
  [result](./r43_evidence_plan.md), [receipts](./r43_evidence_summary.json).
  Immutable tri-state types, exact Action/legacy adapters and reconstruction-based
  binding validation.236 focused tests/1,931 subtests;87 regressions/33 subtests.
  All512 ordinary records unchanged; typed evidence matches across processes,
  import modes, execution order/hashseeds and a separate snapshot. No new permission.
- [x] R43-04 Clothing trace/reconstruction — PASS, 2026-09-11;
  [result](./r43_clothing_plan.md), [receipts](./r43_clothing_summary.json).
  Shared renderer trace and selected-attempt capture;102/512 runtime-available
  history-bound proofs,512 audit-only exact replays, no new family permission.
  259 focused tests/1,963 subtests;87 regressions/33 subtests; paired512 unchanged.
- [x] R43-05 Scene trace/reconstruction — PASS, 2026-09-11;
  [result](./r43_scene_plan.md), [receipts](./r43_scene_summary.json).
  Source/default/raw hashes and shuffle/dedupe trace;10/512 runtime-bound proofs,
  512 audit-only exact replays, known gallery/reference ownership.278 focused
  tests/1,963 subtests;87 regressions/33 subtests; paired512 unchanged.
- [x] R43-06 Template/Subject/Garnish/Mood adapters — PASS, 2026-09-12;
  [result](./r43_support_plan.md), [receipts](./r43_support_summary.json).
  All seven common components diagnosed from current Builder inputs; source and
  grammar remain separate.299 focused tests/1,963 subtests;87 regressions/33 subtests;
  paired512 unchanged, fresh root/package evidence identical. No new permission.
- [x] R43-07 Family-specific proof and constructors — PASS, 2026-09-12;
  [result](./r43_family_plan.md), [receipts](./r43_family_summary.json).
  One common authority, six bound constructors and opt-in adapters;348 focused
  tests/1,963 subtests,87 regressions/33 subtests pass. Ordinary512 unchanged.
  Recombination6-family PASS; common real-graph eligible0/512, recorded separately.
- [x] R43-08 Integration and real-graph six-family evidence — PASS, 2026-09-12;
  [ordinary expansion](./r43_ordinary_plan.md), [receipts](./r43_ordinary_summary.json).
  Ordinary v2 9→10/512; old9 successes/502 remaining fallbacks and selected facts
  preserved. All6 real-graph families forced (15 rows);423 focused/87 regression
  tests pass. Ordinary execution remains3 families; formal adoption BLOCKED.
- [x] R43-09 Development verification and separate architecture/development verdicts — PASS, 2026-09-12;
  [portable CLI/result](./r43_verification_plan.md), [receipts](./r43_verification_summary.json).
  Architecture/development PASS;492 focused/87 regression tests; clean-source full
  intake is canonical-byte-identical. Ordinary10/512,3 families,all6 real forced.
  Guide unmet and formal evidence pending; adoption-preflight/adoption BLOCKED.
- [x] R43-10 Conditional formal evaluation handoff — prepared, 2026-09-12;
  [handoff and complete obligations](./r43_handoff.md), [integrity receipts](./r43_handoff_summary.json).
  Original sealed1120 files and historical formal/paired/fixed80 evidence verified;
  source/config/measurement comparability recorded. Actual formal handoff/adoption
  BLOCKED (guide unmet; candidate formal NOT_RUN). No evaluation freeze/main/N2.8.

Next bounded follow-up (outside the completed R43 task sequence): plan reusable
Action+Scene coverage from the remaining fallback intersections before automatic
heavy formal evaluation. Keep the locked thresholds and semantic selection.

---

## 0. Common Instructions for Codex

全 task 共通:

- 一度に1 task ID のみ実装する。
- task 開始時に `progress.md` を `IN_PROGRESS` にする。
- task 終了時に command/result/changed files/commit を `progress.md` に記録する。
- V150 protected data を variation expansion 目的で変更しない。
- public `Context*` node I/O を変更しない。
- `context_json` contract/version を変更しない。
- semantic-only policy を維持する。
- seed determinism を維持する。
- LLM / embedding / NLP package dependency を追加しない。
- camera/quality/style/artist domain を active output に追加しない。
- Acceptance fail 時は次 task に進まない。
- 既存の失敗を unrelated fix として抱き合わせない。
- large audit / blind review / 3x256 confirmation を毎 task で繰り返さない。

---

# F0. Wave Setup / V150 Freeze

## F0.1 Add canonical wave docs

Files:

```text
docs/diversity_refactor/spec.md
docs/diversity_refactor/tasks.md
docs/diversity_refactor/progress.md
```

Acceptance:

- [x] 3 files are tracked
- [x] each file links the other two
- [x] Codex execution contract is explicit
- [x] V150 freeze is explicit

---

## F0.2 Capture exact V150 baseline

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

Record in `progress.md`:

- HEAD
- date
- counts
- command results
- source/data hashes if existing tooling exposes them

Acceptance:

- [x] baseline HEAD recorded
- [x] exact V150 counts recorded
- [x] missing action pools = 0
- [x] validators have no unexplained errors
- [x] full flow passes or pre-existing failure is classified

---

## F0.3 Mark V250/V350/V500 deferred

Files likely:

```text
README.md
CURRENT_STATUS.md
docs/variation_expansion/500k_loop_plan.md
docs/diversity_refactor/progress.md
```

Requirements:

- preserve historical 500k plan
- do not delete V150 evidence
- state that current active roadmap is effective-diversity / realizer / scheduler
- state V250/V350/V500 are deferred, not cancelled

Acceptance:

- [x] README no longer presents 250k/500k as immediate next implementation target
- [x] CURRENT_STATUS points to `docs/diversity_refactor/`
- [x] 500k plan remains accessible as deferred historical/future roadmap
- [x] no runtime/data change

---

## F0.4 Add freeze regression guard

Preferred test:

```text
assets/test_v150_freeze_contract.py
```

Guard only stable intent, not incidental file bytes.

Recommended checks:

- active variation count remains expected V150 count
- subject/location scope remains V150 baseline
- protected expansion files are not accidentally replaced by a new target plan
- no test asserts future 250k/500k target as active requirement

Avoid:
- making normal tests depend on volatile docs wording
- hardcoding every JSON byte

Acceptance:

- [x] test fails on accidental base expansion
- [x] test does not block legitimate bugfix-only data correction without an intentional baseline update
- [x] focused test passes

---

# A1. Effective Diversity Audit

## A1.1 Lock metric schema before implementation

Create or document:

```text
effective-diversity-audit/v1
semantic_signature_v1/core
semantic_signature_v1/frame
```

Files:

```text
docs/diversity_refactor/spec.md
docs/diversity_refactor/progress.md
```

Lock:

- metric names
- N values
- signature fields
- normalization rules
- report envelope

Acceptance:

- [x] schema is written before metric code
- [x] semantic signature does not depend primarily on parsing final prose
- [x] syntax family source is debug/content-plan metadata where available

---

## A1.2 Implement pure metric helpers

Files:

```text
tools/effective_diversity_metrics.py
assets/test_effective_diversity_metrics.py
```

Implement:

```text
semantic uniqueness
axis coverage
exact repetition
normalized repetition
semantic repetition
Shannon syntax entropy
normalized syntax entropy
max consecutive family run
```

Tests must include:
- empty input
- one family
- perfectly balanced families
- highly skewed families
- duplicate records
- deterministic ordering

Acceptance:

- [x] no external dependency
- [x] pure functions
- [x] focused tests pass
- [x] K<=1 entropy handled explicitly
- [x] divide-by-zero safe

---

## A1.3 Implement semantic signature builder

Preferred:

```text
tools/effective_diversity_metrics.py
```

May add a small helper module if needed.

Inputs:
- workflow runner record
- final context
- ActionFrame/debug decisions

Requirements:
- canonical subject/location
- action family/main verb
- object family
- frame-level slots when available
- missing values use explicit sentinel or omission consistently
- do not use whole final prompt as semantic signature

Acceptance:

- [x] paraphrase-only surface change does not necessarily create a new core signature
- [x] object/action change does create a new signature
- [x] signature output is deterministic
- [x] tests cover missing ActionFrame

---

## A1.4 Implement audit CLI using workflow runner

File:

```text
tools/audit_effective_diversity.py
assets/test_effective_diversity_audit.py
```

Reuse:

```text
tools/workflow_prompt_runner.py
```

CLI minimum:

```bash
python tools/audit_effective_diversity.py --profile smoke
python tools/audit_effective_diversity.py --profile gate
python tools/audit_effective_diversity.py --profile release
```

Optional:
- `--seed-start`
- `--sample-count`
- `--output`

Requirements:
- read-only
- deterministic
- canonical JSON
- records source/workflow/config hashes where available

Acceptance:

- [x] smoke audit runs without mutating repository sources
- [x] same input produces same metrics/report hash
- [x] invalid profile fails clearly
- [x] unit test uses small sample and does not become a long audit

---

## A1.5 Capture V150 effective-diversity baseline

Run:

```bash
python tools/audit_effective_diversity.py --profile gate --output assets/results/effective_diversity/v150_baseline_gate.json
```

If `assets/results/` is ignored:
- do not force large generated artifact into Git
- record path + SHA-256 + summary metrics in `progress.md`
- tracked compact summary is allowed if consistent with current repository policy

Record at minimum:

```text
semantic_core_unique@128/512/2048
semantic_frame_unique@128/512/2048
coverage axes
exact duplicate rate
normalized duplicate rate
semantic duplicate rate
syntax family counts
normalized syntax entropy
max same-action-family run
max same-syntax-family run
```

Acceptance:

- [x] baseline is hash-bound
- [x] thresholds are not selected until baseline is visible
- [x] no runtime behavior changed

---

## A1.6 Lock Realizer/Scheduler target and guard thresholds

Based on A1.5 only.

Write to `progress.md`:

Target examples:
- syntax entropy improvement
- targeted coverage improvement
- consecutive run reduction

Guards:
- semantic core unique non-regression
- semantic frame unique non-regression
- consistency non-regression
- naturalness non-regression
- banned-domain leakage = 0
- determinism = exact

Do not invent aggressive percentages without evidence.

Acceptance:

- [x] target metrics explicitly separated from guard metrics
- [x] thresholds cite baseline values
- [x] thresholds are locked before N2 implementation comparison

---

# N2. Natural Language Realizer v2

## N2.1 Add realizer-v2 internal contract tests

Before changing active rendering.

Preserve the immutable baseline source snapshot (including the uncommitted audit implementation)
and bind later observations/comparisons to the A1.6 lock in `progress.md` section 7.
The aggregate A1.5 report alone cannot prove per-seed semantic-slot preservation.

Files:

```text
assets/test_prompt_realizer_v2.py
```

Test invariants:

- same semantic slots → same facts after realization
- no object invention
- no location invention
- no subject count change
- no banned domain terms
- deterministic by seed
- unsupported surface falls back
- solo safety remains valid

Acceptance:

- [x] failing tests describe intended v2 behavior before activation
- [x] no public node changes

---

## N2.2 Extend syntax-family metadata

Preferred file:

```text
vocab/data/template_catalog.json
```

Or a small new internal config if cleaner:

```text
vocab/data/natural_language_realizer_v2.json
```

Add metadata for 6 required family candidates:

```text
subject_action_scene
subject_action__scene_tail
scene_lead_subject_action
action_lead_subject_scene
subject_scene_action
subject_action_scene_insert
```

Optional:
```text
scene_sentence__subject_action
subject_action_progress__scene
```

Each family defines:
- key
- roles
- required slots
- allowed/avoided action surfaces
- sentence count / clause order
- fallback safety

Acceptance:

- [x] at least 6 families represented
- [x] no new semantic vocabulary bulk list
- [x] asset validator or dedicated validation rejects malformed family definitions

---

## N2.3 Implement eligibility engine

Files likely:

```text
pipeline/prompt_realizer.py
prompt_renderer.py
```

May extract:

```text
pipeline/syntax_family_selector.py
```

only if responsibility is clearly reduced.

Implement:

```text
eligible_syntax_families(plan, action_frame, action_surface, ...)
```

Rules:
- filter before select
- fragment/gerund/clause handled explicitly
- dangling modifier unsafe cases excluded
- missing scene anchor excludes scene-lead families
- no safe family → baseline

Debug:
- eligible keys
- rejected keys/reasons when debug enabled
- fallback reason

Acceptance:

- [x] eligibility deterministic
- [x] baseline always available
- [x] unsafe action surfaces cannot force incompatible family
- [x] focused tests pass

---

## N2.4 Implement v2 realization for first 3 families

Implement:

```text
subject_action_scene
subject_action__scene_tail
scene_lead_subject_action
```

Requirements:
- reuse existing clauses where possible
- preserve current punctuation normalization
- do not introduce general verb-conjugation framework

Run:
- focused realizer tests
- smoke effective-diversity audit

Acceptance:

- [x] semantic invariants pass
- [x] natural text snapshots added
- [x] deterministic
- [x] no banned domain leakage

---

## N2.5 Implement v2 realization for remaining required families

Implement:

```text
action_lead_subject_scene
subject_scene_action
subject_action_scene_insert
```

Rules:
- action-lead only when modifier attachment is safe
- subject-scene-action only when predicate realization is explicitly supported
- otherwise baseline/family fallback

Optional family 7–8 only after required six are stable.

Acceptance:

- [x] 6 safe families can become eligible on appropriate fixtures
- [x] unsafe fixtures fall back rather than produce broken English
- [x] no large lexical dictionary added

---

## N2.6 Add v2 decision/debug payload

`ContextPromptBuilder` decision must expose:

```text
realizer_version
syntax_family
eligible_syntax_families
syntax_fallback_reason
clause_order
```

Acceptance:

- [x] Effective Diversity Audit reads syntax family from metadata, not prose regex
- [x] debug addition does not break context/workflow compatibility
- [x] deterministic debug payload

---

## N2.7 Run Realizer v2 candidate gate

Run:
- focused realizer tests
- prompt renderer snapshots
- `verify_full_flow`
- effective diversity `gate`
- prompt-quality fixed cohort comparison

Compare to A1.5 baseline.

Required:
- target syntax metrics improve
- semantic guard metrics pass
- naturalness non-regression
- redundancy non-regression

Acceptance:

- [x] before/after table recorded in `progress.md`
- [x] candidate marked `ELIGIBLE`, `REJECTED`, or `BLOCKED`
- [x] no activation if thresholds fail

---

## N2.7-R1 Repair real-workflow eligibility and re-evaluate (follow-up)

Created from candidate-01 rejection; completed as an isolated repair/evaluation.
Candidate-02 verdict: REJECTED (three real v2 applications; six-family/entropy gates unmet).
Evidence: progress.md N2.7 receipt, 0/2048 v2 applications and exact v1 fallback preservation.

Before edits, write a bounded repair plan and regression fixtures from actual failed workflow clauses.
Likely scope: `pipeline/syntax_family_selector.py`, concrete-plan integration in `prompt_renderer.py`,
`pipeline/prompt_realizer.py` as needed, and corresponding tests.

- Preserve semantic facts and selected template/slot information; do not simplify away subject/clothing/scene content.
- Derive positive safety from verified template/slot structure; retain existing unsafe-clause rejection fixtures.
- Do not weaken A1.6 thresholds, policy, missing-value rules or the six-observed-family requirement.
- Freeze a new candidate/source identity, run the same gate and fixed-cohort comparison, record a new verdict.
- N2.8 remains blocked until an eligible candidate satisfies all applicable adoption requirements.

Acceptance:

- [x] real workflow clauses have regression coverage, not only simple noun-phrase fixtures
- [x] no semantic/policy/solo/determinism regression or threshold relaxation
- [x] new candidate gate, per-seed comparison and terminal verdict recorded

Evidence: `assets/results/diversity_refactor/n27-candidate-02/verdict.json`, code-review.md,
locked-gates.json and progress.md. Automatic preservation checks passed; no new human-quality claim.

---

## N2.7-R2 Extend structural coverage beyond the bounded direct-template lane

Completed as an isolated structural repair/evaluation. Candidate-03 is REJECTED:
four observed structures and three actual v2 orders, but only three supported measured seeds.

- Plan the next bounded change before edits; use recorded unsupported real template/slot structures.
- Preserve clause provenance through construction and validate each proposed attachment/order.
  Do not grow a whole-prompt/seed allowlist or infer grammar safety from catalog membership.
- Preserve all selected facts, unknown safety facts, negative fixtures, V150 assets and A1.6 thresholds.
- Improve reusable constructor/template coverage; distinguish actual v2 family executions from v1 labels.
- Freeze a new isolated candidate and rerun the same source-bound gate and fixed-cohort comparison.
- N2.8 stays blocked until all required adoption evidence passes.

Acceptance:

- [x] newly supported structures have real-workflow and adversarial regression coverage
- [x] no semantic/policy/solo/determinism regression or threshold relaxation
- [x] new gate, per-seed observations and terminal candidate verdict recorded

Evidence: `assets/results/diversity_refactor/n27-candidate-03/verdict.json`, repair-plan.md,
code-review.md, locked-gates.json and progress.md. New placements bind modifiers to the location
through a relative clause; two-sentence bytes and unsupported-placement fallback are preserved.

---

## N2.7-R3 Broaden verified clause coverage beyond the three measured seeds

Completed as a bounded productive-grammar repair and isolated evaluation. Candidate04 REJECTED:
actual applications3→5/2048, but observed families4 and normalized entropy remain below adoption gates.

- Write a bounded producer/grammar-evidence plan before edits. Identify reusable source constructor
  evidence for background and clothing first; do not extend whole-action or seed allowlists.
- Bind any structural evidence to the actual selected text. Catalog membership, heuristic ActionFrame
  slots and caller safety booleans alone remain insufficient grammar proof.
- Demonstrate newly supported actual clauses beyond the three R1/R2 examples before freezing the
  next candidate. Preserve nouns, actions, relationships, unknown facts and verified modifier ownership.
- Preserve upstream selected facts, public node/context contracts, V150 assets and exact v1 fallback.
  Do not serialize new producer debug fields merely to bypass the fixed per-seed preservation checks.
- Keep all A1.6 targets and the same source-bound2048/8192-reference/fixed80 evaluation. Report
  broader application separately from declared/observed families; do not activate without adoption evidence.

Acceptance:

- [x] broader real-clause coverage and adversarial grammar/binding tests
- [x] no semantic/policy/solo/determinism regression or threshold relaxation
- [x] new frozen candidate, paired observations, fixed gates and terminal verdict

Evidence: `assets/results/diversity_refactor/n27-candidate-04/verdict.json`, pre-freeze-smoke.json,
coverage-diagnosis.json and progress.md. Seed41/458 execute v2 through the real graph; no runtime seed list
or new complete action strings. Finite grammar, producer binding and location prepositions are tested.

---

## N2.7-R4 Expand productive action and common subordinate-clause coverage

State: **BLOCKED** (candidate05 development verified 2026-09-09; adoption evidence incomplete).
Execution followed the supplied `docs/scg_diversity_refactor_docs/# N2.7-R4 Codex Implementation Spec.txt`.
Source hash: `4bd18edb40ac756f4871a4a2b317542e9260dacd2ec09c620b45eaf0a3af2b21`.
Intake512 exact replay512, structural primary28 vs legacy8; actual v2 remains5/512,
observed families4. Unchanged non-action intersection contains only the old5 cases.
Candidate05 only; active runtime untouched. Details and limitations are in progress.md.

- Plan the next bounded grammar pass from the recorded source clauses, prioritizing recurring action
  constructions (motion/stance, manner and subordinate predicates) over additional complete strings.
- Reuse the nominal/valency and producer-bound grammar; review actor identity, modifier ownership,
  referents and place overlap before deriving safety facts for any new construction or placement.
- Keep source leaf membership distinct from grammar proof. Preserve explicit unknowns, old output hashes,
  exact v1 fallback, public/context contracts, upstream selected facts and V150 data.
- Demonstrate additional actual clauses and unseen grammatical combinations before freezing a new candidate.
  Retain all A1.6 thresholds, six observed families, same fixed cohort/reference ranges and zero-regression guards.
- Record formal gate, paired observations and terminal verdict. No promotion on grammar-test success alone.

Acceptance:

- [x] reusable action constructions broaden measured real-clause coverage (primary grammar only; actual v2 unchanged)
- [x] adversarial subject/ownership/overlap/binding tests and development512 preservation checks pass
- [ ] fresh source-bound candidate gate/fixed80/per-seed receipt and explicit adoption verdict

Formal8192/2048/fixed80 was not run under R4 sections15/23; BLOCKED is an evidence
limitation, not a measured A1.6 threshold rejection.120 tests/1,807 subtests passed;
the pre-existing active-only metadata test remains deselected as in candidate04.

### N2.7-R4.1 Follow-up: missing producer grammar and scene attachment evidence

Scoped development PASS; adoption **BLOCKED** (2026-09-09, isolated candidate06).
Source: `462423f496516f2377407c10b61c15f35f16412c709170e14d45c542ef823d13`.
Actual v2 applications5 ->7/512; new original seeds190/482 execute standalone scene.
Old5 outputs and505 fallbacks remain byte-identical; paired512 semantic/upstream
preservation and22 rollback/determinism probes pass.139 focused tests/1,862 subtests
and29 context regressions pass. See progress.md and candidate06 `verdict.json`.

The bounded pass addressed candidate05 diagnostic source leaves:
compound predicate identity, grammatical subject vs owner, and scene attachment.
Preserve existing runtime-only evidence and public/semantic contracts. Acceptance
must include additional unchanged real-graph examples and6-family positive fixtures
before formal gates. No scheduler, active apply, new allowlists, or relaxed thresholds.

- [x] additional unchanged real-workflow examples execute v2
- [x] runtime-only producer binding, ownership/unknown/old-output regressions verified
- [ ] all6 real-graph family fixtures and full formal adoption evidence

Next bounded follow-up: scene/whole-action coverage and independent placement proof;
retain catalog requirements and unknown overlap rather than granting unproved families.

### N2.7-R4.2 Compound predicates and independent placement proof

Scoped development PASS; adoption **BLOCKED** (2026-09-09, isolated candidate07).
Source: `b8a99c2fa84cc59e2ade7378d6614527a3bfe672d42e474d0dbaca6078c57472`.
New original88/234 bring actual v2 **7 ->9/512**. Prior7 and503 fallback raw/cleaned
outputs remain exact; semantic/upstream512 and24 rollback/determinism probes pass.
160 focused tests/1,890 subtests plus29 context regressions pass; existing1 exclusion
is independently reproduced on parent06. See progress.md/candidate07 verdict.

The bounded pass diagnosed candidate06 complete-case
gaps, preserve semantic/frame identity while validating grammatical predicates,
and prove bounded scene placements from producer fields. Retain prior successful
outputs and all unknown guards. Paired512 and independent review are required;
formal evaluation remains gated on adequate coverage and six-family proof.

- [x] new complete real-workflow cases with explicit owner/subject separation
- [x] compound parser/head binding and finite scene ownership regressions
- [x] paired512 preservation, old-output retention and independent code review
- [ ] sufficient real-graph syntax-family coverage and formal adoption evidence

Further work keeps the current unknown guards and public contracts; no N2.8 apply.

---

## N2.8 Activate Realizer v2 for `composition_mode=true`

Only after N2.7 eligible.

Requirements:
- public node I/O unchanged
- `composition_mode=false` remains legacy rollback
- v1 internal fallback retained for one release/wave
- README/CURRENT_STATUS only updated after final verification

Acceptance:

- [ ] active workflow uses v2
- [ ] fallback path tested
- [ ] workflow sample loads/saves
- [ ] effective audit shows expected syntax families

---

# D3. Deterministic Diversity Scheduler

## D3.1 Implement scheduler primitive with exhaustive unit tests

Preferred new file:

```text
pipeline/diversity_scheduler.py
assets/test_diversity_scheduler.py
```

API example:

```python
spread_index(seed, size, namespace, block_key="")
```

Tests:
- size 0/1 behavior
- deterministic
- bounds
- namespace separation
- consecutive-seed spread
- multiple sizes including prime/non-prime
- no built-in hash dependence

Acceptance:

- [ ] uses `mix_seed`
- [ ] no global mutable RNG
- [ ] deterministic across process runs
- [ ] distribution tests are deterministic, not flaky statistical tests

---

## D3.2 Add generic family-group selection helper

API concept:

```python
select_spread_group(
    candidates,
    diversity_key,
    seed,
    namespace,
    ...
)
```

Requirements:
- receives already eligible candidates
- never reintroduces filtered candidates
- stable sorting before scheduling
- explicit fallback for missing diversity key

Acceptance:

- [ ] input order variations do not silently change result when canonical keys are equal/stable
- [ ] empty/single group handled
- [ ] tests cover duplicate family keys

---

## D3.3 Integrate scheduler into syntax-family selection

Use only eligible v2 syntax families.

Selection order:

```text
eligibility
  ↓
role/preference weighting if applicable
  ↓
scheduler
  ↓
render
```

Run:
- scheduler tests
- realizer tests
- effective-diversity smoke/gate

Primary target:
- higher syntax coverage@N
- lower max consecutive same syntax
- normalized syntax entropy improvement

Acceptance:

- [ ] semantic/naturalness guards pass
- [ ] syntax target improves vs N2 baseline
- [ ] deterministic

---

## D3.4 Audit action-family bias before integration

Do not modify action selection yet.

Use Effective Diversity baseline/current candidate to identify:
- dominant action families
- dominant verbs
- dominant objects
- consecutive repeats
- whether current history penalty already solves the problem

Select one diversity key for first integration:

Preferred order:
1. existing explicit action semantic family/purpose
2. normalized main verb
3. object family
4. composite key only if needed

Record decision in `progress.md`.

Acceptance:

- [ ] chosen key justified by measured bias
- [ ] no scheduler integration if no meaningful action bias exists

---

## D3.5 Integrate scheduler into action selection

Likely files:

```text
pipeline/action_generator.py
pipeline/diversity_scheduler.py
```

Keep existing:
- solo safety
- object hotspot policy
- recent verb penalty
- recent object penalty
- location compatibility
- Semantic EPIG / semantic rank

Scheduler acts only inside quality-equivalent/eligible candidates.

Do not flatten meaningful weights without evidence.

Acceptance:

- [ ] focused action tests pass
- [ ] semantic EPIG tests pass
- [ ] object-policy tests pass
- [ ] action coverage/repetition target improves or candidate is rejected
- [ ] no consistency regression

---

## D3.6 Optional scheduler axes

Only create subtask if audit demonstrates need.

Candidates:

```text
garnish family
template part family
clothing family
```

For each:
- baseline bias evidence required
- separate task
- separate focused gate

Acceptance:

- [ ] no speculative broad integration

---

# R4. Combined Adoption / Final Verification

## R4.1 Run combined gate

Commands:

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python assets/calc_variations.py --json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
python tools/audit_effective_diversity.py --profile release --output assets/results/effective_diversity/final_release.json
```

Also run current repository-required:
- prompt-quality fixed cohort
- frontend tests
- GUI/workflow round-trip
- blind review / confirmation only if current contract requires it for active prompt-surface adoption

Acceptance:

- [ ] all mandatory gates pass
- [ ] V150 count remains frozen
- [ ] no public I/O change
- [ ] final effective-diversity report hash recorded

---

## R4.2 Produce final before/after table

Record in `progress.md`:

```text
V150 baseline
Realizer v2 candidate
Realizer v2 + Scheduler final
```

Metrics:
- semantic_unique@N core/frame
- coverage@N by axis
- repetition
- syntax entropy
- action-family distribution
- consistency
- naturalness
- deterministic checks

Acceptance:

- [ ] improvement claims tied to measured metrics
- [ ] no theoretical variation number used as substitute for effective diversity

---

## R4.3 Update canonical docs

Files:

```text
README.md
CURRENT_STATUS.md
REPO_STRUCTURE.md   # only if structure changed
docs/diversity_refactor/progress.md
```

State:
- V150 semantic-base frozen
- Effective Diversity Audit command
- Realizer v2 active status
- Scheduler active axes
- V250/V350/V500 remain deferred
- rollback path

Acceptance:

- [ ] docs match actual runtime
- [ ] no stale "next target 500k" language as active roadmap
- [ ] commands are copy/paste runnable

---

## R4.4 Close wave

`progress.md`:

```text
Wave status: PROMOTED | PARTIALLY_PROMOTED | REJECTED
```

If partial:
- specify which features promoted
- specify which rejected
- do not leave ambiguous TODOs as if promoted

Acceptance:

- [ ] every task has terminal status
- [ ] unresolved work moved to explicit follow-up section
- [ ] final HEAD/commit recorded
