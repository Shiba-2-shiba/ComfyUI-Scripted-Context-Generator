# Solo Duplicate Suppression Refactor Tasks

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
対象ブランチ: `dev2`
作成日: 2026-06-18
関連仕様: `solo_duplicate_refactor_spec.md`
関連進捗: `solo_duplicate_refactor_progress.md`

---

## 0. Common Instructions

Use these rules for every task in this refactor wave.

- Do not change public `Context*` node inputs or outputs.
- Do not add dependencies.
- Do not add camera, lens, framing, or render-effect terms.
- Keep solo mode as the default.
- Preserve seed determinism.
- Add regression tests before behavior-changing edits.
- Keep each pass scoped to one smell category.
- Prefer vocabulary normalization over broad deletion.
- Run focused verification after each pass.

Focused verification:

```bash
python -m pytest assets/test_solo_duplicate_suppression.py assets/test_action_generator.py assets/test_prompt_snapshots.py assets/test_context_content_pipeline.py -q
python tools/validate_prompt_data.py
```

Broad verification before commit:

```bash
python -m pytest assets/test_location_semantics.py assets/test_object_focus_service.py assets/test_location_resolution.py assets/test_workflow_diversity_analyzer.py assets/test_prompt_snapshots.py assets/test_location_alias_workflow_compat.py assets/test_context_content_pipeline.py assets/test_variation_scope.py assets/test_build_compatibility_review.py assets/test_data_consistency.py assets/test_expansion_delta.py assets/test_build_action_pools.py assets/test_action_diversity_audit.py assets/test_action_generator.py assets/test_personality_garnish.py -q
python tools/validate_prompt_data.py
python -m py_compile core/solo_safety.py pipeline/action_generator.py prompt_renderer.py vocab/garnish/logic.py
```

---

## SD0. Documentation Setup

### SD0.1 Add refactor documentation

Files:

```text
docs/semantic_epig/solo_duplicate_refactor_spec.md
docs/semantic_epig/solo_duplicate_refactor_progress.md
docs/semantic_epig/solo_duplicate_refactor_tasks.md
```

Acceptance:

- [x] Supplied prompts/images are summarized
- [x] Root cause is separated from background `crowd`
- [x] Implementation order is documented
- [x] Verification commands are documented

---

## SD1. Behavior Lock

### SD1.1 Add supplied prompt regression fixture

Files:

```text
assets/fixtures/solo_duplicate_prompt_cases.json
assets/test_solo_duplicate_suppression.py
```

Requirements:

- Store the five supplied prompt examples as regression inputs.
- Include metadata for the observed image filename and suspected risk categories.
- Keep this test prompt-side; do not require image generation.

Acceptance:

- [x] Fixture contains all five supplied prompts
- [x] Test identifies risks in current prompts before normalization
- [x] Test is deterministic

### SD1.2 Add solo duplicate risk scanner

Files:

```text
core/solo_safety.py
assets/test_solo_duplicate_suppression.py
```

Requirements:

- Add a function that classifies prompt fragments into risk families:
  - `other_person`
  - `social_talk`
  - `mirror_clone`
  - `multi_action_density`
  - `location_first_template`
- Keep existing `is_solo_safe_text()` behavior backward-compatible until SD2/SD3 decide how each risk is enforced.

Acceptance:

- [x] `friend approaching` is classified as `other_person`
- [x] `hands moving as she talks` is classified as `social_talk`
- [x] `standing by the mirror` is classified as `mirror_clone`
- [x] `At the edge of {loc}` template is classified as `location_first_template`

---

## SD2. Solo Safety Taxonomy

### SD2.1 Extend people/social patterns

Files:

```text
core/solo_safety.py
assets/test_solo_duplicate_suppression.py
assets/test_action_generator.py
```

Requirements:

- Add explicit patterns for:
  - `friend`
  - `friends`
  - `classmates`
  - `companion`
  - unsafe `talks`, `talking`, `chatting`, `conversation`
- Distinguish phrases that can be normalized from phrases that must be rejected.

Acceptance:

- [x] Normal random solo action selection does not emit `friend/friends/classmates`
- [x] Viewer-facing social clauses remain allowed
- [x] Existing tests for viewer normalization still pass

### SD2.2 Add mirror/reflection risk patterns

Files:

```text
core/solo_safety.py
assets/test_solo_duplicate_suppression.py
```

Requirements:

- Add risk patterns for action-centric:
  - `mirror`
  - `mirrored wall`
  - `reflection`
  - `reflections`
- Do not globally delete harmless non-action reflective texture unless it is used as an action anchor.

Acceptance:

- [x] `standing by the mirror` is not solo-random-safe
- [x] `brushing hair in front of a mirror` is not solo-random-safe
- [x] non-action location texture can be handled separately by tests and policy

---

## SD3. Action Pool Normalization

### SD3.1 Normalize friend/talk action candidates

Files:

```text
vocab/source/action_pools/*.json
vocab/data/action_pools.json
pipeline/action_generator.py
assets/test_action_generator.py
assets/test_solo_duplicate_suppression.py
```

Requirements:

- Replace or normalize unsafe social action text in normal solo pools.
- Candidate rewrites should preserve the scene intent without adding another visible person.

Examples:

| Current | Solo-safe replacement |
|---|---|
| `waving to a friend approaching the cafe` | `waving lightly toward the viewer from the cafe table` |
| `laughing at a friend's joke` | `holding back a laugh while meeting the viewer's eyes` |
| `waiting for a friend near the fountain` | `waiting near the fountain with her attention toward the viewer` |
| `talking quietly with classmates over lunch` | `quietly collecting her thoughts over lunch` |

