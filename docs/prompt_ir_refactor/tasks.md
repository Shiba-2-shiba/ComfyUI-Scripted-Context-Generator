# Prompt IR Refactor Tasks

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
対象ブランチ: `dev2`
作成日: 2026-06-19
関連仕様: `spec.md`
関連進捗: `progress.md`

---

## 0. Common Instructions

Use these rules for every task in this refactor wave.

- Do not use LLMs for runtime prompt generation.
- Do not add model, CLIP, embedding, or fine-tuning dependencies.
- Do not change public `Context*` node inputs or outputs.
- Preserve seed determinism.
- Preserve semantic-only policy.
- Start with read-only audit before changing output prompts.
- Keep long audits under `tools/`, not as normal unittest prerequisites.
- Record decision/debug payloads in `DebugInfo.decision`.
- Keep prompt generation script-only and deterministic.

Baseline verification:

```bash
git status --short --branch
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --check
python assets/calc_variations.py --json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

---

## P0. Docs And Behavior-Lock Plan

### P0.1 Add planning documentation

Files:

```text
docs/prompt_ir_refactor/spec.md
docs/prompt_ir_refactor/progress.md
docs/prompt_ir_refactor/tasks.md
```

Acceptance:

- [x] The five implementation steps are documented
- [x] Paper-to-design mapping is explicit
- [x] Non-goals exclude LLM/model/sampling changes
- [x] Verification gates are listed

---

## P1. Prompt IR Specification

### P1.1 Define Prompt IR component contract

Candidate files:

```text
docs/prompt_ir_refactor/spec.md
core/prompt_ir.py
assets/test_prompt_ir.py
```

Requirements:

- Define component names:
  - `subject`
  - `character_profile`
  - `clothing`
  - `foreground_action`
  - `object_relation`
  - `location_core`
  - `background_context`
  - `props`
  - `mood`
  - `garnish`
- Define fields:
  - `name`
  - `text`
  - `source`
  - `entities`
  - `families`
  - `risk_families`
  - `budget_cost`
- Keep the first implementation internal only.

Acceptance:

- [x] Prompt IR can be built from existing prompt fragments without changing rendered prompt
- [x] Invalid component name is rejected by tests
- [x] Empty text is rejected or ignored consistently
- [x] Component ordering is deterministic

### P1.2 Add passive IR debug hook

Candidate files:

```text
pipeline/prompt_orchestrator.py
prompt_renderer.py
assets/test_prompt_ir.py
```

Requirements:

- Build IR in passive mode during prompt construction
- Attach summary under `DebugInfo.decision.prompt_ir`
- Do not change `rendered_text`

Acceptance:

- [x] Existing prompt snapshots remain unchanged
- [x] Debug includes component counts and component names
- [x] Seed determinism target tests pass

---

## P2. Read-Only Prompt Validator Audit

### P2.1 Add validator functions

Candidate files:

```text
core/prompt_ir_validator.py
assets/test_prompt_ir_validator.py
```

Validators:

- `solo_conflict_score`
- `plural_artifact_score`
- `foreground_background_alignment_score`
- `semantic_family_overload_score`
- `layout_order_score`
- `location_object_consistency_score`
- `prompt_length_budget_score`

Acceptance:

- [x] Known solo conflict phrases are scored
- [x] Known plural artifact phrases are scored
- [x] Clean prompts receive lower risk scores than fixture failures
- [x] Validator returns structured report without mutating prompt text

### P2.2 Add audit tool

Candidate files:

```text
tools/audit_prompt_ir_candidates.py
assets/fixtures/prompt_ir_audit_cases.json
```

CLI:

```bash
python tools/audit_prompt_ir_candidates.py --seed-count 8 --output assets/results/prompt_ir_validator_smoke.json
```

Acceptance:

- [x] Audit output includes per-case validator scores
- [x] Output includes dropped/flagged component reasons
- [x] Audit can run without generated artifact prerequisites
- [x] `assets/results/` output remains ignored
- [x] Audit output includes false positive / false negative summary
- [x] Audit fixture set includes clean true negatives and risky true positives

---

## P3. Candidate-And-Rerank

### P3.1 Add deterministic candidate generation

Candidate files:

```text
pipeline/prompt_candidate_generator.py
assets/test_prompt_candidate_rerank.py
```

Requirements:

- Generate 2 initial branches per context
- Branch only low-risk variable components first:
  - `background_context`
  - `props`
  - `garnish`
  - `action_surface`
- Use labeled `mix_seed()` calls

Acceptance:

- [x] Same seed produces same candidates
- [x] Different branch index produces distinct candidate IDs
- [x] Subject identity does not branch
- [x] Candidate count is bounded

### P3.2 Add rerank selection

Candidate files:

```text
pipeline/prompt_candidate_selector.py
pipeline/prompt_orchestrator.py
assets/test_prompt_candidate_rerank.py
```

Requirements:

- Score candidates with validator output
- Select highest score or lowest risk according to documented ordering
- Record selected and rejected candidates in debug
- Apply active selection only for risk-bearing solo prompts; keep layout-first broad reordering inactive

Acceptance:

- [x] Selected candidate is deterministic
- [x] Rejected candidates include reason codes
- [x] If all candidates fail, fallback to current single-path output
- [x] Existing prompt snapshots remain unchanged for clean prompt paths
- [x] Risk-bearing solo prompts can use the lower-risk sanitizing candidate as final output
- [x] Active selection audit preview includes selected text, validation, and dropped components
- [x] Location-first solo prompts can use a subject-first layout-repair candidate
- [x] Active expansion is gated by fixture-backed false positive / false negative reporting

---

## P4. Layout-First Renderer

### P4.1 Define layout-first render contract

Candidate files:

```text
prompt_renderer.py
assets/test_prompt_renderer.py
assets/test_prompt_snapshots.py
```

Target order:

```text
layout skeleton:
  subject + location_core + foreground_action

