# Codex Temporary Exceptions

As of 2026-03-21, the M14 runtime-side-effect and hygiene cleanup has closed the two newest operational exceptions:

- default prompt-renderer file logging is no longer active
- the repo-local pytest cache warning/noise pattern is no longer part of the default validation path

Only intentional operating constraints remain below.

## Active workflow fixture policy

- only `ComfyUI-workflow-context.json` is treated as an active workflow fixture.
  - Rationale: the repository still supports one active public workflow surface only.
  - Exit: add another fixture only if a new public workflow surface is intentionally introduced.

## Historical artifact note

- `simple_template_debug.log` may still exist in old worktrees from pre-M14 runs.
  - Rationale: the runtime no longer writes to it by default, but old generated files are not automatically deleted by this refactor.
  - Exit: manual cleanup can happen separately when the user wants to remove historical generated artifacts.

- old `pytest-cache-files-*` directories may still exist from pre-M14 local runs.
  - Rationale: repo config now prevents the current warning/noise pattern, but historical transient directories are not automatically deleted by this refactor.
  - Exit: manual cleanup can happen separately when the user wants a fully cleaned workspace.

## Current baseline

- `python -m pytest assets -q`: `222 passed`, `161 subtests passed`, `0 warnings`
- `asset_validator.validate_assets()`: `0` warnings
- official workflow analyzer (`32` runs): `32 / 32` unique prompts, `runs_with_warnings = 0`
- template audit baseline remains `31` unique templates and `2` action-surface categories (`gerund = 21`, `framed = 11`)
- repetition guard saved artifacts still report `avg_recent4_costume_signature_repeat_rate = 0.0` for both `seed_start = 0` and `seed_start = 40`

## Current boundary note

- shared fragment sanitization now lives in `core.semantic_policy`
  - Rationale: banned-term removal and compact punctuation cleanup should stay consistent across runtime assembly and validation-facing helpers.
  - Exit: keep `PromptCleaner` focused on final user-facing polish only; do not rebuild a second shared sanitization layer there.
