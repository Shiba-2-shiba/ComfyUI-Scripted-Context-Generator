# Codex Refactor Spec

## 1. Purpose

The next refactor targets prompt-surface repetition rather than architecture cleanup.
Recent investigation confirmed that `calm breathing` is only the most visible symptom of a broader issue: fixed staging tags and repeated semantic cues are injected across multiple layers, making a small set of moods dominate the final prompt surface.

This round should reduce repeated semantics structurally, not by patching one phrase at a time.

## 2. Current confirmed state

- `python -m pytest assets -q` last known baseline remains green at `222 passed` and `161 subtests passed`
- `asset_validator.validate_assets()` remains at `0` warnings
- `python tools/analyze_context_workflow_diversity.py --runs 32 --seed-start 0` last known baseline remains warning-clean
- `mood_map.json` stores `staging_tags` as fixed full lists, not sampled subsets
- `pipeline/mood_builder.py` joins every `staging_tag` into one string and returns the full set on every call
- `prompt_renderer.py` appends `staging_tags` wholesale to the final prompt when present
- active prompt-source distribution is calm-heavy: `quiet_focused = 27 / 105` and `peaceful_relaxed = 28 / 105`
- end-to-end reconstruction on the active prompt source produced breath-family language in `62 / 105` prompts
- the same reconstruction produced `calm breathing` in `27 / 105` prompts and `slow breath` in `28 / 105` prompts
- repeated final-surface tags are not limited to breath terms; `still posture`, `focused expression`, `gentle smile`, `soft gaze`, `loose hands`, and related tags also appear at high rates

## 3. Business goal

Make the generated prompt surface feel more varied and less overdetermined by a few mood defaults by tightening four things:

1. fixed mood staging should no longer inject the same full tag bundle every time
2. repeated semantic cues should be constrained across `action`, `meta_mood`, `staging_tags`, and `garnish`
3. calm-heavy vocabulary should stop dominating simply because it is the default path
4. prompt-diversity regressions should become measurable instead of anecdotal

## 4. Main design goals

### G1. Staging must be sampled, not always fully appended
`staging_tags` should behave like a deterministic seed-driven pool, not a mandatory full suffix.

### G2. Semantic repetition must be controlled across layers
The system should reason about semantic families such as `breath`, `gaze`, `posture`, `hands`, and `smile/mouth`, then avoid stacking near-duplicate cues from multiple sources.

### G3. Fixes must be phrase-agnostic
The implementation must not special-case only `calm breathing`. It should reduce the same failure mode for other repeated tags and future vocabulary.

### G4. Mood vocabulary must stop forcing physiological cues
Common moods such as `quiet_focused` and `peaceful_relaxed` should not require breath-language on every prompt.

### G5. Repetition must be observable
The repository should expose audit output and regression checks for high-frequency tags and semantic-family incidence.

## 5. Explicit scope for this refactor

In scope:

- add prompt-surface repetition audits for staging, garnish, and final prompts
- introduce semantic-family grouping for repeated surface cues
- sample `staging_tags` instead of appending full lists
- add cross-layer semantic-family dedupe or budgets
- rebalance `mood_map.json` descriptions and staging tags where they force repeated cues
- review calm-heavy defaults in source data where they materially amplify repetition
- add regression coverage for determinism and repetition controls
- document the new repetition-control operating model under `リファクタリング/`

Deferred from this round:

- broad workflow redesign
- new public nodes or workflow surfaces
- major changes to prompt composition templates unless repetition controls prove insufficient
- unrelated service-boundary or diagnostics cleanup that is already complete

## 6. Hard invariants

### Prompt invariants
- final prompts must remain free of banned `style`, `quality`, `camera`, `render`, and `body_type` domains
- `meta.style` remains legacy read-only metadata
- repetition controls must not introduce broken grammar or conflicting body cues

### Runtime invariants
- `nodes_context.py` and `nodes_prompt_cleaner.py` public node classes must remain loadable
- `ComfyUI-workflow-context.json` remains the active workflow sample
- same seed and same inputs remain deterministic even after staging sampling and semantic budgeting

### Evaluation invariants
- `python -m pytest assets -q` must continue to pass
- `asset_validator.validate_assets()` must remain at zero warnings
- workflow diversity analysis must remain warning-clean on the active sample

## 7. Repository risks to address

