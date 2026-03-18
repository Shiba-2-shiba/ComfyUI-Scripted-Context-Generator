# Context Cutover Plan

## Goal

Record the concrete gates and completion state for removing compat and bridge
surfaces after the context-first migration.

Related documents:
- [Task Plan](./context_v2_tasks.md)
- [Migration Note](./context_migration_notes.md)
- [Progress Log](./context_v2_progress.md)

The machine-readable source of truth is:
- `tools/archive/cutover_plan.json`

## Removal Gates

Compat and bridge nodes were removable only when the following gates were
satisfied for the path being retired:

1. `context_feature_parity`
   The context-first surface covers the required behavior.
2. `migration_docs_complete`
   The replacement path is documented for users and maintainers.
3. `verification_green`
   Python workflow checks, frontend CPU-only checks, and GUI round-trip checks
   are all green after the cutover.
4. `compat_sample_not_required`
   Required only for compat nodes. The compat workflow sample is no longer
   needed as the primary migration regression baseline.

## Node Retirement Map

Retirement should happen in waves rather than deleting all old surfaces at
once.

### Wave 1: Transition Nodes

Wave 1 retirements are complete: `FieldsToContext`, `ContextToFields`, and
`ContextPatch` are removed from the active surface.

### Wave 2: Compat Leaf Nodes

Remove leaf-style compat helpers after the compat sample is no longer needed
and the context-first replacements are stable.

Wave 2 retirements are complete: `CharacterProfileNode`, `DictionaryExpand`,
`ThemeClothingExpander`, and `ThemeLocationExpander`, along with their
dedicated compat fixtures, have been removed from the active surface.

### Wave 3: Compat Core Flow Nodes

Wave 3 retirements are complete: `PackParser`, `SceneVariator`,
`GarnishSampler`, and `SimpleTemplateBuilder` are removed from the active
surface, and there is no remaining compat workflow baseline.

All three retirement waves are now complete. The machine-readable cutover
inventory is empty.

## Practical Cutover Order

1. Keep the public surface on context-first nodes only.
2. Keep historical migration notes in docs/archive only.
3. Do not reintroduce compat or bridge workflow baselines.

The recommended/default verification baseline stays on the context workflow.
Dedicated compat-regression lanes were retired after the Wave 3 cutover
completed.

## Current Readiness Reporting

Use:

`python tools/archive/report_cutover_readiness.py`

This now reports that no active compat or transition nodes remain in the live
cutover inventory.