detail pass:
  clothing + object_relation + props

atmosphere pass:
  mood + garnish + background_context
```

Acceptance:

- [x] Layout clauses precede optional garnish/detail overload in IR render path
- [x] solo subject remains early in prompt
- [x] location-first templates are still filtered for solo contexts
- [x] Prompt snapshots remain unchanged for clean prompt paths
- [x] Layout-first broad reordering is not active output yet
- [x] Layout-first repair is active only for location-first solo prompts

### P4.2 Add layout-order validator integration

Candidate files:

```text
core/prompt_ir_validator.py
prompt_renderer.py
assets/test_prompt_ir_validator.py
```

Acceptance:

- [x] Renderer debug includes layout order score
- [x] Bad order fixture scores worse than good order fixture
- [x] No camera/quality/body-type terms are introduced
- [x] Clean `1girl, solo in ...` prompts are not falsely scored as location-first
- [x] Location-first prompt fixtures score worse than subject-first repaired candidates

---

## P5. Risk Family Policy

### P5.1 Add data-driven risk family policy

Candidate files:

```text
vocab/data/prompt_risk_families.json
core/prompt_risk_policy.py
asset_validator.py
assets/test_asset_validator.py
```

Initial families:

- `other_person`
- `crowd`
- `social_interaction`
- `family_artifact`
- `mirror_clone`
- `ineffective_motion`
- `plural_prop_overload`
- `foreground_background_conflict`

Acceptance:

- [x] Risk family JSON validates
- [x] Empty family pattern list is rejected
- [x] Duplicate patterns are detected
- [x] Existing solo risk fixtures map to expected families

### P5.2 Migrate solo safety to risk family lookup

Candidate files:

```text
core/solo_safety.py
core/prompt_risk_policy.py
assets/test_solo_duplicate_suppression.py
```

Requirements:

- Preserve existing `solo_duplicate_risk_flags()` public behavior
- Use risk family policy internally where possible
- Keep phrase-level sanitization local to affected components

Acceptance:

- [x] Existing solo duplicate tests pass
- [x] `family photos`, `staff`, `friends`, `people`, `customers` are classified by family
- [x] `decorative pillows` style plural artifact can be flagged independently from people conflict
- [x] benign viewer-facing phrases remain allowed

---

## P6. Final Verification And Docs

### P6.1 Run full verification

Commands:

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --check
python assets/calc_variations.py --json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

Acceptance:

- [x] Full unittest passes on the current tree
- [x] Prompt data validator reports `ERROR: []`, `WARNING: []`
- [x] Asset validator reports `0` issues
- [x] Base variations remain `103,212` unless separately approved
- [x] Workflow widget validation passes

### P6.2 Update active docs

Files:

```text
CURRENT_STATUS.md
REPO_STRUCTURE.md
docs/prompt_ir_refactor/progress.md
docs/prompt_ir_refactor/tasks.md
```

Acceptance:

- [x] Completed milestones are marked `Done`
- [x] Verification snapshot is current
- [x] Remaining risks are listed
- [x] New tools/tests are discoverable

### P6.3 Review diff

Commands:

```bash
git diff --stat
git diff --check
git status --short
```

Acceptance:

- [x] Diff is scoped to Prompt IR refactor
- [x] No unrelated generated artifacts are included
- [x] No whitespace errors
