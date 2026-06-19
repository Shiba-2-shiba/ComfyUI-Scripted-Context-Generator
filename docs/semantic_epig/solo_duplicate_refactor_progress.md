# Solo Duplicate Suppression Refactor Progress

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
対象ブランチ: `dev2`
作成日: 2026-06-18
関連仕様: `solo_duplicate_refactor_spec.md`
関連タスク: `solo_duplicate_refactor_tasks.md`

---

## 1. Current State

`dev2` currently includes the background clutter cleanup commit:

```text
fc16811 Reduce background clutter in generated scene prompts
```

After that cleanup, user-provided examples show `1girl, solo` prompts producing multiple instances of the same character. The observed issue is not primarily background extras; it is same-character duplication.

---

## 2. Evidence Summary

Input file:

```text
C:\Users\inott\Downloads\新しいフォルダー\複数人数が出現プロンプト.txt
```

Image folder:

```text
C:\Users\inott\Downloads\新しいフォルダー\新しいフォルダー
```

Observed image files:

| File | Result | Notes |
|---|---|---|
| `260618-052301_00001_.png` | 2 same red-haired subjects | Prompt includes `friend approaching`, `hands moving as she talks` |
| `260618-052432_00001_.png` | 2 same red-haired subjects | Prompt includes `standing by the mirror` |
| `260618-052518_00001_.png` | 3 same black-haired subjects | Prompt includes `brushing hair in front of a mirror` |
| `260618-052649_00001_.png` | 2 same platinum subjects | Prompt uses location-first template |
| `260618-052735_00001_.png` | 2 same silver-haired subjects | Prompt has route/ticket scene anchors plus energetic mood |

---

## 3. Findings

### 3.1 Prior crowd hypothesis is insufficient

The earlier hypothesis that `crowd` options such as `teacher supervising`, `small groups`, or `students` were the main cause does not match these images.

Those terms still deserve cleanup, but they do not explain the five supplied failures.

### 3.2 Stronger explanation

The common failure pattern is one subject receiving multiple competing anchors:

- social target: `friend`, `talks`
- reflection target: `mirror`, `reflection`
- motion/gesture stack: `waving`, `checking`, `hands moving`, `open posture`
- weak subject anchoring: location-first templates

This can cause the image model to place the same subject multiple times.

### 3.3 Current solo safety gap

`core/solo_safety.py` currently blocks:

- `crowd*`
- `people`
- `someone`
- selected `students pass/passing`
- `passing by/through`

It does not block or normalize:

- `friend`
- `friends`
- `classmates`
- `talks`
- `talking`
- `mirror`
- `mirrored`
- `reflection`

---

## 4. Milestone Status

| Milestone | Title | Status | Notes |
|---|---|---|---|
| SD0 | Documentation setup | Done | Spec/progress/tasks docs added |
| SD1 | Regression fixtures | Done | Five supplied prompts captured in `assets/fixtures/solo_duplicate_prompt_cases.json` |
| SD2 | Solo risk taxonomy | Done | Added other-person, social-talk, mirror-clone, density, and location-first risk detection |
| SD3 | Action pool normalization | Done | Rewrote friend/talk/mirror candidates to viewer-facing or self-contained phrasing |
| SD4 | Garnish/staging density control | Done | Replaced social-talk garnish and compacted solo support cues in prompt assembly |
| SD5 | Solo template filtering | Done | Solo composition filters location-first templates |
| SD6 | Audit and verification | In progress | Audit tool added; broad verification still pending |

Status vocabulary:

- `Not started`
- `In progress`
- `Blocked`
- `Done`
- `Deferred`

---

## 5. Decision Log

| Date | Decision | Reason | Impact |
|---|---|---|---|
| 2026-06-18 | Treat this as `solo duplicate`, not generic multi-person | Images show same-character clones | Tests should inspect clone-inducing prompt text, not only `crowd` terms |
| 2026-06-18 | Keep viewer-facing strategy | It preserves interpersonal expression without adding another visible person | Friend/talk phrases should normalize to viewer/self-contained phrasing |
| 2026-06-18 | Handle mirror/reflection separately | Mirrors can duplicate the subject even with no other person | Mirror actions need exclusion or solo-safe rewrites |
| 2026-06-18 | Subject-first templates are part of solo safety | Location-first prompts weaken one-subject anchoring | Prompt renderer should filter templates when solo mode is active |

