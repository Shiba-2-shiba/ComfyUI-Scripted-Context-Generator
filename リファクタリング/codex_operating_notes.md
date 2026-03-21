# Codex Operating Notes

## Recommended working mode

Run Codex in small PR-oriented sessions.
Each session should target one task from `codex_task_set.md`.

Preferred execution order for the current refactor:

1. No active Ready tasks. `TASK-M18-01` remains deferred unless a new session confirms that one generation module is still too dense to maintain safely.

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

> Work on `TASK-M15-01` from `codex_task_set.md`.
> Goal: reduce implementation ownership inside `registry.py` so it behaves like a real compatibility facade rather than a second loader layer.
> You may modify: `registry.py`, `location_service.py`, `character_service.py`, and related tests.
> Do not modify: public node class names, workflow sample content, or prompt policy constraints.
> Acceptance criteria: compatibility callers still work, service ownership becomes clearer, and the full `assets` suite remains green.
> Validation: run py_compile on touched modules, run focused registry/resolver tests, then run the full `assets` suite.
> Return: summary, changed files, validation results, compatibility impact, and follow-up tasks.

## Guardrails for Codex

- Prefer measured cleanup over broad redesign.
- Preserve prompt safety and determinism while tightening architecture.
- Keep `pipeline/content_pipeline.py` available as the intentional compatibility facade.
- Keep prompt-renderer diagnostics opt-in; do not restore default file logging.
- Do not reintroduce pytest cache noise or other avoidable workspace artifacts in the default validation path.
- Keep shared fragment sanitization in `core.semantic_policy`, prompt assembly cleanup as a thin delegating layer, and `PromptCleaner` as final user-facing polish.
- Do not reintroduce camera/framing/style language into public prompt output.
- Do not add new workflow surfaces during this refactor unless explicitly requested.
