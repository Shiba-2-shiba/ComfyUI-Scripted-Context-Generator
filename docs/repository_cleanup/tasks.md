# Repository Cleanup Refactor Tasks

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
対象ブランチ: `dev2`
作成日: 2026-06-19
関連仕様: `spec.md`
関連進捗: `progress.md`

---

## 0. Common Instructions

Use these rules for every task in this cleanup wave.

- Do not change public `Context*` node inputs or outputs.
- Do not change prompt generation semantics intentionally.
- Do not add dependencies.
- Preserve seed determinism.
- Preserve current variation sizing unless a check reveals a pre-existing inconsistency.
- Keep each pass small and independently verifiable.
- Do not move broad directory trees before tests prove the current behavior.
- Prefer deleting inert files over adding new layers.

Focused baseline:

```bash
git status --short --branch
python tools/validate_prompt_data.py
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --check
python assets/calc_variations.py --json
python -m unittest assets.test_solo_duplicate_suppression assets.test_location_semantics assets.test_vocab_lint assets.test_mood_builder
```

---

## R0. Refactor Docs Setup

### R0.1 Add repository cleanup documentation

Files:

```text
docs/repository_cleanup/spec.md
docs/repository_cleanup/progress.md
docs/repository_cleanup/tasks.md
```

Acceptance:

- [x] The four selected cleanup areas are documented
- [x] Non-goals protect runtime behavior
- [x] Verification gates are documented
- [x] Heavy audit split is ordered before structural cleanup

---

## R1. Behavior Lock And Heavy Audit Split

### R1.1 Record pre-change baseline

Commands:

```bash
git status --short --branch
python tools/validate_prompt_data.py
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --check
python assets/calc_variations.py --json
python -m unittest assets.test_solo_duplicate_suppression assets.test_location_semantics assets.test_vocab_lint assets.test_mood_builder
```

Acceptance:

- [x] Results are recorded in `docs/repository_cleanup/progress.md`
- [x] Any failure is classified before cleanup edits continue

### R1.2 Split long repetition guard threshold checks

Files:

```text
assets/test_repetition_guard_audit.py
tools/audit_repetition_guard.py
docs/repository_cleanup/progress.md
```

Requirements:

- Keep short deterministic coverage in unittest
- Move or document `step_count=32, scenario_count=8` as explicit long audit
- Avoid relying on skipped tests as the main solution
- Preserve threshold evaluation logic

Acceptance:

- [x] `python -m unittest assets.test_repetition_guard_audit` completes quickly
- [x] Long audit can still be run explicitly
- [x] Progress doc records the long audit command and expected runtime class

### R1.3 Check full discovery after split

Command:

```bash
python -m unittest discover -s assets -p "test_*.py"
```

Acceptance:

- [x] Full discovery no longer blocks on the known repetition guard long audit
- [x] Any remaining slow audit-style test is listed as a follow-up or split in this wave

---

## R2. `assets/` Responsibility Cleanup

### R2.1 Document active ownership map

Files:

```text
REPO_STRUCTURE.md
CURRENT_STATUS.md
docs/repository_cleanup/progress.md
```

Requirements:

- Clarify which `assets/` paths are active tests, fixtures, ignored outputs, tracked metric inputs, and archive
- Make `assets/results/` generated-artifact policy explicit
- Mention that archive files are not active verification inputs

Acceptance:

- [x] Future readers can distinguish tests from generated artifacts
- [x] Current source-of-truth docs point to the cleanup plan

### R2.2 Resolve tracked generated baseline policy

Candidate file:

```text
assets/results/baseline_20260215_083827.json
```

Requirements:

- Determine whether the file is referenced by tests or docs
- Choose one of:
  - move to `assets/fixtures/` if required as a tracked fixture
  - delete if unused and reproducible
  - document as intentionally tracked exception

Acceptance:

- [x] `.gitignore` policy and tracked files no longer contradict silently
- [x] Tests that need the baseline still pass

### R2.3 Optional low-risk file moves

Only do this if R2.1 and R2.2 show a clear low-risk target.

Candidate directions:

```text
assets/fixtures/          tracked inputs
assets/results/           ignored outputs
tools/                    executable audit scripts
docs/*/archive/           historical docs
```

Acceptance:

- [x] Imports are updated
- [x] Docs links are updated
- [x] Focused tests pass; final discovery is covered by R5

---

## R3. Compatibility Facade Guardrails

### R3.1 Add facade ownership comments

Files:

```text
pipeline/content_pipeline.py
background_vocab.py
clothing_vocab.py
improved_pose_emotion_vocab.py
```

Requirements:

- State that each file is a compatibility facade
- State allowed repo-owned callers
- State preferred import destination for new runtime code
- State removal condition or reason to keep

Acceptance:

- [x] Each facade has a clear future-modifier warning
- [x] No runtime behavior changes

### R3.2 Add compatibility boundary test

Candidate file:

```text
assets/test_compatibility_boundaries.py
```

Requirements:

- Scan tracked Python files
- Ignore docs, archive, tests that intentionally guard compatibility, and the facade files themselves
- Fail if new runtime code imports compatibility facade modules
- Keep an explicit allowlist for intentional callers

Acceptance:

- [x] Existing intended compatibility tests still pass
- [x] New accidental facade import would fail a test

### R3.3 Verify compatibility behavior

Commands:

```bash
python -m unittest assets.test_deprecated_behavior assets.test_registry assets.test_context_content_pipeline
python -m unittest assets.test_compatibility_boundaries
```

Acceptance:

- [x] Compatibility surfaces remain importable
- [x] Guardrails pass

---

## R4. Empty Placeholder Deletion

### R4.1 Check references

Command:

```bash
rg -n "vocab/(background|clothing|data|garnish)/test.md|test.md" README.md CURRENT_STATUS.md REPO_STRUCTURE.md docs assets tools vocab
```

Acceptance:

- [x] References are absent or updated before deletion

### R4.2 Delete inert placeholders

Files:

```text
vocab/background/test.md
vocab/clothing/test.md
vocab/data/test.md
vocab/garnish/test.md
```

Acceptance:

- [x] Files are removed
- [x] No docs or tests refer to them outside this cleanup record
- [x] `git status --short` shows only expected deletions and planned docs/test edits

### R4.3 Verify no behavior impact

Commands:

```bash
python tools/validate_prompt_data.py
python -m unittest assets.test_vocab_lint assets.test_data_consistency
```

Acceptance:

- [x] Validation still passes
- [x] Vocab tests still pass

---

## R5. Final Verification And Docs Update

### R5.1 Run final gate

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

- [x] Commands pass, or failures are documented as known slow audit / ignored artifact issues
- [x] base variations remain `103,212`
- [x] variation boundary remains `120 subjects / 90 locations`

### R5.2 Update active docs

Files:

```text
CURRENT_STATUS.md
REPO_STRUCTURE.md
docs/repository_cleanup/progress.md
```

Acceptance:

- [x] Completed milestones are marked `Done`
- [x] Remaining risks are listed
- [x] Current verification snapshot is accurate
- [x] Cleanup docs are discoverable from current status docs

### R5.3 Review diff

Commands:

```bash
git diff --stat
git diff --check
git status --short
```

Acceptance:

- [x] Diff contains only scoped cleanup changes
- [x] No whitespace errors
- [x] No unrelated generated artifacts are staged or included