---

## 6. Cleanup Plan

Scope:

- solo safety text classification
- action pool solo filtering/normalization
- garnish/staging solo density
- prompt template selection in solo mode
- regression tests and focused audits

Order:

1. Lock the five supplied prompts as regression cases.
2. Add explicit solo duplicate risk classification.
3. Normalize or reject unsafe social action phrases.
4. Normalize or reject mirror/reflection action phrases.
5. Reduce action/garnish/staging stacking in solo mode.
6. Filter location-first templates in solo mode.
7. Run focused and broad verification.

Out of scope:

- Camera/lens additions
- Public node I/O changes
- New dependencies
- Full image-count guarantee

---

## 7. Verification Log

| Command | Result | Notes |
|---|---|---|
| `python -m pytest assets\test_solo_duplicate_suppression.py -q` | Pass | 8 tests, 15 subtests |
| `python -m pytest assets\test_solo_duplicate_suppression.py assets\test_action_generator.py assets\test_personality_garnish.py -q` | Pass | 38 tests, 39 subtests |
| `python -m pytest assets\test_solo_duplicate_suppression.py assets\test_prompt_snapshots.py assets\test_context_content_pipeline.py -q` | Pass | 34 tests, 31 subtests |
| `python -m pytest assets\test_solo_duplicate_suppression.py assets\test_action_generator.py assets\test_prompt_snapshots.py assets\test_context_content_pipeline.py assets\test_personality_garnish.py assets\test_build_action_pools.py assets\test_action_diversity_audit.py -q` | Pass | 73 tests, 55 subtests |
| `python -m pytest assets\test_location_semantics.py assets\test_object_focus_service.py assets\test_location_resolution.py assets\test_workflow_diversity_analyzer.py assets\test_prompt_snapshots.py assets\test_location_alias_workflow_compat.py assets\test_context_content_pipeline.py assets\test_variation_scope.py assets\test_build_compatibility_review.py assets\test_data_consistency.py assets\test_expansion_delta.py assets\test_build_action_pools.py assets\test_action_diversity_audit.py assets\test_action_generator.py assets\test_personality_garnish.py assets\test_solo_duplicate_suppression.py -q` | Pass | 118 tests, 61 subtests |
| `python tools\validate_prompt_data.py` | Pass | `ERROR: []`, `WARNING: []` |
| `python -m py_compile core\solo_safety.py pipeline\action_generator.py prompt_renderer.py vocab\garnish\logic.py` | Pass | syntax check |
| `python tools\audit_solo_duplicate_risk.py` | Pass | reports fixture risks plus runtime-filtered existing action candidates |

Pending:

- Manual ComfyUI visual smoke test.

---

## 8. Open Questions

| Question | Current answer |
|---|---|
| Should explicit mirror actions be fully removed? | No. Remove from normal solo random selection or rewrite; keep direct support where possible. |
| Should all `talk` phrases be banned? | No. Convert solo-safe cases to viewer-facing or self-contained phrasing. |
| Should `crowd` cleanup continue? | Yes, but it is secondary for the supplied examples. |
| Should visual QA be mandatory before commit? | Recommended for this issue because prompt tests cannot guarantee rendered count. |

---

## 9. Implementation Log

### 9.1 SD1-SD2 risk detection

- Added `assets/fixtures/solo_duplicate_prompt_cases.json`.
- Added `assets/test_solo_duplicate_suppression.py`.
- Added risk-family classification in `core/solo_safety.py`.
- Added action-specific solo safety through `is_solo_action_safe_text()`.

### 9.2 SD3 action/garnish vocabulary normalization

- Replaced `friend`, `classmates`, `talking`, `mirror`, and `reflection` action candidates in source and generated action pools.
- Replaced `hands moving as she talks` with `one hand lifted mid-gesture`.
- Toned down energetic mood descriptions that encouraged multi-pose interpretation.

### 9.3 SD4-SD5 prompt assembly safeguards

- Added solo support-cue compaction in `prompt_renderer.py`.
- Added solo template filtering for location-first templates.
- Added prompt debug fields for dropped solo support tags and filtered template keys.

### 9.4 SD6 audit support

- Added `tools/audit_solo_duplicate_risk.py`.
- The audit currently reports known fixture risks and existing action-pool candidates that runtime solo filtering suppresses.
