# Solo Duplicate Suppression Refactor Specification

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
対象ブランチ: `dev2`
作成日: 2026-06-18
関連文書:

- `docs/semantic_epig/solo_duplicate_refactor_progress.md`
- `docs/semantic_epig/solo_duplicate_refactor_tasks.md`
- `docs/semantic_epig/refactor_spec.md`
- `docs/semantic_epig/progress.md`

---

## 1. 目的

`1girl, solo` を指定しているにもかかわらず、画像内に同一キャラクターが2体または3体へ分身する出力を減らす。

このリファクタでは、背景に他人が出る `crowd` 問題とは分けて扱う。今回の調査対象画像では、主な問題は背景人物ではなく、同一人物が複数ポーズ・複数位置に解釈される `solo duplicate` である。

---

## 2. 調査入力

ユーザー提供:

- `C:\Users\inott\Downloads\新しいフォルダー\複数人数が出現プロンプト.txt`
- `C:\Users\inott\Downloads\新しいフォルダー\新しいフォルダー\*.png`

確認した画像:

| File | 観察 | 主な誘因候補 |
|---|---|---|
| `260618-052301_00001_.png` | 同一赤髪キャラが左右に2体 | `friend approaching`, `hands moving as she talks`, lively/social mood |
| `260618-052432_00001_.png` | 鏡像ではなく同一赤髪キャラが2体 | `standing by the mirror`, `hands moving as she talks` |
| `260618-052518_00001_.png` | 同一黒髪キャラが3体 | `brushing hair in front of a mirror`, high action/garnish density |
| `260618-052649_00001_.png` | 同一白髪キャラが2体 | location-first template, multiple state clauses |
| `260618-052735_00001_.png` | 同一銀髪キャラが2体 | repeated route/ticket-gate scene anchors, lively/social mood |

---

## 3. Root Cause Model

### 3.1 Not the primary cause in these examples

The examples do not mainly show background extras such as `students`, `employees`, or `crowd`. They show the same subject repeated.

Existing `crowd` cleanup remains useful, but it is not sufficient for this failure mode.

### 3.2 Primary causes

#### A. Other-person action text passes solo safety

Examples:

- `waving to a friend approaching the cafe`
- `hands moving as she talks`
- `laughing at a friend's joke`
- `waiting for a friend`
- `talking quietly with classmates`

Problem:

- These phrases imply another person inside the scene.
- Current `core/solo_safety.py` blocks `people`, `someone`, and some `students pass` patterns, but does not block or normalize `friend`, `friends`, `classmates`, `talks`, or `talking`.

Expected behavior:

- In solo mode, social action text should be normalized to viewer-facing text or removed.

#### B. Mirror/reflection actions clone the subject

Examples:

- `standing by the mirror`
- `brushing hair in front of a mirror`
- `standing in front of a mirror, trying on clothes`
- `checking reflection in the mirrored wall`

Problem:

- Image models often render the reflection as a second full character rather than a safe reflected detail.
- This creates same-character duplication even without any explicit second person.

Expected behavior:

- In solo mode, mirror/reflection action candidates should be excluded from normal random selection or rewritten to non-reflective dressing-room/self-check phrasing.

#### C. Action/garnish/staging overload

Examples from one prompt:

```text
waving ...
holding herself ready ...
checking ...
keeping pace ...
responding to viewer ...
hands moving ...
open posture
```

Problem:

- Multiple simultaneous body/action cues can be interpreted as several instances of the same character.
- Current semantic-family budgeting reduces some near-duplicate families, but it does not enforce a single main pose/action anchor.

Expected behavior:

- In solo mode, final prompt assembly should keep one primary action plus a small number of compatible support cues.
- Social/gesture garnish should not add a second implied action when the action already contains a strong verb.

#### D. Location-first template weakens subject anchoring

Example:

```text
At the edge of pristine modern kitchen ..., a solo girl ..., wiping down ...
```

Problem:

- When the location is the sentence opener, the model may establish scene space before the subject anchor and then place the subject more than once.

Expected behavior:

- In solo mode, subject-first templates should be preferred or required.

---

## 4. Scope

### In scope

