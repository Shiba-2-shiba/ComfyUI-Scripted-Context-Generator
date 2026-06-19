# Prompt IR Refactor Progress

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
対象ブランチ: `dev2`
作成日: 2026-06-19
関連仕様: `spec.md`
関連タスク: `tasks.md`

---

## 1. Current State

P1-P5 の初期実装と、限定 active selection の導入は完了。

この文書セットは、複数の2026年論文から取り込める設計思想を、
既存の script-only prompt generation 方針に合わせて段階導入するためのもの。

Prompt IR / validator / candidate rerank は、solo 文脈で active risk family または location-first layout risk が
検出された場合に限り、sanitizing / layout-repair candidate を実出力へ反映する。
広範な layout-first 再描画はまだ active output には使わない。
`social_interaction` 単独と `mirror_clone` は検出・監査のみで、active output には使わない。

---

## 2. Baseline Repo State

2026-06-19 時点:

| Check | Result | Notes |
|---|---|---|
| `git status --short --branch` | Pass | `## dev2...origin/dev2` |
| Current prompt surface | Stable | Context-first `Context*` nodes + `PromptCleaner` |
| Current base variations | Stable | `103,212` |
| Current variation boundary | Stable | `120 subjects / 90 locations` |
| Repository cleanup | Done | `bb254ff Make repository cleanup checks routine-safe` pushed |

---

## 3. Milestone Status

| Milestone | Title | Status | Notes |
|---|---|---|---|
| P0 | Docs and behavior-lock plan | Done | `spec.md`, `progress.md`, `tasks.md` added |
| P1 | Prompt IR specification | Done | `core/prompt_ir.py`, passive debug shape, unit tests |
| P2 | Read-only prompt validator audit | Done | `core/prompt_ir_validator.py`, `tools/audit_prompt_ir_candidates.py` |
| P3 | Candidate-and-rerank | Done | Deterministic candidates, selector summary, guarded active selection |
| P4 | Layout-first renderer | Done | Layout-first repair is active only for location-first solo prompts; broad output reordering is not active |
| P5 | Risk family policy | Done | `vocab/data/prompt_risk_families.json`, policy loader, solo safety integration |
| P6 | Final verification and docs | In progress | Active docs updated; full discover contains existing long-running audit tests |

Status vocabulary:

- `Not started`
- `In progress`
- `Blocked`
- `Done`
- `Deferred`

---

## 4. Decision Log

| Date | Decision | Reason | Impact |
|---|---|---|---|
| 2026-06-19 | Keep the refactor script-only | User explicitly wants no LLM in prompt generation | No LLM decomposition, agent runtime, or model API dependency |
| 2026-06-19 | Use papers as design input, not implementation source | Most methods operate inside diffusion sampling or learned embeddings | Implement text/IR/validator analogs only |
| 2026-06-19 | Start with read-only validator | Avoid changing prompt output before scoring is understood | P2 precedes rerank and renderer changes |
| 2026-06-19 | Keep public node I/O unchanged | Existing ComfyUI workflows must continue to load | IR starts internal/passive |
| 2026-06-19 | Use deterministic branch seeds | Candidate generation must preserve reproducibility | Branches use labeled `mix_seed()` |
| 2026-06-19 | Start rerank as passive | Avoid output drift while validator quality is still being observed | Superseded by guarded active selection after target tests were added |
| 2026-06-19 | Avoid audit overhead on clean paths | Normal prompt generation must not pay full audit cost | Active selection first checks risk families; candidate scoring runs only for risk-bearing solo prompts or debug/audit |
| 2026-06-19 | Enable guarded active selection | User requested the next phase after passive foundation | Only solo prompts with active risk families can use the sanitized lower-risk candidate |
| 2026-06-19 | Keep layout-first broad reordering inactive | Full prompt reordering has higher snapshot/output drift risk | Active branch sanitizes risky clauses while preserving the baseline order |
| 2026-06-19 | Fix validator residual risk after sanitization | Clean `1girl, solo in ...` prompts were being misread as location-first | Subject anchor detection now prefers real subject phrases and falls back to tag anchors |
| 2026-06-19 | Add active preview to Prompt IR audit | Audit should show what the active selector would output | `tools/audit_prompt_ir_candidates.py` reports `active_selection` with selected text and validation |
| 2026-06-19 | Enable guarded layout repair | Location-first solo prompts were still a known duplicate-risk pattern | Only location-first risk can activate layout-first repair; clean/risk-free prompts keep baseline order |
| 2026-06-19 | Expand audit cases before widening active scope | Active selection should not expand without false positive / false negative visibility | `prompt_ir_audit_cases.json` now covers 45 clean/risky/borderline/out-of-scope cases and reports expectation summary |
| 2026-06-19 | Narrow commuter risk matching | `commuter pass` was a false positive for crowd risk | Only plural `commuters` is treated as crowd/person risk |
| 2026-06-19 | Keep standalone social and mirror risks audit-only | These risks are real but too broad for safe text-only active cleanup | Active cleanup stays focused on person/crowd/family-artifact/plural-prop/ineffective-motion/layout cases |
| 2026-06-19 | Expand fixture coverage inside existing active families | More variants are safer than activating new broad risk families | Audit now covers 45 cases, including social-only passive cases and person-linked social residue cleanup |

