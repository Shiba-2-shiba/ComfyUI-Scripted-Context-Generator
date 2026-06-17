# Semantic EPIG Refactor Progress

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
対象ブランチ: `dev2`
作成日: 2026-06-16
関連仕様: `refactor_spec.md`
関連タスク: `refactor_tasks.md`

---

## 1. Current State

`dev2` は Semantic EPIG の5 domainが all-active で統合済み。

```text
action: active
object_relation: active
location_scene: active
clothing_tpo: active
personality_behavior: active
```

現在のリファクタ方針は、既存 active 挙動を前提に、観測性・検証性・asset schema・候補供給・builder境界を順に改善すること。

---

## 2. Baseline Verification

2026-06-16 に `dev2` 作業ツリーで確認。

| Command | Result | Notes |
|---|---|---|
| `git status --short --branch` | Pass | `## dev2...origin/dev2`, clean |
| Semantic EPIG focused unittest | Pass | 57 tests OK |
| `asset_validator.validate_assets()` | Pass | `0` issues |
| `python tools\validate_prompt_data.py` | Pass | `ERROR: []`, `WARNING: []` |
| `python tools\verify_full_flow.py` | Pass | OK |
| full unittest discovery | Incomplete | 300s timeout before completion; observed `assets/results/prompt_repetition_active_source_8.json` missing error |

Focused unittest command:

```bash
python -m unittest assets.test_semantic_space assets.test_semantic_epig assets.test_action_semantics assets.test_location_semantics assets.test_clothing_semantics assets.test_personality_semantics assets.test_action_generator assets.test_object_focus_service assets.test_personality_garnish
```

Notes:

- `assets/results/` is gitignored.
- Missing audit baseline artifacts must be treated separately from runtime failures.
- No script or runtime file was modified during this evaluation.

---

## 3. Milestone Status

| Milestone | Title | Status | Notes |
|---|---|---|---|
| R0 | Refactor docs setup | Done | `refactor_spec.md`, `refactor_progress.md`, `refactor_tasks.md` added |
| R1 | Debug meaning cleanup | Done | Added explicit scoring/change/baseline/semantic debug fields |
| R2 | Prompt-level audit tool | Done | Added active/passive prompt audit fixture, tool, and tests |
| R3 | Object relation validator | Done | Added dedicated schema validator and validation tests |
| R4 | Action descriptor candidate supply | Done | Descriptor metadata can supply slot candidates; relation-key-specific fixture remains a follow-up |
| R5 | Personality top-k context filter | Done | Ranked candidates are tried before fallback with reject debug |
| R6 | Builder responsibility split | Done | R6.1 parser, R6.2 relation binder, R6.3 renderer, R6.4 location split, and R6.5 clothing split completed |
| R7 | Final verification and docs update | Done | R6後の full verification passed; remaining follow-ups are documented |

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
| 2026-06-16 | Keep existing implementation docs unchanged | They describe the completed rollout, not the next refactor wave | Add new `refactor_*` docs |
| 2026-06-16 | Do debug/audit before builder split | Output changes must be explainable before moving code | R1/R2 precede R6 |
| 2026-06-16 | Keep all-active config as current baseline | `dev2` is already all-active | Refactor should observe current behavior, not silently disable domains |
| 2026-06-16 | Treat full unittest artifact failure separately | `assets/results/` is ignored and may be absent | Do not confuse missing baseline JSON with runtime failure |
| 2026-06-16 | Complete R1-R5 before structural split | Debug, audit, validation, candidate supply, and top-k personality behavior are now covered by focused tests | R6 can start from a clearer behavior baseline |

---

## 5. Findings From Review

### 5.1 Confirmed strengths

- Semantic EPIG common foundation exists and is tested.
- Domain-specific semantic modules exist:
  - `pipeline/action_semantics.py`
  - `pipeline/location_semantics.py`
  - `pipeline/clothing_semantics.py`
  - `vocab/personality_semantics.py`
- Object relation integration exists in `object_focus_service.py` and `pipeline/action_generator.py`.
- Public node surface remains context-first.
- `validate_assets()` reports no issues.

### 5.2 Resolved risks

| Initial risk | Resolution |
|---|---|
| `selected_by_semantic` had ambiguous meaning | R1 added explicit scoring/change/baseline/semantic debug fields |
| No prompt-level active/passive audit | R2 added audit fixtures, tool, and tests |
| Object relation validator was shallow | R3 added dedicated `object_relation_profiles.json` structure validation |
| Action EPIG mostly reweighted existing options | R4 added descriptor-backed candidate supply |
| Personality context arguments were underused | R5 added ranked candidate stream and context rejection before fallback |
| Builders were large and mixed responsibilities | R6 split parser, relation binder, renderer, location policy/selector, and clothing candidate renderer/selector |

### 5.3 Remaining follow-ups