Acceptance:

- [x] `action_pools.json` and source action pool data remain consistent
- [x] solo random action generation does not emit unsafe social target text
- [x] direct viewer-facing alternatives are still expressive

### SD3.2 Normalize mirror action candidates

Files:

```text
vocab/source/action_pools/*.json
vocab/data/action_pools.json
assets/test_solo_duplicate_suppression.py
```

Requirements:

- Replace high-risk mirror actions in normal solo action pools.

Examples:

| Current | Solo-safe replacement |
|---|---|
| `standing by the mirror, adjusting clothes` | `adjusting clothes beside the dresser` |
| `brushing hair in front of a mirror` | `brushing hair beside the vanity` |
| `checking reflection in the mirrored wall` | `checking her appearance before moving on` |

Acceptance:

- [x] normal solo generation avoids action-centric `mirror/reflection`
- [x] location identity remains intact where possible

---

## SD4. Garnish and Mood Density Control

### SD4.1 Remove social-talk garnish from solo random output

Files:

```text
mood_map.json
vocab/garnish/logic.py
vocab/data/personality_behavior_profiles.json
assets/test_personality_garnish.py
assets/test_solo_duplicate_suppression.py
```

Requirements:

- Replace `hands moving as she talks` with a solo-safe gesture.
- Ensure energetic/cheerful mood does not imply an off-screen interlocutor unless normalized to viewer-facing.

Candidate replacements:

```text
one hand lifted mid-gesture
hands moving with excitement
bright smile with an easy stance
```

Acceptance:

- [x] energetic garnish no longer emits `talks`
- [x] cheerful/energetic output remains visually expressive

### SD4.2 Cap action/garnish/staging stack in solo mode

Files:

```text
prompt_renderer.py
vocab/garnish/logic.py
assets/test_solo_duplicate_suppression.py
assets/test_prompt_snapshots.py
```

Requirements:

- Prevent final prompts from stacking multiple strong action/gesture cues.
- Prefer one main action plus at most one support cue from gesture/posture.
- Preserve existing semantic-family budget where it already works.

Acceptance:

- [x] supplied prompt fixtures produce compact solo-safe prompt text
- [x] prompt snapshots are updated intentionally if outputs change
- [x] debug shows dropped or suppressed garnish/staging tags

---

## SD5. Solo Template Filtering

### SD5.1 Prefer subject-first templates in solo mode

Files:

```text
prompt_renderer.py
vocab/data/template_catalog.json
assets/test_solo_duplicate_suppression.py
assets/test_prompt_snapshots.py
```

Requirements:

- In solo mode, filter or heavily penalize templates where location appears before subject.
- Keep non-solo behavior unchanged if possible.

Avoid in solo mode:

```text
At the edge of {loc}, {subject_clause}, {action_clause}
In {loc}, {subject_clause}, {action_clause}
Inside {loc}, {subject_clause}, {action_clause}
```

Acceptance:

- [x] solo composition chooses subject-first templates
- [x] regression prompt 4 no longer starts with `At the edge of`
- [x] template selection remains deterministic

### SD5.2 Add prompt debug for solo template filtering

Files:

```text
prompt_renderer.py
assets/test_solo_duplicate_suppression.py
```

Requirements:

- Record whether solo template filtering was applied.
- Record filtered template keys when practical.

Acceptance:

- [x] debug payload exposes solo template filtering
- [x] tests assert filtering behavior without relying on random image output

---

## SD6. Audit and Validation

### SD6.1 Add solo duplicate risk audit tool

Files:

```text
tools/audit_solo_duplicate_risk.py
assets/test_solo_duplicate_suppression.py
```

Requirements:

- Scan `prompts.jsonl`, `vocab/data/action_pools.json`, mood/garnish data, and prompt snapshot fixtures.
- Report risk families:
  - `other_person`
  - `social_talk`
  - `mirror_clone`
  - `location_first_template`
  - `multi_action_density`

Acceptance:

- [x] Tool returns JSON report
- [x] Known risky fixture cases are detected
- [ ] Post-cleanup report has no high-risk normal solo candidates

Note: Existing `crowd/people/someone` and routine-artifact candidates are still reported by the audit because they remain in action pools and are suppressed by runtime solo filtering. Removing or rewriting those is a separate background-extra cleanup follow-up.

### SD6.2 Update progress docs

Files:

```text
docs/semantic_epig/solo_duplicate_refactor_progress.md
```

Acceptance:

- [x] Milestone statuses are current
- [x] Verification log includes commands and results
- [x] Remaining risks are documented

---

## SD7. Final Verification

### SD7.1 Run focused verification

Acceptance:

- [x] `python -m pytest assets/test_solo_duplicate_suppression.py assets/test_action_generator.py assets/test_prompt_snapshots.py assets/test_context_content_pipeline.py -q` passes
- [x] `python tools/validate_prompt_data.py` passes

### SD7.2 Run broad verification

Acceptance:

- [x] broad pytest command from section 0 passes
- [x] py_compile command from section 0 passes
- [x] no unrelated files are changed

### SD7.3 Manual visual smoke test

Requirements:

- Regenerate a small sample from the five supplied cases.
- Compare against original failure class.

Acceptance:

- [ ] No obvious same-character duplicate in reviewed sample
- [ ] If a duplicate remains, record prompt text and suspected risk family in progress doc

---

## Deferred Follow-ups

- Background `crowd` term cleanup for true background extras.
- Optional negative prompt hints, if the workflow owner wants to change negative prompt policy later.
- Broader mirror policy for non-solo mode.