---

## 5. Paper Insight Map

| Paper | Adopt | Do not adopt |
|---|---|---|
| ComfySearch | validation-guided construction, state-aware diagnostics, selective branching | LLM/agent workflow generation |
| PRISM | component decomposition, long prompt factorization | trainable decomposition module, diffusion score composition |
| Object-Background T2I | foreground/background entity split, multi-path pruning idea | attention masks, latent background projection, CLIP scoring |
| Prompt Grafting | layout-first / detail-later ordering | denoising-time prompt switching, LLM-generated layout prompts |
| DDiffusion | risk family / concept distribution, local sanitization | CLIP/MLP semantic retrieval, image localization/redaction |

---

## 6. Open Risks

### 6.1 Output drift

Prompt output may change if IR or layout-first rendering is introduced too early.

Mitigation:

- P2 is read-only.
- P3 active selection is guarded to risk-bearing solo prompts.
- Snapshot tests must be updated only for intentional behavior changes.

### 6.2 Validator overfitting

Risk family rules can become a brittle regex list.

Mitigation:

- Move risk families into data policy.
- Add asset validator checks for duplicate/empty/unscoped patterns.
- Track false positives in audit output.
- Keep fixture-backed false positive / false negative counts visible before widening active selection.

### 6.3 Candidate explosion

Multiple branches can make generation slow and hard to reason about.

Mitigation:

- Start with 2 branches.
- Branch only background / props / garnish / action surface.
- Keep long audits explicit under `tools/`.

### 6.4 Schema compatibility

Adding new fields directly to `PromptContext` could break old workflow payloads.

Mitigation:

- Store early IR in debug/extras only.
- Add schema tests before persistent schema changes.

---

## 7. Implementation Log

### P0. Docs and behavior-lock plan

Files:

```text
docs/prompt_ir_refactor/spec.md
docs/prompt_ir_refactor/progress.md
docs/prompt_ir_refactor/tasks.md
```

Acceptance:

- [x] Paper-to-design mapping is documented
- [x] Non-goals protect script-only direction
- [x] Five requested implementation steps are represented as milestones
- [x] Verification gates are explicit

---

### P1. Prompt IR specification

Files:

```text
core/prompt_ir.py
assets/test_prompt_ir.py
```

Acceptance:

- [x] Prompt IR can be built from existing prompt fragments without changing rendered prompt
- [x] Invalid component name is rejected by tests
- [x] Empty text is rejected or ignored consistently
- [x] Component ordering is deterministic

### P2. Read-only prompt validator audit

Files:

```text
core/prompt_ir_validator.py
tools/audit_prompt_ir_candidates.py
assets/fixtures/prompt_ir_audit_cases.json
assets/test_prompt_ir_validator.py
```

