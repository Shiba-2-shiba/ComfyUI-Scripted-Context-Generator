# Codex Refactor Spec

## 1. Purpose

The M9-M13 refactor is complete and the repository is healthy again.
The next refactor is narrower and more operational: remove runtime side effects that do not belong in the default node path, tighten service boundaries that still blur compatibility and implementation concerns, and consolidate duplicated heuristics before they drift.

This round starts from a green baseline and targets maintainability rather than feature expansion.

## 2. Current confirmed state

- `python -m pytest assets -q` passes with `211 passed` and `161 subtests passed`
- `asset_validator.validate_assets()` returns `0`
- `python tools/analyze_context_workflow_diversity.py --runs 32 --seed-start 0` remains warning-clean with `32 / 32` unique prompts
- `pipeline/content_pipeline.py` is already reduced to an intentional compatibility facade
- `prompt_renderer.py` still configures debug file logging at import time unless explicitly changed
- repository-local test runs have produced noisy `pytest` cache warnings and transient `pytest-cache-files-*` artifacts in the project root
- `registry.py` still owns data loading and compatibility helpers beyond a thin facade role
- object-focus and normalization heuristics still live in more than one module

## 3. Business goal

Make the repository easier to operate and extend safely by tightening four things:

1. default runtime behavior should be quiet and side-effect free
2. compatibility facades should not keep accumulating implementation ownership
3. shared heuristics should live in one place instead of drifting across modules
4. repository-local validation should stay clean without creating avoidable workspace noise

## 4. Main design goals

### G1. Default prompt rendering must not write files
`prompt_renderer.py` should only emit debug file logs when a maintainer explicitly opts in.

### G2. Compatibility modules must stay thin
`registry.py` and the remaining facades should describe stable compatibility surfaces, not become a second implementation layer with their own caches and loaders.

### G3. Shared object/policy heuristics must be single-sourced
Object-flag extraction and concentration-policy lookups should not be duplicated across `action_generator`, `location_builder`, and history helpers.

### G4. Text normalization boundaries must be explicit
`semantic_policy`, prompt assembly normalization, and `PromptCleaner` should each own a distinct layer of cleanup instead of overlapping unpredictably.

### G5. Validation runs should leave less incidental debris
The repo should not generate avoidable cache warnings or untracked temporary directories during normal local validation.

## 5. Explicit scope for this refactor

In scope:

- make prompt-renderer debug logging opt-in
- stabilize pytest cache behavior and ignore transient cache artifacts
- slim `registry.py` toward a real compatibility facade
- extract or centralize duplicated object-focus helpers where practical
- clarify normalization boundaries between shared sanitization and final cleaning
- add regression coverage for any new compatibility or logging behavior

Deferred from this round:

- broad prompt-surface redesign beyond the completed M10 work
- new workflow surfaces
- new vocabulary expansion unless a later task proves it is needed
- removal of compatibility facades that are still part of the external surface

## 6. Hard invariants

### Prompt invariants
- final prompts must remain free of banned `style`, `quality`, `camera`, `render`, and `body_type` domains
- `meta.style` remains legacy read-only metadata
- public node UI must not regrow deprecated controls

### Runtime invariants
- `nodes_context.py` and `nodes_prompt_cleaner.py` public node classes must remain loadable
- `ComfyUI-workflow-context.json` remains the active workflow sample
- same seed and same inputs remain deterministic

### Evaluation invariants
- `python -m pytest assets -q` must continue to pass
- `asset_validator.validate_assets()` must remain at zero warnings
- workflow diversity analysis must remain warning-clean on the active sample

## 7. Repository risks to address

### R1. Import-time logging side effects
`prompt_renderer.py` currently behaves like a diagnostic script even when imported as runtime code.

### R2. Facade creep
`registry.py` still owns enough implementation detail that future cleanup risks circular coupling or source-of-truth confusion.

### R3. Heuristic drift
Object-focus logic and policy lookups are duplicated across modules, making future tuning harder to reason about.

### R4. Normalization drift
Multiple cleanup passes exist, but the boundary between policy sanitization, prompt assembly, and final text cleaning is not sharp enough.

### R5. Repository hygiene noise
Pytest cache warnings and transient cache directories add noise to validation and code review.

## 8. Preferred implementation direction

### D1. Make diagnostics explicit
Prefer environment-gated or helper-gated debug logging over import-time file handlers.

### D2. Move ownership to service modules
Prefer `location_service.py`, `character_service.py`, and other service modules as the owners of data loading and resolution logic. Keep `registry.py` as a compatibility forwarding surface.

### D3. Centralize shared heuristics
Prefer a single helper module or clearly owned service for object flags and concentration-policy reads rather than repeated local copies.

### D4. Separate sanitization from cleanup
Prefer `semantic_policy` for banned-term and shared sanitization rules, prompt assembly for structural composition, and `PromptCleaner` for final user-facing cleanup.

### D5. Keep validation local and quiet
Prefer repository config that prevents avoidable cache warnings rather than relying on users to ignore them.

## 9. Target architecture after this refactor

### Runtime diagnostics path
- default prompt rendering writes no debug file
- maintainers can still enable deep logging intentionally

### Compatibility path
- `registry.py` is thin and forwards to service-owned loaders/resolvers
- service modules own caches and source-of-truth knowledge

### Shared heuristic path
- object-focus helpers are not duplicated across multiple runtime modules
- policy-driven weighting reads from one shared path

### Normalization path
- shared sanitization and final cleaning are easier to reason about and test independently

### Validation path
- normal local pytest runs avoid the current cache warning noise

## 10. Acceptance criteria by end state

### A. Functional acceptance
- prompt rendering no longer attaches file logging by default
- repo-local validation no longer emits the current pytest cache warning under the default workflow
- compatibility callers keep working while implementation ownership moves toward service modules

### B. Maintainability acceptance
- `registry.py` is materially thinner than the current post-M13 state
- object/policy helper duplication is reduced or explicitly centralized
- normalization responsibilities are documented and regression-tested

### C. Quality acceptance
- `python -m pytest assets -q` passes
- `asset_validator.validate_assets()` stays at zero
- `python tools/analyze_context_workflow_diversity.py --runs 32 --seed-start 0` remains warning-clean

## 11. Required test strategy

### Unit tests
- prompt-renderer logging default behavior
- compatibility facade behavior that must remain stable
- any extracted object-focus or normalization helpers

### Integration tests
- active workflow sample execution through the analyzer
- focused node/path tests for touched runtime modules

### Regression checks
- full `assets` pytest run
- asset validator
- workflow diversity analyzer

## 12. Milestones

### M14. Runtime side-effect and hygiene cleanup
- remove default prompt-renderer file logging
- stabilize pytest cache behavior
- document the new default diagnostic behavior

### M15. Registry and service-boundary cleanup
- reduce implementation ownership inside `registry.py`
- keep compatibility behavior stable while moving loaders/resolvers to services

### M16. Shared heuristic consolidation
- centralize object-focus helpers and policy access
- reduce duplicated classification logic across runtime modules

### M17. Text normalization boundary cleanup
- tighten the contract between shared sanitization, assembly normalization, and final cleaning
- add regression coverage that makes the separation explicit

## 13. Definition of done

This refactor is done when:

- runtime prompt rendering is quiet by default
- validation runs are clean enough that cache noise is no longer part of normal operation
- compatibility facades stay available but no longer blur source-of-truth ownership
- duplicated heuristics are reduced to a defensible boundary
- `python -m pytest assets -q` still passes
- `asset_validator.validate_assets()` stays at zero
