# Repository Cleanup Refactor Progress

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
対象ブランチ: `dev2`
作成日: 2026-06-19
関連仕様: `spec.md`
関連タスク: `tasks.md`

---

## 1. Current State

このリファクタは完了。

対象範囲:

- heavy audit separation
- `assets/` responsibility cleanup
- compatibility facade boundary guardrails
- empty placeholder deletion

実装変更は R1-R4 まで完了した。

---

## 2. Baseline Findings

2026-06-19 に `dev2` 作業ツリーで確認。

| Check | Result | Notes |
|---|---|---|
| `git status --short --branch` | Pass | `## dev2...origin/dev2`, clean |
| tracked files | Info | 427 files |
| `assets/results/` tracking | Needs cleanup | `.gitignore` 対象だが `assets/results/baseline_20260215_083827.json` が tracked |
| empty placeholders | Needs cleanup | 4 tracked `vocab/*/test.md` files |
| focused solo/location/vocab/mood unittest | Pass | 31 tests OK |
| `tools/validate_prompt_data.py` | Pass | `ERROR: []`, `WARNING: []` |
| `assets/calc_variations.py --json` | Pass | `103,212` base variations |
| `tools/check_variation_scope.py` | Pass | `120 subjects / 90 locations / 5,806 rows` |
| `tools/build_action_pools.py --check` | Pass | `ERROR: []`, `WARNING: []` |
| `tools/build_compatibility_review.py --check` | Pass | `ERROR: []`, `WARNING: []` |
| repetition guard default audit unittest | Timeout | one test exceeded 60 seconds |

Timeout command:

```bash
python -m unittest assets.test_repetition_guard_audit.TestRepetitionGuardAudit.test_repetition_guard_thresholds_pass_for_default_audit
```

This is treated as a test-organization issue, not as a runtime correctness failure.

---

## 3. Milestone Status

| Milestone | Title | Status | Notes |
|---|---|---|---|
| R0 | Refactor docs setup | Done | `spec.md`, `progress.md`, `tasks.md` added |
| R1 | Behavior lock and heavy audit split | Done | Long repetition guard checks are explicit CLI audits; unit tests use short inputs |
| R2 | `assets/` responsibility cleanup | Done | Ignored results policy documented; tracked generated baseline removed |
| R3 | Compatibility facade guardrails | Done | Runtime facade imports removed and boundary test added |
| R4 | Empty placeholder deletion | Done | Four tracked `vocab/*/test.md` placeholders removed |
| R5 | Final docs and verification | Done | Final gate passed |

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
| 2026-06-19 | Keep this refactor behavior-preserving | User requested repository cleanup/refactor, not generation changes | Prompt output and node I/O stay unchanged |
| 2026-06-19 | Split heavy audit before moving files | Need a trustworthy normal test loop before structural cleanup | R1 precedes R2-R4 |
| 2026-06-19 | Prefer small ownership clarifications over broad directory moves | Moving all tests out of `assets/` could create noisy import churn | Large relocation is optional and must be justified |
| 2026-06-19 | Treat compatibility facades as supported surfaces until guarded | They preserve old imports and workflow compatibility | Do not delete facades in this wave |
| 2026-06-19 | Delete empty placeholders only after reference search | They are likely inert, but tracked references must be checked | R4 includes an explicit pre-delete check |

---

## 5. Open Risks

### 5.1 Full unittest discovery cost

Full discovery may remain slow even after repetition guard split if other audit-style tests exist.

Mitigation:

- identify remaining slow tests after R1
- split each one into short unittest plus explicit audit CLI
- record expected long audit commands separately

### 5.2 File move churn

Moving tests or scripts out of `assets/` can break imports and docs links.

Mitigation:

- prefer ownership documentation first
- move only files with clear destination and low import risk
- run discovery immediately after each move

### 5.3 Tracked generated baseline handling

`assets/results/baseline_20260215_083827.json` is tracked while the directory is ignored.

Mitigation options:

- move it to `assets/fixtures/` if it is a required regression fixture
- delete it if unused and reproducible
- document why it remains tracked if neither move nor deletion is safe

### 5.4 Compatibility facade caller detection

Static import scanning can produce false positives in docs, tests, archives, or facade files themselves.

Mitigation:

- maintain an explicit allowlist
- ignore docs/archive paths in the boundary test
- keep `assets/test_deprecated_behavior.py` as the intentional compatibility test owner

---

## 6. Implementation Log

### R0. Refactor docs setup

Planned files:

```text
docs/repository_cleanup/spec.md
docs/repository_cleanup/progress.md
docs/repository_cleanup/tasks.md
```

Acceptance:

- [x] Scope covers the four user-selected cleanup areas
- [x] Non-goals protect prompt generation and public node I/O
- [x] Task order starts with behavior lock and heavy audit split
- [x] Verification gates are explicit

### R1. Behavior lock and heavy audit split

- Recorded pre-change baseline checks.
- Replaced `assets/test_repetition_guard_audit.py` 32x8 threshold unittest with 8x2 unit windows.
- Kept the 32x8 threshold audit available through:

```bash
python tools/audit_repetition_guard.py --step-count 32 --scenario-count 8 --seed-start 0 --enforce-thresholds
python tools/audit_repetition_guard.py --step-count 32 --scenario-count 8 --seed-start 40 --enforce-thresholds
```

Verification:

- `python -m unittest assets.test_repetition_guard_audit`: 5 tests OK in 12.251s
- `python tools/audit_repetition_guard.py --help`: Pass

### R2. `assets/` responsibility cleanup

- Replaced generated-artifact comparison tests with unit report structure checks:
  - `assets/test_prompt_repetition_audit.py`
  - `assets/test_template_diversity_audit.py`
- Kept long prompt/template audit generation as explicit CLI commands under `tools/`.
- Removed unused tracked generated artifact:
  - `assets/results/baseline_20260215_083827.json`
- Updated `CURRENT_STATUS.md` and `REPO_STRUCTURE.md` with the generated-output policy.

Verification:

- `python -m unittest assets.test_prompt_repetition_audit assets.test_template_diversity_audit assets.test_repetition_guard_audit`: 14 tests OK

### R3. Compatibility facade guardrails

- Added `assets/test_compatibility_boundaries.py`.
- Added boundary contracts to:
  - `pipeline/content_pipeline.py`
  - `background_vocab.py`
  - `clothing_vocab.py`
  - `improved_pose_emotion_vocab.py`
- Replaced repo-owned runtime imports of compatibility facades with narrower package imports:
  - `pipeline/clothing_candidate_renderer.py` imports `vocab.clothing`
  - `pipeline/context_pipeline.py` imports `vocab.garnish`
  - `pipeline/location_builder.py` imports `vocab.background`

Verification:

- `python -m unittest assets.test_compatibility_boundaries assets.test_deprecated_behavior assets.test_registry assets.test_context_content_pipeline`: 38 tests OK
- `python -m py_compile pipeline\clothing_candidate_renderer.py pipeline\context_pipeline.py pipeline\location_builder.py assets\test_compatibility_boundaries.py`: Pass

### R4. Empty placeholder deletion

- Confirmed the placeholder references were only in this cleanup plan.
- Removed:
  - `vocab/background/test.md`
  - `vocab/clothing/test.md`
  - `vocab/data/test.md`
  - `vocab/garnish/test.md`

Verification:

- `python tools/validate_prompt_data.py`: `ERROR: []`, `WARNING: []`
- `python -m unittest assets.test_vocab_lint assets.test_data_consistency`: 6 tests OK

---

## 7. Verification Notes

Last known focused checks before this plan:

```bash
python tools/validate_prompt_data.py
python assets/calc_variations.py --json
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --check
python -m unittest assets.test_solo_duplicate_suppression assets.test_location_semantics assets.test_vocab_lint assets.test_mood_builder
```

Known result:

- prompt data validator: `ERROR: []`, `WARNING: []`
- base variations: `103,212`
- variation scope: `120 subjects / 90 locations / 5,806 rows`
- focused unittest: `31 tests OK`

Known gap:

- `git diff --check` reports only existing LF -> CRLF working-copy warnings, no whitespace errors.

### R5. Final docs and verification

- Updated active docs:
  - `CURRENT_STATUS.md`
  - `REPO_STRUCTURE.md`
  - `docs/repository_cleanup/progress.md`
  - `docs/repository_cleanup/tasks.md`
- Ran final verification gate.

Verification:

| Command | Result |
|---|---|
| `python -m unittest discover -s assets -p "test_*.py"` | Pass: 394 tests OK in 181.220s |
| `python tools/validate_prompt_data.py` | Pass: `ERROR: []`, `WARNING: []` |
| `python tools/verify_full_flow.py` | Pass |
| `python tools/check_widgets_values.py` | Pass |
| `python tools/check_variation_scope.py` | Pass: 120 subjects / 90 locations / 5,806 rows / 103,212 base variations |
| `python tools/build_action_pools.py --check` | Pass: `ERROR: []`, `WARNING: []` |
| `python tools/build_compatibility_review.py --check` | Pass: `ERROR: []`, `WARNING: []` |
| `python assets/calc_variations.py --json` | Pass: 103,212 base variations |
| `asset_validator.validate_assets()` | Pass: 0 issues |
| `git diff --check` | Pass: LF -> CRLF warnings only |