| Follow-up | Status |
|---|---|
| Relation-key-specific action descriptor fixture/test | Open; matcher supports `relation_keys`, but no dedicated relation-key descriptor case was added |
| Broader docs (`README.md`, `CURRENT_STATUS.md`) | Updated with refactor doc entry points and current verification snapshot |
| Ignored audit artifacts under `assets/results/` | Generated locally as needed; intentionally not tracked |

---

## 6. Cleanup Plan

Scope:

- Semantic EPIG debug payloads
- Semantic EPIG audit support
- Semantic EPIG asset validation
- Action / Personality semantic selection internals
- Builder split only after behavior is locked

Order:

1. R1: Debug meaning cleanup
2. R2: Prompt-level audit
3. R3: Object relation validator
4. R4: Action descriptor candidate supply
5. R5: Personality top-k context filter
6. R6: Builder split
7. R7: Final verification and docs

Out of scope for this refactor wave:

- Public node I/O changes
- New dependencies
- Image generation evaluation loop
- ComfyUI workflow schema changes
- Broad vocabulary expansion unrelated to Semantic EPIG

---

## 7. Implementation Log

### 7.1 R1 Debug meaning cleanup

- Added shared Semantic EPIG selection debug fields.
- Split "semantic scoring is enabled" from "semantic changed the selected output".
- Added slot/section/attempt/candidate-level debug for action, location, clothing, and personality.

Verification:

- `python -m py_compile pipeline\semantic_epig.py pipeline\action_semantics.py pipeline\action_generator.py pipeline\location_semantics.py pipeline\location_builder.py pipeline\clothing_semantics.py pipeline\clothing_builder.py vocab\personality_semantics.py vocab\garnish\logic.py`
- `python -m unittest assets.test_semantic_epig assets.test_action_semantics assets.test_action_generator assets.test_location_semantics assets.test_context_content_pipeline assets.test_clothing_semantics assets.test_personality_semantics assets.test_personality_garnish`

### 7.2 R2 Prompt-level audit

- Added `assets/fixtures/semantic_epig_audit_cases.json`.
- Added `tools/audit_semantic_epig_outputs.py`.
- Added deterministic audit tests.

Verification:

- `python -m unittest assets.test_semantic_epig_audit`
- `python tools\audit_semantic_epig_outputs.py --samples assets\fixtures\semantic_epig_audit_cases.json --seed-start 0 --seed-count 1 --output assets\results\semantic_epig_audit_smoke.json`

### 7.3 R3 Object relation validator

- Added dedicated `validate_object_relation_profiles()`.
- Connected object relation schema validation into `validate_semantic_epig_assets()`.
- Added malformed-schema tests.

Verification:

- `python -m unittest assets.test_asset_validator assets.test_object_focus_service`
- `asset_validator.validate_assets()` returns `0` issues.

### 7.4 R4 Action descriptor candidate supply

- Added descriptor option matching by purpose/action/object/relation metadata.
- Added descriptor-supplied action slot candidates without changing public node I/O.
- Added focused action semantic/generator tests.

Verification:

- `python -m unittest assets.test_action_semantics assets.test_action_generator assets.test_asset_validator`
- `asset_validator.validate_assets()` returns `0` issues.

Remaining R4 note:

- The function supports `relation_keys`, but a dedicated relation-key descriptor fixture/test remains open.

### 7.5 R5 Personality top-k context filter

- Added ranked personality candidate stream.
- Added reject callback support before fallback.
- Added debug for rejected candidates, fallback, and selected candidate rank.

Verification:

- `python -m unittest assets.test_personality_semantics assets.test_personality_garnish assets.test_emotion_vad_alignment`
- `python -m unittest assets.test_semantic_epig_audit`

### 7.6 R6.1 Action parser split

- Added `pipeline/action_parser.py`.
- Moved active action text extraction, verb parsing, phrase normalization, contextual clause splitting, and pool action slot parsing out of `action_generator.py`.
- Kept `pipeline.action_generator` public imports compatible by delegating `action_text()`, `action_verb()`, and `parse_pool_action_to_slots()`.
- Removed the old parser constants/helpers from `action_generator.py`.

Verification:

- `python -m py_compile pipeline\action_parser.py pipeline\action_generator.py`
- `python -m unittest assets.test_action_generator assets.test_action_semantics assets.test_object_focus_service`

### 7.7 R6.2 Action relation binder split

- Added `pipeline/action_relation_binder.py`.
- Moved object relation slot application and relation debug assembly out of `action_generator.py`.
- Kept object relation behavior unchanged: active mode can fill missing role slots, existing slots are skipped rather than overwritten.
- Added direct binder coverage for preserving existing slots while still applying missing object state.

Verification:

- `python -m py_compile pipeline\action_relation_binder.py pipeline\action_generator.py`
- `python -m unittest assets.test_action_generator assets.test_object_focus_service`

### 7.8 R6.3 Action renderer split