- `core/solo_safety.py`
- `pipeline/action_generator.py`
- `pipeline/prompt_orchestrator.py`
- `prompt_renderer.py`
- `vocab/garnish/logic.py`
- `mood_map.json`
- `vocab/data/personality_behavior_profiles.json`
- `vocab/data/action_pools.json`
- `vocab/source/action_pools/*.json`
- focused tests under `assets/`
- optional audit tool for solo duplicate risk phrases

### Out of scope

- Public ComfyUI node input/output changes
- Camera, lens, framing, or render-effect prompt terms
- New dependencies
- Model-side image guarantee
- Broad location redesign
- Removing explicit direct support for all mirror locations outside solo mode

---

## 5. Design Principles

1. Solo mode remains the default.
2. Do not add camera/lens terms.
3. Preserve seed determinism.
4. Preserve public node I/O.
5. Prefer normalization over deletion when the phrase has a useful solo-safe meaning.
6. Keep explicit user/direct selections possible where feasible, but remove risky terms from normal random solo selection.
7. Add tests before behavior-changing cleanup.

---

## 6. Target Behavior

### 6.1 Other-person normalization

In solo mode:

| Input pattern | Output policy |
|---|---|
| `friend approaching` | `acknowledging the viewer from her seat` or equivalent viewer-facing action |
| `talking with/to friend` | `as if responding directly to the viewer` or self-contained gesture |
| `classmates`, `friends`, `employees nearby` | reject from solo random candidate pools |
| `someone` | keep blocked as current behavior |

### 6.2 Mirror/reflection handling

In solo mode:

| Input pattern | Output policy |
|---|---|
| `standing by the mirror` | replace with `adjusting clothes near the dresser` |
| `brushing hair in front of a mirror` | replace with `brushing hair beside the vanity` |
| `checking reflection` | remove from normal pool or rewrite to `checking her appearance` |
| background mirror props | allow only when not action-centric and not combined with reflective wording |

### 6.3 Prompt assembly density

The final prompt should prefer:

```text
subject + clothing + one action + one viewer/pose cue + location
```

It should avoid:

```text
subject + action A + action B + action C + social cue + hand cue + posture cue + second scene anchor
```

### 6.4 Subject-first templates

In solo mode, prefer or require templates where `{subject_clause}` appears before `{loc}`.

Allowed:

```text
{subject_clause}, {action_clause}, the rest of the scene opening into {loc}
```

Avoid in solo mode:

```text
At the edge of {loc}, {subject_clause}, {action_clause}
In {loc}, {subject_clause}, {action_clause}
Inside {loc}, {subject_clause}, {action_clause}
```

---

## 7. Regression Fixtures

The five user-provided prompts should become regression fixtures.

Minimum assertions:

- final solo-safe prompt contains no `friend`, `friends`, `classmates`, or unsafe `someone`
- final solo-safe prompt contains no action-centric `mirror`, `mirrored`, or `reflection`
- final solo-safe prompt does not use location-first templates in solo mode
- final solo-safe prompt does not stack more than one strong action/gesture garnish after action generation
- generated debug explains which phrases were normalized or dropped

---

## 8. Verification Commands

Focused:

```bash
python -m pytest assets/test_solo_duplicate_suppression.py assets/test_action_generator.py assets/test_prompt_snapshots.py assets/test_context_content_pipeline.py -q
python tools/validate_prompt_data.py
```

Broader before commit:

```bash
python -m pytest assets/test_location_semantics.py assets/test_object_focus_service.py assets/test_location_resolution.py assets/test_workflow_diversity_analyzer.py assets/test_prompt_snapshots.py assets/test_location_alias_workflow_compat.py assets/test_context_content_pipeline.py assets/test_variation_scope.py assets/test_build_compatibility_review.py assets/test_data_consistency.py assets/test_expansion_delta.py assets/test_build_action_pools.py assets/test_action_diversity_audit.py assets/test_action_generator.py assets/test_personality_garnish.py -q
python tools/validate_prompt_data.py
python -m py_compile core/solo_safety.py pipeline/action_generator.py prompt_renderer.py vocab/garnish/logic.py
```

Manual visual check:

- Regenerate a small sample using the five regression prompts.
- Confirm the issue is no longer same-character duplication.

---

## 9. Remaining Risk

Prompt-side cleanup cannot guarantee image-side count correctness. The goal is to remove prompt patterns that strongly invite duplicate subject rendering while preserving expressive solo behavior.