### R1. Fixed staging over-injection
`mood_map.json` currently behaves like a hard-coded suffix list for common moods.

### R2. Cross-layer semantic duplication
The same idea can appear in `description`, `staging_tags`, and `garnish` without any family-aware suppression.

### R3. Calm-default amplification
Even when a phrase is not hard-coded directly, calm-heavy mood distribution and fallback logic still bias the output surface.

### R4. Phrase-by-phrase patch drift
Hand-removing `calm breathing` alone would leave `slow breath`, `focused expression`, `still posture`, and future equivalents untouched.

### R5. Weak observability
The repo currently requires manual prompt reading to discover these issues, which makes regressions easy to miss.

## 8. Preferred implementation direction

### D1. Audit first
Establish explicit counters for repeated tags, semantic families, and per-mood fixed outputs before changing runtime behavior.

### D2. Sample deterministic subsets
Prefer seed-driven subset selection for `staging_tags` rather than joining the entire list every time.

### D3. Budget by semantic family
Prefer reusable semantic-family helpers that can say "we already have a breath cue" or "we already have a gaze cue" across all prompt layers.

### D4. Rebalance data after controls exist
Change `mood_map.json` and calm-heavy source data after structural controls are in place so the data cleanup is guided by measurable outputs.

### D5. Keep fixes general
Prefer family-level and duplication-level rules over phrase blacklist patches whenever possible.

## 9. Target architecture after this refactor

### Mood expansion path
- `mood_builder` returns a deterministic sampled staging subset rather than a full fixed bundle
- mood descriptions and staging tags no longer force the same physiological cue on every sample

### Prompt assembly path
- prompt assembly can reason about semantic overlap between `action`, `meta_mood`, `staging_tags`, and `garnish`
- repeated families are capped or suppressed before final assembly

### Vocabulary path
- `mood_map.json` uses more varied, less forced staging language
- common moods are not structurally required to emit breath cues

### Validation path
- audits report top repeated tags and family incidence for staging, garnish, and final prompts
- regression checks can fail when fixed-tag repetition grows back

## 10. Acceptance criteria by end state

### A. Functional acceptance
- `staging_tags` are sampled deterministically rather than appended as full fixed lists
- no common mood forces a single staging tag into every output sample by construction
- repetition controls operate on semantic families, not only on one literal phrase

### B. Maintainability acceptance
- semantic-family logic has a single clear owner rather than being reimplemented ad hoc
- `mood_map.json` and runtime controls have a documented contract for how much staging can surface
- the operating docs explain how to audit and tune repetition safely

### C. Quality acceptance
- `quiet_focused` and `peaceful_relaxed` no longer force breath-family language through fixed staging bundles
- the repository exposes repeat-rate metrics for tags and semantic families on the active prompt source
- `python -m pytest assets -q` passes
- `asset_validator.validate_assets()` stays at zero
- `python tools/analyze_context_workflow_diversity.py --runs 32 --seed-start 0` remains warning-clean

## 11. Required test strategy

### Unit tests
- staging subset sampling determinism
- semantic-family classification and dedupe behavior
- per-layer overlap suppression for repeated cues

### Integration tests
- active workflow sample execution through the prompt path with repetition controls enabled
- focused node/path tests for `mood_builder`, `context_pipeline`, and `prompt_renderer`

### Regression checks
- full `assets` pytest run
- asset validator
- workflow diversity analyzer
- repetition audit baseline on the active prompt source

## 12. Milestones

### M18. Repetition observability and guardrails
- add auditable counters for high-frequency tags and semantic families
- lock in deterministic behavior for any new staging-selection helper

### M19. Runtime repetition controls
- sample `staging_tags` instead of appending full lists
- add cross-layer semantic-family budgets and dedupe

### M20. Vocabulary and source-data rebalance
- rewrite high-frequency mood staging and description phrasing that forces repeated cues
- reduce calm-heavy source defaults where audits show structural overrepresentation

## 13. Definition of done

This refactor is done when:

- repeated prompt-surface cues are constrained structurally rather than patched one phrase at a time
- fixed mood staging no longer injects the same full semantic bundle every run
- repetition audits exist and are part of the maintenance workflow
- calm-heavy moods no longer force breath-language as a default surface
- `python -m pytest assets -q` still passes
- `asset_validator.validate_assets()` stays at zero