- Added `pipeline/action_renderer.py`.
- Moved `render_action_slots()` and clause append/dedupe behavior out of `action_generator.py`.
- Kept `pipeline.action_generator.render_action_slots()` as a compatibility entry point.
- Added direct renderer coverage for clause order, dedupe, `activity_first`, and `append_clause()`.

Verification:

- `python -m py_compile pipeline\action_renderer.py pipeline\action_generator.py`
- `python -m unittest assets.test_action_generator`
- `python -m unittest assets.test_action_generator assets.test_action_semantics assets.test_object_focus_service assets.test_context_pipeline assets.test_context_content_pipeline assets.test_prompt_snapshots`

### 7.9 R6.4 Location selector/policy split

- Added `pipeline/location_policy.py`.
- Added `pipeline/location_segment_selector.py`.
- Moved lighting/off-mode filtering, FX deny filtering, daily-life/time/weather policy, and weighted segment selection out of `location_builder.py`.
- Kept `expand_location_prompt()` flow unchanged and preserved existing semantic debug/ranking behavior.
- Added direct policy/selector tests for lighting filtering, FX allow/deny behavior, semantic score weighting, and deterministic semantic choice.

Verification:

- `python -m py_compile pipeline\location_policy.py pipeline\location_segment_selector.py pipeline\location_builder.py`
- `python -m unittest assets.test_location_semantics assets.test_context_content_pipeline assets.test_fx_cleanup assets.test_bias_controls assets.test_determinism`

### 7.10 R6.5 Clothing candidate renderer/selector split

- Added `pipeline/clothing_candidate_renderer.py`.
- Added `pipeline/clothing_candidate_selector.py`.
- Moved clothing candidate rendering, state-detail hard filters, outerwear location policy, repeat penalty, and TPO candidate selection out of `clothing_builder.py`.
- Kept `expand_clothing_prompt()` public behavior and debug payload assembly in `clothing_builder.py`.
- Added direct renderer/selector tests for state-detail location filtering and repeat/TPO score reporting.

Verification:

- `python -m py_compile pipeline\clothing_candidate_renderer.py pipeline\clothing_candidate_selector.py pipeline\clothing_builder.py`
- `python -m unittest assets.test_clothing_semantics assets.test_context_content_pipeline assets.test_context_state_adapter assets.test_determinism`

### 7.11 Full unittest discovery snapshot

2026-06-16 local run:

- First `python -m unittest discover -s assets -p "test_*.py"` timed out at 300s and exposed missing ignored artifact `assets/results/prompt_repetition_active_source_8.json`.
- Regenerated ignored audit artifacts:
  - `python tools\audit_prompt_repetition.py --samples-per-row 8 --output assets\results\prompt_repetition_active_source_8.json --enforce-thresholds`
  - `python tools\audit_template_diversity.py --seed-count 32 --seed-start 0 --output assets\results\template_diversity_32.json --enforce-thresholds`
- Updated `assets/fixtures/prompt_snapshot_cases.json` to match the current R4/R5 active semantic outputs.
- Final `python -m unittest discover -s assets -p "test_*.py"` result: 326 tests OK in 564.325s.

### 7.12 R7 Final verification

2026-06-16 local run after R6.5:

| Command | Result |
|---|---|
| `python -m unittest discover -s assets -p "test_*.py"` | Pass: 334 tests OK in 559.021s |
| `python tools\validate_prompt_data.py` | Pass: `ERROR: []`, `WARNING: []` |
| `python tools\verify_full_flow.py` | Pass |
| `python tools\check_widgets_values.py` | Pass |
| `python assets\calc_variations.py --json` | Pass |
| `asset_validator.validate_assets()` | Pass: `0` issues |
| `python -m unittest assets.test_prompt_snapshots assets.test_context_pipeline assets.test_context_state_adapter assets.test_determinism` | Pass: 16 tests OK |
| `python -m unittest assets.test_repetition_guard_audit` | Pass: 5 tests OK |

R7 remaining follow-ups:

- R4 relation-key-specific descriptor fixture/test remains open because the matcher supports `relation_keys` but no dedicated relation-key descriptor case was added.
- Generated audit artifacts under `assets/results/` remain ignored and are not part of the diff.

---

## 8. Verification Notes

Before each implementation pass:

```bash
python -m unittest assets.test_semantic_space assets.test_semantic_epig assets.test_action_semantics assets.test_location_semantics assets.test_clothing_semantics assets.test_personality_semantics assets.test_action_generator assets.test_object_focus_service assets.test_personality_garnish
```

Before claiming full completion:

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python assets/calc_variations.py --json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

If full unittest fails due to ignored audit artifacts, regenerate or record the artifact gap explicitly:

```bash
python tools/audit_prompt_repetition.py --samples-per-row 8 --output assets/results/prompt_repetition_active_source_8.json --enforce-thresholds
python tools/audit_template_diversity.py --seed-count 32 --seed-start 0 --output assets/results/template_diversity_32.json --enforce-thresholds
```