Acceptance:

- [x] Known solo conflict phrases are scored
- [x] Known plural artifact phrases are scored
- [x] Clean prompts receive lower risk scores than fixture failures
- [x] Validator returns structured report without mutating prompt text
- [x] Audit output includes per-case validator and candidate scores

### P3. Candidate-and-rerank

Files:

```text
pipeline/prompt_candidate_generator.py
pipeline/prompt_candidate_selector.py
assets/test_prompt_candidate_rerank.py
```

Acceptance:

- [x] Same seed produces same candidates
- [x] Different branch index produces distinct candidate IDs
- [x] Subject identity does not branch
- [x] Candidate count is bounded
- [x] Selected/rejected candidates are summarized in debug
- [x] Lower-risk sanitizing candidate can be applied to solo prompt output
- [x] Clean prompt paths keep baseline output
- [x] Active selection preview is visible in the Prompt IR audit report
- [x] Location-first solo prompts can select a subject-first layout-repair candidate
- [x] Audit fixture set includes clean, risky, borderline, and out-of-scope cases
- [x] Audit report summarizes false positive / false negative cases
- [x] Standalone `social_interaction` cases remain audit-only
- [x] Person-linked social residue, such as `talking with friends`, is cleaned only when an active person/crowd risk is present

### P4. Layout-first renderer

Files:

```text
core/prompt_ir.py
core/prompt_ir_validator.py
prompt_renderer.py
```

Acceptance:

- [x] Layout-first render contract exists for IR/candidate audit path
- [x] Layout order validator scores bad order worse than good order
- [x] Renderer debug includes layout-order score through `prompt_ir_validator`
- [x] No camera/quality/body-type terms are introduced
- [x] Broad layout-first output reordering remains inactive in this wave
- [x] Guarded active selection preserves baseline clause order while removing risky local fragments
- [x] Active-sanitized clean solo prompts score `total_risk == 0`
- [x] Layout-first repair is guarded to location-first risk, not broad prompt rewriting

### P5. Risk family policy

Files:

```text
vocab/data/prompt_risk_families.json
core/prompt_risk_policy.py
core/solo_safety.py
asset_validator.py
```

Acceptance:

- [x] Risk family JSON validates
- [x] Empty family pattern list is rejected
- [x] Duplicate patterns are detected
- [x] Existing solo risk fixtures map to expected families
- [x] `family photos`, `staff`, `friends`, `people`, `customers`, `decorative pillows`, and `quick step` are classified by policy

## 8. Verification Notes

2026-06-19 implementation verification:

```bash
python -m unittest assets.test_prompt_ir assets.test_prompt_ir_validator assets.test_prompt_candidate_rerank assets.test_prompt_renderer assets.test_prompt_snapshots assets.test_solo_duplicate_suppression assets.test_asset_validator assets.test_determinism
python tools/audit_prompt_ir_candidates.py --seed-count 8 --output assets/results/prompt_ir_validator_smoke.json
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --check
python assets/calc_variations.py --json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

Results:

- Prompt IR targeted unittest: `66 tests OK`
- Prompt IR audit CLI: generated ignored smoke output under `assets/results/` with active selection preview
- Prompt IR audit summary: `45` cases, `45` passed, false positive cases `[]`, false negative cases `[]`
- prompt data validator: `ERROR: []`, `WARNING: []`
- full flow: `OK`
- workflow widget validation: `OK`
- variation scope: `ERROR: []`, `WARNING: []`, base variations `103,212`
- action pool check: `ERROR: []`, `WARNING: []`
- compatibility review check: `ERROR: []`, `WARNING: []`
- asset validator: `0` issues

Long unittest note:

- `python -m unittest discover -s assets -p "test_*.py"` passed at `420 tests OK`
  in `201.276s`.
- The long runtime is dominated by existing audit-style unittest coverage such as
  `assets.test_action_diversity_audit`; the Prompt IR target tests finish in under 2 seconds.
