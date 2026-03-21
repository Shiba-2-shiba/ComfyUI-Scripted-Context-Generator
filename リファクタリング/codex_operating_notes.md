# Codex Operating Notes

## Recommended working mode

Run Codex in small PR-oriented sessions.
Each session should target one task from `codex_task_set.md`.

Preferred execution order for the current refactor:

1. `TASK-M18-01` Add a repetition audit for staging, garnish, and final prompts
2. `TASK-M18-02` Add focused regression coverage for deterministic staging selection
3. `TASK-M19-01` Sample `staging_tags` instead of appending full fixed lists
4. `TASK-M19-02` Add cross-layer semantic-family dedupe and budgets
5. `TASK-M20-01` Rework high-frequency `mood_map` staging and descriptions
6. `TASK-M20-02` Review calm-heavy source defaults outside `mood_map`

## Session input template

Use this exact structure when starting a Codex task:

1. Goal
2. Files allowed to change
3. Files not allowed to change
4. Acceptance criteria
5. Validation commands
6. Compatibility constraints
7. Output format required

## Example session prompt

> Work on `TASK-M19-02` from `codex_task_set.md`.
> Goal: add semantic-family-aware repetition controls so action, mood text, staging, and garnish stop stacking the same cue in one prompt.
> You may modify: the shared semantic helper you introduce, `pipeline/context_pipeline.py`, `pipeline/mood_builder.py`, `prompt_renderer.py`, `vocab/garnish/logic.py`, and related tests.
> Do not modify: public node class names, workflow sample content, or prompt policy constraints.
> Acceptance criteria: the fix is phrase-agnostic, deterministic, covered by focused tests, and the repetition audit improves against baseline.
> Validation: run py_compile on touched modules, run focused semantic-family tests, rerun the repetition audit, then run the full `assets` suite.
> Return: summary, changed files, validation results, compatibility impact, audit delta, and follow-up tasks.

## Guardrails for Codex

- Prefer structural fixes over phrase-by-phrase edits.
- Do not patch only `calm breathing` unless a task explicitly calls for temporary triage.
- Preserve prompt safety and determinism while changing staging or dedupe behavior.
- Keep `pipeline/content_pipeline.py` available as the intentional compatibility facade.
- Keep prompt-renderer diagnostics opt-in; do not restore default file logging.
- Do not reintroduce pytest cache noise or other avoidable workspace artifacts in the default validation path.
- Keep shared fragment sanitization in `core.semantic_policy`, prompt assembly cleanup as a thin delegating layer, and `PromptCleaner` as final user-facing polish.
- Prefer semantic-family controls such as `breath`, `gaze`, `posture`, `hands`, and `smile/mouth` over literal string blacklists.
- Audit before and after changing prompt-surface behavior; do not tune by anecdote alone.
- Do not reintroduce camera/framing/style language into public prompt output.
- Do not add new workflow surfaces during this refactor unless explicitly requested.
