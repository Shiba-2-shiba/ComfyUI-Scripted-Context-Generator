# Codex Task Set

This task set covers the post-M13 follow-up refactor.
The focus is operational and architectural: reduce runtime side effects, tighten service ownership, consolidate duplicated heuristics, and clean up repository validation noise.

---

## Milestone M14 — Runtime side-effect and hygiene cleanup

### TASK-M14-01 Make prompt-renderer debug logging opt-in
**Goal**
Stop `prompt_renderer.py` from attaching a file logger during normal imports while preserving an explicit maintainer path for deep diagnostics.

**Files**
- `prompt_renderer.py`
- focused tests under `assets/`
- docs under `リファクタリング/` and public docs only if behavior needs to be surfaced

**Acceptance**
- importing `prompt_renderer.py` does not create or append a debug log by default
- maintainers can still enable file logging intentionally through an explicit switch
- prompt rendering behavior remains deterministic and policy-safe

**Validation**
- `python -m py_compile prompt_renderer.py assets/test_prompt_renderer.py`
- `python -m pytest assets/test_prompt_renderer.py -q`
- `python -m pytest assets -q`

**Codex prompt**
> Make `prompt_renderer.py` stop writing debug logs by default. Keep diagnostics available behind an explicit opt-in, add regression coverage for the default quiet behavior, and preserve prompt determinism.

---

### TASK-M14-02 Stabilize pytest cache behavior and ignore transient artifacts
**Goal**
Prevent the current repo-local pytest cache warning/noise pattern and keep transient cache output out of code review.

**Files**
- `pytest.ini`
- `.gitignore`
- related docs under `リファクタリング/`

**Acceptance**
- normal local `python -m pytest assets -q` runs no longer emit the current cache warning
- transient cache directories are ignored by git
- no test discovery or asset paths regress

**Validation**
- `python -m pytest assets -q`
- `git status --short`

**Codex prompt**
> Clean up the repo-local pytest cache behavior so validation runs stop producing the current warning/noise pattern. Keep the change small, local to repo config, and compatible with the existing test suite.

---

## Milestone M15 — Registry and service-boundary cleanup

### TASK-M15-01 Slim `registry.py` into a real compatibility facade
**Goal**
Reduce implementation ownership inside `registry.py` by forwarding more loading and resolution behavior to the service modules that already own the data.

**Files**
- `registry.py`
- `location_service.py`
- `character_service.py`
- any focused tests under `assets/`

**Acceptance**
- `registry.py` becomes materially thinner
- service modules remain the source of truth for loading and resolution behavior
- compatibility APIs exposed by `registry.py` keep working

**Validation**
- `python -m py_compile registry.py location_service.py character_service.py`
- focused pytest for registry and resolver behavior
- `python -m pytest assets -q`

**Codex prompt**
> Refactor `registry.py` into a thinner compatibility surface by pushing ownership back to `location_service.py` and `character_service.py`. Preserve all current compatibility behavior and update focused regression tests in the same change.

---

### TASK-M15-02 Add regression coverage for service-boundary expectations
**Goal**
Lock in the intended ownership split once `registry.py` is thinned.

**Files**
- `assets/test_registry.py`
- other focused resolver tests if needed

**Acceptance**
- tests prove compatibility callers still work
- tests make service/facade ownership clearer instead of only checking happy-path values

**Validation**
- `python -m pytest assets/test_registry.py -q`

**Codex prompt**
> After slimming `registry.py`, add targeted regression coverage so future edits do not rebuild a second implementation layer inside the facade.

---

## Milestone M16 — Shared heuristic consolidation

### TASK-M16-01 Centralize object-focus helpers and policy access
**Goal**
Reduce duplicated object extraction and concentration-policy logic across `action_generator`, `location_builder`, and related helpers.

**Files**
- `pipeline/action_generator.py`
- `pipeline/location_builder.py`
- `history_service.py`
- new shared helper module only if it clearly reduces duplication
- focused tests under `assets/`

**Acceptance**
- duplicated object-focus logic is materially reduced
- policy access has a single clear owner
- diversity behavior stays deterministic

**Validation**
- `python -m py_compile` on touched modules
- focused pytest for touched helpers
- `python -m pytest assets -q`

**Codex prompt**
> Consolidate shared object-focus and concentration-policy helpers so runtime modules stop carrying near-duplicate logic. Keep behavior deterministic and update focused tests with the refactor.

---

## Milestone M17 — Text normalization boundary cleanup

### TASK-M17-01 Clarify shared sanitization versus final cleaning
**Goal**
Make it easier to reason about what belongs in `core.semantic_policy`, prompt assembly normalization, and `PromptCleaner`.

**Files**
- `core/semantic_policy.py`
- `prompt_renderer.py`
- `nodes_prompt_cleaner.py`
- focused tests under `assets/`

**Acceptance**
- shared sanitization and final cleaning have a clearer contract
- overlapping cleanup logic is reduced where practical
- policy safety remains unchanged

**Validation**
- `python -m py_compile core/semantic_policy.py prompt_renderer.py nodes_prompt_cleaner.py`
- focused pytest for touched tests
- `python -m pytest assets -q`

**Codex prompt**
> Tighten the boundary between shared sanitization, prompt assembly normalization, and `PromptCleaner` so the cleanup flow is easier to maintain. Preserve public behavior and add focused regression coverage.

---

## Deferred work

### TASK-M18-01 Split oversized generation modules further
**Status**
Deferred unless M15-M17 leave a single module too dense to maintain safely.

**Reason**
Module splitting should follow ownership cleanup, not precede it.

**Codex prompt**
> Deferred. Do not start module-splitting work until the service-boundary and shared-helper refactors have clarified where the code should live.
