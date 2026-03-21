# Codex Temporary Exceptions

As of 2026-03-21, the completed M14-M17 maintenance cleanup remains in effect, but a new temporary exception is now active:

- prompt-surface repetition is still structurally over-injected by fixed mood staging and cross-layer semantic duplication

This exception is the reason for the new M18-M20 refactor plan.

## Active workflow fixture policy

- only `ComfyUI-workflow-context.json` is treated as an active workflow fixture.
  - Rationale: the repository still supports one active public workflow surface only.
  - Exit: add another fixture only if a new public workflow surface is intentionally introduced.

## Active repetition exception

- `mood_map.json` still behaves like a fixed staging suffix for common moods.
  - Rationale: `pipeline/mood_builder.py` currently joins full `staging_tags`, and `prompt_renderer.py` appends them wholesale.
  - Exit: close this exception once `TASK-M19-01` samples deterministic staging subsets and `TASK-M19-02` adds semantic-family repetition controls.

- calm-heavy moods still force repeated surface cues into the final prompt path.
  - Rationale: `quiet_focused` and `peaceful_relaxed` currently account for `55 / 105` active prompt rows, and their staging/descriptions contribute directly to repeated `breath`, `gaze`, `posture`, and `hands` cues.
  - Exit: close this exception once `TASK-M20-01` and `TASK-M20-02` reduce forced repeated vocabulary after runtime controls are in place.

## Historical artifact note

- `simple_template_debug.log` may still exist in old worktrees from pre-M14 runs.
  - Rationale: the runtime no longer writes to it by default, but old generated files are not automatically deleted by completed maintenance work.
  - Exit: manual cleanup can happen separately when the user wants to remove historical generated artifacts.

- old `pytest-cache-files-*` directories may still exist from pre-M14 local runs.
  - Rationale: repo config now prevents the old warning/noise pattern, but historical transient directories are not automatically deleted by completed maintenance work.
  - Exit: manual cleanup can happen separately when the user wants a fully cleaned workspace.

## Current baseline

- `python -m pytest assets -q`: `222 passed`, `161 subtests passed`, `0 warnings`
- `asset_validator.validate_assets()`: `0` warnings
- official workflow analyzer (`32` runs): `32 / 32` unique prompts, `runs_with_warnings = 0`
- active prompt-source rows with breath-family language in end-to-end reconstruction: `62 / 105`
- active prompt-source rows with `calm breathing`: `27 / 105`
- active prompt-source rows with `slow breath`: `28 / 105`
- high-frequency final-surface tags also include `still posture`, `focused expression`, `gentle smile`, `soft gaze`, `loose hands`, and `careful hands`

## Current boundary note

- shared fragment sanitization now lives in `core.semantic_policy`
  - Rationale: banned-term removal and compact punctuation cleanup should stay consistent across runtime assembly and validation-facing helpers.
  - Exit: keep `PromptCleaner` focused on final user-facing polish only; do not rebuild a second shared sanitization layer there.

- the next repetition fix must be family-aware rather than phrase-specific
  - Rationale: `calm breathing` is only one instance of the broader fixed-staging and cross-layer duplication pattern.
  - Exit: keep semantic-family controls as the primary mechanism unless a later audit proves a literal phrase exception is still required.
