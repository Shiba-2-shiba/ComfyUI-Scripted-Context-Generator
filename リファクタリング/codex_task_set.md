# Codex Task Set

This task set covers the prompt-repetition refactor that follows the completed M14-M17 maintenance cleanup.
The focus is structural prompt-surface variation: reduce fixed staging injection, prevent semantic-family stacking, and make repetition measurable.

---

## Milestone M18 — Repetition observability and guardrails

### TASK-M18-01 Add a repetition audit for staging, garnish, and final prompts
**Goal**
Create a repeatable audit that measures high-frequency tags, semantic-family incidence, and per-mood fixed outputs on the active prompt source.

**Files**
- `tools/` audit scripts
- `pipeline/` helper modules only if the audit needs shared parsing logic
- focused tests under `assets/`
- docs under `リファクタリング/`

**Acceptance**
- the repo can report top repeated staging tags, garnish tags, and final-surface tags
- the audit reports semantic-family counts such as `breath`, `gaze`, `posture`, `hands`, and `smile/mouth`
- the audit can show when a mood forces the same tag into every sample

**Validation**
- `python -m py_compile` on touched audit/helpers
- focused pytest for the new audit helpers
- run the repetition audit on the active prompt source

**Codex prompt**
> Add a repetition audit that measures high-frequency tags and semantic-family incidence across staging, garnish, and final prompt output. Keep the audit deterministic and make the report useful for tuning future changes.

---

### TASK-M18-02 Add focused regression coverage for deterministic staging selection
**Goal**
Lock in the expected deterministic behavior before runtime repetition controls start changing prompt content.

**Files**
- `pipeline/mood_builder.py`
- focused tests under `assets/`

**Acceptance**
- tests make the current or newly introduced staging-selection contract explicit
- seed-driven behavior remains deterministic
- the tests are precise enough to catch accidental reintroduction of fixed full-list injection

**Validation**
- `python -m py_compile pipeline/mood_builder.py`
- `python -m pytest` for touched staging tests

**Codex prompt**
> Add focused regression coverage around `mood_builder` so deterministic staging selection is locked in before the repetition-control refactor changes runtime behavior.

---

## Milestone M19 — Runtime repetition controls

### TASK-M19-01 Sample `staging_tags` instead of appending full fixed lists
**Goal**
Stop `mood_map` staging from behaving like a mandatory five-tag suffix on every prompt.

**Files**
- `pipeline/mood_builder.py`
- `prompt_renderer.py`
- `pipeline/prompt_orchestrator.py` if needed
- focused tests under `assets/`

**Acceptance**
- staging uses a deterministic seed-driven subset rather than the full list
- prompt rendering keeps working when staging is absent, partial, or reordered
- no seed/determinism regressions are introduced

**Validation**
- `python -m py_compile pipeline/mood_builder.py prompt_renderer.py pipeline/prompt_orchestrator.py`
- focused pytest for touched modules
- `python -m pytest assets -q`

**Codex prompt**
> Refactor staging injection so `mood_map` no longer appends the full `staging_tags` list on every prompt. Use a deterministic sampled subset, preserve prompt assembly behavior, and cover the change with focused tests.

---

### TASK-M19-02 Add cross-layer semantic-family dedupe and budgets
**Goal**
Prevent the same semantic idea from being emitted repeatedly across `action`, `meta_mood`, `staging_tags`, and `garnish`.

**Files**
- shared helper module under `core/` or `pipeline/`
- `pipeline/context_pipeline.py`
- `pipeline/mood_builder.py`
- `prompt_renderer.py`
- `vocab/garnish/logic.py`
- focused tests under `assets/`

**Acceptance**
- semantic families have a single clear owner
- repeated families can be detected and suppressed before final assembly
- the fix is phrase-agnostic and not limited to `calm breathing`

**Validation**
- `python -m py_compile` on touched runtime modules
- focused pytest for semantic-family behavior
- `python -m pytest assets -q`
- run the repetition audit and compare to the recorded baseline

**Codex prompt**
> Add semantic-family-aware repetition controls across action, mood text, staging, and garnish so near-duplicate cues stop stacking in the final prompt. Keep the design general rather than special-casing one phrase.

---

## Milestone M20 — Vocabulary and source-data rebalance

### TASK-M20-01 Rework high-frequency `mood_map` staging and descriptions
**Goal**
Reduce forced physiological and posture cues in common moods, especially where the audit shows fixed repeated outputs.

**Files**
- `mood_map.json`
- focused tests or audit fixtures under `assets/`
- docs under `リファクタリング/`

**Acceptance**
- `quiet_focused` and `peaceful_relaxed` stop forcing breath-family language through static staging bundles
- mood descriptions and staging tags avoid needless overlap within the same mood entry
- audits show improved per-mood variety after the data update

**Validation**
- relevant lint/validation tests for `mood_map.json`
- repetition audit on the active prompt source
- `python -m pytest assets -q`

**Codex prompt**
> Rework the high-frequency `mood_map` entries so common moods stop forcing repeated breath/posture cues. Keep the language policy-safe, seed-deterministic, and backed by the repetition audit.

---

### TASK-M20-02 Review calm-heavy source defaults outside `mood_map`
**Goal**
Reduce structural calm bias that remains after runtime repetition controls are in place.

**Files**
- `prompts.jsonl`
- `vocab/data/action_pools.json`
- `vocab/garnish/logic.py`
- related audit/tests under `assets/` and `tools/`

**Acceptance**
- calm-heavy defaults are reduced only where audits show material amplification
- no single fallback path recreates the same overrepresented surface
- diversity improvements do not break compatibility or determinism

**Validation**
- focused tests for touched source-data/runtime modules
- repetition audit on the active prompt source
- `python -m pytest assets -q`
- `python tools/analyze_context_workflow_diversity.py --runs 32 --seed-start 0`

**Codex prompt**
> After runtime repetition controls are in place, review calm-heavy source defaults in prompt data, action pools, and garnish logic. Reduce structural calm bias only where the audit shows it materially affects the final prompt surface.

---

## Deferred work

### TASK-M21-01 Revisit template-catalog weighting only if repetition remains template-driven
**Status**
Deferred unless M18-M20 show that semantic repetition is no longer the main problem and template weighting is the remaining source of sameness.

**Reason**
The current evidence points to fixed staging and semantic stacking before template selection, so template redesign should not lead this refactor.

**Codex prompt**
> Deferred. Do not start template-catalog or composition redesign until repetition audits show that staging and semantic-family controls are no longer the main bottleneck.
