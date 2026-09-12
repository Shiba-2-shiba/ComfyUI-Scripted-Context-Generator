# Semantic Diversity / Natural Language Refactor Tasks

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`  
関連仕様: `docs/diversity_refactor/spec.md`  
進捗正本: `docs/diversity_refactor/progress.md`

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

- [ ] 3 files are tracked
- [ ] each file links the other two
- [ ] Codex execution contract is explicit
- [ ] V150 freeze is explicit

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

- [ ] baseline HEAD recorded
- [ ] exact V150 counts recorded
- [ ] missing action pools = 0
- [ ] validators have no unexplained errors
- [ ] full flow passes or pre-existing failure is classified

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

- [ ] README no longer presents 250k/500k as immediate next implementation target
- [ ] CURRENT_STATUS points to `docs/diversity_refactor/`
- [ ] 500k plan remains accessible as deferred historical/future roadmap
- [ ] no runtime/data change

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

- [ ] test fails on accidental base expansion
- [ ] test does not block legitimate bugfix-only data correction without an intentional baseline update
- [ ] focused test passes

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

- [ ] schema is written before metric code
- [ ] semantic signature does not depend primarily on parsing final prose
- [ ] syntax family source is debug/content-plan metadata where available

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

- [ ] no external dependency
- [ ] pure functions
- [ ] focused tests pass
- [ ] K<=1 entropy handled explicitly
- [ ] divide-by-zero safe

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

- [ ] paraphrase-only surface change does not necessarily create a new core signature
- [ ] object/action change does create a new signature
- [ ] signature output is deterministic
- [ ] tests cover missing ActionFrame

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

- [ ] smoke audit runs without mutating repository sources
- [ ] same input produces same metrics/report hash
- [ ] invalid profile fails clearly
- [ ] unit test uses small sample and does not become a long audit

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

- [ ] baseline is hash-bound
- [ ] thresholds are not selected until baseline is visible
- [ ] no runtime behavior changed

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

- [ ] target metrics explicitly separated from guard metrics
- [ ] thresholds cite baseline values
- [ ] thresholds are locked before N2 implementation comparison

---

# N2. Natural Language Realizer v2

## N2.1 Add realizer-v2 internal contract tests

Before changing active rendering.

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

- [ ] failing tests describe intended v2 behavior before activation
- [ ] no public node changes

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

- [ ] at least 6 families represented
- [ ] no new semantic vocabulary bulk list
- [ ] asset validator or dedicated validation rejects malformed family definitions

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

- [ ] eligibility deterministic
- [ ] baseline always available
- [ ] unsafe action surfaces cannot force incompatible family
- [ ] focused tests pass

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

- [ ] semantic invariants pass
- [ ] natural text snapshots added
- [ ] deterministic
- [ ] no banned domain leakage

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

- [ ] 6 safe families can become eligible on appropriate fixtures
- [ ] unsafe fixtures fall back rather than produce broken English
- [ ] no large lexical dictionary added

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

- [ ] Effective Diversity Audit reads syntax family from metadata, not prose regex
- [ ] debug addition does not break context/workflow compatibility
- [ ] deterministic debug payload

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

- [ ] before/after table recorded in `progress.md`
- [ ] candidate marked `ELIGIBLE`, `REJECTED`, or `BLOCKED`
- [ ] no activation if thresholds fail

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
